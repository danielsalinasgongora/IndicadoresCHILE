from __future__ import annotations

import json
import os
import sqlite3
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from scripts.update_data import update_database

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "indicadores.db"
SEED_PATH = BASE_DIR / "data" / "seed_events_governments.json"


@dataclass(frozen=True)
class IndicatorMeta:
    key: str
    label: str
    unit: str


INDICATORS: dict[str, IndicatorMeta] = {
    "inflation": IndicatorMeta("inflation", "Inflación anual", "%"),
    "gdp_growth": IndicatorMeta("gdp_growth", "Crecimiento PIB real", "%"),
}


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


root_path = os.getenv("ROOT_PATH", "")

app = FastAPI(title="Indicadores Chile Dashboard API", version="1.1.0", lifespan=lifespan, root_path=root_path)

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in allowed_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def require_admin_api_key(x_api_key: str | None = Header(default=None)) -> None:
    configured = os.getenv("ADMIN_API_KEY")
    if not configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ADMIN_API_KEY no está configurada en el servidor.",
        )
    if not x_api_key or x_api_key != configured:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autorizado")


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                indicator TEXT NOT NULL,
                country TEXT NOT NULL,
                year INTEGER NOT NULL,
                value REAL NOT NULL,
                source TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(indicator, country, year)
            );

            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                scope TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS governments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                president TEXT NOT NULL,
                start_year INTEGER NOT NULL,
                end_year INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS risk_country (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER NOT NULL UNIQUE,
                spread_bps REAL NOT NULL
            );
            """
        )

        with open(SEED_PATH, "r", encoding="utf-8") as fp:
            seed = json.load(fp)

        if conn.execute("SELECT COUNT(*) AS c FROM events").fetchone()["c"] == 0:
            conn.executemany(
                "INSERT INTO events(year, title, description, scope) VALUES(?, ?, ?, ?)",
                [(e["year"], e["title"], e["description"], e["scope"]) for e in seed["events"]],
            )

        if conn.execute("SELECT COUNT(*) AS c FROM governments").fetchone()["c"] == 0:
            conn.executemany(
                "INSERT INTO governments(president, start_year, end_year) VALUES(?, ?, ?)",
                [(g["president"], g["start_year"], g["end_year"]) for g in seed["governments"]],
            )

        if conn.execute("SELECT COUNT(*) AS c FROM risk_country").fetchone()["c"] == 0:
            conn.executemany(
                "INSERT INTO risk_country(year, spread_bps) VALUES(?, ?)",
                [(r["year"], r["spread_bps"]) for r in seed["risk_country"]],
            )


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net; style-src 'self'; img-src 'self' data:;"
    return response


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request, "indicators": INDICATORS})


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/metadata/last-update")
def last_update() -> dict[str, str | None]:
    with get_conn() as conn:
        row = conn.execute("SELECT MAX(updated_at) AS last_updated_at FROM observations").fetchone()
    return {"last_updated_at": row["last_updated_at"] if row else None}


@app.post("/api/admin/refresh", dependencies=[Depends(require_admin_api_key)])
def admin_refresh() -> dict[str, str]:
    update_database(DB_PATH)
    return {"status": "updated"}


@app.get("/api/indicators")
def indicators() -> list[dict[str, str]]:
    return [meta.__dict__ for meta in INDICATORS.values()]


def query_series(indicator: str, countries: Iterable[str], start_year: int, end_year: int) -> list[dict]:
    countries_list = list(countries)
    if not countries_list:
        raise HTTPException(status_code=400, detail="Debe enviar al menos un país")
    if indicator not in INDICATORS:
        raise HTTPException(status_code=400, detail=f"Indicador no soportado: {indicator}")

    placeholders = ",".join(["?"] * len(countries_list))
    sql = f"""
        SELECT indicator, country, year, value, source
        FROM observations
        WHERE indicator = ?
          AND country IN ({placeholders})
          AND year BETWEEN ? AND ?
        ORDER BY year ASC
    """
    with get_conn() as conn:
        rows = conn.execute(sql, [indicator, *countries_list, start_year, end_year]).fetchall()
    return [dict(row) for row in rows]


@app.get("/api/series")
def series(
    indicator: str = Query(...),
    countries: str = Query("CHL,OED,WLD"),
    start_year: int = Query(2000, ge=1960, le=2100),
    end_year: int = Query(date.today().year, ge=1960, le=2100),
) -> dict:
    if start_year > end_year:
        raise HTTPException(status_code=400, detail="start_year no puede ser mayor que end_year")
    country_list = [c.strip().upper() for c in countries.split(",") if c.strip()]
    data = query_series(indicator=indicator, countries=country_list, start_year=start_year, end_year=end_year)
    return {"indicator": indicator, "countries": country_list, "data": data}


@app.get("/api/curve/sum")
def sum_curves(
    left: str = Query(..., description="Formato: indicator:country"),
    right: str = Query(..., description="Formato: indicator:country"),
    start_year: int = Query(2000),
    end_year: int = Query(date.today().year),
) -> dict:
    def parse_curve(value: str) -> tuple[str, str]:
        parts = value.split(":")
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail=f"Formato inválido para curva: {value}")
        return parts[0], parts[1].upper()

    left_indicator, left_country = parse_curve(left)
    right_indicator, right_country = parse_curve(right)
    left_rows = query_series(left_indicator, [left_country], start_year, end_year)
    right_rows = query_series(right_indicator, [right_country], start_year, end_year)

    left_by_year = {r["year"]: r["value"] for r in left_rows}
    right_by_year = {r["year"]: r["value"] for r in right_rows}
    years = sorted(set(left_by_year).intersection(right_by_year))

    return {
        "left": {"indicator": left_indicator, "country": left_country},
        "right": {"indicator": right_indicator, "country": right_country},
        "data": [
            {
                "year": y,
                "value": round(left_by_year[y] + right_by_year[y], 4),
                "left": left_by_year[y],
                "right": right_by_year[y],
            }
            for y in years
        ],
    }


@app.get("/api/context/events")
def context_events(start_year: int = 2000, end_year: int = date.today().year) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT year, title, description, scope FROM events WHERE year BETWEEN ? AND ? ORDER BY year ASC",
            (start_year, end_year),
        ).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/risk/governments")
def risk_vs_government(start_year: int = 2000, end_year: int = date.today().year) -> list[dict]:
    with get_conn() as conn:
        risk = conn.execute(
            "SELECT year, spread_bps FROM risk_country WHERE year BETWEEN ? AND ? ORDER BY year",
            (start_year, end_year),
        ).fetchall()
        governments = conn.execute("SELECT president, start_year, end_year FROM governments").fetchall()

    output = []
    for row in risk:
        president = "N/A"
        for gov in governments:
            if gov["start_year"] <= row["year"] <= gov["end_year"]:
                president = gov["president"]
                break
        output.append({"year": row["year"], "spread_bps": row["spread_bps"], "president": president})
    return output


@app.get("/api/insights/overview")
def insights_overview(start_year: int = 2018, end_year: int = date.today().year) -> dict:
    inflation = query_series("inflation", ["CHL", "WLD"], start_year, end_year)
    gdp = query_series("gdp_growth", ["CHL", "OED"], start_year, end_year)
    events = context_events(start_year, end_year)

    def avg(rows: list[dict], country: str) -> float | None:
        vals = [r["value"] for r in rows if r["country"] == country]
        return round(sum(vals) / len(vals), 2) if vals else None

    return {
        "range": {"start_year": start_year, "end_year": end_year},
        "inflation_gap_chile_world": None
        if avg(inflation, "CHL") is None or avg(inflation, "WLD") is None
        else round(avg(inflation, "CHL") - avg(inflation, "WLD"), 2),
        "gdp_gap_chile_oecd": None
        if avg(gdp, "CHL") is None or avg(gdp, "OED") is None
        else round(avg(gdp, "CHL") - avg(gdp, "OED"), 2),
        "events_count": len(events),
    }

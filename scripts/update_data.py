"""Actualiza indicadores desde World Bank API (CHL, OED, WLD)."""

from __future__ import annotations

import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "indicadores.db"

SERIES = {
    "inflation": "FP.CPI.TOTL.ZG",
    "gdp_growth": "NY.GDP.MKTP.KD.ZG",
}
COUNTRIES = ["CHL", "OED", "WLD"]
REQUEST_TIMEOUT_S = int(os.getenv("WORLD_BANK_TIMEOUT_S", "30"))
MAX_RETRIES = int(os.getenv("WORLD_BANK_MAX_RETRIES", "3"))


def fetch_world_bank(country: str, indicator_code: str) -> list[dict]:
    url = f"https://api.worldbank.org/v2/country/{country}/indicator/{indicator_code}?format=json&per_page=200"

    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT_S)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list) or len(payload) < 2:
                return []
            return payload[1]
        except requests.RequestException as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                time.sleep(1.5 * attempt)

    if last_error is not None:
        raise last_error
    return []


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
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
        )
        """
    )


def upsert_observation(conn: sqlite3.Connection, indicator: str, country: str, year: int, value: float) -> None:
    conn.execute(
        """
        INSERT INTO observations(indicator, country, year, value, source, updated_at)
        VALUES(?, ?, ?, ?, ?, ?)
        ON CONFLICT(indicator, country, year)
        DO UPDATE SET
            value = excluded.value,
            source = excluded.source,
            updated_at = excluded.updated_at
        """,
        (indicator, country, year, value, "world_bank", datetime.now(timezone.utc).isoformat()),
    )


def update_database(db_path: Path = DB_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        ensure_table(conn)
        for indicator_key, indicator_code in SERIES.items():
            for country in COUNTRIES:
                rows = fetch_world_bank(country, indicator_code)
                for row in rows:
                    value = row.get("value")
                    year = row.get("date")
                    if value is None or year is None:
                        continue
                    upsert_observation(conn, indicator_key, country, int(year), float(value))
        conn.commit()


def main() -> None:
    update_database(DB_PATH)


if __name__ == "__main__":
    main()

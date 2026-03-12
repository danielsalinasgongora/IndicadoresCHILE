from __future__ import annotations

import os
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import DB_PATH, app, init_db
from scripts import update_data


MOCK_SERIES = [
    {"date": "2023", "value": 5.0},
    {"date": "2022", "value": 8.0},
    {"date": "2021", "value": 4.5},
    {"date": "2020", "value": 3.0},
    {"date": "2019", "value": 2.0},
]


def setup_module() -> None:
    if Path(DB_PATH).exists():
        Path(DB_PATH).unlink()

    init_db()

    original_fetch = update_data.fetch_world_bank
    try:
        update_data.fetch_world_bank = lambda country, indicator: MOCK_SERIES
        update_data.update_database(DB_PATH)
    finally:
        update_data.fetch_world_bank = original_fetch


def test_health() -> None:
    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_series_and_sum() -> None:
    client = TestClient(app)
    series = client.get(
        "/api/series",
        params={"indicator": "inflation", "countries": "CHL,OED,WLD", "start_year": 2019, "end_year": 2023},
    )
    assert series.status_code == 200
    assert len(series.json()["data"]) > 0

    summed = client.get(
        "/api/curve/sum",
        params={"left": "inflation:CHL", "right": "gdp_growth:CHL", "start_year": 2019, "end_year": 2023},
    )
    assert summed.status_code == 200
    assert len(summed.json()["data"]) > 0


def test_insights_and_metadata_endpoints() -> None:
    client = TestClient(app)

    insights = client.get("/api/insights/overview", params={"start_year": 2019, "end_year": 2023})
    assert insights.status_code == 200
    body = insights.json()
    assert "inflation_gap_chile_world" in body
    assert "gdp_gap_chile_oecd" in body

    metadata = client.get("/api/metadata/last-update")
    assert metadata.status_code == 200
    assert metadata.json()["last_updated_at"] is not None


def test_admin_refresh_requires_api_key() -> None:
    client = TestClient(app)

    os.environ.pop("ADMIN_API_KEY", None)
    no_key = client.post("/api/admin/refresh")
    assert no_key.status_code == 503

    os.environ["ADMIN_API_KEY"] = "secret123"
    unauthorized = client.post("/api/admin/refresh")
    assert unauthorized.status_code == 401

    original_fetch = update_data.fetch_world_bank
    try:
        update_data.fetch_world_bank = lambda country, indicator: MOCK_SERIES
        authorized = client.post("/api/admin/refresh", headers={"X-API-Key": "secret123"})
    finally:
        update_data.fetch_world_bank = original_fetch

    assert authorized.status_code == 200
    assert authorized.json()["status"] == "updated"


def test_security_headers_present() -> None:
    client = TestClient(app)
    resp = client.get("/api/health")

    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert "default-src 'self'" in resp.headers["content-security-policy"]

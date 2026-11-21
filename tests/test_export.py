"""CSV export of screened results."""

import csv

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.schemas.screen import PagedCompanies, ScreenRequest
from app.seed.metrics import seed_metrics
from app.services.export import screen_to_csv
from tests.test_screening_api import _seed


def test_export_returns_filtered_rows_and_requested_columns(
    client: TestClient, db_session: Session
) -> None:
    _seed(db_session)

    response = client.post(
        "/api/v1/screen/export",
        json={
            "filters": [{"metric": "sector", "op": "eq", "value": "Technology"}],
            "sort": [{"metric": "market_cap", "dir": "desc"}],
            "columns": ["market_cap", "pe_ratio"],
            "limit": 50,
            "offset": 0,
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    rows = list(csv.reader(response.text.splitlines()))
    assert rows[0][:5] == ["ticker", "name", "exchange", "sector", "industry"]
    assert "market_cap" in rows[0] and "pe_ratio" in rows[0]
    assert {row[0] for row in rows[1:]} == {"AAA", "BBB", "DDD"}


def test_export_keeps_negative_numbers_numeric(db_session: Session) -> None:
    seed_metrics(db_session)
    result = PagedCompanies(
        total=1,
        limit=50,
        offset=0,
        items=[
            {
                "ticker": "NEG",
                "name": "Negative",
                "exchange": None,
                "sector": None,
                "industry": None,
                "metrics": {"roe": "-15.0"},
                "score": None,
                "score_components": {},
                "missing_metrics": [],
            }
        ],
    )

    rows = list(csv.reader(screen_to_csv(result, ScreenRequest(columns=["roe"])).splitlines()))

    assert rows[1][5] == "-15.0"


def test_export_neutralises_formula_injection(db_session: Session) -> None:
    seed_metrics(db_session)
    result = PagedCompanies(
        total=1,
        limit=50,
        offset=0,
        items=[
            {
                "ticker": "=HYPERLINK",
                "name": "+cmd",
                "exchange": None,
                "sector": None,
                "industry": None,
                "metrics": {"pe_ratio": "15"},
                "score": None,
                "score_components": {},
                "missing_metrics": [],
            }
        ],
    )

    csv_text = screen_to_csv(result, ScreenRequest(columns=["pe_ratio"]))
    rows = list(csv.reader(csv_text.splitlines()))

    assert rows[1][0] == "'=HYPERLINK"
    assert rows[1][1] == "'+cmd"

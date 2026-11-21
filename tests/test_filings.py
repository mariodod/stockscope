"""SEC filings for new-filing alerts."""

from datetime import date, timedelta
from typing import Any

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ingestion.jobs import refresh_filings
from app.models import Company, FilingEvent
from app.providers.base import FilingSeed
from app.providers.sec import SECProvider


def test_sec_maps_recent_filings() -> None:
    payload = {
        "filings": {
            "recent": {
                "accessionNumber": ["0001-25-000001", "0001-25-000002"],
                "form": ["10-K", "8-K"],
                "filingDate": ["2026-01-15", "2026-02-01"],
                "primaryDocument": ["10k.htm", "8k.htm"],
            }
        }
    }
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    )

    filings = list(SECProvider(client=client).get_recent_filings("320193", 10))

    assert len(filings) == 2
    assert filings[0].accession_number == "0001-25-000001"
    assert filings[1].form == "8-K"
    assert filings[1].filing_date == date(2026, 2, 1)


def test_filing_ingestion_is_idempotent(db_session: Session) -> None:
    company = Company(ticker="FIL", name="Filing Co", cik="123")
    db_session.add(company)
    db_session.commit()

    class Provider:
        name = "sec"

        def get_recent_filings(self, cik: str | None, limit: int = 20) -> Any:
            yield FilingSeed(
                accession_number="0001-26-000001",
                form="10-Q",
                filing_date=date.today(),
                primary_document="10q.htm",
            )

    provider = Provider()
    assert refresh_filings(db_session, provider, ["FIL"]) == 1
    assert refresh_filings(db_session, provider, ["FIL"]) == 1
    assert db_session.scalar(select(func.count()).select_from(FilingEvent)) == 1


def test_filing_endpoint_filters_by_ticker(client: TestClient, db_session: Session) -> None:
    company = Company(ticker="FIL", name="Filing Co")
    db_session.add(company)
    db_session.flush()
    db_session.add(
        FilingEvent(
            company_id=company.id,
            accession_number="0001-26-000002",
            form="8-K",
            filing_date=date.today() - timedelta(days=2),
            source="sec",
        )
    )
    db_session.commit()

    response = client.get("/api/v1/filings", params={"days": 30, "tickers": "FIL"})

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["form"] == "8-K"

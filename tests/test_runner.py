"""The ingestion runner uses the selected universe provider."""

from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.ingestion import runner
from app.models import Company
from app.providers.base import CompanySeed


def test_runner_uses_selected_universe_provider(monkeypatch: Any) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)

    class FakeProvider:
        name = "fmp"

        def list_companies(self) -> Any:
            yield CompanySeed(ticker="FMP1", name="FMP company")

    monkeypatch.setattr(runner, "build_providers", lambda: {"fmp": FakeProvider()})
    monkeypatch.setattr(runner, "SessionLocal", factory)

    runner.run_job("universe", 10, "fmp")

    with Session(engine) as session:
        assert [row[0] for row in session.execute(select(Company.ticker)).all()] == ["FMP1"]

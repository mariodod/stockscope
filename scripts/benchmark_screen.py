"""Seed a representative universe and time one composite screen run."""

import time
from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import Company, FundamentalFact, Quote
from app.schemas.screen import (
    FilterCondition,
    FilterOp,
    RankingSpec,
    ScreenRequest,
    SortSpec,
)
from app.seed.metrics import seed_metrics
from app.services.screening import screen

COMPANIES = 10_400
METRICS = ("pe_ratio", "roe", "revenue_growth_yoy", "market_cap", "debt_to_equity")


def main() -> None:
    with TemporaryDirectory() as directory:
        url = f"sqlite:///{Path(directory) / 'benchmark.db'}"
        engine = create_engine(url)
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            seed_metrics(session)
            session.add_all(
                Company(
                    ticker=f"S{index:05d}",
                    name=f"Company {index}",
                    sector="Technology" if index % 2 else "Energy",
                    exchange="NASDAQ",
                )
                for index in range(COMPANIES)
            )
            session.commit()
            ids = list(session.scalars(select(Company.id)).all())
            facts = []
            quotes = []
            for index, company_id in enumerate(ids):
                values = {
                    "pe_ratio": 5 + index % 40,
                    "roe": index % 100 / 100,
                    "revenue_growth_yoy": index % 50 / 100,
                    "debt_to_equity": index % 200 / 100,
                }
                for key, value in values.items():
                    facts.append(
                        FundamentalFact(
                            company_id=company_id,
                            metric_key=key,
                            period="TTM",
                            value=Decimal(str(value)),
                            unit="ratio",
                            source="benchmark",
                            as_of_date=date(2026, 1, 1),
                        )
                    )
                quotes.append(
                    Quote(
                        company_id=company_id,
                        date=date(2026, 1, 2),
                        market_cap=Decimal(str(1_000_000_000 + index * 1_000_000)),
                        pe_ratio=Decimal(str(values["pe_ratio"])),
                        source="benchmark",
                    )
                )
            session.add_all(facts)
            session.add_all(quotes)
            session.commit()

            request = ScreenRequest(
                filters=[
                    FilterCondition(metric="market_cap", op=FilterOp.GTE, value=1e9),
                    FilterCondition(metric="pe_ratio", op=FilterOp.LTE, value=30),
                    FilterCondition(metric="debt_to_equity", op=FilterOp.LTE, value=1.5),
                ],
                sort=[SortSpec(metric=key) for key in ("revenue_growth_yoy", "roe", "market_cap")],
                ranking=RankingSpec(
                    weights={"pe_ratio": 0.2, "roe": 0.3, "revenue_growth_yoy": 0.5}
                ),
                columns=list(METRICS),
                limit=50,
            )
            started = time.perf_counter()
            result = screen(session, request)
            elapsed = time.perf_counter() - started
            print(f"companies={COMPANIES} facts={len(facts)}")
            print(f"screen elapsed: {elapsed:.3f}s")
            print(f"total matches: {result.total}, returned: {len(result.items)}")

        engine.dispose()


if __name__ == "__main__":
    main()

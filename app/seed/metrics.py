"""Seed the metric registry from docs/metrics.md, the source of truth.

Run after migrations with: python -m app.seed.metrics
"""

import argparse
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import MetricDefinition, MetricDirection

DOCS_PATH = Path(__file__).resolve().parents[2] / "docs" / "metrics.md"

CATEGORIES = {
    "Valuation": "valuation",
    "Profitability": "profitability",
    "Growth": "growth",
    "Financial health": "financial_health",
    "Dividends & market": "dividends_market",
    "Descriptive (not scored)": "descriptive",
}


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _is_separator(cells: list[str]) -> bool:
    return all(cell and set(cell) <= {"-", ":"} for cell in cells)


def parse_metrics(path: Path = DOCS_PATH) -> list[MetricDefinition]:
    """Parse the markdown tables in the metrics catalog into registry entries."""
    text = path.read_text(encoding="utf-8")
    category = "other"
    metrics: list[MetricDefinition] = []
    seen: set[str] = set()

    for line in text.splitlines():
        if line.startswith("## "):
            heading = line[3:].strip()
            category = CATEGORIES.get(heading, heading.lower().replace(" ", "_"))
            continue
        if not line.startswith("|"):
            continue

        cells = _cells(line)
        if len(cells) not in (3, 5) or cells[0] == "metric_key" or _is_separator(cells):
            continue

        key = cells[0].strip("`")
        if not key or key in seen:
            continue
        seen.add(key)

        if len(cells) == 5:
            label, formula, unit, raw_direction = cells[1], cells[2], cells[3], cells[4]
            description = ""
        else:
            label, description = cells[1], cells[2]
            formula, unit, raw_direction = "", "none", "none"

        try:
            direction = MetricDirection(raw_direction.lower())
        except ValueError:
            direction = MetricDirection.NONE

        metrics.append(
            MetricDefinition(
                key=key,
                label=label,
                category=category,
                unit=unit,
                direction=direction,
                formula=formula,
                description=description,
                is_derived="derived" in formula.lower(),
                active=True,
            )
        )

    return metrics


def seed_metrics(session: Session, path: Path = DOCS_PATH) -> tuple[int, int]:
    """Upsert catalog metrics; returns (inserted, updated) counts. Idempotent."""
    definitions = parse_metrics(path)
    existing = {metric.key: metric for metric in session.scalars(select(MetricDefinition)).all()}

    inserted = 0
    updated = 0
    for definition in definitions:
        current = existing.get(definition.key)
        if current is None:
            session.add(definition)
            inserted += 1
            continue
        current.label = definition.label
        current.category = definition.category
        current.unit = definition.unit
        current.direction = definition.direction
        current.formula = definition.formula
        current.description = definition.description
        current.is_derived = definition.is_derived
        updated += 1

    session.commit()
    return inserted, updated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=DOCS_PATH, help="metrics catalog markdown")
    args = parser.parse_args()

    session = SessionLocal()
    try:
        inserted, updated = seed_metrics(session, args.path)
    finally:
        session.close()
    print(f"Metrics seeded: {inserted} inserted, {updated} updated")


if __name__ == "__main__":
    main()

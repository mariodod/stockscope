"""CSV export for screened company lists."""

import csv
from io import StringIO

from app.schemas.screen import CompanySummary, PagedCompanies, ScreenRequest

MAX_EXPORT_ROWS = 5000

BASE_COLUMNS = ("ticker", "name", "exchange", "sector", "industry")
UNSAFE_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _cell(value: object) -> str:
    """Return a CSV-safe string, neutralising spreadsheet formula injection."""
    if value is None:
        return ""
    text = str(value)
    if text.startswith(UNSAFE_PREFIXES):
        return f"'{text}"
    return text


def _metric_columns(result: PagedCompanies, request: ScreenRequest) -> list[str]:
    keys: list[str] = list(request.columns)
    for item in result.items:
        for key in item.metrics:
            if key not in keys:
                keys.append(key)
    return keys


def _row(item: CompanySummary, columns: list[str]) -> list[str]:
    values: dict[str, object] = {
        "ticker": item.ticker,
        "name": item.name,
        "exchange": item.exchange,
        "sector": item.sector,
        "industry": item.industry,
        "score": item.score,
        "missing_metrics": ", ".join(item.missing_metrics),
    }
    values.update(item.metrics)
    return [_cell(values.get(column)) for column in columns]


def screen_to_csv(result: PagedCompanies, request: ScreenRequest) -> str:
    """Render a screen result as CSV text."""
    columns = [*BASE_COLUMNS, *_metric_columns(result, request), "score", "missing_metrics"]
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(columns)
    for item in result.items:
        writer.writerow(_row(item, columns))
    return output.getvalue()

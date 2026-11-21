"""Conversions from provider payload values into canonical fact values."""

from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any


def dec(value: Any) -> Decimal | None:
    """Return a Decimal for numeric-ish values; None for empty or junk."""
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def whole(value: Any) -> int | None:
    number = dec(value)
    return int(number) if number is not None else None


def as_of(value: Any, fallback: date) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)) and value > 0:
        seconds = value / 1000 if value > 10**11 else value
        try:
            return datetime.fromtimestamp(seconds, tz=UTC).date()
        except (OSError, OverflowError, ValueError):
            return fallback
    if isinstance(value, str) and value:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return fallback
    return fallback

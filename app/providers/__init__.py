"""Data provider adapters and their canonical data shapes."""

from app.providers.base import CompanySeed, FactSeed, Provider, QuoteSeed
from app.providers.fmp import FMPProvider
from app.providers.http import RateLimiter
from app.providers.sec import SECProvider
from app.providers.yf import YFinanceProvider

__all__ = [
    "CompanySeed",
    "FMPProvider",
    "FactSeed",
    "Provider",
    "QuoteSeed",
    "SECProvider",
    "YFinanceProvider",
    "build_providers",
]


def build_providers() -> dict[str, Provider]:
    return {
        "fmp": FMPProvider(limiter=RateLimiter(min_interval=0.25)),
        "sec": SECProvider(limiter=RateLimiter(min_interval=0.15)),
        "yfinance": YFinanceProvider(),
    }

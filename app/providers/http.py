"""Shared HTTP fetch with bounded retries for transient provider failures."""

import time
from typing import Any

import httpx


class ProviderHttpError(RuntimeError):
    """Raised when a provider request cannot be completed."""


RETRYABLE = {429, 500, 502, 503, 504}


def fetch_json(
    client: httpx.Client,
    url: str,
    *,
    params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
) -> Any:
    for attempt in range(3):
        response = client.get(url, params=params, headers=headers)
        if response.status_code in RETRYABLE:
            if attempt < 2:
                time.sleep(0.1 * 2**attempt)
                continue
            raise ProviderHttpError(f"repeated HTTP {response.status_code} from {url}")
        if response.is_error:
            raise ProviderHttpError(f"HTTP {response.status_code} from {url}")
        return response.json()
    raise ProviderHttpError(f"request failed: {url}")

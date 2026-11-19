"""Shared HTTP fetch with rate limiting and bounded retries."""

import threading
import time
from typing import Any

import httpx


class ProviderHttpError(RuntimeError):
    """Raised when a provider request cannot be completed."""


class RateLimiter:
    """Space requests so free-tier providers do not return 429s."""

    def __init__(self, min_interval: float) -> None:
        self.min_interval = min_interval
        self._last = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            elapsed = time.monotonic() - self._last
            delay = self.min_interval - elapsed
            if delay > 0:
                time.sleep(delay)
            self._last = time.monotonic()


RETRYABLE = {429, 500, 502, 503, 504}


def fetch_json(
    client: httpx.Client,
    url: str,
    *,
    params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    limiter: RateLimiter | None = None,
) -> Any:
    for attempt in range(3):
        if limiter is not None:
            limiter.wait()
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

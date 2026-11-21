"""Thread-safe TTL caches for read-only API responses.

In-memory by default; set REDIS_URL and install the `cache` extra to share a
cache between processes.
"""

import json
import threading
import time
from collections.abc import Callable
from decimal import Decimal
from typing import Any, Protocol, TypeVar, cast

from app.config import settings

T = TypeVar("T")


class Cache(Protocol):
    def get_or_set(self, key: str, loader: Callable[[], T]) -> T: ...

    def clear(self) -> None: ...


class TTLCache:
    def __init__(self, default_ttl: float = 60.0) -> None:
        self.default_ttl = default_ttl
        self._entries: dict[str, tuple[float, object]] = {}
        self._lock = threading.Lock()

    def get_or_set(self, key: str, loader: Callable[[], T]) -> T:
        now = time.monotonic()
        with self._lock:
            entry = self._entries.get(key)
            if entry is not None and entry[0] > now:
                return cast(T, entry[1])

        value = loader()
        with self._lock:
            self._entries[key] = (now + self.default_ttl, value)
        return value

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


def _encode(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"Cannot cache value of type {type(value).__name__}")


class RedisCache:
    prefix = "stockscope:"

    def __init__(self, client: Any, default_ttl: int = 60) -> None:
        self.client = client
        self.default_ttl = default_ttl

    def get_or_set(self, key: str, loader: Callable[[], T]) -> T:
        full_key = f"{self.prefix}{key}"
        cached = self.client.get(full_key)
        if cached is not None:
            return cast(T, json.loads(cached))
        value = loader()
        self.client.set(full_key, json.dumps(value, default=_encode), ex=self.default_ttl)
        return value

    def clear(self) -> None:
        for key in self.client.keys(f"{self.prefix}*"):
            self.client.delete(key)


def build_cache() -> Cache:
    if not settings.redis_url:
        return TTLCache()
    import redis

    client = redis.from_url(settings.redis_url)
    return RedisCache(client)


api_cache = build_cache()

"""Small thread-safe TTL cache for read-only API responses."""

import threading
import time
from collections.abc import Callable
from typing import TypeVar, cast

T = TypeVar("T")


class TTLCache:
    def __init__(self, default_ttl: float = 60.0) -> None:
        self.default_ttl = default_ttl
        self._entries: dict[str, tuple[float, object]] = {}
        self._lock = threading.Lock()

    def get_or_set(self, key: str, loader: Callable[[], T], ttl: float | None = None) -> T:
        now = time.monotonic()
        with self._lock:
            entry = self._entries.get(key)
            if entry is not None and entry[0] > now:
                return cast(T, entry[1])

        value = loader()
        with self._lock:
            self._entries[key] = (now + (self.default_ttl if ttl is None else ttl), value)
        return value

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


api_cache = TTLCache(default_ttl=60.0)

"""TTL cache behavior for read-only API responses."""

from typing import Any

from app.cache import TTLCache


def test_cache_reuses_value_until_expiry(monkeypatch: Any) -> None:
    clock = {"now": 100.0}
    monkeypatch.setattr("app.cache.time.monotonic", lambda: clock["now"])
    cache = TTLCache(default_ttl=10.0)
    calls = {"n": 0}

    def load() -> int:
        calls["n"] += 1
        return calls["n"]

    assert cache.get_or_set("key", load) == 1
    assert cache.get_or_set("key", load) == 1

    clock["now"] += 11.0
    assert cache.get_or_set("key", load) == 2
    assert calls["n"] == 2


def test_redis_cache_uses_shared_store_and_json() -> None:
    from app.cache import RedisCache

    store: dict[str, str] = {}

    class FakeRedis:
        def get(self, key: str) -> str | None:
            return store.get(key)

        def set(self, key: str, value: str, ex: int) -> None:
            store[key] = value

        def keys(self, pattern: str) -> list[str]:
            return [key for key in store if key.startswith("stockscope:")]

        def delete(self, key: str) -> None:
            store.pop(key, None)

    cache = RedisCache(FakeRedis())
    assert cache.get_or_set("metrics", lambda: [{"key": "pe_ratio"}]) == [
        {"key": "pe_ratio"}
    ]
    assert "stockscope:metrics" in store
    assert cache.get_or_set("metrics", lambda: []) == [{"key": "pe_ratio"}]

    cache.clear()
    assert store == {}


def test_clear_removes_entries() -> None:
    cache = TTLCache()
    assert cache.get_or_set("key", lambda: "value") == "value"
    cache.clear()
    assert cache.get_or_set("key", lambda: "new") == "new"

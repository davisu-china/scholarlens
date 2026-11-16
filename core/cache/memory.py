"""内存缓存（雏形/测试；含简单 TTL）。"""

from __future__ import annotations

import time


class InMemoryCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[str, float | None]] = {}

    async def get(self, key: str) -> str | None:
        item = self._store.get(key)
        if item is None:
            return None
        value, expire = item
        if expire is not None and time.monotonic() > expire:
            self._store.pop(key, None)
            return None
        return value

    async def set(self, key: str, value: str, *, ttl_seconds: int | None = None) -> None:
        expire = time.monotonic() + ttl_seconds if ttl_seconds else None
        self._store[key] = (value, expire)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

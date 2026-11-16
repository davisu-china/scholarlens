"""Redis 缓存（redis.asyncio）。实现 core.cache.ports.Cache。"""

from __future__ import annotations

from core.config import settings


class RedisCache:
    def __init__(self, url: str | None = None, *, namespace: str = "sl") -> None:
        self._url = url or settings.redis_url
        self._ns = namespace
        self._client = None

    def _key(self, key: str) -> str:
        return f"{self._ns}:{key}"

    def _ensure(self):
        if self._client is None:
            import redis.asyncio as redis

            self._client = redis.from_url(self._url, decode_responses=True)
        return self._client

    async def get(self, key: str) -> str | None:
        return await self._ensure().get(self._key(key))

    async def set(self, key: str, value: str, *, ttl_seconds: int | None = None) -> None:
        await self._ensure().set(self._key(key), value, ex=ttl_seconds)

    async def delete(self, key: str) -> None:
        await self._ensure().delete(self._key(key))

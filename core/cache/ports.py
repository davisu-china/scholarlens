"""缓存接口。Redis 生产实现 + 内存 fake。"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Cache(Protocol):
    async def get(self, key: str) -> str | None: ...
    async def set(self, key: str, value: str, *, ttl_seconds: int | None = None) -> None: ...
    async def delete(self, key: str) -> None: ...

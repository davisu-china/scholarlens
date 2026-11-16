"""异步数据库引擎与建表。"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from core.config import settings
from core.db.schema import metadata

_engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(settings.database_url, future=True)
    return _engine


def make_engine(url: str) -> AsyncEngine:
    """供测试注入独立引擎（如 sqlite+aiosqlite）。"""
    return create_async_engine(url, future=True)


async def create_all(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)


def session_factory(engine: AsyncEngine) -> async_sessionmaker:
    return async_sessionmaker(engine, expire_on_commit=False)

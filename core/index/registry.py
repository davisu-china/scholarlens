"""已入库论文的登记表：支撑知识库列表与按 collection 分组。

雏形内存版；生产可换 Postgres（papers 表）。与解析/索引解耦——ingest 入库后登记。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class PaperMeta:
    paper_id: str
    title: str
    collection: str
    n_chunks: int
    year: int | None = None


@runtime_checkable
class PaperRegistry(Protocol):
    async def add(self, meta: PaperMeta) -> None: ...
    async def list(self, collection: str | None = None) -> list[PaperMeta]: ...
    async def collections(self) -> list[tuple[str, int]]: ...


class InMemoryPaperRegistry:
    def __init__(self) -> None:
        self._papers: dict[str, PaperMeta] = {}

    async def add(self, meta: PaperMeta) -> None:
        self._papers[meta.paper_id] = meta

    async def list(self, collection: str | None = None) -> list[PaperMeta]:
        items = list(self._papers.values())
        if collection:
            items = [p for p in items if p.collection == collection]
        return sorted(items, key=lambda p: p.title)

    async def collections(self) -> list[tuple[str, int]]:
        counts: dict[str, int] = {}
        for p in self._papers.values():
            counts[p.collection] = counts.get(p.collection, 0) + 1
        return sorted(counts.items())

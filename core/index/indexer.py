"""索引编排（PRD 第 06/08 章）。

把一篇 PaperIR 建成可检索状态：
  切分(多粒度 + contextual) → embedding → 写向量库
  表格 → 四元组 → 写表格库
  参考文献 → 写引用图

只依赖 ports，可用 fakes 端到端测试。
"""

from __future__ import annotations

from dataclasses import dataclass

from core.config import settings
from core.index.chunker import MultiGranularityChunker
from core.index.table_extractor import TableExtractor
from core.ingest.schema import PaperIR
from core.ports import Embedder, GraphStore, LLMClient, TableStore, VectorStore


@dataclass
class IndexReport:
    paper_id: str
    n_chunks: int
    n_table_rows: int
    n_citations: int


class Indexer:
    def __init__(
        self,
        *,
        embedder: Embedder,
        vector_store: VectorStore,
        chunker: MultiGranularityChunker | None = None,
        table_extractor: TableExtractor | None = None,
        table_store: TableStore | None = None,
        graph_store: GraphStore | None = None,
        llm: LLMClient | None = None,
        context_model: str | None = None,
    ) -> None:
        self._embedder = embedder
        self._vs = vector_store
        self._chunker = chunker or MultiGranularityChunker(
            llm if settings.contextual_chunk else None,
            concurrency=settings.contextual_concurrency,
            timeout=settings.contextual_timeout,
            model=context_model,
        )
        self._table_extractor = table_extractor
        self._table_store = table_store
        self._graph_store = graph_store

    async def index_paper(
        self, paper: PaperIR, *, collection: str = "default"
    ) -> IndexReport:
        # 1. 切分 + embedding + 写向量库
        chunks = await self._chunker.chunk(paper)
        collection = collection.strip() or "default"
        for c in chunks:
            c.collection = collection
        vectors = await self._embedder.embed([c.indexed_text for c in chunks])
        await self._vs.upsert(chunks, vectors)

        # 2. 表格 → 四元组 → 表格库
        n_rows = 0
        if self._table_store is not None:
            await self._table_store.delete_by_paper(paper.paper_id)
        if self._table_extractor and self._table_store:
            for block in paper.blocks:
                if block.type == "table":
                    rows = await self._table_extractor.extract(block, paper)
                    await self._table_store.insert_rows(rows)
                    n_rows += len(rows)

        # 3. 参考文献 → 引用图
        n_cite = 0
        if self._graph_store:
            await self._graph_store.add_paper(paper.paper_id)
            for ref in paper.references:
                if ref.s2_paper_id:
                    await self._graph_store.add_citation(paper.paper_id, ref.s2_paper_id)
                    n_cite += 1

        return IndexReport(
            paper_id=paper.paper_id, n_chunks=len(chunks), n_table_rows=n_rows, n_citations=n_cite
        )

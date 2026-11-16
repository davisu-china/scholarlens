"""混合检索：四路召回 + RRF 融合 + Cross-Encoder 重排 + 父块扩展。

参见 PRD 第 09 章。本模块只依赖 ports，不关心背后是 Qdrant 还是内存 fake。
"""

from __future__ import annotations

import asyncio

from core.domain import Evidence, Query
from core.obs import langfuse as obs
from core.ports import Embedder, GraphStore, Reranker, TableStore, VectorStore


def rrf_fuse(rankings: list[list[Evidence]], k: int = 60) -> list[Evidence]:
    """Reciprocal Rank Fusion：score = Σ 1/(k + rank_i)。

    对各路分数的尺度/分布不敏感，无需加权调参。相同 id 的证据合并。
    """
    scores: dict[str, float] = {}
    pool: dict[str, Evidence] = {}
    for ranking in rankings:
        for rank, ev in enumerate(ranking):
            scores[ev.id] = scores.get(ev.id, 0.0) + 1.0 / (k + rank)
            pool.setdefault(ev.id, ev)
    ordered = sorted(scores, key=lambda eid: scores[eid], reverse=True)
    out = []
    for eid in ordered:
        ev = pool[eid]
        ev.score = scores[eid]
        out.append(ev)
    return out


class HybridRetriever:
    """把四路召回、融合、重排、扩展编排起来。

    各路后端通过构造函数注入；缺省的路（如没有 graph store）会被跳过。
    """

    def __init__(
        self,
        *,
        embedder: Embedder,
        vector_store: VectorStore,
        reranker: Reranker,
        table_store: TableStore | None = None,
        graph_store: GraphStore | None = None,
        recall_limit: int = 100,
        fuse_top: int = 50,
    ) -> None:
        self._embedder = embedder
        self._vs = vector_store
        self._reranker = reranker
        self._tables = table_store
        self._graph_store = graph_store
        self._recall_limit = recall_limit
        self._fuse_top = fuse_top

    async def _ensure_vectors(self, q: Query) -> Query:
        if q.dense_vec is None or q.sparse_vec is None:
            (dense, sparse), = await self._embedder.embed([q.text])
            q = q.model_copy(update={"dense_vec": dense, "sparse_vec": sparse})
        return q

    async def _dense(self, q: Query) -> list[Evidence]:
        return await self._vs.search_dense(q.dense_vec or [], q.filters, self._recall_limit)

    async def _sparse(self, q: Query) -> list[Evidence]:
        return await self._vs.search_sparse(q.sparse_vec or {}, q.filters, self._recall_limit)

    async def _table(self, q: Query) -> list[Evidence]:
        if self._tables is None or q.intent != "numeric":
            return []
        return await self._tables.query(q)

    async def _graph(self, q: Query) -> list[Evidence]:
        """沿引用图把种子论文的邻居也纳入 dense 召回（payload 过滤到这些论文）。"""
        if self._graph_store is None or not q.seed_papers:
            return []
        neighbors = await self._graph_store.expand(q.seed_papers, hops=1)
        if not neighbors:
            return []
        gq = q.model_copy(update={"filters": {**q.filters, "paper_ids": neighbors}})
        return await self._vs.search_dense(gq.dense_vec or [], gq.filters, self._recall_limit)

    async def retrieve(self, q: Query) -> list[Evidence]:
        with obs.span("retrieve", q.text) as sink:
            q = await self._ensure_vectors(q)
            dense, sparse, table, graph = await asyncio.gather(
                self._dense(q), self._sparse(q), self._table(q), self._graph(q)
            )
            fused = rrf_fuse([dense, sparse, table, graph])[: self._fuse_top]
            sink(metadata={"dense": len(dense), "sparse": len(sparse),
                           "table": len(table), "graph": len(graph), "fused": len(fused)})
            if not fused:
                return []
            with obs.span("rerank") as rsink:
                reranked = await self._reranker.rerank(q.text, fused, q.top_k)
                rsink(metadata={"in": len(fused), "out": len(reranked)})
            return reranked

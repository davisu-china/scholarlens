"""混合检索：四路召回 + RRF 融合 + Cross-Encoder 重排 + 父块扩展。

参见 PRD 第 09 章「混合检索与重排」。
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Literal

from core.ingest.schema import Provenance

QueryIntent = Literal["factoid", "numeric", "survey", "paper_specific"]


@dataclass
class Query:
    text: str
    intent: QueryIntent = "factoid"
    filters: dict = field(default_factory=dict)   # year / venue / collection / 权限
    embedding: list[float] | None = None
    sparse_vec: dict | None = None
    seed_papers: list[str] = field(default_factory=list)


@dataclass
class Evidence:
    id: str                 # evidence id，生成时作为 [eid] 引用
    text: str
    score: float
    provenance: Provenance


async def _noop() -> list[Evidence]:
    return []


def rrf_fuse(rankings: list[list[Evidence]], k: int = 60) -> list[Evidence]:
    """Reciprocal Rank Fusion: score = Σ 1/(k + rank_i)。对各路分数分布不敏感，无需调参。"""
    scores: dict[str, float] = {}
    pool: dict[str, Evidence] = {}
    for ranking in rankings:
        for rank, ev in enumerate(ranking):
            scores[ev.id] = scores.get(ev.id, 0.0) + 1.0 / (k + rank)
            pool[ev.id] = ev
    ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    return [pool[eid] for eid, _ in ordered]


async def hybrid_search(q: Query, k: int = 10) -> list[Evidence]:
    """四路并发召回 → RRF 融合 top50 → 重排 top_k → 父块扩展。"""
    dense, sparse, table, graph = await asyncio.gather(
        _dense_search(q),
        _sparse_search(q),
        _table_search(q) if q.intent == "numeric" else _noop(),
        _graph_expand(q) if q.seed_papers else _noop(),
    )
    fused = rrf_fuse([dense, sparse, table, graph], k=60)[:50]
    reranked = await _rerank(q.text, fused, top_k=k)
    return _expand_to_parent(reranked, max_tokens=6000)


# --- 以下为各路召回 / 重排 / 扩展的占位实现，待接入真实后端 ---

async def _dense_search(q: Query) -> list[Evidence]:
    raise NotImplementedError("TODO: Qdrant dense search (BGE-M3), payload filter 下推")


async def _sparse_search(q: Query) -> list[Evidence]:
    raise NotImplementedError("TODO: Qdrant sparse / BM25 / SPLADE")


async def _table_search(q: Query) -> list[Evidence]:
    raise NotImplementedError("TODO: Postgres 结构化表格查询")


async def _graph_expand(q: Query) -> list[Evidence]:
    raise NotImplementedError("TODO: Neo4j 引用图 1-hop 扩展")


async def _rerank(query: str, evidence: list[Evidence], top_k: int) -> list[Evidence]:
    raise NotImplementedError("TODO: bge-reranker-v2-m3 Cross-Encoder 精排")


def _expand_to_parent(evidence: list[Evidence], max_tokens: int) -> list[Evidence]:
    raise NotImplementedError("TODO: Small-to-Big 父块扩展，同章节合并")

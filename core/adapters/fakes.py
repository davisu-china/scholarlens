"""所有 port 的内存假实现。

目标：行为「足够真实」，让整条检索/问答链路能在单测里端到端跑通，而不需要
Qdrant / Neo4j / GPU / 模型下载。向量用确定性的词袋哈希，相似度可预测可断言。
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import defaultdict
from collections.abc import AsyncIterator

from pydantic import BaseModel

from core.domain import Chunk, Evidence, Query
from core.ingest.schema import PaperIR, ResultRow

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_DIM = 64


def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _hash_bucket(token: str, dim: int) -> int:
    return int(hashlib.md5(token.encode()).hexdigest(), 16) % dim


def _dense(text: str, dim: int = _DIM) -> list[float]:
    """确定性词袋向量，L2 归一化。"""
    vec = [0.0] * dim
    for tok in _tokens(text):
        vec[_hash_bucket(tok, dim)] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _sparse(text: str) -> dict[int, float]:
    counts: dict[int, float] = defaultdict(float)
    for tok in _tokens(text):
        counts[_hash_bucket(tok, 1 << 20)] += 1.0
    return dict(counts)


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def _sparse_dot(a: dict[int, float], b: dict[int, float]) -> float:
    small, large = (a, b) if len(a) <= len(b) else (b, a)
    return sum(w * large.get(k, 0.0) for k, w in small.items())


def _match_filters(chunk: Chunk, filters: dict) -> bool:
    """fake 只支持 paper_id / collection 两种过滤键，够测试用。"""
    if "paper_id" in filters and chunk.paper_id != filters["paper_id"]:
        return False
    if "paper_ids" in filters and chunk.paper_id not in filters["paper_ids"]:
        return False
    return True


class FakeEmbedder:
    async def embed(self, texts: list[str]) -> list[tuple[list[float], dict[int, float]]]:
        return [(_dense(t), _sparse(t)) for t in texts]


class FakeVectorStore:
    """按 chunk 存向量，dense 用 cosine、sparse 用点积排序。"""

    def __init__(self) -> None:
        self._chunks: dict[str, Chunk] = {}
        self._dense: dict[str, list[float]] = {}
        self._sparse: dict[str, dict[int, float]] = {}

    async def upsert(
        self, chunks: list[Chunk], vectors: list[tuple[list[float], dict[int, float]]]
    ) -> None:
        for chunk, (dvec, svec) in zip(chunks, vectors, strict=True):
            self._chunks[chunk.id] = chunk
            self._dense[chunk.id] = dvec
            self._sparse[chunk.id] = svec

    def _to_evidence(self, cid: str, score: float) -> Evidence:
        c = self._chunks[cid]
        return Evidence(
            id=cid, text=c.text, score=score, provenance=c.provenance, section_path=c.section_path
        )

    async def search_dense(self, vec: list[float], filters: dict, limit: int) -> list[Evidence]:
        scored = [
            (cid, _cosine(vec, dv))
            for cid, dv in self._dense.items()
            if _match_filters(self._chunks[cid], filters)
        ]
        scored.sort(key=lambda kv: kv[1], reverse=True)
        return [self._to_evidence(cid, s) for cid, s in scored[:limit]]

    async def search_sparse(self, vec: dict[int, float], filters: dict, limit: int) -> list[Evidence]:
        scored = [
            (cid, _sparse_dot(vec, sv))
            for cid, sv in self._sparse.items()
            if _match_filters(self._chunks[cid], filters) and _sparse_dot(vec, sv) > 0
        ]
        scored.sort(key=lambda kv: kv[1], reverse=True)
        return [self._to_evidence(cid, s) for cid, s in scored[:limit]]


class FakeReranker:
    """用 query 与候选的 token Jaccard 相似度重排。"""

    async def rerank(self, query: str, candidates: list[Evidence], top_k: int) -> list[Evidence]:
        q = set(_tokens(query))

        def jaccard(ev: Evidence) -> float:
            t = set(_tokens(ev.text))
            return len(q & t) / len(q | t) if (q | t) else 0.0

        ranked = sorted(candidates, key=jaccard, reverse=True)
        for ev in ranked:
            ev.score = jaccard(ev)
        return ranked[:top_k]


class FakeGraphStore:
    def __init__(self) -> None:
        self._out: dict[str, set[str]] = defaultdict(set)   # 引用
        self._in: dict[str, set[str]] = defaultdict(set)    # 被引
        self._papers: set[str] = set()

    async def add_paper(self, paper_id: str) -> None:
        self._papers.add(paper_id)

    async def add_citation(self, src_paper_id: str, dst_paper_id: str) -> None:
        self._out[src_paper_id].add(dst_paper_id)
        self._in[dst_paper_id].add(src_paper_id)

    async def expand(self, seed_papers: list[str], hops: int) -> list[str]:
        seen: set[str] = set(seed_papers)
        frontier = set(seed_papers)
        for _ in range(hops):
            nxt: set[str] = set()
            for p in frontier:
                nxt |= self._out[p] | self._in[p]
            nxt -= seen
            seen |= nxt
            frontier = nxt
        return sorted(seen - set(seed_papers))


class FakeLLM:
    """可脚本化的假 LLM。

    - responses: 按调用顺序返回的文本列表（complete / stream）
    - structured_responses: structured() 按顺序返回的对象
    """

    def __init__(
        self,
        responses: list[str] | None = None,
        structured_responses: list[BaseModel] | None = None,
    ) -> None:
        self._responses = list(responses or [])
        self._structured = list(structured_responses or [])
        self.calls: list[str] = []

    async def complete(self, prompt: str, *, model: str | None = None, system: str | None = None) -> str:
        self.calls.append(prompt)
        return self._responses.pop(0) if self._responses else ""

    async def stream(
        self, prompt: str, *, model: str | None = None, system: str | None = None
    ) -> AsyncIterator[str]:
        text = await self.complete(prompt, model=model, system=system)
        for tok in text.split(" "):
            yield tok + " "

    async def structured[T: BaseModel](self, prompt: str, schema: type[T], *, model: str | None = None) -> T:
        self.calls.append(prompt)
        if not self._structured:
            # 没有预置时返回该 schema 的空实例（字段都有默认值的 schema 可构造）。
            return schema()
        obj = self._structured.pop(0)
        assert isinstance(obj, schema), f"预置返回 {type(obj)} 与期望 {schema} 不符"
        return obj


class FakeNLI:
    """token 重叠比例近似蕴含概率：假设的词被前提覆盖得越多，概率越高。"""

    async def entailment(self, pairs: list[tuple[str, str]]) -> list[float]:
        probs = []
        for premise, hypothesis in pairs:
            p, h = set(_tokens(premise)), set(_tokens(hypothesis))
            probs.append(len(p & h) / len(h) if h else 0.0)
        return probs


class FakeParser:
    """返回预置的 PaperIR（构造测试数据用）。"""

    def __init__(self, paper: PaperIR) -> None:
        self._paper = paper

    async def parse(self, pdf_bytes: bytes, *, source_hint: str | None = None) -> PaperIR:
        return self._paper


class FakeTableStore:
    def __init__(self) -> None:
        self.rows: list[ResultRow] = []

    async def insert_rows(self, rows: list[ResultRow]) -> None:
        self.rows.extend(rows)

    async def query(self, q: Query) -> list[Evidence]:
        hits = []
        q_tokens = set(_tokens(q.text))
        for i, r in enumerate(self.rows):
            text = f"{r.method} on {r.dataset}: {r.metric}={r.value}"
            if q_tokens & set(_tokens(text)):
                prov = r.source or None
                hits.append(
                    Evidence(
                        id=f"table-{i}",
                        text=text,
                        score=1.0,
                        provenance=prov or _null_provenance(),
                    )
                )
        return hits


class FakeBlobStore:
    def __init__(self) -> None:
        self._store: dict[str, bytes] = {}

    async def put(self, key: str, data: bytes) -> None:
        self._store[key] = data

    async def get(self, key: str) -> bytes:
        return self._store[key]

    async def exists(self, key: str) -> bool:
        return key in self._store


def _null_provenance():
    from core.ingest.schema import Provenance

    return Provenance(paper_id="unknown", block_id="unknown")

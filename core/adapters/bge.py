"""真实向量化 adapter：BGE-M3（dense+sparse 一次前向）+ bge-reranker-v2-m3。

实现 core.ports.Embedder 与 core.ports.Reranker。模型用 FlagEmbedding 加载。
⚠️ 需下载模型（GPU 更快），无法在无依赖沙箱里运行。
"""

from __future__ import annotations

from core.config import settings
from core.domain import Evidence


class BGEM3Embedder:
    """BGE-M3：一次前向同时得到 dense 向量与 sparse(lexical weights)。"""

    def __init__(self, model_name: str | None = None, *, use_fp16: bool = True) -> None:
        self._model_name = model_name or settings.embedding_model
        self._use_fp16 = use_fp16
        self._model = None

    def _ensure(self):
        if self._model is None:
            from FlagEmbedding import BGEM3FlagModel

            self._model = BGEM3FlagModel(self._model_name, use_fp16=self._use_fp16)
        return self._model

    async def embed(self, texts: list[str]) -> list[tuple[list[float], dict[int, float]]]:
        model = self._ensure()
        out = model.encode(texts, return_dense=True, return_sparse=True, return_colbert_vecs=False)
        dense = out["dense_vecs"]
        sparse = out["lexical_weights"]  # list[dict[token_id_str, weight]]
        results = []
        for i in range(len(texts)):
            dvec = [float(x) for x in dense[i]]
            svec = {int(k): float(v) for k, v in sparse[i].items()}
            results.append((dvec, svec))
        return results


class BGEReranker:
    """bge-reranker-v2-m3 Cross-Encoder 精排。"""

    def __init__(self, model_name: str | None = None, *, use_fp16: bool = True) -> None:
        self._model_name = model_name or settings.reranker_model
        self._use_fp16 = use_fp16
        self._model = None

    def _ensure(self):
        if self._model is None:
            from FlagEmbedding import FlagReranker

            self._model = FlagReranker(self._model_name, use_fp16=self._use_fp16)
        return self._model

    async def rerank(self, query: str, candidates: list[Evidence], top_k: int) -> list[Evidence]:
        if not candidates:
            return []
        model = self._ensure()
        scores = model.compute_score([[query, ev.text] for ev in candidates], normalize=True)
        if not isinstance(scores, list):
            scores = [scores]
        for ev, s in zip(candidates, scores, strict=True):
            ev.score = float(s)
        return sorted(candidates, key=lambda e: e.score, reverse=True)[:top_k]

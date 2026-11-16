"""硅基流动 API 向量化与重排（无需本地 GPU）。

- SiliconFlowEmbedder 实现 core.ports.Embedder：
    dense 走硅基流动 /embeddings（bge-m3，1024 维）；
    sparse 由本地词法编码器给出（见 bm25_sparse.py）——因为 OpenAI 兼容的 embeddings
    接口只返回 dense，拿不到 bge-m3 的学习型 sparse。词法 sparse 已能覆盖"专有名词精确
    召回"这一主要价值（模型名、数据集名）。
- SiliconFlowReranker 实现 core.ports.Reranker：走 /rerank（bge-reranker-v2-m3）。

httpx 延迟导入；transport 可注入 MockTransport 便于测试。
"""

from __future__ import annotations

from core.adapters.bm25_sparse import LexicalSparseEncoder
from core.config import settings
from core.domain import Evidence


class SiliconFlowEmbedder:
    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str | None = None,
        model: str | None = None,
        transport=None,
    ) -> None:
        self._key = api_key or settings.siliconflow_api_key
        self._base = (base_url or settings.siliconflow_api_base).rstrip("/")
        self._model = model or settings.embedding_model
        self._transport = transport
        self._sparse = LexicalSparseEncoder()

    async def embed(self, texts: list[str]) -> list[tuple[list[float], dict[int, float]]]:
        if not texts:
            return []
        if not self._key:
            raise RuntimeError("未配置 SL_SILICONFLOW_API_KEY")
        import httpx

        async with httpx.AsyncClient(timeout=60.0, transport=self._transport) as client:
            resp = await client.post(
                f"{self._base}/embeddings",
                headers={"Authorization": f"Bearer {self._key}"},
                json={"model": self._model, "input": texts},
            )
            resp.raise_for_status()
            data = resp.json()["data"]
        # 按 index 排序，保证与输入顺序一致
        dense = [item["embedding"] for item in sorted(data, key=lambda d: d["index"])]
        return [(dense[i], self._sparse.encode(texts[i])) for i in range(len(texts))]


class SiliconFlowReranker:
    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str | None = None,
        model: str | None = None,
        transport=None,
    ) -> None:
        self._key = api_key or settings.siliconflow_api_key
        self._base = (base_url or settings.siliconflow_api_base).rstrip("/")
        self._model = model or settings.reranker_model
        self._transport = transport

    async def rerank(self, query: str, candidates: list[Evidence], top_k: int) -> list[Evidence]:
        if not candidates:
            return []
        if not self._key:
            raise RuntimeError("未配置 SL_SILICONFLOW_API_KEY")
        import httpx

        async with httpx.AsyncClient(timeout=60.0, transport=self._transport) as client:
            resp = await client.post(
                f"{self._base}/rerank",
                headers={"Authorization": f"Bearer {self._key}"},
                json={
                    "model": self._model,
                    "query": query,
                    "documents": [c.text for c in candidates],
                    "top_n": min(top_k, len(candidates)),
                },
            )
            resp.raise_for_status()
            results = resp.json()["results"]
        out: list[Evidence] = []
        for r in results:
            ev = candidates[r["index"]]
            ev.score = float(r["relevance_score"])
            out.append(ev)
        return out

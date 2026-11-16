"""带缓存的 Embedder 装饰器：按文本缓存 (dense, sparse)，命中则跳过 API 调用。

学术库里大量 chunk 会重复出现相同句子（公式、常见术语、重复段落），缓存能显著
减少向量化的 API 调用与费用。缓存 key 用文本哈希；装饰任意 Embedder。
"""

from __future__ import annotations

import hashlib
import json

from core.cache.ports import Cache
from core.ports import Embedder


def _key(model: str, text: str) -> str:
    h = hashlib.sha256(text.encode()).hexdigest()[:24]
    return f"emb:{model}:{h}"


class CachedEmbedder:
    def __init__(self, inner: Embedder, cache: Cache, *, model_tag: str = "bge-m3", ttl_seconds: int | None = None) -> None:
        self._inner = inner
        self._cache = cache
        self._tag = model_tag
        self._ttl = ttl_seconds

    async def embed(self, texts: list[str]) -> list[tuple[list[float], dict[int, float]]]:
        results: list[tuple[list[float], dict[int, float]] | None] = [None] * len(texts)
        miss_idx: list[int] = []
        miss_texts: list[str] = []

        # 1. 查缓存
        for i, t in enumerate(texts):
            cached = await self._cache.get(_key(self._tag, t))
            if cached is not None:
                dense, sparse = json.loads(cached)
                results[i] = (dense, {int(k): v for k, v in sparse.items()})
            else:
                miss_idx.append(i)
                miss_texts.append(t)

        # 2. 未命中的批量调底层，并回写缓存
        if miss_texts:
            fresh = await self._inner.embed(miss_texts)
            for j, (i, t) in enumerate(zip(miss_idx, miss_texts, strict=True)):
                dense, sparse = fresh[j]
                results[i] = (dense, sparse)
                await self._cache.set(
                    _key(self._tag, t),
                    json.dumps([dense, {str(k): v for k, v in sparse.items()}]),
                    ttl_seconds=self._ttl,
                )

        return [r for r in results if r is not None]

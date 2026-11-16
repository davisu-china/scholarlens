"""缓存：内存缓存 TTL、带缓存 embedder 命中跳过底层调用。"""
import pytest

from core import ports
from core.adapters.cached_embedder import CachedEmbedder
from core.adapters.fakes import FakeEmbedder
from core.cache.memory import InMemoryCache
from core.cache.ports import Cache


async def test_memory_cache_set_get_delete():
    c = InMemoryCache()
    assert await c.get("k") is None
    await c.set("k", "v")
    assert await c.get("k") == "v"
    await c.delete("k")
    assert await c.get("k") is None


async def test_memory_cache_ttl(monkeypatch):
    import core.cache.memory as m
    t = {"now": 1000.0}
    monkeypatch.setattr(m.time, "monotonic", lambda: t["now"])
    c = InMemoryCache()
    await c.set("k", "v", ttl_seconds=10)
    t["now"] = 1005.0
    assert await c.get("k") == "v"       # 未过期
    t["now"] = 1011.0
    assert await c.get("k") is None      # 过期


class CountingEmbedder(FakeEmbedder):
    def __init__(self):
        self.calls = 0
    async def embed(self, texts):
        self.calls += 1
        return await super().embed(texts)


async def test_cached_embedder_skips_repeat_calls():
    inner = CountingEmbedder()
    emb = CachedEmbedder(inner, InMemoryCache())
    r1 = await emb.embed(["position interpolation", "yarn"])
    assert inner.calls == 1
    # 同样文本再来 → 全命中缓存，不再调底层
    r2 = await emb.embed(["position interpolation", "yarn"])
    assert inner.calls == 1
    assert r1[0][0] == r2[0][0]          # dense 一致
    # 部分新文本 → 只为新的调一次
    await emb.embed(["position interpolation", "brand new text"])
    assert inner.calls == 2


async def test_cached_embedder_preserves_order_and_sparse():
    emb = CachedEmbedder(FakeEmbedder(), InMemoryCache())
    out = await emb.embed(["alpha", "beta", "alpha"])
    assert len(out) == 3
    assert out[0][0] == out[2][0]        # 两个 alpha 相同
    assert isinstance(out[0][1], dict)   # sparse 还原为 {int: float}


def test_memory_cache_satisfies_port():
    assert isinstance(InMemoryCache(), Cache)
    from core.cache.redis_cache import RedisCache
    assert isinstance(RedisCache(), Cache)


async def test_cached_embedder_satisfies_embedder_port():
    assert isinstance(CachedEmbedder(FakeEmbedder(), InMemoryCache()), ports.Embedder)

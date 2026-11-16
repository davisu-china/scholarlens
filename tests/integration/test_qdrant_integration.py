"""Qdrant 真实读写（需 docker compose 起 Qdrant）。"""
import pytest
import pytest_asyncio

from core.adapters.qdrant_store import QdrantVectorStore
from core.adapters.fakes import FakeEmbedder
from core.domain import Chunk, Granularity, Query
from core.ingest.schema import Provenance

pytestmark = pytest.mark.parametrize("host_port", [("localhost", 6333)])


@pytest_asyncio.fixture
async def store(require):
    s = QdrantVectorStore(collection="sl_itest", dense_dim=64)  # FakeEmbedder 是 64 维
    yield s
    import contextlib
    with contextlib.suppress(Exception):
        await s._ensure().delete_collection("sl_itest")


async def test_upsert_and_hybrid_search(store):
    emb = FakeEmbedder()
    chunks = [
        Chunk(id="c1", paper_id="p1", level=Granularity.CHUNK, text="position interpolation fine tuning",
              provenance=Provenance(paper_id="p1", block_id="c1")),
        Chunk(id="c2", paper_id="p2", level=Granularity.CHUNK, text="image classification cats dogs",
              provenance=Provenance(paper_id="p2", block_id="c2")),
    ]
    await store.upsert(chunks, await emb.embed([c.text for c in chunks]))
    (qv, _), = await emb.embed(["position interpolation"])
    hits = await store.search_dense(qv, {}, limit=5)
    assert hits and hits[0].provenance.paper_id == "p1"
    # payload 过滤
    filtered = await store.search_dense(qv, {"paper_id": "p2"}, limit=5)
    assert all(h.provenance.paper_id == "p2" for h in filtered)

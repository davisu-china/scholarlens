import pytest
import pytest_asyncio

from core.adapters.fakes import FakeEmbedder, FakeGraphStore, FakeReranker, FakeVectorStore
from core.domain import Chunk, Evidence, Granularity, Query
from core.ingest.schema import Provenance
from core.retrieval.hybrid import HybridRetriever, rrf_fuse


def _ev(eid, score=0.0):
    return Evidence(id=eid, text=eid, score=score, provenance=Provenance(paper_id="p", block_id="b"))


def test_rrf_rewards_consensus():
    r1 = [_ev("A"), _ev("B"), _ev("C")]
    r2 = [_ev("A"), _ev("C"), _ev("D")]
    assert rrf_fuse([r1, r2])[0].id == "A"


def test_rrf_dedups_and_sets_score():
    fused = rrf_fuse([[_ev("A"), _ev("B")], [_ev("A"), _ev("B")]])
    assert sorted(e.id for e in fused) == ["A", "B"]
    assert all(e.score > 0 for e in fused)


def _chunk(cid, paper, text):
    return Chunk(id=cid, paper_id=paper, level=Granularity.CHUNK, text=text,
                 provenance=Provenance(paper_id=paper, block_id=cid))


@pytest_asyncio.fixture
async def retriever():
    emb, vs = FakeEmbedder(), FakeVectorStore()
    chunks = [
        _chunk("c1", "p1", "position interpolation requires fine tuning"),
        _chunk("c2", "p1", "yarn frequency interpolation lower perplexity at 128k"),
        _chunk("c3", "p2", "unrelated text about image classification cats"),
    ]
    vectors = await emb.embed([c.text for c in chunks])
    await vs.upsert(chunks, vectors)
    return HybridRetriever(embedder=emb, vector_store=vs, reranker=FakeReranker())


async def test_hybrid_retrieve_ranks_relevant_first(retriever):
    hits = await retriever.retrieve(Query(text="yarn perplexity at 128k", top_k=2))
    assert hits, "should retrieve something"
    assert hits[0].id == "c2"
    assert "c3" not in [h.id for h in hits]


async def test_filters_restrict_to_paper(retriever):
    hits = await retriever.retrieve(Query(text="interpolation", filters={"paper_id": "p2"}, top_k=5))
    assert all(h.provenance.paper_id == "p2" for h in hits)


async def test_graph_expand_two_hops():
    g = FakeGraphStore()
    for a, b in [("p1", "p2"), ("p2", "p3")]:
        await g.add_citation(a, b)
    assert await g.expand(["p1"], hops=1) == ["p2"]
    assert await g.expand(["p1"], hops=2) == ["p2", "p3"]

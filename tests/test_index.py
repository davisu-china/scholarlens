import pytest

from core.adapters.fakes import (
    FakeEmbedder, FakeGraphStore, FakeLLM, FakeTableStore, FakeVectorStore,
)
from core.domain import Query
from core.index.indexer import Indexer
from core.index.table_extractor import TableExtractor, normalize_method, value_in_table
from core.index.table_extractor import _RawRow, _RawRows
from core.retrieval.hybrid import HybridRetriever
from core.adapters.fakes import FakeReranker


def test_normalize_method():
    assert normalize_method("YaRN (s=16)") == "YaRN"
    assert normalize_method("YaRN（动态）") == "YaRN"
    assert normalize_method("  PI  ") == "PI"


def test_value_in_table():
    html = "<table><tr><td>3.2</td><td>128</td></tr></table>"
    assert value_in_table(3.2, html)
    assert not value_in_table(9.9, html)


async def test_table_extractor_drops_hallucinated_values(paper):
    table = next(b for b in paper.blocks if b.type == "table")
    # LLM 抽出两行：一行数值在表中(3.2)，一行不在(9.9) → 后者应被丢弃
    llm = FakeLLM(structured_responses=[_RawRows(rows=[
        _RawRow(method="YaRN (s=16)", dataset="128K", metric="PPL", value=3.2),
        _RawRow(method="Fake", dataset="X", metric="PPL", value=9.9),
    ])])
    rows = await TableExtractor(llm).extract(table, paper)
    assert len(rows) == 1
    assert rows[0].method == "YaRN"
    assert rows[0].source.paper_id == "p1"


async def test_indexer_makes_paper_retrievable(paper):
    emb, vs = FakeEmbedder(), FakeVectorStore()
    indexer = Indexer(embedder=emb, vector_store=vs)
    report = await indexer.index_paper(paper)
    assert report.n_chunks > 0

    retriever = HybridRetriever(embedder=emb, vector_store=vs, reranker=FakeReranker())
    hits = await retriever.retrieve(Query(text="frequency interpolation perplexity 128k"))
    assert hits
    assert hits[0].provenance.paper_id == "p1"


async def test_indexer_builds_citation_graph(paper):
    paper.references[0].s2_paper_id = "p-chen"
    g = FakeGraphStore()
    indexer = Indexer(
        embedder=FakeEmbedder(), vector_store=FakeVectorStore(),
        table_extractor=None, table_store=None, graph_store=g,
    )
    report = await indexer.index_paper(paper)
    assert report.n_citations == 1
    assert await g.expand(["p1"], hops=1) == ["p-chen"]

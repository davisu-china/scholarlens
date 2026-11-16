import pytest

from core.adapters.fakes import FakeLLM
from core.domain import Granularity
from core.index.chunker import MultiGranularityChunker, estimate_tokens


async def test_chunker_produces_all_levels(paper):
    chunks = await MultiGranularityChunker().chunk(paper)
    levels = {c.level for c in chunks}
    assert Granularity.PAPER in levels
    assert Granularity.SECTION in levels
    assert Granularity.CHUNK in levels
    assert Granularity.ELEMENT in levels


async def test_paper_chunk_has_title_and_abstract(paper):
    chunks = await MultiGranularityChunker().chunk(paper)
    l0 = next(c for c in chunks if c.level == Granularity.PAPER)
    assert "YaRN" in l0.text and "context window" in l0.text.lower()


async def test_leaf_chunks_carry_provenance(paper):
    chunks = await MultiGranularityChunker().chunk(paper)
    leaves = [c for c in chunks if c.level == Granularity.CHUNK]
    assert leaves
    for c in leaves:
        assert c.provenance.paper_id == "p1"
        assert c.section_path  # 不跨章节，带章节路径


async def test_contextual_prefix_added_when_llm_present(paper):
    llm = FakeLLM(responses=["本段出自 YaRN 论文方法节"] * 20)
    chunks = await MultiGranularityChunker(llm).chunk(paper)
    l2 = [c for c in chunks if c.level == Granularity.CHUNK]
    assert all(c.context_prefix for c in l2)
    assert l2[0].context_prefix in l2[0].indexed_text


def test_estimate_tokens():
    assert estimate_tokens("hello world") <= 5
    assert estimate_tokens("中文四个字") == 5

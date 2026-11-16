"""端到端：用 fakes 把 索引 → 问答 / 深度研究 跑通。"""
import pytest
import pytest_asyncio

from core.adapters.fakes import FakeLLM
from core.agent.schemas import InfoPoints, ResearchPlan, PlanItem
from core.container import build_container


@pytest_asyncio.fixture
async def indexed_container(paper):
    """装好一篇论文、可直接问答的容器。"""
    c = build_container()
    await c.indexer.index_paper(paper)
    return c


async def test_qa_end_to_end(indexed_container):
    c = indexed_container
    # 让 FakeLLM 产出带引用的答案；证据 id 由服务分配为 e0/e1...
    c.qa._llm = FakeLLM(responses=["YaRN reaches lower perplexity at 128K [e0]."])
    c.verifier._llm = c.qa._llm
    result = await c.qa.answer("yarn perplexity at 128k")
    assert result.evidence
    assert result.answer.claims
    # 该论断能在证据里找到支撑
    assert any(claim.best_eid is not None for claim in result.answer.claims)


async def test_qa_refuses_without_evidence():
    c = build_container()  # 空库
    result = await c.qa.answer("something with no indexed evidence at all")
    assert "没有找到" in result.answer.answer
    assert result.evidence == {}


async def test_qa_stream_yields_tokens_then_done(indexed_container):
    c = indexed_container
    c.qa._llm = FakeLLM(responses=["YaRN lower perplexity [e0]."])
    c.verifier._llm = c.qa._llm
    events = [ev async for ev in c.qa.stream("yarn perplexity")]
    assert events[0]["event"] == "token"
    assert events[-1]["event"] == "done"
    assert "trust" in events[-1]["data"]


async def test_deep_research_end_to_end(indexed_container):
    c = indexed_container
    # 脚本化 LLM：structured() 依次返回 计划、各子问题信息点；complete() 返回综述
    llm = FakeLLM(
        responses=["YaRN interpolates by frequency and reaches lower perplexity at 128K [e0]."],
        structured_responses=[
            ResearchPlan(subquestions=[PlanItem(text="yarn perplexity at 128k")]),
            InfoPoints(points=["yarn perplexity", "128k"]),
        ],
    )
    c.coordinator._llm = llm
    c.verifier._llm = llm
    result = await c.coordinator.run("how does yarn extend context")
    assert result.plan == ["yarn perplexity at 128k"]
    assert result.rounds >= 1
    assert result.answer.claims
    kinds = [s.kind for s in result.trace]
    assert kinds[0] == "plan" and "write" in kinds and "verify" in kinds

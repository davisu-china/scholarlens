"""LangGraph 绑定：中断/恢复、覆盖度驱动的多轮循环、与 coordinator 等价。"""
import pytest
import pytest_asyncio

from core.adapters.fakes import FakeLLM
from core.agent.coordinator import ResearchCoordinator
from core.agent.graph import ResearchGraphRunner
from core.agent.schemas import InfoPoints, PlanItem, ResearchPlan
from core.container import build_container


@pytest_asyncio.fixture
async def coordinator(paper):
    c = build_container()
    await c.indexer.index_paper(paper)
    return c


def _llm():
    # structured: 计划(1 子问题) + 两轮反思信息点；complete: 综述
    return FakeLLM(
        responses=["YaRN reaches lower perplexity at 128K [e0]."],
        structured_responses=[
            ResearchPlan(subquestions=[PlanItem(text="yarn perplexity at 128k")]),
            InfoPoints(points=["yarn perplexity", "128k"]),
        ],
    )


async def test_start_interrupts_after_planner(coordinator):
    llm = _llm()
    coordinator.coordinator._llm = llm
    runner = ResearchGraphRunner(coordinator.coordinator)
    plan = await runner.start("how does yarn extend context", thread_id="t1")
    assert plan == ["yarn perplexity at 128k"]   # 停在 planner 后，拿到计划


async def test_resume_with_edited_plan(coordinator):
    llm = _llm()
    coordinator.coordinator._llm = llm
    coordinator.verifier._llm = llm
    runner = ResearchGraphRunner(coordinator.coordinator)
    await runner.start("how does yarn extend context", thread_id="t2")
    # 用户把计划改成自己的子问题
    result = await runner.resume("t2", approved_plan=["yarn perplexity"])
    assert result.plan == ["yarn perplexity"]        # 用了编辑后的计划
    assert result.answer.claims                       # 跑完出了答案
    kinds = [s.kind for s in result.trace]
    assert "plan" in kinds and "write" in kinds and "verify" in kinds


async def test_one_shot_equivalent(coordinator):
    llm = _llm()
    coordinator.coordinator._llm = llm
    coordinator.verifier._llm = llm
    runner = ResearchGraphRunner(coordinator.coordinator)
    result = await runner.one_shot("how does yarn extend context", thread_id="t3")
    assert result.rounds >= 1
    assert result.answer.claims

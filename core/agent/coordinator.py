"""深度研究 Agent 协调器（PRD 第 10 章）。

这是 Agent 的「大脑」，用 ports 编排，可在单测里用 fakes 端到端跑：
  Plan → (Human Review) → [Research → Reflect]×N → Write → Verify

关键设计：用「证据覆盖度」而非固定轮数决定是否继续补检索（≤max_rounds 轮）。
未覆盖的信息点直接转成下一轮的补充查询，使补检索有明确目标。

LangGraph 绑定见 graph.py —— 它把这里的步骤接成带 checkpoint / 可中断的状态机；
本协调器本身不依赖 LangGraph，因此逻辑可独立测试。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from core.agent.coverage import compute_coverage, token_overlap_covered
from core.agent.schemas import InfoPoints, ResearchPlan
from core.domain import Evidence, Query, VerifiedAnswer
from core.llm import prompts
from core.ports import LLMClient
from core.retrieval.hybrid import HybridRetriever
from core.retrieval.router import classify_rule
from core.verify.citation import CitationVerifier


@dataclass
class TraceStep:
    """研究过程的一步，供前端 Trace 时间线展示。"""

    kind: str                       # plan / research / reflect / write / verify
    detail: str
    data: dict = field(default_factory=dict)


@dataclass
class ResearchResult:
    question: str
    plan: list[str]
    answer: VerifiedAnswer
    coverage: float
    rounds: int
    trace: list[TraceStep] = field(default_factory=list)


class ResearchCoordinator:
    def __init__(
        self,
        *,
        llm: LLMClient,
        retriever: HybridRetriever,
        verifier: CitationVerifier,
        strong_model: str | None = None,
        small_model: str | None = None,
        max_rounds: int = 3,
        coverage_target: float = 0.8,
        is_covered: Callable[[str, list[str]], bool] = token_overlap_covered,
    ) -> None:
        self._llm = llm
        self._retriever = retriever
        self._verifier = verifier
        self._strong = strong_model
        self._small = small_model
        self._max_rounds = max_rounds
        self._coverage_target = coverage_target
        self._is_covered = is_covered

    async def plan(self, question: str, *, model: str | None = None) -> list[str]:
        plan: ResearchPlan = await self._llm.structured(
            prompts.PLAN_PROMPT.format(question=question), ResearchPlan, model=model or self._strong
        )
        return [item.text for item in plan.subquestions]

    async def _research(self, queries: list[str]) -> list[Evidence]:
        """对一批（子）问题检索，合并去重证据。"""
        collected: dict[str, Evidence] = {}
        for q in queries:
            intent = classify_rule(q)
            hits = await self._retriever.retrieve(Query(text=q, intent=intent))
            for ev in hits:
                collected.setdefault(ev.id, ev)
        return list(collected.values())

    async def _reflect(self, subquestions: list[str], evidence: list[Evidence]) -> tuple[float, list[str]]:
        """算总覆盖度，返回 (coverage, 未覆盖信息点→补充查询)。"""
        ev_texts = [e.text for e in evidence]
        all_points: list[str] = []
        missing: list[str] = []
        for sq in subquestions:
            ip: InfoPoints = await self._llm.structured(
                prompts.INFO_POINTS_PROMPT.format(subquestion=sq), InfoPoints, model=self._small
            )
            all_points.extend(ip.points)
            rep = compute_coverage(ip.points, ev_texts, self._is_covered)
            missing.extend(rep.missing)
        overall = compute_coverage(all_points, ev_texts, self._is_covered)
        return overall.coverage, missing

    async def run(
        self, question: str, *, approved_plan: list[str] | None = None, model: str | None = None
    ) -> ResearchResult:
        """model：用户选择的强模型 id（覆盖 plan/write）；反思/改写仍用小模型。"""
        trace: list[TraceStep] = []

        subquestions = approved_plan or await self.plan(question, model=model)
        trace.append(TraceStep("plan", f"拆解为 {len(subquestions)} 个子问题", {"subquestions": subquestions}))

        evidence: dict[str, Evidence] = {}
        coverage = 0.0
        rounds = 0
        queries = list(subquestions)

        while rounds < self._max_rounds:
            rounds += 1
            new_ev = await self._research(queries)
            for ev in new_ev:
                evidence.setdefault(ev.id, ev)
            trace.append(TraceStep("research", f"第 {rounds} 轮召回 {len(new_ev)} 条证据",
                                   {"round": rounds, "n": len(new_ev)}))

            coverage, missing = await self._reflect(subquestions, list(evidence.values()))
            trace.append(TraceStep("reflect", f"覆盖度 {coverage:.0%}", {"coverage": coverage, "missing": missing}))

            if coverage >= self._coverage_target or not missing:
                break
            queries = missing  # 下一轮只补检索未覆盖的信息点

        evidence_list = list(evidence.values())
        evidence_map = {eid: ev for eid, ev in enumerate_evidence(evidence_list)}
        draft = await self._llm.complete(
            prompts.WRITE_PROMPT.format(
                question=question, evidence=prompts.format_evidence(evidence_map)
            ),
            model=model or self._strong,
        )
        trace.append(TraceStep("write", "生成综述草稿", {"chars": len(draft)}))

        verified = await self._verifier.verify(draft, evidence_map)
        trace.append(TraceStep("verify", f"可信度 {verified.trust:.0%}",
                               {"trust": verified.trust, "n_claims": len(verified.claims)}))

        return ResearchResult(
            question=question, plan=subquestions, answer=verified,
            coverage=coverage, rounds=rounds, trace=trace,
        )


def enumerate_evidence(evidence: list[Evidence]):
    """给证据分配稳定的短 id（e0, e1, ...）并重写 Evidence.id，供 [eid] 引用。"""
    for i, ev in enumerate(evidence):
        eid = f"e{i}"
        ev.id = eid
        yield eid, ev

"""深度研究 Agent 的 LangGraph 绑定（PRD 第 10 章）。

把 ResearchCoordinator 的各步骤接成一个带循环、带 checkpoint、可中断的状态机：

    START → planner → [interrupt_after] → researcher → reflector
              ↑__________________________________|  (覆盖不足且未超轮数)
            reflector → writer → verifier → END   (覆盖充分或超轮数)

- interrupt_after=["planner"]：生成计划后暂停，交给用户编辑，再从断点恢复（human-in-the-loop）
- checkpointer：State 持久化，支持中断后恢复（默认 MemorySaver，生产可换 Postgres）

节点逻辑全部复用 coordinator，因此业务逻辑仍可脱离 LangGraph 单测；本模块只负责编排。
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from core.agent.coordinator import (
    ResearchCoordinator,
    ResearchResult,
    TraceStep,
    enumerate_evidence,
)
from core.domain import Evidence, VerifiedAnswer
from core.llm import prompts


class GraphState(TypedDict, total=False):
    question: str
    model: str | None
    plan: list[str]
    evidence: Annotated[list[Evidence], operator.add]   # 各轮证据自动合并
    coverage: float
    rounds: int
    missing: list[str]
    draft: str
    answer: VerifiedAnswer
    trace: Annotated[list[TraceStep], operator.add]


def build_research_graph(coordinator: ResearchCoordinator, *, checkpointer=None):
    """用 coordinator 的方法作节点，编译成可中断、带 checkpoint 的图。"""
    c = coordinator

    async def planner(state: GraphState) -> dict:
        subs = await c.plan(state["question"], model=state.get("model"))
        return {
            "plan": subs,
            "rounds": 0,
            "trace": [TraceStep("plan", f"拆解为 {len(subs)} 个子问题", {"subquestions": subs})],
        }

    async def researcher(state: GraphState) -> dict:
        queries = state.get("missing") or state["plan"]   # 补检索只查未覆盖项
        new_ev = await c._research(queries)
        rnd = state.get("rounds", 0) + 1
        return {
            "evidence": new_ev,
            "rounds": rnd,
            "trace": [TraceStep("research", f"第 {rnd} 轮召回 {len(new_ev)} 条证据",
                                {"round": rnd, "n": len(new_ev)})],
        }

    async def reflector(state: GraphState) -> dict:
        coverage, missing = await c._reflect(state["plan"], state.get("evidence", []))
        return {
            "coverage": coverage,
            "missing": missing,
            "trace": [TraceStep("reflect", f"覆盖度 {coverage:.0%}",
                                {"coverage": coverage, "missing": missing})],
        }

    async def writer(state: GraphState) -> dict:
        ev_map = {eid: ev for eid, ev in enumerate_evidence(state.get("evidence", []))}
        draft = await c._llm.complete(
            prompts.WRITE_PROMPT.format(
                question=state["question"], evidence=prompts.format_evidence(ev_map)
            ),
            model=state.get("model") or c._strong,
        )
        state["_ev_map"] = ev_map  # 传给 verifier
        return {"draft": draft, "trace": [TraceStep("write", "生成综述草稿", {"chars": len(draft)})]}

    async def verifier(state: GraphState) -> dict:
        ev_map = state.get("_ev_map") or {eid: ev for eid, ev in enumerate_evidence(state.get("evidence", []))}
        answer = await c._verifier.verify(state["draft"], ev_map)
        return {"answer": answer,
                "trace": [TraceStep("verify", f"可信度 {answer.trust:.0%}",
                                    {"trust": answer.trust, "n_claims": len(answer.claims)})]}

    def route_after_reflect(state: GraphState) -> str:
        if state["coverage"] >= c._coverage_target or state["rounds"] >= c._max_rounds or not state.get("missing"):
            return "writer"
        return "researcher"

    g = StateGraph(GraphState)
    for name, fn in [("planner", planner), ("researcher", researcher),
                     ("reflector", reflector), ("writer", writer), ("verifier", verifier)]:
        g.add_node(name, fn)
    g.add_edge(START, "planner")
    g.add_edge("planner", "researcher")
    g.add_edge("researcher", "reflector")
    g.add_conditional_edges("reflector", route_after_reflect, {"writer": "writer", "researcher": "researcher"})
    g.add_edge("writer", "verifier")
    g.add_edge("verifier", END)

    return g.compile(checkpointer=checkpointer or MemorySaver(), interrupt_after=["planner"])


def state_to_result(state: GraphState) -> ResearchResult:
    """把终态转成与 coordinator.run 一致的结果对象。"""
    return ResearchResult(
        question=state["question"],
        plan=state.get("plan", []),
        answer=state.get("answer") or VerifiedAnswer(answer="", trust=0.0),
        coverage=state.get("coverage", 0.0),
        rounds=state.get("rounds", 0),
        trace=state.get("trace", []),
    )


class ResearchGraphRunner:
    """深度研究的 human-in-the-loop 驱动器。

    start()  → 运行到 planner 后中断，返回 (thread_id, plan)，供用户编辑
    resume() → 用（可编辑的）计划从断点继续，跑到结束返回 ResearchResult
    one_shot() → 不中断，一次跑完（等价 coordinator.run，但走图 + checkpoint）
    """

    def __init__(self, coordinator: ResearchCoordinator, *, checkpointer=None) -> None:
        self._app = build_research_graph(coordinator, checkpointer=checkpointer)

    @staticmethod
    def _cfg(thread_id: str) -> dict:
        return {"configurable": {"thread_id": thread_id}}

    async def start(self, question: str, thread_id: str, *, model: str | None = None) -> list[str]:
        """跑到 planner 后中断，返回生成的计划。"""
        await self._app.ainvoke({"question": question, "model": model}, self._cfg(thread_id))
        snap = await self._app.aget_state(self._cfg(thread_id))
        return snap.values.get("plan", [])

    async def resume(self, thread_id: str, *, approved_plan: list[str] | None = None) -> ResearchResult:
        """用户确认/编辑计划后从断点继续，跑到结束。"""
        cfg = self._cfg(thread_id)
        if approved_plan is not None:
            await self._app.aupdate_state(cfg, {"plan": approved_plan})
        await self._app.ainvoke(None, cfg)   # 从断点继续到 END
        snap = await self._app.aget_state(cfg)
        return state_to_result(snap.values)

    async def one_shot(self, question: str, thread_id: str, *, model: str | None = None) -> ResearchResult:
        await self.start(question, thread_id, model=model)
        return await self.resume(thread_id)

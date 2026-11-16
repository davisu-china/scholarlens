"""深度研究 Agent：LangGraph 带循环状态机。

Planner → (Human Review) → Researcher → Reflector → Writer → Verifier
Reflector 用「证据覆盖度」决定是否继续补检索（≤3 轮），而非固定轮数。

参见 PRD 第 10 章「深度研究 Agent」。
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from core.retrieval.hybrid import Evidence


class SubQuestion(TypedDict):
    text: str
    status: str                 # pending / answered
    evidence: list[Evidence]


class ResearchState(TypedDict):
    question: str
    plan: list[SubQuestion]
    evidence: Annotated[list[Evidence], operator.add]  # 并行分支证据自动合并
    coverage: float
    rounds: int
    draft: str


# --- 节点实现占位 ---

async def plan_node(state: ResearchState) -> dict:
    """强模型把问题拆成子问题树。"""
    raise NotImplementedError("TODO: Planner，强模型拆解子问题")


async def research_node(state: ResearchState) -> dict:
    """用 Send API 对每个子问题 fan-out，并行调用 hybrid_search 等工具。"""
    raise NotImplementedError("TODO: Researcher，并行执行子问题")


async def reflect_node(state: ResearchState) -> dict:
    """小模型评估覆盖度 = 已覆盖信息点 / 总信息点；未覆盖项转为补充查询。"""
    raise NotImplementedError("TODO: Reflector，覆盖度评估")


async def write_node(state: ResearchState) -> dict:
    """强模型分章撰写带引用的综述。"""
    raise NotImplementedError("TODO: Writer，分章撰写")


async def verify_node(state: ResearchState) -> dict:
    """NLI 逐句校验，未通过的句子回到 write 重写。"""
    raise NotImplementedError("TODO: Verifier，接 core.verify.citation")


def build_graph():  # noqa: ANN201 — 返回 compiled LangGraph app
    """构建并编译研究图。

    g.add_conditional_edges("reflector",
        lambda s: "writer" if s["coverage"] >= 0.8 or s["rounds"] >= 3 else "researcher")
    app = g.compile(checkpointer=PostgresSaver(pool), interrupt_after=["planner"])
    """
    raise NotImplementedError("TODO: 组装 StateGraph，PostgresSaver checkpoint，planner 后中断")

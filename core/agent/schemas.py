"""Agent 结构化输出的 schema。用于 LLM 的 structured() 约束 JSON 输出。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PlanItem(BaseModel):
    """研究计划里的一个子问题。"""

    text: str
    rationale: str = ""        # 为什么需要这个子问题


class ResearchPlan(BaseModel):
    """Planner 产出的子问题树（v1 为平铺列表）。"""

    subquestions: list[PlanItem] = Field(default_factory=list)


class InfoPoints(BaseModel):
    """Reflector 为一个子问题列出的「回答它需要哪些信息点」。"""

    points: list[str] = Field(default_factory=list)

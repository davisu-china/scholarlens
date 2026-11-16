"""POST /research — 深度研究模式，SSE 推送 Plan / Trace / Answer。参见 PRD F3 + 第 10 章。"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

import uuid

from apps.api.deps import get_billing, get_container, get_graph_runner, get_user
from core.billing.plans import ACTION_RESEARCH
from core.billing.service import BillingService, ModelNotAllowed, QuotaExceeded
from core.container import Container
from core.llm import usage
from core.obs import langfuse as obs

router = APIRouter()


class ResearchRequest(BaseModel):
    question: str
    collection: str | None = None
    model: str | None = None
    approved_plan: list[str] | None = None


@router.post("")
async def research(
    req: ResearchRequest,
    c: Container = Depends(get_container),
    user: str = Depends(get_user),
    billing: BillingService = Depends(get_billing),
) -> EventSourceResponse:
    try:
        await billing.check_model(user, req.model)
        await billing.check_quota(user, ACTION_RESEARCH)
    except ModelNotAllowed as e:
        raise HTTPException(403, str(e)) from e
    except QuotaExceeded as e:
        raise HTTPException(429, str(e)) from e

    async def gen():
        acc = usage.start()
        obs.set_context(user_id=user, feature="research")
        with obs.span("research-request", req.question):
            result = await c.coordinator.run(req.question, approved_plan=req.approved_plan, model=req.model)
        for step in result.trace:
            yield {"event": step.kind, "data": json.dumps({"detail": step.detail, **step.data}, ensure_ascii=False)}
        yield {
            "event": "answer",
            "data": json.dumps(
                {
                    "answer": result.answer.answer,
                    "trust": result.answer.trust,
                    "claims": [cl.model_dump() for cl in result.answer.claims],
                    "coverage": result.coverage,
                },
                ensure_ascii=False,
            ),
        }
        await billing.record(user, ACTION_RESEARCH, model_id=req.model, cost_cny=acc.total_cost_cny)

    return EventSourceResponse(gen())


class PlanRequest(BaseModel):
    question: str
    model: str | None = None


@router.post("/plan")
async def make_plan(
    req: PlanRequest,
    user: str = Depends(get_user),
    billing: BillingService = Depends(get_billing),
    runner=Depends(get_graph_runner),
) -> dict:
    """深度研究第一步：生成研究计划并在此暂停，交给用户编辑（human-in-the-loop）。"""
    try:
        await billing.check_model(user, req.model)
        await billing.check_quota(user, ACTION_RESEARCH)
    except ModelNotAllowed as e:
        raise HTTPException(403, str(e)) from e
    except QuotaExceeded as e:
        raise HTTPException(429, str(e)) from e
    thread_id = uuid.uuid4().hex
    plan = await runner.start(req.question, thread_id, model=req.model)
    return {"thread_id": thread_id, "plan": plan}


class ResumeRequest(BaseModel):
    thread_id: str
    approved_plan: list[str] | None = None


@router.post("/resume")
async def resume(
    req: ResumeRequest,
    user: str = Depends(get_user),
    billing: BillingService = Depends(get_billing),
    runner=Depends(get_graph_runner),
) -> EventSourceResponse:
    """用户确认/编辑计划后从断点继续，SSE 推送过程与最终综述。"""
    async def gen():
        acc = usage.start()
        obs.set_context(user_id=user, feature="research")
        with obs.span("research-resume", req.thread_id):
            result = await runner.resume(req.thread_id, approved_plan=req.approved_plan)
        for step in result.trace:
            yield {"event": step.kind, "data": json.dumps({"detail": step.detail, **step.data}, ensure_ascii=False)}
        yield {"event": "answer", "data": json.dumps({
            "answer": result.answer.answer, "trust": result.answer.trust,
            "claims": [cl.model_dump() for cl in result.answer.claims], "coverage": result.coverage,
        }, ensure_ascii=False)}
        await billing.record(user, ACTION_RESEARCH, model_id=None, cost_cny=acc.total_cost_cny)

    return EventSourceResponse(gen())

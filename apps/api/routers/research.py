"""POST /research — 深度研究模式，SSE 推送 Plan / Trace / Answer。

human-in-the-loop：planner 产出计划后中断，用户编辑确认再继续。参见 PRD F3 + 第 10 章。
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

router = APIRouter()


class ResearchRequest(BaseModel):
    question: str
    collection: str | None = None
    thread_id: str | None = None   # 复用已中断的会话（编辑计划后继续）
    approved_plan: list[dict] | None = None


async def _stream_research(req: ResearchRequest) -> AsyncIterator[dict]:
    # TODO: 调用 core.agent.graph，把每个节点事件映射成 SSE：
    #   plan / hybrid_search / table_query / citation_expand / reflect / verify / answer
    yield {"event": "plan", "data": "[]"}
    yield {"event": "done", "data": "{}"}
    raise NotImplementedError


@router.post("")
async def research(req: ResearchRequest) -> EventSourceResponse:
    return EventSourceResponse(_stream_research(req))

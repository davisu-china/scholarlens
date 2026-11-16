"""POST /query — 快速问答，SSE 流式输出。

答案每句以 [eid] 结尾，前端据此渲染引用角标。参见 PRD F2。
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

router = APIRouter()


class QueryRequest(BaseModel):
    question: str
    collection: str | None = None
    filters: dict = {}


async def _stream_answer(req: QueryRequest) -> AsyncIterator[dict]:
    # TODO: Query 路由 → hybrid_search → 受约束生成（流式）→ verify_claims
    yield {"event": "token", "data": "（TODO：接入检索与生成流水线）"}
    yield {"event": "done", "data": "{}"}
    raise NotImplementedError


@router.post("")
async def query(req: QueryRequest) -> EventSourceResponse:
    return EventSourceResponse(_stream_answer(req))

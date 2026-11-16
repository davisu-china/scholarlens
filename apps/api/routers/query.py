"""POST /query — 快速问答，SSE 流式输出。参见 PRD F2。"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from apps.api.deps import get_container
from core.container import Container

router = APIRouter()


class QueryRequest(BaseModel):
    question: str
    collection: str | None = None
    filters: dict = {}


@router.post("")
async def query(req: QueryRequest, c: Container = Depends(get_container)) -> EventSourceResponse:
    filters = dict(req.filters)
    if req.collection:
        filters["collection"] = req.collection

    async def gen():
        async for ev in c.qa.stream(req.question, filters=filters):
            data = ev["data"] if isinstance(ev["data"], str) else json.dumps(ev["data"], ensure_ascii=False)
            yield {"event": ev["event"], "data": data}

    return EventSourceResponse(gen())

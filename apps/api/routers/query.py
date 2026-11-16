"""POST /query — 快速问答，SSE 流式输出。参见 PRD F2。"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from apps.api.deps import get_billing, get_container, get_user
from core.billing.plans import ACTION_QUERY
from core.billing.service import BillingService, ModelNotAllowed, QuotaExceeded
from core.container import Container

router = APIRouter()


class QueryRequest(BaseModel):
    question: str
    collection: str | None = None
    model: str | None = None


@router.post("")
async def query(
    req: QueryRequest,
    c: Container = Depends(get_container),
    user: str = Depends(get_user),
    billing: BillingService = Depends(get_billing),
) -> EventSourceResponse:
    try:
        await billing.check_model(user, req.model)
        await billing.check_quota(user, ACTION_QUERY)
    except ModelNotAllowed as e:
        raise HTTPException(403, str(e)) from e
    except QuotaExceeded as e:
        raise HTTPException(429, str(e)) from e

    filters = dict({} if req.collection is None else {"collection": req.collection})

    async def gen():
        async for ev in c.qa.stream(req.question, filters=filters, model=req.model):
            data = ev["data"] if isinstance(ev["data"], str) else json.dumps(ev["data"], ensure_ascii=False)
            yield {"event": ev["event"], "data": data}
        await billing.record(user, ACTION_QUERY, model_id=req.model)

    return EventSourceResponse(gen())

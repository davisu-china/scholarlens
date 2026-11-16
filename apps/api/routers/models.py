"""GET /models — 可选 LLM 清单（含当前套餐是否解锁），供前端模型选择器。"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from apps.api.deps import get_billing, get_user
from core.billing.service import BillingService
from core.llm.catalog import build_catalog, default_strong_id

router = APIRouter()


@router.get("")
async def list_models(user: str = Depends(get_user), billing: BillingService = Depends(get_billing)) -> dict:
    catalog = build_catalog()
    plan = await billing.plan_for(user)
    default = default_strong_id(catalog) if catalog else None
    models = []
    for s in catalog.values():
        locked = not plan.allows_model(s.id)
        models.append({"id": s.id, "label": s.label, "description": s.description,
                       "tier": s.tier, "locked": locked})
    # 默认模型若被锁，退回到第一个可用的
    allowed = [m["id"] for m in models if not m["locked"]]
    if default not in allowed and allowed:
        default = allowed[0]
    return {"default": default, "plan": plan.id, "models": models}

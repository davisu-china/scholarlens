"""GET /billing/overview — 当前套餐、配额剩余、用量汇总。
POST /billing/plan — 切换套餐（雏形/演示用；生产由支付回调驱动）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from apps.api.deps import get_billing, get_user
from core.billing.plans import PLANS
from core.billing.service import BillingService

router = APIRouter()


@router.get("/overview")
async def overview(user: str = Depends(get_user), billing: BillingService = Depends(get_billing)) -> dict:
    return await billing.overview(user)


@router.get("/plans")
async def plans() -> list[dict]:
    return [
        {"id": p.id, "name": p.name, "price_cny_per_month": p.price_cny_per_month,
         "allowed_models": sorted(p.allowed_models),
         "quotas": {a: {"per_day": q.per_day, "per_month": q.per_month} for a, q in p.quotas.items()}}
        for p in PLANS.values()
    ]


class SetPlan(BaseModel):
    plan_id: str


@router.post("/plan")
async def set_plan(req: SetPlan, user: str = Depends(get_user),
                   billing: BillingService = Depends(get_billing)) -> dict:
    if req.plan_id not in PLANS:
        raise HTTPException(400, f"未知套餐：{req.plan_id}")
    await billing._subs.set_plan_id(user, req.plan_id)  # noqa: SLF001 — 雏形直接设置
    return await billing.overview(user)

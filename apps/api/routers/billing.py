"""计费与支付路由。

- GET  /billing/overview  当前套餐 + 配额剩余 + 用量汇总
- GET  /billing/plans     套餐清单
- POST /billing/checkout  下单（返回订单号与应付金额）
- POST /billing/webhook   支付网关回调（HMAC 验签后履约升级）
- POST /billing/simulate-payment/{order_id}  雏形：模拟支付成功（生产删除，由真实网关回调）
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from apps.api.deps import get_billing, get_payment, get_user
from core.billing.plans import PLANS
from core.billing.payment import PaymentError, PaymentService, sign_payload
from core.billing.service import BillingService
from core.config import settings

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


class Checkout(BaseModel):
    plan_id: str


@router.post("/checkout")
async def checkout(req: Checkout, user: str = Depends(get_user),
                   pay: PaymentService = Depends(get_payment)) -> dict:
    try:
        order = await pay.checkout(user, req.plan_id)
    except PaymentError as e:
        raise HTTPException(400, str(e)) from e
    # 真实网关这里返回支付二维码/跳转链接；雏形给出订单信息
    return {"order_id": order.id, "amount_cny": order.amount_cny, "plan_id": order.plan_id,
            "pay_url": f"/pay/mock/{order.id}"}


class Webhook(BaseModel):
    order_id: str
    status: str
    signature: str


@router.post("/webhook")
async def webhook(req: Webhook, pay: PaymentService = Depends(get_payment)) -> dict:
    """支付网关回调（无需用户鉴权，靠 HMAC 签名验真）。"""
    try:
        order = await pay.handle_webhook(req.order_id, req.status, req.signature)
    except PaymentError as e:
        raise HTTPException(400, str(e)) from e
    return {"order_id": order.id, "status": order.status, "plan_id": order.plan_id}


@router.post("/simulate-payment/{order_id}")
async def simulate_payment(order_id: str, pay: PaymentService = Depends(get_payment)) -> dict:
    """雏形专用：服务端自行签名并履约，模拟网关回调成功。生产环境应删除。"""
    sig = sign_payload(order_id, "paid", settings.billing_webhook_secret)
    try:
        order = await pay.handle_webhook(order_id, "paid", sig)
    except PaymentError as e:
        raise HTTPException(400, str(e)) from e
    return {"order_id": order.id, "status": order.status, "plan_id": order.plan_id}

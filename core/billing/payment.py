"""支付服务：下单、验签回调、履约升级套餐。

真实支付网关（微信/支付宝/Stripe）通过 webhook 回调，用 HMAC 签名校验来源，
验签通过后把用户升级到已购套餐。这里给出可直接替换的骨架。
"""

from __future__ import annotations

import hashlib
import hmac

from core.billing.orders import Order, OrderStore
from core.billing.plans import PLANS
from core.billing.ports import SubscriptionStore


class PaymentError(Exception):
    pass


def sign_payload(order_id: str, status: str, secret: str) -> str:
    return hmac.new(secret.encode(), f"{order_id}:{status}".encode(), hashlib.sha256).hexdigest()


class PaymentService:
    def __init__(self, orders: OrderStore, subscriptions: SubscriptionStore, *, webhook_secret: str) -> None:
        self._orders = orders
        self._subs = subscriptions
        self._secret = webhook_secret

    async def checkout(self, user_id: str, plan_id: str) -> Order:
        plan = PLANS.get(plan_id)
        if plan is None:
            raise PaymentError(f"未知套餐：{plan_id}")
        if plan.price_cny_per_month <= 0:
            raise PaymentError(f"套餐「{plan.name}」无需支付")
        return await self._orders.create(user_id, plan_id, plan.price_cny_per_month)

    async def handle_webhook(self, order_id: str, status: str, signature: str) -> Order:
        expected = sign_payload(order_id, status, self._secret)
        if not hmac.compare_digest(expected, signature):
            raise PaymentError("签名校验失败")
        order = await self._orders.get(order_id)
        if order is None:
            raise PaymentError(f"订单不存在：{order_id}")
        if status == "paid":
            await self._orders.mark_paid(order_id)
            await self._subs.set_plan_id(order.user_id, order.plan_id)  # 履约：升级套餐
        return order

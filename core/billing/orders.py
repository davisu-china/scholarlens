"""支付订单（雏形内存版；生产换 Postgres + 真实支付网关）。"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

OrderStatus = Literal["pending", "paid", "cancelled"]


@dataclass
class Order:
    id: str
    user_id: str
    plan_id: str
    amount_cny: float
    status: OrderStatus = "pending"


@runtime_checkable
class OrderStore(Protocol):
    async def create(self, user_id: str, plan_id: str, amount_cny: float) -> Order: ...
    async def get(self, order_id: str) -> Order | None: ...
    async def mark_paid(self, order_id: str) -> Order | None: ...


class InMemoryOrderStore:
    def __init__(self) -> None:
        self._orders: dict[str, Order] = {}

    async def create(self, user_id: str, plan_id: str, amount_cny: float) -> Order:
        oid = uuid.uuid4().hex[:16]
        order = Order(id=oid, user_id=user_id, plan_id=plan_id, amount_cny=amount_cny)
        self._orders[oid] = order
        return order

    async def get(self, order_id: str) -> Order | None:
        return self._orders.get(order_id)

    async def mark_paid(self, order_id: str) -> Order | None:
        order = self._orders.get(order_id)
        if order and order.status == "pending":
            order.status = "paid"
        return order

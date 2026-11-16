"""Postgres（SQLAlchemy async）版的用户/订阅/用量/订单存储。

实现与内存版相同的接口；SQL 可移植（Postgres 生产 / SQLite 测试通跑）。
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncEngine

from core.auth.users import BadCredentials, DuplicateUser, _hash
from core.billing.orders import Order
from core.db import schema


class SqlUserStore:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def register(self, username: str, password: str) -> str:
        salt = os.urandom(16)
        uid = uuid.uuid4().hex[:12]
        async with self._engine.begin() as conn:
            exists = await conn.scalar(select(schema.users.c.id).where(schema.users.c.username == username))
            if exists:
                raise DuplicateUser(f"用户名已存在：{username}")
            await conn.execute(insert(schema.users).values(
                id=uid, username=username, salt=salt, pw_hash=_hash(password, salt)))
        return uid

    async def authenticate(self, username: str, password: str) -> str:
        async with self._engine.connect() as conn:
            row = (await conn.execute(
                select(schema.users.c.id, schema.users.c.salt, schema.users.c.pw_hash)
                .where(schema.users.c.username == username))).first()
        if row is None:
            raise BadCredentials("用户名或密码错误")
        import hmac
        if not hmac.compare_digest(bytes(row.pw_hash), _hash(password, bytes(row.salt))):
            raise BadCredentials("用户名或密码错误")
        return row.id


class SqlSubscriptionStore:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def get_plan_id(self, user_id: str) -> str | None:
        async with self._engine.connect() as conn:
            return await conn.scalar(
                select(schema.subscriptions.c.plan_id).where(schema.subscriptions.c.user_id == user_id))

    async def set_plan_id(self, user_id: str, plan_id: str) -> None:
        async with self._engine.begin() as conn:
            exists = await conn.scalar(
                select(schema.subscriptions.c.user_id).where(schema.subscriptions.c.user_id == user_id))
            if exists:
                await conn.execute(update(schema.subscriptions)
                    .where(schema.subscriptions.c.user_id == user_id).values(plan_id=plan_id))
            else:
                await conn.execute(insert(schema.subscriptions).values(user_id=user_id, plan_id=plan_id))


class SqlUsageStore:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def record(self, user_id, action, *, units=1, model_id=None, cost_cny=0.0, at=None):
        from datetime import timezone
        async with self._engine.begin() as conn:
            await conn.execute(insert(schema.usage_events).values(
                user_id=user_id, action=action, units=units, model_id=model_id,
                cost_cny=cost_cny, at=at or datetime.now(timezone.utc)))

    async def count_since(self, user_id: str, action: str, since: datetime) -> int:
        async with self._engine.connect() as conn:
            total = await conn.scalar(
                select(func.coalesce(func.sum(schema.usage_events.c.units), 0)).where(
                    (schema.usage_events.c.user_id == user_id)
                    & (schema.usage_events.c.action == action)
                    & (schema.usage_events.c.at >= since)))
        return int(total or 0)

    async def summary(self, user_id: str) -> dict:
        from collections import defaultdict
        by_action: dict[str, int] = defaultdict(int)
        by_model: dict[str, int] = defaultdict(int)
        cost = 0.0
        async with self._engine.connect() as conn:
            rows = (await conn.execute(select(
                schema.usage_events.c.action, schema.usage_events.c.units,
                schema.usage_events.c.model_id, schema.usage_events.c.cost_cny)
                .where(schema.usage_events.c.user_id == user_id))).all()
        for r in rows:
            by_action[r.action] += r.units
            if r.model_id:
                by_model[r.model_id] += r.units
            cost += r.cost_cny or 0.0
        return {"by_action": dict(by_action), "by_model": dict(by_model), "cost_cny": round(cost, 4)}


class SqlOrderStore:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def create(self, user_id: str, plan_id: str, amount_cny: float) -> Order:
        oid = uuid.uuid4().hex[:16]
        async with self._engine.begin() as conn:
            await conn.execute(insert(schema.orders).values(
                id=oid, user_id=user_id, plan_id=plan_id, amount_cny=amount_cny, status="pending"))
        return Order(id=oid, user_id=user_id, plan_id=plan_id, amount_cny=amount_cny, status="pending")

    async def get(self, order_id: str) -> Order | None:
        async with self._engine.connect() as conn:
            row = (await conn.execute(select(schema.orders).where(schema.orders.c.id == order_id))).first()
        return Order(id=row.id, user_id=row.user_id, plan_id=row.plan_id,
                     amount_cny=row.amount_cny, status=row.status) if row else None

    async def mark_paid(self, order_id: str) -> Order | None:
        async with self._engine.begin() as conn:
            await conn.execute(update(schema.orders)
                .where((schema.orders.c.id == order_id) & (schema.orders.c.status == "pending"))
                .values(status="paid"))
        return await self.get(order_id)

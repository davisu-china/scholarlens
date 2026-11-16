"""计费服务：套餐权限 + 配额校验 + 用量记录。

用法（API 层）：
    await billing.check_model(user, model_id)      # 模型是否在套餐内
    await billing.check_quota(user, ACTION_QUERY)   # 是否还有额度
    ... 执行业务 ...
    await billing.record(user, ACTION_QUERY, model_id=..., cost_cny=...)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from core.billing.plans import Plan, Quota, get_plan
from core.billing.ports import SubscriptionStore, UsageStore


class BillingError(Exception):
    """基类。"""


class ModelNotAllowed(BillingError):
    def __init__(self, model_id: str, plan: Plan) -> None:
        super().__init__(f"当前套餐「{plan.name}」不包含模型 {model_id}")
        self.model_id = model_id
        self.plan = plan


class QuotaExceeded(BillingError):
    def __init__(self, action: str, window: str, limit: int) -> None:
        super().__init__(f"已达{('当日' if window == 'day' else '当月')}配额上限（{action}: {limit}）")
        self.action = action
        self.window = window
        self.limit = limit


def _window_start(window: str, now: datetime) -> datetime:
    if window == "day":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


@dataclass
class QuotaStatus:
    action: str
    window: str
    limit: int | None
    used: int

    @property
    def remaining(self) -> int | None:
        return None if self.limit is None else max(0, self.limit - self.used)


class BillingService:
    def __init__(self, subscriptions: SubscriptionStore, usage: UsageStore) -> None:
        self._subs = subscriptions
        self._usage = usage

    async def plan_for(self, user_id: str) -> Plan:
        return get_plan(await self._subs.get_plan_id(user_id))

    async def check_model(self, user_id: str, model_id: str | None) -> None:
        if model_id is None:
            return
        plan = await self.plan_for(user_id)
        if not plan.allows_model(model_id):
            raise ModelNotAllowed(model_id, plan)

    async def _status(self, user_id: str, plan: Plan, action: str) -> list[QuotaStatus]:
        now = datetime.now(timezone.utc)
        quota: Quota = plan.quota_for(action)
        out: list[QuotaStatus] = []
        for window in ("day", "month"):
            limit = quota.limit(window)
            if limit is None:
                continue
            used = await self._usage.count_since(user_id, action, _window_start(window, now))
            out.append(QuotaStatus(action, window, limit, used))
        return out

    async def check_quota(self, user_id: str, action: str, *, units: int = 1) -> None:
        plan = await self.plan_for(user_id)
        for st in await self._status(user_id, plan, action):
            if st.limit is not None and st.used + units > st.limit:
                raise QuotaExceeded(action, st.window, st.limit)

    async def record(
        self, user_id: str, action: str, *, units: int = 1,
        model_id: str | None = None, cost_cny: float = 0.0,
    ) -> None:
        await self._usage.record(
            user_id, action, units=units, model_id=model_id, cost_cny=cost_cny
        )

    async def overview(self, user_id: str) -> dict:
        """账单/用量看板数据：套餐、各动作剩余额度、用量汇总。"""
        plan = await self.plan_for(user_id)
        quotas: list[dict] = []
        for action in plan.quotas:
            for st in await self._status(user_id, plan, action):
                quotas.append({
                    "action": st.action, "window": st.window,
                    "limit": st.limit, "used": st.used, "remaining": st.remaining,
                })
        return {
            "plan": {"id": plan.id, "name": plan.name, "price_cny_per_month": plan.price_cny_per_month},
            "allowed_models": sorted(plan.allowed_models),
            "quotas": quotas,
            "usage": await self._usage.summary(user_id),
        }

"""内存版订阅与用量存储（雏形/测试用）。

生产替换为 Postgres：subscriptions(user_id, plan_id)、usage_events(user_id, action,
units, model_id, cost_cny, at) + 按时间窗聚合的查询即可，接口不变。
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class _Event:
    action: str
    units: int
    model_id: str | None
    cost_cny: float
    at: datetime


class InMemorySubscriptionStore:
    def __init__(self, initial: dict[str, str] | None = None) -> None:
        self._plans: dict[str, str] = dict(initial or {})

    async def get_plan_id(self, user_id: str) -> str | None:
        return self._plans.get(user_id)

    async def set_plan_id(self, user_id: str, plan_id: str) -> None:
        self._plans[user_id] = plan_id


class InMemoryUsageStore:
    def __init__(self) -> None:
        self._events: dict[str, list[_Event]] = defaultdict(list)

    async def record(
        self, user_id, action, *, units=1, model_id=None, cost_cny=0.0, at=None
    ) -> None:
        self._events[user_id].append(_Event(action, units, model_id, cost_cny, at or _now()))

    async def count_since(self, user_id: str, action: str, since: datetime) -> int:
        return sum(
            e.units for e in self._events[user_id] if e.action == action and e.at >= since
        )

    async def summary(self, user_id: str) -> dict:
        by_action: dict[str, int] = defaultdict(int)
        by_model: dict[str, int] = defaultdict(int)
        cost = 0.0
        for e in self._events[user_id]:
            by_action[e.action] += e.units
            if e.model_id:
                by_model[e.model_id] += e.units
            cost += e.cost_cny
        return {"by_action": dict(by_action), "by_model": dict(by_model), "cost_cny": round(cost, 4)}

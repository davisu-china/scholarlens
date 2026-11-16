"""计费相关的抽象接口。内存实现见 store.py，可换 Postgres。"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class SubscriptionStore(Protocol):
    """用户 → 套餐 id 的映射。"""

    async def get_plan_id(self, user_id: str) -> str | None: ...

    async def set_plan_id(self, user_id: str, plan_id: str) -> None: ...


@runtime_checkable
class UsageStore(Protocol):
    """用量记录与统计。"""

    async def record(
        self, user_id: str, action: str, *, units: int = 1, model_id: str | None = None,
        cost_cny: float = 0.0, at: datetime | None = None,
    ) -> None: ...

    async def count_since(self, user_id: str, action: str, since: datetime) -> int:
        """统计 since 之后某动作的累计 units。"""
        ...

    async def summary(self, user_id: str) -> dict:
        """返回用户的用量汇总（按动作/模型），供账单与看板。"""
        ...

"""套餐定义（商业化雏形）。

每个套餐规定：可用的模型 id 集合（"*" 表示全部）、各类动作的配额（按天/按月）。
配额值为 None 表示不限。真实运营时这张表可改为从数据库/配置中心读取。
"""

from __future__ import annotations

from dataclasses import dataclass, field

# 计量的动作类型
ACTION_QUERY = "query"           # 一次快速问答
ACTION_RESEARCH = "research"     # 一次深度研究
ACTION_INGEST_PAGES = "ingest_pages"  # 解析入库的页数

ALL_MODELS = "*"


@dataclass(frozen=True)
class Quota:
    per_day: int | None = None
    per_month: int | None = None

    def limit(self, window: str) -> int | None:
        return self.per_day if window == "day" else self.per_month


@dataclass(frozen=True)
class Plan:
    id: str
    name: str
    allowed_models: frozenset[str]            # 具体模型 id，或 {"*"}
    quotas: dict[str, Quota] = field(default_factory=dict)  # action -> Quota
    price_cny_per_month: float = 0.0

    def allows_model(self, model_id: str) -> bool:
        return ALL_MODELS in self.allowed_models or model_id in self.allowed_models

    def quota_for(self, action: str) -> Quota:
        return self.quotas.get(action, Quota())


PLANS: dict[str, Plan] = {
    "free": Plan(
        id="free",
        name="免费版",
        allowed_models=frozenset({"deepseek", "haiku"}),      # 只给便宜模型
        quotas={
            ACTION_QUERY: Quota(per_day=20),
            ACTION_RESEARCH: Quota(per_day=2),
            ACTION_INGEST_PAGES: Quota(per_month=50),
        },
        price_cny_per_month=0.0,
    ),
    "pro": Plan(
        id="pro",
        name="专业版",
        allowed_models=frozenset({ALL_MODELS}),                # 解锁全部，含 Opus
        quotas={
            ACTION_QUERY: Quota(per_day=500),
            ACTION_RESEARCH: Quota(per_day=50),
            ACTION_INGEST_PAGES: Quota(per_month=2000),
        },
        price_cny_per_month=99.0,
    ),
    "enterprise": Plan(
        id="enterprise",
        name="企业版",
        allowed_models=frozenset({ALL_MODELS}),
        quotas={},                                             # 不限量
        price_cny_per_month=0.0,                               # 面议
    ),
}

DEFAULT_PLAN_ID = "free"


def get_plan(plan_id: str | None) -> Plan:
    return PLANS.get(plan_id or DEFAULT_PLAN_ID, PLANS[DEFAULT_PLAN_ID])

"""FastAPI 依赖：提供应用容器。

默认用 fakes（开箱即跑、便于演示）。设置 SL_USE_REAL_ADAPTERS=1 时接真实后端
（见 core/adapters/real.py 的 build_real_container）。
"""

from __future__ import annotations

import os
from functools import lru_cache

from core.config import settings
from core.container import Container, build_container


@lru_cache
def get_container() -> Container:
    if os.getenv("SL_USE_REAL_ADAPTERS") == "1":
        from core.adapters.real import build_real_container

        return build_real_container()
    # fakes 模式下，只要配置了 MinerU token，PDF 解析就走真实云 API
    parser = None
    if settings.mineru_api_token:
        from core.adapters.mineru_cloud import MinerUCloudParser

        parser = MinerUCloudParser()
    return build_container(parser=parser)


# --- 计费（雏形）---
from fastapi import Header  # noqa: E402

from core.billing.service import BillingService  # noqa: E402
from core.billing.store import InMemorySubscriptionStore, InMemoryUsageStore  # noqa: E402

_SUBS = InMemorySubscriptionStore()
_USAGE = InMemoryUsageStore()


@lru_cache
def get_billing() -> BillingService:
    """计费服务单例（内存存储；生产换 Postgres 实现同一组 port）。"""
    return BillingService(_SUBS, _USAGE)


async def get_user(x_user_id: str = Header(default="demo")) -> str:
    """从请求头解析用户。雏形用 X-User-Id；生产换 JWT 的 sub。"""
    return x_user_id

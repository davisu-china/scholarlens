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
from fastapi import Header, HTTPException  # noqa: E402

from core.auth.jwt import AuthError, decode_token  # noqa: E402
from core.auth.users import InMemoryUserStore  # noqa: E402
from core.billing.service import BillingService  # noqa: E402
from core.billing.store import InMemorySubscriptionStore, InMemoryUsageStore  # noqa: E402
from core.billing.orders import InMemoryOrderStore  # noqa: E402
from core.billing.payment import PaymentService  # noqa: E402
from core.config import settings  # noqa: E402

def _build_stores():
    """按 settings.use_db 选择存储后端：Postgres 或内存。"""
    if settings.use_db:
        from core.db.engine import get_engine
        from core.db.stores import SqlOrderStore, SqlSubscriptionStore, SqlUsageStore, SqlUserStore

        eng = get_engine()
        return (SqlSubscriptionStore(eng), SqlUsageStore(eng), SqlUserStore(eng), SqlOrderStore(eng))
    return (InMemorySubscriptionStore(), InMemoryUsageStore(), InMemoryUserStore(), InMemoryOrderStore())


_SUBS, _USAGE, _USERS, _ORDERS = _build_stores()


@lru_cache
def get_billing() -> BillingService:
    """计费服务单例（内存存储；生产换 Postgres 实现同一组 port）。"""
    return BillingService(_SUBS, _USAGE)


def get_users() -> InMemoryUserStore:
    return _USERS


@lru_cache
def get_payment() -> PaymentService:
    return PaymentService(_ORDERS, _SUBS, webhook_secret=settings.billing_webhook_secret)


async def get_user(authorization: str = Header(default="")) -> str:
    """从 Authorization: Bearer <jwt> 解析用户 id（JWT 的 sub）。"""
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "缺少 Bearer token")
    try:
        return decode_token(authorization.split(" ", 1)[1].strip())
    except AuthError as e:
        raise HTTPException(401, str(e)) from e

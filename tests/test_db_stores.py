"""Postgres 存储的 SQL 逻辑：用 SQLite(aiosqlite) 真实跑，验证可移植查询。"""
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio

from core.auth.users import BadCredentials, DuplicateUser
from core.db.engine import create_all, make_engine
from core.db.stores import SqlOrderStore, SqlSubscriptionStore, SqlUsageStore, SqlUserStore


@pytest_asyncio.fixture
async def engine(tmp_path):
    eng = make_engine(f"sqlite+aiosqlite:///{tmp_path}/t.db")
    await create_all(eng)
    yield eng
    await eng.dispose()


async def test_user_register_login(engine):
    us = SqlUserStore(engine)
    uid = await us.register("alice", "secret")
    assert await us.authenticate("alice", "secret") == uid
    with pytest.raises(BadCredentials):
        await us.authenticate("alice", "wrong")
    with pytest.raises(DuplicateUser):
        await us.register("alice", "x")


async def test_subscription_upsert(engine):
    subs = SqlSubscriptionStore(engine)
    assert await subs.get_plan_id("u1") is None
    await subs.set_plan_id("u1", "free")
    assert await subs.get_plan_id("u1") == "free"
    await subs.set_plan_id("u1", "pro")           # 覆盖
    assert await subs.get_plan_id("u1") == "pro"


async def test_usage_count_and_summary(engine):
    usage = SqlUsageStore(engine)
    now = datetime.now(timezone.utc)
    await usage.record("u1", "query", model_id="deepseek", cost_cny=0.01)
    await usage.record("u1", "query", model_id="opus", cost_cny=0.5)
    await usage.record("u1", "research")
    # 昨天的一条，不计入"今天"
    await usage.record("u1", "query", at=now - timedelta(days=1))

    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    assert await usage.count_since("u1", "query", today) == 2
    assert await usage.count_since("u1", "research", today) == 1
    s = await usage.summary("u1")
    assert s["by_action"]["query"] == 3  # summary 不按时间窗
    assert s["by_model"]["opus"] == 1
    assert abs(s["cost_cny"] - 0.51) < 1e-6


async def test_order_lifecycle(engine):
    orders = SqlOrderStore(engine)
    o = await orders.create("u1", "pro", 99.0)
    assert o.status == "pending"
    got = await orders.get(o.id)
    assert got.user_id == "u1" and got.amount_cny == 99.0
    paid = await orders.mark_paid(o.id)
    assert paid.status == "paid"
    # 已支付再标记无效
    again = await orders.mark_paid(o.id)
    assert again.status == "paid"


def test_build_stores_switch(monkeypatch, tmp_path):
    from core.config import settings
    import apps.api.deps as deps
    from core.db.stores import SqlSubscriptionStore
    from core.billing.store import InMemorySubscriptionStore
    monkeypatch.setattr(settings, "use_db", False)
    subs, usage, users, orders = deps._build_stores()
    assert isinstance(subs, InMemorySubscriptionStore)
    monkeypatch.setattr(settings, "use_db", True)
    monkeypatch.setattr(settings, "database_url", f"sqlite+aiosqlite:///{tmp_path}/s.db")
    import core.db.engine as e
    e._engine = None  # 重置单例，避免复用别的 URL
    subs2, *_ = deps._build_stores()
    assert isinstance(subs2, SqlSubscriptionStore)

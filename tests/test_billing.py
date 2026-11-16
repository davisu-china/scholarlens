"""套餐与用量计量：服务层逻辑 + API 层强制。"""
import pytest

from core.billing.plans import ACTION_QUERY, ACTION_RESEARCH, get_plan
from core.billing.service import BillingService, ModelNotAllowed, QuotaExceeded
from core.billing.store import InMemorySubscriptionStore, InMemoryUsageStore


def _svc(plan_for_demo=None):
    subs = InMemorySubscriptionStore({"demo": plan_for_demo} if plan_for_demo else {})
    return BillingService(subs, InMemoryUsageStore()), subs


async def test_default_plan_is_free():
    svc, _ = _svc()
    plan = await svc.plan_for("demo")
    assert plan.id == "free"


async def test_free_plan_blocks_opus():
    svc, _ = _svc("free")
    with pytest.raises(ModelNotAllowed):
        await svc.check_model("demo", "opus")
    # 免费版允许的模型放行
    await svc.check_model("demo", "deepseek")


async def test_pro_plan_allows_all_models():
    svc, _ = _svc("pro")
    await svc.check_model("demo", "opus")  # 不抛异常


async def test_query_quota_enforced_and_recorded():
    svc, _ = _svc("free")  # free: query 每天 20
    for _ in range(20):
        await svc.check_quota("demo", ACTION_QUERY)
        await svc.record("demo", ACTION_QUERY, model_id="deepseek")
    with pytest.raises(QuotaExceeded) as ei:
        await svc.check_quota("demo", ACTION_QUERY)
    assert ei.value.window == "day" and ei.value.limit == 20


async def test_research_quota_separate_from_query():
    svc, _ = _svc("free")  # research 每天 2
    for _ in range(2):
        await svc.record("demo", ACTION_RESEARCH)
    with pytest.raises(QuotaExceeded):
        await svc.check_quota("demo", ACTION_RESEARCH)
    # query 额度不受影响
    await svc.check_quota("demo", ACTION_QUERY)


async def test_enterprise_unlimited():
    svc, _ = _svc("enterprise")
    for _ in range(1000):
        await svc.record("demo", ACTION_QUERY)
    await svc.check_quota("demo", ACTION_QUERY)  # 不抛


async def test_overview_shape():
    svc, _ = _svc("free")
    await svc.record("demo", ACTION_QUERY, model_id="deepseek", cost_cny=0.01)
    ov = await svc.overview("demo")
    assert ov["plan"]["id"] == "free"
    assert ov["usage"]["by_action"]["query"] == 1
    assert ov["usage"]["by_model"]["deepseek"] == 1
    q = next(x for x in ov["quotas"] if x["action"] == "query")
    assert q["used"] == 1 and q["remaining"] == 19


# ---- API 层 ----

@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from apps.api.deps import get_billing
    from apps.api.main import app
    get_billing.cache_clear()
    return TestClient(app)


def test_api_overview_default_free(client):
    r = client.get("/billing/overview", headers={"X-User-Id": "u1"})
    assert r.status_code == 200
    assert r.json()["plan"]["id"] == "free"


def test_api_locked_model_returns_403(client):
    # free 用户选 opus → 403
    r = client.post("/query", json={"question": "x", "model": "opus"}, headers={"X-User-Id": "u2"})
    assert r.status_code == 403
    assert "不包含模型" in r.json()["detail"]


def test_api_upgrade_then_opus_allowed(client):
    h = {"X-User-Id": "u3"}
    client.post("/billing/plan", json={"plan_id": "pro"}, headers=h)
    # 升级后 opus 不再被计费拦截（可能因无证据返回 200 的拒答流）
    r = client.post("/query", json={"question": "x", "model": "opus"}, headers=h)
    assert r.status_code == 200


def test_api_models_marks_locked_for_free(client):
    r = client.get("/models", headers={"X-User-Id": "u4"})
    body = r.json()
    locked = {m["id"]: m["locked"] for m in body["models"]}
    # free 套餐：opus 锁、deepseek/haiku 不锁（若这些模型在目录里）
    if "opus" in locked:
        assert locked["opus"] is True
    if "deepseek" in locked:
        assert locked["deepseek"] is False

"""支付回调验签 + 认证（JWT）。"""
import pytest

from core.auth.jwt import AuthError, create_token, decode_token
from core.auth.users import BadCredentials, DuplicateUser, InMemoryUserStore
from core.billing.orders import InMemoryOrderStore
from core.billing.payment import PaymentError, PaymentService, sign_payload
from core.billing.store import InMemorySubscriptionStore


# ---- JWT ----

def test_jwt_roundtrip():
    tok = create_token("u123")
    assert decode_token(tok) == "u123"


def test_jwt_tampered_rejected():
    with pytest.raises(AuthError):
        decode_token(create_token("u1") + "x")


# ---- 用户 ----

async def test_register_login_wrong_password():
    us = InMemoryUserStore()
    uid = await us.register("alice", "secret")
    assert await us.authenticate("alice", "secret") == uid
    with pytest.raises(BadCredentials):
        await us.authenticate("alice", "wrong")
    with pytest.raises(DuplicateUser):
        await us.register("alice", "x")


# ---- 支付 ----

async def test_payment_flow_upgrades_plan():
    orders, subs = InMemoryOrderStore(), InMemorySubscriptionStore()
    pay = PaymentService(orders, subs, webhook_secret="s3cret")
    order = await pay.checkout("bob", "pro")
    assert order.amount_cny == 99.0 and order.status == "pending"
    # 正确签名 → 履约
    sig = sign_payload(order.id, "paid", "s3cret")
    await pay.handle_webhook(order.id, "paid", sig)
    assert await subs.get_plan_id("bob") == "pro"


async def test_webhook_bad_signature_rejected():
    orders, subs = InMemoryOrderStore(), InMemorySubscriptionStore()
    pay = PaymentService(orders, subs, webhook_secret="s3cret")
    order = await pay.checkout("bob", "pro")
    with pytest.raises(PaymentError, match="签名校验失败"):
        await pay.handle_webhook(order.id, "paid", "forged")
    assert await subs.get_plan_id("bob") is None  # 未升级


async def test_checkout_free_plan_rejected():
    pay = PaymentService(InMemoryOrderStore(), InMemorySubscriptionStore(), webhook_secret="s")
    with pytest.raises(PaymentError, match="无需支付"):
        await pay.checkout("bob", "free")


# ---- token 成本计量 ----

def test_usage_accumulator_cost():
    from core.llm import usage
    acc = usage.start()
    usage.record("claude-opus-5-5", 1000, 500)
    usage.record("deepseek-chat", 2000, 1000)
    assert acc.total_tokens == 4500
    # opus: 1*0.11 + 0.5*0.55 = 0.385 ; deepseek: 2*0.001 + 1*0.002 = 0.004
    assert abs(acc.total_cost_cny - 0.389) < 1e-6

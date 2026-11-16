"""Prometheus 指标 + /metrics 端点 + 阶段 span 时延记录。"""
import pytest
from fastapi.testclient import TestClient

from apps.api.deps import get_billing
from apps.api.main import app
from core.obs import metrics


def test_record_llm_increments_counters():
    before = metrics.LLM_CALLS.labels(model="deepseek-chat")._value.get()
    metrics.record_llm("deepseek-chat", 100, 50, 0.01)
    assert metrics.LLM_CALLS.labels(model="deepseek-chat")._value.get() == before + 1
    assert metrics.LLM_TOKENS.labels(model="deepseek-chat", direction="input")._value.get() >= 100


def test_metrics_endpoint_exposes_prometheus_text():
    get_billing.cache_clear()
    c = TestClient(app)
    c.get("/health")  # 产生一次 HTTP 指标
    r = c.get("/metrics")
    assert r.status_code == 200
    body = r.text
    assert "scholarlens_http_requests_total" in body
    assert "scholarlens_llm_calls_total" in body
    assert "scholarlens_pipeline_stage_duration_seconds" in body


async def test_span_records_stage_latency_even_without_langfuse():
    from core.obs import langfuse as obs
    obs._enabled = False  # Langfuse 未启用
    before = metrics.STAGE_LATENCY.labels(stage="retrieve")._sum.get()
    with obs.span("retrieve", "q") as sink:
        sink(metadata={"x": 1})   # no-op，但时延仍会记
    assert metrics.STAGE_LATENCY.labels(stage="retrieve")._sum.get() > before


async def test_span_noop_when_disabled_does_not_raise():
    from core.obs import langfuse as obs
    obs._enabled = False
    with obs.span("anything") as sink:
        sink(output="x", metadata={"k": "v"})  # 不应抛异常

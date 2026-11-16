"""Prometheus 指标。进程内收集，经 /metrics 暴露给 Prometheus 抓取。

- HTTP 请求量与时延（中间件记录）
- LLM 调用量 / token / 成本（LiteLLMClient 记录）
- 流水线阶段时延（retrieve / rerank / verify，obs.span 记录）
"""

from __future__ import annotations

from prometheus_client import Counter, Histogram

HTTP_REQUESTS = Counter(
    "scholarlens_http_requests_total", "HTTP 请求数", ["method", "path", "status"]
)
HTTP_LATENCY = Histogram(
    "scholarlens_http_request_duration_seconds", "HTTP 时延", ["method", "path"]
)

LLM_CALLS = Counter("scholarlens_llm_calls_total", "LLM 调用数", ["model"])
LLM_TOKENS = Counter("scholarlens_llm_tokens_total", "LLM token 数", ["model", "direction"])
LLM_COST = Counter("scholarlens_llm_cost_cny_total", "LLM 成本(元)", ["model"])

STAGE_LATENCY = Histogram(
    "scholarlens_pipeline_stage_duration_seconds", "流水线阶段时延", ["stage"]
)


def record_llm(model: str, input_tokens: int, output_tokens: int, cost_cny: float) -> None:
    LLM_CALLS.labels(model=model).inc()
    LLM_TOKENS.labels(model=model, direction="input").inc(input_tokens)
    LLM_TOKENS.labels(model=model, direction="output").inc(output_tokens)
    LLM_COST.labels(model=model).inc(cost_cny)

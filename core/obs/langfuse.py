"""Langfuse 可观测接入（PRD 非功能需求：每次请求全链路 trace）。

用 Langfuse Python SDK（v3/OTEL）直接埋点——这是 Langfuse Cloud 当前唯一的实时写入
路径（旧的 SDK v2 ingest 与 LiteLLM 的 'langfuse' callback 已于 2026-11-16 在云端停用）。
每次 LLM 调用包成一个 generation span，记录模型、输入、输出、token 用量；trace 带上
用户/功能/会话属性。

未配置 key 或未装 langfuse 时全部为 no-op，不影响运行。实测导出返回 200、数据可在
云端查到。
"""

from __future__ import annotations

import contextlib
import contextvars
import os
from dataclasses import dataclass

from core.config import settings

_enabled = False
_client = None


@dataclass
class ObsContext:
    user_id: str | None = None
    feature: str | None = None       # qa / research / plan / verify ...
    session_id: str | None = None


_current: contextvars.ContextVar[ObsContext | None] = contextvars.ContextVar("obs_ctx", default=None)


def setup_langfuse() -> bool:
    """初始化 Langfuse 客户端（幂等）。配置齐全且 SDK 可用时返回 True。"""
    global _enabled, _client
    if _enabled:
        return True
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        return False
    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.langfuse_public_key)
    os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.langfuse_secret_key)
    if settings.langfuse_host:
        os.environ.setdefault("LANGFUSE_HOST", settings.langfuse_host)
    try:
        from langfuse import get_client
    except ImportError:
        return False
    _client = get_client()
    _enabled = True
    return True


def is_enabled() -> bool:
    return _enabled


def client():
    return _client


def set_context(user_id: str | None = None, feature: str | None = None, session_id: str | None = None) -> None:
    _current.set(ObsContext(user_id=user_id, feature=feature, session_id=session_id))


def _context() -> ObsContext:
    return _current.get() or ObsContext()


@contextlib.contextmanager
def generation(name: str, model: str, input_payload):
    """把一次 LLM 调用包成 Langfuse generation span。

    yield 一个 sink：sink(output, input_tokens, output_tokens) 在调用完成后回填结果。
    未启用或 span 创建失败时 yield 一个 no-op sink，调用方逻辑不变。
    """
    if not _enabled or _client is None:
        yield lambda *_a, **_k: None
        return
    ctx = _context()
    try:
        cm = _client.start_as_current_observation(
            as_type="generation", name=name, model=model, input=input_payload
        )
    except Exception:
        yield lambda *_a, **_k: None
        return
    # 到这里 span 已建好：只 yield 一次，body 的异常照常传播（span 会记录并关闭）
    with cm as gen:
        def _sink(output, input_tokens: int = 0, output_tokens: int = 0) -> None:
            with contextlib.suppress(Exception):
                gen.update(
                    output=output,
                    model=model,
                    usage_details={"input": input_tokens, "output": output_tokens},
                    metadata=_trace_metadata(ctx),
                )
        yield _sink


def _trace_metadata(ctx: ObsContext) -> dict:
    md: dict = {"service": "scholarlens"}
    if ctx.feature:
        md["feature"] = ctx.feature
    if ctx.user_id:
        md["user_id"] = ctx.user_id
    if ctx.session_id:
        md["session_id"] = ctx.session_id
    return md


def flush() -> None:
    if _client is not None:
        with contextlib.suppress(Exception):
            _client.flush()

"""Langfuse 可观测接入（PRD 非功能需求：每次请求全链路 trace）。

采用 LiteLLM 原生 Langfuse 回调：配置 key 后，每次 LLM 调用自动上报模型、token、
成本、延迟与 prompt/response，无需在每个调用点写埋点。再通过请求级 contextvar 附带
元数据（用户、功能名、会话），让 Langfuse 按 trace/generation 分组。

未配置 key 时全部为 no-op，不影响运行。
"""

from __future__ import annotations

import contextvars
import os
from dataclasses import dataclass

from core.config import settings

_enabled = False


@dataclass
class ObsContext:
    user_id: str | None = None
    feature: str | None = None       # qa / research / plan / verify ...
    session_id: str | None = None


_current: contextvars.ContextVar[ObsContext | None] = contextvars.ContextVar("obs_ctx", default=None)


def setup_langfuse() -> bool:
    """按配置启用 LiteLLM 的 Langfuse 回调（幂等）。返回是否启用。"""
    global _enabled
    if _enabled:
        return True
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        return False
    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.langfuse_public_key)
    os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.langfuse_secret_key)
    if settings.langfuse_host:
        os.environ.setdefault("LANGFUSE_HOST", settings.langfuse_host)
    try:
        import litellm
    except ImportError:
        return False
    for attr in ("callbacks", "success_callback", "failure_callback"):
        cbs = getattr(litellm, attr, None)
        if isinstance(cbs, list) and "langfuse" not in cbs:
            cbs.append("langfuse")
    _enabled = True
    return True


def is_enabled() -> bool:
    return _enabled


def set_context(user_id: str | None = None, feature: str | None = None, session_id: str | None = None) -> None:
    _current.set(ObsContext(user_id=user_id, feature=feature, session_id=session_id))


def current_metadata() -> dict:
    """构造传给 LiteLLM 的 metadata（被 Langfuse 回调读取）。未启用或无上下文时为空。"""
    if not _enabled:
        return {}
    ctx = _current.get()
    if ctx is None:
        return {}
    md: dict = {}
    if ctx.feature:
        md["generation_name"] = ctx.feature
        md["trace_name"] = f"scholarlens:{ctx.feature}"
    if ctx.user_id:
        md["trace_user_id"] = ctx.user_id
    if ctx.session_id:
        md["session_id"] = ctx.session_id
    md["tags"] = ["scholarlens"]
    return md

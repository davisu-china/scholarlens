"""Langfuse 可观测接入：启用开关、请求元数据、注入 LLM 调用。"""
import pytest

from core.obs import langfuse as obs


@pytest.fixture(autouse=True)
def _reset():
    obs._enabled = False
    obs._current.set(None)
    yield
    obs._enabled = False
    obs._current.set(None)


def test_disabled_without_keys(monkeypatch):
    from core.config import settings
    monkeypatch.setattr(settings, "langfuse_public_key", None)
    monkeypatch.setattr(settings, "langfuse_secret_key", None)
    assert obs.setup_langfuse() is False
    assert obs.is_enabled() is False
    assert obs.current_metadata() == {}  # 未启用 → 无元数据


def test_enabled_appends_litellm_callback(monkeypatch):
    import litellm
    from core.config import settings
    monkeypatch.setattr(settings, "langfuse_public_key", "pk")
    monkeypatch.setattr(settings, "langfuse_secret_key", "sk")
    monkeypatch.setattr(settings, "langfuse_host", "http://lf:3000")
    monkeypatch.setattr(litellm, "callbacks", [], raising=False)
    assert obs.setup_langfuse() is True
    assert "langfuse" in litellm.callbacks
    # 幂等：再调不重复
    obs.setup_langfuse()
    assert litellm.callbacks.count("langfuse") == 1


def test_metadata_reflects_context(monkeypatch):
    obs._enabled = True
    obs.set_context(user_id="u1", feature="qa", session_id="s1")
    md = obs.current_metadata()
    assert md["generation_name"] == "qa"
    assert md["trace_name"] == "scholarlens:qa"
    assert md["trace_user_id"] == "u1"
    assert md["session_id"] == "s1"
    assert "scholarlens" in md["tags"]


def test_litellm_client_injects_metadata(monkeypatch):
    from core.adapters.litellm_client import LiteLLMClient
    obs._enabled = True
    obs.set_context(user_id="u2", feature="research")
    c = LiteLLMClient(default_model="claude-opus-5-5", api_base="https://x/v1", api_key="k")
    extra = c._extra()
    assert extra["metadata"]["trace_user_id"] == "u2"
    assert extra["metadata"]["generation_name"] == "research"


def test_no_metadata_when_disabled():
    from core.adapters.litellm_client import LiteLLMClient
    c = LiteLLMClient(default_model="m", api_base="https://x/v1", api_key="k")
    assert "metadata" not in c._extra()  # 未启用 obs

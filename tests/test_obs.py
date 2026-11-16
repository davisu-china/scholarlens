"""Langfuse 可观测：启用开关、generation span 的 no-op 与回填、trace 元数据。"""
import pytest

from core.obs import langfuse as obs


@pytest.fixture(autouse=True)
def _reset():
    obs._enabled = False
    obs._client = None
    obs._current.set(None)
    yield
    obs._enabled = False
    obs._client = None
    obs._current.set(None)


def test_disabled_without_keys(monkeypatch):
    from core.config import settings
    monkeypatch.setattr(settings, "langfuse_public_key", None)
    monkeypatch.setattr(settings, "langfuse_secret_key", None)
    assert obs.setup_langfuse() is False
    assert obs.is_enabled() is False


def test_generation_is_noop_when_disabled():
    # 未启用：yield 一个可调用的 no-op sink，不抛异常
    with obs.generation("qa", "deepseek-chat", "hi") as sink:
        sink("output", 10, 5)   # 不应报错
    assert obs.client() is None


def test_trace_metadata_from_context():
    obs.set_context(user_id="u1", feature="qa", session_id="s1")
    md = obs._trace_metadata(obs._context())
    assert md["feature"] == "qa"
    assert md["user_id"] == "u1"
    assert md["session_id"] == "s1"
    assert md["service"] == "scholarlens"


class _FakeGen:
    def __init__(self): self.updates = []
    def update(self, **kw): self.updates.append(kw)


class _FakeCM:
    def __init__(self, gen): self._gen = gen
    def __enter__(self): return self._gen
    def __exit__(self, *a): return False


class _FakeClient:
    def __init__(self): self.gen = _FakeGen(); self.started = []
    def start_as_current_observation(self, **kw):
        self.started.append(kw)
        return _FakeCM(self.gen)


def test_generation_records_output_and_usage_when_enabled():
    fake = _FakeClient()
    obs._enabled = True
    obs._client = fake
    obs.set_context(user_id="u2", feature="qa")

    with obs.generation("qa", "deepseek-chat", "问题") as sink:
        sink("答案", 9, 39)

    # span 以正确的名称/模型/输入开启
    assert fake.started[0]["name"] == "qa"
    assert fake.started[0]["model"] == "deepseek-chat"
    assert fake.started[0]["input"] == "问题"
    # sink 回填了 output + usage + metadata
    up = fake.gen.updates[0]
    assert up["output"] == "答案"
    assert up["usage_details"] == {"input": 9, "output": 39}
    assert up["metadata"]["user_id"] == "u2"


def test_generation_degrades_if_span_creation_fails():
    class Boom:
        def start_as_current_observation(self, **kw): raise RuntimeError("x")
    obs._enabled = True
    obs._client = Boom()
    # 建 span 失败也不能影响主流程
    with obs.generation("qa", "m", "x") as sink:
        sink("o", 1, 1)

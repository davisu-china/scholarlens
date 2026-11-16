"""模型目录与多网关路由（商业化多模型选择）。"""
import pytest

from core import ports
from core.adapters.multi_llm import MultiGatewayLLM
from core.llm.catalog import ModelSpec, build_catalog, default_cheap_id, default_strong_id


def _spec(sid, model, base="https://x/v1", key="k", tier="flagship"):
    return ModelSpec(id=sid, label=sid, description="", tier=tier, model=model, api_base=base, api_key=key)


def test_catalog_only_includes_configured(monkeypatch):
    from core.config import settings
    monkeypatch.setattr(settings, "llm_api_key", "k")
    monkeypatch.setattr(settings, "llm_api_base", "https://airouter/v1")
    monkeypatch.setattr(settings, "deepseek_api_key", None)
    cat = build_catalog()
    assert "opus" in cat and "haiku" in cat
    assert "deepseek" not in cat  # 没配 key → 不出现


def test_catalog_includes_deepseek_when_keyed(monkeypatch):
    from core.config import settings
    monkeypatch.setattr(settings, "llm_api_key", "k")
    monkeypatch.setattr(settings, "deepseek_api_key", "dk")
    cat = build_catalog()
    assert "deepseek" in cat
    assert cat["deepseek"].api_base.endswith("deepseek.com/v1")


def test_default_ids():
    cat = {"opus": _spec("opus", "m"), "haiku": _spec("haiku", "m", tier="cheap"),
           "deepseek": _spec("deepseek", "m", base="https://api.deepseek.com/v1", tier="cheap")}
    assert default_strong_id(cat) == "opus"
    assert default_cheap_id(cat) == "haiku"


def test_multi_gateway_routes_to_right_client():
    cat = {
        "opus": _spec("opus", "claude-opus-5-5", base="https://airouter/v1", key="ak"),
        "deepseek": _spec("deepseek", "deepseek-chat", base="https://api.deepseek.com/v1", key="dk"),
    }
    m = MultiGatewayLLM(cat, default_id="opus")
    # 每个 id 解析到用对应 base/key/model 配置的子客户端
    opus = m._resolve("opus")
    ds = m._resolve("deepseek")
    assert opus._api_base == "https://airouter/v1" and opus._api_key == "ak"
    assert opus._model(None) == "openai/claude-opus-5-5"
    assert ds._api_base == "https://api.deepseek.com/v1" and ds._api_key == "dk"
    assert ds._model(None) == "openai/deepseek-chat"
    assert m._resolve(None) is opus  # 默认


def test_multi_gateway_unknown_model_raises():
    m = MultiGatewayLLM({"opus": _spec("opus", "m")}, default_id="opus")
    with pytest.raises(ValueError, match="未知"):
        m._resolve("gpt-9")


def test_multi_gateway_empty_catalog_raises():
    with pytest.raises(RuntimeError, match="模型目录为空"):
        MultiGatewayLLM({})


def test_multi_gateway_satisfies_llm_port():
    assert isinstance(MultiGatewayLLM({"opus": _spec("opus", "m")}, default_id="opus"), ports.LLMClient)


async def test_per_request_model_flows_to_llm():
    """用户选的模型 id 透传到 LLM（用 FakeLLM 记录收到的 model）。"""
    from core.adapters.fakes import FakeLLM
    from core.container import build_container

    class RecordingLLM(FakeLLM):
        def __init__(self):
            super().__init__(responses=["ans [e0]."] * 5)
            self.models = []
        async def complete(self, prompt, *, model=None, system=None):
            self.models.append(model)
            return await super().complete(prompt, model=model, system=system)

    llm = RecordingLLM()
    c = build_container(llm=llm, strong_model="opus")
    # 让检索有证据
    from core.domain import Chunk, Granularity
    from core.ingest.schema import Provenance
    chunk = Chunk(id="c1", paper_id="p", level=Granularity.CHUNK, text="position interpolation perplexity",
                  provenance=Provenance(paper_id="p", block_id="c1"))
    vecs = await c.embedder.embed([chunk.text])
    await c.vector_store.upsert([chunk], vecs)
    await c.qa.answer("position interpolation perplexity", model="deepseek")
    assert "deepseek" in llm.models  # 用户选择覆盖了默认 opus

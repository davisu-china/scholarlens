"""新增的无 GPU adapter：LLM 判官 NLI、硅基流动向量化/重排、词法 sparse、LLM 自定义端点。"""
import httpx
import pytest

from core import ports
from core.adapters.bm25_sparse import LexicalSparseEncoder
from core.adapters.fakes import FakeLLM
from core.adapters.llm_nli import LLMJudgeNLI
from core.adapters.siliconflow import SiliconFlowEmbedder, SiliconFlowReranker
from core.domain import Evidence
from core.ingest.schema import Provenance


# ---- LLM 判官引用校验 ----

async def test_llm_judge_parses_scores():
    llm = FakeLLM(responses=["1.0", "0", "0.7 支持", "乱答"])
    nli = LLMJudgeNLI(llm)
    out = await nli.entailment([("e", "h"), ("e", "h"), ("e", "h"), ("e", "h")])
    assert out == [1.0, 0.0, 0.7, 0.0]  # 第四个无数字 → 0


async def test_llm_judge_clamps_and_empty():
    assert await LLMJudgeNLI(FakeLLM()).entailment([]) == []
    out = await LLMJudgeNLI(FakeLLM(responses=["1.5"])).entailment([("e", "h")])
    assert out == [1.0]


async def test_llm_judge_satisfies_port():
    assert isinstance(LLMJudgeNLI(FakeLLM()), ports.NLIModel)


async def test_llm_judge_drives_citation_verifier():
    """端到端：LLM 判官接进引用校验，支持句判对、不支持句判错。"""
    from core.verify.citation import CitationVerifier

    evidence = {
        "e1": Evidence(id="e1", text="YaRN reaches lower perplexity at 128K",
                       provenance=Provenance(paper_id="p", block_id="e1")),
        "e2": Evidence(id="e2", text="The sky is blue",
                       provenance=Provenance(paper_id="p", block_id="e2")),
    }
    # 判官：第一句给高分，第二句给 0
    llm = FakeLLM(responses=["0.95", "0.0"])
    verifier = CitationVerifier(LLMJudgeNLI(llm), threshold=0.6)
    result = await verifier.verify("YaRN lowers perplexity [e1]. YaRN was built by aliens [e2].", evidence)
    assert result.claims[0].supported is True
    assert result.claims[1].supported is False


# ---- 词法 sparse ----

def test_lexical_sparse_overlap_and_disjoint():
    enc = LexicalSparseEncoder()
    a, b = enc.encode("position interpolation YaRN"), enc.encode("YaRN frequency")
    shared = set(a) & set(b)
    assert shared  # "yarn" 命中
    assert set(enc.encode("")) == set()
    # 完全不同的文本点积为 0
    c = enc.encode("totally different words here")
    assert not (set(a) & set(c) - {k for k in a if k in c and False})


# ---- 硅基流动（MockTransport）----

def _sf_transport(kind):
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.headers["authorization"] == "Bearer k"
        if kind == "emb":
            n = len(__import__("json").loads(req.content)["input"])
            return httpx.Response(200, json={"data": [
                {"index": i, "embedding": [float(i)] * 1024} for i in range(n)]})
        return httpx.Response(200, json={"results": [
            {"index": 2, "relevance_score": 0.9},
            {"index": 0, "relevance_score": 0.5},
        ]})
    return httpx.MockTransport(handler)


async def test_siliconflow_embedder_dense_and_sparse():
    emb = SiliconFlowEmbedder("k", transport=_sf_transport("emb"))
    out = await emb.embed(["position interpolation", "YaRN method"])
    assert len(out) == 2
    dense0, sparse0 = out[0]
    assert len(dense0) == 1024
    assert sparse0  # 词法 sparse 非空


async def test_siliconflow_reranker_orders_by_score():
    cands = [Evidence(id=f"c{i}", text=f"doc {i}", provenance=Provenance(paper_id="p", block_id=f"c{i}"))
             for i in range(3)]
    rr = SiliconFlowReranker("k", transport=_sf_transport("rr"))
    out = await rr.rerank("q", cands, top_k=2)
    assert [e.id for e in out] == ["c2", "c0"]  # 按返回顺序（已排序）
    assert out[0].score == 0.9


def test_siliconflow_satisfies_ports():
    assert isinstance(SiliconFlowEmbedder("k"), ports.Embedder)
    assert isinstance(SiliconFlowReranker("k"), ports.Reranker)


# ---- LLM 自定义端点前缀 ----

def test_litellm_custom_endpoint_prefix():
    from core.adapters.litellm_client import LiteLLMClient
    c = LiteLLMClient(default_model="claude-opus-5-5", api_base="https://x/v1", api_key="k")
    assert c._model(None) == "openai/claude-opus-5-5"  # 自定义网关加前缀
    assert c._model("openai/foo") == "openai/foo"       # 已含 provider 不重复加
    c2 = LiteLLMClient(default_model="claude-opus-5-5", api_base="")
    assert c2._model(None) == "claude-opus-5-5"         # 官方 SDK 不加前缀

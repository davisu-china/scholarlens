"""API 层端到端：TestClient 打 /health /query /research，验证接线。"""
import pytest
from fastapi.testclient import TestClient

from apps.api.deps import get_container
from apps.api.main import app
from core.adapters.fakes import FakeLLM
from core.agent.schemas import PlanItem, ResearchPlan


@pytest.fixture
def client(paper):
    get_container.cache_clear()
    c = get_container()
    # 同步索引一篇论文到这个单例容器
    import asyncio
    asyncio.run(c.indexer.index_paper(paper))
    # 脚本化 LLM，让生成带引用
    llm = FakeLLM(
        responses=["YaRN reaches lower perplexity at 128K [e0]."],
        structured_responses=[ResearchPlan(subquestions=[PlanItem(text="yarn perplexity")])],
    )
    c.qa._llm = llm
    c.coordinator._llm = llm
    c.verifier._llm = llm
    yield TestClient(app)
    get_container.cache_clear()


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_query_streams_sse(client):
    r = client.post("/query", json={"question": "yarn perplexity at 128k"})
    assert r.status_code == 200
    assert "event: token" in r.text
    assert "event: done" in r.text


def test_research_streams_trace_and_answer(client):
    r = client.post("/research", json={"question": "how does yarn extend context"})
    assert r.status_code == 200
    assert "event: plan" in r.text
    assert "event: answer" in r.text


def test_citation_graph(client):
    r = client.get("/papers/p1/citations")
    assert r.status_code == 200
    assert "nodes" in r.json()

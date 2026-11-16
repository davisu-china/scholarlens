import pytest
import pytest_asyncio

from core.adapters.fakes import FakeLLM
from core.container import build_container
from eval import metrics
from eval.dataset import EvalExample
from eval.runner import run_suite


def test_recall_at_k():
    assert metrics.recall_at_k(["a", "b", "c"], {"b", "x"}, k=2) == 0.5
    assert metrics.recall_at_k(["a", "b"], set(), k=2) == 1.0


def test_answer_token_f1():
    assert metrics.answer_token_f1("yarn lower perplexity", "yarn lower perplexity") == 1.0
    assert metrics.answer_token_f1("totally different", "yarn perplexity") == 0.0
    assert 0 < metrics.answer_token_f1("yarn high perplexity", "yarn lower perplexity") < 1


def test_citation_precision_recall():
    pred = {("c1", "e1"), ("c2", "e9")}
    gold = {("c1", "e1"), ("c2", "e2")}
    assert metrics.citation_precision(pred, gold) == 0.5
    assert metrics.citation_recall(pred, gold) == 0.5


def test_refusal_correct():
    assert metrics.refusal_correct(did_refuse=True, is_answerable=False)
    assert not metrics.refusal_correct(did_refuse=True, is_answerable=True)


@pytest_asyncio.fixture
async def qa(paper):
    c = build_container()
    await c.indexer.index_paper(paper)
    c.qa._llm = FakeLLM(responses=["YaRN reaches lower perplexity at 128K [e0]."] * 10)
    c.verifier._llm = c.qa._llm
    return c.qa


async def test_run_suite_computes_metrics(qa):
    svc = qa
    examples = [
        EvalExample(qid="1", question="yarn perplexity at 128k",
                    gold_answer="YaRN reaches lower perplexity at 128K", answerable=True),
        EvalExample(qid="2", question="totally unrelated unindexed topic xyzzy", answerable=False),
    ]
    report = await run_suite(svc, examples, suite="unit")
    assert report.n == 2
    assert 0.0 <= report.answer_f1 <= 1.0
    # 例1应被回答(有证据)，例2应被拒答(无证据) → 拒答判定都正确
    assert report.refusal_accuracy == 1.0

import pytest

from core.adapters.fakes import FakeLLM, FakeNLI
from core.domain import Evidence
from core.ingest.schema import Provenance
from core.verify.citation import CitationVerifier, numbers_grounded, split_claims


def _ev(eid, text):
    return Evidence(id=eid, text=text, provenance=Provenance(paper_id="p", block_id=eid))


def test_split_claims_extracts_citations():
    ans = "YaRN reaches lower perplexity at 128K [e2]. NTK needs no fine-tuning [e3]."
    claims = split_claims(ans)
    assert len(claims) == 2
    assert claims[0].eids == ["e2"]
    assert "[e2]" not in claims[0].text


def test_split_claims_multi_citation():
    claims = split_claims("Both methods work well [e1, e2].")
    assert claims[0].eids == ["e1", "e2"]


def test_numbers_grounded():
    assert numbers_grounded("accuracy is 92.1", "we report 92.1 accuracy")
    assert not numbers_grounded("accuracy is 99.9", "we report 92.1 accuracy")
    assert numbers_grounded("no numbers here", "anything")


async def test_verifier_marks_supported_and_unsupported():
    evidence = {
        "e1": _ev("e1", "YaRN reaches lower perplexity at 128K context length"),
        "e2": _ev("e2", "The weather is sunny today"),
    }
    answer = "YaRN reaches lower perplexity at 128K [e1]. YaRN was invented by aliens [e2]."
    verifier = CitationVerifier(FakeNLI(), threshold=0.6)
    result = await verifier.verify(answer, evidence)
    assert result.claims[0].supported is True
    assert result.claims[1].supported is False
    assert 0.0 < result.trust < 1.0
    assert result.claims[0].span is not None


async def test_verifier_rewrites_unsupported_claim():
    evidence = {"e1": _ev("e1", "YaRN reaches lower perplexity at 128K")}
    answer = "YaRN was invented by aliens in 1950 [e1]."
    # LLM 重写成与证据吻合的句子
    llm = FakeLLM(responses=["YaRN reaches lower perplexity at 128K"])
    verifier = CitationVerifier(FakeNLI(), llm, threshold=0.6)
    result = await verifier.verify(answer, evidence)
    assert "aliens" not in result.claims[0].text
    assert result.claims[0].supported is True

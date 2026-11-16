from core.agent.coverage import compute_coverage, token_overlap_covered
from core.ingest.dedup import SeenRegistry, content_hash, paper_id_from_bytes


def test_dedup_same_content():
    reg = SeenRegistry()
    data = b"%PDF fake content"
    assert not reg.is_duplicate(data)
    reg.register(data)
    assert reg.is_duplicate(data)
    assert not reg.is_duplicate(b"other")


def test_paper_id_stable():
    assert paper_id_from_bytes(b"abc") == paper_id_from_bytes(b"abc")
    assert content_hash(b"abc") != content_hash(b"abd")


def test_coverage_full_and_partial():
    points = ["PI perplexity", "PI training cost"]
    evidence = ["PI perplexity is high at long context"]
    rep = compute_coverage(points, evidence, token_overlap_covered)
    assert rep.covered == ["PI perplexity"]
    assert rep.missing == ["PI training cost"]
    assert rep.coverage == 0.5
    assert not rep.is_sufficient


def test_coverage_sufficient():
    points = ["a b c", "d e f"]
    ev = ["a b c d", "d e f g"]
    rep = compute_coverage(points, ev, token_overlap_covered)
    assert rep.is_sufficient

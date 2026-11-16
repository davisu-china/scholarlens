"""RRF 融合的单元测试——骨架里唯一已实现的纯函数，确保测试链路通。"""

from core.retrieval.hybrid import Evidence, rrf_fuse
from core.ingest.schema import Provenance


def _ev(eid: str, score: float = 0.0) -> Evidence:
    return Evidence(id=eid, text=eid, score=score, provenance=Provenance(paper_id="p", block_id="b"))


def test_rrf_rewards_consensus():
    # A 在两路都靠前，应排第一
    r1 = [_ev("A"), _ev("B"), _ev("C")]
    r2 = [_ev("A"), _ev("C"), _ev("D")]
    fused = rrf_fuse([r1, r2], k=60)
    assert fused[0].id == "A"


def test_rrf_dedups():
    r1 = [_ev("A"), _ev("B")]
    r2 = [_ev("A"), _ev("B")]
    fused = rrf_fuse([r1, r2])
    assert sorted(e.id for e in fused) == ["A", "B"]

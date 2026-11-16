import pytest

from core.retrieval.router import classify_rule


@pytest.mark.parametrize("text,expected", [
    ("哪个方法在 NQ 上 EM 最高", "numeric"),
    ("对比 5 种长上下文方法在 LongBench 上的结果", "numeric"),
    ("梳理 RAG 中 Reranker 技术从 2020 年到现在的演进", "survey"),
    ("有哪些用对比学习做 Reranker 的工作", "survey"),
    ("这篇论文的实验设置是什么", "paper_specific"),
    ("公式 3 里的 beta 是什么", "paper_specific"),
    ("什么是 Position Interpolation", "factoid"),
])
def test_classify_rule(text, expected):
    assert classify_rule(text) == expected

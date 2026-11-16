"""评测指标（PRD 第 12 章）。纯函数，可单测。

- recall_at_k        证据段召回（QASPER evidence）
- answer_token_f1    答案与标准答案的 token 级 F1
- citation_precision / citation_recall  引用准确率 / 召回率
- refusal_correct    证据不足时是否正确拒答
"""

from __future__ import annotations

import re

_TOKEN = re.compile(r"[a-z0-9]+")


def _toks(s: str) -> list[str]:
    return _TOKEN.findall(s.lower())


def recall_at_k(retrieved_ids: list[str], gold_ids: set[str], k: int) -> float:
    """前 k 个召回里命中的 gold 证据占全部 gold 的比例。"""
    if not gold_ids:
        return 1.0
    topk = set(retrieved_ids[:k])
    return len(topk & gold_ids) / len(gold_ids)


def answer_token_f1(pred: str, gold: str) -> float:
    """SQuAD/QASPER 风格的 token F1。"""
    p, g = _toks(pred), _toks(gold)
    if not p and not g:
        return 1.0
    if not p or not g:
        return 0.0
    from collections import Counter

    common = Counter(p) & Counter(g)
    overlap = sum(common.values())
    if overlap == 0:
        return 0.0
    precision = overlap / len(p)
    recall = overlap / len(g)
    return 2 * precision * recall / (precision + recall)


def citation_precision(pred_pairs: set[tuple[str, str]], gold_pairs: set[tuple[str, str]]) -> float:
    """pred_pairs / gold_pairs 是 (claim_id, evidence_id) 对集合。"""
    if not pred_pairs:
        return 1.0
    return len(pred_pairs & gold_pairs) / len(pred_pairs)


def citation_recall(pred_pairs: set[tuple[str, str]], gold_pairs: set[tuple[str, str]]) -> float:
    if not gold_pairs:
        return 1.0
    return len(pred_pairs & gold_pairs) / len(gold_pairs)


def refusal_correct(did_refuse: bool, is_answerable: bool) -> bool:
    """可回答却拒答、或不可回答却硬答，都算错。"""
    return did_refuse != is_answerable


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0

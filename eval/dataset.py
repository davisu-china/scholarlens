"""评测数据集加载（PRD 第 12 章）。

统一成 EvalExample：问题 + 标准答案 + gold 证据 id + 是否可回答。
内置 JSONL 加载器；QASPER / SciFact / LitSearch 的适配可在此扩展。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class EvalExample:
    qid: str
    question: str
    gold_answer: str = ""
    gold_evidence_ids: set[str] = field(default_factory=set)
    answerable: bool = True


def load_jsonl(path: str | Path) -> list[EvalExample]:
    """每行一个 JSON：{qid, question, gold_answer?, gold_evidence_ids?, answerable?}。"""
    out: list[EvalExample] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        out.append(
            EvalExample(
                qid=str(d["qid"]),
                question=d["question"],
                gold_answer=d.get("gold_answer", ""),
                gold_evidence_ids=set(d.get("gold_evidence_ids", [])),
                answerable=d.get("answerable", True),
            )
        )
    return out

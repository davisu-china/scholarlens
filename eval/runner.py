"""评测执行器（PRD 第 12 章）。

对一组 EvalExample 跑问答流水线，算指标，产出可复现报告（dict）。
生产里把报告写入 Postgres 的 eval_runs 表并在看板展示趋势。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.qa import QAService
from eval import metrics
from eval.dataset import EvalExample


@dataclass
class EvalReport:
    suite: str
    n: int
    answer_f1: float
    citation_precision: float
    refusal_accuracy: float
    per_example: list[dict] = field(default_factory=list)

    def to_row(self) -> dict:
        return {
            "suite": self.suite, "n": self.n, "answer_f1": self.answer_f1,
            "citation_precision": self.citation_precision, "refusal_accuracy": self.refusal_accuracy,
        }


async def run_suite(qa: QAService, examples: list[EvalExample], *, suite: str = "dev") -> EvalReport:
    f1s: list[float] = []
    cps: list[float] = []
    refusals: list[bool] = []
    per: list[dict] = []

    for ex in examples:
        result = await qa.answer(ex.question)
        text = result.answer.answer
        did_refuse = not result.evidence

        f1 = metrics.answer_token_f1(text, ex.gold_answer) if ex.gold_answer else 0.0
        pred_pairs = {(c.text, c.best_eid) for c in result.answer.claims if c.best_eid}
        gold_pairs = {(c.text, gid) for c in result.answer.claims for gid in ex.gold_evidence_ids}
        cp = metrics.citation_precision(pred_pairs, gold_pairs) if pred_pairs else 1.0
        ref_ok = metrics.refusal_correct(did_refuse, ex.answerable)

        f1s.append(f1)
        cps.append(cp)
        refusals.append(ref_ok)
        per.append({"qid": ex.qid, "answer_f1": f1, "refused": did_refuse, "trust": result.answer.trust})

    return EvalReport(
        suite=suite,
        n=len(examples),
        answer_f1=metrics.mean(f1s),
        citation_precision=metrics.mean(cps),
        refusal_accuracy=metrics.mean([1.0 if r else 0.0 for r in refusals]),
        per_example=per,
    )

"""GET /eval — 评测看板：指标趋势、消融对比、bad case。参见 PRD F8 + 第 12 章。

读取已落库的评测结果（生产为 Postgres eval_runs）。此处返回内存演示数据。
"""

from __future__ import annotations

from fastapi import APIRouter

from eval.ablation import ABLATION_MATRIX

router = APIRouter()


@router.get("/ablation-matrix")
async def ablation_matrix() -> list[dict]:
    """返回消融实验矩阵定义（数值待实测填入）。"""
    return [
        {
            "name": c.name,
            "layout_parse": c.layout_parse,
            "contextual_chunk": c.contextual_chunk,
            "hybrid": c.hybrid,
            "rerank": c.rerank,
            "verify": c.verify,
            "agent": c.agent,
        }
        for c in ABLATION_MATRIX
    ]


@router.get("/runs")
async def eval_runs(suite: str | None = None) -> list[dict]:
    # TODO: 从 Postgres eval_runs 读取历史评测；此处占位空列表
    return []

"""GET /eval — 评测看板：指标趋势、消融对比、bad case。参见 PRD F8 + 第 12 章。"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/runs")
async def eval_runs(suite: str | None = None) -> list[dict]:
    # TODO: 从 Postgres eval_runs 表读取各版本指标
    raise NotImplementedError


@router.get("/bad-cases")
async def bad_cases() -> list[dict]:
    raise NotImplementedError

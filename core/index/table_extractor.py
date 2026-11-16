"""实验结果表格 → (method, dataset, metric, value) 四元组（PRD 第 08 章）。

用 LLM 做结构化抽取，再做方法名归一化与数值校验（数值必须在原表中出现）。
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from core.ingest.schema import Block, PaperIR, Provenance, ResultRow
from core.ports import LLMClient

_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


class _RawRow(BaseModel):
    method: str
    dataset: str
    metric: str
    value: float


class _RawRows(BaseModel):
    rows: list[_RawRow] = Field(default_factory=list)


def normalize_method(name: str) -> str:
    """去掉括号里的超参并去空白：'YaRN (s=16)' → 'YaRN'。"""
    return re.sub(r"\s*[（(].*?[)）]\s*", "", name).strip()


def value_in_table(value: float, table_html: str) -> bool:
    """数值反幻觉：抽出的 value 必须在原表文本中出现。"""
    present = set(_NUMBER.findall(table_html))
    # 同时匹配 '3.2' 与 '3.20' 这类写法
    return any(abs(float(p) - value) < 1e-9 for p in present)


class TableExtractor:
    def __init__(self, llm: LLMClient, *, model: str | None = None) -> None:
        self._llm = llm
        self._model = model

    async def extract(self, table: Block, paper: PaperIR) -> list[ResultRow]:
        from core.llm.prompts import TABLE_EXTRACT_PROMPT

        raw: _RawRows = await self._llm.structured(
            TABLE_EXTRACT_PROMPT.format(
                caption=table.caption or "",
                section=" / ".join(table.section_path),
                html=table.content,
            ),
            _RawRows,
            model=self._model,
        )
        out: list[ResultRow] = []
        for r in raw.rows:
            if not value_in_table(r.value, table.content):
                continue  # 丢弃原表中不存在的数值
            out.append(
                ResultRow(
                    method=normalize_method(r.method),
                    dataset=r.dataset,
                    metric=r.metric,
                    value=r.value,
                    source=Provenance(paper_id=paper.paper_id, block_id=table.id, bboxes=table.bboxes),
                )
            )
        return out

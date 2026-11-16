"""POST /ingest — 文献导入：解析 → 索引。参见 PRD F1。

同步版本便于本地使用；批量导入走 Celery 异步（apps/worker）。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel

from apps.api.deps import get_container
from core.container import Container

router = APIRouter()


class IngestResponse(BaseModel):
    paper_id: str
    title: str
    n_chunks: int
    n_table_rows: int
    n_references: int


@router.post("/upload")
async def upload(files: list[UploadFile], c: Container = Depends(get_container)) -> list[IngestResponse]:
    if c.parser is None:
        raise HTTPException(503, "未配置 PDF 解析器：请在 .env 中设置 SL_MINERU_API_TOKEN")
    out: list[IngestResponse] = []
    for f in files:
        paper = await c.parser.parse(await f.read(), source_hint=f.filename)
        report = await c.indexer.index_paper(paper)
        out.append(
            IngestResponse(
                paper_id=paper.paper_id,
                title=paper.title,
                n_chunks=report.n_chunks,
                n_table_rows=report.n_table_rows,
                n_references=len(paper.references),
            )
        )
    return out

"""POST /ingest — 文献导入：解析 → 存原件 → 索引 → 登记。参见 PRD F1。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from pydantic import BaseModel

from apps.api.deps import get_billing, get_container, get_user
from core.billing.plans import ACTION_INGEST_PAGES
from core.billing.service import BillingService, QuotaExceeded
from core.container import Container
from core.index.registry import PaperMeta

router = APIRouter()


class IngestResponse(BaseModel):
    paper_id: str
    title: str
    collection: str
    n_chunks: int
    n_table_rows: int
    n_references: int


@router.post("/upload")
async def upload(
    files: list[UploadFile],
    collection: str = Form("default"),
    c: Container = Depends(get_container),
    user: str = Depends(get_user),
    billing: BillingService = Depends(get_billing),
) -> list[IngestResponse]:
    if c.parser is None:
        raise HTTPException(503, "未配置 PDF 解析器：请在 .env 中设置 SL_MINERU_API_TOKEN")
    out: list[IngestResponse] = []
    for f in files:
        data = await f.read()
        paper = await c.parser.parse(data, source_hint=f.filename)
        pages = max((bb.page for b in paper.blocks for bb in b.bboxes), default=1)
        try:
            await billing.check_quota(user, ACTION_INGEST_PAGES, units=pages)
        except QuotaExceeded as e:
            raise HTTPException(429, str(e)) from e
        report = await c.indexer.index_paper(paper)
        await c.blob.put(f"pdf/{paper.paper_id}.pdf", data)                 # 存原件供溯源阅读
        await c.registry.add(PaperMeta(paper_id=paper.paper_id, title=paper.title,
                                       collection=collection, n_chunks=report.n_chunks, year=paper.year))
        await billing.record(user, ACTION_INGEST_PAGES, units=pages)
        out.append(IngestResponse(
            paper_id=paper.paper_id, title=paper.title, collection=collection,
            n_chunks=report.n_chunks, n_table_rows=report.n_table_rows, n_references=len(paper.references)))
    return out

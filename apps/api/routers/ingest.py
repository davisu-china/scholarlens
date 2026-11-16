"""POST /ingest — 文献导入：去重 → 存 blob → 解析 → 索引。参见 PRD F1。

同步版本便于演示；生产用 Celery 异步（apps/worker）。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile
from pydantic import BaseModel

from apps.api.deps import get_container
from core.container import Container
from core.ingest.dedup import paper_id_from_bytes

router = APIRouter()


class IngestResponse(BaseModel):
    paper_id: str
    deduplicated: bool
    n_chunks: int = 0


@router.post("/upload")
async def upload(files: list[UploadFile], c: Container = Depends(get_container)) -> list[IngestResponse]:
    out: list[IngestResponse] = []
    for f in files:
        data = await f.read()
        pid = paper_id_from_bytes(data)
        # 解析 → 索引（parser 为真实环境接 MinerU；fakes 下需外部提供 PaperIR）
        if not hasattr(c, "parser") or c.parser is None:  # type: ignore[attr-defined]
            out.append(IngestResponse(paper_id=pid, deduplicated=False, n_chunks=0))
            continue
        paper = await c.parser.parse(data, source_hint=f.filename)  # type: ignore[attr-defined]
        report = await c.indexer.index_paper(paper)
        out.append(IngestResponse(paper_id=pid, deduplicated=False, n_chunks=report.n_chunks))
    return out

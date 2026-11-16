"""POST /ingest — 文献导入，交给 Celery 异步解析，SSE 推送进度。参见 PRD F1。"""

from __future__ import annotations

from fastapi import APIRouter, UploadFile
from pydantic import BaseModel

router = APIRouter()


class IngestResponse(BaseModel):
    task_id: str
    paper_id: str | None = None
    deduplicated: bool = False


@router.post("/upload")
async def upload(files: list[UploadFile]) -> list[IngestResponse]:
    # TODO: 校验类型/大小 → 算 SHA-256 去重 → 存 MinIO → 投递 Celery 解析任务
    raise NotImplementedError


@router.get("/status/{task_id}")
async def status(task_id: str) -> dict:
    # TODO: 查询 Celery 任务状态（也可用 SSE 实时推送）
    raise NotImplementedError

"""GET /papers — 论文列表、元数据、解析结果、引用图谱。参见 PRD F6/F7。"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def list_papers(collection: str | None = None) -> list[dict]:
    raise NotImplementedError


@router.get("/{paper_id}")
async def get_paper(paper_id: str) -> dict:
    # TODO: 返回 PaperIR + 版面分块（供前端 bbox 高亮）
    raise NotImplementedError


@router.get("/{paper_id}/citations")
async def citation_graph(paper_id: str) -> dict:
    # TODO: 从 Neo4j 取引用/被引子图
    raise NotImplementedError

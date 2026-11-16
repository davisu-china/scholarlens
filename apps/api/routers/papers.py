"""GET /papers — 论文列表 / 元数据 / 引用图谱。参见 PRD F6/F7。"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from apps.api.deps import get_container
from core.container import Container

router = APIRouter()


@router.get("/{paper_id}/citations")
async def citation_graph(paper_id: str, c: Container = Depends(get_container)) -> dict:
    neighbors = await c.graph_store.expand([paper_id], hops=1)
    return {
        "nodes": [{"id": paper_id, "seed": True}, *({"id": n} for n in neighbors)],
        "edges": [{"source": paper_id, "target": n} for n in neighbors],
    }

"""GET /papers — 论文列表 / collection 分组 / 引用图 / 原文 PDF。参见 PRD F6/F7。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response

from apps.api.deps import get_container, get_user
from core.container import Container

router = APIRouter()


@router.get("")
async def list_papers(collection: str | None = None, user: str = Depends(get_user),
                      c: Container = Depends(get_container)) -> list[dict]:
    papers = await c.registry.list(collection)
    return [{"paper_id": p.paper_id, "title": p.title, "collection": p.collection,
             "n_chunks": p.n_chunks, "year": p.year} for p in papers]


@router.get("/collections")
async def collections(user: str = Depends(get_user), c: Container = Depends(get_container)) -> list[dict]:
    return [{"name": name, "count": n} for name, n in await c.registry.collections()]


@router.get("/{paper_id}/pdf")
async def get_pdf(paper_id: str, c: Container = Depends(get_container)) -> Response:
    key = f"pdf/{paper_id}.pdf"
    if not await c.blob.exists(key):
        raise HTTPException(404, "PDF 未找到")
    return Response(await c.blob.get(key), media_type="application/pdf")


@router.get("/{paper_id}/citations")
async def citation_graph(paper_id: str, c: Container = Depends(get_container)) -> dict:
    neighbors = await c.graph_store.expand([paper_id], hops=1)
    return {"nodes": [{"id": paper_id, "seed": True}, *({"id": n} for n in neighbors)],
            "edges": [{"source": paper_id, "target": n} for n in neighbors]}

"""GET /models — 可选 LLM 清单，供前端模型选择器（商业化多模型）。"""

from __future__ import annotations

from fastapi import APIRouter

from core.llm.catalog import build_catalog, default_strong_id

router = APIRouter()


@router.get("")
async def list_models() -> dict:
    catalog = build_catalog()
    default = default_strong_id(catalog) if catalog else None
    return {
        "default": default,
        "models": [
            {"id": s.id, "label": s.label, "description": s.description, "tier": s.tier}
            for s in catalog.values()
        ],
    }

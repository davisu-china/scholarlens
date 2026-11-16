"""FastAPI 入口。路由见 PRD 第 06 章 API Gateway。"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.routers import eval as eval_router
from apps.api.routers import ingest, papers, query, research

app = FastAPI(title="ScholarLens API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
app.include_router(query.router, prefix="/query", tags=["query"])
app.include_router(research.router, prefix="/research", tags=["research"])
app.include_router(papers.router, prefix="/papers", tags=["papers"])
app.include_router(eval_router.router, prefix="/eval", tags=["eval"])


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}

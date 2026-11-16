"""FastAPI 入口。路由见 PRD 第 06 章 API Gateway。"""

from __future__ import annotations

import time

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from apps.api.routers import eval as eval_router
from apps.api.routers import auth, billing, ingest, models, papers, query, research

app = FastAPI(title="ScholarLens API", version="0.1.0")


@app.on_event("startup")
async def _startup() -> None:
    from core.config import settings
    from core.obs.langfuse import setup_langfuse

    setup_langfuse()
    if settings.use_db:
        from core.db.engine import create_all, get_engine

        await create_all(get_engine())  # 幂等建表

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
app.include_router(query.router, prefix="/query", tags=["query"])
app.include_router(research.router, prefix="/research", tags=["research"])
app.include_router(papers.router, prefix="/papers", tags=["papers"])
app.include_router(models.router, prefix="/models", tags=["models"])
app.include_router(billing.router, prefix="/billing", tags=["billing"])
app.include_router(eval_router.router, prefix="/eval", tags=["eval"])


@app.middleware("http")
async def _prometheus_mw(request: Request, call_next):
    from core.obs.metrics import HTTP_LATENCY, HTTP_REQUESTS

    start = time.perf_counter()
    response = await call_next(request)
    # 用路由模板而非实际路径，避免 path 基数爆炸
    route = request.scope.get("route")
    path = getattr(route, "path", request.url.path)
    HTTP_REQUESTS.labels(method=request.method, path=path, status=response.status_code).inc()
    HTTP_LATENCY.labels(method=request.method, path=path).observe(time.perf_counter() - start)
    return response


@app.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}

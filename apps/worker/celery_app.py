"""Celery app：离线 Ingestion 流水线（PRD 第 06/07 章）。

按文件 SHA-256 幂等、失败重试、每阶段产物落 MinIO。任务体把 parse → index 串起来，
真实 adapter 由 core.adapters.real 提供。
"""

from __future__ import annotations

import asyncio

from celery import Celery

from core.config import settings
from core.ingest.dedup import content_hash

celery_app = Celery("scholarlens", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(task_track_started=True, task_acks_late=True, worker_prefetch_multiplier=1)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def ingest_paper(self, minio_key: str) -> dict:
    """解析并索引一篇论文。minio_key 指向已上传的 PDF。"""
    try:
        return asyncio.run(_ingest(minio_key))
    except NotImplementedError:
        raise  # 真实环境未接入时直接抛出，便于定位
    except Exception as exc:  # noqa: BLE001
        raise self.retry(exc=exc) from exc


async def _ingest(minio_key: str) -> dict:
    from core.adapters.minio_blob import MinioBlobStore
    from core.adapters.real import build_real_container

    blob = MinioBlobStore()
    pdf = await blob.get(minio_key)
    container = build_real_container()
    paper = await container.parser.parse(pdf, source_hint=minio_key)
    report = await container.indexer.index_paper(paper)
    return {
        "paper_id": report.paper_id,
        "sha256": content_hash(pdf),
        "n_chunks": report.n_chunks,
        "n_table_rows": report.n_table_rows,
        "n_citations": report.n_citations,
    }

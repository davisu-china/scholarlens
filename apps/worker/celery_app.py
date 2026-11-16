"""Celery app：离线 Ingestion 流水线。

按文件 SHA-256 幂等、失败重试、每阶段产物落 MinIO。参见 PRD 第 06/07 章。
"""

from __future__ import annotations

from celery import Celery

from core.config import settings

celery_app = Celery("scholarlens", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(task_track_started=True, task_acks_late=True)


@celery_app.task(bind=True, max_retries=3)
def ingest_paper(self, minio_key: str) -> dict:  # noqa: ANN001
    """解析一篇论文：版面检测 → 元素识别 → 章节树 → 参考文献对齐 → 切分 → Embedding → 入库。

    各步骤对应 core.ingest / core.index 下的模块。
    """
    raise NotImplementedError(
        "TODO: MinerU 解析 → PaperIR → Contextual Chunking → BGE-M3 embedding → Qdrant/Postgres/Neo4j"
    )

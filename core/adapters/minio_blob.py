"""真实对象存储 adapter：MinIO，存 PDF 原件与解析产物。

实现 core.ports.BlobStore。⚠️ 需运行中的 MinIO，无法在沙箱里联调。
"""

from __future__ import annotations

import asyncio
import io

from core.config import settings

_BUCKET = "scholarlens"


class MinioBlobStore:
    def __init__(self, bucket: str = _BUCKET) -> None:
        self._bucket = bucket
        self._client = None

    def _ensure(self):
        if self._client is None:
            from minio import Minio

            self._client = Minio(
                settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=False,
            )
            if not self._client.bucket_exists(self._bucket):
                self._client.make_bucket(self._bucket)
        return self._client

    async def put(self, key: str, data: bytes) -> None:
        client = self._ensure()
        await asyncio.to_thread(
            client.put_object, self._bucket, key, io.BytesIO(data), length=len(data)
        )

    async def get(self, key: str) -> bytes:
        client = self._ensure()
        resp = await asyncio.to_thread(client.get_object, self._bucket, key)
        try:
            return resp.read()
        finally:
            resp.close()
            resp.release_conn()

    async def exists(self, key: str) -> bool:
        from minio.error import S3Error

        client = self._ensure()
        try:
            await asyncio.to_thread(client.stat_object, self._bucket, key)
            return True
        except S3Error:
            return False

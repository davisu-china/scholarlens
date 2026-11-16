"""真实向量库 adapter：Qdrant（dense + sparse 混合 + payload 过滤）。

实现 core.ports.VectorStore。payload 里存 paper_id / collection / section_path /
provenance，过滤在召回阶段下推到 Qdrant。
⚠️ 需运行中的 Qdrant（deploy/docker-compose.yml），无法在沙箱里联调。
"""

from __future__ import annotations

from core.config import settings
from core.domain import Chunk, Evidence
from core.ingest.schema import Provenance

_COLLECTION = "scholarlens"
_DENSE = "dense"
_SPARSE = "sparse"


class QdrantVectorStore:
    def __init__(self, url: str | None = None, *, collection: str = _COLLECTION, dense_dim: int = 1024) -> None:
        self._url = url or settings.qdrant_url
        self._collection = collection
        self._dense_dim = dense_dim
        self._client = None

    def _ensure(self):
        if self._client is None:
            from qdrant_client import AsyncQdrantClient

            self._client = AsyncQdrantClient(url=self._url)
        return self._client

    async def ensure_collection(self) -> None:
        from qdrant_client import models

        client = self._ensure()
        existing = {c.name for c in (await client.get_collections()).collections}
        if self._collection in existing:
            return
        await client.create_collection(
            collection_name=self._collection,
            vectors_config={_DENSE: models.VectorParams(size=self._dense_dim, distance=models.Distance.COSINE)},
            sparse_vectors_config={_SPARSE: models.SparseVectorParams()},
        )

    async def upsert(
        self, chunks: list[Chunk], vectors: list[tuple[list[float], dict[int, float]]]
    ) -> None:
        from qdrant_client import models

        await self.ensure_collection()
        points = []
        for chunk, (dvec, svec) in zip(chunks, vectors, strict=True):
            points.append(
                models.PointStruct(
                    id=_uuid(chunk.id),
                    vector={
                        _DENSE: dvec,
                        _SPARSE: models.SparseVector(indices=list(svec), values=list(svec.values())),
                    },
                    payload={
                        "chunk_id": chunk.id,
                        "paper_id": chunk.paper_id,
                        "level": int(chunk.level),
                        "text": chunk.text,
                        "section_path": chunk.section_path,
                        "collection": chunk.provenance.paper_id,  # 可换为真实 collection 字段
                        "provenance": chunk.provenance.model_dump(),
                    },
                )
            )
        await self._ensure().upsert(collection_name=self._collection, points=points)

    def _filter(self, filters: dict):
        from qdrant_client import models

        conditions = []
        if "paper_id" in filters:
            conditions.append(models.FieldCondition(key="paper_id", match=models.MatchValue(value=filters["paper_id"])))
        if "paper_ids" in filters:
            conditions.append(models.FieldCondition(key="paper_id", match=models.MatchAny(any=filters["paper_ids"])))
        if "collection" in filters:
            conditions.append(models.FieldCondition(key="collection", match=models.MatchValue(value=filters["collection"])))
        return models.Filter(must=conditions) if conditions else None

    def _to_evidence(self, point) -> Evidence:
        p = point.payload
        return Evidence(
            id=p["chunk_id"],
            text=p["text"],
            score=point.score,
            provenance=Provenance(**p["provenance"]),
            section_path=p.get("section_path", []),
        )

    async def search_dense(self, vec: list[float], filters: dict, limit: int) -> list[Evidence]:
        from qdrant_client import models

        res = await self._ensure().query_points(
            collection_name=self._collection,
            query=vec,
            using=_DENSE,
            query_filter=self._filter(filters),
            limit=limit,
            with_payload=True,
        )
        return [self._to_evidence(p) for p in res.points]

    async def search_sparse(self, vec: dict[int, float], filters: dict, limit: int) -> list[Evidence]:
        from qdrant_client import models

        res = await self._ensure().query_points(
            collection_name=self._collection,
            query=models.SparseVector(indices=list(vec), values=list(vec.values())),
            using=_SPARSE,
            query_filter=self._filter(filters),
            limit=limit,
            with_payload=True,
        )
        return [self._to_evidence(p) for p in res.points]


def _uuid(chunk_id: str) -> str:
    """Qdrant point id 需是 uuid 或 int；用 chunk_id 的确定性 uuid5。"""
    import uuid

    return str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))

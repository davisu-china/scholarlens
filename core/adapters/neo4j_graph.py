"""真实引用图 adapter：Neo4j。实现 core.ports.GraphStore。

⚠️ 需运行中的 Neo4j（deploy/docker-compose.yml），无法在沙箱里联调。
"""

from __future__ import annotations

from core.config import settings


class Neo4jGraphStore:
    def __init__(self, uri: str | None = None, user: str | None = None, password: str | None = None) -> None:
        self._uri = uri or settings.neo4j_uri
        self._user = user or settings.neo4j_user
        self._password = password or settings.neo4j_password
        self._driver = None

    def _ensure(self):
        if self._driver is None:
            from neo4j import AsyncGraphDatabase

            self._driver = AsyncGraphDatabase.driver(self._uri, auth=(self._user, self._password))
        return self._driver

    async def add_paper(self, paper_id: str) -> None:
        async with self._ensure().session() as s:
            await s.run("MERGE (p:Paper {id: $id})", id=paper_id)

    async def add_citation(self, src_paper_id: str, dst_paper_id: str) -> None:
        async with self._ensure().session() as s:
            await s.run(
                "MERGE (a:Paper {id: $src}) MERGE (b:Paper {id: $dst}) MERGE (a)-[:CITES]->(b)",
                src=src_paper_id, dst=dst_paper_id,
            )

    async def expand(self, seed_papers: list[str], hops: int) -> list[str]:
        # 沿引用/被引任意方向扩展 hops 跳，排除种子本身
        query = (
            f"MATCH (p:Paper)-[:CITES*1..{int(hops)}]-(n:Paper) "
            "WHERE p.id IN $seeds AND NOT n.id IN $seeds "
            "RETURN DISTINCT n.id AS id"
        )
        async with self._ensure().session() as s:
            res = await s.run(query, seeds=seed_papers)
            return sorted([r["id"] async for r in res])

    async def close(self) -> None:
        if self._driver is not None:
            await self._driver.close()

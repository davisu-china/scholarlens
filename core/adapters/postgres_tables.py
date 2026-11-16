"""真实表格库 adapter：Postgres 存实验结果四元组，支持数值问答检索。

实现 core.ports.TableStore。用 SQLAlchemy 2.0 async。
⚠️ 需运行中的 Postgres，无法在沙箱里联调。
"""

from __future__ import annotations

from core.config import settings
from core.domain import Evidence, Query
from core.ingest.schema import Provenance, ResultRow

_DDL = """
CREATE TABLE IF NOT EXISTS result_rows (
    id BIGSERIAL PRIMARY KEY,
    method TEXT NOT NULL,
    dataset TEXT NOT NULL,
    metric TEXT NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    paper_id TEXT,
    block_id TEXT
);
"""


class PostgresTableStore:
    def __init__(self, dsn: str | None = None) -> None:
        self._dsn = dsn or settings.postgres_dsn
        self._engine = None

    def _ensure(self):
        if self._engine is None:
            from sqlalchemy.ext.asyncio import create_async_engine

            self._engine = create_async_engine(self._dsn)
        return self._engine

    async def init(self) -> None:
        from sqlalchemy import text

        async with self._ensure().begin() as conn:
            await conn.execute(text(_DDL))

    async def insert_rows(self, rows: list[ResultRow]) -> None:
        from sqlalchemy import text

        if not rows:
            return
        async with self._ensure().begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO result_rows (method,dataset,metric,value,paper_id,block_id) "
                    "VALUES (:method,:dataset,:metric,:value,:paper_id,:block_id)"
                ),
                [
                    {
                        "method": r.method, "dataset": r.dataset, "metric": r.metric, "value": r.value,
                        "paper_id": r.source.paper_id if r.source else None,
                        "block_id": r.source.block_id if r.source else None,
                    }
                    for r in rows
                ],
            )

    async def query(self, q: Query) -> list[Evidence]:
        """简单实现：按 method/dataset/metric 的关键词 ILIKE 匹配。

        生产可做更强的 NL→SQL 或结构化槽位抽取；这里给可用基线。
        """
        from sqlalchemy import text

        like = f"%{q.text}%"
        async with self._ensure().connect() as conn:
            res = await conn.execute(
                text(
                    "SELECT method,dataset,metric,value,paper_id,block_id FROM result_rows "
                    "WHERE method ILIKE :q OR dataset ILIKE :q OR metric ILIKE :q LIMIT 50"
                ),
                {"q": like},
            )
            rows = res.fetchall()
        out = []
        for i, r in enumerate(rows):
            out.append(
                Evidence(
                    id=f"table-{i}",
                    text=f"{r.method} on {r.dataset}: {r.metric}={r.value}",
                    score=1.0,
                    provenance=Provenance(paper_id=r.paper_id or "unknown", block_id=r.block_id or "unknown"),
                )
            )
        return out

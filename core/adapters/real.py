"""生产形态的 composition root：用真实 adapter 组装容器。

被 apps/api/deps.py 在 SL_USE_REAL_ADAPTERS=1 时调用。各 adapter 重依赖延迟导入，
因此导入本模块本身不要求装齐所有依赖；只有真正构建时才需要对应库与服务。

⚠️ 真实联调需要 Qdrant / Neo4j / Postgres / MinIO 运行中，以及 BGE / DeBERTa 模型与
LLM API key。无法在无依赖沙箱里验证——这里保证接口对齐与装配正确。
"""

from __future__ import annotations

from core.adapters.bge import BGEM3Embedder, BGEReranker
from core.adapters.litellm_client import LiteLLMClient
from core.adapters.neo4j_graph import Neo4jGraphStore
from core.adapters.nli import DebertaNLI
from core.adapters.postgres_tables import PostgresTableStore
from core.adapters.qdrant_store import QdrantVectorStore
from core.config import settings
from core.container import Container, build_container


def build_real_container() -> Container:
    return build_container(
        llm=LiteLLMClient(default_model=settings.strong_model),
        embedder=BGEM3Embedder(),
        vector_store=QdrantVectorStore(),
        reranker=BGEReranker(),
        table_store=PostgresTableStore(),
        graph_store=Neo4jGraphStore(),
        nli=DebertaNLI(),
    )

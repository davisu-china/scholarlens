"""生产形态的 composition root：用真实 adapter 组装容器。

被 apps/api/deps.py 在 SL_USE_REAL_ADAPTERS=1 时调用。各 adapter 重依赖延迟导入，
因此导入本模块本身不要求装齐所有依赖；只有真正构建时才需要对应库与服务。

默认组合（均无需本地 GPU）：
- LLM：airouter 等 OpenAI 兼容网关（llm_api_base + llm_api_key），强模型 opus、小模型 haiku
- 向量化/重排：硅基流动 API（bge-m3 / bge-reranker-v2-m3）+ 本地词法 sparse
- 引用校验：LLM 判官（nli_mode=llm）或本地 DeBERTa（nli_mode=deberta）
- PDF 解析：MinerU 云 API（有 token）或本地 MinerU

需要运行中的 Qdrant / Neo4j / Postgres / MinIO。
"""

from __future__ import annotations

from core.adapters.multi_llm import MultiGatewayLLM
from core.llm.catalog import build_catalog, default_cheap_id, default_strong_id
from core.adapters.mineru_cloud import MinerUCloudParser
from core.adapters.mineru_parser import MinerUParser
from core.adapters.neo4j_graph import Neo4jGraphStore
from core.adapters.postgres_tables import PostgresTableStore
from core.adapters.qdrant_store import QdrantVectorStore
from core.adapters.siliconflow import SiliconFlowEmbedder, SiliconFlowReranker
from core.config import settings
from core.container import Container, build_container
from core.ports import LLMClient, NLIModel, Parser


def build_real_container() -> Container:
    catalog = build_catalog()
    strong_id = default_strong_id(catalog)
    cheap_id = default_cheap_id(catalog)
    llm = MultiGatewayLLM(catalog, default_id=strong_id)
    return build_container(
        llm=llm,
        embedder=SiliconFlowEmbedder(),
        vector_store=QdrantVectorStore(),
        reranker=SiliconFlowReranker(),
        table_store=PostgresTableStore(),
        graph_store=Neo4jGraphStore(),
        nli=default_nli(llm, cheap_id),
        parser=default_parser(),
        strong_model=strong_id,
        small_model=cheap_id,
    )


def default_nli(llm: LLMClient, cheap_model_id: str) -> NLIModel:
    """引用校验后端：默认 LLM 判官（无需 GPU），nli_mode=deberta 时用本地模型。"""
    if settings.nli_mode == "deberta":
        from core.adapters.nli import DebertaNLI

        return DebertaNLI()
    from core.adapters.llm_nli import LLMJudgeNLI

    return LLMJudgeNLI(llm, model=cheap_model_id)


def default_parser() -> Parser:
    """有 MinerU 云 token 就用云解析（无需 GPU），否则用本地 MinerU。"""
    return MinerUCloudParser() if settings.mineru_api_token else MinerUParser()

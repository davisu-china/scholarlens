"""契约测试：真实 adapter 构造正常，且结构上满足对应的 Protocol。

重依赖在 adapter 内部延迟导入，所以这些检查不需要装 qdrant/torch/litellm 等。
真实功能联调需外部服务，不在此测。
"""
from core import ports


def test_litellm_satisfies_llm_port():
    from core.adapters.litellm_client import LiteLLMClient
    assert isinstance(LiteLLMClient(), ports.LLMClient)


def test_bge_satisfies_embedder_and_reranker():
    from core.adapters.bge import BGEM3Embedder, BGEReranker
    assert isinstance(BGEM3Embedder(), ports.Embedder)
    assert isinstance(BGEReranker(), ports.Reranker)


def test_qdrant_satisfies_vector_store():
    from core.adapters.qdrant_store import QdrantVectorStore
    assert isinstance(QdrantVectorStore(), ports.VectorStore)


def test_neo4j_satisfies_graph_store():
    from core.adapters.neo4j_graph import Neo4jGraphStore
    assert isinstance(Neo4jGraphStore(), ports.GraphStore)


def test_nli_satisfies_port():
    from core.adapters.nli import DebertaNLI
    assert isinstance(DebertaNLI(), ports.NLIModel)


def test_postgres_satisfies_table_store():
    from core.adapters.postgres_tables import PostgresTableStore
    assert isinstance(PostgresTableStore(), ports.TableStore)


def test_minio_satisfies_blob_store():
    from core.adapters.minio_blob import MinioBlobStore
    assert isinstance(MinioBlobStore(), ports.BlobStore)


def test_mineru_satisfies_parser():
    from core.adapters.mineru_parser import MinerUParser
    assert isinstance(MinerUParser(), ports.Parser)


def test_real_container_module_imports():
    # 不构建（会连真实服务），只验证装配代码可导入
    import core.adapters.real as real
    assert hasattr(real, "build_real_container")

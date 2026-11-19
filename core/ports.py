"""Ports：所有外部系统的抽象接口（六边形架构的「端口」）。

业务逻辑只依赖这些 Protocol，不依赖具体实现。每个 port 都有：
- 一个真实 adapter（core/adapters/，接 Qdrant / Neo4j / LiteLLM / MinerU …）
- 一个内存 fake（core/adapters/fakes.py，用于单测和本地快速起步）

更换后端 = 换一个 adapter，业务代码零改动。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from core.domain import Chunk, Evidence, Query
from core.ingest.schema import PaperIR, ResultRow


class EmbedResult(Protocol):
    dense: list[float]
    sparse: dict[int, float]


@runtime_checkable
class Embedder(Protocol):
    """文本向量化。BGE-M3 一次前向同时给出 dense 与 sparse。"""

    async def embed(self, texts: list[str]) -> list[tuple[list[float], dict[int, float]]]:
        """返回每条文本的 (dense_vec, sparse_vec)。"""
        ...


@runtime_checkable
class VectorStore(Protocol):
    """向量库（Qdrant）。payload filter 在召回阶段下推。"""

    async def upsert(self, chunks: list[Chunk], vectors: list[tuple[list[float], dict[int, float]]]) -> None: ...

    async def search_dense(self, vec: list[float], filters: dict, limit: int) -> list[Evidence]: ...

    async def search_sparse(self, vec: dict[int, float], filters: dict, limit: int) -> list[Evidence]: ...


@runtime_checkable
class Reranker(Protocol):
    """Cross-Encoder 精排（bge-reranker-v2-m3）。"""

    async def rerank(self, query: str, candidates: list[Evidence], top_k: int) -> list[Evidence]: ...


@runtime_checkable
class GraphStore(Protocol):
    """引用图（Neo4j）。"""

    async def add_paper(self, paper_id: str) -> None: ...

    async def add_citation(self, src_paper_id: str, dst_paper_id: str) -> None: ...

    async def expand(self, seed_papers: list[str], hops: int) -> list[str]:
        """从种子论文沿引用/被引关系扩展，返回相关 paper_id。"""
        ...


@runtime_checkable
class LLMClient(Protocol):
    """LLM 网关（LiteLLM）。失败 fallback 由 adapter 内部处理。"""

    async def complete(self, prompt: str, *, model: str | None = None, system: str | None = None) -> str: ...

    async def stream(self, prompt: str, *, model: str | None = None, system: str | None = None):
        """异步产出 token。"""
        ...

    async def structured[T](self, prompt: str, schema: type[T], *, model: str | None = None) -> T:
        """约束 JSON 输出并解析为 Pydantic 模型。"""
        ...


@runtime_checkable
class NLIModel(Protocol):
    """自然语言推理（DeBERTa-NLI），判断 P(前提蕴含假设)。"""

    async def entailment(self, pairs: list[tuple[str, str]]) -> list[float]:
        """每对 (premise, hypothesis) 返回蕴含概率。"""
        ...


@runtime_checkable
class Parser(Protocol):
    """PDF 解析器（MinerU + GROBID），输出归一化的 PaperIR。"""

    async def parse(self, pdf_bytes: bytes, *, source_hint: str | None = None) -> PaperIR: ...


@runtime_checkable
class TableStore(Protocol):
    """实验结果表格的结构化存储（Postgres）。"""

    async def insert_rows(self, rows: list[ResultRow]) -> None: ...

    async def delete_by_paper(self, paper_id: str) -> None: ...

    async def query(self, q: Query) -> list[Evidence]:
        """数值类问题路由到这里做结构化查询。"""
        ...


@runtime_checkable
class BlobStore(Protocol):
    """对象存储（MinIO），存 PDF 原件与解析产物。"""

    async def put(self, key: str, data: bytes) -> None: ...

    async def get(self, key: str) -> bytes: ...

    async def exists(self, key: str) -> bool: ...

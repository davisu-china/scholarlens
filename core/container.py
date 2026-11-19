"""Composition root：把 ports 组装成服务。

默认用内存 fakes，让整个应用（含 API）开箱即跑、便于演示与测试；
把 `build_container(fake=False)` 接上真实 adapter 即为生产形态——业务服务零改动。
"""

from __future__ import annotations

from dataclasses import dataclass

from core.adapters import fakes
from core.agent.coordinator import ResearchCoordinator
from core.index.indexer import Indexer
from core.index.table_extractor import TableExtractor
from core.index.registry import InMemoryPaperRegistry, PaperRegistry
from core.ports import (
    BlobStore,
    Embedder,
    GraphStore,
    LLMClient,
    NLIModel,
    Parser,
    Reranker,
    TableStore,
    VectorStore,
)
from core.qa import QAService
from core.retrieval.hybrid import HybridRetriever
from core.verify.citation import CitationVerifier


@dataclass
class Container:
    embedder: Embedder
    vector_store: VectorStore
    reranker: Reranker
    table_store: TableStore
    graph_store: GraphStore
    llm: LLMClient
    nli: NLIModel

    retriever: HybridRetriever
    verifier: CitationVerifier
    indexer: Indexer
    qa: QAService
    coordinator: ResearchCoordinator
    parser: Parser | None = None   # PDF 解析器；未配置时 /ingest 无法解析
    blob: BlobStore | None = None
    registry: PaperRegistry | None = None


def build_container(
    *,
    llm: LLMClient | None = None,
    embedder: Embedder | None = None,
    vector_store: VectorStore | None = None,
    reranker: Reranker | None = None,
    table_store: TableStore | None = None,
    graph_store: GraphStore | None = None,
    nli: NLIModel | None = None,
    parser: Parser | None = None,
    blob: BlobStore | None = None,
    registry: PaperRegistry | None = None,
    strong_model: str | None = None,   # 默认强模型 id（plan/write/qa）
    small_model: str | None = None,    # 默认小模型 id（reflect/改写）
) -> Container:
    """任何未显式注入的 port 都用 fake 兜底。生产环境把真实 adapter 传进来即可。"""
    embedder = embedder or fakes.FakeEmbedder()
    vector_store = vector_store or fakes.FakeVectorStore()
    reranker = reranker or fakes.FakeReranker()
    table_store = table_store or fakes.FakeTableStore()
    graph_store = graph_store or fakes.FakeGraphStore()
    llm = llm or fakes.FakeLLM()
    nli = nli or fakes.FakeNLI()
    blob = blob or fakes.FakeBlobStore()
    registry = registry or InMemoryPaperRegistry()

    retriever = HybridRetriever(
        embedder=embedder,
        vector_store=vector_store,
        reranker=reranker,
        table_store=table_store,
        graph_store=graph_store,
    )
    verifier = CitationVerifier(nli, llm)
    indexer = Indexer(
        embedder=embedder,
        vector_store=vector_store,
        table_extractor=TableExtractor(llm),
        table_store=table_store,
        graph_store=graph_store,
        llm=llm,
        context_model=small_model,
    )
    qa = QAService(llm=llm, retriever=retriever, verifier=verifier, model=strong_model)
    coordinator = ResearchCoordinator(
        llm=llm, retriever=retriever, verifier=verifier,
        strong_model=strong_model, small_model=small_model,
    )

    return Container(
        embedder=embedder,
        vector_store=vector_store,
        reranker=reranker,
        table_store=table_store,
        graph_store=graph_store,
        llm=llm,
        nli=nli,
        retriever=retriever,
        verifier=verifier,
        indexer=indexer,
        qa=qa,
        coordinator=coordinator,
        parser=parser,
        blob=blob,
        registry=registry,
    )

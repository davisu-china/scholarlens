"""跨模块共享的领域模型。

与 `core.ingest.schema`（解析产出的 Document IR）分工：
- schema.py 描述「论文被解析成什么」(PaperIR / Block / BBox / Reference)
- domain.py 描述「检索与问答过程中流动的东西」(Chunk / Query / Evidence / Claim)

所有类型都是 Pydantic 模型，便于校验、序列化（API 边界）和测试构造。
"""

from __future__ import annotations

from enum import IntEnum
from typing import Literal

from pydantic import BaseModel, Field

from core.ingest.schema import Provenance

# --------------------------------------------------------------------------- #
# 多粒度索引单元（PRD 第 08 章）
# --------------------------------------------------------------------------- #


class Granularity(IntEnum):
    """四层索引。数值越小粒度越粗。"""

    PAPER = 0      # L0 整篇：标题 + 摘要 + 结构化摘要
    SECTION = 1    # L1 章节：章节摘要
    CHUNK = 2      # L2 段落：~400 token，主要召回单元
    ELEMENT = 3    # L3 元素：表格行 / 公式 / 图注


class Chunk(BaseModel):
    """一个可被索引和召回的单元。

    `context_prefix` 是 Contextual Retrieval 的上下文前缀（PRD 第 08 章），
    入库时与 `text` 拼接后一起做 embedding 与 BM25，解决 chunk 缺主语的问题。
    """

    id: str
    paper_id: str
    collection: str = ""      # 所属文献库，检索时按它过滤
    level: Granularity
    text: str
    context_prefix: str = ""
    section_path: list[str] = Field(default_factory=list)
    provenance: Provenance

    @property
    def indexed_text(self) -> str:
        """真正进入索引的文本：上下文前缀 + 正文。"""
        return f"{self.context_prefix}\n\n{self.text}".strip() if self.context_prefix else self.text


# --------------------------------------------------------------------------- #
# 检索
# --------------------------------------------------------------------------- #

QueryIntent = Literal["factoid", "numeric", "survey", "paper_specific"]


class Query(BaseModel):
    """一次检索请求。经 Query 处理后填充 embedding / sparse / intent。"""

    text: str
    intent: QueryIntent = "factoid"
    filters: dict = Field(default_factory=dict)        # year / venue / collection / 权限
    dense_vec: list[float] | None = None
    sparse_vec: dict[int, float] | None = None         # term_id -> weight
    seed_papers: list[str] = Field(default_factory=list)
    top_k: int = 10


class Evidence(BaseModel):
    """一条检索到的证据。`id` 在生成时作为 [eid] 被引用。"""

    id: str
    text: str
    score: float = 0.0
    provenance: Provenance
    section_path: list[str] = Field(default_factory=list)

    model_config = {"frozen": False}


# --------------------------------------------------------------------------- #
# 引用校验（PRD 第 11 章）
# --------------------------------------------------------------------------- #


class Claim(BaseModel):
    """答案里的一条「论断 + 引用」。"""

    text: str
    eids: list[str] = Field(default_factory=list)
    supported: bool = False
    best_eid: str | None = None
    span: Provenance | None = None       # 命中证据内最相似句子的位置，供前端精确高亮


class VerifiedAnswer(BaseModel):
    """校验后的答案。`trust` = 有据论断占比。"""

    answer: str
    claims: list[Claim] = Field(default_factory=list)
    trust: float = 0.0

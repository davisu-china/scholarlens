"""Document Intermediate Representation (Document IR).

所有解析器（MinerU / GROBID / ...）的输出都归一到这里定义的 Pydantic 模型。
下游模块（index / retrieval / agent）只依赖这组 IR，因此更换解析器不需要改动下游代码。

参见 PRD 第 07 章「文档解析流水线」。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

BlockType = Literal["text", "equation", "table", "figure", "caption"]


class BBox(BaseModel):
    """页面坐标框，前端用于原文高亮。

    page 从 1 开始；坐标按页面尺寸归一化到 0–1000（MinerU 的输出约定），
    前端按「渲染页宽高 / 1000」缩放。
    """

    page: int
    x0: float
    y0: float
    x1: float
    y1: float


class Reference(BaseModel):
    """一条参考文献，已尽量对齐到 Semantic Scholar paperId。"""

    key: str                       # 文内引用 key，如 "chen2023pi"
    raw: str                       # 原始引文字符串
    title: str | None = None
    year: int | None = None
    s2_paper_id: str | None = None  # 对齐后的 Semantic Scholar id（可能为空）


class Block(BaseModel):
    """版面切分后的最小语义块。"""

    id: str
    type: BlockType
    content: str                       # 文本 / LaTeX / HTML 表格 / VLM 图像描述
    bboxes: list[BBox]                 # 跨页元素有多个 bbox
    section_path: list[str] = Field(default_factory=list)  # ["3 Method", "3.2 ..."]
    refs: list[str] = Field(default_factory=list)          # 块内引用的参考文献 key
    caption: str | None = None         # 表格 / 图的标题


class PaperIR(BaseModel):
    """一篇论文的完整中间表示。"""

    paper_id: str                      # 内部 id（SHA-256 前缀）
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str | None = None
    abstract: str = ""
    blocks: list[Block] = Field(default_factory=list)
    references: list[Reference] = Field(default_factory=list)


class Provenance(BaseModel):
    """溯源信息：一条内容来自哪篇论文的哪个块的哪些坐标框。"""

    paper_id: str
    block_id: str
    bboxes: list[BBox] = Field(default_factory=list)


class ResultRow(BaseModel):
    """实验结果表格抽取出的四元组 (method, dataset, metric, value)。"""

    method: str
    dataset: str
    metric: str
    value: float
    source: Provenance | None = None

"""多粒度索引与 Contextual Chunking（PRD 第 08 章）。

把一篇 PaperIR 切成四层 Chunk：
  L0 Paper   —— 标题 + 摘要（粗筛）
  L1 Section —— 按 section_path 聚合的章节文本（定位章节）
  L2 Chunk   —— ~400 token 段落，不跨章节（主要召回单元）
  L3 Element —— 表格 / 公式 / 图注（数值与公式问答）

Contextual Chunking：入库前为每个 L2 chunk 生成 50–100 token 的上下文前缀，
解决「chunk 缺主语无法被检索」的问题。前缀生成通过 LLM port，可关闭；
生成时按 concurrency 限并发，单个 chunk 失败或超时不影响其他 chunk。
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict

from core.domain import Chunk, Granularity
from core.ingest.schema import Block, PaperIR, Provenance
from core.ports import LLMClient

logger = logging.getLogger(__name__)


def estimate_tokens(text: str) -> int:
    """粗略 token 估计：中文按字符、英文按 ~4 字符/token。够切分决策用。"""
    ascii_chars = sum(1 for c in text if c.isascii())
    cjk_chars = len(text) - ascii_chars
    return cjk_chars + ascii_chars // 4


def _provenance(paper_id: str, block: Block) -> Provenance:
    return Provenance(paper_id=paper_id, block_id=block.id, bboxes=block.bboxes)


def _split_text(text: str, max_tokens: int) -> list[str]:
    """按句子边界把长文本切成不超过 max_tokens 的片段。"""
    import re

    sentences = re.split(r"(?<=[。！？.!?])\s*", text.strip())
    chunks: list[str] = []
    cur: list[str] = []
    cur_tok = 0
    for sent in sentences:
        if not sent:
            continue
        t = estimate_tokens(sent)
        if cur and cur_tok + t > max_tokens:
            chunks.append(" ".join(cur))
            cur, cur_tok = [], 0
        cur.append(sent)
        cur_tok += t
    if cur:
        chunks.append(" ".join(cur))
    return chunks


_CONTEXT_PROMPT = (
    "这是论文《{title}》{section} 的一个片段。请用一句话(50-100字)说明它的背景"
    "(出自哪篇论文的哪个部分、在讨论什么)，作为检索用的上下文前缀，不要复述原文。\n\n"
    "片段：{chunk}\n\n上下文前缀："
)


class MultiGranularityChunker:
    def __init__(
        self,
        llm: LLMClient | None = None,
        *,
        chunk_tokens: int = 400,
        concurrency: int = 5,
        timeout: float = 30.0,
        model: str | None = None,
    ) -> None:
        self._llm = llm
        self._chunk_tokens = chunk_tokens
        self._concurrency = max(1, concurrency)
        self._timeout = timeout
        self._model = model

    def _paper_chunk(self, paper: PaperIR) -> Chunk:
        text = f"{paper.title}\n\n{paper.abstract}".strip()
        return Chunk(
            id=f"{paper.paper_id}:L0",
            paper_id=paper.paper_id,
            level=Granularity.PAPER,
            text=text,
            provenance=Provenance(paper_id=paper.paper_id, block_id="__paper__"),
        )

    def _section_chunks(self, paper: PaperIR) -> list[Chunk]:
        by_section: dict[tuple[str, ...], list[Block]] = defaultdict(list)
        for b in paper.blocks:
            if b.type in ("text", "caption"):
                by_section[tuple(b.section_path)].append(b)
        out: list[Chunk] = []
        for i, (path, blocks) in enumerate(by_section.items()):
            if not path:
                continue
            text = " ".join(b.content for b in blocks)
            out.append(
                Chunk(
                    id=f"{paper.paper_id}:L1:{i}",
                    paper_id=paper.paper_id,
                    level=Granularity.SECTION,
                    text=text,
                    section_path=list(path),
                    provenance=_provenance(paper.paper_id, blocks[0]),
                )
            )
        return out

    def _leaf_chunks(self, paper: PaperIR) -> list[Chunk]:
        out: list[Chunk] = []
        n = 0
        for b in paper.blocks:
            if b.type == "text":
                for piece in _split_text(b.content, self._chunk_tokens):
                    out.append(
                        Chunk(
                            id=f"{paper.paper_id}:L2:{n}",
                            paper_id=paper.paper_id,
                            level=Granularity.CHUNK,
                            text=piece,
                            section_path=b.section_path,
                            provenance=_provenance(paper.paper_id, b),
                        )
                    )
                    n += 1
            elif b.type in ("table", "equation", "figure"):
                content = b.content if b.type != "figure" else (b.caption or b.content)
                out.append(
                    Chunk(
                        id=f"{paper.paper_id}:L3:{b.id}",
                        paper_id=paper.paper_id,
                        level=Granularity.ELEMENT,
                        text=content,
                        section_path=b.section_path,
                        provenance=_provenance(paper.paper_id, b),
                    )
                )
        return out

    async def _add_context(self, paper: PaperIR, chunks: list[Chunk]) -> None:
        """为 L2 chunk 并发生成上下文前缀（就地修改）。无 LLM 时跳过。"""
        if self._llm is None:
            return

        targets = [c for c in chunks if c.level == Granularity.CHUNK]
        sem = asyncio.Semaphore(self._concurrency)

        async def fill(c: Chunk) -> None:
            section = "（" + " / ".join(c.section_path) + "）" if c.section_path else ""
            prompt = _CONTEXT_PROMPT.format(
                title=paper.title, section=section, chunk=c.text
            )
            async with sem:
                try:
                    prefix = await asyncio.wait_for(
                        self._llm.complete(prompt, model=self._model),
                        timeout=self._timeout,
                    )
                except Exception as exc:
                    logger.warning("context prefix failed for %s: %s", c.id, exc)
                    return
            c.context_prefix = prefix.strip()

        await asyncio.gather(*(fill(c) for c in targets))

    async def chunk(self, paper: PaperIR) -> list[Chunk]:
        chunks = [self._paper_chunk(paper), *self._section_chunks(paper), *self._leaf_chunks(paper)]
        await self._add_context(paper, chunks)
        return chunks

"""真实 PDF 解析 adapter：MinerU 版面解析 + GROBID 参考文献，输出 PaperIR。

实现 core.ports.Parser。这是「解析质量决定 RAG 上限」的关键环节（PRD 第 07 章）。
MinerU 把每页切成 block（title/text/equation/table/figure/caption），公式转 LaTeX、
表格转 HTML；GROBID 负责参考文献结构化。

⚠️ MinerU 需 GPU 与模型；GROBID 需独立服务。无法在沙箱里联调。这里给出把 MinerU 的
中间产物归一化到 PaperIR 的映射骨架，真实字段名以所用 MinerU 版本为准。
"""

from __future__ import annotations

import hashlib

from core.ingest.schema import BBox, Block, PaperIR, Reference


class MinerUParser:
    def __init__(self, *, grobid_url: str | None = None) -> None:
        self._grobid_url = grobid_url

    async def parse(self, pdf_bytes: bytes, *, source_hint: str | None = None) -> PaperIR:
        paper_id = hashlib.sha256(pdf_bytes).hexdigest()[:16]
        mineru_doc = await self._run_mineru(pdf_bytes)
        blocks = [self._to_block(paper_id, i, b) for i, b in enumerate(mineru_doc["blocks"])]
        references = await self._parse_references(pdf_bytes)
        meta = mineru_doc.get("meta", {})
        return PaperIR(
            paper_id=paper_id,
            title=meta.get("title", source_hint or paper_id),
            authors=meta.get("authors", []),
            year=meta.get("year"),
            venue=meta.get("venue"),
            abstract=meta.get("abstract", ""),
            blocks=blocks,
            references=references,
        )

    async def _run_mineru(self, pdf_bytes: bytes) -> dict:
        """调用 MinerU 得到结构化中间产物。

        伪代码（真实 API 以 magic_pdf 版本为准）：
            from magic_pdf.pipe.UNIPipe import UNIPipe
            pipe = UNIPipe(pdf_bytes, {"_pdf_type": "", "model_list": []}, image_writer)
            pipe.pipe_classify(); pipe.pipe_analyze(); pipe.pipe_parse()
            return normalize(pipe.pipe_mk_uni_format())
        """
        raise NotImplementedError("接入 MinerU（magic_pdf）：返回 {'blocks': [...], 'meta': {...}}")

    def _to_block(self, paper_id: str, idx: int, b: dict) -> Block:
        """把 MinerU 的一个 block 映射到 PaperIR.Block。"""
        return Block(
            id=f"{paper_id}:b{idx}",
            type=b["type"],  # 已约定为 text/equation/table/figure/caption
            content=b["content"],  # 公式=LaTeX，表格=HTML，图=VLM 描述
            bboxes=[BBox(page=bb["page"], x0=bb["x0"], y0=bb["y0"], x1=bb["x1"], y1=bb["y1"]) for bb in b["bboxes"]],
            section_path=b.get("section_path", []),
            caption=b.get("caption"),
        )

    async def _parse_references(self, pdf_bytes: bytes) -> list[Reference]:
        """GROBID → TEI XML → Reference，再由上层对齐 Semantic Scholar paperId。"""
        if not self._grobid_url:
            return []
        raise NotImplementedError("接入 GROBID processReferences，解析 TEI 为 Reference 列表")

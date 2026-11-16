"""MinerU 云解析 adapter：调用 mineru.net 的精准解析 API，输出 PaperIR。

实现 core.ports.Parser，无需本地 GPU。流程（官方文档 https://mineru.net/apiManage/docs）：
  1. POST /api/v4/file-urls/batch            申请上传链接，得到 batch_id
  2. PUT  <上传链接>                          上传 PDF（不能带 Content-Type，否则签名失效）
  3. GET  /api/v4/extract-results/batch/{id}  轮询直到 state=done
  4. 下载 full_zip_url，读取其中的 *_content_list.json

映射逻辑 `content_list_to_paper_ir` 是纯函数，用真实返回样本做了单测
（tests/fixtures/mineru_content_list_sample.json）。

坐标约定：MinerU 返回的 bbox 已按页面尺寸归一化到 0–1000，这里原样保留；
前端高亮时按「渲染页宽高 / 1000」缩放。页码转成从 1 开始。

Token 从环境变量 SL_MINERU_API_TOKEN 读取（写在 .env 里，不进仓库）。
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
import re
import zipfile

from core.config import settings
from core.ingest.schema import BBox, Block, PaperIR, Reference

# 不进入正文的版面元素
_SKIP_TYPES = {"page_number", "aside_text", "page_footnote", "header", "footer"}
# 章节编号：'2' / '2.1' / '3.2.1'，也兼容附录 'A' / 'A.1'
_SECTION_NO = re.compile(r"^((?:\d+|[A-Z])(?:\.\d+)*)\.?\s+\S")
_YEAR = re.compile(r"\b(19|20)\d{2}\b")
_ARXIV_STAMP = re.compile(r"arXiv:\S+.*?\b((?:19|20)\d{2})\b")


class MinerUError(RuntimeError):
    """MinerU 云 API 返回失败或超时。"""


# --------------------------------------------------------------------------- #
# 纯映射：content_list.json → PaperIR
# --------------------------------------------------------------------------- #


def _bbox(item: dict) -> list[BBox]:
    box = item.get("bbox")
    if not box or len(box) != 4:
        return []
    return [BBox(page=item.get("page_idx", 0) + 1, x0=box[0], y0=box[1], x1=box[2], y1=box[3])]


def _join(parts: list[str] | None) -> str:
    return " ".join(p.strip() for p in (parts or []) if p and p.strip())


def _section_depth(heading: str) -> int:
    """按编号推断层级：'2 METHOD' → 1，'2.1 BACKGROUND' → 2；无编号视为顶层。"""
    m = _SECTION_NO.match(heading)
    return m.group(1).count(".") + 1 if m else 1


def _strip_latex_fence(text: str) -> str:
    return text.strip().removeprefix("$$").removesuffix("$$").strip()


def _reference(index: int, raw: str) -> Reference:
    years = [m.group(0) for m in _YEAR.finditer(raw)]
    year = int(years[-1]) if years else None  # 引文里最后出现的年份通常是发表年
    return Reference(key=f"ref{index}", raw=raw.strip(), year=year)


def content_list_to_paper_ir(
    content_list: list[dict], *, paper_id: str, source_hint: str | None = None
) -> PaperIR:
    """把 MinerU 的 content_list 归一化为 PaperIR。

    - 标题：第一个 text_level == 1 的块
    - 章节路径：由章节标题的编号维护一个层级栈
    - 摘要：'ABSTRACT' 标题下的正文
    - 作者：标题与第一个章节标题之间的文本行（原样保留，不强行拆分人名）
    """
    title = ""
    authors: list[str] = []
    abstract_parts: list[str] = []
    year: int | None = None
    blocks: list[Block] = []
    references: list[Reference] = []

    section_stack: list[str] = []
    seen_title = False
    seen_heading = False
    in_abstract = False

    def add_block(kind: str, content: str, item: dict, caption: str | None = None) -> None:
        if not content.strip():
            return
        blocks.append(
            Block(
                id=f"{paper_id}:b{len(blocks)}",
                type=kind,  # type: ignore[arg-type]
                content=content.strip(),
                bboxes=_bbox(item),
                section_path=list(section_stack),
                caption=caption or None,
            )
        )

    for item in content_list:
        kind = item.get("type", "")

        if kind == "aside_text":
            m = _ARXIV_STAMP.search(item.get("text", ""))
            if m and year is None:
                year = int(m.group(1))
            continue
        if kind in _SKIP_TYPES:
            continue

        if kind == "ref_text":
            references.append(_reference(len(references), item.get("text", "")))
            continue

        if kind == "text":
            text = item.get("text", "").strip()
            if not text:
                continue
            level = item.get("text_level")
            if level == 1 and not seen_title:
                title, seen_title = text, True
                continue
            if level:  # 章节标题
                seen_heading = True
                in_abstract = text.lower() == "abstract"
                if not in_abstract:
                    depth = _section_depth(text)
                    del section_stack[depth - 1 :]
                    section_stack.append(text)
                continue
            if seen_title and not seen_heading:
                authors.append(text)  # 标题之后、首个章节之前：作者 / 单位 / 邮箱
                continue
            if in_abstract:
                abstract_parts.append(text)
                continue
            add_block("text", text, item)

        elif kind == "equation":
            add_block("equation", _strip_latex_fence(item.get("text", "")), item)

        elif kind == "table":
            caption = _join(item.get("table_caption"))
            add_block("table", item.get("table_body", ""), item, caption)

        elif kind in ("chart", "image"):
            caption = _join(item.get(f"{kind}_caption"))
            # 图没有可检索的正文，用图注（或 VLM 描述）作为内容
            add_block("figure", item.get("content") or caption, item, caption)

        elif kind == "code":
            caption = _join(item.get("code_caption"))
            add_block("text", item.get("code_body", ""), item, caption)

    return PaperIR(
        paper_id=paper_id,
        title=title or source_hint or paper_id,
        authors=authors,
        year=year,
        abstract=" ".join(abstract_parts),
        blocks=blocks,
        references=references,
    )


def extract_content_list(zip_bytes: bytes) -> list[dict]:
    """从结果压缩包里取出 *_content_list.json。"""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        names = [n for n in z.namelist() if n.endswith("_content_list.json")]
        if not names:
            raise MinerUError("结果压缩包中没有 content_list.json")
        return json.loads(z.read(names[0]))


# --------------------------------------------------------------------------- #
# API 客户端
# --------------------------------------------------------------------------- #


class MinerUCloudParser:
    def __init__(
        self,
        token: str | None = None,
        *,
        base_url: str | None = None,
        model_version: str | None = None,
        poll_interval: float = 3.0,
        timeout: float = 600.0,
        transport=None,  # 测试时注入 httpx.MockTransport
    ) -> None:
        self._token = token or settings.mineru_api_token
        self._base = (base_url or settings.mineru_api_base).rstrip("/")
        self._model_version = model_version or settings.mineru_model_version
        self._poll_interval = poll_interval
        self._timeout = timeout
        self._transport = transport

    def _headers(self) -> dict[str, str]:
        if not self._token:
            raise MinerUError("未配置 SL_MINERU_API_TOKEN")
        return {"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"}

    @staticmethod
    def _unwrap(resp) -> dict:
        resp.raise_for_status()
        body = resp.json()
        if body.get("code") != 0:
            raise MinerUError(f"MinerU API 错误：{body.get('msg')} (trace_id={body.get('trace_id')})")
        return body["data"]

    async def _submit_and_upload(self, client, pdf_bytes: bytes, name: str) -> str:
        data = self._unwrap(
            await client.post(
                f"{self._base}/api/v4/file-urls/batch",
                headers=self._headers(),
                json={"files": [{"name": name}], "model_version": self._model_version},
            )
        )
        # 上传链接是预签名的：不能附带任何额外 header
        upload = await client.put(data["file_urls"][0], content=pdf_bytes)
        upload.raise_for_status()
        return data["batch_id"]

    async def _wait_for_zip_url(self, client, batch_id: str) -> str:
        waited = 0.0
        while waited < self._timeout:
            data = self._unwrap(
                await client.get(
                    f"{self._base}/api/v4/extract-results/batch/{batch_id}", headers=self._headers()
                )
            )
            result = data["extract_result"][0]
            state = result.get("state")
            if state == "done":
                return result["full_zip_url"]
            if state == "failed":
                raise MinerUError(f"解析失败：{result.get('err_msg')}")
            await asyncio.sleep(self._poll_interval)
            waited += self._poll_interval
        raise MinerUError(f"解析超时（>{self._timeout:.0f}s），batch_id={batch_id}")

    async def parse(self, pdf_bytes: bytes, *, source_hint: str | None = None) -> PaperIR:
        import httpx

        paper_id = hashlib.sha256(pdf_bytes).hexdigest()[:16]
        name = source_hint if source_hint and source_hint.lower().endswith(".pdf") else f"{paper_id}.pdf"
        async with httpx.AsyncClient(
            timeout=120.0, follow_redirects=True, transport=self._transport
        ) as client:
            batch_id = await self._submit_and_upload(client, pdf_bytes, name)
            zip_url = await self._wait_for_zip_url(client, batch_id)
            zip_resp = await client.get(zip_url)
            zip_resp.raise_for_status()
        content_list = extract_content_list(zip_resp.content)
        return content_list_to_paper_ir(content_list, paper_id=paper_id, source_hint=source_hint)

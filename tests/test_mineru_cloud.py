"""MinerU 云解析 adapter：映射逻辑用真实返回样本测，API 流程用 MockTransport 测。"""
import io
import json
import zipfile
from pathlib import Path

import httpx
import pytest

from core import ports
from core.adapters.mineru_cloud import (
    MinerUCloudParser,
    MinerUError,
    content_list_to_paper_ir,
    extract_content_list,
)

SAMPLE = json.loads((Path(__file__).parent / "fixtures" / "mineru_content_list_sample.json").read_text("utf-8"))


@pytest.fixture
def paper():
    return content_list_to_paper_ir(SAMPLE, paper_id="pid")


def test_title_authors_abstract_year(paper):
    assert paper.title.startswith("EXTENDING CONTEXT WINDOW")
    assert any("Shouyuan Chen" in a for a in paper.authors)
    assert paper.abstract.startswith("We present Position Interpolation")
    assert paper.year == 2023  # 来自页边的 arXiv 戳


def test_layout_noise_is_dropped(paper):
    texts = [b.content for b in paper.blocks]
    assert not any(t.startswith("arXiv:") for t in texts)   # 页边栏
    assert "1" not in texts                                   # 页码
    assert "ABSTRACT" not in texts                            # 标题不作为正文块


def test_section_path_follows_numbering(paper):
    intro = next(b for b in paper.blocks if b.content.startswith("Large language models"))
    assert intro.section_path == ["1 INTRODUCTION"]
    nested = [b.section_path for b in paper.blocks if len(b.section_path) == 2]
    assert nested and all(p[0].startswith("2 ") and p[1].startswith("2.") for p in nested)


def test_blocks_keep_page_and_normalized_bbox(paper):
    for b in paper.blocks:
        assert b.bboxes, b.id
        box = b.bboxes[0]
        assert box.page >= 1
        assert 0 <= box.x0 < box.x1 <= 1000 and 0 <= box.y0 < box.y1 <= 1000


def test_equation_table_figure_mapping(paper):
    kinds = {b.type for b in paper.blocks}
    assert {"text", "equation", "table", "figure"} <= kinds
    eq = next(b for b in paper.blocks if b.type == "equation")
    assert not eq.content.startswith("$$")
    table = next(b for b in paper.blocks if b.type == "table")
    assert table.content.startswith("<table>") and "Table 1" in (table.caption or "")
    fig = next(b for b in paper.blocks if b.type == "figure")
    assert "Figure 1" in fig.content


def test_references_extracted(paper):
    assert len(paper.references) == 3
    assert paper.references[0].raw.startswith("Joshua Ainslie")
    assert all(r.year for r in paper.references)


# ---- API 流程 ----

def _zip_with(content_list) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("abc_content_list.json", json.dumps(content_list))
        z.writestr("full.md", "# x")
    return buf.getvalue()


def _transport(states, *, submit_code=0):
    calls = {"poll": 0, "upload_headers": None}

    def handler(req: httpx.Request) -> httpx.Response:
        url = str(req.url)
        if url.endswith("/api/v4/file-urls/batch"):
            assert req.headers["authorization"] == "Bearer tok"
            return httpx.Response(200, json={"code": submit_code, "msg": "ok" if submit_code == 0 else "bad token",
                                             "data": {"batch_id": "B1", "file_urls": ["https://upload.example/put"]}})
        if url == "https://upload.example/put":
            calls["upload_headers"] = dict(req.headers)
            return httpx.Response(200)
        if url.endswith("/api/v4/extract-results/batch/B1"):
            state = states[min(calls["poll"], len(states) - 1)]
            calls["poll"] += 1
            return httpx.Response(200, json={"code": 0, "msg": "ok", "data": {"extract_result": [
                {"state": state, "full_zip_url": "https://cdn.example/r.zip", "err_msg": "boom"}]}})
        if url == "https://cdn.example/r.zip":
            return httpx.Response(200, content=_zip_with(SAMPLE))
        return httpx.Response(404)

    return httpx.MockTransport(handler), calls


async def test_parse_full_flow_polls_until_done():
    transport, calls = _transport(["pending", "running", "done"])
    parser = MinerUCloudParser("tok", poll_interval=0, transport=transport)
    paper = await parser.parse(b"%PDF-fake", source_hint="pi.pdf")
    assert calls["poll"] == 3
    assert paper.title.startswith("EXTENDING CONTEXT WINDOW")
    assert len(paper.paper_id) == 16
    # 预签名上传不能带鉴权或 Content-Type
    assert "authorization" not in calls["upload_headers"]
    assert "content-type" not in calls["upload_headers"]


async def test_parse_raises_on_failed_state():
    transport, _ = _transport(["failed"])
    with pytest.raises(MinerUError, match="boom"):
        await MinerUCloudParser("tok", poll_interval=0, transport=transport).parse(b"x")


async def test_parse_raises_on_api_error_code():
    transport, _ = _transport(["done"], submit_code=-1)
    with pytest.raises(MinerUError, match="bad token"):
        await MinerUCloudParser("tok", poll_interval=0, transport=transport).parse(b"x")


async def test_missing_token_is_reported(monkeypatch):
    from core.adapters import mineru_cloud
    monkeypatch.setattr(mineru_cloud.settings, "mineru_api_token", None)
    with pytest.raises(MinerUError, match="SL_MINERU_API_TOKEN"):
        await MinerUCloudParser(transport=_transport(["done"])[0]).parse(b"x")


def test_zip_without_content_list_raises():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("full.md", "x")
    with pytest.raises(MinerUError):
        extract_content_list(buf.getvalue())


def test_satisfies_parser_port():
    assert isinstance(MinerUCloudParser("tok"), ports.Parser)

import pytest

from core.ingest.schema import BBox, Block, PaperIR, Reference


@pytest.fixture
def paper() -> PaperIR:
    """一篇用于测试的小论文 IR：含正文、表格、公式、跨章节结构。"""
    return PaperIR(
        paper_id="p1",
        title="YaRN: Efficient Context Window Extension",
        authors=["Peng et al."],
        year=2023,
        venue="ICLR",
        abstract="We extend the context window of large language models via frequency-aware interpolation.",
        blocks=[
            Block(
                id="b1", type="text",
                content="Position Interpolation linearly compresses position indices. "
                        "It requires a small amount of fine-tuning to recover performance.",
                bboxes=[BBox(page=4, x0=0, y0=0, x1=1, y1=1)],
                section_path=["3 Method", "3.1 Position Interpolation"],
                refs=["chen2023pi"],
            ),
            Block(
                id="b2", type="text",
                content="YaRN interpolates by frequency bands and reaches lower perplexity at 128K. "
                        "It needs only about 0.1% of the pretraining data to fine-tune.",
                bboxes=[BBox(page=6, x0=0, y0=0, x1=1, y1=1)],
                section_path=["3 Method", "3.2 Frequency-aware Interpolation"],
            ),
            Block(
                id="t1", type="table",
                content="<table><tr><td>YaRN</td><td>128K</td><td>3.2</td></tr></table>",
                caption="Table 3: Perplexity at 128K",
                bboxes=[BBox(page=6, x0=0, y0=0, x1=1, y1=1)],
                section_path=["4 Experiments"],
            ),
        ],
        references=[Reference(key="chen2023pi", raw="Chen et al. 2023", title="Position Interpolation")],
    )


@pytest.fixture
def auth():
    """返回一个函数：给定 TestClient 和用户名，注册并返回带 JWT 的请求头。"""
    def _make(client, username="demo", password="pw"):
        r = client.post("/auth/register", json={"username": username, "password": password})
        if r.status_code == 409:
            r = client.post("/auth/login", json={"username": username, "password": password})
        return {"Authorization": f"Bearer {r.json()['access_token']}"}
    return _make

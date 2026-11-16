"""论文登记、collection 分组、PDF 存取。"""
import io
import pytest
from fastapi.testclient import TestClient

from apps.api.deps import get_container
from apps.api.main import app


@pytest.fixture
def client(paper):
    get_container.cache_clear()
    c = get_container()
    # 装一个假 parser，让 /ingest 能解析任意上传
    from core.adapters.fakes import FakeParser
    c.parser = FakeParser(paper)
    return TestClient(app)


def _pdf_upload(client, auth, collection="long-context"):
    h = auth(client, "pu")
    return client.post("/ingest/upload",
                       files={"files": ("paper.pdf", io.BytesIO(b"%PDF-fake"), "application/pdf")},
                       data={"collection": collection}, headers=h), h


def test_ingest_registers_paper_and_collection(client, auth):
    r, h = _pdf_upload(client, auth)
    assert r.status_code == 200
    body = r.json()[0]
    assert body["collection"] == "long-context" and body["n_chunks"] > 0
    # 列表与分组
    papers = client.get("/papers", headers=h).json()
    assert any(p["title"].startswith("YaRN") for p in papers)
    cols = client.get("/papers/collections", headers=h).json()
    assert {"name": "long-context", "count": 1} in cols


def test_pdf_served_back(client, auth):
    r, h = _pdf_upload(client, auth)
    pid = r.json()[0]["paper_id"]
    pdf = client.get(f"/papers/{pid}/pdf", headers=h)
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content == b"%PDF-fake"


def test_pdf_404_when_missing(client, auth):
    h = auth(client, "pu")
    assert client.get("/papers/nope/pdf", headers=h).status_code == 404

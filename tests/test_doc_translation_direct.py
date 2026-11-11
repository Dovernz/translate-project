import pytest
import io
import os
from pathlib import Path
from docx import Document
from httpx import AsyncClient, ASGITransport

from app import app, DOCS_OUTPUT_DIR
from core.document_helper import get_document_preview, translate_document

@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.mark.anyio
async def test_extract_txt(client):
    content = b"Xin chao the gioi. Day la van ban kiem thu document translation."
    files = {'file': ('sample.txt', content, 'text/plain')}
    res = await client.post("/api/document/extract", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["format"] == "txt"
    assert "Xin chao" in data["text"]

@pytest.mark.anyio
async def test_extract_docx(client):
    doc = Document()
    doc.add_heading("Tieu de tai lieu test", level=1)
    doc.add_paragraph("Doan van ban mau so 1.")
    table = doc.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "Cot A"
    table.cell(0, 1).text = "Cot B"
    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)

    files = {'file': ('sample.docx', bio.getvalue(), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
    res = await client.post("/api/document/extract", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["format"] == "docx"
    assert "Tieu de tai lieu test" in data["text"]
    assert "Cot A" in data["text"]

@pytest.mark.anyio
async def test_extract_srt(client):
    srt = (
        "1\n00:00:01,000 --> 00:00:03,000\nHello world\n\n"
        "2\n00:00:04,000 --> 00:00:06,000\nGeminiTrans Format Preservation\n"
    ).encode("utf-8")
    files = {'file': ('sample.srt', srt, 'text/plain')}
    res = await client.post("/api/document/extract", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["format"] == "srt"
    assert "Hello world" in data["text"]
    assert "GeminiTrans" in data["text"]

@pytest.mark.anyio
async def test_download_endpoint(client):
    test_id = "test_doc_123"
    test_folder = DOCS_OUTPUT_DIR / test_id
    test_folder.mkdir(parents=True, exist_ok=True)
    sample_file = test_folder / "test_out.docx"
    sample_file.write_bytes(b"PK0304_MOCK_DOCX_CONTENT")

    res = await client.get(f"/api/document/download/{test_id}/test_out.docx")
    assert res.status_code == 200
    assert res.content == b"PK0304_MOCK_DOCX_CONTENT"

@pytest.mark.anyio
async def test_document_helper_preview_direct():
    res = get_document_preview("test.txt", b"Direct preview text test")
    assert res["format"] == "txt"
    assert "Direct preview" in res["text"]

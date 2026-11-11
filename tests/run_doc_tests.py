import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
import io
import os
from docx import Document
from httpx import AsyncClient, ASGITransport

from app import app, DOCS_OUTPUT_DIR
from core.document_helper import get_document_preview

async def main():
    print("=== STARTING DOCUMENT TRANSLATION SUITE ===")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Test 1: extract txt
        content = b"Xin chao the gioi. Day la van ban kiem thu document translation."
        files = {'file': ('sample.txt', content, 'text/plain')}
        res = await client.post("/api/document/extract", files=files)
        assert res.status_code == 200, f"TXT status {res.status_code}"
        data = res.json()
        assert data["format"] == "txt"
        assert "Xin chao" in data["text"]
        print("[PASS] Test 1: Extract TXT successful")

        # Test 2: extract docx
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
        assert res.status_code == 200, f"DOCX status {res.status_code}"
        data = res.json()
        assert data["format"] == "docx"
        assert "Tieu de tai lieu test" in data["text"]
        assert "Cot A" in data["text"]
        print("[PASS] Test 2: Extract DOCX (paragraphs + tables) successful")

        # Test 3: extract srt
        srt = (
            "1\n00:00:01,000 --> 00:00:03,000\nHello world\n\n"
            "2\n00:00:04,000 --> 00:00:06,000\nGeminiTrans Format Preservation\n"
        ).encode("utf-8")
        files = {'file': ('sample.srt', srt, 'text/plain')}
        res = await client.post("/api/document/extract", files=files)
        assert res.status_code == 200, f"SRT status {res.status_code}"
        data = res.json()
        assert data["format"] == "srt"
        assert "Hello world" in data["text"]
        print("[PASS] Test 3: Extract SRT successful")

        # Test 4: download endpoint
        test_id = "test_doc_123"
        test_folder = DOCS_OUTPUT_DIR / test_id
        test_folder.mkdir(parents=True, exist_ok=True)
        sample_file = test_folder / "test_out.docx"
        sample_file.write_bytes(b"PK0304_MOCK_DOCX_CONTENT")

        res = await client.get(f"/api/document/download/{test_id}/test_out.docx")
        assert res.status_code == 200, f"Download status {res.status_code}"
        assert res.content == b"PK0304_MOCK_DOCX_CONTENT"
        print("[PASS] Test 4: Download translated document successful")

        # Test 5: direct preview helper
        preview = get_document_preview("test.md", b"# Markdown Header\nSome markdown text")
        assert preview["format"] == "md"
        assert "Markdown Header" in preview["text"]
        print("[PASS] Test 5: Direct get_document_preview successful")

    print("\n>>> ALL 5 TESTS PASSED WITH 100% SUCCESS! <<<")

if __name__ == "__main__":
    asyncio.run(main())

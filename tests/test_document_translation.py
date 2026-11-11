import pytest
import io
import os
import shutil
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from docx import Document

# Giả định cấu trúc thư mục và import từ app.py
from app import app
from core.document_helper import DocumentHelper
from config import DOCS_OUTPUT_DIR

@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.fixture(autouse=True)
def setup_teardown_docs_dir():
    # Tạo thư mục output tạm thời cho test
    os.makedirs(DOCS_OUTPUT_DIR, exist_ok=True)
    yield
    # Clean up sau khi test xong (tùy chọn)
    # shutil.rmtree(DOCS_OUTPUT_DIR)

@pytest.mark.anyio
async def test_document_extract_txt(client):
    content = b"Hello, this is a test document content."
    files = {'file': ('test.txt', content, 'text/plain')}
    
    response = await client.post("/api/document/extract", files=files)
    
    assert response.status_code == 200
    data = response.json()
    assert data["format"] == "txt"
    assert "Hello" in data["preview_text"]
    assert data["preview_text"] != ""

@pytest.mark.anyio
async def test_document_extract_docx(client):
    # Tạo file docx mẫu trong bộ nhớ
    doc = Document()
    doc.add_paragraph("This is a test paragraph.")
    table = doc.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "Cell 1"
    table.cell(0, 1).text = "Cell 2"
    
    docx_io = io.BytesIO()
    doc.save(docx_io)
    docx_io.seek(0)
    
    files = {'file': ('test.docx', docx_io, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
    
    response = await client.post("/api/document/extract", files=files)
    
    assert response.status_code == 200
    data = response.json()
    assert data["format"] == "docx"
    assert "test paragraph" in data["preview_text"]
    assert "Cell 1" in data["preview_text"]

@pytest.mark.anyio
async def test_document_extract_srt(client):
    srt_content = (
        "1\n"
        "00:00:01,000 --> 00:00:04,000\n"
        "Hello world!\n\n"
        "2\n"
        "00:00:05,000 --> 00:00:08,000\n"
        "Testing SRT extraction."
    ).encode('utf-8')
    
    files = {'file': ('test.srt', srt_content, 'application/x-subrip')}
    
    response = await client.post("/api/document/extract", files=files)
    
    assert response.status_code == 200
    data = response.json()
    assert data["format"] == "srt"
    assert "Hello world" in data["preview_text"]
    assert "Testing SRT" in data["preview_text"]

@pytest.mark.anyio
async def test_document_translate_docx_structure():
    # Mock hàm dịch của Gemini để trả về text cố định
    async def mock_translate_text(text, *args, **kwargs):
        return f"Dịch: {text}"

    # Tạo file docx gốc
    doc = Document()
    doc.add_paragraph("Original Paragraph")
    table = doc.add_table(rows=1, cols=1)
    table.cell(0, 0).text = "Original Table Cell"
    
    input_io = io.BytesIO()
    doc.save(input_io)
    input_io.seek(0)
    
    # Giả lập quá trình dịch document
    with patch('core.gemini_client.GeminiClient.generate_content', side_effect=mock_translate_text):
        # Giả sử DocumentHelper.translate_docx xử lý logic này
        output_io = await DocumentHelper.translate_docx(input_io, target_lang="Vietnamese")
        
        # Kiểm tra file kết quả
        output_io.seek(0)
        translated_doc = Document(output_io)
        
        # Kiểm tra cấu trúc: vẫn còn 1 paragraph và 1 table
        assert len(translated_doc.paragraphs) >= 1
        assert len(translated_doc.tables) == 1
        assert "Dịch:" in translated_doc.paragraphs[0].text
        assert "Dịch:" in translated_doc.tables[0].cell(0, 0).text

@pytest.mark.anyio
async def test_document_translate_srt_structure():
    srt_content = "1\n00:00:01,000 --> 00:00:02,000\nHello\n"
    
    async def mock_translate_text(text, *args, **kwargs):
        return "Xin chào"

    with patch('core.gemini_client.GeminiClient.generate_content', side_effect=mock_translate_text):
        translated_srt = await DocumentHelper.translate_srt(srt_content, target_lang="Vietnamese")
        
        # Kiểm tra timestamp và index được bảo toàn
        assert "1" in translated_srt
        assert "00:00:01,000 --> 00:00:02,000" in translated_srt
        assert "Xin chào" in translated_srt

@pytest.mark.anyio
async def test_document_translate_markdown_code_protection():
    md_content = "Here is code:\n```python\nprint('hello')\n```\nEnd."
    
    # Mock translator: chỉ dịch text, không chạm vào code block (giả định logic của helper)
    async def mock_translate_text(text, *args, **kwargs):
        if "print" in text: return text # Giả lập logic không dịch code
        return "Đây là code:"

    with patch('core.gemini_client.GeminiClient.generate_content', side_effect=mock_translate_text):
        translated_md = await DocumentHelper.translate_markdown(md_content, target_lang="Vietnamese")
        
        assert "```python" in translated_md
        assert "print('hello')" in translated_md
        assert "```" in translated_md

@pytest.mark.anyio
async def test_document_download_endpoint(client):
    test_id = "test_session_123"
    filename = "translated_test.docx"
    
    # Tạo đường dẫn giả lập
    session_dir = Path(DOCS_OUTPUT_DIR) / test_id
    session_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = session_dir / filename
    with open(file_path, "wb") as f:
        f.write(b"fake docx content")
    
    # Gọi API download
    response = await client.get(f"/api/document/download/{test_id}/{filename}")
    
    assert response.status_code == 200
    assert response.content == b"fake docx content"
    assert response.headers["content-type"] == "application/octet-stream"
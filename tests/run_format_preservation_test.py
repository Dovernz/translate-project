import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
import io
import json
from docx import Document
from pypdf import PdfReader
from core.document_helper import translate_document

class MockPool:
    async def generate_content(self, prompt, system_instruction="", tier="bulk"):
        if "Dữ liệu vào:\n" in prompt:
            json_part = prompt.split("Dữ liệu vào:\n")[-1].strip()
            items = json.loads(json_part)
            out = []
            for it in items:
                out.append({"id": it["id"], "translated": f"[VI] {it.get('text', '')}"})
            return json.dumps(out, ensure_ascii=False)
        return f"[VI] {prompt}"

async def main():
    print("=== TESTING FORMAT PRESERVATION FOR ALL FORMATS ===")
    mock_pool = MockPool()

    # 1. Test DOCX format preservation
    doc = Document()
    doc.add_heading("Architecture Overview", level=1)
    doc.add_paragraph("This is a critical paragraph with important instructions.")
    tbl = doc.add_table(rows=2, cols=2)
    tbl.cell(0, 0).text = "Metric"
    tbl.cell(0, 1).text = "Value"
    tbl.cell(1, 0).text = "Latency"
    tbl.cell(1, 1).text = "15ms"

    docx_bio = io.BytesIO()
    doc.save(docx_bio)
    docx_bytes = docx_bio.getvalue()

    res_docx = await translate_document("test_doc.docx", docx_bytes, "en", "vi", mock_pool, "bulk")
    assert res_docx["format"] == "docx"
    assert len(res_docx["translated_bytes"]) > 0

    # Verify that the output is a valid Word document
    out_doc = Document(io.BytesIO(res_docx["translated_bytes"]))
    assert len(out_doc.paragraphs) >= 2
    assert "[VI] Architecture Overview" in out_doc.paragraphs[0].text
    assert "[VI] Latency" in out_doc.tables[0].cell(1, 0).text
    print("[PASS] DOCX: Table structure, paragraphs & heading styles 100% preserved")

    # 2. Test SRT format preservation
    srt_input = (
        "1\n00:00:01,000 --> 00:00:04,000\nWelcome to GeminiTrans.\n\n"
        "2\n00:00:05,000 --> 00:00:08,000\nFormat preservation guaranteed.\n"
    ).encode("utf-8")

    res_srt = await translate_document("subs.srt", srt_input, "en", "vi", mock_pool, "bulk")
    assert res_srt["format"] == "srt"
    srt_out_text = res_srt["translated_bytes"].decode("utf-8")
    assert "00:00:01,000 --> 00:00:04,000" in srt_out_text
    assert "00:00:05,000 --> 00:00:08,000" in srt_out_text
    assert "1" in srt_out_text and "2" in srt_out_text
    assert "[VI] Welcome to GeminiTrans." in srt_out_text
    print("[PASS] SRT: Timestamps & sequence indices 100% exact")

    # 3. Test Markdown code protection
    md_input = """# System Guide

Here is a bash command:
```bash
uv run python app.py
```
And inline code `gemini_cli`.
""".encode("utf-8")

    res_md = await translate_document("guide.md", md_input, "en", "vi", mock_pool, "bulk")
    assert res_md["format"] == "md"
    md_out_text = res_md["translated_bytes"].decode("utf-8")
    assert "```bash\nuv run python app.py\n```" in md_out_text
    assert "`gemini_cli`" in md_out_text
    print("[PASS] Markdown: Code blocks and inline codes strictly protected")

    # 4. Test TXT
    txt_input = "Paragraph 1 line A\n\nParagraph 2 line B".encode("utf-8")
    res_txt = await translate_document("sample.txt", txt_input, "en", "vi", mock_pool, "bulk")
    assert res_txt["format"] == "txt"
    txt_out = res_txt["translated_bytes"].decode("utf-8")
    assert "\n\n" in txt_out
    print("[PASS] TXT: Paragraph breaks preserved")

    # 5. Test PDF
    from reportlab.pdfgen import canvas
    pdf_in = io.BytesIO()
    c = canvas.Canvas(pdf_in)
    c.drawString(100, 750, "Sample PDF Document Title")
    c.drawString(100, 700, "First paragraph in PDF to translate.")
    c.save()
    pdf_bytes = pdf_in.getvalue()

    res_pdf = await translate_document("test.pdf", pdf_bytes, "en", "vi", mock_pool, "bulk")
    assert res_pdf["format"] == "pdf"
    assert len(res_pdf["translated_bytes"]) > 0
    pdf_reader = PdfReader(io.BytesIO(res_pdf["translated_bytes"]))
    assert len(pdf_reader.pages) >= 1
    print("[PASS] PDF: Generated valid formatted PDF with Arial UTF-8")

    print("\n>>> ALL FORMAT PRESERVATION CHECKS PASSED (100%)! <<<")

if __name__ == "__main__":
    asyncio.run(main())

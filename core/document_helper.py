"""
Module hỗ trợ dịch tài liệu cho dự án GeminiTrans.
Tương thích Python 3.14+, hỗ trợ dịch và bảo toàn định dạng (Format-Preserving)
cho các tệp DOCX, SRT, Markdown, TXT và PDF.
"""

import io
import os
import re
import json
import html
import inspect
from typing import Callable, Any, Optional

import docx
import pypdf
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ==========================================
# HELPER FUNCTIONS & UTILS
# ==========================================

async def _notify_progress(
    callback: Optional[Callable],
    percent: float,
    message: str,
    preview_chunk: str = ""
) -> None:
    """Gọi callback tiến độ an toàn hỗ trợ cả sync và async function."""
    if callback is None:
        return
    try:
        if inspect.iscoroutinefunction(callback):
            await callback(percent, message, preview_chunk)
        else:
            res = callback(percent, message, preview_chunk)
            if inspect.isawaitable(res):
                await res
    except Exception:
        pass


def _decode_bytes(file_bytes: bytes) -> str:
    """Giải mã file bytes sang string với fallback latin-1."""
    try:
        return file_bytes.decode('utf-8')
    except UnicodeDecodeError:
        return file_bytes.decode('latin-1', errors='replace')


async def _call_generate_content(
    pool: Any,
    prompt: str,
    system_instruction: str,
    tier: str
) -> str:
    """Gọi pool.generate_content an toàn hỗ trợ cả sync/async return."""
    res = pool.generate_content(prompt, system_instruction=system_instruction, tier=tier)
    if inspect.isawaitable(res):
        res = await res
    if hasattr(res, 'text'):
        return str(res.text)
    return str(res)


def _clean_and_parse_json(raw_response: str) -> list[dict]:
    """Bóc tách và parse mảng JSON từ phản hồi của model."""
    cleaned = raw_response.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    
    try:
        res = json.loads(cleaned)
        if isinstance(res, list):
            return res
    except json.JSONDecodeError:
        pass

    # Regex fallback tìm đoạn chứa mảng JSON [...]
    match = re.search(r'\[\s*\{.*\}\s*\]', cleaned, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    
    raise ValueError("Không thể trích xuất mảng JSON hợp lệ từ phản hồi.")


# ==========================================
# BATCH TRANSLATION CORE
# ==========================================

async def _batch_translate_texts(
    texts: list[str],
    source_lang: str,
    target_lang: str,
    pool: Any,
    tier: str = "bulk",
    progress_callback: Optional[Callable] = None,
    start_pct: float = 10.0,
    end_pct: float = 90.0
) -> list[str]:
    """Dịch danh sách văn bản theo các batch nhỏ (15-20 câu/batch)."""
    if not texts:
        return []

    batch_size = 15
    batches = [texts[i:i + batch_size] for i in range(0, len(texts), batch_size)]
    translated_texts: list[str] = []
    total_batches = len(batches)

    system_instruction = (
        "Bạn là dịch giả tài liệu chuyên nghiệp. Chỉ trả về duy nhất mảng JSON "
        "đã dịch theo đúng định dạng được yêu cầu, không thêm bất kỳ văn bản nào khác."
    )

    for idx, batch in enumerate(batches):
        payload = [{"id": i, "text": text} for i, text in enumerate(batch)]
        json_input = json.dumps(payload, ensure_ascii=False)

        prompt = (
            f"Dịch các đoạn văn bản sau từ ngôn ngữ '{source_lang}' sang '{target_lang}'.\n"
            f"Giữ nguyên cấu trúc ID và trả về DUY NHẤT một mảng JSON có định dạng:\n"
            f'[{{\"id\": 0, \"translated\": \"...\"}}, ...]\n\n'
            f"Dữ liệu vào:\n{json_input}"
        )

        batch_translated = list(batch)  # Fallback mặc định là văn bản gốc

        try:
            response_text = await _call_generate_content(
                pool=pool,
                prompt=prompt,
                system_instruction=system_instruction,
                tier=tier
            )
            parsed_data = _clean_and_parse_json(response_text)
            
            # Khôi phục kết quả theo ID
            id_map = {item["id"]: item.get("translated", "") for item in parsed_data if "id" in item}
            for i in range(len(batch)):
                if i in id_map and id_map[i]:
                    batch_translated[i] = id_map[i]

        except Exception as e:
            # Nếu gặp lỗi ở batch, giữ nguyên văn bản gốc
            pass

        translated_texts.extend(batch_translated)

        # Tiến độ
        current_pct = start_pct + ((idx + 1) / total_batches) * (end_pct - start_pct)
        preview = batch_translated[0][:100] if batch_translated else ""
        msg = f"Đã dịch batch {idx + 1}/{total_batches}"
        await _notify_progress(progress_callback, current_pct, msg, preview)

    return translated_texts


# ==========================================
# FORMAT HANDLERS
# ==========================================

async def _translate_docx(
    file_bytes: bytes,
    source_lang: str,
    target_lang: str,
    pool: Any,
    tier: str,
    progress_callback: Optional[Callable]
) -> tuple[bytes, list[str]]:
    """Xử lý và dịch file Microsoft Word (.docx)."""
    doc = docx.Document(io.BytesIO(file_bytes))
    target_paragraphs = []

    # 1. Đoạn văn chính
    for p in doc.paragraphs:
        if p.text.strip():
            target_paragraphs.append(p)

    # 2. Bảng biểu
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    if p.text.strip():
                        target_paragraphs.append(p)

    # 3. Header & Footer
    for section in doc.sections:
        for container in [section.header, section.footer]:
            if container and not container.is_linked_to_previous:
                for p in container.paragraphs:
                    if p.text.strip():
                        target_paragraphs.append(p)
                for table in container.tables:
                    for row in table.rows:
                        for cell in row.cells:
                            for p in cell.paragraphs:
                                if p.text.strip():
                                    target_paragraphs.append(p)

    source_texts = [p.text for p in target_paragraphs]
    translated_texts = await _batch_translate_texts(
        source_texts, source_lang, target_lang, pool, tier, progress_callback, 10.0, 90.0
    )

    # Ghi đè kết quả dịch nhưng giữ trọn vẹn style ở Run đầu tiên
    for para, trans_text in zip(target_paragraphs, translated_texts):
        if para.runs:
            para.runs[0].text = trans_text
            for r in para.runs[1:]:
                r.text = ""
        else:
            para.text = trans_text

    out_io = io.BytesIO()
    doc.save(out_io)
    return out_io.getvalue(), translated_texts


async def _translate_srt(
    file_bytes: bytes,
    source_lang: str,
    target_lang: str,
    pool: Any,
    tier: str,
    progress_callback: Optional[Callable]
) -> tuple[bytes, list[str]]:
    """Xử lý và dịch file phụ đề SubRip (.srt)."""
    content = _decode_bytes(file_bytes)
    # Tách các block SRT chuẩn
    blocks = re.split(r'\n\s*\n', content.strip().replace('\r\n', '\n'))
    
    parsed_blocks = []
    sub_texts = []

    srt_pattern = re.compile(r'^(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3})\n([\s\S]+)$')

    for block in blocks:
        match = srt_pattern.match(block.strip())
        if match:
            idx, timestamp, text = match.groups()
            parsed_blocks.append({'type': 'srt', 'index': idx, 'timestamp': timestamp, 'text': text})
            sub_texts.append(text)
        else:
            parsed_blocks.append({'type': 'raw', 'raw': block})

    translated_texts = await _batch_translate_texts(
        sub_texts, source_lang, target_lang, pool, tier, progress_callback, 10.0, 90.0
    )

    out_blocks = []
    trans_idx = 0
    for block in parsed_blocks:
        if block['type'] == 'srt':
            trans_val = translated_texts[trans_idx] if trans_idx < len(translated_texts) else block['text']
            out_blocks.append(f"{block['index']}\n{block['timestamp']}\n{trans_val}")
            trans_idx += 1
        else:
            out_blocks.append(block['raw'])

    res_srt = "\n\n".join(out_blocks)
    return res_srt.encode('utf-8'), translated_texts


async def _translate_markdown(
    file_bytes: bytes,
    source_lang: str,
    target_lang: str,
    pool: Any,
    tier: str,
    progress_callback: Optional[Callable]
) -> tuple[bytes, list[str]]:
    """Xử lý và dịch file Markdown (.md) có bảo toàn các khối code."""
    content = _decode_bytes(file_bytes)
    
    # Tách và bảo vệ khối code ```...``` và inline code `...`
    code_placeholders = {}
    
    def mask_code(match):
        key = f"___CODE_BLOCK_{len(code_placeholders)}___"
        code_placeholders[key] = match.group(0)
        return key

    # Mask code blocks trước, sau đó mask inline code
    masked_content = re.sub(r'```[\s\S]*?```', mask_code, content)
    masked_content = re.sub(r'`[^`\n]+`', mask_code, masked_content)

    # Tách đoạn văn để dịch
    paragraphs = masked_content.split('\n\n')
    non_empty_paras = [p for p in paragraphs if p.strip()]

    translated_paras = await _batch_translate_texts(
        non_empty_paras, source_lang, target_lang, pool, tier, progress_callback, 10.0, 90.0
    )

    # Ghép lại văn bản đã dịch
    trans_map = dict(zip(non_empty_paras, translated_paras))
    reconstructed = []
    for p in paragraphs:
        if p in trans_map:
            reconstructed.append(trans_map[p])
        else:
            reconstructed.append(p)

    out_text = "\n\n".join(reconstructed)

    # Khôi phục các khối code nguyên bản
    for key, original_code in code_placeholders.items():
        out_text = out_text.replace(key, original_code)

    return out_text.encode('utf-8'), translated_paras


async def _translate_txt(
    file_bytes: bytes,
    source_lang: str,
    target_lang: str,
    pool: Any,
    tier: str,
    progress_callback: Optional[Callable]
) -> tuple[bytes, list[str]]:
    """Xử lý và dịch file văn bản thuần (.txt)."""
    content = _decode_bytes(file_bytes)
    paragraphs = re.split(r'\n\n+', content)
    non_empty_paras = [p.strip() for p in paragraphs if p.strip()]

    translated_paras = await _batch_translate_texts(
        non_empty_paras, source_lang, target_lang, pool, tier, progress_callback, 10.0, 90.0
    )

    trans_map = dict(zip(non_empty_paras, translated_paras))
    out_paras = [trans_map.get(p.strip(), p) for p in paragraphs]
    
    out_text = "\n\n".join(out_paras)
    return out_text.encode('utf-8'), translated_paras


async def _translate_pdf(
    file_bytes: bytes,
    source_lang: str,
    target_lang: str,
    pool: Any,
    tier: str,
    progress_callback: Optional[Callable]
) -> tuple[bytes, list[str]]:
    """Xử lý PDF, đọc text từng trang và tái tạo PDF đầu ra bằng ReportLab."""
    reader = pypdf.PdfReader(io.BytesIO(file_bytes))
    raw_texts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            raw_texts.append(text)

    full_text = "\n\n".join(raw_texts)
    paragraphs = [p.strip() for p in re.split(r'\n\n+', full_text) if p.strip()]

    translated_paras = await _batch_translate_texts(
        paragraphs, source_lang, target_lang, pool, tier, progress_callback, 10.0, 85.0
    )

    # Đăng ký Font Arial để hỗ trợ Tiếng Việt 100%
    font_name = "Helvetica"
    font_path = "C:/Windows/Fonts/arial.ttf"
    if os.path.exists(font_path):
        try:
            pdfmetrics.registerFont(TTFont('Arial', font_path))
            font_name = 'Arial'
        except Exception:
            pass

    out_io = io.BytesIO()
    doc_pdf = SimpleDocTemplate(
        out_io,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    custom_style = ParagraphStyle(
        'PDFBody',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10,
        leading=14
    )

    story = []
    for text_item in translated_paras:
        safe_text = html.escape(text_item).replace('\n', '<br/>')
        story.append(Paragraph(safe_text, custom_style))
        story.append(Spacer(1, 8))

    doc_pdf.build(story)
    await _notify_progress(progress_callback, 95.0, "Đã khởi tạo PDF hoàn tất")
    
    return out_io.getvalue(), translated_paras


# ==========================================
# MAIN ENTRY POINT
# ==========================================

async def translate_document(
    filename: str,
    file_bytes: bytes,
    source_lang: str,
    target_lang: str,
    pool: Any,
    tier: str = "bulk",
    progress_callback: Optional[Callable] = None
) -> dict:
    """
    Hàm chính dịch tài liệu chuyên nghiệp cho GeminiTrans.

    Returns dict:
        {
            "translated_bytes": bytes,
            "out_filename": str,
            "preview_text": str,
            "format": str,
            "char_count": int,
            "paragraph_count": int
        }
    """
    await _notify_progress(progress_callback, 5.0, f"Đang chuẩn bị dịch '{filename}'...")

    ext = os.path.splitext(filename)[1].lower().strip('.')
    base_name = os.path.splitext(filename)[0]
    out_filename = f"{base_name}_translated.{ext}"

    translated_bytes = b""
    translated_segments = []

    if ext == "docx":
        translated_bytes, translated_segments = await _translate_docx(
            file_bytes, source_lang, target_lang, pool, tier, progress_callback
        )
    elif ext == "srt":
        translated_bytes, translated_segments = await _translate_srt(
            file_bytes, source_lang, target_lang, pool, tier, progress_callback
        )
    elif ext in ["md", "markdown"]:
        translated_bytes, translated_segments = await _translate_markdown(
            file_bytes, source_lang, target_lang, pool, tier, progress_callback
        )
    elif ext == "txt":
        translated_bytes, translated_segments = await _translate_txt(
            file_bytes, source_lang, target_lang, pool, tier, progress_callback
        )
    elif ext == "pdf":
        translated_bytes, translated_segments = await _translate_pdf(
            file_bytes, source_lang, target_lang, pool, tier, progress_callback
        )
    else:
        raise ValueError(f"Định dạng tệp '.{ext}' chưa được hỗ trợ.")

    # Tính toán thông số thống kê
    full_preview = "\n\n".join(translated_segments)
    preview_text = full_preview[:500] if full_preview else ""
    char_count = sum(len(s) for s in translated_segments)
    paragraph_count = len(translated_segments)

    await _notify_progress(progress_callback, 100.0, "Dịch tài liệu thành công!", preview_text)

    return {
        "translated_bytes": translated_bytes,
        "out_filename": out_filename,
        "preview_text": preview_text,
        "format": ext,
        "char_count": char_count,
        "paragraph_count": paragraph_count
    }
def get_document_preview(filename: str, file_bytes: bytes) -> dict:
    import io
    ext = filename.split('.')[-1].lower()
    text = ""
    try:
        if ext == 'docx':
            from docx import Document
            doc = Document(io.BytesIO(file_bytes))
            paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for p in cell.paragraphs:
                            if p.text.strip():
                                paras.append(p.text.strip())
            text = "\n".join(paras[:50])
        elif ext == 'pdf':
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(file_bytes))
            pages = []
            for i in range(min(5, len(reader.pages))):
                pages.append(reader.pages[i].extract_text())
            text = "\n".join(pages)
        elif ext == 'srt':
            content_str = file_bytes.decode('utf-8', errors='ignore')
            lines = content_str.splitlines()
            dialogs = [l for l in lines if not l.isdigit() and '-->' not in l and l.strip()][:30]
            text = "\n".join(dialogs)
        else:
            text = file_bytes.decode('utf-8', errors='ignore')[:2000]
    except Exception as e:
        text = f"Không thể trích xuất xem trước: {str(e)}"
    
    return {"text": text, "format": ext}

def export_edited_document(content: str, format: str, original_filename: str = "") -> tuple[bytes, str, str]:
    import io, os
    from docx import Document
    out_io = io.BytesIO()
    ext = format.lower().strip('.')
    base = os.path.splitext(original_filename)[0] if original_filename else "document_translated"
    out_filename = f"{base}.{ext}"

    if ext == "docx":
        doc = Document()
        for p in content.split("\n"):
            p_str = p.strip()
            if not p_str:
                continue
            if p_str.startswith("### "):
                doc.add_heading(p_str[4:], level=3)
            elif p_str.startswith("## "):
                doc.add_heading(p_str[3:], level=2)
            elif p_str.startswith("# "):
                doc.add_heading(p_str[2:], level=1)
            else:
                doc.add_paragraph(p_str)
        doc.save(out_io)
        mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif ext == "pdf":
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import html
        font_name = "Helvetica"
        if os.path.exists("C:/Windows/Fonts/arial.ttf"):
            try:
                pdfmetrics.registerFont(TTFont("Arial", "C:/Windows/Fonts/arial.ttf"))
                font_name = "Arial"
            except Exception:
                pass
        doc = SimpleDocTemplate(out_io, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        styles = getSampleStyleSheet()
        style = ParagraphStyle("VNPdf", parent=styles["Normal"], fontName=font_name, fontSize=11, leading=15)
        story = []
        for p in content.split("\n"):
            if p.strip():
                story.append(Paragraph(html.escape(p.strip()).replace("\n", "<br/>"), style))
                story.append(Spacer(1, 8))
        doc.build(story)
        mime = "application/pdf"
    elif ext in ["srt", "md", "txt"]:
        out_io.write(content.encode("utf-8"))
        mime = "text/plain" if ext != "md" else "text/markdown"
    else:
        out_io.write(content.encode("utf-8"))
        mime = "application/octet-stream"
    return out_io.getvalue(), out_filename, mime

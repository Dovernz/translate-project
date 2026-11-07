import os
import re
import json
import asyncio
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core.key_pool import KeyPool, MODEL_TIERS
from core.video_helper import get_video_info, extract_youtube_id

app = FastAPI(title="Gemini Universal Translator & Realtime Video Subtitler")

# Khởi tạo Smart Key Pool
pool = KeyPool()

class TranslateRequest(BaseModel):
    text: str
    source_lang: str = "auto"
    target_lang: str = "vi"
    tier: str = "bulk"
    stream: bool = True

class VideoInfoRequest(BaseModel):
    url: str

class VideoChunkTranslateRequest(BaseModel):
    chunk_text: str
    target_lang: str = "vi"
    context: Optional[str] = ""

@app.get("/api/pool-status")
def get_pool_status():
    return pool.get_status()

@app.get("/api/models")
def get_models():
    return MODEL_TIERS

@app.post("/api/translate")
async def translate_text(req: TranslateRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Nội dung dịch không được để trống")

    src = req.source_lang if req.source_lang != "auto" else "ngôn ngữ gốc"
    tgt = req.target_lang
    lang_names = {
        "vi": "Tiếng Việt",
        "en": "Tiếng Anh",
        "ja": "Tiếng Nhật",
        "ko": "Tiếng Hàn",
        "zh": "Tiếng Trung (Giản thể)",
        "fr": "Tiếng Pháp",
        "de": "Tiếng Đức"
    }
    tgt_name = lang_names.get(tgt, tgt)

    system_instruction = (
        f"Bạn là một dịch giả chuyên nghiệp AI. Hãy dịch chuẩn xác toàn bộ nội dung sau từ {src} sang {tgt_name}. "
        "Giữ nguyên định dạng gốc (Markdown, thẻ HTML, cấu trúc code, dấu xuống dòng). "
        "Không thêm bất kỳ lời chào hay giải thích nào ngoài nội dung đã dịch."
    )

    if req.stream:
        async def event_generator():
            async for token in pool.generate_content_stream(req.text, system_instruction, req.tier):
                yield f"data: {json.dumps({'chunk': token}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")
    else:
        result = await pool.generate_content(req.text, system_instruction, req.tier)
        return {"translated_text": result}

@app.post("/api/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    translate_to_vi: bool = Form(True)
):
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="File âm thanh rỗng")
    
    mime_type = file.content_type or "audio/mp3"
    prompt = (
        "Hãy lắng nghe file âm thanh này và thực hiện 2 nhiệm vụ:\n"
        "1. TRANSCRIPT: Ghi lại chính xác nguyên văn bằng ngôn ngữ gốc (kèm mốc thời gian [mm:ss] nếu có).\n"
        "2. TRANSLATION: Dịch toàn bộ nội dung sang Tiếng Việt chuẩn xác, tự nhiên.\n"
        "Trả về định dạng rõ ràng:\n"
        "### 📝 Transcript Gốc:\n<nội dung gốc>\n\n"
        "### 🇻🇳 Bản Dịch Tiếng Việt:\n<nội dung dịch>"
    )
    
    try:
        result = await pool.generate_multimodal(contents, mime_type, prompt)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/video/info")
async def fetch_video_info(req: VideoInfoRequest):
    loop = asyncio.get_event_loop()
    info = await loop.run_in_executor(None, get_video_info, req.url)
    return info

@app.post("/api/video/translate-chunk")
async def translate_video_chunk(req: VideoChunkTranslateRequest):
    """
    Xoay vòng Key Pool để dịch từng câu/chunk phụ đề của video với độ trễ thấp nhất
    """
    system_instruction = (
        f"Bạn là hệ thống phụ đề video trực tiếp. Hãy dịch câu thoại/đoạn sau sang {req.target_lang}. "
        "Yêu cầu: Ngắn gọn, súc tích, văn phong tự nhiên hợp ngữ cảnh phim. CHỈ trả về câu dịch duy nhất, không giải thích."
    )
    translated = await pool.generate_content(req.chunk_text, system_instruction, tier="bulk")
    return {
        "original": req.chunk_text,
        "translated": translated.strip(),
        "key_index": (pool.current_index % len(pool.keys)) if pool.keys else 1
    }

@app.get("/", response_class=HTMLResponse)
def get_home():
    html_file = Path(__file__).parent / "templates" / "index.html"
    if html_file.exists():
        with open(html_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Translator App Ready</h1>"

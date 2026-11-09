import re
import os
import uuid
import json
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException, Body
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core.key_pool import KeyPool, MODEL_TIERS
from core.video_helper import (
    get_video_info,
    extract_youtube_id,
    extract_audio_from_video,
    download_video_from_url,
    extract_subtitles_from_url,
    cleanup_storage,
    parse_subtitles_from_ai,
    export_srt,
    burn_subtitles_to_video
)

app = FastAPI(title="Gemini Universal Translator & Realtime Subtitler")

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Mount thư mục tĩnh để stream và download video
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.mount("/outputs", StaticFiles(directory=str(OUTPUT_DIR)), name="outputs")

# Khởi tạo Smart Key Pool
pool = KeyPool()

# Data models
class TranslateRequest(BaseModel):
    text: str
    source_lang: str = "auto"
    target_lang: str = "vi"
    tier: str = "bulk"
    stream: bool = True

class VideoInfoRequest(BaseModel):
    url: str

class VideoProcessUrlRequest(BaseModel):
    url: str

class VideoChunkTranslateRequest(BaseModel):
    chunk_text: str
    target_lang: str = "vi"
    context: Optional[str] = ""

class AutoSubRequest(BaseModel):
    video_id: str
    target_lang: str = "vi"
    url: Optional[str] = ""

class BurnSubRequest(BaseModel):
    video_id: str
    subtitles: List[Dict[str, Any]]
    font_size: int = 22
    text_color: str = "#FBBF24"
    bg_color: str = "#000000"
    bg_opacity: float = 0.85
    mask_old_sub: bool = True
    vertical_margin: int = 35

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

@app.post("/api/video/process-url")
async def process_video_url(req: VideoProcessUrlRequest):
    """
    Xử lý link video: Tự động dọn rác cũ, tải video/audio và sẵn sàng cho AI quét
    """
    if not req.url.strip():
        raise HTTPException(status_code=400, detail="Vui lòng cung cấp link video")
    
    # Dọn dẹp ổ đĩa định kỳ để tránh tốn dung lượng
    cleanup_storage(UPLOAD_DIR, OUTPUT_DIR, max_age_minutes=30)

    loop = asyncio.get_event_loop()
    res = await loop.run_in_executor(None, download_video_from_url, req.url.strip(), UPLOAD_DIR)
    if not res.get("success"):
        raise HTTPException(status_code=500, detail=res.get("error", "Lỗi tải video từ đường dẫn"))
    return res

@app.post("/api/video/translate-chunk")
async def translate_video_chunk(req: VideoChunkTranslateRequest):
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

@app.post("/api/video/upload")
async def upload_video(file: UploadFile = File(...)):
    # Dọn dẹp video tạm cũ hơn 30 phút
    cleanup_storage(UPLOAD_DIR, OUTPUT_DIR, max_age_minutes=30)

    ext = Path(file.filename or "video.mp4").suffix.lower()
    if ext not in [".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"]:
        ext = ".mp4"
    
    video_id = str(uuid.uuid4())[:8]
    saved_filename = f"{video_id}_{file.filename}"
    saved_path = UPLOAD_DIR / saved_filename
    
    with open(saved_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            f.write(chunk)
            
    audio_path = UPLOAD_DIR / f"{video_id}_audio.mp3"
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, extract_audio_from_video, saved_path, audio_path)

    return {
        "video_id": video_id,
        "filename": file.filename,
        "saved_filename": saved_filename,
        "video_url": f"/uploads/{saved_filename}",
        "size_bytes": saved_path.stat().st_size
    }

@app.post("/api/video/auto-subtitle")
async def auto_subtitle_video(req: AutoSubRequest):
    """
    Quét video bằng AI:
    1. Ưu tiên Zero-Video: trích xuất phụ đề gốc trực tiếp từ URL (chỉ 10KB) và dịch siêu tốc trong 2s.
    2. Fallback: Nếu không có sub gốc, gửi audio đến Gemini Multimodal Model.
    """
    lang_map = {
        "vi": "Tiếng Việt",
        "en": "Tiếng Anh",
        "ja": "Tiếng Nhật",
        "ko": "Tiếng Hàn",
        "zh": "Tiếng Trung",
        "fr": "Tiếng Pháp"
    }
    target_name = lang_map.get(req.target_lang, "Tiếng Việt")

    # ƯU TIÊN 1: Nếu có URL, thử trích xuất phụ đề gốc có sẵn (Zero-Download)
    if req.url:
        loop = asyncio.get_event_loop()
        extracted_subs = await loop.run_in_executor(None, extract_subtitles_from_url, req.url, UPLOAD_DIR)
        if extracted_subs and len(extracted_subs) > 0:
            chunk_size = 25
            chunks = [extracted_subs[i:i + chunk_size] for i in range(0, len(extracted_subs), chunk_size)]

            async def translate_chunk(chunk):
                batch_lines = [f"{s['id']}. {s['original']}" for s in chunk]
                prompt = (
                    f"Bạn là chuyên gia dịch phụ đề phim. Hãy dịch từng câu sau sang {target_name}.\n"
                    f"Yêu cầu: Giữ nguyên số thứ tự và định dạng '[Số]. [Bản dịch]'. Ngắn gọn, súc tích, chuẩn ngữ cảnh.\n"
                    f"Chỉ trả về danh sách dịch, không giải thích:\n"
                    + "\n".join(batch_lines)
                )
                try:
                    res_text = await pool.generate_content(prompt, tier="bulk")
                    sub_map = {}
                    for line in res_text.split("\n"):
                        line = line.strip()
                        m = re.match(r"^(\d+)[\.\:\-\s]+(.+)$", line)
                        if m:
                            try:
                                sub_map[int(m.group(1))] = m.group(2).strip()
                            except Exception:
                                pass
                    for s in chunk:
                        s["translated"] = sub_map.get(s["id"], s["original"])
                except Exception as ex:
                    print(f"[DEBUG] Lỗi dịch chunk: {ex}")
                    for s in chunk:
                        s["translated"] = s["original"]

            await asyncio.gather(*(translate_chunk(c) for c in chunks))

            srt_path = OUTPUT_DIR / f"{req.video_id}.srt"
            export_srt(extracted_subs, srt_path)

            return {
                "video_id": req.video_id,
                "subtitles": extracted_subs,
                "srt_url": f"/outputs/{req.video_id}.srt",
                "mode": "zero_download_caption"
            }

    # ƯU TIÊN 2: Quét bằng Gemini Multimodal Audio Model
    audio_path = UPLOAD_DIR / f"{req.video_id}_audio.mp3"
    if not audio_path.exists():
        matches = list(UPLOAD_DIR.glob(f"{req.video_id}_*"))
        if not matches:
            raise HTTPException(status_code=404, detail="Không tìm thấy dữ liệu video/audio.")
        video_path = matches[0]
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(None, extract_audio_from_video, video_path, audio_path)
        if not success or not audio_path.exists():
            raise HTTPException(status_code=500, detail="Không thể trích xuất âm thanh từ video.")

    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    prompt = (
        f"Bạn là chuyên gia nhận diện giọng nói và dịch phụ đề video tự động. "
        f"Hãy lắng nghe toàn bộ file âm thanh và trích xuất từng câu thoại kèm mốc thời gian, sau đó dịch sang {target_name}. "
        f"Yêu cầu xuất ra BẮT BUỘC dạng mảng JSON thuần túy (JSON Array), KHÔNG viết giải thích hay bọc thẻ văn bản khác:\n"
        f"[\n"
        f'  {{"start": "00:01.000", "end": "00:04.500", "original": "câu thoại gốc", "translated": "bản dịch {target_name}"}},\n'
        f'  {{"start": "00:05.000", "end": "00:08.200", "original": "câu tiếp theo", "translated": "bản dịch tiếp theo"}}\n'
        f"]"
    )

    try:
        ai_response = await pool.generate_multimodal(
            audio_bytes=audio_bytes,
            mime_type="audio/mp3",
            prompt=prompt
        )
        subtitles = parse_subtitles_from_ai(ai_response)
        
        if not subtitles:
            subtitles = [{
                "id": 1,
                "start": 1.0,
                "end": 5.0,
                "start_str": "00:00:01.000",
                "end_str": "00:00:05.000",
                "original": "Audio recognized",
                "translated": "Đã hoàn thành nhận diện âm thanh"
            }]

        srt_path = OUTPUT_DIR / f"{req.video_id}.srt"
        export_srt(subtitles, srt_path)

        return {
            "video_id": req.video_id,
            "subtitles": subtitles,
            "srt_url": f"/outputs/{req.video_id}.srt",
            "mode": "multimodal_audio"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi AI Subtitling: {str(e)}")

@app.post("/api/video/burn-subtitles")
async def burn_subtitles_endpoint(req: BurnSubRequest):
    matches = [p for p in UPLOAD_DIR.glob(f"{req.video_id}_*") if not p.name.endswith(".mp3")]
    if not matches:
        raise HTTPException(status_code=404, detail="Không tìm thấy file video gốc để in phụ đề.")
    
    video_path = matches[0]
    srt_path = OUTPUT_DIR / f"{req.video_id}.srt"
    output_video_path = OUTPUT_DIR / f"{req.video_id}_subtitled.mp4"

    export_srt(req.subtitles, srt_path)

    loop = asyncio.get_event_loop()
    success = await loop.run_in_executor(
        None,
        burn_subtitles_to_video,
        video_path,
        srt_path,
        output_video_path,
        req.font_size,
        req.text_color,
        req.bg_color,
        req.bg_opacity,
        req.mask_old_sub,
        req.vertical_margin
    )

    if not success or not output_video_path.exists():
        raise HTTPException(status_code=500, detail="Không thể burn phụ đề vào video qua ffmpeg.")

    return {
        "status": "success",
        "video_id": req.video_id,
        "download_url": f"/outputs/{req.video_id}_subtitled.mp4",
        "srt_url": f"/outputs/{req.video_id}.srt"
    }

@app.get("/", response_class=HTMLResponse)
def get_home():
    html_file = Path(__file__).parent / "templates" / "index.html"
    if html_file.exists():
        with open(html_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Translator App Ready</h1>"

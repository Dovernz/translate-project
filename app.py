from fastapi import Response
from core.document_helper import export_edited_document
import sys
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
import re
import os
import time
import uuid
import json
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException, Body, BackgroundTasks
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import aiofiles
import zipfile
from core.manga_helper import (
    detect_and_translate_manga,
    detect_image_mime,
    render_translated_page,
    fetch_images_from_url,
    analyze_manga_site_with_ai,
    extract_chapters_from_url,
    extract_images_from_zip,
    natural_sort_key
)

from core.key_pool import KeyPool, MODEL_TIERS
from core.document_helper import translate_document, get_document_preview
from core.webpage_helper import process_and_translate_webpage
from core.video_sub import (
    SUPPORTED_VIDEO_LANGUAGES,
    AutoSubRequest,
    TranslateSubtitlesRequest,
    process_auto_subtitle,
    process_translate_subtitles
)
from core.video_helper import (
    get_video_info,
    extract_youtube_id,
    extract_audio_from_video,
    download_video_from_url,
    extract_subtitles_from_url,
    cleanup_storage,
    parse_subtitles_from_ai,
    export_srt,
    export_vtt,
    burn_subtitles_to_video,
    safe_log
)

app = FastAPI(title="Gemini Universal Translator & Realtime Subtitler")

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
DOCS_OUTPUT_DIR = OUTPUT_DIR / "documents"
DOCS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MANGA_UPLOAD_DIR = UPLOAD_DIR / "manga"
MANGA_OUTPUT_DIR = OUTPUT_DIR / "manga"
MANGA_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MANGA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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

# AutoSubRequest moved to core.video_sub

class MangaChaptersRequest(BaseModel):
    url: str

class MangaProcessUrlRequest(BaseModel):
    url: str
    session_id: Optional[str] = None

class MangaTranslatePageRequest(BaseModel):
    session_id: str
    page_index: int
    target_lang: str = "vi"

class MangaTranslateAllRequest(BaseModel):
    session_id: str
    target_lang: str = "vi"
    concurrency: int = 7

class MangaExportZipRequest(BaseModel):
    session_id: str

class WebpageTranslateRequest(BaseModel):
    url: str
    target_lang: str = "vi"
    tier: str = "bulk"
    bypass_cache: bool = False

class BurnSubRequest(BaseModel):
    video_id: str
    subtitles: List[Dict[str, Any]]
    font_size: int = 22
    text_color: str = "#FBBF24"
    bg_color: str = "#000000"
    bg_opacity: float = 0.85
    mask_old_sub: bool = True
    vertical_margin: int = 35

is_server_shutting_down = False

@app.get("/api/pool-status")
def get_pool_status():
    if is_server_shutting_down:
        return {"status": "shutting_down", "total_keys": 0, "active_keys": 0, "keys": []}
    return pool.get_status()

@app.post("/api/shutdown")
async def shutdown_server():
    global is_server_shutting_down
    is_server_shutting_down = True
    import os, signal, asyncio
    async def kill_later():
        await asyncio.sleep(0.5)
        os.kill(os.getpid(), signal.SIGTERM)
    asyncio.create_task(kill_later())
    return {"status": "shutting_down", "message": "Server is shutting down"}

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


@app.post("/api/document/extract")
async def extract_document(file: UploadFile = File(...)):
    file_bytes = await file.read()
    return get_document_preview(file.filename or "document.txt", file_bytes)
@app.post("/api/webpage/translate")
async def translate_webpage(req: WebpageTranslateRequest):
    if not req.url or not req.url.strip():
        raise HTTPException(status_code=400, detail="Vui lòng nhập đường dẫn URL trang web.")
    try:
        result = await process_and_translate_webpage(
            url=req.url.strip(),
            target_lang=req.target_lang,
            pool=pool,
            tier=req.tier,
            bypass_cache=req.bypass_cache
        )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        print(f"Error translating webpage: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi khi tải hoặc dịch trang web: {str(e)}")

@app.post("/api/webpage/cache/clear")
def clear_webpage_cache(req: Optional[Dict[str, Any]] = Body(None)):
    from core.webpage_helper import web_cache
    target_url = req.get("url") if req else None
    web_cache.invalidate(target_url) if target_url else web_cache.invalidate("")
    return {"status": "success", "message": "Cache invalidated"}

@app.get("/test-article", response_class=HTMLResponse)
def get_test_article():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Artificial Intelligence and Future of Machine Learning</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.8; margin: 40px auto; max-width: 800px; padding: 0 20px; color: #1e293b; background: #ffffff; }
        h1 { color: #0f172a; border-bottom: 2px solid #e2e8f0; padding-bottom: 12px; }
        h2 { color: #334155; margin-top: 32px; }
        p { margin: 16px 0; font-size: 16px; }
        .card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; margin: 24px 0; }
        li { margin-bottom: 8px; }
        .nav-box { margin-top: 30px; padding: 18px; background: #e0f2fe; border: 1px solid #bae6fd; border-radius: 10px; }
        .demo-link { display: inline-flex; align-items: center; gap: 8px; padding: 10px 18px; background: #0284c7; color: #ffffff !important; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 14px; transition: background 0.2s; }
        .demo-link:hover { background: #0369a1; }
    </style>
</head>
<body>
    <h1>Artificial Intelligence and Future of Machine Learning</h1>
    <p>Artificial Intelligence (AI) has emerged as one of the most transformative technological innovations of the twenty-first century. From automated reasoning to deep neural networks, AI systems are reshaping industries and society.</p>
    <div class="card">
        <h2>Core Innovations in Modern AI Architectures</h2>
        <p>Modern machine learning models leverage massive datasets and transformer architectures to generate human-like reasoning, synthesize software code, and analyze visual information at unprecedented scale.</p>
        <ul>
            <li>Multimodal foundation models capable of reasoning across text, voice, and vision.</li>
            <li>Low-latency edge deployment optimized for real-time translation and embedded agents.</li>
            <li>Context-aware attention mechanisms improving natural language comprehension.</li>
        </ul>
    </div>
    <h2>Impact on Global Communication and Real-time Translation</h2>
    <p>Cross-lingual communication barriers are rapidly collapsing. Neural translation pipelines preserve syntactic subtleties, cultural idioms, and original document presentation with high precision.</p>
    
    <div class="nav-box">
        <h3 style="margin-top:0; color: #0369a1;">Featured Deep-Dive Exploration</h3>
        <p style="margin-bottom: 14px;">Continue reading our next article on distributed autonomous intelligence:</p>
        <a id="link-to-article-2" class="demo-link" href="/test-article-2">
            <span>Next Article: Autonomous Multi-Agent Architectures</span> &rarr;
        </a>
    </div>

    <h2>The Roadmap Ahead</h2>
    <p>As computational efficiency increases, next-generation AI agents will collaborate autonomously to orchestrate distributed workflows, verify correctness, and eliminate language barriers globally.</p>
    <p>Continued advances in ethical alignment, low-resource language preservation, and zero-storage processing guarantee enhanced user privacy and data sovereignty.</p>
    <p style="margin-top: 150px; color: #64748b; font-size: 14px;">Published by Tech Innovations Journal &copy; 2026. All rights reserved.</p>
</body>
</html>"""

@app.get("/test-article-2", response_class=HTMLResponse)
def get_test_article_2():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Autonomous Multi-Agent Architectures</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.8; margin: 40px auto; max-width: 800px; padding: 0 20px; color: #1e293b; background: #ffffff; }
        h1 { color: #0f172a; border-bottom: 2px solid #e2e8f0; padding-bottom: 12px; }
        h2 { color: #334155; margin-top: 32px; }
        p { margin: 16px 0; font-size: 16px; }
        .card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; margin: 24px 0; }
        .nav-box { margin-top: 30px; padding: 18px; background: #fef3c7; border: 1px solid #fde68a; border-radius: 10px; }
        .demo-link { display: inline-flex; align-items: center; gap: 8px; padding: 10px 18px; background: #d97706; color: #ffffff !important; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 14px; transition: background 0.2s; }
        .demo-link:hover { background: #b45309; }
    </style>
</head>
<body>
    <h1>Autonomous Multi-Agent Architectures</h1>
    <p>Autonomous multi-agent systems represent a paradigm shift in software engineering, moving from monolithic single-prompt models to orchestrated teams of specialist agents.</p>
    <div class="card">
        <h2>Key Benefits of Agentic Collaboration</h2>
        <p>Specialized agents coordinate through explicit protocols, separating responsibilities into architecture design, automated testing, and security verification.</p>
    </div>
    <div class="nav-box">
        <h3 style="margin-top:0; color: #b45309;">Navigation Back to Foundation Article</h3>
        <p style="margin-bottom: 14px;">Return to the foundational article on Machine Learning and AI:</p>
        <a id="link-back-to-article-1" class="demo-link" href="/test-article">
            &larr; <span>Back to Artificial Intelligence Overview</span>
        </a>
    </div>
    <p style="margin-top: 150px; color: #64748b; font-size: 14px;">Published by Tech Innovations Journal &copy; 2026. All rights reserved.</p>
</body>
</html>"""

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
    url_str = (req.url or "").strip()
    if not url_str:
        return {"title": "Unknown", "error": "URL rỗng"}
    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, get_video_info, url_str)
        return info
    except Exception as e:
        safe_log(f"[ERROR] fetch_video_info error: {e}")
        return {"title": "Video Stream", "error": str(e)}

@app.post("/api/video/process-url")
async def process_video_url(req: VideoProcessUrlRequest):
    """
    Xử lý link video: Tự động dọn rác cũ, tải video/audio và sẵn sàng cho AI quét
    """
    url_str = (req.url or "").strip()
    if not url_str:
        return JSONResponse(status_code=200, content={"success": False, "error": "Vui lòng cung cấp link video", "detail": "Vui lòng cung cấp link video"})
    
    try:
        # Dọn dẹp ổ đĩa định kỳ để tránh tốn dung lượng
        try:
            cleanup_storage(UPLOAD_DIR, OUTPUT_DIR, max_age_minutes=30)
        except Exception as e_clean:
            safe_log(f"[WARN] cleanup_storage error: {e_clean}")

        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, download_video_from_url, url_str, UPLOAD_DIR)
        if not res or not res.get("success"):
            err_msg = (res.get("error") if res else None) or "Không thể tải video từ đường dẫn này."
            return JSONResponse(status_code=200, content={"success": False, "error": err_msg, "detail": err_msg})
        return res
    except Exception as e:
        safe_log(f"[ERROR] process_video_url error: {e}")
        err_msg = f"Lỗi xử lý video: {str(e)}"
        return JSONResponse(status_code=200, content={"success": False, "error": err_msg, "detail": err_msg})

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
    loop = asyncio.get_event_loop()
    return await process_auto_subtitle(req, pool, loop, UPLOAD_DIR, OUTPUT_DIR)

@app.post("/api/video/translate-subtitles")
async def translate_subtitles_endpoint(req: TranslateSubtitlesRequest):
    return await process_translate_subtitles(req, pool, OUTPUT_DIR)

@app.post("/api/video/burn-subtitles")
async def burn_subtitles_endpoint(req: BurnSubRequest):
    matches = [p for p in UPLOAD_DIR.glob(f"{req.video_id}_*") if not p.name.endswith(".mp3")]
    if not matches:
        raise HTTPException(status_code=404, detail="Không tìm thấy file video gốc để in phụ đề.")
    
    video_path = matches[0]
    srt_path = OUTPUT_DIR / f"{req.video_id}.srt"
    vtt_path = OUTPUT_DIR / f"{req.video_id}.vtt"
    output_video_path = OUTPUT_DIR / f"{req.video_id}_subtitled.mp4"

    export_srt(req.subtitles, srt_path)
    export_vtt(req.subtitles, vtt_path)

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
        "clean_download_url": f"/api/video/download/{req.video_id}_subtitled.mp4?cleanup=1",
        "srt_url": f"/outputs/{req.video_id}.srt",
        "vtt_url": f"/outputs/{req.video_id}.vtt"
    }

@app.get("/api/video/download/{filename}")
async def download_file_with_cleanup(filename: str, background_tasks: BackgroundTasks, cleanup: bool = False):
    """
    Tải file về máy và tự động dọn dẹp tức thì ngay sau khi stream hoàn tất (nếu cleanup=True).
    Không tốn dung lượng máy chủ lưu trữ lâu dài!
    """
    # Ngăn chặn Directory Traversal
    safe_filename = Path(filename).name
    file_path = OUTPUT_DIR / safe_filename
    if not file_path.exists():
        file_path = UPLOAD_DIR / safe_filename
    
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File không tồn tại hoặc đã được dọn dẹp sạch sẽ")

    if cleanup:
        def cleanup_temp_file():
            # Chờ 3 giây để đảm bảo client đã nhận xong bytes cuối cùng
            time.sleep(3)
            try:
                if file_path.exists():
                    file_path.unlink()
                    print(f"[AUTO-CLEANUP] Đã xóa file tạm thời sau khi tải: {file_path.name}")
            except Exception as e:
                print(f"[AUTO-CLEANUP ERROR] {e}")
        background_tasks.add_task(cleanup_temp_file)

    return FileResponse(
        path=str(file_path),
        filename=safe_filename,
        media_type="application/octet-stream"
    )

@app.post("/api/video/cleanup")
async def cleanup_video_endpoint(req: Dict[str, Any] = Body(...)):
    """
    Xóa sạch toàn bộ video gốc, file audio trích xuất và file video đã burn của video_id chỉ định.
    Đảm bảo 0-byte ổ đĩa tồn đọng trên server.
    """
    video_id = req.get("video_id")
    if not video_id:
        raise HTTPException(status_code=400, detail="Thiếu video_id")
    
    cleaned_files = []
    for d in [UPLOAD_DIR, OUTPUT_DIR]:
        for p in d.glob(f"{video_id}*"):
            try:
                if p.is_file():
                    cleaned_files.append(p.name)
                    p.unlink()
            except Exception as e:
                print(f"[CLEANUP ERROR] {p}: {e}")

    return {
        "status": "success",
        "video_id": video_id,
        "deleted_count": len(cleaned_files),
        "deleted_files": cleaned_files
    }

# ==========================================
# MANGA & COMIC TRANSLATION ENDPOINTS
# ==========================================

@app.post("/api/manga/upload")
async def upload_manga(
    files: List[UploadFile] = File(...),
    session_id: Optional[str] = Form(None)
):
    if not files:
        raise HTTPException(status_code=400, detail="Không có tệp nào được tải lên")

    sid = session_id or uuid.uuid4().hex[:12]
    orig_dir = MANGA_UPLOAD_DIR / sid / "original"
    orig_dir.mkdir(parents=True, exist_ok=True)

    for upload_file in files:
        filename = upload_file.filename or "page.jpg"
        ext = Path(filename).suffix.lower()
        if ext in [".zip", ".cbz"]:
            content = await upload_file.read()
            extract_images_from_zip(content, orig_dir)
        elif ext in [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".avif"]:
            dest = orig_dir / filename
            async with aiofiles.open(dest, "wb") as f:
                content = await upload_file.read()
                await f.write(content)

    img_files = [p for p in orig_dir.iterdir() if p.is_file() and p.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".avif"]]
    img_files.sort(key=natural_sort_key)

    if not img_files:
        raise HTTPException(status_code=400, detail="Không tìm thấy tệp ảnh truyện hợp lệ trong dữ liệu tải lên")

    pages = []
    for idx, p in enumerate(img_files):
        pages.append({
            "page_index": idx + 1,
            "filename": p.name,
            "original_url": f"/uploads/manga/{sid}/original/{p.name}",
            "translated_url": None,
            "status": "pending"
        })

    return {
        "status": "success",
        "session_id": sid,
        "total_pages": len(pages),
        "pages": pages
    }

@app.post("/api/manga/paste-and-translate")
async def paste_and_translate_manga(
    file: UploadFile = File(...),
    target_lang: str = Form("vi"),
    session_id: Optional[str] = Form(None)
):
    if not file:
        raise HTTPException(status_code=400, detail="Không có dữ liệu ảnh tải lên từ Clipboard")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Dữ liệu ảnh từ Clipboard bị rỗng")

    orig_ext = Path(file.filename or "").suffix.lower()
    if orig_ext not in [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".avif"]:
        mime = detect_image_mime(content)
        if "jpeg" in mime or "jpg" in mime:
            ext = ".jpg"
        elif "webp" in mime:
            ext = ".webp"
        else:
            ext = ".png"
    else:
        ext = orig_ext

    sid = session_id or uuid.uuid4().hex[:12]
    orig_dir = MANGA_UPLOAD_DIR / sid / "original"
    trans_dir = MANGA_OUTPUT_DIR / sid / "translated"
    bubble_dir = MANGA_OUTPUT_DIR / sid / "bubbles"
    orig_dir.mkdir(parents=True, exist_ok=True)
    trans_dir.mkdir(parents=True, exist_ok=True)
    bubble_dir.mkdir(parents=True, exist_ok=True)

    timestamp_ms = int(time.time() * 1000)
    filename = f"paste_{timestamp_ms}{ext}"
    dest = orig_dir / filename
    async with aiofiles.open(dest, "wb") as f:
        await f.write(content)

    # Perform AI Inpainting + Speech Bubble Detection & Translation
    bubbles = []
    try:
        bubbles = await detect_and_translate_manga(content, target_lang=target_lang, pool=pool)
    except Exception as e:
        print(f"Error in detect_and_translate_manga for pasted image: {e}")

    loop = asyncio.get_event_loop()
    translated_bytes = await loop.run_in_executor(None, render_translated_page, content, bubbles)

    out_file = trans_dir / filename
    async with aiofiles.open(out_file, "wb") as f:
        await f.write(translated_bytes)

    bubble_file = bubble_dir / f"{Path(filename).stem}.json"
    async with aiofiles.open(bubble_file, "w", encoding="utf-8") as f:
        await f.write(json.dumps(bubbles, ensure_ascii=False, indent=2))

    orig_url = f"/uploads/manga/{sid}/original/{filename}"
    trans_url = f"/outputs/manga/{sid}/translated/{filename}?t={int(time.time())}"

    page_item = {
        "page_index": 1,
        "filename": filename,
        "original_url": orig_url,
        "translated_url": trans_url,
        "status": "translated",
        "bubbles": bubbles
    }

    return {
        "status": "success",
        "session_id": sid,
        "total_pages": 1,
        "page_index": 1,
        "filename": filename,
        "original_url": orig_url,
        "translated_url": trans_url,
        "bubbles": bubbles,
        "pages": [page_item]
    }

@app.post("/api/manga/chapters")
async def get_manga_chapters(req: MangaChaptersRequest):
    if not req.url or not req.url.strip():
        raise HTTPException(status_code=400, detail="URL truyện không được để trống")
    try:
        data = await analyze_manga_site_with_ai(req.url.strip(), pool)
        return {
            "status": "success",
            **data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi phân tích danh sách chapter: {str(e)}")

@app.post("/api/manga/process-url")
async def process_manga_url(req: MangaProcessUrlRequest):
    if not req.url or not req.url.strip():
        raise HTTPException(status_code=400, detail="URL truyện không được để trống")

    sid = req.session_id or uuid.uuid4().hex[:12]
    orig_dir = MANGA_UPLOAD_DIR / sid / "original"
    orig_dir.mkdir(parents=True, exist_ok=True)

    try:
        downloaded = await fetch_images_from_url(req.url, orig_dir)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi tải ảnh từ liên kết: {str(e)}")

    if not downloaded:
        raise HTTPException(status_code=400, detail="Không tìm thấy ảnh truyện từ liên kết đã cung cấp")

    pages = []
    for idx, p in enumerate(downloaded):
        pages.append({
            "page_index": idx + 1,
            "filename": p.name,
            "original_url": f"/uploads/manga/{sid}/original/{p.name}",
            "translated_url": None,
            "status": "pending"
        })

    return {
        "status": "success",
        "session_id": sid,
        "total_pages": len(pages),
        "pages": pages
    }

@app.post("/api/manga/translate-page")
async def translate_manga_page(req: MangaTranslatePageRequest):
    orig_dir = MANGA_UPLOAD_DIR / req.session_id / "original"
    if not orig_dir.exists():
        raise HTTPException(status_code=404, detail="Phiên dịch truyện không tồn tại")

    img_files = [p for p in orig_dir.iterdir() if p.is_file() and p.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".avif"]]
    img_files.sort(key=natural_sort_key)

    if req.page_index < 1 or req.page_index > len(img_files):
        raise HTTPException(status_code=404, detail=f"Không tìm thấy trang #{req.page_index}")

    target_file = img_files[req.page_index - 1]
    async with aiofiles.open(target_file, "rb") as f:
        img_bytes = await f.read()

    bubbles = await detect_and_translate_manga(img_bytes, target_lang=req.target_lang, pool=pool)
    loop = asyncio.get_event_loop()
    translated_bytes = await loop.run_in_executor(None, render_translated_page, img_bytes, bubbles)

    trans_dir = MANGA_OUTPUT_DIR / req.session_id / "translated"
    bubble_dir = MANGA_OUTPUT_DIR / req.session_id / "bubbles"
    trans_dir.mkdir(parents=True, exist_ok=True)
    bubble_dir.mkdir(parents=True, exist_ok=True)

    out_file = trans_dir / target_file.name
    async with aiofiles.open(out_file, "wb") as f:
        await f.write(translated_bytes)

    bubble_file = bubble_dir / f"{target_file.stem}.json"
    async with aiofiles.open(bubble_file, "w", encoding="utf-8") as f:
        await f.write(json.dumps(bubbles, ensure_ascii=False, indent=2))

    return {
        "status": "success",
        "session_id": req.session_id,
        "page_index": req.page_index,
        "filename": target_file.name,
        "original_url": f"/uploads/manga/{req.session_id}/original/{target_file.name}",
        "translated_url": f"/outputs/manga/{req.session_id}/translated/{target_file.name}?t={int(time.time())}",
        "bubbles": bubbles
    }

@app.post("/api/manga/translate-all")
async def translate_all_manga(req: MangaTranslateAllRequest):
    orig_dir = MANGA_UPLOAD_DIR / req.session_id / "original"
    if not orig_dir.exists():
        raise HTTPException(status_code=404, detail="Phiên dịch truyện không tồn tại")

    img_files = [p for p in orig_dir.iterdir() if p.is_file() and p.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".avif"]]
    img_files.sort(key=natural_sort_key)

    if not img_files:
        raise HTTPException(status_code=400, detail="Không có trang truyện nào trong phiên này")

    trans_dir = MANGA_OUTPUT_DIR / req.session_id / "translated"
    bubble_dir = MANGA_OUTPUT_DIR / req.session_id / "bubbles"
    trans_dir.mkdir(parents=True, exist_ok=True)
    bubble_dir.mkdir(parents=True, exist_ok=True)

    concurrency = min(req.concurrency or 7, len(pool.keys) if pool.keys else 5)
    sem = asyncio.Semaphore(max(1, concurrency))
    loop = asyncio.get_event_loop()

    async def process_single(idx: int, file_path: Path):
        async with sem:
            async with aiofiles.open(file_path, "rb") as f:
                img_bytes = await f.read()

            try:
                bubbles = await detect_and_translate_manga(img_bytes, target_lang=req.target_lang, pool=pool)
                translated_bytes = await loop.run_in_executor(None, render_translated_page, img_bytes, bubbles)
            except Exception as e:
                bubbles = []
                translated_bytes = img_bytes

            out_file = trans_dir / file_path.name
            async with aiofiles.open(out_file, "wb") as f:
                await f.write(translated_bytes)

            bubble_file = bubble_dir / f"{file_path.stem}.json"
            async with aiofiles.open(bubble_file, "w", encoding="utf-8") as f:
                await f.write(json.dumps(bubbles, ensure_ascii=False))

            return {
                "page_index": idx + 1,
                "filename": file_path.name,
                "original_url": f"/uploads/manga/{req.session_id}/original/{file_path.name}",
                "translated_url": f"/outputs/manga/{req.session_id}/translated/{file_path.name}?t={int(time.time())}",
                "bubbles": bubbles,
                "status": "translated"
            }

    tasks = [process_single(i, f) for i, f in enumerate(img_files)]
    results = await asyncio.gather(*tasks)
    results.sort(key=lambda x: x["page_index"])

    return {
        "status": "success",
        "session_id": req.session_id,
        "total_pages": len(results),
        "pages": results
    }

@app.post("/api/manga/export-zip")
async def export_manga_zip(req: MangaExportZipRequest):
    trans_dir = MANGA_OUTPUT_DIR / req.session_id / "translated"
    orig_dir = MANGA_UPLOAD_DIR / req.session_id / "original"

    source_dir = trans_dir if (trans_dir.exists() and any(trans_dir.iterdir())) else orig_dir
    if not source_dir.exists():
        raise HTTPException(status_code=404, detail="Không tìm thấy chapter đã dịch")

    img_files = [p for p in source_dir.iterdir() if p.is_file() and p.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".avif"]]
    img_files.sort(key=natural_sort_key)

    if not img_files:
        raise HTTPException(status_code=404, detail="Không có trang truyện nào để xuất ZIP")

    zip_filename = f"manga_translated_{req.session_id}.zip"
    zip_path = MANGA_OUTPUT_DIR / req.session_id / zip_filename
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for idx, img_path in enumerate(img_files):
            arcname = f"page_{idx + 1:03d}{img_path.suffix.lower()}"
            zf.write(img_path, arcname=arcname)

    return {
        "status": "success",
        "session_id": req.session_id,
        "download_url": f"/outputs/manga/{req.session_id}/{zip_filename}",
        "total_pages": len(img_files)
    }

@app.get("/api/manga/session/{session_id}")
async def get_manga_session(session_id: str):
    orig_dir = MANGA_UPLOAD_DIR / session_id / "original"
    trans_dir = MANGA_OUTPUT_DIR / session_id / "translated"
    bubble_dir = MANGA_OUTPUT_DIR / session_id / "bubbles"

    if not orig_dir.exists():
        raise HTTPException(status_code=404, detail="Phiên không tồn tại")

    img_files = [p for p in orig_dir.iterdir() if p.is_file() and p.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".avif"]]
    img_files.sort(key=natural_sort_key)

    pages = []
    for idx, p in enumerate(img_files):
        trans_file = trans_dir / p.name
        is_trans = trans_file.exists()
        bubbles = []
        bubble_file = bubble_dir / f"{p.stem}.json"
        if bubble_file.exists():
            try:
                with open(bubble_file, "r", encoding="utf-8") as bf:
                    bubbles = json.load(bf)
            except Exception:
                pass

        pages.append({
            "page_index": idx + 1,
            "filename": p.name,
            "original_url": f"/uploads/manga/{session_id}/original/{p.name}",
            "translated_url": f"/outputs/manga/{session_id}/translated/{p.name}?t={int(time.time())}" if is_trans else None,
            "status": "translated" if is_trans else "pending",
            "bubbles": bubbles
        })

    return {
        "status": "success",
        "session_id": session_id,
        "total_pages": len(pages),
        "pages": pages
    }

@app.get("/api/system/check-update")
async def check_system_update():
    """
    Kiểm tra commit local so với remote (GitHub).
    """
    try:
        if not (BASE_DIR / ".git").exists():
            return {
                "status": "error",
                "message": "Không tìm thấy thư mục .git trong dự án.",
                "has_update": False
            }

        branch_proc = await asyncio.create_subprocess_shell(
            "git branch --show-current",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(BASE_DIR)
        )
        branch_out, _ = await branch_proc.communicate()
        branch = branch_out.decode("utf-8", errors="ignore").strip() or "main"

        commit_proc = await asyncio.create_subprocess_shell(
            'git log -1 --format="%h - %s (%cd)" --date=relative',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(BASE_DIR)
        )
        commit_out, _ = await commit_proc.communicate()
        current_commit = commit_out.decode("utf-8", errors="ignore").strip()

        fetch_proc = await asyncio.create_subprocess_shell(
            f"git fetch origin {branch}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(BASE_DIR)
        )
        try:
            await asyncio.wait_for(fetch_proc.communicate(), timeout=8.0)
        except asyncio.TimeoutError:
            return {
                "status": "warning",
                "message": "Kiểm tra remote quá thời gian (hãy kiểm tra kết nối mạng).",
                "has_update": False,
                "current_commit": current_commit,
                "branch": branch
            }

        count_proc = await asyncio.create_subprocess_shell(
            f"git rev-list --count HEAD..origin/{branch}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(BASE_DIR)
        )
        count_out, _ = await count_proc.communicate()
        count_str = count_out.decode("utf-8", errors="ignore").strip()
        behind_count = int(count_str) if count_str.isdigit() else 0

        remote_commit = ""
        if behind_count > 0:
            rem_proc = await asyncio.create_subprocess_shell(
                f'git log -1 --format="%h - %s (%cd)" --date=relative origin/{branch}',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(BASE_DIR)
            )
            rem_out, _ = await rem_proc.communicate()
            remote_commit = rem_out.decode("utf-8", errors="ignore").strip()

        return {
            "status": "success",
            "has_update": behind_count > 0,
            "behind_count": behind_count,
            "current_commit": current_commit,
            "remote_commit": remote_commit,
            "branch": branch
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "has_update": False
        }


@app.post("/api/system/perform-update")
async def perform_system_update():
    """
    Tự động chạy git pull và đồng bộ thư viện nếu cần.
    """
    try:
        if not (BASE_DIR / ".git").exists():
            return {
                "status": "error",
                "message": "Không tìm thấy thư mục .git trong dự án."
            }

        branch_proc = await asyncio.create_subprocess_shell(
            "git branch --show-current",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(BASE_DIR)
        )
        branch_out, _ = await branch_proc.communicate()
        branch = branch_out.decode("utf-8", errors="ignore").strip() or "main"

        pull_proc = await asyncio.create_subprocess_shell(
            f"git pull origin {branch}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(BASE_DIR)
        )
        pull_out, _ = await pull_proc.communicate()
        pull_msg = pull_out.decode("utf-8", errors="ignore").strip()

        venv_py = BASE_DIR / ".venv" / "Scripts" / "python.exe"
        if not venv_py.exists():
            venv_py = BASE_DIR / "venv" / "Scripts" / "python.exe"

        pip_msg = ""
        if venv_py.exists():
            req_file = BASE_DIR / "requirements.txt"
            if req_file.exists():
                pip_proc = await asyncio.create_subprocess_shell(
                    f'"{venv_py}" -m pip install -r requirements.txt --quiet',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(BASE_DIR)
                )
                try:
                    await asyncio.wait_for(pip_proc.communicate(), timeout=30.0)
                    pip_msg = "Đã đồng bộ requirements.txt."
                except asyncio.TimeoutError:
                    pip_msg = "Đồng bộ thư viện đang chạy ngầm."

        return {
            "status": "success",
            "message": "Cập nhật hệ thống thành công!",
            "details": pull_msg,
            "pip_status": pip_msg,
            "branch": branch
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Lỗi trong quá trình cập nhật: {str(e)}"
        }


@app.get("/static/qrcode.min.js")
def get_qrcode_js():
    js_file = Path(__file__).parent / "templates" / "qrcode.min.js"
    if js_file.exists():
        return FileResponse(js_file, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="Not found")


@app.get("/api/network-info")
def get_network_info():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 1))
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = '127.0.0.1'
    finally:
        s.close()
    port = int(os.environ.get("PORT", 8090))
    return {
        "local_ip": local_ip,
        "port": port,
        "lan_url": f"http://{local_ip}:{port}",
        "localhost_url": f"http://localhost:{port}"
    }


@app.get("/", response_class=HTMLResponse)
def get_home(tab: Optional[str] = None):
    html_file = Path(__file__).parent / "templates" / "index.html"
    if html_file.exists():
        with open(html_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Translator App Ready</h1>"



@app.post("/api/document/translate-stream")
async def translate_document_stream(
    file: UploadFile = File(...),
    source_lang: str = Form("auto"),
    target_lang: str = Form("vi"),
    tier: str = Form("bulk")
):
    import asyncio, json, uuid
    from fastapi.responses import StreamingResponse

    file_bytes = await file.read()
    filename = file.filename or "document.txt"
    doc_id = str(uuid.uuid4())[:8]

    async def event_generator():
        queue = asyncio.Queue()

        async def progress_callback(pct, msg, preview=""):
            await queue.put({"type": "progress", "percent": pct, "message": msg, "preview": preview})

        async def run_translation():
            try:
                # Giả định pool đã được định nghĩa trong app.py
                res = await translate_document(
                    filename=filename,
                    file_bytes=file_bytes,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    pool=pool,
                    tier=tier,
                    progress_callback=progress_callback
                )
                save_dir = DOCS_OUTPUT_DIR / doc_id
                save_dir.mkdir(parents=True, exist_ok=True)
                out_path = save_dir / res["out_filename"]
                with open(out_path, "wb") as f:
                    f.write(res["translated_bytes"])

                await queue.put({
                    "type": "done",
                    "percent": 100,
                    "message": "Hoàn tất dịch tài liệu!",
                    "download_url": f"/api/document/download/{doc_id}/{res['out_filename']}",
                    "filename": res["out_filename"],
                    "format": res["format"],
                    "preview_text": res.get("preview_text", ""),
                    "char_count": res.get("char_count", 0),
                    "paragraph_count": res.get("paragraph_count", 0)
                })
            except Exception as e:
                await queue.put({"type": "error", "message": str(e)})
            finally:
                await queue.put("[DONE]")

        asyncio.create_task(run_translation())

        while True:
            data = await queue.get()
            if data == "[DONE]":
                yield "data: [DONE]\n\n"
                break
            yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/document/download/{doc_id}/{filename}")
async def download_document(doc_id: str, filename: str):
    from fastapi.responses import FileResponse
    file_path = DOCS_OUTPUT_DIR / Path(doc_id).name / Path(filename).name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File không tồn tại")
    return FileResponse(path=str(file_path), filename=filename, media_type="application/octet-stream")


@app.post("/api/document/export-edited")
async def api_export_edited(req: Dict[str, Any] = Body(...)):
    import urllib.parse
    content = req.get("content", "")
    fmt = req.get("format", "docx")
    filename = req.get("filename", "document")
    out_bytes, out_filename, mime_type = export_edited_document(content, fmt, filename)
    encoded_filename = urllib.parse.quote(out_filename)
    return Response(
        content=out_bytes,
        media_type=mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{out_filename}"; filename*=UTF-8\'\'{encoded_filename}',
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8090))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)

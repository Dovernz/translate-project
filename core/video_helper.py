import os
import re
import sys
import time
import json
import uuid
import shutil
import asyncio
import importlib.metadata
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from urllib.parse import parse_qs, urlsplit
import yt_dlp
from core.sub_splitter import segment_subtitles

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

_youtube_diagnostic_lock = threading.Lock()
_youtube_diagnostic = {"event": "not_started", "timestamp": None, "events": []}


def _record_youtube_diagnostic(event: str, *, reset: bool = False):
    with _youtube_diagnostic_lock:
        events = [] if reset else list(_youtube_diagnostic["events"])
        if not events or events[-1] != event:
            events.append(event)
        _youtube_diagnostic.update(
            event=event,
            timestamp=datetime.now(timezone.utc).isoformat(),
            events=events[-12:],
        )


def get_youtube_diagnostics() -> Dict[str, Any]:
    with _youtube_diagnostic_lock:
        return dict(_youtube_diagnostic)


def _youtube_download_error_message(detail: str) -> str:
    events = set(get_youtube_diagnostics()["events"])
    if "client_http_429" in events:
        return (
            "YouTube đang giới hạn lượt truy cập từ máy chủ (HTTP 429). "
            "Hãy thử lại sau, tải tệp video lên, hoặc dùng phiên bản local."
        )
    if "client_http_403" in events:
        return (
            "YouTube từ chối yêu cầu từ máy chủ (HTTP 403) trước khi trả player response. "
            "Hãy thử lại sau, tải tệp video lên, hoặc dùng phiên bản local."
        )
    return detail


class _YouTubeDiagnosticLogger:
    def _record_message(self, message):
        text = str(message).lower()
        http_status = re.search(r"http error\s*(\d{3})", text)
        if http_status and http_status.group(1) in {"400", "403", "429", "500", "502", "503"}:
            _record_youtube_diagnostic(f"client_http_{http_status.group(1)}")
        elif "po token providers:" in text:
            _record_youtube_diagnostic("provider_loaded")
        elif "generating a " in text and " po token " in text:
            _record_youtube_diagnostic("token_generation_started")
        elif "failed while generating pot" in text or "failed to get a po token" in text:
            _record_youtube_diagnostic("token_generation_failed")
        elif "player response playability status:" in text:
            status_match = re.search(r"playability status:\s*([a-z_]+)", text)
            status = status_match.group(1) if status_match else "unknown"
            if status not in {
                "ok",
                "unplayable",
                "login_required",
                "error",
                "age_check_required",
                "content_check_required",
                "live_stream_offline",
                "video_unavailable",
                "private",
                "unlisted",
            }:
                status = "other"
            _record_youtube_diagnostic(f"client_status_{status}")
        elif "downloading mweb player api json" in text:
            _record_youtube_diagnostic("mweb_player_requested")
        elif "downloading tv player api json" in text:
            _record_youtube_diagnostic("tv_player_requested")
        elif "downloading web safari player api json" in text:
            _record_youtube_diagnostic("web_safari_player_requested")
        elif "failed to extract any player response" in text:
            _record_youtube_diagnostic("no_player_response")

    def debug(self, message):
        self._record_message(message)

    def info(self, message):
        self._record_message(message)

    def warning(self, message):
        self._record_message(message)

    def error(self, message):
        self._record_message(message)


def safe_log(msg: str):
    try:
        print(msg)
    except UnicodeEncodeError:
        try:
            print(msg.encode('ascii', errors='backslashreplace').decode('ascii'))
        except Exception:
            pass
    except Exception:
        pass

def extract_youtube_id(url: str) -> Optional[str]:
    parsed_url = urlsplit(url if "://" in url else f"//{url}")
    hostname = (parsed_url.hostname or "").lower().rstrip(".")
    is_youtube_host = (
        hostname == "youtu.be"
        or hostname.endswith(".youtu.be")
        or hostname == "youtube.com"
        or hostname.endswith(".youtube.com")
        or hostname == "youtube-nocookie.com"
        or hostname.endswith(".youtube-nocookie.com")
    )
    if not is_youtube_host:
        return None

    video_id = parse_qs(parsed_url.query).get("v", [None])[0]
    if video_id and re.fullmatch(r"[0-9A-Za-z_-]{11}", video_id):
        return video_id

    match = re.match(
        r"^/(?:embed|shorts|live|v)?/?([0-9A-Za-z_-]{11})(?:/|$)",
        parsed_url.path,
    )
    if match:
        return match.group(1)
    return None

def cleanup_storage(upload_dir: Path, output_dir: Path, max_age_minutes: int = 30):
    now = time.time()
    for d in [upload_dir, output_dir]:
        if not d.exists():
            continue
        for p in d.glob("*"):
            if p.name == ".gitkeep":
                continue
            try:
                if (
                    not p.is_symlink()
                    and p.is_file()
                    and now - p.stat().st_mtime > max_age_minutes * 60
                ):
                    p.unlink()
            except OSError as error:
                safe_log(f"[WARN] Could not remove expired temporary file {p}: {error}")

def get_video_info(url: str) -> Dict[str, Any]:
    yt_id = extract_youtube_id(url)
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'skip_download': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            data = ydl.extract_info(url, download=False)
        if not data:
            raise ValueError("Không lấy được thông tin video")
        return {
            "title": data.get("title", "Video không tên"),
            "duration": data.get("duration", 0),
            "thumbnail": data.get("thumbnail", "") or (f"https://img.youtube.com/vi/{yt_id}/hqdefault.jpg" if yt_id else ""),
            "uploader": data.get("uploader", ""),
            "extractor": data.get("extractor_key") or data.get("extractor"),
            "webpage_url": data.get("webpage_url", url),
            "youtube_id": yt_id
        }
    except Exception as e:
        safe_log(f"[WARN] get_video_info thất bại ({url}): {e}")
        return {
            "title": "Video Stream",
            "duration": 0,
            "thumbnail": f"https://img.youtube.com/vi/{yt_id}/hqdefault.jpg" if yt_id else "",
            "uploader": "External Stream",
            "extractor": None,
            "webpage_url": url,
            "youtube_id": yt_id,
            "error": str(e)
        }

def _bgutil_ytdlp_fallback_options(
    url: str,
    base_options: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Build the opt-in mweb/bgutil retry only when its runtime is installed."""
    if not extract_youtube_id(url):
        return None

    if os.getenv("BGUTIL_YTDLP_FALLBACK", "").strip().lower() not in {"1", "true", "yes"}:
        return None

    server_home = os.getenv("BGUTIL_YTDLP_SERVER_HOME", "").strip()
    if not server_home:
        safe_log("[WARN] BGUTIL YouTube fallback is enabled but BGUTIL_YTDLP_SERVER_HOME is not set")
        return None

    server_path = Path(server_home)
    if (
        not (server_path / "src" / "generate_once.ts").is_file()
        or not (server_path / "node_modules").is_dir()
    ):
        safe_log(f"[WARN] BGUTIL YouTube fallback provider files are missing from {server_path}")
        return None
    if not shutil.which("deno"):
        safe_log("[WARN] BGUTIL YouTube fallback is enabled but Deno is unavailable")
        return None
    try:
        importlib.metadata.version("bgutil-ytdlp-pot-provider")
    except importlib.metadata.PackageNotFoundError:
        safe_log("[WARN] BGUTIL YouTube fallback is enabled but the yt-dlp provider package is not installed")
        return None

    return {
        **base_options,
        "verbose": True,
        "logger": _YouTubeDiagnosticLogger(),
        "extractor_args": {
            "youtube": {"player_client": ["mweb", "tv", "web_safari"]},
            "youtubepot-bgutilscript": {"server_home": [str(server_path)]},
        },
    }


def _streamlink_fallback_eligible(url: str, download_errors: List[str]) -> bool:
    if extract_youtube_id(url):
        return False

    combined_errors = " ".join(download_errors).lower()
    if any(
        marker in combined_errors
        for marker in (
            "http error 401",
            "http error 403",
            "http error 429",
            "login_required",
            "sign in to confirm",
            "drm",
            "private video",
            "age-restricted",
        )
    ):
        return False

    return any(
        marker in combined_errors
        for marker in (
            "unsupported url",
            "no suitable extractor",
            "no yt-dlp extractor matched",
            "no video formats found",
            "requested format is not available",
        )
    )


def _download_with_streamlink(url: str, output_path: Path):
    from streamlink import Streamlink

    session = Streamlink()
    session.set_option("stream-segment-timeout", 30)
    stream = session.streams(url).get("best")
    if stream is None:
        raise ValueError("Streamlink không tìm thấy luồng video công khai phù hợp")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    stream_path = output_path.with_suffix(".stream")
    byte_limit = 4 * 1024 * 1024 * 1024
    deadline = time.monotonic() + 3 * 60 * 60
    try:
        with stream.open() as stream_reader, stream_path.open("wb") as stream_file:
            while chunk := stream_reader.read(1024 * 1024):
                if time.monotonic() >= deadline:
                    raise TimeoutError("Streamlink vượt giới hạn tải 3 giờ")
                if stream_file.tell() + len(chunk) > byte_limit:
                    raise ValueError("Streamlink vượt giới hạn dung lượng 4 GiB")
                stream_file.write(chunk)

        if not stream_path.is_file() or stream_path.stat().st_size == 0:
            raise ValueError("Streamlink không nhận được dữ liệu video")

        subprocess.run(
            [
                "ffmpeg", "-y", "-threads", "1", "-i", str(stream_path),
                "-c", "copy", "-movflags", "+faststart", str(output_path),
            ],
            capture_output=True,
            check=True,
            timeout=300,
        )
        if not output_path.is_file() or output_path.stat().st_size == 0:
            raise ValueError("FFmpeg không tạo được video MP4 từ luồng")
    finally:
        try:
            stream_path.unlink(missing_ok=True)
        except OSError as e:
            safe_log(f"[WARN] Không thể xóa luồng tạm {stream_path}: {e}")


def extract_subtitles_from_url(url: str, output_dir: Path) -> Optional[List[Dict[str, Any]]]:
    """
    Trích xuất phụ đề gốc trực tiếp từ link và ghép câu hoàn chỉnh (Zero-Video Download).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    tmp_id = str(uuid.uuid4())[:8]
    sub_path_template = str(output_dir / f"{tmp_id}_sub.%(ext)s")
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['en', 'vi', 'ko', 'ja', 'zh'],
        'subtitlesformat': 'vtt',
        'outtmpl': sub_path_template,
        'socket_timeout': 8,
    }
    try:
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except Exception as e:
            safe_log(f"[WARN] Tải một số phụ đề thất bại, kiểm tra phụ đề đã tải được: {e}")

        vtt_files = list(output_dir.glob(f"{tmp_id}_sub.*.vtt"))
        if not vtt_files:
            return None
            
        vtt_file = vtt_files[0]
        with open(vtt_file, "r", encoding="utf-8", errors="replace") as f:
            vtt_content = f.read()
            
        blocks = vtt_content.split('\n\n')
        raw_cues = []
        for b in blocks:
            lines = [l.strip() for l in b.strip().split('\n') if l.strip()]
            if not lines:
                continue
            time_line = None
            text_lines = []
            for l in lines:
                if '-->' in l:
                    time_line = l
                elif time_line:
                    clean = re.sub(r'<[^>]+>', '', l).strip()
                    if clean and not clean.startswith('align:') and not clean.startswith('position:'):
                        text_lines.append(clean)
            if time_line and text_lines:
                t_match = re.search(r'(\d{2}:\d{2}:\d{2}\.\d{3}|\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3}|\d{2}:\d{2}\.\d{3})', time_line)
                if t_match:
                    raw_cues.append((t_match.group(1), t_match.group(2), text_lines[-1]))

        # Hợp nhất các câu rolling captions thành câu hoàn chỉnh
        merged = []
        for s, e, t in raw_cues:
            if not merged:
                merged.append([s, e, t])
            else:
                last = merged[-1]
                if t.startswith(last[2]) and len(t) > len(last[2]):
                    last[1] = e
                    last[2] = t
                elif last[2].startswith(t):
                    last[1] = e
                else:
                    merged.append([s, e, t])

        subs = []
        for idx, (s_str, e_str, txt) in enumerate(merged, 1):
            s_sec = parse_time_to_seconds(s_str)
            e_sec = parse_time_to_seconds(e_str)
            subs.append({
                "id": idx,
                "start": s_sec,
                "end": max(e_sec, s_sec + 1.2),
                "start_str": seconds_to_vtt_time(s_sec),
                "end_str": seconds_to_vtt_time(max(e_sec, s_sec + 1.2)),
                "original": txt,
                "translated": ""
            })

        if len(subs) > 0:
            return segment_subtitles(subs, max_duration=6.0)
        return None
    except Exception as e:
        safe_log(f"[DEBUG] Lỗi trích xuất auto-subs: {e}")
        return None
    finally:
        for vtt_file in output_dir.glob(f"{tmp_id}_sub.*.vtt"):
            try:
                vtt_file.unlink(missing_ok=True)
            except OSError as e:
                safe_log(f"[WARN] Không thể xóa phụ đề tạm {vtt_file}: {e}")

def download_video_from_url(url: str, output_dir: Path) -> Dict[str, Any]:
    _record_youtube_diagnostic("download_started", reset=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    video_id = str(uuid.uuid4())[:8]
    output_template = str(output_dir / f"{video_id}_%(title).50s.%(ext)s")

    base_ydl_opts = {
        'format': 'bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'outtmpl': output_template,
    }
    ydl_profiles = [base_ydl_opts]
    bgutil_profile = _bgutil_ytdlp_fallback_options(url, base_ydl_opts)
    if bgutil_profile:
        ydl_profiles.append(bgutil_profile)
        _record_youtube_diagnostic("fallback_ready")
    download_errors = []

    def remove_partial_downloads():
        for path in output_dir.glob(f"{video_id}_*"):
            try:
                path.unlink(missing_ok=True)
            except OSError as e:
                safe_log(f"[WARN] Không thể xóa video tải dở {path}: {e}")

    for profile_index, ydl_opts in enumerate(ydl_profiles):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            matches = [
                path for path in output_dir.glob(f"{video_id}_*")
                if path.is_file() and path.stat().st_size > 0
            ]
            video_matches = [
                path for path in matches
                if path.suffix.lower() in [".mp4", ".mkv", ".webm", ".mov", ".m4v"]
            ]
            if video_matches:
                saved_file = video_matches[0]
                audio_path = output_dir / f"{video_id}_audio.mp3"
                extract_audio_from_video(saved_file, audio_path)

                return {
                    "success": True,
                    "video_id": video_id,
                    "filename": saved_file.name,
                    "video_url": f"/uploads/{saved_file.name}",
                    "size_bytes": saved_file.stat().st_size
                }
            if matches:
                saved_file = matches[0]
                return {
                    "success": True,
                    "video_id": video_id,
                    "filename": saved_file.name,
                    "video_url": f"/uploads/{saved_file.name}",
                    "size_bytes": saved_file.stat().st_size
                }

            download_errors.append("yt-dlp không tạo được file video")
        except Exception as e:
            download_errors.append(str(e))
            safe_log(f"[WARN] Tải video thất bại (profile {profile_index + 1}): {e}")

        remove_partial_downloads()

    if _streamlink_fallback_eligible(url, download_errors):
        streamlink_path = output_dir / f"{video_id}_streamlink.mp4"
        try:
            _download_with_streamlink(url, streamlink_path)
            audio_path = output_dir / f"{video_id}_audio.mp3"
            extract_audio_from_video(streamlink_path, audio_path)
            return {
                "success": True,
                "video_id": video_id,
                "filename": streamlink_path.name,
                "video_url": f"/uploads/{streamlink_path.name}",
                "size_bytes": streamlink_path.stat().st_size,
                "extractor": "Streamlink",
            }
        except Exception as e:
            download_errors.append(f"Streamlink fallback: {e}")
            safe_log(f"[WARN] Streamlink fallback thất bại: {e}")
            try:
                streamlink_path.unlink(missing_ok=True)
            except OSError as cleanup_error:
                safe_log(f"[WARN] Không thể xóa video Streamlink tải dở {streamlink_path}: {cleanup_error}")

    fallback_errors = []
    audio_template = str(output_dir / f"{video_id}_audio.%(ext)s")
    base_audio_opts = {
        'format': 'bestaudio/ba/b/best',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'outtmpl': audio_template,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    audio_profiles = [base_audio_opts]
    bgutil_audio_profile = _bgutil_ytdlp_fallback_options(url, base_audio_opts)
    if bgutil_audio_profile:
        audio_profiles.append(bgutil_audio_profile)

    for profile_index, ydl_audio_opts in enumerate(audio_profiles):
        try:
            with yt_dlp.YoutubeDL(ydl_audio_opts) as ydl:
                ydl.download([url])

            audio_matches = [
                path for path in output_dir.glob(f"{video_id}_audio.mp3")
                if path.is_file() and path.stat().st_size > 0
            ]
            if audio_matches:
                audio_file = audio_matches[0]
                return {
                    "success": True,
                    "video_id": video_id,
                    "filename": audio_file.name,
                    "video_url": "",
                    "is_audio_only": True,
                    "size_bytes": audio_file.stat().st_size
                }

            fallback_errors.append("yt-dlp không tạo được file audio MP3")
        except Exception as e:
            fallback_errors.append(str(e))
            safe_log(f"[ERROR] Fallback audio thất bại (profile {profile_index + 1}): {e}")

        remove_partial_downloads()

    err_msg = download_errors[-1] if download_errors else "Không thể tải video từ đường dẫn này."
    fb_err = fallback_errors[-1] if fallback_errors else ""
    detail_err = f"Lỗi tải video: {err_msg}" + (f" | Lỗi fallback audio: {fb_err}" if fb_err else "")
    return {
        "success": False,
        "error": _youtube_download_error_message(detail_err),
        "detail": detail_err,
    }

def extract_audio_from_video(video_path: Path, output_audio: Path) -> bool:
    output_audio.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-threads", "1",
        "-i", str(video_path),
        "-vn",
        "-acodec", "libmp3lame",
        "-ar", "16000",
        "-ac", "1",
        "-q:a", "4",
        str(output_audio)
    ]
    try:
        subprocess.run(cmd, capture_output=True, check=True, timeout=120)
        return output_audio.exists() and output_audio.stat().st_size > 0
    except Exception as e:
        safe_log(f"[ERROR] Trích xuất audio thất bại: {e}")
        return False

def parse_time_to_seconds(ts: str) -> float:
    ts = ts.strip().replace(",", ".")
    parts = ts.split(":")
    if len(parts) == 3:
        return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    elif len(parts) == 2:
        return float(parts[0]) * 60 + float(parts[1])
    try:
        return float(ts)
    except Exception:
        return 0.0

def seconds_to_srt_time(sec: float) -> str:
    hours = int(sec // 3600)
    minutes = int((sec % 3600) // 60)
    secs = int(sec % 60)
    millis = int(round((sec - int(sec)) * 1000))
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def seconds_to_vtt_time(sec: float) -> str:
    hours = int(sec // 3600)
    minutes = int((sec % 3600) // 60)
    secs = int(sec % 60)
    millis = int(round((sec - int(sec)) * 1000))
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

def clean_gemini_json(raw_text: str) -> str:
    text = raw_text.strip()
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0].strip()
    return text

def parse_subtitles_from_ai(ai_output: str) -> List[Dict[str, Any]]:
    cleaned = clean_gemini_json(ai_output)
    try:
        items = json.loads(cleaned)
        if isinstance(items, list):
            result = []
            for idx, it in enumerate(items, 1):
                start_sec = parse_time_to_seconds(str(it.get("start", "0")))
                end_sec = parse_time_to_seconds(str(it.get("end", str(start_sec + 3.0))))
                item_dict = {
                    "id": idx,
                    "start": start_sec,
                    "end": end_sec,
                    "start_str": seconds_to_vtt_time(start_sec),
                    "end_str": seconds_to_vtt_time(end_sec),
                    "original": it.get("original", "").strip(),
                    "translated": it.get("translated", it.get("text", "")).strip()
                }
                if "translations" in it:
                    item_dict["translations"] = it.get("translations")
                result.append(item_dict)
            return segment_subtitles(result, max_duration=6.0)
    except Exception:
        pass

    pattern = r'(?:\[)?(\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d+)?)\s*(?:-->|-)\s*(\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d+)?)(?:\])?\s*[:\-|]?\s*(.*?)(?=\n(?:\[)?\d{1,2}:\d{2}|$)'
    matches = re.findall(pattern, ai_output, re.DOTALL)
    result = []
    for idx, m in enumerate(matches, 1):
        s_sec = parse_time_to_seconds(m[0])
        e_sec = parse_time_to_seconds(m[1])
        content = m[2].strip()
        orig, trans = "", content
        if " | " in content:
            parts = content.split(" | ", 1)
            orig, trans = parts[0].strip(), parts[1].strip()
        result.append({
            "id": idx,
            "start": s_sec,
            "end": e_sec,
            "start_str": seconds_to_vtt_time(s_sec),
            "end_str": seconds_to_vtt_time(e_sec),
            "original": orig,
            "translated": trans
        })
    return segment_subtitles(result, max_duration=6.0)

def export_srt(subtitles: List[Dict[str, Any]], output_path: Path, lang: Optional[str] = None):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for idx, sub in enumerate(subtitles, 1):
            s_str = seconds_to_srt_time(sub["start"])
            e_str = seconds_to_srt_time(sub["end"])
            text = None
            if lang and isinstance(sub.get("translations"), dict) and lang in sub["translations"]:
                text = sub["translations"][lang]
            if not text:
                text = sub.get("translated") or sub.get("text") or ""
            f.write(f"{idx}\n{s_str} --> {e_str}\n{text}\n\n")

def export_vtt(subtitles: List[Dict[str, Any]], output_path: Path, lang: Optional[str] = None):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        for idx, sub in enumerate(subtitles, 1):
            s_str = seconds_to_vtt_time(sub["start"])
            e_str = seconds_to_vtt_time(sub["end"])
            text = None
            if lang and isinstance(sub.get("translations"), dict) and lang in sub["translations"]:
                text = sub["translations"][lang]
            if not text:
                text = sub.get("translated") or sub.get("text") or ""
            f.write(f"{idx}\n{s_str} --> {e_str}\n{text}\n\n")

def hex_color_to_ass(hex_color: str) -> str:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 6:
        r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6]
        return f"&H00{b}{g}{r}"
    return "&H00FFFFFF"

def burn_subtitles_to_video(
    video_path: Path,
    srt_path: Path,
    output_video: Path,
    font_size: int = 22,
    text_color: str = "#FBBF24",
    bg_color: str = "#000000",
    bg_opacity: float = 0.85,
    mask_old_sub: bool = True,
    vertical_margin: int = 35
) -> bool:
    output_video.parent.mkdir(parents=True, exist_ok=True)
    primary_color = hex_color_to_ass(text_color)
    alpha_int = int(round((1.0 - bg_opacity) * 255))
    alpha_hex = f"{alpha_int:02X}"
    bg_hex = bg_color.lstrip("#")
    if len(bg_hex) == 6:
        br, bg, bb = bg_hex[0:2], bg_hex[2:4], bg_hex[4:6]
        back_color = f"&H{alpha_hex}{bb}{bg}{br}"
    else:
        back_color = f"&H{alpha_hex}000000"

    srt_clean = str(srt_path).replace("\\", "/").replace(":", "\\:")
    border_style = 3 if mask_old_sub else 1
    outline_val = 0 if mask_old_sub else 2
    
    sub_filter = (
        f"subtitles='{srt_clean}':force_style="
        f"'FontName=Arial,FontSize={font_size},"
        f"PrimaryColour={primary_color},"
        f"BackColour={back_color},"
        f"BorderStyle={border_style},"
        f"Outline={outline_val},"
        f"Shadow=0,"
        f"Alignment=2,"
        f"MarginV={vertical_margin}'"
    )

    cmd = [
        "ffmpeg", "-y",
        "-threads", "1",
        "-i", str(video_path),
        "-vf", sub_filter,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "22",
        "-c:a", "copy",
        str(output_video)
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if proc.returncode != 0:
            safe_log(f"[FFMPEG ERROR] {proc.stderr}")
            return False
        return output_video.exists() and output_video.stat().st_size > 0
    except Exception as e:
        safe_log(f"[ERROR] Burn video failed: {e}")
        return False

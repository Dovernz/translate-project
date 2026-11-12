import os
import re
import sys
import time
import json
import uuid
import shutil
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
import yt_dlp

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
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed\/|shorts\/|youtu.be\/)([0-9A-Za-z_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
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
                if p.is_file() and (now - p.stat().st_mtime > max_age_minutes * 60):
                    p.unlink()
            except Exception:
                pass

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
            "webpage_url": url,
            "youtube_id": yt_id,
            "error": str(e)
        }

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

        return subs if len(subs) > 0 else None
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
    return {"success": False, "error": detail_err}

def extract_audio_from_video(video_path: Path, output_audio: Path) -> bool:
    output_audio.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
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
            return result
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
    return result

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

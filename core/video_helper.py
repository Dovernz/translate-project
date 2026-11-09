import os
import re
import json
import uuid
import shutil
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

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

def get_video_info(url: str) -> Dict[str, Any]:
    yt_id = extract_youtube_id(url)
    cmd = [
        "yt-dlp",
        "--dump-single-json",
        "--no-playlist",
        "--skip-download",
        url
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=20)
        data = json.loads(res.stdout)
        return {
            "title": data.get("title", "Video không tên"),
            "duration": data.get("duration", 0),
            "thumbnail": data.get("thumbnail", ""),
            "uploader": data.get("uploader", ""),
            "webpage_url": data.get("webpage_url", url),
            "youtube_id": yt_id
        }
    except Exception as e:
        return {
            "title": "Video Stream",
            "duration": 0,
            "thumbnail": f"https://img.youtube.com/vi/{yt_id}/hqdefault.jpg" if yt_id else "",
            "uploader": "External Stream",
            "webpage_url": url,
            "youtube_id": yt_id,
            "error": str(e)
        }

def download_video_from_url(url: str, output_dir: Path) -> Dict[str, Any]:
    """
    Tải video trực tuyến (YouTube, Vimeo, MP4 direct) bằng yt-dlp vào thư mục uploads
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    video_id = str(uuid.uuid4())[:8]
    output_template = str(output_dir / f"{video_id}_%(title).50s.%(ext)s")
    
    cmd = [
        "yt-dlp",
        "-f", "bv*[height<=720]+ba/b[height<=720]/best",
        "--merge-output-format", "mp4",
        "--no-playlist",
        "-o", output_template,
        url
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=180)
        matches = list(output_dir.glob(f"{video_id}_*"))
        if matches:
            saved_file = matches[0]
            # Trích xuất audio luôn để sẵn sàng cho AI quét
            audio_path = output_dir / f"{video_id}_audio.mp3"
            extract_audio_from_video(saved_file, audio_path)
            
            return {
                "success": True,
                "video_id": video_id,
                "filename": saved_file.name,
                "video_url": f"/uploads/{saved_file.name}",
                "size_bytes": saved_file.stat().st_size
            }
    except Exception as e:
        print(f"[ERROR] Tải video thất bại: {e}")
        # Thử fallback chỉ tải audio nếu định dạng video quá nặng
        try:
            audio_template = str(output_dir / f"{video_id}_audio.%(ext)s")
            cmd_audio = ["yt-dlp", "-x", "--audio-format", "mp3", "--no-playlist", "-o", audio_template, url]
            subprocess.run(cmd_audio, capture_output=True, text=True, check=True, timeout=90)
            return {
                "success": True,
                "video_id": video_id,
                "filename": f"Audio_{video_id}.mp3",
                "video_url": "",
                "is_audio_only": True
            }
        except Exception as e2:
            print(f"[ERROR] Fallback audio thất bại: {e2}")

    return {"success": False, "error": "Không thể tải video từ đường dẫn này."}

def extract_audio_from_video(video_path: Path, output_audio: Path) -> bool:
    """
    Trích xuất audio tối ưu cho AI nhận diện giọng nói (16kHz Mono MP3)
    """
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
        print(f"[ERROR] Trích xuất audio thất bại: {e}")
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
                result.append({
                    "id": idx,
                    "start": start_sec,
                    "end": end_sec,
                    "start_str": seconds_to_vtt_time(start_sec),
                    "end_str": seconds_to_vtt_time(end_sec),
                    "original": it.get("original", "").strip(),
                    "translated": it.get("translated", it.get("text", "")).strip()
                })
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

def export_srt(subtitles: List[Dict[str, Any]], output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for idx, sub in enumerate(subtitles, 1):
            s_str = seconds_to_srt_time(sub["start"])
            e_str = seconds_to_srt_time(sub["end"])
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
            print(f"[FFMPEG ERROR] {proc.stderr}")
            return False
        return output_video.exists() and output_video.stat().st_size > 0
    except Exception as e:
        print(f"[ERROR] Burn video failed: {e}")
        return False

import re
import json
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import HTTPException
from pydantic import BaseModel

from core.video_helper import (
    extract_subtitles_from_url,
    extract_audio_from_video,
    parse_subtitles_from_ai,
    export_srt,
    export_vtt,
    clean_gemini_json
)

SUPPORTED_VIDEO_LANGUAGES = {
    "vi": "Tiếng Việt",
    "en": "Tiếng Anh (English)",
    "ja": "Tiếng Nhật (Japanese)",
    "ko": "Tiếng Hàn (Korean)",
    "zh": "Tiếng Trung (Chinese)",
    "fr": "Tiếng Pháp (French)",
    "de": "Tiếng Đức (German)",
    "es": "Tiếng Tây Ban Nha (Spanish)",
    "ru": "Tiếng Nga (Russian)",
    "th": "Tiếng Thái (Thai)",
    "id": "Tiếng Indonesia",
    "it": "Tiếng Ý (Italian)",
    "pt": "Tiếng Bồ Đào Nha (Portuguese)"
}


class AutoSubRequest(BaseModel):
    video_id: str
    target_lang: str = "vi"
    target_langs: Optional[List[str]] = None
    url: Optional[str] = ""


class TranslateSubtitlesRequest(BaseModel):
    video_id: str
    subtitles: List[Dict[str, Any]]
    target_lang: str = "vi"
    target_langs: Optional[List[str]] = None


async def process_auto_subtitle(req: AutoSubRequest, pool, loop, upload_dir: Path, output_dir: Path) -> Dict[str, Any]:
    selected_langs = req.target_langs if (req.target_langs and len(req.target_langs) > 0) else [req.target_lang]
    primary_lang = req.target_lang or selected_langs[0]
    if primary_lang not in selected_langs:
        selected_langs.insert(0, primary_lang)

    is_multi = len(selected_langs) > 1
    primary_name = SUPPORTED_VIDEO_LANGUAGES.get(primary_lang, primary_lang)
    all_names = ", ".join([f"{c} ({SUPPORTED_VIDEO_LANGUAGES.get(c, c)})" for c in selected_langs])

    extracted_subs = None
    mode = ""

    # ƯU TIÊN 1: Nếu có URL, thử trích xuất phụ đề gốc có sẵn (Zero-Download)
    if req.url:
        extracted_subs = await loop.run_in_executor(None, extract_subtitles_from_url, req.url, upload_dir)
        if extracted_subs and len(extracted_subs) > 0:
            mode = "zero_download_caption"
            chunk_size = 25
            chunks = [extracted_subs[i:i + chunk_size] for i in range(0, len(extracted_subs), chunk_size)]

            async def translate_chunk(chunk):
                batch_lines = [f"{s['id']}. {s['original']}" for s in chunk]
                if not is_multi:
                    prompt = (
                        f"Bạn là chuyên gia dịch phụ đề phim. Hãy dịch từng câu sau sang {primary_name}.\n"
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
                            tr = sub_map.get(s["id"], s["original"])
                            s["translated"] = tr
                            if "translations" not in s or not isinstance(s["translations"], dict):
                                s["translations"] = {}
                            s["translations"][primary_lang] = tr
                    except Exception as ex:
                        for s in chunk:
                            s["translated"] = s["original"]
                            if "translations" not in s:
                                s["translations"] = {}
                            s["translations"][primary_lang] = s["original"]
                else:
                    langs_sample = json.dumps({c: f"Bản dịch {SUPPORTED_VIDEO_LANGUAGES.get(c, c)}" for c in selected_langs}, ensure_ascii=False)
                    prompt = (
                        f"Bạn là chuyên gia dịch phụ đề phim đa ngôn ngữ. Dịch từng câu sau sang các ngôn ngữ: {all_names}.\n"
                        f"Định dạng trả về BẮT BUỘC dạng JSON Object có key là số thứ tự câu:\n"
                        f"{{\"1\": {langs_sample}}}\n"
                        f"Chỉ trả về JSON thuần túy, không giải thích:\n"
                        + "\n".join(batch_lines)
                    )
                    try:
                        res_text = await pool.generate_content(prompt, tier="bulk")
                        cleaned = clean_gemini_json(res_text)
                        data_map = json.loads(cleaned)
                        for s in chunk:
                            cid = str(s["id"])
                            if cid in data_map and isinstance(data_map[cid], dict):
                                s["translations"] = data_map[cid]
                                s["translated"] = data_map[cid].get(primary_lang, s["original"])
                            else:
                                if "translations" not in s:
                                    s["translations"] = {}
                                s["translations"][primary_lang] = s["original"]
                                s["translated"] = s["original"]
                    except Exception as ex:
                        for s in chunk:
                            s["translated"] = s["original"]
                            if "translations" not in s:
                                s["translations"] = {}
                            s["translations"][primary_lang] = s["original"]

            await asyncio.gather(*(translate_chunk(c) for c in chunks))

    # ƯU TIÊN 2: Quét bằng Gemini Multimodal Audio Model nếu chưa có sub
    if not extracted_subs:
        mode = "multimodal_audio"
        audio_path = upload_dir / f"{req.video_id}_audio.mp3"
        if not audio_path.exists():
            matches = list(upload_dir.glob(f"{req.video_id}_*"))
            if not matches:
                raise HTTPException(status_code=404, detail="Không tìm thấy dữ liệu video/audio.")
            video_path = matches[0]
            success = await loop.run_in_executor(None, extract_audio_from_video, video_path, audio_path)
            if not success or not audio_path.exists():
                raise HTTPException(status_code=500, detail="Không thể trích xuất âm thanh từ video.")

        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
        try:
            audio_path.unlink(missing_ok=True)
        except OSError as cleanup_error:
            print(f"[WARN] Could not remove intermediate audio {audio_path}: {cleanup_error}")

        if not is_multi:
            prompt = (
                f"Bạn là chuyên gia nhận diện giọng nói và dịch phụ đề video tự động. "
                f"Hãy lắng nghe toàn bộ file âm thanh và trích xuất từng câu thoại kèm mốc thời gian, sau đó dịch sang {primary_name}. "
                f"Yêu cầu xuất ra BẮT BUỘC dạng mảng JSON thuần túy (JSON Array), KHÔNG viết giải thích hay bọc thẻ văn bản khác:\n"
                f"[\n"
                f'  {{"start": "00:01.000", "end": "00:04.500", "original": "câu thoại gốc", "translated": "bản dịch {primary_name}"}},\n'
                f'  {{"start": "00:05.000", "end": "00:08.200", "original": "câu tiếp theo", "translated": "bản dịch tiếp theo"}}\n'
                f"]"
            )
        else:
            langs_sample = json.dumps({c: f"bản dịch {SUPPORTED_VIDEO_LANGUAGES.get(c, c)}" for c in selected_langs}, ensure_ascii=False)
            prompt = (
                f"Bạn là chuyên gia nhận diện giọng nói và dịch phụ đề video đa ngôn ngữ. "
                f"Hãy lắng nghe file âm thanh, trích xuất từng câu thoại kèm mốc thời gian, và dịch sang các ngôn ngữ: {all_names}. "
                f"Yêu cầu xuất ra BẮT BUỘC dạng mảng JSON thuần túy (JSON Array), KHÔNG viết giải thích hay bọc thẻ văn bản khác:\n"
                f"[\n"
                f'  {{"start": "00:01.000", "end": "00:04.500", "original": "câu thoại gốc", "translations": {langs_sample}, "translated": "bản dịch {primary_name}"}}\n'
                f"]"
            )

        try:
            ai_response = await pool.generate_multimodal(
                audio_bytes=audio_bytes,
                mime_type="audio/mp3",
                prompt=prompt
            )
            extracted_subs = parse_subtitles_from_ai(ai_response)
            if not extracted_subs:
                extracted_subs = [{
                    "id": 1,
                    "start": 1.0,
                    "end": 5.0,
                    "start_str": "00:00:01.000",
                    "end_str": "00:00:05.000",
                    "original": "Audio recognized",
                    "translated": f"Đã nhận diện âm thanh ({primary_name})",
                    "translations": {primary_lang: f"Đã nhận diện âm thanh ({primary_name})"}
                }]
            for sub in extracted_subs:
                if "translations" not in sub or not isinstance(sub["translations"], dict):
                    sub["translations"] = {primary_lang: sub.get("translated", "")}
                elif primary_lang in sub["translations"]:
                    sub["translated"] = sub["translations"][primary_lang]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Lỗi AI Subtitling: {str(e)}")

    # Xuất các file phụ đề SRT & VTT
    srt_path = output_dir / f"{req.video_id}.srt"
    vtt_path = output_dir / f"{req.video_id}.vtt"
    export_srt(extracted_subs, srt_path, lang=primary_lang)
    export_vtt(extracted_subs, vtt_path, lang=primary_lang)

    lang_urls = {}
    for l_code in selected_langs:
        l_srt = output_dir / f"{req.video_id}_{l_code}.srt"
        l_vtt = output_dir / f"{req.video_id}_{l_code}.vtt"
        export_srt(extracted_subs, l_srt, lang=l_code)
        export_vtt(extracted_subs, l_vtt, lang=l_code)
        lang_urls[l_code] = {
            "srt_url": f"/outputs/{req.video_id}_{l_code}.srt",
            "vtt_url": f"/outputs/{req.video_id}_{l_code}.vtt"
        }

    return {
        "video_id": req.video_id,
        "subtitles": extracted_subs,
        "target_lang": primary_lang,
        "target_langs": selected_langs,
        "lang_urls": lang_urls,
        "srt_url": f"/outputs/{req.video_id}.srt",
        "vtt_url": f"/outputs/{req.video_id}.vtt",
        "mode": mode
    }


async def process_translate_subtitles(req: TranslateSubtitlesRequest, pool, output_dir: Path) -> Dict[str, Any]:
    if not req.subtitles:
        raise HTTPException(status_code=400, detail="Không có danh sách phụ đề để dịch.")

    target_code = req.target_lang
    target_name = SUPPORTED_VIDEO_LANGUAGES.get(target_code, target_code)

    subtitles = req.subtitles
    chunk_size = 30
    chunks = [subtitles[i:i + chunk_size] for i in range(0, len(subtitles), chunk_size)]

    async def translate_chunk(chunk):
        batch_lines = [f"{s.get('id', i+1)}. {s.get('original') or s.get('translated') or ''}" for i, s in enumerate(chunk)]
        prompt = (
            f"Bạn là chuyên gia dịch phụ đề phim. Hãy dịch từng câu sau sang {target_name}.\n"
            f"Yêu cầu: Giữ nguyên số thứ tự và định dạng '[Số]. [Bản dịch]'. Ngắn gọn, tự nhiên chuẩn phụ đề.\n"
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
            for i, s in enumerate(chunk):
                sid = s.get("id", i + 1)
                tr = sub_map.get(sid, s.get("original") or s.get("translated") or "")
                s["translated"] = tr
                if "translations" not in s or not isinstance(s["translations"], dict):
                    s["translations"] = {}
                s["translations"][target_code] = tr
        except Exception as ex:
            print(f"[DEBUG] Lỗi dịch sub chunk sang {target_code}: {ex}")

    await asyncio.gather(*(translate_chunk(c) for c in chunks))

    # Cập nhật SRT và VTT
    srt_path = output_dir / f"{req.video_id}_{target_code}.srt"
    vtt_path = output_dir / f"{req.video_id}_{target_code}.vtt"
    export_srt(subtitles, srt_path, lang=target_code)
    export_vtt(subtitles, vtt_path, lang=target_code)

    # Cập nhật file mặc định
    export_srt(subtitles, output_dir / f"{req.video_id}.srt", lang=target_code)
    export_vtt(subtitles, output_dir / f"{req.video_id}.vtt", lang=target_code)

    return {
        "status": "success",
        "video_id": req.video_id,
        "target_lang": target_code,
        "subtitles": subtitles,
        "srt_url": f"/outputs/{req.video_id}_{target_code}.srt",
        "vtt_url": f"/outputs/{req.video_id}_{target_code}.vtt"
    }
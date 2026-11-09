import io
import re
import os
import json
import asyncio
import zipfile
from urllib.parse import urljoin, urlparse
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple
import httpx
from PIL import Image, ImageDraw, ImageFont

# Candidate font paths supporting Vietnamese diacritics
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/tahoma.ttf",
]

def get_best_font(size: int, font_path: Optional[str] = None) -> ImageFont.FreeTypeFont:
    """Load the best available TTF font with fallback to default PIL font."""
    if font_path and os.path.exists(font_path):
        try:
            return ImageFont.truetype(font_path, size=size)
        except Exception:
            pass

    for candidate in FONT_CANDIDATES:
        if os.path.exists(candidate):
            try:
                return ImageFont.truetype(candidate, size=size)
            except Exception:
                continue

    # Fallback to default
    try:
        return ImageFont.load_default()
    except Exception:
        return ImageFont.load_default()

def natural_sort_key(s: Union[str, Path]):
    """Natural sort key for filenames (e.g. page_1, page_2, ..., page_10)."""
    name = str(s)
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', name)]

def detect_image_mime(image_bytes: bytes) -> str:
    """Detect mime type from image header bytes."""
    if image_bytes.startswith(b'\xff\xd8\xff'):
        return "image/jpeg"
    elif image_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
        return "image/png"
    elif image_bytes.startswith(b'RIFF') and b'WEBP' in image_bytes[:16]:
        return "image/webp"
    elif image_bytes.startswith(b'GIF8'):
        return "image/gif"
    return "image/jpeg"

async def detect_and_translate_manga(
    image_bytes: bytes,
    target_lang: str = "vi",
    pool = None
) -> List[Dict[str, Any]]:
    """
    Detect speech bubbles/dialogue in manga/comic page and translate using Gemini Vision.
    Returns:
        List of dicts: [{"box_2d": [ymin, xmin, ymax, xmax], "original": str, "translated": str}]
        Coordinates are normalized to 0-1000.
    """
    if pool is None:
        raise ValueError("KeyPool instance must be provided to detect_and_translate_manga")

    mime_type = detect_image_mime(image_bytes)

    lang_map = {
        "vi": "Tiếng Việt tự nhiên, phù hợp văn phong truyện tranh (xưng hô chuẩn mực theo sắc thái, biểu cảm)",
        "en": "Natural English suitable for comics/manga dialogues",
        "ja": "Natural Japanese manga dialogue style",
        "ko": "Natural Korean manhwa dialogue style",
        "zh": "Natural Chinese manhua dialogue style",
        "fr": "Natural French comic dialogue",
        "de": "Natural German comic dialogue"
    }
    target_lang_desc = lang_map.get(target_lang, f"ngôn ngữ {target_lang}")

    system_instruction = (
        "Bạn là Chuyên gia Dịch thuật Truyện tranh (Manga, Manhwa, Manhua, Comics) đa ngôn ngữ chuyên nghiệp. "
        "Nhiệm vụ của bạn là nhận diện vị trí các bóng thoại (speech bubbles), hộp thoại dẫn chuyện (caption boxes) "
        "và dịch toàn bộ các câu thoại sang ngôn ngữ đích chuẩn xác, tự nhiên, giàu biểu cảm và vừa vặn khung thoại."
    )

    prompt = f"""Hãy phân tích trang truyện tranh/manga/manhwa này:
1. Quét toàn bộ các đoạn thoại/bóng thoại, hộp dẫn chuyện hoặc văn bản thoại nhân vật.
2. Với mỗi bóng thoại/văn bản, xác định tọa độ khung bao (bounding box) theo chuẩn [ymin, xmin, ymax, xmax] trên thang đo chuẩn hóa từ 0 đến 1000 (0 là góc trên bên trái, 1000 là góc dưới bên phải).
3. Trích xuất câu gốc (original).
4. Dịch sang {target_lang_desc} (translated). Bản dịch phải ngắn gọn, súc tích, tự nhiên, văn phong truyện tranh chuẩn.

BẮT BUỘC trả về duy nhất một mảng JSON (JSON Array) hợp lệ theo cấu trúc sau, không kèm bất kỳ giải thích nào:
[
  {{
    "box_2d": [ymin, xmin, ymax, xmax],
    "original": "câu gốc trong bóng thoại",
    "translated": "bản dịch tiếng Việt tự nhiên"
  }}
]
Nếu trang truyện không có bóng thoại hoặc chỉ toàn hình vẽ, trả về: []
"""

    response_text = await pool.generate_multimodal(
        audio_bytes=image_bytes,
        mime_type=mime_type,
        prompt=prompt,
        system_instruction=system_instruction,
        model_name="gemini-3.5-flash",
        response_mime_type="application/json"
    )

    # Clean and parse JSON response
    clean_text = response_text.strip()
    # Strip markdown fences if present
    if clean_text.startswith("```"):
        clean_text = re.sub(r"^```[a-zA-Z0-9]*\s*", "", clean_text)
        clean_text = re.sub(r"\s*```$", "", clean_text)
        clean_text = clean_text.strip()

    # Find JSON array boundaries
    start_idx = clean_text.find("[")
    end_idx = clean_text.rfind("]")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        clean_text = clean_text[start_idx:end_idx + 1]

    try:
        bubbles = json.loads(clean_text)
        if not isinstance(bubbles, list):
            return []
    except Exception:
        # Fallback regex extraction if JSON parsing fails
        bubbles = []
        pattern = re.compile(r'\{\s*"box_2d"\s*:\s*\[(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\]\s*,\s*"original"\s*:\s*"(.*?)"\s*,\s*"translated"\s*:\s*"(.*?)"\s*\}', re.DOTALL)
        for m in pattern.finditer(response_text):
            ymin, xmin, ymax, xmax = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
            bubbles.append({
                "box_2d": [ymin, xmin, ymax, xmax],
                "original": m.group(5),
                "translated": m.group(6)
            })

    # Validate bubble structures
    valid_bubbles = []
    for b in bubbles:
        if isinstance(b, dict) and "box_2d" in b and "translated" in b:
            box = b.get("box_2d")
            if isinstance(box, list) and len(box) == 4:
                ymin, xmin, ymax, xmax = box
                if ymax > ymin and xmax > xmin:
                    valid_bubbles.append({
                        "box_2d": [max(0, min(1000, int(ymin))),
                                   max(0, min(1000, int(xmin))),
                                   max(0, min(1000, int(ymax))),
                                   max(0, min(1000, int(xmax)))],
                        "original": str(b.get("original", "")).strip(),
                        "translated": str(b.get("translated", "")).strip()
                    })

    return valid_bubbles

def sample_background_color(img: Image.Image, x1: int, y1: int, x2: int, y2: int) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
    """
    Sample bubble background color avoiding text/borders and choose appropriate text color.
    Returns (bg_color, text_color).
    """
    W, H = img.size
    samples = []
    steps_x, steps_y = 6, 6
    dx = (x2 - x1) / (steps_x + 1)
    dy = (y2 - y1) / (steps_y + 1)
    for i in range(1, steps_x + 1):
        for j in range(1, steps_y + 1):
            px = int(x1 + i * dx)
            py = int(y1 + j * dy)
            if 0 <= px < W and 0 <= py < H:
                try:
                    pixel = img.getpixel((px, py))
                    if isinstance(pixel, (tuple, list)) and len(pixel) >= 3:
                        samples.append(pixel[:3])
                except Exception:
                    pass

    if not samples:
        return ((255, 255, 255), (15, 15, 15))

    # Filter out dark text pixels (luminance < 100) to find real background color
    bg_candidates = [p for p in samples if (0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2]) >= 100]
    if bg_candidates:
        avg_r = sum(p[0] for p in bg_candidates) // len(bg_candidates)
        avg_g = sum(p[1] for p in bg_candidates) // len(bg_candidates)
        avg_b = sum(p[2] for p in bg_candidates) // len(bg_candidates)
    else:
        avg_r = sum(p[0] for p in samples) // len(samples)
        avg_g = sum(p[1] for p in samples) // len(samples)
        avg_b = sum(p[2] for p in samples) // len(samples)

    luminance = 0.299 * avg_r + 0.587 * avg_g + 0.114 * avg_b

    # If luminance is bright, use pure white background with dark text
    if luminance > 175:
        return ((255, 255, 255), (15, 15, 15))
    elif luminance > 120:
        return ((avg_r, avg_g, avg_b), (15, 15, 15))
    else:
        # Dark bubble / caption
        return ((avg_r, avg_g, avg_b), (245, 245, 245))

def wrap_text_to_lines(text: str, font: Any, max_width: int) -> List[str]:
    """Break text into lines that do not exceed max_width."""
    words = text.split()
    if not words:
        return []
    
    lines = []
    current_line = []
    
    for word in words:
        test_line = " ".join(current_line + [word])
        try:
            line_w = font.getlength(test_line)
        except AttributeError:
            line_w = font.getbbox(test_line)[2] - font.getbbox(test_line)[0]
            
        if line_w <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
                current_line = [word]
            else:
                # A single very long word
                lines.append(word)
                current_line = []
                
    if current_line:
        lines.append(" ".join(current_line))
        
    return lines

def render_translated_page(
    image_bytes: bytes,
    bubble_data: List[Dict[str, Any]],
    font_path: Optional[str] = None
) -> bytes:
    """
    Renders translated text over manga speech bubbles:
    - Inpaints/masks original bubble text with matching background.
    - Word-wraps text and dynamically calculates optimal font size.
    - Centers text in bubble.
    Returns JPEG bytes.
    """
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    draw = ImageDraw.Draw(img)
    W, H = img.size

    for bubble in bubble_data:
        box_2d = bubble.get("box_2d", [])
        if len(box_2d) != 4:
            continue
        ymin, xmin, ymax, xmax = box_2d
        x1 = int(xmin * W / 1000.0)
        y1 = int(ymin * H / 1000.0)
        x2 = int(xmax * W / 1000.0)
        y2 = int(ymax * H / 1000.0)

        bw = x2 - x1
        bh = y2 - y1
        if bw < 10 or bh < 10:
            continue

        translated = bubble.get("translated", "").strip()
        if not translated:
            continue

        # Inpaint mask bounds (expand slightly to cleanly cover old glyphs)
        exp_x = max(6, int(bw * 0.04))
        exp_y = max(4, int(bh * 0.08))
        bx1 = max(0, x1 - exp_x)
        by1 = max(0, y1 - exp_y)
        bx2 = min(W, x2 + exp_x)
        by2 = min(H, y2 + exp_y)
        inner_w = bx2 - bx1
        inner_h = by2 - by1

        # Background and text color
        bg_color, text_color = sample_background_color(img, bx1, by1, bx2, by2)

        # Mask/inpaint old text using rounded rectangle
        corner_radius = max(3, min(inner_w, inner_h) // 6)
        draw.rounded_rectangle([bx1, by1, bx2, by2], radius=corner_radius, fill=bg_color)

        # Dynamic Font Size and Word Wrap calculation
        avail_w = max(10, int(inner_w * 0.94))
        avail_h = max(10, int(inner_h * 0.92))

        # Determine optimal font size
        max_font_size = min(48, max(12, int(inner_h * 0.65)))
        min_font_size = 10

        best_font = None
        best_lines = [translated]
        best_line_h = 14

        for size in range(max_font_size, min_font_size - 1, -1):
            font = get_best_font(size, font_path)
            lines = wrap_text_to_lines(translated, font, avail_w)
            line_h = int(size * 1.25)
            total_text_h = len(lines) * line_h

            if total_text_h <= avail_h:
                best_font = font
                best_lines = lines
                best_line_h = line_h
                break

        if best_font is None:
            best_font = get_best_font(min_font_size, font_path)
            best_lines = wrap_text_to_lines(translated, best_font, avail_w)
            best_line_h = int(min_font_size * 1.25)

        total_text_h = len(best_lines) * best_line_h
        start_y = by1 + max(0, (inner_h - total_text_h) // 2)

        for i, line in enumerate(best_lines):
            try:
                line_w = best_font.getlength(line)
            except AttributeError:
                line_w = best_font.getbbox(line)[2] - best_font.getbbox(line)[0]
            line_x = bx1 + max(0, (inner_w - line_w) // 2)
            line_y = start_y + (i * best_line_h)
            draw.text((line_x, line_y), line, font=best_font, fill=text_color)

    out_buf = io.BytesIO()
    img.save(out_buf, format="JPEG", quality=95, optimize=True)
    return out_buf.getvalue()

async def fetch_images_from_url(url: str, output_dir: Union[str, Path]) -> List[Path]:
    """
    Downloads images from URL:
    - If direct image link (.jpg, .png, .webp, etc.), downloads directly.
    - If comic/chapter webpage link, parses page images and downloads in order.
    Returns list of downloaded Path objects.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Referer": url
    }

    clean_url = url.strip()

    # Check direct image by extension or content type
    is_direct_img = bool(re.search(r'\.(jpg|jpeg|png|webp|avif|bmp)(\?.*)?$', clean_url, re.IGNORECASE))

    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=30.0) as client:
        resp = await client.get(clean_url)
        content_type = resp.headers.get("Content-Type", "").lower()

        if is_direct_img or "image/" in content_type:
            ext = "jpg"
            if "png" in content_type or clean_url.lower().endswith(".png"):
                ext = "png"
            elif "webp" in content_type or clean_url.lower().endswith(".webp"):
                ext = "webp"
            
            dest_file = out_path / f"page_001.{ext}"
            with open(dest_file, "wb") as f:
                f.write(resp.content)
            return [dest_file]

        # Otherwise parse webpage HTML for comic chapter images
        html = resp.text
        # Look for image tags with src, data-src, data-original, data-lazy-src, data-cdn
        img_urls = []
        pattern = re.compile(r'<img[^>]+(?:data-src|data-original|data-lazy-src|data-cdn|src)=["\']([^"\']+)["\']', re.IGNORECASE)
        for match in pattern.finditer(html):
            raw_img_url = match.group(1).strip()
            # Normalize with urljoin for relative or scheme-relative URLs
            resolved_url = urljoin(clean_url, raw_img_url)
            low = resolved_url.lower()
            if any(bad in low for bad in ["logo", "avatar", "icon", "banner", "ads", "badge", ".gif", ".svg"]):
                continue
            if any(ext in low for ext in [".jpg", ".jpeg", ".png", ".webp", "chapter", "manga", "cdn", "image"]):
                if resolved_url not in img_urls:
                    img_urls.append(resolved_url)

        if not img_urls:
            # Try looser match
            looser = re.findall(r'https?://[^\s"\'<>]+\.(?:jpg|jpeg|png|webp)', html, re.IGNORECASE)
            for u in looser:
                if u not in img_urls and not any(bad in u.lower() for bad in ["logo", "avatar", "icon", "banner", "ads"]):
                    img_urls.append(u)

        if not img_urls:
            raise ValueError("Không tìm thấy hình ảnh trang truyện nào từ liên kết web đã cung cấp.")

        # Concurrently download images (limit concurrency to 5)
        sem = asyncio.Semaphore(5)
        downloaded_files: List[Tuple[int, Path]] = []

        async def download_one(idx: int, target_url: str):
            async with sem:
                try:
                    r = await client.get(target_url, headers={"Referer": clean_url}, timeout=20.0)
                    if r.status_code == 200 and len(r.content) > 5000: # filter out tiny tracking pixels
                        ext = "jpg"
                        if target_url.lower().endswith(".png"):
                            ext = "png"
                        elif target_url.lower().endswith(".webp"):
                            ext = "webp"
                        dest = out_path / f"page_{idx:03d}.{ext}"
                        with open(dest, "wb") as f:
                            f.write(r.content)
                        downloaded_files.append((idx, dest))
                except Exception:
                    pass

        tasks = [download_one(i + 1, u) for i, u in enumerate(img_urls[:50])] # safety cap 50 pages per chapter
        await asyncio.gather(*tasks)

        # Sort downloaded files by index
        downloaded_files.sort(key=lambda x: x[0])
        return [f[1] for f in downloaded_files]

async def extract_chapters_from_url(url: str) -> Dict[str, Any]:
    """
    Parses comic/manga URL to extract chapter list and detect the current chapter.
    Supports:
    - Series index pages with chapter tables/lists.
    - Direct chapter pages with chapter dropdowns or previous/next chapter links.
    - URL template pattern detection (e.g. .../chap-1, .../chapter-10).
    """
    clean_url = url.strip()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": clean_url
    }

    series_title = "Bộ truyện tranh"
    chapters: List[Dict[str, Any]] = []
    current_chapter_url = clean_url
    current_chapter_index = 0

    # Detect chapter number from URL if present
    # Matches /chapter-12, /chap-12, /ch-12, /chuong-12, /c12, /tap-12
    url_chap_match = re.search(r'(?:chap(?:ter)?|ch(?:ương)?|tập|vol|c)[-_/\s]*(\d+(?:\.\d+)?)', clean_url, re.IGNORECASE)
    detected_curr_num = float(url_chap_match.group(1)) if url_chap_match else None

    # Fetch webpage HTML
    html = ""
    try:
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=20.0) as client:
            resp = await client.get(clean_url)
            if resp.status_code == 200:
                html = resp.text
                final_url = str(resp.url)
                current_chapter_url = final_url
    except Exception:
        pass

    if html:
        # 1. Series / Page Title extraction
        t_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        if t_match:
            raw_title = t_match.group(1).strip()
            # Clean generic site suffixes like "| NetTruyen", "- BlogTruyen", etc.
            raw_title = re.sub(r'\s*[-|–—]\s*(?:Đọc truyện|NetTruyen|TruyenQQ|MangaDex|BlogTruyen|Tuổi Thơ|Truyện Online).*$', '', raw_title, flags=re.IGNORECASE).strip()
            if raw_title:
                series_title = raw_title

        # 2. Extract chapters from HTML <a> and <option> tags
        seen_urls = set()
        
        # Check <option value="...">Chapter ...</option> (standard chapter select dropdowns)
        opt_pattern = re.compile(r'<option\s+[^>]*value=["\']([^"\']+)["\'][^>]*>(.*?)</option>', re.IGNORECASE | re.DOTALL)
        for m in opt_pattern.finditer(html):
            val = m.group(1).strip()
            text = re.sub(r'<[^>]+>', ' ', m.group(2)).strip()
            combined = f"{text} {val}"
            cm = re.search(r'(?:chap(?:ter)?|ch(?:ương)?|tập|vol|c)[-_.\s]*(\d+(?:\.\d+)?)', combined, re.IGNORECASE)
            if cm and (val.startswith("http") or val.startswith("/")):
                full_u = urljoin(clean_url, val)
                if full_u not in seen_urls:
                    seen_urls.add(full_u)
                    num_val = float(cm.group(1))
                    name = text if len(text) < 60 and len(text) > 1 else f"Chương {cm.group(1)}"
                    chapters.append({
                        "id": f"chap_{cm.group(1)}",
                        "name": name,
                        "url": full_u,
                        "num": num_val
                    })

        # Check <a href="...">Chapter ...</a> links
        if len(chapters) < 2:
            a_pattern = re.compile(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)
            for m in a_pattern.finditer(html):
                href = m.group(1).strip()
                if not href or href.startswith("#") or href.startswith("javascript:"):
                    continue
                text = re.sub(r'<[^>]+>', ' ', m.group(2)).strip()
                combined = f"{text} {href}"
                cm = re.search(r'(?:chap(?:ter)?|ch(?:ương)?|tập|vol|c)[-_.\s/](\d+(?:\.\d+)?)', combined, re.IGNORECASE)
                if cm:
                    full_u = urljoin(clean_url, href)
                    if full_u not in seen_urls:
                        seen_urls.add(full_u)
                        num_val = float(cm.group(1))
                        name = text if len(text) < 60 and len(text) > 1 else f"Chương {cm.group(1)}"
                        chapters.append({
                            "id": f"chap_{cm.group(1)}",
                            "name": name,
                            "url": full_u,
                            "num": num_val
                        })

    # 3. If no chapters were found in HTML, but URL is a template (e.g. .../chap-1 or .../chapter-5)
    if not chapters and url_chap_match:
        curr_n = int(detected_curr_num or 1)
        # Create a template by replacing the chapter number
        prefix = clean_url[:url_chap_match.start(1)]
        suffix = clean_url[url_chap_match.end(1):]
        
        # Generate chapters from 1 up to curr_n + 10 (or at least 15 chapters)
        max_gen = max(curr_n + 5, 15)
        for i in range(1, max_gen + 1):
            c_url = f"{prefix}{i}{suffix}"
            chapters.append({
                "id": f"chap_{i}",
                "name": f"Chương {i}",
                "url": c_url,
                "num": float(i)
            })

    # Sort chapters by chapter number ascending
    if chapters:
        chapters.sort(key=lambda x: x.get("num", 0))

        # Find current chapter index
        for idx, c in enumerate(chapters):
            if c["url"] == current_chapter_url:
                current_chapter_index = idx
                break
            if detected_curr_num is not None and abs(c.get("num", -999) - detected_curr_num) < 0.01:
                current_chapter_index = idx
                break
    else:
        # Fallback: single chapter entry
        chapters = [{
            "id": "chap_1",
            "name": "Chương hiện tại",
            "url": clean_url,
            "num": 1.0
        }]
        current_chapter_index = 0

    return {
        "series_title": series_title,
        "chapters": chapters,
        "current_chapter_url": chapters[current_chapter_index]["url"] if chapters else clean_url,
        "current_chapter_index": current_chapter_index,
        "total_chapters": len(chapters)
    }

def extract_images_from_zip(zip_source: Union[bytes, Path, str], output_dir: Union[str, Path]) -> List[Path]:
    """
    Extracts image files from a ZIP or CBZ archive and sorts them in natural order.
    Returns list of extracted image Paths.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    if isinstance(zip_source, bytes):
        zip_file = zipfile.ZipFile(io.BytesIO(zip_source))
    else:
        zip_file = zipfile.ZipFile(str(zip_source))

    extracted: List[Path] = []
    with zip_file:
        file_list = [f for f in zip_file.namelist() if not f.startswith("__MACOSX/") and not f.endswith("/")]
        # Filter image files
        img_names = [f for f in file_list if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp'))]
        img_names.sort(key=natural_sort_key)

        for idx, filename in enumerate(img_names):
            ext = Path(filename).suffix.lower() or ".jpg"
            dest = out_path / f"page_{idx + 1:03d}{ext}"
            with zip_file.open(filename) as src, open(dest, "wb") as dst:
                dst.write(src.read())
            extracted.append(dest)

    return extracted

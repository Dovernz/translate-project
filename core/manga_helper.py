import io
import re
import os
import json
import asyncio
import zipfile
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
    Sample bubble background color and choose appropriate text color (black or white).
    Returns (bg_color, text_color).
    """
    W, H = img.size
    # Sample a few points inside the margin of the box (near corners)
    sample_points = [
        (min(W - 1, max(0, x1 + 4)), min(H - 1, max(0, y1 + 4))),
        (min(W - 1, max(0, x2 - 4)), min(H - 1, max(0, y1 + 4))),
        (min(W - 1, max(0, x1 + 4)), min(H - 1, max(0, y2 - 4))),
        (min(W - 1, max(0, x2 - 4)), min(H - 1, max(0, y2 - 4))),
        (min(W - 1, max(0, (x1 + x2) // 2)), min(H - 1, max(0, y1 + 4))),
    ]
    
    r_total, g_total, b_total, count = 0, 0, 0, 0
    for px, py in sample_points:
        try:
            pixel = img.getpixel((px, py))
            if isinstance(pixel, (tuple, list)) and len(pixel) >= 3:
                r_total += pixel[0]
                g_total += pixel[1]
                b_total += pixel[2]
                count += 1
        except Exception:
            continue

    if count == 0:
        return ((255, 255, 255), (15, 15, 15))

    avg_r = r_total // count
    avg_g = g_total // count
    avg_b = b_total // count
    luminance = 0.299 * avg_r + 0.587 * avg_g + 0.114 * avg_b

    # If luminance is bright, use pure white background with dark text
    if luminance > 140:
        return ((255, 255, 255), (20, 20, 20))
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
        if bw < 12 or bh < 12:
            continue

        translated = bubble.get("translated", "").strip()
        if not translated:
            continue

        # Inset slightly to preserve outer bubble ink lines
        pad_x = max(2, int(bw * 0.05))
        pad_y = max(2, int(bh * 0.05))
        bx1, by1 = x1 + pad_x, y1 + pad_y
        bx2, by2 = x2 - pad_x, y2 - pad_y
        inner_w = bx2 - bx1
        inner_h = by2 - by1

        # Background and text color
        bg_color, text_color = sample_background_color(img, bx1, by1, bx2, by2)

        # Mask/inpaint old text using rounded rectangle
        corner_radius = max(4, min(inner_w, inner_h) // 4)
        draw.rounded_rectangle([bx1, by1, bx2, by2], radius=corner_radius, fill=bg_color)

        # Dynamic Font Size and Word Wrap calculation
        avail_w = max(10, int(inner_w * 0.90))
        avail_h = max(10, int(inner_h * 0.90))

        # Determine optimal font size
        max_font_size = min(36, max(12, int(inner_h / 2.5)))
        min_font_size = 9

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
        pattern = re.compile(r'<img[^>]+(?:data-src|data-original|data-lazy-src|data-cdn|src)=["\'](https?://[^"\']+)["\']', re.IGNORECASE)
        for match in pattern.finditer(html):
            img_url = match.group(1).strip()
            # Filter out badges, avatars, icons, logos, ads
            low = img_url.lower()
            if any(bad in low for bad in ["logo", "avatar", "icon", "banner", "ads", "badge", ".gif", ".svg"]):
                continue
            if any(ext in low for ext in [".jpg", ".jpeg", ".png", ".webp", "chapter", "manga", "cdn", "image"]):
                if img_url not in img_urls:
                    img_urls.append(img_url)

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

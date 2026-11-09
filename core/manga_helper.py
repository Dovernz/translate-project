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

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

# Candidate font paths supporting Vietnamese diacritics
FONT_CANDIDATES_BOLD = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/tahomabd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]

FONT_CANDIDATES_REGULAR = [
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/tahoma.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

def parse_hex_color(hex_str: Optional[str], default: Tuple[int, int, int] = (0, 0, 0)) -> Tuple[int, int, int]:
    """Parse a HEX color string (#RGB, #RRGGBB, RGB, RRGGBB) to an RGB tuple."""
    if not hex_str or not isinstance(hex_str, str):
        return default
    s = hex_str.strip().lstrip('#')
    if len(s) == 3:
        s = ''.join([c * 2 for c in s])
    if len(s) == 6:
        try:
            return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
        except ValueError:
            return default
    return default

def get_best_font(size: int, font_weight: str = "normal", font_path: Optional[str] = None) -> ImageFont.FreeTypeFont:
    """Load the best available TTF font with weight support and fallback to default PIL font."""
    if font_path and os.path.exists(font_path):
        try:
            return ImageFont.truetype(font_path, size=size)
        except Exception:
            pass

    weight = str(font_weight or "normal").lower()
    if weight in ["heavy", "black", "bold", "semibold", "bolder"]:
        candidates = FONT_CANDIDATES_BOLD + FONT_CANDIDATES_REGULAR
    else:
        candidates = FONT_CANDIDATES_REGULAR + FONT_CANDIDATES_BOLD

    for candidate in candidates:
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
        "Bạn là Chuyên gia Đồ họa Thị giác và Dịch thuật Đa phương tiện cao cấp (Manga, Manhwa, Comics, Poster, Banner truyền thông). "
        "Nhiệm vụ của bạn là nhận diện chính xác từng khối văn bản/bóng thoại, dịch chuẩn xác tự nhiên theo ngữ cảnh, "
        "và bóc tách tỉ mỉ toàn bộ thông số phong cách đồ họa (màu chữ, màu nền, độ đậm, viền chữ) "
        "để hệ thống tái tạo lại kiểu dáng hoàn hảo như nguyên tác mỹ thuật."
    )

    prompt = f"""Hãy phân tích hình ảnh này (trang truyện tranh, áp phích, banner quảng cáo hoặc ấn phẩm đồ họa):
1. Quét toàn bộ các đoạn văn bản, tiêu đề, khẩu hiệu hoặc bóng thoại cần dịch.
2. Với mỗi khối văn bản, xác định tọa độ khung bao (bounding box) theo chuẩn [ymin, xmin, ymax, xmax] trên thang đo chuẩn hóa từ 0 đến 1000 (0 là góc trên bên trái, 1000 là góc dưới bên phải). Khung bao PHẢI ôm trọn toàn bộ chữ kể cả phần dấu, mũ nhô lên hoặc viền chữ.
3. Trích xuất câu gốc (original).
4. Dịch sang {target_lang_desc} (translated). Bản dịch phải ngắn gọn, súc tích, tự nhiên, văn phong phù hợp với loại hình ảnh (truyện tranh hoặc áp phích/banner).
5. Trích xuất CHÍNH XÁC các thuộc tính phong cách đồ họa (styling) của chữ gốc:
   - text_color: Mã màu HEX của chữ gốc (ví dụ: '#E30613' cho chữ đỏ, '#FFFFFF' cho chữ trắng, '#000000' cho chữ đen, '#F5A623' cho chữ vàng nghệ...).
   - bg_color: Mã màu HEX của nền ngay sát dưới/bao quanh chữ để phục vụ xoá chữ/inpainting trùng màu nền (ví dụ: '#D21E24' cho nền cờ đỏ/ruy băng đỏ Vietjet, '#FFF7EA' cho nền kem/ivory, '#FFFFFF' cho nền trắng...).
   - font_weight: 'heavy' (chữ tiêu đề rất đậm) | 'bold' (chữ đậm) | 'normal' (chữ thường) | 'light'.
   - stroke_color: Mã màu HEX của viền chữ hoặc viền bóng nếu chữ có viền nổi bật (ví dụ: '#FFD700' hoặc '#FFC72C' cho viền vàng, '#FFFFFF' cho viền trắng, '#000000' cho viền đen), hoặc null nếu không có viền.
   - stroke_width: Độ dày viền ước lượng (integer từ 1 đến 5), hoặc 0 nếu không có viền.
   - is_uppercase: boolean (true nếu bản gốc toàn bộ viết HOA).

BẮT BUỘC trả về duy nhất một mảng JSON (JSON Array) hợp lệ theo cấu trúc sau, không kèm bất kỳ giải thích nào:
[
  {{
    "box_2d": [ymin, xmin, ymax, xmax],
    "original": "WELCOME NEW MEMBERS",
    "translated": "CHÀO MỪNG THÀNH VIÊN MỚI",
    "text_color": "#E30613",
    "bg_color": "#FFF7EA",
    "font_weight": "heavy",
    "stroke_color": "#FFC72C",
    "stroke_width": 2,
    "is_uppercase": true
  }}
]
Nếu ảnh không có chữ hoặc chỉ toàn hình vẽ, trả về: []
"""

    response_text = await pool.generate_multimodal(
        audio_bytes=image_bytes,
        mime_type=mime_type,
        prompt=prompt,
        system_instruction=system_instruction,
        model_name="gemini-3.5-flash-lite",
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
        pattern = re.compile(r'\{\s*"box_2d"\s*:\s*\[(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\]\s*,\s*"original"\s*:\s*"(.*?)"\s*,\s*"translated"\s*:\s*"(.*?)"', re.DOTALL)
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
                    orig_str = str(b.get("original", "")).strip()
                    trans_str = str(b.get("translated", "")).strip()
                    is_upper = bool(b.get("is_uppercase", False)) or (bool(orig_str) and orig_str.isupper())

                    valid_bubbles.append({
                        "box_2d": [max(0, min(1000, int(ymin))),
                                   max(0, min(1000, int(xmin))),
                                   max(0, min(1000, int(ymax))),
                                   max(0, min(1000, int(xmax)))],
                        "original": orig_str,
                        "translated": trans_str,
                        "text_color": b.get("text_color"),
                        "bg_color": b.get("bg_color"),
                        "font_weight": str(b.get("font_weight", "bold" if is_upper else "normal")),
                        "stroke_color": b.get("stroke_color"),
                        "stroke_width": int(b.get("stroke_width", 0) or 0),
                        "is_uppercase": is_upper
                    })

    return valid_bubbles

def sample_background_smart(
    img: Image.Image,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    hint_hex: Optional[str] = None
) -> Tuple[int, int, int]:
    """Sample perimeter border pixels around the text box to get the authentic background color."""
    W, H = img.size
    border_pixels = []
    step_x = max(1, (x2 - x1) // 30)
    step_y = max(1, (y2 - y1) // 30)

    for px in range(max(0, x1), min(W, x2), step_x):
        for py in [max(0, y1 - 2), min(H - 1, y2 + 2)]:
            border_pixels.append(img.getpixel((px, py))[:3])
    for py in range(max(0, y1), min(H, y2), step_y):
        for px in [max(0, x1 - 2), min(W - 1, x2 + 2)]:
            border_pixels.append(img.getpixel((px, py))[:3])

    if border_pixels:
        med_r = sorted([p[0] for p in border_pixels])[len(border_pixels) // 2]
        med_g = sorted([p[1] for p in border_pixels])[len(border_pixels) // 2]
        med_b = sorted([p[2] for p in border_pixels])[len(border_pixels) // 2]
        return (med_r, med_g, med_b)

    if hint_hex:
        c = parse_hex_color(hint_hex, default=None)
        if c is not None:
            return c

    return (255, 255, 255)

def sample_background_color(img: Image.Image, x1: int, y1: int, x2: int, y2: int) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
    """Backward compatible wrapper returning (bg_color, text_color)."""
    bg_rgb = sample_background_smart(img, x1, y1, x2, y2)
    lum = 0.299 * bg_rgb[0] + 0.587 * bg_rgb[1] + 0.114 * bg_rgb[2]
    text_rgb = (255, 255, 255) if lum < 128 else (15, 15, 15)
    return (bg_rgb, text_rgb)

def wrap_text_to_lines(text: str, font: Any, max_width: int, stroke_width: int = 0) -> List[str]:
    """Break text into lines respecting existing newlines, max_width, and stroke thickness."""
    if not text:
        return []

    paragraphs = text.split("\n")
    final_lines = []

    for para in paragraphs:
        words = para.strip().split()
        if not words:
            continue
        current_line = []
        for word in words:
            test_line = " ".join(current_line + [word])
            try:
                bbox = font.getbbox(test_line, stroke_width=stroke_width)
                line_w = bbox[2] - bbox[0]
            except Exception:
                try:
                    line_w = font.getlength(test_line)
                except Exception:
                    line_w = len(test_line) * 10

            if line_w <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    final_lines.append(" ".join(current_line))
                    current_line = [word]
                else:
                    final_lines.append(word)
                    current_line = []

        if current_line:
            final_lines.append(" ".join(current_line))

    return final_lines

def render_translated_page(
    image_bytes: bytes,
    bubble_data: List[Dict[str, Any]],
    font_path: Optional[str] = None
) -> bytes:
    """
    Renders translated text over images, manga bubbles, and posters with full graphic style preservation:
    - Smart Inpainting: removes original text seamlessly via cv2 texture inpainting or perimeter-sampled mask.
    - Style Preservation: matches original text color, font weight, uppercase styling, and stroke/outline.
    - Returns high quality image bytes.
    """
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    W, H = img.size

    # Filter out empty bubbles or unchanged proper names/logos
    active_bubbles = []
    for b in bubble_data:
        box = b.get("box_2d", [])
        if len(box) != 4:
            continue
        orig = str(b.get("original", "")).strip()
        trans = str(b.get("translated", "")).strip()
        if not trans:
            continue
        # If original and translation are identical, keep crisp original logo/text untouched
        if orig and orig.lower() == trans.lower():
            continue
        active_bubbles.append(b)

    # Inpainting step
    if HAS_CV2 and active_bubbles:
        try:
            # Convert PIL RGB image to OpenCV BGR numpy array
            img_np = np.array(img)
            img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
            inpaint_mask = np.zeros((H, W), dtype=np.uint8)

            for bubble in active_bubbles:
                ymin, xmin, ymax, xmax = bubble["box_2d"]
                x1 = int(xmin * W / 1000.0)
                y1 = int(ymin * H / 1000.0)
                x2 = int(xmax * W / 1000.0)
                y2 = int(ymax * H / 1000.0)

                pad = 3
                x1 = max(0, x1 - pad)
                y1 = max(0, y1 - pad)
                x2 = min(W, x2 + pad)
                y2 = min(H, y2 + pad)
                roi = img_bgr[y1:y2, x1:x2]
                if roi.size == 0:
                    continue

                # Compute background color of region from perimeter
                top = roi[:2, :, :]
                bot = roi[-2:, :, :]
                bg_b = int((np.median(top[:, :, 0]) + np.median(bot[:, :, 0])) / 2)
                bg_g = int((np.median(top[:, :, 1]) + np.median(bot[:, :, 1])) / 2)
                bg_r = int((np.median(top[:, :, 2]) + np.median(bot[:, :, 2])) / 2)

                diff = np.abs(roi.astype(np.int32) - np.array([bg_b, bg_g, bg_r]))
                dist = np.sum(diff, axis=2)

                # Identify text and outline pixels
                is_text = (dist > 16).astype(np.uint8)
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
                roi_mask = cv2.dilate(is_text, kernel) * 255
                inpaint_mask[y1:y2, x1:x2] = np.maximum(inpaint_mask[y1:y2, x1:x2], roi_mask)

            # Inpaint using Fast Marching Method (Telea)
            inpainted_bgr = cv2.inpaint(img_bgr, inpaint_mask, inpaintRadius=4, flags=cv2.INPAINT_TELEA)
            img = Image.fromarray(cv2.cvtColor(inpainted_bgr, cv2.COLOR_BGR2RGB))
        except Exception:
            # Fallback to PIL inpaint if cv2 encounters any error
            pass

    draw = ImageDraw.Draw(img)

    for bubble in active_bubbles:
        box_2d = bubble.get("box_2d", [])
        ymin, xmin, ymax, xmax = box_2d
        x1 = int(xmin * W / 1000.0)
        y1 = int(ymin * H / 1000.0)
        x2 = int(xmax * W / 1000.0)
        y2 = int(ymax * H / 1000.0)

        bw = x2 - x1
        bh = y2 - y1
        if bw < 8 or bh < 8:
            continue

        orig = str(bubble.get("original", "")).strip()
        translated = str(bubble.get("translated", "")).strip()
        if not translated:
            continue

        # Case preservation
        is_upper = bool(bubble.get("is_uppercase", False)) or (bool(orig) and orig.isupper())
        if is_upper:
            translated = translated.upper()

        # Inpaint mask bounds
        exp_x = max(2, int(bw * 0.02))
        exp_y = max(2, int(bh * 0.03))
        bx1 = max(0, x1 - exp_x)
        by1 = max(0, y1 - exp_y)
        bx2 = min(W, x2 + exp_x)
        by2 = min(H, y2 + exp_y)
        inner_w = bx2 - bx1
        inner_h = by2 - by1

        # Background color
        bg_color = sample_background_smart(img, bx1, by1, bx2, by2, bubble.get("bg_color"))

        # If cv2 wasn't used or left artifacts, draw seamless rounded rectangle mask
        if not HAS_CV2:
            corner_radius = max(2, min(inner_w, inner_h) // 8)
            draw.rounded_rectangle([bx1, by1, bx2, by2], radius=corner_radius, fill=bg_color)

        # Text color
        lum = 0.299 * bg_color[0] + 0.587 * bg_color[1] + 0.114 * bg_color[2]
        fallback_text = (255, 255, 255) if lum < 128 else (15, 15, 15)
        text_color = parse_hex_color(bubble.get("text_color"), default=fallback_text) if bubble.get("text_color") else fallback_text

        # Stroke / outline styling
        stroke_color_hex = bubble.get("stroke_color")
        stroke_rgb = parse_hex_color(stroke_color_hex, default=None) if stroke_color_hex else None
        base_stroke_w = int(bubble.get("stroke_width", 0) or 0)
        has_stroke = bool(stroke_rgb)

        font_weight = str(bubble.get("font_weight", "bold" if is_upper else "normal"))

        # Dynamic Font Size and Word Wrap calculation
        avail_w = max(10, int(inner_w * 0.96))
        avail_h = max(10, int(inner_h * 0.94))

        max_font_size = min(120, max(12, int(inner_h * 0.82)))
        min_font_size = 10

        best_font = None
        best_lines = [translated]
        best_line_h = 14
        best_stroke_w = 0

        for size in range(max_font_size, min_font_size - 1, -1):
            cur_stroke_w = max(base_stroke_w, max(2, int(size * 0.075))) if has_stroke else 0
            font = get_best_font(size, font_weight=font_weight, font_path=font_path)
            lines = wrap_text_to_lines(translated, font, avail_w, stroke_width=cur_stroke_w)
            line_h = int(size * 1.25) + cur_stroke_w * 2
            total_text_h = len(lines) * line_h

            if total_text_h <= avail_h:
                best_font = font
                best_lines = lines
                best_line_h = line_h
                best_stroke_w = cur_stroke_w
                break

        if best_font is None:
            best_stroke_w = max(base_stroke_w, 2) if has_stroke else 0
            best_font = get_best_font(min_font_size, font_weight=font_weight, font_path=font_path)
            best_lines = wrap_text_to_lines(translated, best_font, avail_w, stroke_width=best_stroke_w)
            best_line_h = int(min_font_size * 1.25) + best_stroke_w * 2

        total_text_h = len(best_lines) * best_line_h
        start_y = by1 + max(0, (inner_h - total_text_h) // 2)

        for i, line in enumerate(best_lines):
            try:
                bbox = best_font.getbbox(line, stroke_width=best_stroke_w)
                line_w = bbox[2] - bbox[0]
            except Exception:
                try:
                    line_w = best_font.getlength(line)
                except Exception:
                    line_w = len(line) * 10

            line_x = bx1 + max(0, (inner_w - line_w) // 2)
            line_y = start_y + (i * best_line_h)

            text_kwargs = {
                "xy": (line_x, line_y),
                "text": line,
                "font": best_font,
                "fill": text_color
            }
            if stroke_rgb and best_stroke_w > 0:
                text_kwargs["stroke_width"] = best_stroke_w
                text_kwargs["stroke_fill"] = stroke_rgb

            draw.text(**text_kwargs)

    out_buf = io.BytesIO()
    is_png = image_bytes.startswith(b'\x89PNG')
    if is_png:
        img.save(out_buf, format="PNG")
    else:
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

async def analyze_manga_site_with_ai(url: str, pool: Any = None) -> Dict[str, Any]:
    """
    AI Web Chapter Analyzer:
    Analyzes manga/comic websites dynamically using Gemini API via Key Pool.
    Adaptable to any manga site (NetTruyen, MangaDex, MangaKakalot, Webtoon, AsuraScans...).
    Extracts:
    - Comic title
    - Chapters list (id, name, url)
    - URL pattern for consecutive chapters
    """
    clean_url = url.strip()
    if not clean_url:
        raise ValueError("URL web truyện không được để trống")

    if pool is None:
        from core.key_pool import KeyPool
        pool = KeyPool()

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": clean_url
    }

    html = ""
    final_url = clean_url
    try:
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=25.0) as client:
            resp = await client.get(clean_url)
            if resp.status_code == 200:
                html = resp.text
                final_url = str(resp.url)
    except Exception as e:
        pass

    # Extract page metadata & candidate links
    page_title = ""
    headings_list = []
    extracted_links = []
    seen_urls = set()

    if html:
        # Title
        t_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        if t_match:
            page_title = re.sub(r'<[^>]+>', '', t_match.group(1)).strip()

        # Headings H1, H2
        for h in re.finditer(r'<h[12][^>]*>(.*?)</h[12]>', html, re.IGNORECASE | re.DOTALL):
            txt = re.sub(r'<[^>]+>', ' ', h.group(1)).strip()
            if txt and len(txt) < 120 and txt not in headings_list:
                headings_list.append(txt)

        # 1. <option value="...">...</option> (Chapter select dropdowns)
        opt_pattern = re.compile(r'<option\s+[^>]*value=["\']([^"\']+)["\'][^>]*>(.*?)</option>', re.IGNORECASE | re.DOTALL)
        for m in opt_pattern.finditer(html):
            val = m.group(1).strip()
            txt = re.sub(r'<[^>]+>', ' ', m.group(2)).strip()
            if not val or val.startswith("#") or val.startswith("javascript:"):
                continue
            full_u = urljoin(final_url, val)
            if full_u not in seen_urls:
                seen_urls.add(full_u)
                extracted_links.append({"text": txt or val, "url": full_u})

        # 2. <a href="...">...</a> links
        a_pattern = re.compile(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)
        for m in a_pattern.finditer(html):
            href = m.group(1).strip()
            if not href or href.startswith("#") or href.startswith("javascript:") or href.startswith("mailto:") or href.startswith("tel:"):
                continue
            # Filter obvious non-chapter assets
            if any(href.lower().endswith(ext) for ext in [".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".woff", ".woff2"]):
                continue

            txt = re.sub(r'<[^>]+>', ' ', m.group(2)).strip()
            full_u = urljoin(final_url, href)
            if full_u not in seen_urls:
                seen_urls.add(full_u)
                extracted_links.append({"text": txt or full_u, "url": full_u})

    # Prioritize manga/chapter links if there are too many links
    filtered_links = []
    keywords = ["chap", "chapter", "ch-", "chuong", "chương", "vol", "tap", "tập", "episode", "read", "truyen", "comic"]
    for link in extracted_links:
        combined = f"{link['text']} {link['url']}".lower()
        if any(kw in combined for kw in keywords):
            filtered_links.append(link)

    # If keyword filtering found good candidate links, use them; otherwise use raw extracted links
    final_links = filtered_links if len(filtered_links) >= 2 else extracted_links
    # Cap links to top 250 to ensure compact context
    sample_links = final_links[:250]

    links_text = "\n".join([f"- {l['text']} -> {l['url']}" for l in sample_links]) if sample_links else f"- {clean_url}"
    headings_text = ", ".join(headings_list[:5]) if headings_list else "Không có"

    system_instruction = (
        "Bạn là Chuyên gia AI Web Scraper & Manga Site Architecture Analyzer hàng đầu thế giới. "
        "Nhiệm vụ của bạn là phân tích cấu trúc trang web truyện tranh bất kỳ (NetTruyen, MangaDex, MangaKakalot, Webtoon, AsuraScans...) "
        "để nhận diện chính xác tên truyện, toàn bộ danh sách chapter với link URL đầy đủ, và quy luật url_pattern."
    )

    prompt = f"""Phân tích cấu trúc trang web truyện này. Từ URL nguồn {clean_url} và các liên kết tìm thấy, hãy nhận diện:
1. Tên truyện tranh.
2. Danh sách toàn bộ các chapter (id, tên chapter, link URL đầy đủ).
3. Quy luật/Pattern tạo link của từng chapter trên trang web này để có thể tự sinh link cho các chương tiếp theo.
Trả về BẮT BUỘC dạng JSON thuần túy:
{{
  "comic_title": "...",
  "chapters": [
    {{"id": "1", "name": "Chapter 1", "url": "..."}}
  ],
  "url_pattern": "..."
}}

Thông tin bối cảnh trang web:
- URL nguồn: {clean_url}
- Tiêu đề trang (Page Title): {page_title or 'Chưa rõ'}
- Các thẻ tiêu đề (H1/H2): {headings_text}
- Danh sách các liên kết & dropdown trích xuất từ trang web:
{links_text}
"""

    response_text = await pool.generate_content(
        prompt=prompt,
        system_instruction=system_instruction,
        tier="bulk",
        response_mime_type="application/json",
        max_output_tokens=8192
    )

    clean_text = response_text.strip()
    if clean_text.startswith("```"):
        clean_text = re.sub(r"^```[a-zA-Z0-9]*\s*", "", clean_text)
        clean_text = re.sub(r"\s*```$", "", clean_text)
        clean_text = clean_text.strip()

    # Locate JSON object
    start_idx = clean_text.find("{")
    end_idx = clean_text.rfind("}")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        clean_text = clean_text[start_idx:end_idx + 1]

    parsed_json: Dict[str, Any] = {}
    try:
        parsed_json = json.loads(clean_text)
    except Exception:
        # Minimal fallback if JSON parsing failed
        parsed_json = {
            "comic_title": page_title or "Truyện tranh",
            "chapters": [{"id": "1", "name": "Chapter hiện tại", "url": clean_url}],
            "url_pattern": ""
        }

    comic_title = parsed_json.get("comic_title", "").strip() or page_title or "Bộ truyện tranh"
    # Clean generic website suffixes if present in title
    comic_title = re.sub(r'\s*[-|–—]\s*(?:Đọc truyện|NetTruyen|TruyenQQ|MangaDex|BlogTruyen|MangaKakalot|Webtoon).*$', '', comic_title, flags=re.IGNORECASE).strip()

    url_pattern = parsed_json.get("url_pattern", "") or ""
    raw_chapters = parsed_json.get("chapters", [])
    valid_chapters = []

    for idx, c in enumerate(raw_chapters):
        if not isinstance(c, dict):
            continue
        c_url = c.get("url", "").strip()
        if not c_url:
            continue
        # Ensure full url
        full_chap_url = urljoin(final_url, c_url)
        c_name = c.get("name", "").strip() or f"Chapter {idx + 1}"
        c_id = str(c.get("id", idx + 1))
        valid_chapters.append({
            "id": c_id,
            "name": c_name,
            "url": full_chap_url
        })

    # If no valid chapters found from AI, fallback to current page
    if not valid_chapters:
        valid_chapters.append({
            "id": "1",
            "name": "Chapter 1",
            "url": clean_url
        })

    # Detect current chapter index
    current_chapter_index = 0
    current_chapter_url = valid_chapters[0]["url"]
    for idx, c in enumerate(valid_chapters):
        if c["url"] == clean_url or c["url"] == final_url:
            current_chapter_index = idx
            current_chapter_url = c["url"]
            break

    return {
        "comic_title": comic_title,
        "series_title": comic_title,
        "chapters": valid_chapters,
        "url_pattern": url_pattern,
        "current_chapter_url": current_chapter_url,
        "current_chapter_index": current_chapter_index,
        "total_chapters": len(valid_chapters)
    }

async def extract_chapters_from_url(url: str, pool: Any = None) -> Dict[str, Any]:
    """Compatibility wrapper that calls analyze_manga_site_with_ai."""
    return await analyze_manga_site_with_ai(url, pool)

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

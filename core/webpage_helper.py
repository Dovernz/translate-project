"""
Web Page Translator Helper for GeminiTrans.
Fetches web pages, sanitizes HTML, extracts translatable text blocks,
translates them using Gemini KeyPool, and preserves full layout/CSS.
"""

import re
import os
import time
import json
import asyncio
import hashlib
from collections import OrderedDict
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, urljoin
import httpx
from bs4 import BeautifulSoup, Comment

LANG_NAMES = {
    "vi": "Tiếng Việt",
    "en": "Tiếng Anh (English)",
    "ja": "Tiếng Nhật (Japanese)",
    "ko": "Tiếng Hàn (Korean)",
    "zh": "Tiếng Trung (Chinese)",
    "fr": "Tiếng Pháp (French)",
    "de": "Tiếng Đức (German)",
    "es": "Tiếng Tây Ban Nha (Spanish)",
    "ru": "Tiếng Nga (Russian)"
}

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

# Tags whose inner text should be translated
TRANSLATABLE_TAGS = [
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "li", "blockquote", "figcaption",
    "dt", "dd", "summary", "th", "td", "caption",
    "article", "section"
]

CACHE_DIR = Path("outputs/web_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

class WebCacheManager:
    """
    Two-Tier Web Translator Cache:
    - Tier 1: In-Memory LRU Cache (fastest, 0ms)
    - Tier 2: Persistent Disk Cache (JSON files under outputs/web_cache)
    """
    def __init__(self, max_memory_entries: int = 100, disk_cache_dir: Path = CACHE_DIR):
        self.max_memory_entries = max_memory_entries
        self.disk_cache_dir = disk_cache_dir
        self.disk_cache_dir.mkdir(parents=True, exist_ok=True)
        self._memory_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()

    def _generate_key(self, url: str, target_lang: str) -> str:
        raw = f"{target_lang.strip().lower()}::{url.strip()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, url: str, target_lang: str) -> Optional[Dict[str, Any]]:
        key = self._generate_key(url, target_lang)
        # 1. Check LRU memory cache
        if key in self._memory_cache:
            self._memory_cache.move_to_end(key)
            data = dict(self._memory_cache[key])
            data["from_cache"] = True
            data["cache_source"] = "server_memory_lru"
            return data

        # 2. Check Disk Cache
        disk_file = self.disk_cache_dir / f"{key}.json"
        if disk_file.is_file():
            try:
                with open(disk_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Populate memory cache
                self._memory_cache[key] = data
                if len(self._memory_cache) > self.max_memory_entries:
                    self._memory_cache.popitem(last=False)
                res = dict(data)
                res["from_cache"] = True
                res["cache_source"] = "server_disk"
                return res
            except Exception as e:
                print(f"Error reading disk cache {disk_file}: {e}")

        return None

    def set(self, url: str, target_lang: str, data: Dict[str, Any]):
        key = self._generate_key(url, target_lang)
        cache_data = dict(data)
        cache_data["cached_at"] = time.time()
        # Save to LRU memory cache
        self._memory_cache[key] = cache_data
        self._memory_cache.move_to_end(key)
        if len(self._memory_cache) > self.max_memory_entries:
            self._memory_cache.popitem(last=False)

        # Save to disk cache
        disk_file = self.disk_cache_dir / f"{key}.json"
        try:
            with open(disk_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving to disk cache {disk_file}: {e}")

    def invalidate(self, url: str, target_lang: Optional[str] = None):
        if target_lang:
            key = self._generate_key(url, target_lang)
            self._memory_cache.pop(key, None)
            disk_file = self.disk_cache_dir / f"{key}.json"
            if disk_file.exists():
                try:
                    disk_file.unlink()
                except Exception:
                    pass
        else:
            keys_to_remove = [k for k, val in self._memory_cache.items() if val.get("url") == url]
            for k in keys_to_remove:
                self._memory_cache.pop(k, None)
            # Scan disk files
            try:
                for p in self.disk_cache_dir.glob("*.json"):
                    try:
                        with open(p, "r", encoding="utf-8") as f:
                            d = json.load(f)
                        if d.get("url") == url:
                            p.unlink()
                    except Exception:
                        pass
            except Exception:
                pass

web_cache = WebCacheManager()

def is_valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False

async def fetch_webpage_html(url: str, timeout: float = 20.0) -> str:
    """Fetch raw HTML from target URL safely."""
    fetch_url = url
    if "127.0.0.1:8090" in url:
        fetch_url = url.replace("127.0.0.1:8090", "127.0.0.1:8000")
    elif "localhost:8090" in url:
        fetch_url = url.replace("localhost:8090", "127.0.0.1:8000")

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
        "Cache-Control": "no-cache",
    }
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, verify=False) as client:
        resp = await client.get(fetch_url, headers=headers)
        resp.raise_for_status()
        return resp.text

def sanitize_and_prepare_soup(raw_html: str, base_url: str):
    """
    Sanitize HTML:
    - Inject <base href="..."> for relative assets/links (without target="_blank")
    - Intercept hyperlinks for seamless in-app split-view navigation
    - Remove dangerous scripts, noscripts, iframes, meta refreshes
    - Preserve styles, links, and all CSS
    """
    soup = BeautifulSoup(raw_html, "html.parser")

    # Remove dangerous/unneeded tags
    for tag in soup(["script", "noscript", "iframe", "object", "embed"]):
        tag.decompose()

    # Remove meta refresh
    for meta in soup.find_all("meta", attrs={"http-equiv": re.compile(r"refresh", re.I)}):
        meta.decompose()

    # Ensure <head> exists
    head = soup.find("head")
    if not head:
        head = soup.new_tag("head")
        if soup.html:
            soup.html.insert(0, head)
        else:
            soup.insert(0, head)

    # Base tag for relative URLs (NO target="_blank" so clicks stay in our workspace)
    existing_base = head.find("base")
    if existing_base:
        existing_base["href"] = base_url
        if "target" in existing_base.attrs:
            del existing_base["target"]
    else:
        new_base = soup.new_tag("base", href=base_url)
        head.insert(0, new_base)

    # Strip target="_blank" from any <a> tags
    for a in soup.find_all("a"):
        if a.get("target") == "_blank":
            del a["target"]

    # Injected helper style for smooth scrolling, clean reading and interactive links
    custom_style = soup.new_tag("style")
    custom_style.string = """
        html { scroll-behavior: smooth; }
        body { -webkit-font-smoothing: antialiased; }
        .gemini-trans-highlight { outline: 2px solid #6366f1 !important; }
        a { cursor: pointer !important; }
    """
    head.append(custom_style)

    # Injected script: capture hyperlink clicks and postMessage to parent for auto-translation
    interceptor_script = soup.new_tag("script")
    interceptor_script.string = """
        document.addEventListener('click', function(e) {
            var anchor = e.target.closest('a');
            if (!anchor) return;
            var href = anchor.getAttribute('href');
            if (!href || href.startsWith('#') || href.startsWith('javascript:')) return;
            try {
                var absUrl = anchor.href || new URL(href, document.baseURI || window.location.href).href;
                e.preventDefault();
                e.stopPropagation();
                if (window.parent && window.parent !== window) {
                    window.parent.postMessage({ type: 'GEMINI_TRANS_NAVIGATE', url: absUrl }, '*');
                }
            } catch (err) {}
        }, true);
    """
    head.append(interceptor_script)

    return soup

async def translate_text_batch(
    items: List[Dict[str, Any]],
    target_lang: str,
    pool: Any,
    tier: str = "bulk"
) -> Dict[int, str]:
    """
    Translates a batch of texts using Gemini KeyPool, returning a map {id: translated_text}.
    """
    if not items:
        return {}

    tgt_name = LANG_NAMES.get(target_lang, "Tiếng Việt")
    
    prompt_payload = [{"id": item["id"], "text": item["text"]} for item in items]
    
    system_instruction = (
        f"Bạn là chuyên gia dịch thuật web cao cấp. "
        f"Hãy dịch các đoạn văn bản sau sang {tgt_name}. "
        f"Yêu cầu:\n"
        f"1. Giữ nguyên ý nghĩa, văn phong tự nhiên, trôi chảy, chuẩn văn phong báo chí/tài liệu.\n"
        f"2. Bắt buộc giữ nguyên mã 'id' tương ứng của từng đoạn.\n"
        f"3. Trả về đúng định dạng JSON Array chứa các object có 2 trường 'id' và 'text': [ {{\"id\": 1, \"text\": \"...\"}} ].\n"
        f"4. Không giải thích, không bọc markdown ngoài JSON nếu không cần."
    )

    prompt_text = (
        f"Dịch mảng JSON sau sang {tgt_name}:\n"
        f"{json.dumps(prompt_payload, ensure_ascii=False)}"
    )

    result_map = {}
    try:
        raw_res = await pool.generate_content(prompt_text, system_instruction, tier=tier)
        # Parse JSON from response
        clean_res = raw_res.strip()
        if clean_res.startswith("```json"):
            clean_res = clean_res[7:]
        elif clean_res.startswith("```"):
            clean_res = clean_res[3:]
        if clean_res.endswith("```"):
            clean_res = clean_res[:-3]
        clean_res = clean_res.strip()

        parsed = json.loads(clean_res)
        if isinstance(parsed, list):
            for entry in parsed:
                if isinstance(entry, dict) and "id" in entry and "text" in entry:
                    result_map[int(entry["id"])] = str(entry["text"]).strip()
    except Exception as e:
        print(f"Webpage translate batch fallback error: {e}")
        # Fallback: keep original text
        for item in items:
            result_map[item["id"]] = item["text"]

    return result_map

async def process_and_translate_webpage(
    url: str,
    target_lang: str = "vi",
    pool: Any = None,
    tier: str = "bulk",
    max_elements: int = 150,
    bypass_cache: bool = False
) -> Dict[str, Any]:
    """
    Main function to fetch webpage, parse, translate translatable nodes,
    and return original_html and translated_html.
    Integrated with 2-tier caching: Memory LRU and Disk Cache.
    """
    if not is_valid_url(url):
        raise ValueError("URL không hợp lệ. Vui lòng nhập link bắt đầu bằng http:// hoặc https://")

    # 0. Check Server Cache first (Instant response, 0ms, 100% token savings)
    if not bypass_cache:
        cached_result = web_cache.get(url, target_lang)
        if cached_result:
            return cached_result

    # 1. Fetch raw HTML
    raw_html = await fetch_webpage_html(url)

    # 2. Sanitize and prepare original soup
    orig_soup = sanitize_and_prepare_soup(raw_html, url)
    page_title = orig_soup.title.string.strip() if orig_soup.title and orig_soup.title.string else url

    # 3. Identify and tag translatable elements
    tagged_items = []
    element_id_counter = 0

    # Search for meaningful elements
    candidates = orig_soup.find_all(TRANSLATABLE_TAGS)
    for el in candidates:
        if element_id_counter >= max_elements:
            break
        # Ignore if has children tags that are themselves in TRANSLATABLE_TAGS (to avoid duplicate translation)
        has_child_block = el.find(TRANSLATABLE_TAGS)
        if has_child_block:
            continue

        text = el.get_text(strip=True)
        # Filter out trivial strings (e.g. single symbols, pure digits)
        if len(text) >= 3 and not text.isdigit() and not re.match(r"^[\s\W_]+$", text):
            el["data-tr-id"] = str(element_id_counter)
            tagged_items.append({
                "id": element_id_counter,
                "text": text
            })
            element_id_counter += 1

    # Clone for translated version
    trans_soup = BeautifulSoup(str(orig_soup), "html.parser")

    # 4. Batch items and translate with Gemini KeyPool
    BATCH_SIZE = 20
    batches = [tagged_items[i:i + BATCH_SIZE] for i in range(0, len(tagged_items), BATCH_SIZE)]

    translated_map = {}
    if pool and tagged_items:
        # Run batches concurrently with asyncio.gather
        tasks = [
            translate_text_batch(batch, target_lang=target_lang, pool=pool, tier=tier)
            for batch in batches
        ]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in batch_results:
            if isinstance(res, dict):
                translated_map.update(res)

    # 5. Apply translations to translated_soup
    for tr_id, trans_text in translated_map.items():
        matched_el = trans_soup.find(attrs={"data-tr-id": str(tr_id)})
        if matched_el:
            matched_el.string = trans_text

    # Translate title as well if present
    translated_title = page_title
    if pool and page_title and page_title != url:
        try:
            tgt_name = LANG_NAMES.get(target_lang, "Tiếng Việt")
            t_prompt = f"Dịch tiêu đề bài viết sau sang {tgt_name}. Chỉ trả về tiêu đề đã dịch:\n{page_title}"
            t_res = await pool.generate_content(t_prompt, "Bạn là dịch giả. Chỉ trả về tiêu đề đã dịch.", tier="bulk")
            if t_res and t_res.strip():
                translated_title = t_res.strip()
                if trans_soup.title:
                    trans_soup.title.string = translated_title
        except Exception:
            pass

    final_result = {
        "status": "success",
        "url": url,
        "title": page_title,
        "translated_title": translated_title,
        "original_html": str(orig_soup),
        "translated_html": str(trans_soup),
        "total_nodes": len(tagged_items),
        "target_lang": target_lang,
        "from_cache": False,
        "cache_source": None
    }
    # Store in server cache for instant 0ms subsequent loads
    web_cache.set(url, target_lang, final_result)
    return final_result

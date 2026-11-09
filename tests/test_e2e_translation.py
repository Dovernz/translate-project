import asyncio
import json
import os
import sys
from pathlib import Path
from core.key_pool import KeyPool
from core.manga_helper import detect_and_translate_manga, render_translated_page

sys.stdout.reconfigure(encoding='utf-8')

async def main():
    pool = KeyPool()
    img_path = Path("uploads/manga/67671c9479e5/original/paste_1794216645867.png")
    with open(img_path, "rb") as f:
        img_bytes = f.read()

    print(f"Step 1: Detecting & Translating with Gemini Vision (Image size: {len(img_bytes)} bytes)...")
    bubbles = await detect_and_translate_manga(img_bytes, target_lang="vi", pool=pool)
    print(f"Detected {len(bubbles)} text blocks.")
    print("JSON Bubbles Preview:")
    print(json.dumps(bubbles[:4], ensure_ascii=False, indent=2))

    print("\nStep 2: Rendering translated page with full graphic styling preservation...")
    rendered_bytes = render_translated_page(img_bytes, bubbles)

    out_path = Path("tests/temp/proof_style_preserved.png")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(rendered_bytes)

    print(f"Step 3: Saved rendered output to {out_path} ({len(rendered_bytes)} bytes).")

if __name__ == "__main__":
    asyncio.run(main())

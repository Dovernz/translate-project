# -*- coding: utf-8 -*-
"""
Playwright Test Script: Paste Image and Translate in GeminiTrans
Tuân thủ Rule 16 (Code-Via-API), Rule 19 (0 lỗi JS)
"""

import os
import sys
import io
import time
import base64
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass
from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright, expect

PROOF_DIR = os.path.abspath("proofs")
os.makedirs(PROOF_DIR, exist_ok=True)

def create_sample_comic_image_base64() -> str:
    """Create a sample comic strip bubble image and return as data URL."""
    width, height = 500, 320
    img = Image.new("RGB", (width, height), color="#f8fafc")
    draw = ImageDraw.Draw(img)

    # Draw comic panel border
    draw.rectangle([(10, 10), (width - 10, height - 10)], outline="#0f172a", width=4)

    # Draw a speech bubble oval
    bubble_box = [(40, 50), (460, 230)]
    draw.ellipse(bubble_box, fill="#ffffff", outline="#0f172a", width=3)
    # Speech bubble tail
    draw.polygon([(210, 228), (250, 228), (170, 280)], fill="#ffffff", outline="#0f172a")
    # Mask inside edge of tail
    draw.line([(212, 228), (248, 228)], fill="#ffffff", width=4)

    # Text inside speech bubble
    draw.text((90, 110), "Wait! We can win this battle together!", fill="#000000")
    draw.text((120, 140), "Never give up hope!", fill="#1e293b")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"

def run_test():
    console_errors = []
    page_errors = []

    print("[1/6] Launching Playwright Chromium...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1400, "height": 950},
            permissions=["clipboard-read", "clipboard-write"]
        )
        page = context.new_page()

        # Listen to console errors and unhandled exceptions (Rule 19)
        def handle_console(msg):
            if msg.type == "error":
                # Filter out harmless 404 for optional favicon if any
                if "favicon.ico" not in msg.text:
                    console_errors.append(msg.text)
                    print(f"  [CONSOLE ERROR]: {msg.text}")

        def handle_pageerror(err):
            page_errors.append(str(err))
            print(f"  [PAGE ERROR]: {err}")

        page.on("console", handle_console)
        page.on("pageerror", handle_pageerror)

        print("[2/6] Navigating to http://127.0.0.1:8090/...")
        page.goto("http://127.0.0.1:8090/", wait_until="networkidle")
        page.screenshot(path=os.path.join(PROOF_DIR, "1_homepage_loaded.png"))

        print("[3/6] Switching to Tab Manga (Truyện tranh & Ảnh)...")
        manga_tab_btn = page.locator("#tab-btn-manga")
        expect(manga_tab_btn).to_be_visible()
        manga_tab_btn.click()
        page.wait_for_timeout(500)

        # Check Dropzone and Paste Button elements
        dropzone = page.locator("#manga-dropzone")
        expect(dropzone).to_be_visible()
        paste_btn = page.locator("#btn-manga-paste-clipboard")
        expect(paste_btn).to_be_visible()

        page.screenshot(path=os.path.join(PROOF_DIR, "2_manga_tab_dropzone.png"))

        print("[4/6] Simulating Paste (Ctrl+V) from Clipboard with sample comic speech bubble...")
        data_url = create_sample_comic_image_base64()

        # Dispatch real paste event with image File in DataTransfer
        page.evaluate("""(dataUrl) => {
            fetch(dataUrl)
                .then(r => r.blob())
                .then(blob => {
                    const file = new File([blob], "paste_sample_comic.png", { type: "image/png" });
                    const dt = new DataTransfer();
                    dt.items.add(file);
                    const pasteEvent = new ClipboardEvent("paste", {
                        bubbles: true,
                        cancelable: true,
                        clipboardData: dt
                    });
                    window.dispatchEvent(pasteEvent);
                });
        }""", data_url)

        # Check for Toast Notification
        page.wait_for_timeout(400)
        page.screenshot(path=os.path.join(PROOF_DIR, "3_paste_toast_notification.png"))

        # Wait for AI Inpainting & Translation response
        print("Waiting for /api/manga/paste-and-translate to complete...")
        page.wait_for_selector("#manga-img-1", timeout=30000)
        page.wait_for_timeout(1000)

        print("Translation completed! Capturing result...")
        page.screenshot(path=os.path.join(PROOF_DIR, "4_translated_result.png"))

        print("[5/6] Testing Comparison & Zoom Controls...")
        # 1. Switch to Bản Gốc (Original)
        btn_orig = page.locator("#manga-view-btn-orig")
        btn_orig.click()
        page.wait_for_timeout(500)
        page.screenshot(path=os.path.join(PROOF_DIR, "5_view_mode_original.png"))

        # 2. Switch to Song song (Side-by-Side Split View)
        btn_split = page.locator("#manga-view-btn-split")
        btn_split.click()
        page.wait_for_timeout(600)
        page.screenshot(path=os.path.join(PROOF_DIR, "6_view_mode_split_comparison.png"))

        # 3. Switch back to Bản Dịch (Translated)
        btn_trans = page.locator("#manga-view-btn-trans")
        btn_trans.click()
        page.wait_for_timeout(500)

        # 4. Test Zoom Controls
        zoom_in_btn = page.locator('button[title="Phóng to"]')
        zoom_in_btn.first.click()
        page.wait_for_timeout(300)
        zoom_in_btn.first.click()
        page.wait_for_timeout(300)
        page.screenshot(path=os.path.join(PROOF_DIR, "7_zoom_controls_active.png"))

        # 5. Test Lightbox Modal
        print("[6/6] Testing Lightbox Modal for detailed zoom & inspection...")
        page.evaluate("openMangaLightbox(1)")
        page.wait_for_timeout(500)
        lightbox_modal = page.locator("#manga-lightbox-modal")
        expect(lightbox_modal).to_be_visible()
        page.screenshot(path=os.path.join(PROOF_DIR, "8_lightbox_modal_open.png"))

        # Test toggle split inside lightbox
        lb_split_btn = page.locator("#lb-btn-split")
        lb_split_btn.click()
        page.wait_for_timeout(500)
        page.screenshot(path=os.path.join(PROOF_DIR, "9_lightbox_split_comparison.png"))

        # Close lightbox via ESC key
        page.keyboard.press("Escape")
        page.wait_for_timeout(400)
        expect(lightbox_modal).to_be_hidden()

        browser.close()

    print("\n--- TEST SUMMARY & RULE 19 AUDIT ---")
    print(f"Total Page Errors: {len(page_errors)}")
    print(f"Total Console Errors: {len(console_errors)}")
    if page_errors:
        print("Page Errors Detail:", page_errors)
    if console_errors:
        print("Console Errors Detail:", console_errors)

    assert len(page_errors) == 0, f"FAILED: Encountered {len(page_errors)} page errors!"
    assert len(console_errors) == 0, f"FAILED: Encountered {len(console_errors)} console errors!"
    print("SUCCESS: 0 JS ERRORS, ALL PASTE & TRANSLATE & COMPARISON TESTS PASSED!")

if __name__ == "__main__":
    run_test()

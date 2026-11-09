# -*- coding: utf-8 -*-
"""
Playwright Test Script: Verify Fluid Wide Screen Layout (1920x1080)
- Container expands across widescreen without cramped margins
- Web Page Translator side-by-side 2 columns have ample space
- Video, Text, Manga tabs expand gracefully
- Zero JS console/page errors
- Zero horizontal overflow (scrollWidth <= clientWidth)
"""

import os
import sys
import time

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

from playwright.sync_api import sync_playwright, expect

PROOF_DIR = os.path.abspath("proofs")
os.makedirs(PROOF_DIR, exist_ok=True)

def test_fullwidth_layout():
    console_errors = []
    page_errors = []

    print("[1/6] Launching Playwright Chromium at 1920x1080...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            permissions=["clipboard-read", "clipboard-write"]
        )
        page = context.new_page()

        def handle_console(msg):
            if msg.type == "error":
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
        page.wait_for_timeout(1000)

        # 1. VERIFY OVERFLOW & MAIN CONTAINER WIDTH
        print("[3/6] Verifying Container Width and No Horizontal Overflow...")
        has_h_scroll = page.evaluate("() => document.documentElement.scrollWidth > document.documentElement.clientWidth")
        assert not has_h_scroll, "Detected unwanted horizontal scrollbar on document!"

        main_box = page.locator("main").bounding_box()
        print(f"  Main container width on 1920x1080: {main_box['width']:.1f}px (left: {main_box['x']:.1f}px)")
        assert main_box['width'] >= 1800, f"Expected main width >= 1800px, got {main_box['width']}px"

        # Tab 1: Video proof
        proof_video = os.path.join(PROOF_DIR, "11_fullwidth_video_tab_1920.png")
        page.screenshot(path=proof_video)
        print(f"  --> Saved: {proof_video}")

        # 2. VERIFY TAB TRANSLATE (TEXT SUB-MODE)
        print("[4/6] Verifying Text & Document Translator Tab...")
        page.locator("#tab-btn-translate").click()
        page.wait_for_timeout(500)

        src_box = page.locator("#src-text").bounding_box()
        tgt_box = page.locator("#target-text").bounding_box()
        print(f"  Source textarea width: {src_box['width']:.1f}px, height: {src_box['height']:.1f}px")
        print(f"  Target textarea width: {tgt_box['width']:.1f}px, height: {tgt_box['height']:.1f}px")
        assert src_box['width'] >= 850, f"Expected source box >= 850px, got {src_box['width']}px"
        assert tgt_box['width'] >= 850, f"Expected target box >= 850px, got {tgt_box['width']}px"

        proof_text = os.path.join(PROOF_DIR, "12_fullwidth_text_translator_1920.png")
        page.screenshot(path=proof_text)
        print(f"  --> Saved: {proof_text}")

        # 3. VERIFY WEB PAGE TRANSLATOR SUB-MODE (SPLIT VIEW)
        print("[5/6] Verifying Web Page Translator Sub-Mode in 2-Column Split View...")
        page.locator("#submode-btn-web").click()
        page.wait_for_timeout(500)

        # Activate result workspace to test the 2-column split view layout
        page.evaluate("""() => {
            document.getElementById('web-empty-state').classList.add('hidden');
            const ws = document.getElementById('web-result-workspace');
            ws.classList.remove('hidden');
            document.getElementById('web-result-title').innerText = 'Trang Web Mẫu (Widescreen 1920 Split Test)';
            setWebViewMode('split');
        }""")
        page.wait_for_timeout(500)

        ws_box = page.locator("#web-result-workspace").bounding_box()
        orig_col = page.locator("#web-col-orig").bounding_box()
        trans_col = page.locator("#web-col-trans").bounding_box()
        orig_iframe = page.locator("#web-orig-iframe").bounding_box()
        trans_iframe = page.locator("#web-trans-iframe").bounding_box()

        print(f"  Web Workspace width: {ws_box['width']:.1f}px")
        print(f"  Original Column width: {orig_col['width']:.1f}px, iframe height: {orig_iframe['height']:.1f}px")
        print(f"  Translated Column width: {trans_col['width']:.1f}px, iframe height: {trans_iframe['height']:.1f}px")

        assert ws_box['width'] >= 1800, f"Expected web workspace >= 1800px, got {ws_box['width']}px"
        assert orig_col['width'] >= 850, f"Expected orig column >= 850px, got {orig_col['width']}px"
        assert trans_col['width'] >= 850, f"Expected trans column >= 850px, got {trans_col['width']}px"
        assert orig_iframe['height'] >= 600, f"Expected iframe height >= 600px, got {orig_iframe['height']}px"

        proof_web = os.path.join(PROOF_DIR, "13_fullwidth_web_translator_split_1920.png")
        page.screenshot(path=proof_web)
        print(f"  --> Saved: {proof_web}")

        # 4. VERIFY MANGA TAB & SPLIT MODE
        print("[6/6] Verifying Manga Tab & Split Mode Expansion...")
        page.locator("#tab-btn-manga").click()
        page.wait_for_timeout(500)

        # Switch manga to split mode and check max width
        page.evaluate("() => setMangaViewMode('split')")
        page.wait_for_timeout(300)
        manga_list_maxw = page.evaluate("() => document.getElementById('manga-pages-list').style.maxWidth")
        print(f"  Manga Pages List maxWidth in split mode: {manga_list_maxw}")
        assert manga_list_maxw == "1400px", f"Expected 1400px, got {manga_list_maxw}"

        proof_manga = os.path.join(PROOF_DIR, "14_fullwidth_manga_reader_1920.png")
        page.screenshot(path=proof_manga)
        print(f"  --> Saved: {proof_manga}")

        browser.close()

    print("\n-------------------------------------------")
    print(f"Total Console Errors: {len(console_errors)}")
    print(f"Total Page Errors:    {len(page_errors)}")
    print("-------------------------------------------")

    assert len(console_errors) == 0, f"Encountered {len(console_errors)} console errors: {console_errors}"
    assert len(page_errors) == 0, f"Encountered {len(page_errors)} page errors: {page_errors}"
    print("[SUCCESS] All full-width layout tests PASSED with 0 errors!")

if __name__ == "__main__":
    test_fullwidth_layout()

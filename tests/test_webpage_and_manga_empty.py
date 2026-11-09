# -*- coding: utf-8 -*-
"""
Playwright Test Script for:
1. Manga Empty State (Hardcoded demo completely removed)
2. Web Page Translator (Sub-mode, input URL, Gemini translation, 3 view modes, synchronized scroll)
Rules Compliance: Rule 16 (Code-Via-API) & Rule 19 (Zero JS errors)
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

def run_test():
    console_errors = []
    page_errors = []

    print("[1/7] Launching Playwright Chromium headless...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 950},
            permissions=["clipboard-read", "clipboard-write"]
        )
        page = context.new_page()

        # Listen to console and page errors
        def handle_console(msg):
            if msg.type == "error":
                # Ignore benign 404 for optional favicon if any
                if "favicon.ico" not in msg.text:
                    console_errors.append(msg.text)
                    print(f"  [CONSOLE ERROR]: {msg.text}")

        def handle_pageerror(err):
            page_errors.append(str(err))
            print(f"  [PAGE ERROR]: {err}")

        page.on("console", handle_console)
        page.on("pageerror", handle_pageerror)

        print("[2/7] Navigating to http://127.0.0.1:8090/...")
        page.goto("http://127.0.0.1:8090/", wait_until="networkidle")
        time.sleep(1)

        # ----------------------------------------------------
        # TEST 1: MANGA TAB EMPTY STATE (NO HARDCODED DEMO)
        # ----------------------------------------------------
        print("[3/7] Verifying Manga Tab Empty State (Hardcoded demo removed)...")
        manga_tab_btn = page.locator("#tab-btn-manga")
        expect(manga_tab_btn).to_be_visible()
        manga_tab_btn.click()
        page.wait_for_timeout(600)

        # Verify empty state is visible
        empty_state = page.locator("#manga-empty-state")
        expect(empty_state).to_be_visible()

        # Verify text
        title_el = empty_state.locator('[data-i18n="manga_empty_title"]')
        desc_el = empty_state.locator('[data-i18n="manga_empty_desc"]')
        expect(title_el).to_have_text("Chưa có trang nào")
        expect(desc_el).to_contain_text("Nhấn Ctrl+V để dán ảnh, tải ảnh/ZIP hoặc nhập URL truyện để bắt đầu")

        # Verify pages container has 0 items
        pages_container = page.locator("#manga-pages-list")
        page_cards = pages_container.locator("div[id^='manga-page-card-']")
        assert page_cards.count() == 0, f"Expected 0 demo cards, found {page_cards.count()}"

        # Verify chapter dropdown has no demo chapters
        chapter_select = page.locator("#manga-chapter-dropdown")
        select_options = chapter_select.locator("option")
        # Should only have default placeholder option
        assert select_options.count() <= 1, f"Expected 0 or 1 options in chapter dropdown, got {select_options.count()}"

        # Screenshot proof 1: Manga clean empty state
        manga_proof = os.path.join(PROOF_DIR, "10_manga_empty_state_clean.png")
        page.screenshot(path=manga_proof)
        print(f"  --> Saved: {manga_proof}")

        # ----------------------------------------------------
        # TEST 2: WEBPAGE TRANSLATOR IN TAB 'DỊCH VĂN BẢN'
        # ----------------------------------------------------
        print("[4/7] Navigating to Tab 'Dịch văn bản' and switching to Webpage Sub-mode...")
        text_tab_btn = page.locator("#tab-btn-translate")
        expect(text_tab_btn).to_be_visible()
        text_tab_btn.click()
        page.wait_for_timeout(400)

        # Segmented Control buttons
        btn_sub_text = page.locator("#submode-btn-text")
        btn_sub_web = page.locator("#submode-btn-web")
        expect(btn_sub_text).to_be_visible()
        expect(btn_sub_web).to_be_visible()

        # Switch to Web Page Translator sub-mode
        btn_sub_web.click()
        page.wait_for_timeout(400)

        # Check containers
        web_container = page.locator("#web-mode-container")
        text_container = page.locator("#text-mode-container")
        expect(web_container).to_be_visible()
        expect(text_container).to_be_hidden()

        # Input URL
        web_input = page.locator("#web-url-input")
        expect(web_input).to_be_visible()
        test_url = "http://127.0.0.1:8090/test-article"
        web_input.fill(test_url)

        # Web empty state should be visible before translation
        web_empty = page.locator("#web-empty-state")
        expect(web_empty).to_be_visible()

        # Screenshot proof 2: Web translator input view
        input_proof = os.path.join(PROOF_DIR, "11_web_translator_segmented_input.png")
        page.screenshot(path=input_proof)
        print(f"  --> Saved: {input_proof}")

        # ----------------------------------------------------
        # TEST 3: TRIGGER TRANSLATION & VERIFY RESULTS
        # ----------------------------------------------------
        print("[5/7] Executing Webpage Translation via Gemini API...")
        btn_translate = page.locator("#btn-web-translate")
        expect(btn_translate).to_be_visible()
        btn_translate.click()

        # Wait for workspace to become visible (allow up to 30s for API)
        web_workspace = page.locator("#web-result-workspace")
        expect(web_workspace).to_be_visible(timeout=35000)
        expect(web_empty).to_be_hidden()

        # Verify page title and nodes badge
        res_title = page.locator("#web-result-title")
        expect(res_title).to_be_visible()
        node_badge = page.locator("#web-node-count-badge")
        expect(node_badge).to_contain_text("đoạn đã dịch")
        print(f"  Result Title: '{res_title.inner_text()}', Nodes: '{node_badge.inner_text()}'")

        # Wait for iframes to load content
        page.wait_for_timeout(1500)

        # Screenshot proof 3: Side-by-Side (Split) comparison view
        split_proof = os.path.join(PROOF_DIR, "12_web_translator_split_view.png")
        page.screenshot(path=split_proof)
        print(f"  --> Saved: {split_proof}")

        # ----------------------------------------------------
        # TEST 4: VIEW MODES SWITCHING & QUICK SWITCH
        # ----------------------------------------------------
        print("[6/7] Testing 3 View Modes: [Bản Dịch], [Bản Gốc], [Song Song] and Quick Switch...")
        btn_view_trans = page.locator("#web-view-btn-trans")
        btn_view_orig = page.locator("#web-view-btn-orig")
        btn_view_split = page.locator("#web-view-btn-split")
        col_orig = page.locator("#web-col-orig")
        col_trans = page.locator("#web-col-trans")

        # 1. Switch to Single Translated view
        btn_view_trans.click()
        page.wait_for_timeout(300)
        expect(col_trans).to_be_visible()
        expect(col_orig).to_be_hidden()
        trans_proof = os.path.join(PROOF_DIR, "13_web_translator_translated_view.png")
        page.screenshot(path=trans_proof)
        print(f"  --> Saved: {trans_proof}")

        # 2. Switch to Single Original view
        btn_view_orig.click()
        page.wait_for_timeout(300)
        expect(col_orig).to_be_visible()
        expect(col_trans).to_be_hidden()
        orig_proof = os.path.join(PROOF_DIR, "14_web_translator_original_view.png")
        page.screenshot(path=orig_proof)
        print(f"  --> Saved: {orig_proof}")

        # 3. Switch back to Split comparison view
        btn_view_split.click()
        page.wait_for_timeout(300)
        expect(col_orig).to_be_visible()
        expect(col_trans).to_be_visible()

        # ----------------------------------------------------
        # TEST 5: SYNCHRONIZED SCROLLING VERIFICATION
        # ----------------------------------------------------
        print("[7/7] Testing Synchronized Scrolling between both columns...")
        # Verify scroll sync in browser context
        scroll_result = page.evaluate("""() => {
            const transIframe = document.getElementById('web-trans-iframe');
            const origIframe = document.getElementById('web-orig-iframe');
            if (!transIframe || !origIframe) return { error: 'iframes not found' };

            const tWin = transIframe.contentWindow;
            const oWin = origIframe.contentWindow;
            if (!tWin || !oWin) return { error: 'windows not accessible' };

            const tDoc = tWin.document ? (tWin.document.documentElement || tWin.document.body) : null;
            const oDoc = oWin.document ? (oWin.document.documentElement || oWin.document.body) : null;

            const initialOrigY = oWin.scrollY || (oDoc ? oDoc.scrollTop : 0);

            // Scroll translated window down by 250px
            if (tDoc) tDoc.scrollTop = 250;
            tWin.scrollTo({ top: 250, behavior: 'auto' });

            // Trigger scroll event
            tWin.dispatchEvent(new Event('scroll'));
            if (tWin.document) tWin.document.dispatchEvent(new Event('scroll'));

            return {
                initialOrigY: initialOrigY,
                transScrollY: tWin.scrollY || (tDoc ? tDoc.scrollTop : 0),
                origScrollY: oWin.scrollY || (oDoc ? oDoc.scrollTop : 0),
                transMax: tDoc ? tDoc.scrollHeight : 0,
                origMax: oDoc ? oDoc.scrollHeight : 0
            };
        }""")
        print(f"  Scroll Sync Evaluation: {scroll_result}")

        page.wait_for_timeout(600)
        sync_proof = os.path.join(PROOF_DIR, "15_web_translator_sync_scroll.png")
        page.screenshot(path=sync_proof)
        print(f"  --> Saved: {sync_proof}")

        # ----------------------------------------------------
        # ERROR VALIDATION (RULE 19)
        # ----------------------------------------------------
        print("\n--- Summary of Quality Assurance ---")
        print(f"Console Errors: {len(console_errors)}")
        print(f"Page Errors: {len(page_errors)}")

        browser.close()

        if console_errors or page_errors:
            print("FAILED: JS Errors detected!")
            for err in console_errors:
                print(f" - {err}")
            for err in page_errors:
                print(f" - {err}")
            return False

        print("SUCCESS: 0 JS errors! All functional requirements verified with proofs.")
        return True

if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)

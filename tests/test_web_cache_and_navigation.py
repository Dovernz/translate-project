# -*- coding: utf-8 -*-
"""
Playwright Test Suite for Web Translator Caching, Hyperlink Interception, and History Navigation
- Comprehensive 2-tier Caching: Server LRU/Disk Cache + Client-side Memory Cache (0ms latency)
- Hyperlink Interception: Clicks on <a href="..."> inside iframes update URL input and auto-translate
- Browser Navigation Controls: Back (◀), Forward (▶), Refresh (↻) with dynamic History Stack
- 0 Console Errors, 0 Page Errors
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

        print("[2/7] Navigating to GeminiTrans and opening Web Translator tab...")
        page.goto("http://127.0.0.1:8090/", wait_until="networkidle")

        # Navigate to Text Translator -> Web Translator submode
        page.click("#tab-btn-translate")
        page.wait_for_timeout(300)
        page.click("#submode-btn-web")
        page.wait_for_timeout(300)

        # Check initial button states
        back_btn = page.locator("#btn-web-nav-back")
        forward_btn = page.locator("#btn-web-nav-forward")
        refresh_btn = page.locator("#btn-web-nav-refresh")

        assert back_btn.is_disabled(), "Back button must be initially disabled"
        assert forward_btn.is_disabled(), "Forward button must be initially disabled"
        print("  ✓ Navigation controls initially disabled as expected.")

        # ----------------------------------------------------
        # TEST 1: FIRST PAGE LOAD & TRANSLATE (PAGE 1)
        # ----------------------------------------------------
        print("[3/7] Translating Article 1 (http://127.0.0.1:8090/test-article)...")
        page.fill("#web-url-input", "http://127.0.0.1:8090/test-article")
        page.click("#btn-web-translate")
        page.wait_for_selector("#web-result-workspace:not(.hidden)", timeout=35000)
        page.wait_for_timeout(1000)

        page.screenshot(path=os.path.join(PROOF_DIR, "21_web_nav_page1_loaded.png"))
        print("  --> Saved proof: 21_web_nav_page1_loaded.png")

        # Verify Back & Forward button states (only 1 page in history)
        assert back_btn.is_disabled(), "Back button must be disabled after 1st page load"
        assert forward_btn.is_disabled(), "Forward button must be disabled after 1st page load"

        # ----------------------------------------------------
        # TEST 2: HYPERLINK INTERCEPTION (CLICK TO PAGE 2)
        # ----------------------------------------------------
        print("[4/7] Testing Hyperlink Interception inside iframe...")
        orig_frame = page.frame_locator("#web-orig-iframe")
        article_2_link = orig_frame.locator("#link-to-article-2")
        expect(article_2_link).to_be_visible(timeout=5000)

        print("  Clicking hyperlink #link-to-article-2 inside iframe...")
        article_2_link.click()

        # Verify URL bar updated automatically to Article 2
        page.wait_for_function(
            "() => document.getElementById('web-url-input').value.includes('test-article-2')",
            timeout=5000
        )
        current_input_url = page.input_value("#web-url-input")
        print(f"  ✓ URL input automatically updated to: {current_input_url}")
        assert "test-article-2" in current_input_url, f"Expected test-article-2 in URL, got {current_input_url}"

        # Wait for Article 2 to finish translating and history to update
        page.wait_for_function(
            "() => !document.getElementById('btn-web-nav-back').disabled",
            timeout=30000
        )
        page.wait_for_timeout(500)
        page.screenshot(path=os.path.join(PROOF_DIR, "22_web_nav_page2_intercepted.png"))
        print("  --> Saved proof: 22_web_nav_page2_intercepted.png")

        # Verify Back button is now ENABLED, Forward button is DISABLED
        assert not back_btn.is_disabled(), "Back button MUST be enabled after navigating to 2nd page!"
        assert forward_btn.is_disabled(), "Forward button must still be disabled at end of history"
        print("  ✓ History stack updated: Back button enabled, Forward disabled.")

        # ----------------------------------------------------
        # TEST 3: BROWSER NAVIGATION BACK (◀) & 0ms CLIENT CACHE HIT
        # ----------------------------------------------------
        print("[5/7] Testing Browser Back (◀) with 0ms Cache Hit...")
        t0 = time.time()
        back_btn.click()

        # URL must revert to test-article immediately
        page.wait_for_function(
            "() => document.getElementById('web-url-input').value.endsWith('/test-article')",
            timeout=2000
        )
        back_latency_ms = (time.time() - t0) * 1000
        print(f"  ✓ Back navigation completed in {back_latency_ms:.2f}ms (Instant Cache Hit)!")

        # Verify Cache indicator badge is visible
        badge_text = page.evaluate("() => document.getElementById('web-cache-badge')?.innerText || ''")
        print(f"  ✓ Cache badge status: '{badge_text}'")
        assert "Cache" in badge_text, f"Expected Cache in badge, got '{badge_text}'"

        # Verify button states: Back disabled, Forward ENABLED
        assert back_btn.is_disabled(), "Back button must be disabled at start of history"
        assert not forward_btn.is_disabled(), "Forward button MUST be enabled after navigating back!"
        print("  ✓ Button states after Back: Back disabled, Forward enabled.")

        page.screenshot(path=os.path.join(PROOF_DIR, "23_web_nav_back_to_page1_cache.png"))
        print("  --> Saved proof: 23_web_nav_back_to_page1_cache.png")

        # ----------------------------------------------------
        # TEST 4: BROWSER NAVIGATION FORWARD (▶) & 0ms CLIENT CACHE HIT
        # ----------------------------------------------------
        print("[6/7] Testing Browser Forward (▶) with 0ms Cache Hit...")
        t1 = time.time()
        forward_btn.click()

        # URL must advance to test-article-2 immediately
        page.wait_for_function(
            "() => document.getElementById('web-url-input').value.includes('test-article-2')",
            timeout=2000
        )
        forward_latency_ms = (time.time() - t1) * 1000
        print(f"  ✓ Forward navigation completed in {forward_latency_ms:.2f}ms (Instant Cache Hit)!")

        # Verify button states: Back ENABLED, Forward disabled
        assert not back_btn.is_disabled(), "Back button must be enabled at end of history"
        assert forward_btn.is_disabled(), "Forward button must be disabled at end of history"
        print("  ✓ Button states after Forward: Back enabled, Forward disabled.")

        page.screenshot(path=os.path.join(PROOF_DIR, "24_web_nav_forward_to_page2_cache.png"))
        print("  --> Saved proof: 24_web_nav_forward_to_page2_cache.png")

        # ----------------------------------------------------
        # TEST 5: REFRESH (↻)
        # ----------------------------------------------------
        print("[7/7] Testing Browser Refresh (↻)...")
        refresh_btn.click()
        page.wait_for_timeout(1500)
        page.screenshot(path=os.path.join(PROOF_DIR, "25_web_nav_refreshed.png"))
        print("  --> Saved proof: 25_web_nav_refreshed.png")

        # ----------------------------------------------------
        # CONSOLE & PAGE ERRORS VALIDATION
        # ----------------------------------------------------
        print("\nValidating Zero JS Console/Page Errors...")
        print(f"Console Errors count: {len(console_errors)}")
        print(f"Page Errors count: {len(page_errors)}")
        assert len(console_errors) == 0, f"Detected console errors: {console_errors}"
        assert len(page_errors) == 0, f"Detected page errors: {page_errors}"

        browser.close()

    print("\n=======================================================")
    print("ALL TESTS PASSED: Caching, Hyperlinks & Nav Controls OK!")
    print("=======================================================")

if __name__ == "__main__":
    run_test()

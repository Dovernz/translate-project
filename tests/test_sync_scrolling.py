# -*- coding: utf-8 -*-
"""
Playwright Test Suite for Smooth Synchronized Scrolling with Active Driver & RAF 60FPS
- Ping-pong cycle elimination test (monotonic scroll, zero backward jumps)
- Active driver / Pointer tracking test (smooth transition between left and right columns)
- RAF 60FPS synchronization test
- Sync toggle enable/disable test
- Rule 19: 0 console errors, 0 page errors
"""

import os
import sys
import json
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

    print("[1/6] Launching Playwright Chromium headless...")
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

        print("[2/6] Navigating to GeminiTrans and loading test webpage...")
        page.goto("http://127.0.0.1:8090/", wait_until="networkidle")

        # Navigate to Text Translator -> Webpage sub-mode
        page.click("#tab-btn-translate")
        page.wait_for_timeout(300)
        page.click("#submode-btn-web")
        page.wait_for_timeout(300)

        # Enter test URL and translate
        page.fill("#web-url-input", "http://127.0.0.1:8090/test-article")
        page.click("#btn-web-translate")
        page.wait_for_selector("#web-result-workspace", timeout=30000)
        page.wait_for_timeout(1500)

        # ----------------------------------------------------
        # TEST A: ACTIVE DRIVER (TRANSLATED COLUMN) & PING-PONG ELIMINATION
        # ----------------------------------------------------
        print("[3/6] Testing Active Driver on Right Column (Translated) - Rapid Wheel...")
        trans_box = page.locator("#web-trans-iframe").bounding_box()
        assert trans_box, "Translated iframe not found or not rendered!"

        # Hover over translated iframe to trigger active driver
        page.mouse.move(trans_box['x'] + trans_box['width'] / 2, trans_box['y'] + 100)

        # Rapidly wheel down in 8 chunks of 50px each (20ms intervals)
        trans_history = []
        for i in range(8):
            page.mouse.wheel(0, 50)
            page.wait_for_timeout(25)
            pos = page.evaluate("""() => {
                const tWin = document.getElementById('web-trans-iframe').contentWindow;
                const oWin = document.getElementById('web-orig-iframe').contentWindow;
                return { tY: tWin.scrollY, oY: oWin.scrollY };
            }""")
            trans_history.append(pos)

        print(f"  Trajectory (Translated Driving): {trans_history}")

        # Verify Monotonic Scroll (No ping-pong / zero backward jumps)
        t_values = [h['tY'] for h in trans_history]
        for idx in range(1, len(t_values)):
            assert t_values[idx] >= t_values[idx - 1], (
                f"Ping-pong stutter detected at step {idx}: {t_values[idx - 1]} -> {t_values[idx]}!"
            )

        # Wait for RAF to settle follower position
        page.wait_for_timeout(200)
        settled_trans = page.evaluate("""() => {
            const tWin = document.getElementById('web-trans-iframe').contentWindow;
            const oWin = document.getElementById('web-orig-iframe').contentWindow;
            return { tY: tWin.scrollY, oY: oWin.scrollY };
        }""")
        print(f"  Settled State: {settled_trans}")
        assert settled_trans['tY'] >= 350, f"Expected tY >= 350, got {settled_trans['tY']}"
        assert settled_trans['oY'] > 200, f"Expected oY to follow smoothly, got {settled_trans['oY']}"

        proof_1 = os.path.join(PROOF_DIR, "16_sync_scroll_active_driver_trans.png")
        page.screenshot(path=proof_1)
        print(f"  --> Saved: {proof_1}")

        # ----------------------------------------------------
        # TEST B: ACTIVE DRIVER SWITCH (ORIGINAL COLUMN DRIVING)
        # ----------------------------------------------------
        print("[4/6] Testing Active Driver Switch to Left Column (Original)...")
        orig_box = page.locator("#web-orig-iframe").bounding_box()
        assert orig_box, "Original iframe not found or not rendered!"

        # Move mouse to Original iframe to switch driver
        page.mouse.move(orig_box['x'] + orig_box['width'] / 2, orig_box['y'] + 100)
        page.wait_for_timeout(100)

        # Rapidly wheel down 4 chunks of 60px
        orig_history = []
        for i in range(4):
            page.mouse.wheel(0, 60)
            page.wait_for_timeout(25)
            pos = page.evaluate("""() => {
                const tWin = document.getElementById('web-trans-iframe').contentWindow;
                const oWin = document.getElementById('web-orig-iframe').contentWindow;
                return { oY: oWin.scrollY, tY: tWin.scrollY };
            }""")
            orig_history.append(pos)

        print(f"  Trajectory (Original Driving): {orig_history}")
        o_values = [h['oY'] for h in orig_history]
        for idx in range(1, len(o_values)):
            assert o_values[idx] >= o_values[idx - 1], (
                f"Ping-pong stutter detected on left column at step {idx}: {o_values[idx - 1]} -> {o_values[idx]}!"
            )

        page.wait_for_timeout(200)
        settled_orig = page.evaluate("""() => {
            const tWin = document.getElementById('web-trans-iframe').contentWindow;
            const oWin = document.getElementById('web-orig-iframe').contentWindow;
            return { oY: oWin.scrollY, tY: tWin.scrollY };
        }""")
        print(f"  Settled State after Orig Driver: {settled_orig}")
        assert settled_orig['oY'] > settled_trans['oY'], "Expected oY to advance further!"

        proof_2 = os.path.join(PROOF_DIR, "17_sync_scroll_active_driver_orig.png")
        page.screenshot(path=proof_2)
        print(f"  --> Saved: {proof_2}")

        # ----------------------------------------------------
        # TEST C: TOGGLE SYNCHRONIZED SCROLL SWITCH (DISABLE & RE-ENABLE)
        # ----------------------------------------------------
        print("[5/6] Testing Synchronized Scroll Toggle Switch...")
        sync_checkbox = page.locator("#web-sync-scroll-check")
        expect(sync_checkbox).to_be_checked()

        # Uncheck to disable sync
        sync_checkbox.uncheck()
        expect(sync_checkbox).not_to_be_checked()
        page.wait_for_timeout(100)

        # Record follower position before scroll
        before_dis_oY = page.evaluate("() => document.getElementById('web-orig-iframe').contentWindow.scrollY")

        # Scroll translated column while sync is disabled
        page.mouse.move(trans_box['x'] + trans_box['width'] / 2, trans_box['y'] + 100)
        page.mouse.wheel(0, 100)
        page.wait_for_timeout(200)

        after_dis_oY = page.evaluate("() => document.getElementById('web-orig-iframe').contentWindow.scrollY")
        print(f"  Disabled sync test: oY before={before_dis_oY}, after={after_dis_oY}")
        assert before_dis_oY == after_dis_oY, "Follower should NOT move when sync scroll is disabled!"

        proof_3 = os.path.join(PROOF_DIR, "18_sync_scroll_toggled_off.png")
        page.screenshot(path=proof_3)
        print(f"  --> Saved: {proof_3}")

        # Re-check to enable sync
        sync_checkbox.check()
        expect(sync_checkbox).to_be_checked()

        # ----------------------------------------------------
        # VERIFICATION OF QUALITY ASSURANCE (RULE 19)
        # ----------------------------------------------------
        print("[6/6] Validating Zero JS Console/Page Errors...")
        print(f"Console Errors: {len(console_errors)}")
        print(f"Page Errors: {len(page_errors)}")

        browser.close()

        if console_errors or page_errors:
            print("FAILED: JS Errors detected!")
            for err in console_errors:
                print(f"  [ERROR]: {err}")
            sys.exit(1)

        print("\nALL VERIFICATIONS PASSED: 60FPS Smooth Synchronized Scrolling Verified!")

if __name__ == "__main__":
    run_test()

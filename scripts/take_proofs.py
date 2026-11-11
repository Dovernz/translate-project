import os
import shutil
import time
from playwright.sync_api import sync_playwright

docs_dir = r"D:\Thành\Translate\Docs"
proofs_dir = os.path.join(docs_dir, "proofs")
os.makedirs(proofs_dir, exist_ok=True)

artifact_dir_master = r"C:\Users\thanhcaotien\.gemini\antigravity\brain\926e0bdd-97b9-4b4e-8194-3460ee234e90"
artifact_dir_self = r"C:\Users\thanhcaotien\.gemini\antigravity\brain\983d4b28-ff07-4792-ae46-ce1667964adc"
os.makedirs(artifact_dir_master, exist_ok=True)
os.makedirs(artifact_dir_self, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 950})
    
    print("Navigating to http://127.0.0.1:8090...")
    page.goto("http://127.0.0.1:8090", wait_until="networkidle")
    time.sleep(1)

    # 1. Light Mode - Blue Theme
    print("Capturing 1: Light Mode Blue...")
    page.evaluate("applyTheme('light', 'blue', true)")
    time.sleep(0.6)
    p1 = os.path.join(docs_dir, "proof_light_blue.png")
    page.screenshot(path=p1)
    shutil.copy2(p1, os.path.join(proofs_dir, "proof_light_blue.png"))

    # 2. Light Mode - Orange Theme
    print("Capturing 2: Light Mode Orange...")
    page.evaluate("applyTheme('light', 'orange', true)")
    time.sleep(0.6)
    p2 = os.path.join(docs_dir, "proof_light_orange.png")
    page.screenshot(path=p2)
    shutil.copy2(p2, os.path.join(proofs_dir, "proof_light_orange.png"))

    # 3. Dark Mode - Blue Theme
    print("Capturing 3: Dark Mode Blue...")
    page.evaluate("applyTheme('dark', 'blue', true)")
    time.sleep(0.6)
    p3 = os.path.join(docs_dir, "proof_dark_blue.png")
    page.screenshot(path=p3)
    shutil.copy2(p3, os.path.join(proofs_dir, "proof_dark_blue.png"))

    # 4. Drawer Menu in Light Mode
    print("Capturing 4: Drawer Menu in Light Mode...")
    page.evaluate("applyTheme('light', 'blue', true)")
    time.sleep(0.4)
    page.evaluate("toggleDrawer()")
    time.sleep(0.6)
    p4 = os.path.join(docs_dir, "proof_drawer_menu.png")
    page.screenshot(path=p4)
    shutil.copy2(p4, os.path.join(proofs_dir, "proof_drawer_menu.png"))

    browser.close()

# Copy to artifacts
for p in [p1, p2, p3, p4]:
    fname = os.path.basename(p)
    shutil.copy2(p, os.path.join(artifact_dir_master, fname))
    shutil.copy2(p, os.path.join(artifact_dir_self, fname))

print("ALL PROOFS CAPTURED SUCCESSFULLY!")

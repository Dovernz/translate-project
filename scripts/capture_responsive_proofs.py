import os
import sys
import time
import shutil
import subprocess
import urllib.request

code_dir = r"D:\Thành\Translate\CODE"
docs_dir = r"D:\Thành\Translate\Docs"
artifact_dir = r"C:\Users\thanhcaotien\.gemini\antigravity\brain\926e0bdd-97b9-4b4e-8194-3460ee234e90"

os.makedirs(docs_dir, exist_ok=True)
os.makedirs(artifact_dir, exist_ok=True)

python_exe = os.path.join(code_dir, ".venv", "Scripts", "python.exe")

# Start server in subprocess
print("Starting uvicorn server on port 8090...")
proc = subprocess.Popen(
    [python_exe, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", "8090"],
    cwd=code_dir,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

# Wait for server to be responsive
url = "http://127.0.0.1:8090"
server_ready = False
for i in range(25):
    try:
        resp = urllib.request.urlopen(url, timeout=1)
        if resp.status == 200:
            server_ready = True
            print("Server is ready at", url)
            break
    except Exception:
        time.sleep(0.5)

if not server_ready:
    print("Failed to connect to server!")
    proc.kill()
    sys.exit(1)

try:
    from playwright.sync_api import sync_playwright
    print("Launching Playwright...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # 1. Mobile (390 x 844) - iPhone 14 style
        print("Capturing proof_responsive_mobile.png (390x844)...")
        page_mobile = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True)
        page_mobile.goto(url, wait_until="networkidle")
        time.sleep(1)
        mobile_path = os.path.join(docs_dir, "proof_responsive_mobile.png")
        page_mobile.screenshot(path=mobile_path)
        page_mobile.close()

        # 2. Tablet (768 x 1024) - iPad style
        print("Capturing proof_responsive_tablet.png (768x1024)...")
        page_tablet = browser.new_page(viewport={"width": 768, "height": 1024})
        page_tablet.goto(url, wait_until="networkidle")
        time.sleep(1)
        tablet_path = os.path.join(docs_dir, "proof_responsive_tablet.png")
        page_tablet.screenshot(path=tablet_path)
        page_tablet.close()

        # 3. PC (1280 x 800) - Standard Desktop Laptop
        print("Capturing proof_responsive_pc.png (1280x800)...")
        page_pc = browser.new_page(viewport={"width": 1280, "height": 800})
        page_pc.goto(url, wait_until="networkidle")
        time.sleep(1)
        pc_path = os.path.join(docs_dir, "proof_responsive_pc.png")
        page_pc.screenshot(path=pc_path)
        page_pc.close()

        browser.close()

    print("Screenshots captured successfully!")

    # Copy to artifact dir
    for f in ["proof_responsive_mobile.png", "proof_responsive_tablet.png", "proof_responsive_pc.png"]:
        src = os.path.join(docs_dir, f)
        dst = os.path.join(artifact_dir, f)
        shutil.copy2(src, dst)
        print(f"Copied {f} to {dst}")

finally:
    print("Shutting down server...")
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()
    print("Server stopped.")

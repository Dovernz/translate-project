import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from bs4 import BeautifulSoup

from app import app
from core.webpage_helper import sanitize_and_prepare_soup

client = TestClient(app)

MODULES = [
    "core.js",
    "tab_text.js",
    "tab_document.js",
    "tab_audio.js",
    "tab_video.js",
    "tab_web.js",
    "tab_manga.js",
]

def test_modules_exist_and_mounted():
    base_dir = Path(__file__).resolve().parent.parent
    modules_dir = base_dir / "static" / "js" / "modules"
    assert modules_dir.exists(), "Directory static/js/modules must exist"

    for mod in MODULES:
        file_path = modules_dir / mod
        assert file_path.exists(), f"Module {mod} must exist on disk"
        assert file_path.stat().st_size > 500, f"Module {mod} must have content"

        # Test HTTP route
        resp = client.get(f"/static/js/modules/{mod}")
        assert resp.status_code == 200, f"Route /static/js/modules/{mod} returned {resp.status_code}"
        assert "Error Boundary" in resp.text, f"Module {mod} must have error boundary header"

def test_index_html_loads_modules():
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    for mod in MODULES:
        script_tag = f'/static/js/modules/{mod}'
        assert script_tag in html, f"index.html must include script tag for {mod}"

def test_webpage_helper_sanitizes_highline_overlay():
    mock_html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test Article</title></head>
    <body>
        <div id="highline-mount" style="position:fixed;background:#fff;z-index:9999;"></div>
        <div class="preloader"></div>
        <article>
            <h1>Test Title</h1>
            <p>Test content to translate</p>
        </article>
    </body>
    </html>
    """
    soup = sanitize_and_prepare_soup(mock_html, "https://example.com/test")
    # Verify #highline-mount and preloader are decomposed
    assert soup.find(id="highline-mount") is None, "#highline-mount must be removed by sanitizer"
    assert soup.find(class_="preloader") is None, ".preloader must be removed by sanitizer"
    # Verify article is intact
    assert soup.find("article") is not None, "Article content must remain intact"
    # Verify defense style is injected
    styles = "".join([str(s) for s in soup.find_all("style")])
    assert "#highline-mount" in styles, "Anti-overlay CSS shield must be injected into head"

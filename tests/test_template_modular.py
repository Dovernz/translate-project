from fastapi.testclient import TestClient
from app import app
from pathlib import Path

client = TestClient(app)

def test_template_modular_partials_exist():
    base = Path(__file__).resolve().parent.parent / "templates"
    required = [
        "components/navbar.html",
        "components/modals.html",
        "tabs/tab_text.html",
        "tabs/tab_video.html",
        "tabs/tab_document.html",
        "tabs/tab_web.html",
        "tabs/tab_audio.html",
        "tabs/tab_manga.html"
    ]
    for r in required:
        p = base / r
        assert p.exists(), f"Partial {r} must exist"
        assert p.stat().st_size > 0, f"Partial {r} must not be empty"

def test_index_renders_all_tabs_and_components():
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text
    # Verify elements from partials are present in rendered page
    assert 'id="tab-video"' in html
    assert 'id="tab-document"' in html
    assert 'id="tab-web"' in html
    assert 'id="tab-transcribe"' in html
    assert 'id="tab-manga"' in html
    assert 'id="mobile-drawer"' in html
    assert 'id="export-choice-modal"' in html
    assert 'id="qr-mobile-modal"' in html
    assert 'id="manga-lightbox-modal"' in html

import json
import urllib.request

BASE = "http://localhost:8090"

# 1. HTML check
with urllib.request.urlopen(f"{BASE}/") as resp:
    html = resp.read().decode("utf-8")
assert "doc-source-editor" in html
assert "doc-target-editor" in html
assert "export-edited" in html
print("[PASS] HTML verified")

# 2. Export check for docx, pdf, txt, srt, md
formats = ["docx", "pdf", "txt", "srt", "md"]
for fmt in formats:
    payload = json.dumps({"content": f"# Heading\nTest content for {fmt}\nLine 2", "format": fmt, "filename": f"sample.{fmt}"}).encode("utf-8")
    req = urllib.request.Request(f"{BASE}/api/document/export-edited", data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        data = resp.read()
        assert resp.status == 200, f"Failed on {fmt}"
        assert len(data) > 0, f"Empty response on {fmt}"
        print(f"[PASS] Export {fmt} returned {len(data)} bytes")

print("ALL TESTS PASSED!")

import os
import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from core.video_helper import (
    get_video_info,
    extract_youtube_id,
    download_video_from_url,
    extract_subtitles_from_url
)

def test_extract_youtube_id():
    url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
    yt_id = extract_youtube_id(url)
    assert yt_id == "jNQXAC9IVRw", f"Expected jNQXAC9IVRw, got {yt_id}"
    print("[PASS] test_extract_youtube_id")

def test_get_video_info():
    url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
    info = get_video_info(url)
    assert info.get("youtube_id") == "jNQXAC9IVRw"
    assert "Me at the zoo" in info.get("title", "")
    assert info.get("duration", 0) > 0
    print(f"[PASS] test_get_video_info: {info.get('title')} ({info.get('duration')}s)")

def test_download_and_extract_sub():
    test_dir = ROOT_DIR / "uploads" / "test_tmp"
    test_dir.mkdir(parents=True, exist_ok=True)
    try:
        url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
        res = download_video_from_url(url, test_dir)
        assert res.get("success") is True, f"Download failed: {res}"
        print(f"[PASS] test_download_video_from_url: {res.get('filename')}")
        
        subs = extract_subtitles_from_url(url, test_dir)
        print(f"[PASS] test_extract_subtitles_from_url: {len(subs) if subs else 0} cues")
    finally:
        # Cleanup test files
        for f in test_dir.glob("*"):
            try:
                f.unlink()
            except Exception:
                pass
        try:
            test_dir.rmdir()
        except Exception:
            pass

if __name__ == "__main__":
    test_extract_youtube_id()
    test_get_video_info()
    test_download_and_extract_sub()
    print("ALL TESTS PASSED SUCCESSFULLY!")

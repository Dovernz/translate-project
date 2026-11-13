import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

import app


class VideoBrowserAudioTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app.app)

    def tearDown(self):
        self.client.close()

    def test_youtube_caption_translation_preserves_cue_timing(self):
        captions = [
            {
                "id": 1,
                "start": 1.0,
                "end": 2.0,
                "start_str": "00:00:01.000",
                "end_str": "00:00:02.000",
                "original": "Hello there.",
                "translated": "",
            }
        ]
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch.object(app, "OUTPUT_DIR", Path(temp_dir)),
            patch.object(app, "extract_subtitles_from_url", return_value=captions),
            patch.object(
                app.pool,
                "generate_content",
                new=AsyncMock(return_value='{"1":"Xin chào."}'),
            ),
        ):
            response = self.client.post(
                "/api/video/youtube-captions",
                json={
                    "url": "https://youtu.be/It79k94XMTw",
                    "target_lang": "vi",
                },
            )

        self.assertEqual(response.status_code, 200)
        cue = response.json()["subtitles"][0]
        self.assertEqual((cue["start"], cue["end"]), (1.0, 2.0))
        self.assertEqual(cue["original"], "Hello there.")
        self.assertEqual(cue["translated"], "Xin chào.")

    def test_youtube_caption_route_uses_gemini_transcript_when_public_captions_are_missing(self):
        transcript = (
            '[{"start":"00:00:01.000","end":"00:00:02.000",'
            '"original":"Hello there."}]'
        )
        with (
            patch.object(app, "extract_subtitles_from_url", return_value=None),
            patch.object(
                app.pool,
                "generate_youtube_video_transcript",
                new=AsyncMock(return_value=transcript),
            ) as generate_transcript,
            patch.object(
                app.pool,
                "generate_content",
                new=AsyncMock(return_value='{"1":"Xin chào."}'),
            ),
        ):
            response = self.client.post(
                "/api/video/youtube-captions",
                json={
                    "url": "https://youtu.be/It79k94XMTw",
                    "target_lang": "vi",
                },
            )

        self.assertEqual(response.status_code, 200)
        cue = response.json()["subtitles"][0]
        self.assertEqual(cue["original"], "Hello there.")
        self.assertEqual(cue["translated"], "Xin chào.")
        generate_transcript.assert_awaited_once_with(
            "https://www.youtube.com/watch?v=It79k94XMTw"
        )

    def test_process_url_returns_youtube_captions_before_downloading_media(self):
        subtitles = [
            {
                "id": 1,
                "start": 1.0,
                "end": 2.0,
                "start_str": "00:00:01.000",
                "end_str": "00:00:02.000",
                "original": "Hello",
                "translated": "Xin chào",
            }
        ]
        with (
            patch.object(app, "cleanup_storage"),
            patch.object(app, "_fetch_and_translate_youtube_captions", new=AsyncMock(return_value=subtitles)),
            patch.object(app, "download_video_from_url") as download,
        ):
            response = self.client.post(
                "/api/video/process-url",
                json={
                    "url": "https://youtu.be/It79k94XMTw",
                    "target_lang": "vi",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["mode"], "youtube_captions")
        self.assertEqual(response.json()["subtitles"], subtitles)
        download.assert_not_called()

    def test_process_url_falls_back_to_media_after_transcript_is_unavailable(self):
        with (
            patch.object(app, "cleanup_storage"),
            patch.object(app, "_fetch_and_translate_youtube_captions", new=AsyncMock(return_value=None)),
            patch.object(
                app,
                "download_video_from_url",
                return_value={"success": False, "error": "HTTP 429"},
            ) as download,
        ):
            response = self.client.post(
                "/api/video/process-url",
                json={
                    "url": "https://youtu.be/It79k94XMTw",
                    "target_lang": "vi",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["error"], "HTTP 429")
        self.assertTrue(response.json()["youtube_captions_attempted"])
        download.assert_called_once()

    def test_youtube_caption_route_rejects_non_youtube_urls(self):
        response = self.client.post(
            "/api/video/youtube-captions",
            json={"url": "https://example.test/video", "target_lang": "vi"},
        )

        self.assertEqual(response.status_code, 400)

    def test_capture_transcribes_audio_without_persisting_the_chunk(self):
        with patch.object(
            app.pool,
            "generate_multimodal",
            new=AsyncMock(
                return_value='{"original":"Hello","translated":"Xin chào"}'
            ),
        ) as generate:
            response = self.client.post(
                "/api/video/transcribe-capture-chunk",
                data={"target_lang": "vi"},
                files={"file": ("tab-audio.webm", b"audio bytes", "audio/webm")},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"original": "Hello", "translated": "Xin chào"},
        )
        self.assertEqual(generate.await_args.args[1], "audio/webm")

    def test_capture_rejects_non_audio_and_empty_payloads(self):
        non_audio = self.client.post(
            "/api/video/transcribe-capture-chunk",
            data={"target_lang": "vi"},
            files={"file": ("screen.webm", b"bytes", "video/webm")},
        )
        empty_audio = self.client.post(
            "/api/video/transcribe-capture-chunk",
            data={"target_lang": "vi"},
            files={"file": ("silence.webm", b"", "audio/webm")},
        )

        self.assertEqual(non_audio.status_code, 415)
        self.assertEqual(empty_audio.status_code, 400)

    def test_cleanup_removes_expired_top_level_files_only(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            uploads = root / "uploads"
            outputs = root / "outputs"
            nested = outputs / "documents"
            nested.mkdir(parents=True)
            uploads.mkdir()
            expired = uploads / "expired.mp3"
            recent = outputs / "recent.srt"
            nested_document = nested / "expired.pdf"
            keep = uploads / ".gitkeep"
            expired.write_bytes(b"old")
            recent.write_bytes(b"new")
            nested_document.write_bytes(b"preserve other subsystem data")
            keep.write_bytes(b"")
            old_timestamp = time.time() - 31 * 60
            os.utime(expired, (old_timestamp, old_timestamp))
            os.utime(nested_document, (old_timestamp, old_timestamp))
            os.utime(keep, (old_timestamp, old_timestamp))

            app.cleanup_storage(uploads, outputs, max_age_minutes=30)

            self.assertFalse(expired.exists())
            self.assertTrue(recent.exists())
            self.assertTrue(nested_document.exists())
            self.assertTrue(keep.exists())


if __name__ == "__main__":
    unittest.main()

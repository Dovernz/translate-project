import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import UUID

from core.video_helper import extract_subtitles_from_url


class ExtractSubtitlesFallbackTests(unittest.TestCase):
    def test_keeps_captions_downloaded_before_a_later_language_fails(self):
        output_dir = Path(self.enterContext(TemporaryDirectory()))
        caption_file = output_dir / "deadbeef_sub.en.vtt"

        def download_with_partial_caption(_urls):
            caption_file.write_text(
                "WEBVTT\n\n"
                "00:00:01.000 --> 00:00:02.000\n"
                "Hello there.\n",
                encoding="utf-8",
            )
            raise RuntimeError("HTTP Error 429: Too Many Requests")

        with (
            patch("core.video_helper.yt_dlp.YoutubeDL") as youtube_dl,
            patch(
                "core.video_helper.uuid.uuid4",
                return_value=UUID("deadbeef-0000-0000-0000-000000000000"),
            ),
        ):
            downloader = youtube_dl.return_value.__enter__.return_value
            downloader.download.side_effect = download_with_partial_caption
            subtitles = extract_subtitles_from_url(
                "https://www.youtube.com/watch?v=jNQXAC9IVRw",
                output_dir,
            )

        self.assertIsNotNone(subtitles)
        self.assertEqual(subtitles[0]["original"], "Hello there.")
        self.assertFalse(caption_file.exists())


if __name__ == "__main__":
    unittest.main()

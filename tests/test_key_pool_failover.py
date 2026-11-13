import unittest
from unittest.mock import patch

import httpx

from core.key_pool import KeyPool


class KeyPoolFailoverTests(unittest.IsolatedAsyncioTestCase):
    async def test_youtube_interaction_rotates_to_another_key_after_429(self):
        used_keys = []

        async def handler(request):
            key = request.headers["x-goog-api-key"]
            used_keys.append(key)
            if key == "first-key":
                return httpx.Response(429, json={"error": {"message": "quota"}})
            return httpx.Response(200, json={"output_text": '[{"original":"Hi"}]'})

        transport = httpx.MockTransport(handler)
        real_async_client = httpx.AsyncClient
        pool = KeyPool(keys=["first-key", "second-key"])

        def mock_async_client(**kwargs):
            return real_async_client(transport=transport, **kwargs)

        with patch("core.key_pool.httpx.AsyncClient", side_effect=mock_async_client):
            result = await pool.generate_youtube_video_transcript(
                "https://www.youtube.com/watch?v=It79k94XMTw"
            )

        self.assertEqual(result, '[{"original":"Hi"}]')
        self.assertEqual(used_keys, ["first-key", "second-key"])
        self.assertEqual(pool.usage_stats["first-key"]["errors"], 1)
        self.assertEqual(pool.usage_stats["second-key"]["requests"], 1)

    async def test_multimodal_translation_rotates_keys_after_quota_response(self):
        used_keys = []

        async def handler(request):
            key = request.url.params["key"]
            used_keys.append(key)
            if key == "first-key":
                return httpx.Response(429, json={"error": {"message": "quota"}})
            return httpx.Response(
                200,
                json={
                    "candidates": [
                        {"content": {"parts": [{"text": '{"original":"Hi"}'}]}}
                    ]
                },
            )

        transport = httpx.MockTransport(handler)
        real_async_client = httpx.AsyncClient
        pool = KeyPool(keys=["first-key", "second-key"])

        def mock_async_client(**kwargs):
            return real_async_client(transport=transport, **kwargs)

        with patch("core.key_pool.httpx.AsyncClient", side_effect=mock_async_client):
            result = await pool.generate_multimodal(
                b"audio",
                "audio/webm",
                "Transcribe",
                response_mime_type="application/json",
            )

        self.assertEqual(result, '{"original":"Hi"}')
        self.assertEqual(used_keys, ["first-key", "second-key"])


if __name__ == "__main__":
    unittest.main()

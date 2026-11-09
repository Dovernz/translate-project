import os
import time
import json
import base64
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional, AsyncGenerator
import httpx

def load_gemini_keys() -> List[str]:
    keys = []
    # 1. Local .env
    local_env = Path(".env")
    if local_env.exists():
        try:
            with open(local_env, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GEMINI_API_KEYS="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        keys = [k.strip() for k in val.split(",") if k.strip()]
                    elif line.startswith("GEMINI_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val and val not in keys:
                            keys.append(val)
        except Exception:
            pass

    # 2. Central Agent .env (D:\Thành\Agent\.env)
    if not keys:
        central_env = Path("D:/Thành/Agent/.env")
        if central_env.exists():
            try:
                with open(central_env, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("GEMINI_API_KEYS="):
                            val = line.split("=", 1)[1].strip().strip('"').strip("'")
                            keys = [k.strip() for k in val.split(",") if k.strip()]
                        elif line.startswith("GEMINI_API_KEY="):
                            val = line.split("=", 1)[1].strip().strip('"').strip("'")
                            if val and val not in keys:
                                keys.append(val)
            except Exception:
                pass

    # 3. Process environment variables
    if not keys:
        raw_keys = os.getenv("GEMINI_API_KEYS", "")
        if raw_keys:
            keys = [k.strip() for k in raw_keys.split(",") if k.strip()]
        else:
            single = os.getenv("GEMINI_API_KEY", "")
            if single:
                keys = [single]

    return keys

# Model Tier mapping (Tích hợp Live API & Quota Pool 7 Projects)
MODEL_TIERS = {
    "ultra": {
        "primary": "gemma-4-31b-it",
        "fallbacks": ["gemma-4-26b-a4b-it", "gemini-3.5-flash-lite"],
        "name": "Gemma 4 31B/26B (Ultra High-Speed)",
        "desc": "100.800 req/ngày | 210 RPM - Siêu tốc độ, dịch câu ngắn, phân loại, từ vựng",
        "rpm": 210,
        "rpd": 100800
    },
    "bulk": {
        "primary": "gemini-3.5-flash-lite",
        "fallbacks": ["gemini-3.1-flash-lite", "gemini-2.5-flash-lite"],
        "name": "Gemini 3.5 Flash Lite (Bulk)",
        "desc": "7.000 req/ngày | 210 RPM - Dịch nhanh tài liệu lớn, độ trễ cực thấp",
        "rpm": 210,
        "rpd": 7000
    },
    "standard": {
        "primary": "gemini-3.6-flash",
        "fallbacks": ["gemini-2.5-flash", "gemini-3.5-flash"],
        "name": "Gemini 3.6 Flash (Standard)",
        "desc": "420 req/ngày | 105 RPM - Dịch ngữ cảnh sâu, giữ trọn văn phong & markdown",
        "rpm": 105,
        "rpd": 420
    },
    "deep": {
        "primary": "gemini-3.8-flash",
        "fallbacks": ["gemini-3.6-flash"],
        "name": "Gemini 3.8 Flash (Deep Reasoning)",
        "desc": "140 req/ngày | 35 RPM - Dịch tài liệu học thuật, chuyên ngành, y khoa, pháp lý",
        "rpm": 35,
        "rpd": 140
    },
    "live": {
        "primary": "gemini-3.5-live-translate",
        "fallbacks": ["gemini-3-flash-live", "gemini-3.8-live", "gemini-3.5-flash"],
        "name": "Gemini 3.5 Live Translate (Unlimited RPD)",
        "desc": "Live API Không giới hạn RPD/RPM - Dịch trực tiếp video, manga, audio realtime",
        "rpm": 9999,
        "rpd": 999999
    },
    "transcribe": {
        "primary": "gemini-3.5-transcribe-live",
        "fallbacks": ["gemini-3.5-transcribe", "gemini-3.5-flash-lite"],
        "name": "Gemini 3.5 Transcribe Live (Speech-to-Text)",
        "desc": "Live API Không giới hạn RPD - Bóc băng âm thanh, tạo subtitle tự động",
        "rpm": 9999,
        "rpd": 999999
    },
    "live_dialog": {
        "primary": "gemini-2.5-flash-native-audio-dialog",
        "fallbacks": ["gemini-3-flash-live"],
        "name": "Gemini 2.5 Flash Native Audio Dialog",
        "desc": "Live API Unlimited RPD | 1M TPM - Đối thoại âm thanh tự nhiên tương tác hai chiều",
        "rpm": 9999,
        "rpd": 999999
    },
    "live_thinking": {
        "primary": "gemini-3.8-live-extended-thinking",
        "fallbacks": ["gemini-3.8-live", "gemini-3.8-flash"],
        "name": "Gemini 3.8 Live Extended Thinking",
        "desc": "Live API Unlimited RPD | 65K TPM - Suy luận mở rộng thời gian thực",
        "rpm": 9999,
        "rpd": 999999
    }
}

class KeyPool:
    def __init__(self, keys: Optional[List[str]] = None):
        self.keys = keys or load_gemini_keys()
        self.current_index = 0
        self.cooldowns: Dict[str, float] = {}
        self.usage_stats: Dict[str, Dict[str, int]] = {}
        self.api_base = os.getenv("GEMINI_API_BASE", "https://generativelanguage.googleapis.com/v1beta/models")
        self.cooldown_seconds = int(os.getenv("COOLDOWN_SECONDS", "60"))
        self.request_timeout = float(os.getenv("REQUEST_TIMEOUT", "60.0"))

    def get_status(self) -> Dict[str, Any]:
        now = time.time()
        pool_details = []
        for idx, k in enumerate(self.keys):
            masked = f"{k[:10]}...{k[-6:]}" if len(k) > 16 else "Mã khóa"
            cd = self.cooldowns.get(k, 0)
            remaining_cd = max(0, int(cd - now))
            status = "COOLDOWN" if remaining_cd > 0 else "READY"
            stats = self.usage_stats.get(k, {"requests": 0, "errors": 0})
            pool_details.append({
                "index": idx + 1,
                "masked": masked,
                "status": status,
                "cooldown_remaining": remaining_cd,
                "requests": stats.get("requests", 0),
                "errors": stats.get("errors", 0),
                "is_current": idx == (self.current_index % len(self.keys)) if self.keys else False
            })
        return {
            "total_keys": len(self.keys),
            "current_pointer": (self.current_index % len(self.keys)) + 1 if self.keys else 0,
            "keys": pool_details,
            "tiers": MODEL_TIERS
        }

    def acquire_key(self) -> str:
        if not self.keys:
            raise RuntimeError("Không tìm thấy GEMINI_API_KEYS. Vui lòng kiểm tra file D:\\Thành\\Agent\\.env")
        
        now = time.time()
        n = len(self.keys)
        for _ in range(n):
            key = self.keys[self.current_index % n]
            self.current_index += 1
            if self.cooldowns.get(key, 0) <= now:
                return key
        
        soonest_key = min(self.keys, key=lambda k: self.cooldowns.get(k, 0))
        return soonest_key

    def record_usage(self, key: str, success: bool, status_code: int = 200):
        if key not in self.usage_stats:
            self.usage_stats[key] = {"requests": 0, "errors": 0}
        self.usage_stats[key]["requests"] += 1
        
        if not success:
            self.usage_stats[key]["errors"] += 1
            if status_code == 429:
                self.cooldowns[key] = time.time() + self.cooldown_seconds
            elif status_code in (500, 503):
                self.cooldowns[key] = time.time() + 15

    async def generate_content_stream(
        self,
        prompt: str,
        system_instruction: str = "",
        tier: str = "bulk",
        response_mime_type: Optional[str] = None,
        max_output_tokens: int = 4096
    ) -> AsyncGenerator[str, None]:
        tier_info = MODEL_TIERS.get(tier, MODEL_TIERS["bulk"])
        model_name = tier_info["primary"]
        
        retries = 3
        while retries > 0:
            key = self.acquire_key()
            url = f"{self.api_base}/{model_name}:streamGenerateContent?alt=sse&key={key}"
            
            gen_config: Dict[str, Any] = {
                "temperature": 0.3,
                "maxOutputTokens": max_output_tokens
            }
            if response_mime_type:
                gen_config["responseMimeType"] = response_mime_type

            payload: Dict[str, Any] = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": gen_config
            }
            if system_instruction:
                payload["systemInstruction"] = {
                    "parts": [{"text": system_instruction}]
                }

            try:
                async with httpx.AsyncClient(timeout=self.request_timeout) as client:
                    async with client.stream("POST", url, json=payload) as response:
                        if response.status_code != 200:
                            self.record_usage(key, success=False, status_code=response.status_code)
                            retries -= 1
                            await asyncio.sleep(0.5)
                            continue

                        self.record_usage(key, success=True, status_code=200)
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                data_str = line[6:].strip()
                                if data_str == "[DONE]":
                                    break
                                try:
                                    chunk_json = json.loads(data_str)
                                    candidates = chunk_json.get("candidates", [])
                                    if candidates:
                                        content = candidates[0].get("content", {})
                                        parts = content.get("parts", [])
                                        for p in parts:
                                            text = p.get("text", "")
                                            if text:
                                                yield text
                                except Exception:
                                    continue
                        return
            except Exception:
                self.record_usage(key, success=False, status_code=500)
                retries -= 1
                await asyncio.sleep(0.5)

        yield "\n[Lỗi kết nối hoặc toàn bộ API Keys trong pool đang bận/hết hạn ngạch. Vui lòng thử lại sau vài giây.]"

    async def generate_multimodal(
        self,
        audio_bytes: bytes,
        mime_type: str,
        prompt: str,
        system_instruction: str = "",
        model_name: str = "gemini-3.5-flash-lite",
        response_mime_type: Optional[str] = None
    ) -> str:
        encoded_data = base64.b64encode(audio_bytes).decode("utf-8")
        
        fallback_models = [model_name, "gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-3.6-flash"]
        # Remove duplicates preserving order
        candidate_models = list(dict.fromkeys(fallback_models))

        for current_model in candidate_models:
            retries = 2
            while retries > 0:
                key = self.acquire_key()
                url = f"{self.api_base}/{current_model}:generateContent?key={key}"
                
                parts = [
                    {"text": prompt},
                    {
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": encoded_data
                        }
                    }
                ]
                gen_config: Dict[str, Any] = {
                    "temperature": 0.2,
                    "maxOutputTokens": 8192
                }
                if response_mime_type:
                    gen_config["responseMimeType"] = response_mime_type

                payload: Dict[str, Any] = {
                    "contents": [{"parts": parts}],
                    "generationConfig": gen_config
                }
                if system_instruction:
                    payload["systemInstruction"] = {
                        "parts": [{"text": system_instruction}]
                    }

                try:
                    async with httpx.AsyncClient(timeout=self.request_timeout * 2.0) as client:
                        resp = await client.post(url, json=payload)
                        if resp.status_code != 200:
                            self.record_usage(key, success=False, status_code=resp.status_code)
                            retries -= 1
                            if resp.status_code in [404, 400]:
                                # Switch to next candidate model immediately
                                break
                            await asyncio.sleep(0.5)
                            continue
                        
                        self.record_usage(key, success=True, status_code=200)
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            text_parts = []
                            for p in candidates[0].get("content", {}).get("parts", []):
                                text_parts.append(p.get("text", ""))
                            return "".join(text_parts)
                        return ""
                except Exception:
                    self.record_usage(key, success=False, status_code=500)
                    retries -= 1
                    await asyncio.sleep(0.5)

        raise RuntimeError("Không thể xử lý multimodal qua Gemini Pool sau khi thử các model dự phòng.")

    async def generate_content(
        self,
        prompt: str,
        system_instruction: str = "",
        tier: str = "bulk",
        response_mime_type: Optional[str] = None,
        max_output_tokens: int = 8192
    ) -> str:
        res = []
        async for chunk in self.generate_content_stream(
            prompt,
            system_instruction=system_instruction,
            tier=tier,
            response_mime_type=response_mime_type,
            max_output_tokens=max_output_tokens
        ):
            res.append(chunk)
        return "".join(res)

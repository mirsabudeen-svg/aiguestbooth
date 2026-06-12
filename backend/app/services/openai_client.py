"""Thin OpenAI HTTP client using httpx."""

from __future__ import annotations

import json
from pathlib import Path

import httpx

from app.core.config import get_settings

OPENAI_BASE = "https://api.openai.com/v1"


class OpenAIClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.openai_api_key
        self.chat_model = settings.openai_chat_model
        self.whisper_model = settings.openai_whisper_model

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def transcribe(self, audio_path: str) -> dict:
        path = Path(audio_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        with path.open("rb") as audio_file:
            files = {"file": (path.name, audio_file, "audio/wav")}
            data = {
                "model": self.whisper_model,
                "response_format": "verbose_json",
            }
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    f"{OPENAI_BASE}/audio/transcriptions",
                    headers=self._headers(),
                    files=files,
                    data=data,
                )
                response.raise_for_status()
                payload = response.json()

        text = (payload.get("text") or "").strip()
        language = payload.get("language") or "en"
        duration = payload.get("duration")
        confidence = 0.85 if text else 0.0
        if duration and text:
            confidence = min(0.95, 0.7 + min(duration, 60) / 200)

        return {
            "transcript_text": text,
            "language_code": language[:10] if language else "en",
            "confidence_score": confidence,
        }

    def chat_json(self, system: str, user: str) -> dict:
        body = {
            "model": self.chat_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.3,
        }
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{OPENAI_BASE}/chat/completions",
                headers={**self._headers(), "Content-Type": "application/json"},
                json=body,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)

    def text_to_speech(self, text: str) -> bytes:
        settings = get_settings()
        body = {
            "model": settings.openai_tts_model,
            "input": text[:4096],
            "voice": settings.openai_tts_voice,
            "response_format": "wav",
        }
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{OPENAI_BASE}/audio/speech",
                headers={**self._headers(), "Content-Type": "application/json"},
                json=body,
            )
            response.raise_for_status()
            return response.content

    def moderate(self, text: str) -> str:
        if not text.strip():
            return "pending"

        body = {"input": text}
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{OPENAI_BASE}/moderations",
                headers={**self._headers(), "Content-Type": "application/json"},
                json=body,
            )
            response.raise_for_status()
            result = response.json()["results"][0]

        if result.get("flagged"):
            categories = result.get("categories", {})
            severe = any(
                categories.get(k)
                for k in ("sexual", "violence", "harassment", "hate", "self-harm")
            )
            return "blocked" if severe else "review"
        return "safe"


def get_openai_client() -> OpenAIClient:
    return OpenAIClient()

"""Speech-to-text via OpenAI Whisper."""

from __future__ import annotations

import logging

from app.services.openai_client import get_openai_client

logger = logging.getLogger(__name__)


def transcribe_audio_file(audio_path: str) -> dict:
    client = get_openai_client()
    if not client.enabled:
        logger.warning("OPENAI_API_KEY not set — skipping transcription")
        return {
            "transcript_text": "",
            "language_code": "en",
            "confidence_score": 0.0,
        }

    return client.transcribe(audio_path)

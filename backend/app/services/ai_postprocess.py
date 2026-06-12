"""LLM enrichment: cleanup, summary, sentiment, tags."""

from __future__ import annotations

import logging
import re

from app.services.openai_client import get_openai_client

logger = logging.getLogger(__name__)

ALLOWED_SENTIMENTS = {"positive", "neutral", "emotional", "funny", "advice", "blessing"}
ALLOWED_TAGS = {
    "family",
    "friends",
    "funny",
    "emotional",
    "advice",
    "blessing",
    "children",
    "memories",
    "gratitude",
    "celebration",
}

SYSTEM_PROMPT = """You process transcripts from wedding and event audio guestbook booths.
Return JSON only with these fields:
- cleaned_text: punctuated, readable version of the transcript
- summary: one sentence, max 200 characters
- sentiment: one of positive, neutral, emotional, funny, advice, blessing
- tags: array of 1-5 short lowercase labels chosen from:
  family, friends, funny, emotional, advice, blessing, children, memories, gratitude, celebration
If the transcript is empty or unintelligible, return empty strings and empty tags with sentiment neutral."""


def _basic_cleanup(raw_text: str) -> str:
    text = raw_text.strip()
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    if text and text[-1] not in ".!?":
        text += "."
    return text


def _basic_summary(cleaned_text: str) -> str:
    if not cleaned_text:
        return ""
    return cleaned_text[:200] + ("..." if len(cleaned_text) > 200 else "")


def enrich_transcript(raw_text: str) -> dict:
    """Single LLM call for cleanup, summary, sentiment, and tags."""
    client = get_openai_client()
    if not client.enabled or not raw_text.strip():
        cleaned = _basic_cleanup(raw_text)
        return {
            "cleaned_text": cleaned,
            "summary_text": _basic_summary(cleaned),
            "sentiment_label": "neutral",
            "tags": [],
        }

    try:
        result = client.chat_json(
            SYSTEM_PROMPT,
            f"Transcript:\n{raw_text}",
        )
        cleaned = (result.get("cleaned_text") or "").strip() or _basic_cleanup(raw_text)
        summary = (result.get("summary") or result.get("summary_text") or "").strip()
        if not summary:
            summary = _basic_summary(cleaned)

        sentiment = (result.get("sentiment") or result.get("sentiment_label") or "neutral").lower()
        if sentiment not in ALLOWED_SENTIMENTS:
            sentiment = "neutral"

        raw_tags = result.get("tags") or []
        tags = []
        for tag in raw_tags:
            t = str(tag).lower().strip()
            if t in ALLOWED_TAGS and t not in tags:
                tags.append(t)

        return {
            "cleaned_text": cleaned,
            "summary_text": summary[:200],
            "sentiment_label": sentiment,
            "tags": tags[:5],
        }
    except Exception as exc:
        logger.exception("LLM enrichment failed: %s", exc)
        cleaned = _basic_cleanup(raw_text)
        return {
            "cleaned_text": cleaned,
            "summary_text": _basic_summary(cleaned),
            "sentiment_label": "neutral",
            "tags": [],
        }


def cleanup_transcript(raw_text: str) -> str:
    return enrich_transcript(raw_text)["cleaned_text"]


def summarize_message(cleaned_text: str) -> str:
    return _basic_summary(cleaned_text)


def classify_sentiment(cleaned_text: str) -> str:
    return enrich_transcript(cleaned_text)["sentiment_label"]


def extract_tags(cleaned_text: str, summary: str) -> list[str]:
    return enrich_transcript(cleaned_text or summary)["tags"]

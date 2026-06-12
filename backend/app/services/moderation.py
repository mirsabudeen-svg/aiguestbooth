"""Content safety screening."""

from __future__ import annotations

import logging

from app.services.openai_client import get_openai_client

logger = logging.getLogger(__name__)


def moderate_text(text: str) -> str:
    """Returns: safe | review | blocked | pending"""
    if not text.strip():
        return "pending"

    client = get_openai_client()
    if not client.enabled:
        return "safe"

    try:
        return client.moderate(text)
    except Exception as exc:
        logger.exception("Moderation failed: %s", exc)
        return "review"

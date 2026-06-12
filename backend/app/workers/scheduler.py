"""Schedule AI jobs on background threads."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID

from app.workers.jobs import run_full_pipeline

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ai-worker")


def schedule_processing(audio_message_id: UUID, job_id: UUID | None = None) -> None:
    logger.info("Scheduling AI pipeline for message %s", audio_message_id)
    _executor.submit(run_full_pipeline, audio_message_id, job_id=job_id)

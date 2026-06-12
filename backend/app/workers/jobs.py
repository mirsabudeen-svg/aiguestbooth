"""Background AI processing jobs."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.audio_message import AudioMessage
from app.models.message_tag import MessageTag
from app.models.processing_job import ProcessingJob
from app.models.transcript import Transcript
from app.services.ai_postprocess import enrich_transcript
from app.services.audio_storage import AudioStorageService
from app.services.moderation import moderate_text
from app.services.openai_client import get_openai_client
from app.services.transcription import transcribe_audio_file

logger = logging.getLogger(__name__)


def _latest_job(db: Session, audio_message_id: UUID, statuses: list[str] | None = None) -> ProcessingJob | None:
    query = db.query(ProcessingJob).filter(ProcessingJob.audio_message_id == audio_message_id)
    if statuses:
        query = query.filter(ProcessingJob.status.in_(statuses))
    return query.order_by(ProcessingJob.created_at.desc()).first()


def get_processing_status(db: Session, audio_message_id: UUID) -> str:
    job = _latest_job(db, audio_message_id)
    if not job:
        return "none"
    return job.status


def enqueue_processing(db: Session, audio_message_id: UUID) -> ProcessingJob:
    job = ProcessingJob(audio_message_id=audio_message_id, status="queued")
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def run_full_pipeline(audio_message_id: UUID, *, job_id: UUID | None = None) -> None:
    db = SessionLocal()
    storage = AudioStorageService()
    job: ProcessingJob | None = None

    try:
        if job_id:
            job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        if not job:
            job = _latest_job(db, audio_message_id, statuses=["queued", "failed"])
        if not job:
            logger.warning("No processing job for message %s", audio_message_id)
            return

        if job.status == "running":
            logger.info("Job %s already running", job.id)
            return

        job.status = "running"
        job.attempts += 1
        job.started_at = datetime.now(timezone.utc)
        job.error_message = None
        db.commit()

        message = db.query(AudioMessage).filter(AudioMessage.id == audio_message_id).first()
        if not message:
            raise ValueError("Audio message not found")

        path = storage.resolve_local_path(message.raw_audio_path)
        if not path or not path.exists():
            raise FileNotFoundError(f"Audio file missing: {message.raw_audio_path}")

        client = get_openai_client()
        if not client.enabled:
            raise ValueError("OPENAI_API_KEY not configured — cannot run AI pipeline")

        stt = transcribe_audio_file(str(path))
        enrichment = enrich_transcript(stt["transcript_text"])
        moderation = moderate_text(enrichment["cleaned_text"] or stt["transcript_text"])

        transcript = message.transcript
        if not transcript:
            transcript = Transcript(audio_message_id=message.id)
            db.add(transcript)

        transcript.transcript_text = stt["transcript_text"]
        transcript.cleaned_text = enrichment["cleaned_text"]
        transcript.summary_text = enrichment["summary_text"]
        transcript.sentiment_label = enrichment["sentiment_label"]
        transcript.moderation_label = moderation
        transcript.language_code = stt.get("language_code")
        transcript.confidence_score = stt.get("confidence_score")
        transcript.processed_at = datetime.now(timezone.utc)

        db.query(MessageTag).filter(MessageTag.audio_message_id == message.id).delete()
        for tag in enrichment["tags"]:
            db.add(MessageTag(audio_message_id=message.id, tag=tag))

        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("Processing complete for message %s", audio_message_id)
    except Exception as exc:
        logger.exception("Processing failed for %s: %s", audio_message_id, exc)
        db.rollback()
        if job:
            job = db.query(ProcessingJob).filter(ProcessingJob.id == job.id).first()
            if job:
                job.status = "failed"
                job.error_message = str(exc)[:500]
                db.commit()
    finally:
        db.close()

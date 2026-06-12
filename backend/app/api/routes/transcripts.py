from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import DbSession, OperatorAuth
from app.core.config import get_settings
from app.models.transcript import Transcript
from app.schemas.transcript import TranscriptResponse, TranscriptUpdate
from app.workers.jobs import enqueue_processing
from app.workers.scheduler import schedule_processing

router = APIRouter(prefix="/transcripts", tags=["transcripts"])


@router.patch("/{transcript_id}", response_model=TranscriptResponse)
def update_transcript(
    transcript_id: UUID, body: TranscriptUpdate, db: DbSession, _: OperatorAuth
) -> TranscriptResponse:
    transcript = db.query(Transcript).filter(Transcript.id == transcript_id).first()
    if not transcript:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcript not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(transcript, key, value)
    db.commit()
    db.refresh(transcript)
    return transcript


@router.post("/{transcript_id}/reprocess")
def reprocess_transcript(transcript_id: UUID, db: DbSession, _: OperatorAuth) -> dict:
    settings = get_settings()
    transcript = db.query(Transcript).filter(Transcript.id == transcript_id).first()
    if not transcript:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcript not found")

    job = enqueue_processing(db, transcript.audio_message_id)
    if settings.ai_pipeline_enabled:
        schedule_processing(transcript.audio_message_id, job_id=job.id)

    return {"ok": True, "message": "Reprocessing queued", "job_id": str(job.id)}


class ModerateRequest(BaseModel):
    action: str = Field(..., pattern="^(approve|block|review)$")


@router.post("/{transcript_id}/moderate", response_model=TranscriptResponse)
def moderate_transcript(
    transcript_id: UUID, body: ModerateRequest, db: DbSession, _: OperatorAuth
) -> TranscriptResponse:
    transcript = db.query(Transcript).filter(Transcript.id == transcript_id).first()
    if not transcript:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcript not found")

    label_map = {"approve": "safe", "block": "blocked", "review": "review"}
    transcript.moderation_label = label_map[body.action]
    db.commit()
    db.refresh(transcript)
    return transcript

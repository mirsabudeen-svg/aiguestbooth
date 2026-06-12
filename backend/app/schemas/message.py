from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import PaginatedMeta


class TranscriptSummary(BaseModel):
    id: UUID
    cleaned_text: str | None
    summary_text: str | None
    sentiment_label: str | None
    moderation_label: str
    confidence_score: float | None

    model_config = {"from_attributes": True}


class MessageListItem(BaseModel):
    id: UUID
    session_id: UUID
    event_id: UUID
    booth_name: str | None
    duration_seconds: float | None
    created_at: datetime
    upload_status: str
    processing_status: str = "none"
    summary_text: str | None = None
    sentiment_label: str | None = None
    moderation_label: str | None = None
    transcript_preview: str | None = None
    tags: list[str] = []
    starred: bool = False
    has_snapshot: bool = False


class MessageListResponse(BaseModel):
    items: list[MessageListItem]
    meta: PaginatedMeta


class ProcessingJobSummary(BaseModel):
    id: UUID
    status: str
    attempts: int
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class MessageDetail(BaseModel):
    id: UUID
    session_id: UUID
    event_id: UUID
    booth_id: UUID
    duration_seconds: float | None
    file_size_bytes: int | None
    checksum: str
    audio_url: str
    created_at: datetime
    processing_status: str = "none"
    processing_job: ProcessingJobSummary | None = None
    transcript: TranscriptSummary | None
    tags: list[str] = []
    starred: bool = False
    snapshot_url: str | None = None


class MessageUpdate(BaseModel):
    flagged: bool | None = None
    starred: bool | None = None

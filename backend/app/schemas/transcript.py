from uuid import UUID

from pydantic import BaseModel


class TranscriptUpdate(BaseModel):
    cleaned_text: str | None = None
    summary_text: str | None = None


class TranscriptResponse(BaseModel):
    id: UUID
    audio_message_id: UUID
    transcript_text: str | None
    cleaned_text: str | None
    summary_text: str | None
    sentiment_label: str | None
    moderation_label: str
    language_code: str | None
    confidence_score: float | None

    model_config = {"from_attributes": True}

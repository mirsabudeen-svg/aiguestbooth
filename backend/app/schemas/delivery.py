from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DeliveryMessageItem(BaseModel):
    id: UUID
    session_id: UUID
    duration_seconds: float | None
    created_at: datetime
    summary_text: str | None
    transcript_preview: str | None
    tags: list[str]
    has_snapshot: bool
    audio_url: str
    snapshot_url: str | None


class DeliveryPageResponse(BaseModel):
    event_name: str
    event_type: str
    venue: str | None
    branding_json: dict | None
    message_count: int
    messages: list[DeliveryMessageItem]


class DeliverySettingsResponse(BaseModel):
    delivery_enabled: bool
    delivery_token: str | None
    share_url: str | None
    qr_url: str | None

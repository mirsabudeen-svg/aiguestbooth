from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class BrandingConfig(BaseModel):
    primary_color: str | None = None
    secondary_color: str | None = None
    logo_url: str | None = None


class EventCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    event_type: str = "wedding"
    venue: str | None = None
    max_record_seconds: int = Field(default=120, ge=10, le=300)
    prompt_audio_url: str | None = None
    thank_you_audio_url: str | None = None
    moderation_enabled: bool = True
    retention_days: int = Field(default=90, ge=1, le=3650)
    branding_json: BrandingConfig | dict | None = None


class EventUpdate(BaseModel):
    name: str | None = None
    venue: str | None = None
    max_record_seconds: int | None = Field(None, ge=10, le=300)
    prompt_audio_url: str | None = None
    thank_you_audio_url: str | None = None
    is_active: bool | None = None
    moderation_enabled: bool | None = None
    retention_days: int | None = Field(None, ge=1, le=3650)
    branding_json: BrandingConfig | dict | None = None


class EventResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    event_type: str
    venue: str | None
    max_record_seconds: int
    is_active: bool
    moderation_enabled: bool
    retention_days: int
    prompt_audio_url: str | None
    thank_you_audio_url: str | None
    branding_json: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}

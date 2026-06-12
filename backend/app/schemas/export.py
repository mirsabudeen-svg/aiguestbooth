from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ExportCreate(BaseModel):
    event_id: UUID
    format: str = Field(default="zip", pattern="^(zip|csv|reel|slideshow)$")
    message_ids: list[UUID] | None = None


class ExportResponse(BaseModel):
    id: UUID
    event_id: UUID
    status: str
    format: str
    output_path: str | None
    download_url: str | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}

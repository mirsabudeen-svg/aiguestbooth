from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SessionStartRequest(BaseModel):
    trigger_type: str = Field(default="button", pattern="^(button|handset)$")
    local_reference: str | None = None


class SessionStartResponse(BaseModel):
    session_id: UUID
    event_id: UUID
    booth_id: UUID
    max_record_seconds: int
    started_at: datetime
    status: str


class SessionCompleteRequest(BaseModel):
    duration_seconds: float | None = None


class SessionCompleteResponse(BaseModel):
    session_id: UUID
    status: str
    upload_status: str
    message: str = "Session completed"

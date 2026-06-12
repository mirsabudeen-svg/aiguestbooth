from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class BoothCreate(BaseModel):
    event_id: UUID
    name: str = Field(..., min_length=1, max_length=100)
    location_label: str | None = None


class BoothAssignDevice(BaseModel):
    device_id: UUID | None = None


class BoothResponse(BaseModel):
    id: UUID
    event_id: UUID
    name: str
    location_label: str | None
    status: str
    assigned_device_id: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}

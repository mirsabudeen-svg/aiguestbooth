from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DeviceRegisterRequest(BaseModel):
    serial_number: str = Field(..., min_length=3, max_length=100)
    firmware_version: str | None = None
    display_name: str | None = None


class DeviceRegisterResponse(BaseModel):
    device_id: UUID
    token: str
    message: str = "Store this token securely on the device. It will not be shown again."


class DeviceHeartbeatRequest(BaseModel):
    wifi_strength: int | None = Field(None, ge=0, le=100)
    battery_level: int | None = Field(None, ge=0, le=100)
    state: str | None = None
    queue_depth: int = 0
    firmware_version: str | None = None


class DeviceHeartbeatResponse(BaseModel):
    ok: bool = True
    server_time: datetime


class DeviceConfigResponse(BaseModel):
    event_id: UUID | None = None
    event_name: str | None = None
    booth_id: UUID | None = None
    booth_name: str | None = None
    max_record_seconds: int = 120
    prompt_audio_url: str | None = None
    thank_you_audio_url: str | None = None
    idle_attract_enabled: bool = True
    delivery_share_url: str | None = None
    delivery_qr_url: str | None = None
    assigned: bool = False


class DeviceErrorRequest(BaseModel):
    code: str
    message: str
    session_id: UUID | None = None


class DeviceListItem(BaseModel):
    id: UUID
    serial_number: str
    display_name: str
    status: str
    current_state: str | None
    firmware_version: str | None
    last_seen_at: datetime | None
    last_error_code: str | None
    last_error_message: str | None
    last_error_at: datetime | None
    assigned_booth_id: UUID | None
    assigned_booth_name: str | None
    assigned_event_id: UUID | None

    model_config = {"from_attributes": True}

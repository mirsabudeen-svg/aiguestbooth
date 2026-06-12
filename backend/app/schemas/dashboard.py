from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class BoothStatusItem(BaseModel):
    booth_id: UUID
    booth_name: str
    status: str
    device_state: str | None
    last_seen_at: datetime | None
    messages_today: int
    pending_uploads: int


class DeviceAlertItem(BaseModel):
    device_id: UUID
    serial_number: str
    booth_name: str | None
    error_code: str | None
    error_message: str | None
    error_at: datetime | None
    status: str


class DashboardOverview(BaseModel):
    event_id: UUID | None
    event_name: str | None
    total_messages: int
    messages_today: int
    pending_uploads: int
    failed_uploads: int
    processing_queue: int
    booths: list[BoothStatusItem]
    device_alerts: list[DeviceAlertItem] = []

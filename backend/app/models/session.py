import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class GuestSession(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("events.id"), index=True)
    booth_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("booths.id"), index=True)
    device_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("devices.id"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trigger_type: Mapped[str] = mapped_column(String(20), default="button")
    status: Mapped[str] = mapped_column(String(30), default="started", index=True)
    upload_status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    local_reference: Mapped[str | None] = mapped_column(String(100))

    event = relationship("Event", back_populates="sessions")
    booth = relationship("Booth", back_populates="sessions")
    device = relationship("Device", back_populates="sessions")
    audio_message = relationship("AudioMessage", back_populates="session", uselist=False)

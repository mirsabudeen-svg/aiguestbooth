import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), default="wedding")
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    venue: Mapped[str | None] = mapped_column(String(255))
    branding_json: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    prompt_audio_url: Mapped[str | None] = mapped_column(Text)
    thank_you_audio_url: Mapped[str | None] = mapped_column(Text)
    max_record_seconds: Mapped[int] = mapped_column(Integer, default=120)
    language_mode: Mapped[str] = mapped_column(String(20), default="auto")
    moderation_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    retention_days: Mapped[int] = mapped_column(Integer, default=90)
    delivery_token: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    delivery_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    booth_qr_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    booths = relationship("Booth", back_populates="event")
    sessions = relationship("GuestSession", back_populates="event")
    export_jobs = relationship("ExportJob", back_populates="event")

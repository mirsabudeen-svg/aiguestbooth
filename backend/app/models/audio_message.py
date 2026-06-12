import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AudioMessage(Base):
    __tablename__ = "audio_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id"), unique=True, index=True
    )
    raw_audio_path: Mapped[str] = mapped_column(Text, nullable=False)
    snapshot_path: Mapped[str | None] = mapped_column(Text)
    normalized_audio_path: Mapped[str | None] = mapped_column(Text)
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    mime_type: Mapped[str] = mapped_column(String(50), default="audio/wav")
    checksum: Mapped[str] = mapped_column(String(64), index=True)
    starred: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session = relationship("GuestSession", back_populates="audio_message")
    transcript = relationship("Transcript", back_populates="audio_message", uselist=False)
    tags = relationship("MessageTag", back_populates="audio_message")
    notes = relationship("OperatorNote", back_populates="audio_message")
    processing_jobs = relationship("ProcessingJob", back_populates="audio_message")

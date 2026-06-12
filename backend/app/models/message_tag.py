import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MessageTag(Base):
    __tablename__ = "message_tags"
    __table_args__ = (UniqueConstraint("audio_message_id", "tag", name="uq_message_tag"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audio_message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audio_messages.id"), index=True
    )
    tag: Mapped[str] = mapped_column(String(50), nullable=False)

    audio_message = relationship("AudioMessage", back_populates="tags")

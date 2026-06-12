"""Delete audio older than each event's retention_days policy."""

from datetime import datetime, timedelta, timezone

from app.db.session import SessionLocal
from app.models.audio_message import AudioMessage
from app.models.event import Event
from app.models.session import GuestSession
from app.services.audio_storage import get_storage
from app.services.audit_service import get_audit_service


def main() -> None:
    db = SessionLocal()
    storage = get_storage()
    audit = get_audit_service()
    now = datetime.now(timezone.utc)
    deleted = 0

    try:
        events = db.query(Event).all()
        for event in events:
            cutoff = now - timedelta(days=event.retention_days or 90)
            messages = (
                db.query(AudioMessage)
                .join(GuestSession, AudioMessage.session_id == GuestSession.id)
                .filter(GuestSession.event_id == event.id, AudioMessage.created_at < cutoff)
                .all()
            )
            for msg in messages:
                if msg.raw_audio_path:
                    storage.delete_file(msg.raw_audio_path)
                if msg.snapshot_path:
                    storage.delete_file(msg.snapshot_path)
                audit.log(
                    db,
                    actor_type="system",
                    actor_id="retention",
                    action="delete",
                    resource_type="audio_message",
                    resource_id=str(msg.id),
                    details={"event_id": str(event.id), "retention_days": event.retention_days},
                )
                db.delete(msg)
                deleted += 1
        db.commit()
        print(f"Purged {deleted} message(s) past retention policy.")
    finally:
        db.close()


if __name__ == "__main__":
    main()

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.booth import Booth
from app.models.device import Device
from app.models.event import Event
from app.models.session import GuestSession
from app.schemas.device import DeviceConfigResponse
from app.services.audio_storage import get_storage


def storage_asset_url(base: str, event_id: UUID, asset_type: str) -> str | None:
    storage = get_storage()
    relative = f"events/{event_id}/assets/{asset_type}.wav"
    if storage.settings.storage_backend == "local":
        path = storage.resolve_local_path(relative)
        if not path:
            return None
    return f"{base}/api/v1/events/{event_id}/assets/{asset_type}.wav"


class SessionService:
    def get_device_config(self, db: Session, device: Device) -> DeviceConfigResponse:
        booth = db.query(Booth).filter(Booth.assigned_device_id == device.id).first()
        if not booth:
            return DeviceConfigResponse(assigned=False)

        event = db.query(Event).filter(Event.id == booth.event_id, Event.is_active.is_(True)).first()
        if not event:
            return DeviceConfigResponse(assigned=False)

        settings = get_settings()
        base = settings.public_api_url.rstrip("/")

        def _abs_url(url: str | None) -> str | None:
            if not url:
                return None
            if url.startswith("http://") or url.startswith("https://"):
                return url
            if url.startswith("/"):
                return f"{base}{url}"
            return url

        prompt_url = event.prompt_audio_url or storage_asset_url(base, event.id, "prompt")
        thank_you_url = event.thank_you_audio_url or storage_asset_url(base, event.id, "thank_you")

        delivery_share_url = None
        delivery_qr_url = None
        if event.delivery_enabled and event.delivery_token and event.booth_qr_enabled:
            frontend = settings.frontend_public_url.rstrip("/")
            delivery_share_url = f"{frontend}/share/{event.delivery_token}"
            delivery_qr_url = (
                f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={delivery_share_url}"
            )

        return DeviceConfigResponse(
            event_id=event.id,
            event_name=event.name,
            booth_id=booth.id,
            booth_name=booth.name,
            max_record_seconds=event.max_record_seconds,
            prompt_audio_url=_abs_url(prompt_url),
            thank_you_audio_url=_abs_url(thank_you_url),
            idle_attract_enabled=True,
            delivery_share_url=delivery_share_url,
            delivery_qr_url=delivery_qr_url,
            assigned=True,
        )

    def get_active_session(self, db: Session, device_id: UUID) -> GuestSession | None:
        return (
            db.query(GuestSession)
            .filter(
                GuestSession.device_id == device_id,
                GuestSession.status.in_(["started", "recording"]),
            )
            .order_by(GuestSession.started_at.desc())
            .first()
        )

    def start_session(
        self,
        db: Session,
        device: Device,
        trigger_type: str,
        local_reference: str | None,
    ) -> tuple[GuestSession, Event, Booth]:
        existing = self.get_active_session(db, device.id)
        if existing:
            booth = db.query(Booth).filter(Booth.id == existing.booth_id).first()
            event = db.query(Event).filter(Event.id == existing.event_id).first()
            return existing, event, booth  # type: ignore[return-value]

        booth = db.query(Booth).filter(Booth.assigned_device_id == device.id).first()
        if not booth:
            raise ValueError("DEVICE_NOT_ASSIGNED")

        event = db.query(Event).filter(Event.id == booth.event_id, Event.is_active.is_(True)).first()
        if not event:
            raise ValueError("EVENT_NOT_ACTIVE")

        session = GuestSession(
            event_id=event.id,
            booth_id=booth.id,
            device_id=device.id,
            trigger_type=trigger_type,
            status="started",
            upload_status="pending",
            local_reference=local_reference,
        )
        db.add(session)
        booth.status = "online"
        db.commit()
        db.refresh(session)
        return session, event, booth

    def complete_session(
        self, db: Session, session: GuestSession, duration_seconds: float | None
    ) -> GuestSession:
        session.status = "completed"
        session.ended_at = datetime.now(timezone.utc)
        if duration_seconds is not None and session.audio_message:
            session.audio_message.duration_seconds = duration_seconds
        db.commit()
        db.refresh(session)
        return session

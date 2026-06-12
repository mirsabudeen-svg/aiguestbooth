from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import joinedload

from app.api.deps import DbSession
from app.core.config import get_settings
from app.models.audio_message import AudioMessage
from app.models.event import Event
from app.models.session import GuestSession
from app.models.transcript import Transcript
from app.schemas.delivery import DeliveryMessageItem, DeliveryPageResponse
from app.services.audio_storage import get_storage

router = APIRouter(prefix="/delivery", tags=["delivery"])


def _get_event_by_token(db: DbSession, token: str) -> Event:
    event = (
        db.query(Event)
        .filter(Event.delivery_token == token, Event.delivery_enabled.is_(True))
        .first()
    )
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery page not found")
    return event


@router.get("/{token}", response_model=DeliveryPageResponse)
def get_delivery_page(token: str, db: DbSession) -> DeliveryPageResponse:
    event = _get_event_by_token(db, token)
    settings = get_settings()
    api_base = settings.public_api_url.rstrip("/")

    messages = (
        db.query(AudioMessage)
        .join(GuestSession, AudioMessage.session_id == GuestSession.id)
        .outerjoin(Transcript)
        .options(joinedload(AudioMessage.transcript), joinedload(AudioMessage.tags))
        .filter(
            GuestSession.event_id == event.id,
            Transcript.moderation_label == "safe",
        )
        .order_by(AudioMessage.starred.desc(), AudioMessage.created_at.asc())
        .all()
    )

    items: list[DeliveryMessageItem] = []
    for msg in messages:
        transcript = msg.transcript
        preview = None
        if transcript:
            preview = transcript.cleaned_text or transcript.transcript_text
            if preview and len(preview) > 200:
                preview = preview[:200] + "..."

        snapshot_url = None
        if msg.snapshot_path:
            snapshot_url = f"{api_base}/api/v1/delivery/{token}/snapshot/{msg.session_id}.jpg"

        items.append(
            DeliveryMessageItem(
                id=msg.id,
                session_id=msg.session_id,
                duration_seconds=msg.duration_seconds,
                created_at=msg.created_at,
                summary_text=transcript.summary_text if transcript else None,
                transcript_preview=preview,
                tags=[t.tag for t in msg.tags],
                has_snapshot=bool(msg.snapshot_path),
                audio_url=f"{api_base}/api/v1/delivery/{token}/audio/{msg.session_id}.wav",
                snapshot_url=snapshot_url,
            )
        )

    return DeliveryPageResponse(
        event_name=event.name,
        event_type=event.event_type,
        venue=event.venue,
        branding_json=event.branding_json,
        message_count=len(items),
        messages=items,
    )


@router.get("/{token}/audio/{session_id}.wav")
def stream_delivery_audio(token: str, session_id: UUID, db: DbSession) -> Response:
    event = _get_event_by_token(db, token)
    msg = (
        db.query(AudioMessage)
        .join(GuestSession, AudioMessage.session_id == GuestSession.id)
        .filter(AudioMessage.session_id == session_id, GuestSession.event_id == event.id)
        .first()
    )
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio not found")

    storage = get_storage()
    settings = get_settings()
    if settings.storage_backend == "local":
        path = storage.resolve_local_path(msg.raw_audio_path)
        if not path:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file missing")
        return Response(content=path.read_bytes(), media_type="audio/wav")

    data = storage.read_bytes(msg.raw_audio_path)
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file missing")
    return Response(content=data, media_type="audio/wav")


@router.get("/{token}/snapshot/{session_id}.jpg")
def stream_delivery_snapshot(token: str, session_id: UUID, db: DbSession) -> Response:
    event = _get_event_by_token(db, token)
    msg = (
        db.query(AudioMessage)
        .join(GuestSession, AudioMessage.session_id == GuestSession.id)
        .filter(AudioMessage.session_id == session_id, GuestSession.event_id == event.id)
        .first()
    )
    if not msg or not msg.snapshot_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found")

    storage = get_storage()
    data = storage.read_bytes(msg.snapshot_path)
    if not data and storage.settings.storage_backend == "local":
        path = storage.resolve_local_path(msg.snapshot_path)
        data = path.read_bytes() if path else None
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot file missing")
    return Response(content=data, media_type="image/jpeg")

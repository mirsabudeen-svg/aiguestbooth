from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import Response

from app.api.deps import AdminAuth, DbSession, OperatorAuth
from app.core.config import get_settings
from app.models.event import Event
from pydantic import BaseModel, Field

from app.core.security import generate_delivery_token
from app.schemas.delivery import DeliverySettingsResponse
from app.schemas.event import EventCreate, EventResponse, EventUpdate
from app.services.audio_storage import get_storage
from app.services.tts_service import get_tts_service

router = APIRouter(prefix="/events", tags=["events"])

ASSET_TYPES = {"prompt", "thank_you"}


@router.get("", response_model=list[EventResponse])
def list_events(db: DbSession, _: OperatorAuth) -> list[EventResponse]:
    return db.query(Event).order_by(Event.created_at.desc()).all()


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(body: EventCreate, db: DbSession, _: AdminAuth) -> EventResponse:
    if db.query(Event).filter(Event.slug == body.slug).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already exists")
    data = body.model_dump()
    branding = data.pop("branding_json", None)
    if branding is not None and hasattr(branding, "model_dump"):
        branding = branding.model_dump(exclude_none=True)
    event = Event(**data, branding_json=branding or {})
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("/{event_id}", response_model=EventResponse)
def get_event(event_id: UUID, db: DbSession, _: OperatorAuth) -> EventResponse:
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


@router.patch("/{event_id}", response_model=EventResponse)
def update_event(
    event_id: UUID, body: EventUpdate, db: DbSession, _: AdminAuth
) -> EventResponse:
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        if key == "branding_json" and value is not None:
            if hasattr(value, "model_dump"):
                value = value.model_dump(exclude_none=True)
            existing = event.branding_json or {}
            existing.update(value)
            setattr(event, key, existing)
        else:
            setattr(event, key, value)
    db.commit()
    db.refresh(event)
    return event


@router.post("/{event_id}/assets/{asset_type}")
async def upload_event_asset(
    event_id: UUID,
    asset_type: str,
    db: DbSession,
    _: AdminAuth,
    file: UploadFile = File(...),
) -> dict:
    if asset_type not in ASSET_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid asset type")

    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    data = await file.read()
    if len(data) > get_settings().max_upload_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large")

    storage = get_storage()
    storage.save_event_asset(event_id, asset_type, data)
    public_url = storage.get_asset_public_url(event_id, asset_type)

    if asset_type == "prompt":
        event.prompt_audio_url = public_url
    else:
        event.thank_you_audio_url = public_url
    db.commit()

    return {"ok": True, "asset_type": asset_type, "url": public_url}


@router.get("/{event_id}/assets/{asset_type}.wav")
def serve_event_asset(event_id: UUID, asset_type: str, db: DbSession) -> Response:
    if asset_type not in ASSET_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid asset type")

    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    storage = get_storage()
    relative = f"events/{event_id}/assets/{asset_type}.wav"
    data = storage.read_bytes(relative)
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    return Response(content=data, media_type="audio/wav")


def _delivery_settings(event: Event) -> DeliverySettingsResponse:
    settings = get_settings()
    share_url = None
    qr_url = None
    if event.delivery_enabled and event.delivery_token:
        share_url = f"{settings.frontend_public_url.rstrip('/')}/share/{event.delivery_token}"
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=240x240&data={share_url}"
    return DeliverySettingsResponse(
        delivery_enabled=event.delivery_enabled,
        delivery_token=event.delivery_token,
        share_url=share_url,
        qr_url=qr_url,
    )


@router.get("/{event_id}/delivery", response_model=DeliverySettingsResponse)
def get_delivery_settings(event_id: UUID, db: DbSession, _: AdminAuth) -> DeliverySettingsResponse:
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return _delivery_settings(event)


@router.post("/{event_id}/delivery/enable", response_model=DeliverySettingsResponse)
def enable_delivery(event_id: UUID, db: DbSession, _: AdminAuth) -> DeliverySettingsResponse:
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    if not event.delivery_token:
        event.delivery_token = generate_delivery_token()
    event.delivery_enabled = True
    db.commit()
    db.refresh(event)
    return _delivery_settings(event)


@router.post("/{event_id}/delivery/disable", response_model=DeliverySettingsResponse)
def disable_delivery(event_id: UUID, db: DbSession, _: AdminAuth) -> DeliverySettingsResponse:
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    event.delivery_enabled = False
    db.commit()
    db.refresh(event)
    return _delivery_settings(event)


@router.post("/{event_id}/delivery/rotate", response_model=DeliverySettingsResponse)
def rotate_delivery_token(event_id: UUID, db: DbSession, _: AdminAuth) -> DeliverySettingsResponse:
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    event.delivery_token = generate_delivery_token()
    event.delivery_enabled = True
    db.commit()
    db.refresh(event)
    return _delivery_settings(event)


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)
    asset_type: str = Field(default="prompt", pattern="^(prompt|thank_you)$")


@router.post("/{event_id}/tts")
def generate_tts(event_id: UUID, body: TTSRequest, db: DbSession, _: AdminAuth) -> dict:
    try:
        url = get_tts_service().generate_prompt(db, event_id, body.text, body.asset_type)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"ok": True, "url": url, "asset_type": body.asset_type}

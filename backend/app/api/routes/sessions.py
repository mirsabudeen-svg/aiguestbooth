from fastapi import APIRouter, HTTPException, status

from app.api.deps import DbSession, DeviceAuth
from app.models.session import GuestSession
from app.schemas.session import (
    SessionCompleteRequest,
    SessionCompleteResponse,
    SessionStartRequest,
    SessionStartResponse,
)
from app.services.session_service import SessionService

router = APIRouter(prefix="/sessions", tags=["sessions"])
session_service = SessionService()


@router.post("/start", response_model=SessionStartResponse)
def start_session(
    body: SessionStartRequest, db: DbSession, device: DeviceAuth
) -> SessionStartResponse:
    try:
        session, event, booth = session_service.start_session(
            db, device, body.trigger_type, body.local_reference
        )
    except ValueError as exc:
        code = str(exc)
        if code == "DEVICE_NOT_ASSIGNED":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=code)
        if code == "EVENT_NOT_ACTIVE":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=code)
        raise

    return SessionStartResponse(
        session_id=session.id,
        event_id=event.id,
        booth_id=booth.id,
        max_record_seconds=event.max_record_seconds,
        started_at=session.started_at,
        status=session.status,
    )


@router.post("/{session_id}/complete", response_model=SessionCompleteResponse)
def complete_session(
    session_id: str,
    body: SessionCompleteRequest,
    db: DbSession,
    device: DeviceAuth,
) -> SessionCompleteResponse:
    session = (
        db.query(GuestSession)
        .filter(GuestSession.id == session_id, GuestSession.device_id == device.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SESSION_NOT_FOUND")

    session = session_service.complete_session(db, session, body.duration_seconds)
    return SessionCompleteResponse(
        session_id=session.id,
        status=session.status,
        upload_status=session.upload_status,
    )

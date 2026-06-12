import hashlib
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.api.deps import DbSession, DeviceAuth
from app.core.config import get_settings
from app.models.audio_message import AudioMessage
from app.models.session import GuestSession
from app.models.transcript import Transcript
from app.schemas.upload import AudioUploadResponse
from app.services.audio_storage import get_storage
from app.workers.jobs import enqueue_processing
from app.workers.scheduler import schedule_processing

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/audio", response_model=AudioUploadResponse)
async def upload_audio(
    db: DbSession,
    device: DeviceAuth,
    session_id: UUID = Form(...),
    checksum: str = Form(...),
    file: UploadFile = File(...),
) -> AudioUploadResponse:
    settings = get_settings()
    session = (
        db.query(GuestSession)
        .filter(GuestSession.id == session_id, GuestSession.device_id == device.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SESSION_NOT_FOUND")

    data = await file.read()
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="UPLOAD_TOO_LARGE")

    computed = hashlib.sha256(data).hexdigest()
    if computed != checksum.lower():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="UPLOAD_CHECKSUM_MISMATCH")

    existing = db.query(AudioMessage).filter(AudioMessage.session_id == session_id).first()
    if existing:
        if existing.checksum == checksum:
            return AudioUploadResponse(
                message_id=existing.id,
                session_id=session_id,
                checksum=existing.checksum,
                file_size_bytes=existing.file_size_bytes or 0,
                duplicate=True,
                processing_queued=False,
            )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="SESSION_ALREADY_HAS_AUDIO")

    storage = get_storage()
    path, size = storage.save_bytes(session.event_id, session_id, data)

    message = AudioMessage(
        session_id=session_id,
        raw_audio_path=path,
        file_size_bytes=size,
        checksum=checksum,
        mime_type=file.content_type or "audio/wav",
    )
    db.add(message)
    db.flush()
    db.add(Transcript(audio_message_id=message.id, moderation_label="pending"))
    session.upload_status = "synced"
    session.status = "completed"
    db.commit()
    db.refresh(message)

    job = enqueue_processing(db, message.id)
    if settings.ai_pipeline_enabled:
        schedule_processing(message.id, job_id=job.id)

    return AudioUploadResponse(
        message_id=message.id,
        session_id=session_id,
        checksum=checksum,
        file_size_bytes=size,
        processing_queued=True,
    )


@router.post("/snapshot")
async def upload_snapshot(
    db: DbSession,
    device: DeviceAuth,
    session_id: UUID = Form(...),
    file: UploadFile = File(...),
) -> dict:
    settings = get_settings()
    session = (
        db.query(GuestSession)
        .filter(GuestSession.id == session_id, GuestSession.device_id == device.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SESSION_NOT_FOUND")

    message = db.query(AudioMessage).filter(AudioMessage.session_id == session_id).first()
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AUDIO_NOT_UPLOADED")

    data = await file.read()
    if len(data) > settings.max_snapshot_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="SNAPSHOT_TOO_LARGE")

    storage = get_storage()
    path = storage.save_snapshot(session.event_id, session_id, data)
    message.snapshot_path = path
    db.commit()
    return {"ok": True, "session_id": str(session_id)}

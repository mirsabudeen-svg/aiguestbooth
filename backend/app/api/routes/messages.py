from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, Response
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from app.api.deps import DbSession, OperatorAuth, get_current_user
from app.models.audio_message import AudioMessage
from app.models.booth import Booth
from app.models.processing_job import ProcessingJob
from app.models.session import GuestSession
from app.models.transcript import Transcript
from app.models.user import User
from app.schemas.common import PaginatedMeta
from app.schemas.message import (
    MessageDetail,
    MessageListItem,
    MessageListResponse,
    MessageUpdate,
    ProcessingJobSummary,
    TranscriptSummary,
)
from app.core.config import get_settings
from app.services.audio_storage import get_storage
from app.services.audit_service import get_audit_service
from app.workers.jobs import get_processing_status

router = APIRouter(prefix="/messages", tags=["messages"])


def _latest_job(db: DbSession, audio_message_id: UUID) -> ProcessingJob | None:
    return (
        db.query(ProcessingJob)
        .filter(ProcessingJob.audio_message_id == audio_message_id)
        .order_by(ProcessingJob.created_at.desc())
        .first()
    )


def _build_list_item(
    db: DbSession, msg: AudioMessage, session: GuestSession | None, booth: Booth | None
) -> MessageListItem:
    transcript = msg.transcript
    preview = None
    if transcript:
        preview = transcript.cleaned_text or transcript.transcript_text
        if preview and len(preview) > 160:
            preview = preview[:160] + "..."

    return MessageListItem(
        id=msg.id,
        session_id=msg.session_id,
        event_id=session.event_id if session else UUID(int=0),
        booth_name=booth.name if booth else None,
        duration_seconds=msg.duration_seconds,
        created_at=msg.created_at,
        upload_status=session.upload_status if session else "unknown",
        processing_status=get_processing_status(db, msg.id),
        summary_text=transcript.summary_text if transcript else None,
        sentiment_label=transcript.sentiment_label if transcript else None,
        moderation_label=transcript.moderation_label if transcript else None,
        transcript_preview=preview,
        tags=[t.tag for t in msg.tags],
        starred=msg.starred,
        has_snapshot=bool(msg.snapshot_path),
    )


@router.get("", response_model=MessageListResponse)
def list_messages(
    db: DbSession,
    _: OperatorAuth,
    event_id: UUID | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> MessageListResponse:
    base = db.query(AudioMessage).join(GuestSession, AudioMessage.session_id == GuestSession.id)
    if event_id:
        base = base.filter(GuestSession.event_id == event_id)
    if q:
        base = base.outerjoin(Transcript).filter(
            or_(
                Transcript.cleaned_text.ilike(f"%{q}%"),
                Transcript.transcript_text.ilike(f"%{q}%"),
                Transcript.summary_text.ilike(f"%{q}%"),
            )
        )

    total = base.with_entities(func.count(AudioMessage.id.distinct())).scalar() or 0
    query = base.options(
        joinedload(AudioMessage.transcript),
        joinedload(AudioMessage.tags),
    ).order_by(AudioMessage.created_at.desc())
    offset = (page - 1) * page_size
    messages = query.offset(offset).limit(page_size).all()

    items: list[MessageListItem] = []
    for msg in messages:
        session = db.query(GuestSession).filter(GuestSession.id == msg.session_id).first()
        booth = db.query(Booth).filter(Booth.id == session.booth_id).first() if session else None
        items.append(_build_list_item(db, msg, session, booth))

    return MessageListResponse(
        items=items,
        meta=PaginatedMeta(page=page, page_size=page_size, total=total),
    )


@router.get("/audio/{event_id}/{session_id}.wav")
def stream_audio(
    event_id: UUID,
    session_id: UUID,
    db: DbSession,
    user: User = Depends(get_current_user),
) -> FileResponse | Response:
    msg = (
        db.query(AudioMessage)
        .join(GuestSession, AudioMessage.session_id == GuestSession.id)
        .filter(AudioMessage.session_id == session_id, GuestSession.event_id == event_id)
        .first()
    )
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio not found")

    audit = get_audit_service()
    audit.log_user_action(
        db,
        user.id,
        action="playback",
        resource_type="audio_message",
        resource_id=str(msg.id),
        details={"event_id": str(event_id), "session_id": str(session_id)},
    )

    storage = get_storage()
    settings = get_settings()
    if settings.storage_backend == "local":
        path = storage.resolve_local_path(msg.raw_audio_path)
        if not path:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file missing")
        return FileResponse(path, media_type="audio/wav", filename=f"{session_id}.wav")

    data = storage.read_bytes(msg.raw_audio_path)
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file missing")
    return Response(content=data, media_type="audio/wav")


@router.get("/{message_id}", response_model=MessageDetail)
def get_message(message_id: UUID, db: DbSession, _: OperatorAuth) -> MessageDetail:
    msg = (
        db.query(AudioMessage)
        .options(joinedload(AudioMessage.transcript), joinedload(AudioMessage.tags))
        .filter(AudioMessage.id == message_id)
        .first()
    )
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    session = db.query(GuestSession).filter(GuestSession.id == msg.session_id).first()
    job = _latest_job(db, msg.id)
    storage = get_storage()
    snapshot_url = None
    if msg.snapshot_path:
        snapshot_url = f"/api/v1/messages/snapshot/{session.event_id}/{msg.session_id}.jpg"
    return MessageDetail(
        id=msg.id,
        session_id=msg.session_id,
        event_id=session.event_id,
        booth_id=session.booth_id,
        duration_seconds=msg.duration_seconds,
        file_size_bytes=msg.file_size_bytes,
        checksum=msg.checksum,
        audio_url=storage.get_public_url(session.event_id, msg.session_id),
        created_at=msg.created_at,
        processing_status=get_processing_status(db, msg.id),
        processing_job=ProcessingJobSummary.model_validate(job) if job else None,
        transcript=TranscriptSummary.model_validate(msg.transcript) if msg.transcript else None,
        tags=[t.tag for t in msg.tags],
        starred=msg.starred,
        snapshot_url=snapshot_url,
    )


@router.get("/snapshot/{event_id}/{session_id}.jpg")
def stream_snapshot(
    event_id: UUID,
    session_id: UUID,
    db: DbSession,
    user: User = Depends(get_current_user),
) -> Response:
    _ = user
    msg = (
        db.query(AudioMessage)
        .join(GuestSession, AudioMessage.session_id == GuestSession.id)
        .filter(AudioMessage.session_id == session_id, GuestSession.event_id == event_id)
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


@router.patch("/{message_id}", response_model=MessageDetail)
def update_message(
    message_id: UUID, body: MessageUpdate, db: DbSession, _: OperatorAuth
) -> MessageDetail:
    msg = (
        db.query(AudioMessage)
        .options(joinedload(AudioMessage.transcript), joinedload(AudioMessage.tags))
        .filter(AudioMessage.id == message_id)
        .first()
    )
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    if body.starred is not None:
        msg.starred = body.starred
    db.commit()
    db.refresh(msg)
    return get_message(message_id, db, _)

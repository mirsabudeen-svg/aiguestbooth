from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter

from app.api.deps import DbSession, OperatorAuth
from app.models.audio_message import AudioMessage
from app.models.booth import Booth
from app.models.device import Device
from app.models.event import Event
from app.models.processing_job import ProcessingJob
from app.models.session import GuestSession
from app.schemas.dashboard import BoothStatusItem, DashboardOverview, DeviceAlertItem

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=DashboardOverview)
def dashboard_overview(
    db: DbSession, _: OperatorAuth, event_id: UUID | None = None
) -> DashboardOverview:
    event: Event | None = None
    if event_id:
        event = db.query(Event).filter(Event.id == event_id).first()
    else:
        event = db.query(Event).filter(Event.is_active.is_(True)).order_by(Event.created_at.desc()).first()

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    msg_base = db.query(AudioMessage).join(GuestSession, AudioMessage.session_id == GuestSession.id)
    session_base = db.query(GuestSession)
    if event:
        msg_base = msg_base.filter(GuestSession.event_id == event.id)
        session_base = session_base.filter(GuestSession.event_id == event.id)

    total_messages = msg_base.count()
    messages_today = msg_base.filter(AudioMessage.created_at >= today_start).count()
    pending_uploads = session_base.filter(GuestSession.upload_status.in_(["pending", "retrying"])).count()
    failed_uploads = session_base.filter(GuestSession.upload_status == "failed").count()
    processing_queue = db.query(ProcessingJob).filter(ProcessingJob.status == "queued").count()

    booths: list[BoothStatusItem] = []
    booth_query = db.query(Booth)
    if event:
        booth_query = booth_query.filter(Booth.event_id == event.id)

    for booth in booth_query.all():
        device = (
            db.query(Device).filter(Device.id == booth.assigned_device_id).first()
            if booth.assigned_device_id
            else None
        )
        booth_messages = (
            db.query(AudioMessage)
            .join(GuestSession)
            .filter(GuestSession.booth_id == booth.id, AudioMessage.created_at >= today_start)
            .count()
        )
        booth_pending = (
            db.query(GuestSession)
            .filter(GuestSession.booth_id == booth.id, GuestSession.upload_status == "pending")
            .count()
        )
        booths.append(
            BoothStatusItem(
                booth_id=booth.id,
                booth_name=booth.name,
                status=booth.status,
                device_state=device.current_state if device else None,
                last_seen_at=device.last_seen_at if device else None,
                messages_today=booth_messages,
                pending_uploads=booth_pending,
            )
        )

    device_alerts: list[DeviceAlertItem] = []
    alert_query = db.query(Device).filter(
        Device.status == "error",
        Device.last_error_at.isnot(None),
    )
    for device in alert_query.order_by(Device.last_error_at.desc()).limit(20).all():
        booth = db.query(Booth).filter(Booth.assigned_device_id == device.id).first()
        if event and booth and booth.event_id != event.id:
            continue
        if event and not booth:
            continue
        device_alerts.append(
            DeviceAlertItem(
                device_id=device.id,
                serial_number=device.serial_number,
                booth_name=booth.name if booth else None,
                error_code=device.last_error_code,
                error_message=device.last_error_message,
                error_at=device.last_error_at,
                status=device.status,
            )
        )

    return DashboardOverview(
        event_id=event.id if event else None,
        event_name=event.name if event else None,
        total_messages=total_messages,
        messages_today=messages_today,
        pending_uploads=pending_uploads,
        failed_uploads=failed_uploads,
        processing_queue=processing_queue,
        booths=booths,
        device_alerts=device_alerts,
    )

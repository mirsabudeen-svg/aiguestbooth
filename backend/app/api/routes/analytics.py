from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func

from app.api.deps import DbSession, OperatorAuth
from app.models.audio_message import AudioMessage
from app.models.booth import Booth
from app.models.event import Event
from app.models.message_tag import MessageTag
from app.models.session import GuestSession
from app.schemas.analytics import AnalyticsOverview, BoothBucket, HourlyBucket, TagBucket

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverview)
def analytics_overview(db: DbSession, _: OperatorAuth, event_id: UUID) -> AnalyticsOverview:
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    base = (
        db.query(AudioMessage)
        .join(GuestSession, AudioMessage.session_id == GuestSession.id)
        .filter(GuestSession.event_id == event_id)
    )
    total = base.count()
    starred = base.filter(AudioMessage.starred.is_(True)).count()
    with_snapshot = base.filter(AudioMessage.snapshot_path.isnot(None)).count()

    hour_rows = (
        db.query(func.extract("hour", AudioMessage.created_at).label("hour"), func.count(AudioMessage.id))
        .join(GuestSession, AudioMessage.session_id == GuestSession.id)
        .filter(GuestSession.event_id == event_id)
        .group_by("hour")
        .order_by("hour")
        .all()
    )
    by_hour = [HourlyBucket(hour=int(row.hour), count=row[1]) for row in hour_rows]

    booth_rows = (
        db.query(Booth.id, Booth.name, func.count(AudioMessage.id))
        .join(GuestSession, GuestSession.booth_id == Booth.id)
        .join(AudioMessage, AudioMessage.session_id == GuestSession.id)
        .filter(Booth.event_id == event_id)
        .group_by(Booth.id, Booth.name)
        .order_by(func.count(AudioMessage.id).desc())
        .all()
    )
    by_booth = [
        BoothBucket(booth_id=str(row[0]), booth_name=row[1], count=row[2]) for row in booth_rows
    ]

    tag_rows = (
        db.query(MessageTag.tag, func.count(MessageTag.id))
        .join(AudioMessage, MessageTag.audio_message_id == AudioMessage.id)
        .join(GuestSession, AudioMessage.session_id == GuestSession.id)
        .filter(GuestSession.event_id == event_id)
        .group_by(MessageTag.tag)
        .order_by(func.count(MessageTag.id).desc())
        .limit(15)
        .all()
    )
    top_tags = [TagBucket(tag=row[0], count=row[1]) for row in tag_rows]

    return AnalyticsOverview(
        event_id=str(event.id),
        event_name=event.name,
        total_messages=total,
        starred_count=starred,
        with_snapshot_count=with_snapshot,
        by_hour=by_hour,
        by_booth=by_booth,
        top_tags=top_tags,
    )

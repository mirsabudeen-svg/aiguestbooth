from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import AdminAuth, DbSession, OperatorAuth
from app.models.booth import Booth
from app.models.device import Device
from app.schemas.booth import BoothAssignDevice, BoothCreate, BoothResponse

router = APIRouter(prefix="/booths", tags=["booths"])


@router.get("", response_model=list[BoothResponse])
def list_booths(db: DbSession, _: OperatorAuth, event_id: UUID | None = None) -> list[BoothResponse]:
    q = db.query(Booth)
    if event_id:
        q = q.filter(Booth.event_id == event_id)
    return q.order_by(Booth.created_at.desc()).all()


@router.post("", response_model=BoothResponse, status_code=status.HTTP_201_CREATED)
def create_booth(body: BoothCreate, db: DbSession, _: AdminAuth) -> BoothResponse:
    booth = Booth(**body.model_dump())
    db.add(booth)
    db.commit()
    db.refresh(booth)
    return booth


@router.patch("/{booth_id}/assign-device", response_model=BoothResponse)
def assign_device(
    booth_id: UUID, body: BoothAssignDevice, db: DbSession, _: AdminAuth
) -> BoothResponse:
    booth = db.query(Booth).filter(Booth.id == booth_id).first()
    if not booth:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booth not found")
    if body.device_id is None:
        booth.assigned_device_id = None
        db.commit()
        db.refresh(booth)
        return booth

    device = db.query(Device).filter(Device.id == body.device_id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    existing = db.query(Booth).filter(Booth.assigned_device_id == body.device_id).first()
    if existing and existing.id != booth_id:
        existing.assigned_device_id = None

    booth.assigned_device_id = body.device_id
    db.commit()
    db.refresh(booth)
    return booth

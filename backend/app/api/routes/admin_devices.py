from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter

from app.api.deps import DbSession, OperatorAuth
from app.models.booth import Booth
from app.models.device import Device
from app.schemas.device import DeviceListItem

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("", response_model=list[DeviceListItem])
def list_devices(db: DbSession, _: OperatorAuth) -> list[DeviceListItem]:
    devices = db.query(Device).order_by(Device.serial_number).all()
    items: list[DeviceListItem] = []
    for device in devices:
        booth = db.query(Booth).filter(Booth.assigned_device_id == device.id).first()
        items.append(
            DeviceListItem(
                id=device.id,
                serial_number=device.serial_number,
                display_name=device.display_name,
                status=device.status,
                current_state=device.current_state,
                firmware_version=device.firmware_version,
                last_seen_at=device.last_seen_at,
                last_error_code=device.last_error_code,
                last_error_message=device.last_error_message,
                last_error_at=device.last_error_at,
                assigned_booth_id=booth.id if booth else None,
                assigned_booth_name=booth.name if booth else None,
                assigned_event_id=booth.event_id if booth else None,
            )
        )
    return items

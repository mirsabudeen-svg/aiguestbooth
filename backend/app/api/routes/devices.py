from datetime import datetime, timezone

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import Response

from app.api.deps import AdminAuth, DbSession, DeviceAuth
from app.core.security import generate_device_token, hash_device_token
from app.models.device import Device
from app.schemas.device import (
    DeviceConfigResponse,
    DeviceErrorRequest,
    DeviceHeartbeatRequest,
    DeviceHeartbeatResponse,
    DeviceRegisterRequest,
    DeviceRegisterResponse,
)
from app.core.config import get_settings
from app.services.audit_service import get_audit_service
from app.services.firmware_storage import get_firmware_storage
from app.services.session_service import SessionService
from pydantic import BaseModel

router = APIRouter(prefix="/device", tags=["device"])
session_service = SessionService()


@router.post("/register", response_model=DeviceRegisterResponse)
def register_device(body: DeviceRegisterRequest, db: DbSession) -> DeviceRegisterResponse:
    existing = db.query(Device).filter(Device.serial_number == body.serial_number).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Device already registered. Re-provision required.",
        )

    token = generate_device_token()
    device = Device(
        serial_number=body.serial_number,
        display_name=body.display_name or body.serial_number,
        firmware_version=body.firmware_version,
        auth_token_hash=hash_device_token(token),
        status="registered",
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return DeviceRegisterResponse(device_id=device.id, token=token)


@router.post("/heartbeat", response_model=DeviceHeartbeatResponse)
def device_heartbeat(
    body: DeviceHeartbeatRequest, db: DbSession, device: DeviceAuth
) -> DeviceHeartbeatResponse:
    device.last_seen_at = datetime.now(timezone.utc)
    device.wifi_strength = body.wifi_strength
    device.battery_level = body.battery_level
    device.current_state = body.state
    if body.firmware_version:
        device.firmware_version = body.firmware_version
    db.commit()
    return DeviceHeartbeatResponse(server_time=datetime.now(timezone.utc))


@router.get("/config", response_model=DeviceConfigResponse)
def get_device_config(device: DeviceAuth, db: DbSession) -> DeviceConfigResponse:
    return session_service.get_device_config(db, device)


@router.post("/errors")
def report_device_error(body: DeviceErrorRequest, device: DeviceAuth, db: DbSession) -> dict:
    device.status = "error"
    device.current_state = "error"
    device.last_error_code = body.code
    device.last_error_message = body.message
    device.last_error_at = datetime.now(timezone.utc)
    db.commit()

    audit = get_audit_service()
    audit.log_device_action(
        db,
        device.id,
        action="device_error",
        resource_type="device",
        resource_id=str(device.id),
        details={
            "code": body.code,
            "message": body.message,
            "session_id": str(body.session_id) if body.session_id else None,
        },
    )
    return {"ok": True, "received": body.code}


class FirmwareInfoResponse(BaseModel):
    latest_version: str
    download_url: str | None
    update_available: bool


@router.get("/firmware", response_model=FirmwareInfoResponse)
def get_firmware_info(device: DeviceAuth) -> FirmwareInfoResponse:
    settings = get_settings()
    storage = get_firmware_storage()
    current = device.firmware_version or "0.0.0"
    latest = settings.firmware_latest_version
    download_url = settings.firmware_download_url or None
    if not download_url and storage.exists():
        download_url = storage.public_download_url()
    update_available = _version_less_than(current, latest) and bool(download_url)
    return FirmwareInfoResponse(
        latest_version=latest,
        download_url=download_url if update_available else None,
        update_available=update_available,
    )


@router.get("/firmware/download")
def download_firmware(device: DeviceAuth) -> Response:
    _ = device
    storage = get_firmware_storage()
    data = storage.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Firmware not published")
    return Response(content=data, media_type="application/octet-stream")


@router.post("/firmware/publish")
async def publish_firmware(_: AdminAuth, file: UploadFile = File(...)) -> dict:
    data = await file.read()
    if len(data) < 1024:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Firmware file too small")
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Firmware too large")
    storage = get_firmware_storage()
    storage.save(data)
    return {"ok": True, "download_url": storage.public_download_url(), "bytes": len(data)}


def _version_less_than(current: str, latest: str) -> bool:
    def parse(v: str) -> tuple[int, ...]:
        parts = []
        for piece in v.split("."):
            try:
                parts.append(int(piece))
            except ValueError:
                parts.append(0)
        return tuple(parts)

    return parse(current) < parse(latest)

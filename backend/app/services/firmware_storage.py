from pathlib import Path

from app.core.config import get_settings


class FirmwareStorage:
    def __init__(self) -> None:
        settings = get_settings()
        self.root = Path(settings.storage_path).resolve() / "firmware"
        self.root.mkdir(parents=True, exist_ok=True)
        self.binary_path = self.root / "latest.bin"

    def save(self, data: bytes) -> str:
        self.binary_path.write_bytes(data)
        return str(self.binary_path)

    def read(self) -> bytes | None:
        if not self.binary_path.exists():
            return None
        return self.binary_path.read_bytes()

    def exists(self) -> bool:
        return self.binary_path.exists()

    def public_download_url(self) -> str:
        settings = get_settings()
        base = settings.public_api_url.rstrip("/")
        return f"{base}/api/v1/device/firmware/download"


def get_firmware_storage() -> FirmwareStorage:
    return FirmwareStorage()

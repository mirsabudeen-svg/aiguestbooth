import io
from pathlib import Path
from uuid import UUID

from app.core.config import get_settings


class AudioStorageService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._s3 = None
        if self.settings.storage_backend == "local":
            self.base_path = Path(self.settings.storage_path).resolve()
            self.base_path.mkdir(parents=True, exist_ok=True)
        elif self.settings.storage_backend == "s3":
            import boto3

            kwargs: dict = {"region_name": self.settings.s3_region}
            if self.settings.s3_endpoint:
                kwargs["endpoint_url"] = self.settings.s3_endpoint
            if self.settings.s3_access_key:
                kwargs["aws_access_key_id"] = self.settings.s3_access_key
            if self.settings.s3_secret_key:
                kwargs["aws_secret_access_key"] = self.settings.s3_secret_key
            self._s3 = boto3.client("s3", **kwargs)
            if not self.settings.s3_bucket:
                raise ValueError("S3_BUCKET is required when storage_backend=s3")

    def _audio_relative(self, event_id: UUID, session_id: UUID) -> str:
        return f"events/{event_id}/audio/{session_id}.wav"

    def _asset_relative(self, event_id: UUID, asset_type: str) -> str:
        return f"events/{event_id}/assets/{asset_type}.wav"

    def _snapshot_relative(self, event_id: UUID, session_id: UUID) -> str:
        return f"events/{event_id}/snapshots/{session_id}.jpg"

    def audio_path(self, event_id: UUID, session_id: UUID) -> str:
        relative = self._audio_relative(event_id, session_id)
        if self.settings.storage_backend == "local":
            full = self.base_path / relative
            full.parent.mkdir(parents=True, exist_ok=True)
            return str(full)
        return relative

    def save_bytes(self, event_id: UUID, session_id: UUID, data: bytes) -> tuple[str, int]:
        path = self.audio_path(event_id, session_id)
        if self.settings.storage_backend == "local":
            with open(path, "wb") as f:
                f.write(data)
            return path, len(data)
        self._s3_put(path, data, "audio/wav")
        return path, len(data)

    def save_event_asset(self, event_id: UUID, asset_type: str, data: bytes) -> str:
        path = self._asset_relative(event_id, asset_type)
        if self.settings.storage_backend == "local":
            full = self.base_path / path
            full.parent.mkdir(parents=True, exist_ok=True)
            with open(full, "wb") as f:
                f.write(data)
            return str(full)
        self._s3_put(path, data, "audio/wav")
        return path

    def save_snapshot(self, event_id: UUID, session_id: UUID, data: bytes) -> str:
        path = self._snapshot_relative(event_id, session_id)
        if self.settings.storage_backend == "local":
            full = self.base_path / path
            full.parent.mkdir(parents=True, exist_ok=True)
            with open(full, "wb") as f:
                f.write(data)
            return str(full)
        self._s3_put(path, data, "image/jpeg")
        return path

    def read_bytes(self, stored_path: str) -> bytes | None:
        if self.settings.storage_backend == "local":
            path = self.resolve_local_path(stored_path)
            if not path:
                return None
            return path.read_bytes()
        try:
            obj = self._s3.get_object(Bucket=self.settings.s3_bucket, Key=stored_path)
            return obj["Body"].read()
        except Exception:
            return None

    def delete_file(self, stored_path: str) -> bool:
        if self.settings.storage_backend == "local":
            path = self.resolve_local_path(stored_path)
            if path and path.exists():
                path.unlink()
                return True
            return False
        try:
            self._s3.delete_object(Bucket=self.settings.s3_bucket, Key=stored_path)
            return True
        except Exception:
            return False

    def _s3_put(self, key: str, data: bytes, content_type: str) -> None:
        self._s3.upload_fileobj(
            io.BytesIO(data),
            self.settings.s3_bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )

    def get_public_url(self, event_id: UUID, session_id: UUID) -> str:
        return f"/api/v1/messages/audio/{event_id}/{session_id}.wav"

    def get_asset_public_url(self, event_id: UUID, asset_type: str) -> str:
        base = self.settings.public_api_url.rstrip("/")
        return f"{base}/api/v1/events/{event_id}/assets/{asset_type}.wav"

    def resolve_local_path(self, stored_path: str) -> Path | None:
        if self.settings.storage_backend != "local":
            return None
        path = Path(stored_path)
        if path.is_absolute() and path.exists():
            return path
        alt = self.base_path / stored_path
        if alt.exists():
            return alt
        if path.exists():
            return path
        return None


def get_storage() -> AudioStorageService:
    return AudioStorageService()

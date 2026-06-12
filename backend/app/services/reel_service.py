import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.audio_message import AudioMessage
from app.models.event import Event
from app.models.export_job import ExportJob
from app.models.session import GuestSession
from app.services.audio_storage import AudioStorageService


class ReelService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.storage = AudioStorageService()
        self.exports_dir = Path(self.settings.storage_path).resolve() / "exports"
        self.exports_dir.mkdir(parents=True, exist_ok=True)

    def run_job(self, db: Session, job_id: UUID) -> ExportJob:
        job = db.query(ExportJob).filter(ExportJob.id == job_id).first()
        if not job:
            raise ValueError("Export job not found")

        event = db.query(Event).filter(Event.id == job.event_id).first()
        if not event:
            job.status = "failed"
            job.error_message = "Event not found"
            db.commit()
            return job

        message_ids: list[UUID] | None = None
        if job.options_json:
            raw_ids = job.options_json.get("message_ids") or []
            message_ids = [UUID(x) for x in raw_ids] if raw_ids else None

        query = (
            db.query(AudioMessage)
            .join(GuestSession, AudioMessage.session_id == GuestSession.id)
            .filter(GuestSession.event_id == job.event_id)
            .order_by(AudioMessage.created_at.asc())
        )
        if message_ids:
            query = query.filter(AudioMessage.id.in_(message_ids))
        else:
            query = query.filter(AudioMessage.starred.is_(True))

        messages = query.all()
        if not messages:
            job.status = "failed"
            job.error_message = "No messages selected for reel (star messages or pass message_ids)"
            db.commit()
            return job

        job.status = "running"
        db.commit()

        output_path = self.exports_dir / f"{job.id}-reel.mp3"
        try:
            wav_paths = self._resolve_wav_paths(messages)
            if not wav_paths:
                raise RuntimeError("No audio files found on disk")

            self._concat_with_ffmpeg(wav_paths, output_path)
            job.status = "completed"
            job.output_path = str(output_path)
            job.completed_at = datetime.now(timezone.utc)
            job.error_message = None
        except Exception as exc:
            job.status = "failed"
            job.error_message = str(exc)
            if output_path.exists():
                output_path.unlink(missing_ok=True)

        db.commit()
        db.refresh(job)
        return job

    def _resolve_wav_paths(self, messages: list[AudioMessage]) -> list[Path]:
        paths: list[Path] = []
        for msg in messages:
            if self.storage.settings.storage_backend == "local":
                path = self.storage.resolve_local_path(msg.raw_audio_path)
                if path:
                    paths.append(path)
            else:
                data = self.storage.read_bytes(msg.raw_audio_path)
                if data:
                    tmp = Path(tempfile.gettempdir()) / f"reel-{msg.session_id}.wav"
                    tmp.write_bytes(data)
                    paths.append(tmp)
        return paths

    def _concat_with_ffmpeg(self, wav_paths: list[Path], output_path: Path) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as manifest:
            for path in wav_paths:
                escaped = str(path).replace("'", "'\\''")
                manifest.write(f"file '{escaped}'\n")
            manifest_path = manifest.name

        try:
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    manifest_path,
                    "-c:a",
                    "libmp3lame",
                    "-q:a",
                    "4",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
                timeout=600,
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or "ffmpeg failed")
        finally:
            Path(manifest_path).unlink(missing_ok=True)


def get_reel_service() -> ReelService:
    return ReelService()

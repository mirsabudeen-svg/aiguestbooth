import csv
import io
import json
import zipfile
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


class ExportService:
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

        job.status = "running"
        db.commit()

        messages = (
            db.query(AudioMessage)
            .join(GuestSession, AudioMessage.session_id == GuestSession.id)
            .filter(GuestSession.event_id == job.event_id)
            .order_by(AudioMessage.created_at.asc())
            .all()
        )

        zip_path = self.exports_dir / f"{job.id}.zip"
        manifest: list[dict] = []

        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for msg in messages:
                    path = self.storage.resolve_local_path(msg.raw_audio_path)
                    if not path or not path.exists():
                        continue
                    arcname = f"audio/{msg.session_id}.wav"
                    zf.write(path, arcname=arcname)
                    manifest.append(
                        {
                            "session_id": str(msg.session_id),
                            "message_id": str(msg.id),
                            "filename": arcname,
                            "duration_seconds": msg.duration_seconds,
                            "created_at": msg.created_at.isoformat() if msg.created_at else None,
                            "checksum": msg.checksum,
                        }
                    )

                zf.writestr(
                    "manifest.json",
                    json.dumps(
                        {
                            "event_id": str(event.id),
                            "event_name": event.name,
                            "exported_at": datetime.now(timezone.utc).isoformat(),
                            "message_count": len(manifest),
                            "messages": manifest,
                        },
                        indent=2,
                    ),
                )

                if job.format == "csv":
                    buffer = io.StringIO()
                    writer = csv.DictWriter(
                        buffer,
                        fieldnames=["session_id", "message_id", "filename", "duration_seconds", "created_at", "checksum"],
                    )
                    writer.writeheader()
                    writer.writerows(manifest)
                    zf.writestr("manifest.csv", buffer.getvalue())

            job.status = "completed"
            job.output_path = str(zip_path)
            job.completed_at = datetime.now(timezone.utc)
            job.error_message = None
        except Exception as exc:
            job.status = "failed"
            job.error_message = str(exc)
            if zip_path.exists():
                zip_path.unlink(missing_ok=True)

        db.commit()
        db.refresh(job)
        return job


def get_export_service() -> ExportService:
    return ExportService()

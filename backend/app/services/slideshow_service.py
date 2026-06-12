import html
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


class SlideshowService:
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
            job.error_message = "No starred messages for slideshow"
            db.commit()
            return job

        job.status = "running"
        db.commit()

        zip_path = self.exports_dir / f"{job.id}-slideshow.zip"
        slides: list[dict] = []

        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for idx, msg in enumerate(messages):
                    audio_name = f"assets/{idx:03d}.wav"
                    snapshot_name = f"assets/{idx:03d}.jpg"
                    audio_bytes = self._read_audio(msg)
                    if not audio_bytes:
                        continue
                    zf.writestr(audio_name, audio_bytes)

                    has_image = False
                    if msg.snapshot_path:
                        snap = self.storage.read_bytes(msg.snapshot_path)
                        if not snap and self.storage.settings.storage_backend == "local":
                            path = self.storage.resolve_local_path(msg.snapshot_path)
                            snap = path.read_bytes() if path else None
                        if snap:
                            zf.writestr(snapshot_name, snap)
                            has_image = True

                    transcript = msg.transcript
                    caption = ""
                    if transcript:
                        caption = transcript.summary_text or transcript.cleaned_text or transcript.transcript_text or ""

                    slides.append(
                        {
                            "audio": audio_name,
                            "image": snapshot_name if has_image else None,
                            "caption": caption,
                            "created_at": msg.created_at.isoformat() if msg.created_at else None,
                        }
                    )

                if not slides:
                    raise RuntimeError("No audio files found for slideshow")

                page_html = self._build_html(event.name, slides)
                zf.writestr("index.html", page_html)
                zf.writestr("manifest.json", json.dumps(slides, indent=2))

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

    def _read_audio(self, msg: AudioMessage) -> bytes | None:
        if self.storage.settings.storage_backend == "local":
            path = self.storage.resolve_local_path(msg.raw_audio_path)
            return path.read_bytes() if path else None
        return self.storage.read_bytes(msg.raw_audio_path)

    def _build_html(self, event_name: str, slides: list[dict]) -> str:
        safe_title = html.escape(event_name)
        slides_json = json.dumps(slides)
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{safe_title} — Memory Slideshow</title>
  <style>
    body {{ margin: 0; font-family: Georgia, serif; background: #0f0f18; color: #f5f0e8; }}
    .slide {{ min-height: 100vh; display: none; flex-direction: column; align-items: center; justify-content: center; padding: 2rem; box-sizing: border-box; }}
    .slide.active {{ display: flex; }}
    img {{ max-width: min(90vw, 640px); max-height: 50vh; object-fit: cover; border-radius: 12px; }}
    p {{ max-width: 560px; text-align: center; line-height: 1.5; font-size: 1.15rem; }}
    nav {{ position: fixed; bottom: 1.5rem; left: 0; right: 0; display: flex; justify-content: center; gap: 1rem; }}
    button {{ background: #c9a962; border: none; padding: 0.65rem 1.25rem; border-radius: 8px; font-weight: 600; cursor: pointer; }}
  </style>
</head>
<body>
  <div id="root"></div>
  <nav>
    <button id="prev">Previous</button>
    <button id="play">Play</button>
    <button id="next">Next</button>
  </nav>
  <script>
    const slides = {slides_json};
    let index = 0;
    let audio = null;
    const root = document.getElementById('root');

    function render() {{
      const s = slides[index];
      root.innerHTML = `<section class="slide active">
        ${{s.image ? `<img src="${{s.image}}" alt="" />` : ''}}
        <p>${{s.caption ? s.caption.replace(/</g, '&lt;') : 'Voice message'}}</p>
        <small style="opacity:0.5">${{s.created_at || ''}}</small>
      </section>`;
    }}

    function playCurrent() {{
      if (audio) {{ audio.pause(); }}
      audio = new Audio(slides[index].audio);
      audio.play();
    }}

    document.getElementById('prev').onclick = () => {{ index = (index - 1 + slides.length) % slides.length; render(); }};
    document.getElementById('next').onclick = () => {{ index = (index + 1) % slides.length; render(); }};
    document.getElementById('play').onclick = playCurrent;
    render();
  </script>
</body>
</html>
"""


def get_slideshow_service() -> SlideshowService:
    return SlideshowService()

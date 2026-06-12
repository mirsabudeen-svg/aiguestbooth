from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.event import Event
from app.services.audio_storage import get_storage
from app.services.openai_client import get_openai_client


class TTSService:
    def generate_prompt(self, db: Session, event_id: UUID, text: str, asset_type: str = "prompt") -> str:
        if asset_type not in ("prompt", "thank_you"):
            raise ValueError("asset_type must be prompt or thank_you")

        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise ValueError("Event not found")

        client = get_openai_client()
        if not client.enabled:
            raise RuntimeError("OPENAI_API_KEY required for TTS")

        audio_bytes = client.text_to_speech(text)
        storage = get_storage()
        storage.save_event_asset(event_id, asset_type, audio_bytes)
        public_url = storage.get_asset_public_url(event_id, asset_type)

        if asset_type == "prompt":
            event.prompt_audio_url = public_url
        else:
            event.thank_you_audio_url = public_url
        db.commit()
        return public_url


def get_tts_service() -> TTSService:
    return TTSService()

from uuid import UUID

from pydantic import BaseModel


class AudioUploadResponse(BaseModel):
    message_id: UUID
    session_id: UUID
    checksum: str
    file_size_bytes: int
    duplicate: bool = False
    processing_queued: bool = True

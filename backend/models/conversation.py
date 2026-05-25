from datetime import datetime, timezone
from pydantic import BaseModel


class Message(BaseModel):
    role: str
    content: str


class Conversation(BaseModel):
    id: str | None = None
    user_id: str
    messages: list[Message]
    created_at: datetime = datetime.now(timezone.utc)


class AudioRequest(BaseModel):
    user_id: str
    audio_base64: str
    mime_type: str = "audio/wav"

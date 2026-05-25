from datetime import datetime, timezone
from pydantic import BaseModel


class Person(BaseModel):
    id: str | None = None
    user_id: str
    name: str
    photo_url: str | None = None
    face_embedding_id: str | None = None
    notes: str | None = None
    met_at: datetime = datetime.now(timezone.utc)
    last_seen: datetime | None = None
    contact_frequency_days: int | None = None


class FaceScanRequest(BaseModel):
    user_id: str
    image_base64: str
    context: str | None = None

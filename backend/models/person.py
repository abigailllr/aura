from datetime import datetime, timezone
from pydantic import BaseModel


class Person(BaseModel):
    id: str | None = None
    user_id: str
    name: str
    job: str | None = None
    company: str | None = None
    photo_url: str | None = None
    face_embedding_id: str | None = None
    notes: str | None = None
    met_at: datetime = datetime.now(timezone.utc)
    last_seen: datetime | None = None
    contact_frequency_days: int | None = None

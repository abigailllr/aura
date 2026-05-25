import logging
from datetime import datetime, timezone

import anthropic
from pydantic import BaseModel

from config import settings

logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)


class ContactAlert(BaseModel):
    name: str
    last_seen: str | None
    days_since_contact: int | None
    message: str


class RelationshipInsight(BaseModel):
    alerts: list[ContactAlert]
    summary: str
    tone_patterns: list[str]


def build_timeline(people: list[dict], conversations: list[dict]) -> list[dict]:
    timeline = []
    for person in people:
        last_seen = person.get("last_seen")
        days_since = None

        if last_seen:
            try:
                if isinstance(last_seen, str):
                    last_seen_dt = datetime.fromisoformat(last_seen)
                else:
                    last_seen_dt = last_seen
                days_since = (datetime.now(timezone.utc) - last_seen_dt).days
            except Exception:
                pass

        timeline.append({
            "name": person.get("name"),
            "last_seen": str(last_seen) if last_seen else None,
            "days_since_contact": days_since,
            "notes": person.get("notes"),
            "job": person.get("job"),
            "usual_frequency_days": person.get("contact_frequency_days"),
        })

    return timeline


def analyze(people: list[dict], conversations: list[dict]) -> RelationshipInsight:
    timeline = build_timeline(people, conversations)

    response = client.messages.parse(
        model="claude-opus-4-6",
        max_tokens=512,
        output_format=RelationshipInsight,
        messages=[{
            "role": "user",
            "content": (
                f"Analyze these relationships. Identify who needs attention, "
                f"how long since last contact, and emotional tone patterns. "
                f"Be direct and specific.\n\nData: {timeline}"
            ),
        }],
    )
    return response.parsed_output

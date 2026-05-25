import logging
from datetime import datetime, timezone
from pydantic import BaseModel

import anthropic
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from config import settings

logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def get_calendar_service(token: dict):
    creds = Credentials(
        token=token["access_token"],
        refresh_token=token.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=token.get("client_id"),
        client_secret=token.get("client_secret"),
        scopes=SCOPES,
    )
    return build("calendar", "v3", credentials=creds)


def fetch_events(service, max_results: int = 20) -> list[dict]:
    now = datetime.now(timezone.utc).isoformat()
    result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    return result.get("items", [])


class RescheduleAction(BaseModel):
    event_id: str
    event_title: str
    reason: str
    suggested_time: str


class ScheduleAnalysis(BaseModel):
    actions: list[RescheduleAction]
    summary: str


def analyze_and_suggest(events: list[dict], energy_profile: dict) -> ScheduleAnalysis:
    simplified_events = [
        {
            "id": e.get("id"),
            "title": e.get("summary"),
            "start": e.get("start", {}).get("dateTime"),
            "end": e.get("end", {}).get("dateTime"),
        }
        for e in events
    ]

    response = client.messages.parse(
        model="claude-opus-4-6",
        max_tokens=1024,
        thinking={"type": "adaptive"},
        output_format=ScheduleAnalysis,
        messages=[{
            "role": "user",
            "content": (
                f"Given this energy profile and upcoming calendar events, "
                f"suggest which events to reschedule and when, to align with peak energy windows. "
                f"Hard meetings and deep work should land in peak windows. "
                f"Administrative tasks in low windows.\n\n"
                f"Energy profile: {energy_profile}\n\n"
                f"Events: {simplified_events}"
            ),
        }],
    )
    return response.parsed_output


def reschedule_event(service, event_id: str, new_start: str, new_end: str):
    event = service.events().get(calendarId="primary", eventId=event_id).execute()
    event["start"]["dateTime"] = new_start
    event["end"]["dateTime"] = new_end
    service.events().update(calendarId="primary", eventId=event_id, body=event).execute()
    logger.info("Rescheduled event %s to %s", event_id, new_start)

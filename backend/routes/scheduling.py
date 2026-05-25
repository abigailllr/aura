import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services import firebase
from services.calendar import (
    get_calendar_service,
    fetch_events,
    analyze_and_suggest,
    reschedule_event,
)

logger = logging.getLogger(__name__)
router = APIRouter()


class CalendarRequest(BaseModel):
    user_id: str
    token: dict


class RescheduleRequest(BaseModel):
    user_id: str
    token: dict
    event_id: str
    new_start: str
    new_end: str


@router.post("/analyze")
async def analyze_schedule(req: CalendarRequest):
    energy_doc = firebase.db().collection("energy_profiles").document(req.user_id).get()

    if not energy_doc.exists:
        raise HTTPException(status_code=404, detail="No energy profile found. Collect more biometric data first.")

    energy_profile = energy_doc.to_dict()

    try:
        service = get_calendar_service(req.token)
        events = fetch_events(service)
    except Exception as e:
        logger.error("Calendar fetch failed for user %s: %s", req.user_id, e)
        raise HTTPException(status_code=502, detail="Could not access Google Calendar")

    analysis = analyze_and_suggest(events, energy_profile)
    return analysis.model_dump()


@router.post("/reschedule")
async def reschedule(req: RescheduleRequest):
    try:
        service = get_calendar_service(req.token)
        reschedule_event(service, req.event_id, req.new_start, req.new_end)
    except Exception as e:
        logger.error("Reschedule failed for user %s: %s", req.user_id, e)
        raise HTTPException(status_code=502, detail="Could not reschedule event")

    return {"rescheduled": req.event_id, "new_start": req.new_start}


@router.get("/{user_id}/events")
async def get_events(user_id: str, access_token: str):
    try:
        service = get_calendar_service({"access_token": access_token})
        events = fetch_events(service)
    except Exception as e:
        logger.error("Calendar fetch failed for user %s: %s", user_id, e)
        raise HTTPException(status_code=502, detail="Could not access Google Calendar")

    return events

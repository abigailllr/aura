import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from services import firebase
from services.auth import verify_token
from services.calendar import (
    get_calendar_service,
    fetch_events,
    analyze_and_suggest,
    reschedule_event,
)

logger = logging.getLogger(__name__)
router = APIRouter()


class TokenRequest(BaseModel):
    token: dict


class RescheduleRequest(BaseModel):
    token: dict
    event_id: str
    new_start: str
    new_end: str


@router.post("/analyze")
async def analyze_schedule(req: TokenRequest, user_id: str = Depends(verify_token)):
    energy_doc = firebase.db().collection("energy_profiles").document(user_id).get()

    if not energy_doc.exists:
        raise HTTPException(status_code=404, detail="No energy profile found")

    try:
        service = get_calendar_service(req.token)
        events = fetch_events(service)
    except Exception as e:
        logger.error("Calendar fetch failed for user %s: %s", user_id, e)
        raise HTTPException(status_code=502, detail="Could not access Google Calendar")

    analysis = analyze_and_suggest(events, energy_doc.to_dict())
    return analysis.model_dump()


@router.post("/reschedule")
async def reschedule(req: RescheduleRequest, user_id: str = Depends(verify_token)):
    try:
        service = get_calendar_service(req.token)
        reschedule_event(service, req.event_id, req.new_start, req.new_end)
    except Exception as e:
        logger.error("Reschedule failed for user %s: %s", user_id, e)
        raise HTTPException(status_code=502, detail="Could not reschedule event")

    return {"rescheduled": req.event_id, "new_start": req.new_start}


@router.get("/events")
async def get_events(access_token: str, user_id: str = Depends(verify_token)):
    try:
        service = get_calendar_service({"access_token": access_token})
        events = fetch_events(service)
    except Exception as e:
        logger.error("Calendar fetch failed for user %s: %s", user_id, e)
        raise HTTPException(status_code=502, detail="Could not access Google Calendar")

    return events

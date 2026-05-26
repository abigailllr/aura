import asyncio
import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from services import firebase
from services.auth import verify_token
from services.limiter import limiter
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
@limiter.limit("10/minute")
async def analyze_schedule(request: Request, req: TokenRequest, user_id: str = Depends(verify_token)):
    energy_profile = await asyncio.to_thread(firebase.get_energy_profile, user_id)

    if not energy_profile:
        raise HTTPException(status_code=404, detail="No energy profile found")

    try:
        service = await asyncio.to_thread(get_calendar_service, req.token)
        events = await asyncio.to_thread(fetch_events, service)
    except Exception as e:
        logger.error("Calendar fetch failed for user %s: %s", user_id, e)
        raise HTTPException(status_code=502, detail="Could not access Google Calendar")

    try:
        analysis = await asyncio.to_thread(analyze_and_suggest, events, energy_profile)
    except Exception as e:
        logger.error("Schedule analysis failed for user %s: %s", user_id, e)
        raise HTTPException(status_code=502, detail="Schedule analysis failed")

    return analysis.model_dump()


@router.post("/reschedule")
@limiter.limit("10/minute")
async def reschedule(request: Request, req: RescheduleRequest, user_id: str = Depends(verify_token)):
    try:
        service = await asyncio.to_thread(get_calendar_service, req.token)
        await asyncio.to_thread(reschedule_event, service, req.event_id, req.new_start, req.new_end)
    except Exception as e:
        logger.error("Reschedule failed for user %s: %s", user_id, e)
        raise HTTPException(status_code=502, detail="Could not reschedule event")

    return {"rescheduled": req.event_id, "new_start": req.new_start}


@router.get("/events")
async def get_events(access_token: str, user_id: str = Depends(verify_token)):
    try:
        service = await asyncio.to_thread(get_calendar_service, {"access_token": access_token})
        events = await asyncio.to_thread(fetch_events, service)
    except Exception as e:
        logger.error("Calendar fetch failed for user %s: %s", user_id, e)
        raise HTTPException(status_code=502, detail="Could not access Google Calendar")

    return events

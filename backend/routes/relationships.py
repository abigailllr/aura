import asyncio
import logging
from fastapi import APIRouter, HTTPException, Depends

from services import firebase
from services.auth import verify_token
from services.relationships import analyze

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def get_insights(user_id: str = Depends(verify_token)):
    people = await asyncio.to_thread(firebase.get_people, user_id)
    conversations = await asyncio.to_thread(firebase.get_conversations, user_id, 100)

    if not people:
        return {"alerts": [], "summary": "No people saved yet.", "tone_patterns": []}

    try:
        insight = await asyncio.to_thread(analyze, people, conversations)
    except Exception as e:
        logger.error("Relationship analysis failed for user %s: %s", user_id, e)
        raise HTTPException(status_code=502, detail="Relationship analysis failed")

    return insight.model_dump()


@router.get("/alerts")
async def get_alerts(user_id: str = Depends(verify_token)):
    people = await asyncio.to_thread(firebase.get_people, user_id)
    conversations = await asyncio.to_thread(firebase.get_conversations, user_id, 100)

    if not people:
        return []

    try:
        insight = await asyncio.to_thread(analyze, people, conversations)
    except Exception as e:
        logger.error("Relationship alerts failed for user %s: %s", user_id, e)
        raise HTTPException(status_code=502, detail="Relationship analysis failed")

    return insight.alerts

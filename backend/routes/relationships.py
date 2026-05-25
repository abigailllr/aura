import logging
from fastapi import APIRouter, Depends

from services import firebase
from services.auth import verify_token
from services.relationships import analyze

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def get_insights(user_id: str = Depends(verify_token)):
    people = firebase.get_people(user_id)
    conversations = firebase.get_conversations(user_id, limit=100)

    if not people:
        return {"alerts": [], "summary": "No people saved yet.", "tone_patterns": []}

    insight = analyze(people, conversations)
    return insight.model_dump()


@router.get("/alerts")
async def get_alerts(user_id: str = Depends(verify_token)):
    people = firebase.get_people(user_id)
    conversations = firebase.get_conversations(user_id, limit=100)

    if not people:
        return []

    insight = analyze(people, conversations)
    return insight.alerts

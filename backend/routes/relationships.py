import logging
from fastapi import APIRouter

from services import firebase
from services.relationships import analyze

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{user_id}")
async def get_insights(user_id: str):
    people = firebase.get_people(user_id)
    conversations = firebase.get_conversations(user_id, limit=100)

    if not people:
        return {"alerts": [], "summary": "No people saved yet.", "tone_patterns": []}

    insight = analyze(people, conversations)
    return insight.model_dump()


@router.get("/{user_id}/alerts")
async def get_alerts(user_id: str):
    people = firebase.get_people(user_id)
    conversations = firebase.get_conversations(user_id, limit=100)

    if not people:
        return []

    insight = analyze(people, conversations)
    return insight.alerts

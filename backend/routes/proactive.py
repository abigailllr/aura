import logging
from fastapi import APIRouter, Depends

from services import firebase
from services.auth import verify_token

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/insights")
async def get_insights(user_id: str = Depends(verify_token)):
    insights = firebase.get_unread_insights(user_id)
    firebase.mark_insights_read(user_id)
    return insights

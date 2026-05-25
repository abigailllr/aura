import logging
from fastapi import APIRouter

from services import firebase

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{user_id}")
async def get_conversations(user_id: str, limit: int = 20):
    return firebase.get_conversations(user_id, limit)


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str):
    firebase.db().collection("conversations").document(conversation_id).delete()
    return {"deleted": conversation_id}

import logging
from fastapi import APIRouter, Depends

from services import firebase
from services.auth import verify_token

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def get_conversations(limit: int = 20, user_id: str = Depends(verify_token)):
    return firebase.get_conversations(user_id, limit)


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str, user_id: str = Depends(verify_token)):
    firebase.db().collection("conversations").document(conversation_id).delete()
    return {"deleted": conversation_id}

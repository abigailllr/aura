import asyncio
import logging
from fastapi import APIRouter, HTTPException, Depends

from services import firebase
from services.auth import verify_token

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def get_conversations(limit: int = 20, user_id: str = Depends(verify_token)):
    return await asyncio.to_thread(firebase.get_conversations, user_id, limit)


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str, user_id: str = Depends(verify_token)):
    deleted = await asyncio.to_thread(firebase.delete_conversation, user_id, conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"deleted": conversation_id}

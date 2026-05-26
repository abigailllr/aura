import asyncio
import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from services import firebase, claude
from services.auth import verify_token
from services.connection_manager import manager
from services.limiter import limiter

logger = logging.getLogger(__name__)
router = APIRouter()

GESTURE_ACTIONS = {
    "double_tap": "summarize my last conversation",
    "hold": "what should i focus on right now",
    "swipe_up": "give me a quick energy check",
    "swipe_down": "who should i reach out to today",
}


class GestureEvent(BaseModel):
    gesture: str


@router.post("/")
@limiter.limit("30/minute")
async def handle_gesture(request: Request, event: GestureEvent, user_id: str = Depends(verify_token)):
    prompt = GESTURE_ACTIONS.get(event.gesture)

    if not prompt:
        raise HTTPException(status_code=422, detail=f"unknown gesture: {event.gesture}")

    history = await asyncio.to_thread(firebase.get_conversations, user_id, 5)
    messages = []
    for convo in reversed(history):
        messages.extend(convo.get("messages", []))
    messages.append({"role": "user", "content": prompt})

    try:
        response = await asyncio.to_thread(claude.ask, messages)
    except Exception as e:
        logger.error("Claude failed on gesture for user %s: %s", user_id, e)
        raise HTTPException(status_code=502, detail="AI response failed")

    await asyncio.to_thread(
        firebase.save_conversation,
        user_id,
        messages + [{"role": "assistant", "content": response}],
    )

    await manager.push(user_id, {"type": "gesture_response", "gesture": event.gesture, "text": response})

    return {"gesture": event.gesture, "response": response}

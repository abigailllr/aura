import asyncio
import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from services import firebase
from services.auth import verify_token

logger = logging.getLogger(__name__)
router = APIRouter()


class TokenRequest(BaseModel):
    fcm_token: str


@router.post("/token")
async def register_token(req: TokenRequest, user_id: str = Depends(verify_token)):
    await asyncio.to_thread(firebase.save_fcm_token, user_id, req.fcm_token)
    return {"registered": True}

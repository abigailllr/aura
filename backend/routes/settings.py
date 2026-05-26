import asyncio
import logging
from fastapi import APIRouter, Depends

from services import firebase
from services.auth import verify_token

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def get_settings(user_id: str = Depends(verify_token)):
    settings = await asyncio.to_thread(firebase.get_settings, user_id)
    return settings or {}


@router.patch("/")
async def update_settings(payload: dict, user_id: str = Depends(verify_token)):
    await asyncio.to_thread(firebase.save_settings, user_id, payload)
    return await asyncio.to_thread(firebase.get_settings, user_id)

import asyncio
import logging

from services import firebase, claude
from services.connection_manager import manager

logger = logging.getLogger(__name__)


async def check_user(user_id: str):
    biometrics = await asyncio.to_thread(firebase.get_biometrics, user_id, 10)
    if not biometrics:
        return

    people = await asyncio.to_thread(firebase.get_people, user_id)
    conversations = await asyncio.to_thread(firebase.get_conversations, user_id, 20)

    insight = await asyncio.to_thread(
        claude.generate_proactive_insight, biometrics, people, conversations
    )

    if not insight:
        return

    await asyncio.to_thread(firebase.save_insight, user_id, insight)
    await manager.push(user_id, {"type": "insight", "text": insight})
    logger.info("Proactive insight sent to user %s", user_id)


async def run():
    user_ids = await asyncio.to_thread(firebase.get_active_user_ids)
    if not user_ids:
        return

    await asyncio.gather(*[check_user(uid) for uid in user_ids])

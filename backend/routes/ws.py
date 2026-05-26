import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from firebase_admin import auth

from services import whisper, claude, firebase, tts
from services.connection_manager import manager

logger = logging.getLogger(__name__)
router = APIRouter()


async def _authenticate(websocket: WebSocket) -> str | None:
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001)
        return None
    try:
        decoded = await asyncio.to_thread(auth.verify_id_token, token)
        return decoded["uid"]
    except Exception:
        await websocket.close(code=4001)
        return None


async def _stream_response(
    websocket: WebSocket,
    user_id: str,
    user_text: str,
    speak: bool,
):
    history = await asyncio.to_thread(firebase.get_conversations, user_id, 5)
    messages = []
    for convo in reversed(history):
        messages.extend(convo.get("messages", []))
    messages.append({"role": "user", "content": user_text})

    full_response = ""
    try:
        async for chunk in claude.ask_stream(messages):
            full_response += chunk
            await websocket.send_json({"type": "chunk", "text": chunk})
    except Exception as e:
        logger.error("Claude stream failed for user %s: %s", user_id, e)
        await websocket.send_json({"type": "error", "detail": "AI response failed"})
        return

    await asyncio.to_thread(
        firebase.save_conversation,
        user_id,
        messages + [{"role": "assistant", "content": full_response}],
    )

    done_payload: dict = {"type": "done"}
    if speak and full_response:
        try:
            done_payload["audio_base64"] = await asyncio.to_thread(
                tts.synthesize, full_response
            )
            done_payload["mime_type"] = "audio/mp3"
        except Exception as e:
            logger.error("TTS failed for user %s: %s", user_id, e)

    await websocket.send_json(done_payload)


async def _handle_voice(websocket: WebSocket, user_id: str, payload: dict):
    audio_base64 = payload.get("audio_base64", "").strip()
    if not audio_base64:
        await websocket.send_json({"type": "error", "detail": "audio_base64 is required"})
        return

    mime_type = payload.get("mime_type", "audio/wav")
    speak = payload.get("speak", False)

    try:
        transcript = await asyncio.to_thread(whisper.transcribe, audio_base64, mime_type)
    except Exception as e:
        logger.error("Transcription failed for user %s: %s", user_id, e)
        await websocket.send_json({"type": "error", "detail": "transcription failed"})
        return

    if not transcript.strip():
        await websocket.send_json({"type": "error", "detail": "could not transcribe audio"})
        return

    await websocket.send_json({"type": "transcript", "text": transcript})
    await _stream_response(websocket, user_id, transcript, speak)


async def _handle_text(websocket: WebSocket, user_id: str, payload: dict):
    content = payload.get("content", "").strip()
    if not content:
        await websocket.send_json({"type": "error", "detail": "content is required"})
        return

    speak = payload.get("speak", False)
    await _stream_response(websocket, user_id, content, speak)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    user_id = await _authenticate(websocket)
    if not user_id:
        return

    manager.connect(user_id, websocket)
    logger.info("WebSocket connected: %s", user_id)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "detail": "invalid JSON"})
                continue

            msg_type = message.get("type")

            if msg_type == "voice":
                await _handle_voice(websocket, user_id, message)
            elif msg_type == "text":
                await _handle_text(websocket, user_id, message)
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            else:
                await websocket.send_json({"type": "error", "detail": f"unknown type: {msg_type}"})

    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
        logger.info("WebSocket disconnected: %s", user_id)

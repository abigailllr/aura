import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from models.conversation import AudioRequest
from services import whisper, claude, firebase

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/voice")
async def voice_to_ai(req: AudioRequest):
    try:
        transcript = whisper.transcribe(req.audio_base64, req.mime_type)
    except Exception as e:
        logger.error("Whisper transcription failed: %s", e)
        raise HTTPException(status_code=422, detail="Audio transcription failed")

    history = firebase.get_conversations(req.user_id, limit=5)
    messages = []
    for convo in reversed(history):
        messages.extend(convo.get("messages", []))
    messages.append({"role": "user", "content": transcript})

    try:
        response = claude.ask(messages)
    except Exception as e:
        logger.error("Claude request failed: %s", e)
        raise HTTPException(status_code=502, detail="AI response failed")

    firebase.save_conversation(req.user_id, messages + [
        {"role": "assistant", "content": response}
    ])

    return {"transcript": transcript, "response": response}


@router.post("/voice/stream")
async def voice_to_ai_stream(req: AudioRequest):
    try:
        transcript = whisper.transcribe(req.audio_base64, req.mime_type)
    except Exception as e:
        logger.error("Whisper transcription failed: %s", e)
        raise HTTPException(status_code=422, detail="Audio transcription failed")

    history = firebase.get_conversations(req.user_id, limit=5)
    messages = []
    for convo in reversed(history):
        messages.extend(convo.get("messages", []))
    messages.append({"role": "user", "content": transcript})

    async def generate():
        full_response = ""
        async for chunk in claude.ask_stream(messages):
            full_response += chunk
            yield chunk
        firebase.save_conversation(req.user_id, messages + [
            {"role": "assistant", "content": full_response}
        ])

    return StreamingResponse(generate(), media_type="text/plain")

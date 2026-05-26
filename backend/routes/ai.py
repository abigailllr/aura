import asyncio
import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services import whisper, claude, firebase, tts
from services.auth import verify_token
from services.limiter import limiter

logger = logging.getLogger(__name__)
router = APIRouter()


class VoiceRequest(BaseModel):
    audio_base64: str
    mime_type: str = "audio/wav"
    speak: bool = False


class TTSRequest(BaseModel):
    text: str
    voice: str = "nova"


@router.post("/voice")
@limiter.limit("20/minute")
async def voice_to_ai(request: Request, req: VoiceRequest, user_id: str = Depends(verify_token)):
    try:
        transcript = await asyncio.to_thread(whisper.transcribe, req.audio_base64, req.mime_type)
    except Exception as e:
        logger.error("Whisper transcription failed: %s", e)
        raise HTTPException(status_code=422, detail="Audio transcription failed")

    history = await asyncio.to_thread(firebase.get_conversations, user_id, 5)
    messages = []
    for convo in reversed(history):
        messages.extend(convo.get("messages", []))
    messages.append({"role": "user", "content": transcript})

    try:
        response = await asyncio.to_thread(claude.ask, messages)
    except Exception as e:
        logger.error("Claude request failed: %s", e)
        raise HTTPException(status_code=502, detail="AI response failed")

    await asyncio.to_thread(
        firebase.save_conversation,
        user_id,
        messages + [{"role": "assistant", "content": response}],
    )

    result = {"transcript": transcript, "response": response}

    if req.speak:
        try:
            result["audio_base64"] = await asyncio.to_thread(tts.synthesize, response)
        except Exception as e:
            logger.error("TTS synthesis failed: %s", e)

    return result


@router.post("/voice/stream")
@limiter.limit("20/minute")
async def voice_to_ai_stream(request: Request, req: VoiceRequest, user_id: str = Depends(verify_token)):
    try:
        transcript = await asyncio.to_thread(whisper.transcribe, req.audio_base64, req.mime_type)
    except Exception as e:
        logger.error("Whisper transcription failed: %s", e)
        raise HTTPException(status_code=422, detail="Audio transcription failed")

    history = await asyncio.to_thread(firebase.get_conversations, user_id, 5)
    messages = []
    for convo in reversed(history):
        messages.extend(convo.get("messages", []))
    messages.append({"role": "user", "content": transcript})

    async def generate():
        full_response = ""
        async for chunk in claude.ask_stream(messages):
            full_response += chunk
            yield chunk
        await asyncio.to_thread(
            firebase.save_conversation,
            user_id,
            messages + [{"role": "assistant", "content": full_response}],
        )

    return StreamingResponse(generate(), media_type="text/plain")


@router.post("/speak")
@limiter.limit("30/minute")
async def speak(request: Request, req: TTSRequest, user_id: str = Depends(verify_token)):
    try:
        audio = await asyncio.to_thread(tts.synthesize, req.text, req.voice)
    except Exception as e:
        logger.error("TTS synthesis failed for user %s: %s", user_id, e)
        raise HTTPException(status_code=502, detail="Speech synthesis failed")

    return {"audio_base64": audio, "mime_type": "audio/mp3"}

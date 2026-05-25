import base64
import tempfile
import os
from openai import OpenAI

from config import settings

client = OpenAI(api_key=settings.openai_api_key)


def transcribe(audio_base64: str, mime_type: str = "audio/wav") -> str:
    audio_bytes = base64.b64decode(audio_base64)
    ext = mime_type.split("/")[-1]

    with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name

    try:
        with open(tmp_path, "rb") as f:
            result = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language="en",
            )
        return result.text
    finally:
        os.unlink(tmp_path)

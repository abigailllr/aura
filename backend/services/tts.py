import base64
from openai import OpenAI

from config import settings

client = OpenAI(api_key=settings.openai_api_key)


def synthesize(text: str, voice: str = "nova") -> str:
    response = client.audio.speech.create(
        model="tts-1",
        voice=voice,
        input=text,
        response_format="mp3",
    )
    return base64.b64encode(response.content).decode("utf-8")

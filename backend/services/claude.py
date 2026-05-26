import logging
from pydantic import BaseModel

import anthropic

from config import settings

logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
async_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

AURA_SYSTEM = (
    "You are Aura, an intelligent AI assistant living on a wearable bracelet. "
    "You have access to the user's biometric data, memory of people they've met, "
    "and their schedule. Be concise. Responses are whispered through earbuds. "
    "Two sentences maximum unless the user asks for more detail. "
    "Never mention being an AI bracelet unless asked."
)


def ask(messages: list[dict], system: str = AURA_SYSTEM) -> str:
    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=512,
        thinking={"type": "adaptive"},
        system=system,
        messages=messages,
    )
    return next(b.text for b in response.content if b.type == "text")


async def ask_stream(messages: list[dict], system: str = AURA_SYSTEM):
    async with async_client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=512,
        thinking={"type": "adaptive"},
        system=system,
        messages=messages,
    ) as stream:
        async for text in stream.text_stream:
            yield text


def analyze_relationships(timeline: list[dict]) -> str:
    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=256,
        thinking={"type": "adaptive"},
        messages=[{
            "role": "user",
            "content": (
                f"Analyze this relationship timeline. Identify: who hasn't been contacted "
                f"in a while, emotional tone patterns, relationships needing attention. "
                f"Be specific, use names, under 100 words.\n\nTimeline: {timeline}"
            ),
        }],
    )
    return next(b.text for b in response.content if b.type == "text")


class _EnergyPatterns(BaseModel):
    class Window(BaseModel):
        start_hour: int
        end_hour: int
        label: str

    peak_windows: list[Window]
    low_windows: list[Window]
    insight: str


def analyze_energy_patterns(biometric_history: list[dict]) -> dict:
    response = client.messages.parse(
        model="claude-opus-4-6",
        max_tokens=512,
        output_format=_EnergyPatterns,
        messages=[{
            "role": "user",
            "content": (
                f"Analyze this biometric history. Identify peak energy windows, "
                f"low energy windows, and day-of-week patterns.\n\nData: {biometric_history}"
            ),
        }],
    )
    return response.parsed_output.model_dump()


class _PersonContext(BaseModel):
    name: str
    job: str | None = None
    company: str | None = None
    notes: str | None = None


def extract_person_context(transcript: str) -> _PersonContext:
    response = client.messages.parse(
        model="claude-opus-4-6",
        max_tokens=256,
        output_format=_PersonContext,
        messages=[{
            "role": "user",
            "content": f"Extract person details from this introduction:\n\n{transcript}",
        }],
    )
    return response.parsed_output


class _ProactiveInsight(BaseModel):
    should_notify: bool
    text: str | None = None


def generate_proactive_insight(
    biometrics: list[dict],
    people: list[dict],
    conversations: list[dict],
) -> str | None:
    response = client.messages.parse(
        model="claude-opus-4-6",
        max_tokens=256,
        output_format=_ProactiveInsight,
        messages=[{
            "role": "user",
            "content": (
                "You are Aura, a proactive AI on a wearable bracelet. "
                "Analyze the user's current state and decide if they need a nudge right now. "
                "Only notify if something genuinely actionable is happening: low energy before a demanding task, "
                "a relationship going cold, or a pattern worth breaking. "
                "If nothing noteworthy, set should_notify to false. "
                "If notifying, write one short sentence. Direct, no fluff.\n\n"
                f"Biometrics (recent first): {biometrics}\n"
                f"People they know: {people}\n"
                f"Recent conversations: {conversations}"
            ),
        }],
    )
    result = response.parsed_output
    return result.text if result.should_notify else None

import asyncio
import json
import os

import anthropic
from dotenv import load_dotenv

from app.models import AgentComment

load_dotenv()

_client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Differentiated roles so errors de-correlate instead of echoing.
_ROLES = [
    (
        "Skeptical Fact-Checker",
        "Scrutinize factual accuracy. Flag claims that may be wrong, outdated, or oversimplified.",
    ),
    (
        "Domain Expert",
        "You are a subject-matter expert in the topic being discussed. "
        "Flag technical gaps, missing nuance, or incorrect statements.",
    ),
    (
        "Devil's Advocate",
        "Challenge assumptions and conventional wisdom. "
        "Flag claims presented as settled fact that are actually contested or context-dependent.",
    ),
]

_DECOMPOSE_SYSTEM = (
    "Extract the key factual claims from an AI-generated educational answer. "
    "Return a JSON array of strings — each string is one specific, verifiable factual claim. "
    "Maximum 5 claims. Focus on the most important and fact-checkable statements. "
    "Return only the JSON array, no other text."
)


async def _decompose(draft: str, question: str) -> list[str]:
    response = await _client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=[{"type": "text", "text": _DECOMPOSE_SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": f"Question: {question}\n\nAnswer:\n{draft}"}],
    )
    try:
        return json.loads(response.content[0].text)[:5]
    except Exception:
        return []


async def _critique_one(claim: str, role: str, role_desc: str) -> AgentComment:
    system = (
        f"You are a {role} reviewing claims in an AI-generated educational answer. "
        f"{role_desc}\n\n"
        "Evaluate the given claim and respond with JSON only:\n"
        '{"verdict": "supports"|"refutes"|"unclear", "explanation": "<1-2 sentences>"}'
    )
    response = await _client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": f"Claim: {claim}"}],
    )
    try:
        data = json.loads(response.content[0].text)
        verdict = data.get("verdict", "unclear")
        if verdict not in ("supports", "refutes", "unclear"):
            verdict = "unclear"
        explanation = data.get("explanation", "")
    except Exception:
        verdict = "unclear"
        explanation = response.content[0].text[:300]

    return AgentComment(
        agent="critic",
        role=role,
        content=explanation,
        claim=claim,
        verdict=verdict,
    )


async def critique(draft: str, question: str) -> list[AgentComment]:
    """Decompose draft into atomic claims and red-team each in parallel."""
    claims = await _decompose(draft, question)
    if not claims:
        return []
    tasks = [
        _critique_one(claim, *_ROLES[i % len(_ROLES)])
        for i, claim in enumerate(claims)
    ]
    return list(await asyncio.gather(*tasks))

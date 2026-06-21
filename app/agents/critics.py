import asyncio
import json
import os
import re

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

def _strip_fences(text: str) -> str:
    """Remove markdown code fences that models add around JSON responses."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


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
        return json.loads(_strip_fences(response.content[0].text))[:5]
    except Exception:
        return []


async def _critique_one(
    claim: str, role: str, role_desc: str, claim_id: str | None = None
) -> AgentComment:
    system = (
        f"You are a {role} reviewing claims in an AI-generated educational answer. "
        f"{role_desc}\n\n"
        "Evaluate the given claim and respond with JSON only:\n"
        '{"verdict": "supports"|"refutes"|"unclear", "explanation": "<max 2 short sentences, under 30 words total>"}'
    )
    response = await _client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": f"Claim: {claim}"}],
    )
    raw = response.content[0].text
    data: dict = {}
    try:
        data = json.loads(_strip_fences(raw))
    except Exception:
        # Model sometimes adds text before/after the JSON — extract the first {...} block
        m = re.search(r'\{[^{}]*\}', raw, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group())
            except Exception:
                pass

    verdict = data.get("verdict", "unclear")
    if verdict not in ("supports", "refutes", "unclear"):
        verdict = "unclear"
    explanation = data.get("explanation") or raw.split("{")[0].strip() or raw[:300]

    return AgentComment(
        agent="critic",
        role=role,
        content=explanation,
        claim=claim,
        verdict=verdict,
        claim_id=claim_id,
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


# ── Paragraph-anchored decomposition (blog-post review path) ─────────────────────

_DECOMPOSE_POST_SYSTEM = (
    "Extract the key factual claims from a blog-style study post supplied as numbered paragraphs. "
    "Return a JSON array of objects, each {\"claim\": \"<one verifiable factual claim>\", "
    "\"paragraph_id\": \"<the id of the paragraph it comes from>\"}. "
    "Maximum 5 claims, focusing on the most important and fact-checkable statements. "
    "Use only paragraph ids that appear in the input. Return only the JSON array, no other text."
)


async def _decompose_post(paragraphs: list[dict]) -> list[dict]:
    """paragraphs: [{"id": "p1", "text": "..."}] → [{"claim": str, "paragraph_id": str}]."""
    valid_ids = {p["id"] for p in paragraphs}
    numbered = "\n\n".join(f'[{p["id"]}] {p["text"]}' for p in paragraphs)
    response = await _client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=768,
        system=[{"type": "text", "text": _DECOMPOSE_POST_SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": numbered}],
    )
    try:
        items = json.loads(_strip_fences(response.content[0].text))[:5]
    except Exception:
        return []
    out = []
    for it in items:
        claim = (it.get("claim") or "").strip()
        pid = it.get("paragraph_id")
        if claim and pid in valid_ids:
            out.append({"claim": claim, "paragraph_id": pid})
    return out


async def critique_post(paragraphs: list[dict], question: str) -> list[AgentComment]:
    """Decompose a structured post into claims anchored to paragraphs, red-team each in parallel."""
    claims = await _decompose_post(paragraphs)
    if not claims:
        return []
    tasks = [
        _critique_one(c["claim"], *_ROLES[i % len(_ROLES)], claim_id=c["paragraph_id"])
        for i, c in enumerate(claims)
    ]
    return list(await asyncio.gather(*tasks))

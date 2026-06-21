import asyncio
import os

import anthropic
from dotenv import load_dotenv

from app.models import AgentComment

load_dotenv()

_client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

_SAMPLES = 3
_SAMPLE_SYSTEM = (
    "You evaluate whether a factual claim is likely true, false, or uncertain. "
    "Respond with exactly one word: 'true', 'false', or 'uncertain'. No other text."
)


async def _sample_claim(claim: str) -> str:
    response = await _client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=5,
        temperature=0.8,
        system=[{"type": "text", "text": _SAMPLE_SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": f"Claim: {claim}"}],
    )
    raw = response.content[0].text.strip().lower()
    if "false" in raw:
        return "false"
    if "uncertain" in raw or "unclear" in raw or "unknown" in raw:
        return "uncertain"
    return "true"


async def _disagreement_score(claim: str) -> float:
    """0.0 = all samples agree; 1.0 = all samples differ."""
    verdicts = await asyncio.gather(*[_sample_claim(claim) for _ in range(_SAMPLES)])
    unique = len(set(verdicts))
    return (unique - 1) / (_SAMPLES - 1)


async def compute_confidence(
    critic_comments: list[AgentComment],
    verifier_comments: list[AgentComment],
) -> tuple[float, str]:
    """
    Compute confidence by combining critic/verifier verdicts with multi-sample
    semantic disagreement on contested claims.
    """
    if not critic_comments:
        return 0.9, "high"

    # Multi-sample contested claims in parallel
    contested = [
        c.claim for c in critic_comments
        if c.claim and c.verdict in ("refutes", "unclear")
    ][:3]

    if contested:
        disagreement_scores = await asyncio.gather(
            *[_disagreement_score(claim) for claim in contested]
        )
        avg_disagreement = sum(disagreement_scores) / len(disagreement_scores)
    else:
        avg_disagreement = 0.0

    # Verdict-based base score
    refuted = sum(1 for c in critic_comments if c.verdict == "refutes")
    unclear = sum(1 for c in critic_comments if c.verdict == "unclear")
    verifier_supports = sum(1 for v in verifier_comments if v.verdict == "supports")
    verifier_refutes = sum(1 for v in verifier_comments if v.verdict == "refutes")
    effective_refuted = max(0, refuted - verifier_supports) + verifier_refutes

    base = 1.0 - (effective_refuted * 0.2) - (unclear * 0.08)
    score = base - (avg_disagreement * 0.3)
    score = round(max(0.0, min(1.0, score)), 2)

    if score >= 0.75:
        return score, "high"
    elif score >= 0.4:
        return score, "medium"
    else:
        return score, "low"

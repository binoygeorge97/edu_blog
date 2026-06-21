import asyncio

from app.models import AgentComment
from app.grounding.browser import fetch_evidence

_MAX_CLAIMS = 3  # cap per CLAUDE.md to control browser-hour spend


async def verify(critic_comments: list[AgentComment]) -> list[AgentComment]:
    """Fetch web evidence for claims flagged as refuted or unclear by critics."""
    flagged = [
        c for c in critic_comments
        if c.claim and c.verdict in ("refutes", "unclear")
    ][:_MAX_CLAIMS]

    if not flagged:
        return []

    results = await asyncio.gather(
        *[_verify_one(c) for c in flagged], return_exceptions=True
    )
    return [r for r in results if isinstance(r, AgentComment)]


async def _verify_one(critic_comment: AgentComment) -> AgentComment:
    evidence = await fetch_evidence(critic_comment.claim)
    if evidence is None:
        return AgentComment(
            agent="verifier",
            role="Verifier",
            content="Web evidence unavailable for this claim.",
            claim=critic_comment.claim,
            verdict="unclear",
            url=None,
            claim_id=critic_comment.claim_id,
        )
    return AgentComment(
        agent="verifier",
        role="Verifier",
        content=evidence.quote,
        claim=critic_comment.claim,
        verdict=evidence.verdict,
        url=evidence.url,
        claim_id=critic_comment.claim_id,
    )

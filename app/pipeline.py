import app.telemetry  # noqa: F401 — must be first; triggers Phoenix register() before any anthropic client init

from opentelemetry import trace

from app.agents.generator import generate
from app.agents.critics import critique
from app.agents.verifier import verify
from app.agents.teacher import teach
from app.models import AgentComment, PipelineResult

_tracer = trace.get_tracer("sourcerer.pipeline")


def _compute_confidence(
    critic_comments: list[AgentComment],
    verifier_comments: list[AgentComment],
) -> tuple[float, str]:
    if not critic_comments:
        return 0.9, "high"

    refuted = sum(1 for c in critic_comments if c.verdict == "refutes")
    unclear = sum(1 for c in critic_comments if c.verdict == "unclear")

    # Verifier support can redeem a critic refute
    verifier_supports = sum(1 for v in verifier_comments if v.verdict == "supports")
    effective_refuted = max(0, refuted - verifier_supports)

    score = 1.0 - (effective_refuted * 0.25) - (unclear * 0.1)
    score = max(0.0, min(1.0, score))

    if score >= 0.75:
        return score, "high"
    elif score >= 0.4:
        return score, "medium"
    else:
        return score, "low"


async def run_pipeline(question: str) -> PipelineResult:
    with _tracer.start_as_current_span("pipeline.run") as span:
        span.set_attribute("question", question[:200])

        draft = await generate(question)
        span.set_attribute("draft.length", len(draft))

        critic_comments = await critique(draft, question)
        span.set_attribute("critic.count", len(critic_comments))

        verifier_comments = await verify(critic_comments)
        span.set_attribute("verifier.count", len(verifier_comments))

        answer = await teach(draft, question, critic_comments, verifier_comments)
        span.set_attribute("answer.length", len(answer))

    confidence, confidence_level = _compute_confidence(critic_comments, verifier_comments)

    return PipelineResult(
        answer=answer,
        comments=[
            AgentComment(agent="generator", role="Generator", content=draft),
            *critic_comments,
            *verifier_comments,
        ],
        confidence=confidence,
        confidence_level=confidence_level,
    )


async def reply_to_comment(comment: AgentComment, followup: str) -> PipelineResult:
    context_question = (
        f"{followup}\n\n"
        f"[Context: This is a follow-up to a comment by {comment.role}. "
        f"Their perspective: {comment.content[:500]}"
        + (f" They were discussing the claim: '{comment.claim}'" if comment.claim else "")
        + "]"
    )
    return await run_pipeline(context_question)

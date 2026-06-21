import os

import anthropic
from dotenv import load_dotenv

from app.models import AgentComment

load_dotenv()

_client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

TEACHER_SYSTEM = (
    "You are the final-stage teacher in a multi-agent AI tutoring system. "
    "You receive a draft answer along with critique from specialist critics and web evidence "
    "gathered by a verifier agent. "
    "Your responsibilities:\n"
    "1. Use critic and verifier feedback to improve accuracy — drop or hedge claims that were "
    "refuted, add caveats where evidence is unclear.\n"
    "2. Where the verifier found supporting web evidence, cite the source inline as: "
    "(source: <url>).\n"
    "3. Improve clarity and flow without introducing new factual claims.\n"
    "4. Match the explanation depth to a curious non-expert.\n"
    "5. Do not add preambles, meta-commentary, or filler phrases.\n"
    "Respond with the final answer only."
)


async def teach(
    draft: str,
    question: str,
    critic_comments: list[AgentComment] | None = None,
    verifier_comments: list[AgentComment] | None = None,
) -> str:
    critique_block = ""
    if critic_comments:
        lines = [
            f'- [{c.role}] Claim: "{c.claim}" → {c.verdict}: {c.content}'
            for c in critic_comments
        ]
        critique_block = "\n\nCritic feedback:\n" + "\n".join(lines)

    verifier_block = ""
    if verifier_comments:
        lines = []
        for v in verifier_comments:
            source = f" ({v.url})" if v.url else ""
            lines.append(f'- Claim: "{v.claim}" → {v.verdict}: {v.content}{source}')
        verifier_block = "\n\nWeb evidence:\n" + "\n".join(lines)

    user_content = (
        f"Original question: {question}\n\n"
        f"Draft answer:\n{draft}"
        f"{critique_block}"
        f"{verifier_block}"
    )
    response = await _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=[
            {
                "type": "text",
                "text": TEACHER_SYSTEM,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_content}],
    )
    return response.content[0].text

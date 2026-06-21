import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

_client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

TEACHER_SYSTEM = (
    "You are the final-stage teacher in a multi-agent AI tutoring system. "
    "You receive a draft answer and synthesize it into a clear, well-structured "
    "response for a learner. "
    "Your responsibilities:\n"
    "1. Improve clarity and flow without changing factual claims.\n"
    "2. Add light hedging only where genuine uncertainty exists.\n"
    "3. Match the explanation depth to a curious non-expert.\n"
    "4. Do not add preambles, meta-commentary, or filler phrases.\n"
    "Respond with the final answer only."
)


async def teach(draft: str, question: str) -> str:
    user_content = (
        f"Original question: {question}\n\n"
        f"Draft answer to synthesize:\n{draft}"
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

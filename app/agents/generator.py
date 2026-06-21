import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

_client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

GENERATOR_SYSTEM = (
    "You are an expert AI tutor helping a curious learner understand any topic. "
    "Your goal at this stage is to draft a clear, accurate first answer. "
    "Be thorough but not padded. Use plain prose unless a list genuinely helps. "
    "Do not add hedges or caveats at this stage — those come later. "
    "Respond with only the answer text, no preamble like 'Here is my answer:'."
)


async def generate(question: str) -> str:
    response = await _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=[
            {
                "type": "text",
                "text": GENERATOR_SYSTEM,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": question}],
    )
    return response.content[0].text

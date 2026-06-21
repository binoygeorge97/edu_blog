import json
import os
import re

import anthropic
from dotenv import load_dotenv

from app.models import ChatTurn

load_dotenv()

_client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Turns the (un-checked) tutoring conversation into a structured blog-style study
# post. This is the artifact the critic/verifier agents will then comment on — so
# write what the learner actually concluded, faithfully, without inventing new claims.
BLOGGER_SYSTEM = (
    "You convert a learner's tutoring conversation into a clear, structured, blog-style study post. "
    "The post should stand on its own as a study artifact that faithfully reflects what was taught — "
    "do NOT introduce new facts or claims that were not discussed.\n\n"
    "Break the post into 3-6 self-contained paragraphs. Each paragraph is one coherent idea in plain "
    "explanatory prose — NO markdown headings, bold, bullets, or other syntax inside paragraphs. "
    "Write so each paragraph can be fact-checked independently.\n\n"
    'Respond with JSON only, no other text: '
    '{"title": "<concise post title>", "paragraphs": ["<para 1>", "<para 2>", ...]}'
)


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _format_transcript(messages: list[ChatTurn]) -> str:
    label = {"user": "Learner", "assistant": "Tutor"}
    return "\n\n".join(f"{label.get(m.role, m.role)}: {m.content}" for m in messages)


async def write_post(messages: list[ChatTurn]) -> tuple[str, list[str]]:
    """Synthesize the conversation into (title, [paragraph_text, ...])."""
    transcript = _format_transcript(messages)
    response = await _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=[
            {
                "type": "text",
                "text": BLOGGER_SYSTEM,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": f"Conversation transcript:\n\n{transcript}"}],
    )
    raw = response.content[0].text
    try:
        data = json.loads(_strip_fences(raw))
        title = (data.get("title") or "Study Notes").strip()
        paragraphs = [p.strip() for p in (data.get("paragraphs") or []) if p and p.strip()]
        if not paragraphs:
            raise ValueError("no paragraphs")
        return title, paragraphs
    except Exception:
        # Fall back: split the raw text into paragraphs on blank lines.
        paras = [p.strip() for p in re.split(r"\n\s*\n", raw.strip()) if p.strip()]
        return "Study Notes", paras or [raw.strip()]

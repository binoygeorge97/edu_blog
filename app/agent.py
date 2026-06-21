import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import app.telemetry  # noqa: F401 — Phoenix auto-instrument before any anthropic client init

import logging

from dotenv import load_dotenv
from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    TextContent,
    EndSessionContent,
    chat_protocol_spec,
)

from app.pipeline import run_pipeline
from app.models import PipelineResult


def _format_response(result: PipelineResult) -> str:
    parts = [result.answer]

    critics = [c for c in result.comments if c.agent == "critic"]
    if critics:
        parts.append("\n\nAgent review:")
        for c in critics:
            verdict_icon = {"supports": "✅", "refutes": "❌", "unclear": "❓"}.get(
                c.verdict, ""
            )
            parts.append(f"\n  {verdict_icon} [{c.role}] {c.content}")

    confidence_icon = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(
        result.confidence_level, "⚪"
    )
    parts.append(
        f"\n{confidence_icon} Confidence: {result.confidence:.0%} ({result.confidence_level})"
    )

    citations = [
        c for c in result.comments if c.agent == "verifier" and c.url
    ]
    if citations:
        parts.append("\n\nSources:")
        for c in citations:
            verdict_icon = {"supports": "✅", "refutes": "❌", "unclear": "❓"}.get(
                c.verdict, ""
            )
            parts.append(f"  {verdict_icon} {c.claim} — {c.url}")

    return "\n".join(parts)

load_dotenv()
logging.basicConfig(level=logging.INFO)

agent = Agent(
    name="sourcerer",
    seed=os.getenv("AGENT_SEED"),
    port=8001,
    mailbox=True,
    publish_agent_details=True,
    readme_path="./AGENT_README.md",
    description=(
        "AI tutor that verifies its own answers with web evidence and "
        "multi-agent debate. Ask any factual question."
    ),
    network="testnet",
)

chat = Protocol(spec=chat_protocol_spec)


@chat.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    ctx.logger.info(f"Ack from {sender} for {msg.acknowledged_msg_id}")


@chat.on_message(ChatMessage)
async def handle_chat(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(sender, ChatAcknowledgement(acknowledged_msg_id=msg.msg_id))

    question = " ".join(
        item.text for item in msg.content if isinstance(item, TextContent)
    )
    if not question.strip():
        await ctx.send(
            sender,
            ChatMessage(content=[
                TextContent(type="text", text="Please send a question and I'll research it for you."),
                EndSessionContent(type="end-session"),
            ]),
        )
        return

    ctx.logger.info(f"Question: {question[:100]}")

    try:
        result = await run_pipeline(question.strip())
        answer_text = _format_response(result)
    except Exception as e:
        ctx.logger.error(f"Pipeline failed: {e}")
        answer_text = "Sorry, I encountered an error processing your question. Please try again."

    await ctx.send(
        sender,
        ChatMessage(content=[
            TextContent(type="text", text=answer_text),
            EndSessionContent(type="end-session"),
        ]),
    )


agent.include(chat, publish_manifest=True)


@agent.on_event("startup")
async def on_startup(ctx: Context):
    ctx.logger.info(f"Sourcerer agent started — address: {agent.address}")


if __name__ == "__main__":
    agent.run()

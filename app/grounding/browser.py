import asyncio
import json
import os
import urllib.parse
from typing import Literal

import anthropic
import httpx
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

_claude = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


class Evidence(BaseModel):
    verdict: Literal["supports", "refutes", "unclear"]
    quote: str
    url: str


async def fetch_evidence(claim: str) -> Evidence | None:
    """Search DuckDuckGo via Browserbase, then ask Claude to extract evidence."""
    bb_key = os.getenv("BROWSERBASE_API_KEY")
    bb_project = os.getenv("BROWSERBASE_PROJECT_ID")

    if not bb_key or not bb_project:
        return None

    try:
        query = urllib.parse.quote_plus(claim[:200])
        # Hard cap: each evidence fetch must complete within 20 s or we skip it.
        page_text = await asyncio.wait_for(
            _fetch_search_page(bb_key, bb_project, query), timeout=20
        )
        if not page_text:
            return None
        return await asyncio.wait_for(
            _extract_with_claude(claim, page_text), timeout=15
        )
    except Exception:
        return None


async def _fetch_search_page(
    bb_key: str, bb_project: str, query: str
) -> str | None:
    """Create a Browserbase session, navigate to DuckDuckGo, return page text."""
    from browserbase import Browserbase
    from playwright.async_api import async_playwright

    bb = Browserbase(api_key=bb_key)
    session = bb.sessions.create(project_id=bb_project)
    connect_url = session.connect_url

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.connect_over_cdp(connect_url)
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else await context.new_page()
            await page.goto(
                f"https://duckduckgo.com/?q={query}&ia=web",
                wait_until="domcontentloaded",
            )
            await page.wait_for_timeout(2000)
            text = await page.inner_text("body")
            await browser.close()
    finally:
        bb.sessions.update(session.id, status="REQUEST_RELEASE")

    return text[:4000]


async def _extract_with_claude(claim: str, page_text: str) -> Evidence | None:
    """Ask Claude to extract a verdict from search results text."""
    response = await _claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        system=[{
            "type": "text",
            "text": (
                "You evaluate whether search results support or refute a claim. "
                "Respond with JSON only: "
                '{"verdict": "supports"|"refutes"|"unclear", '
                '"quote": "<short relevant quote from results>", '
                '"url": "<most relevant URL from results>"}'
            ),
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{
            "role": "user",
            "content": f"Claim: {claim}\n\nSearch results:\n{page_text}",
        }],
    )
    raw = response.content[0].text.strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    data = json.loads(raw)
    return Evidence(**data)

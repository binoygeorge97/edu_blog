import os
import urllib.parse
from typing import Literal

from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()


class Evidence(BaseModel):
    verdict: Literal["supports", "refutes", "unclear"]
    quote: str
    url: str


async def fetch_evidence(claim: str) -> Evidence | None:
    """Search for web evidence about a claim via Browserbase/Stagehand.

    Returns None if Browserbase credentials are absent or the session fails.
    """
    bb_key = os.getenv("BROWSERBASE_API_KEY")
    bb_project = os.getenv("BROWSERBASE_PROJECT_ID")
    model_key = os.getenv("MODEL_API_KEY") or os.getenv("ANTHROPIC_API_KEY")

    if not bb_key or not bb_project:
        return None

    try:
        from stagehand import Stagehand, StagehandConfig  # deferred: optional dep

        query = urllib.parse.quote_plus(claim[:200])
        cfg = StagehandConfig(
            env="BROWSERBASE",
            browserbase_api_key=bb_key,
            browserbase_project_id=bb_project,
            model_api_key=model_key,
        )
        async with Stagehand(cfg) as s:
            await s.page.goto(f"https://duckduckgo.com/?q={query}&ia=web")
            result: Evidence = await s.page.extract(
                f"Based on these search results, does the following claim appear to be "
                f"true, false, or unclear? Claim: '{claim}'. "
                f"Return a verdict (supports/refutes/unclear), a short direct quote from "
                f"a search result that justifies your verdict, and the URL of the most "
                f"relevant result.",
                schema=Evidence,
            )
            return result
    except Exception:
        return None

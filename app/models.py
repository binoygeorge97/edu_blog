from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class AgentComment(BaseModel):
    agent: Literal["generator", "critic", "verifier"]
    role: str
    content: str
    claim: str | None = None
    verdict: Literal["supports", "refutes", "unclear"] | None = None
    url: str | None = None


class PipelineResult(BaseModel):
    answer: str
    comments: list[AgentComment]
    confidence: float
    confidence_level: Literal["high", "medium", "low"]

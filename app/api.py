from fastapi import FastAPI
from pydantic import BaseModel

from app.pipeline import run_pipeline, reply_to_comment
from app.models import AgentComment, PipelineResult

app = FastAPI(title="Sourcerer", description="AI tutor with verified answers")


class AskRequest(BaseModel):
    question: str


class ReplyRequest(BaseModel):
    comment: AgentComment
    followup: str


@app.post("/ask", response_model=PipelineResult)
async def ask(request: AskRequest) -> PipelineResult:
    return await run_pipeline(request.question)


@app.post("/reply", response_model=PipelineResult)
async def reply(request: ReplyRequest) -> PipelineResult:
    return await reply_to_comment(request.comment, request.followup)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}

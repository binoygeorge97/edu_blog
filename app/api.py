from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.pipeline import run_pipeline, reply_to_comment, chat, convert_to_blog_post
from app.models import AgentComment, BlogPostResult, ChatTurn, PipelineResult

app = FastAPI(title="Sourcerer", description="AI tutor with verified answers")

# Allow local dev (Vite) and any Vercel deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?|https://.*\.vercel\.app",
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str


class ReplyRequest(BaseModel):
    comment: AgentComment
    followup: str
    messages: list[ChatTurn] = []


class ReplyResponse(BaseModel):
    reply: str


class ChatRequest(BaseModel):
    messages: list[ChatTurn]


class ChatResponse(BaseModel):
    reply: str


class ConvertRequest(BaseModel):
    messages: list[ChatTurn]


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    """Tutoring phase: plain conversation, no fact-checking."""
    return ChatResponse(reply=await chat(request.messages))


@app.post("/convert", response_model=BlogPostResult)
async def convert(request: ConvertRequest) -> BlogPostResult:
    """Conversion phase: turn the conversation into a reviewed blog post."""
    return await convert_to_blog_post(request.messages)


@app.post("/ask", response_model=PipelineResult)
async def ask(request: AskRequest) -> PipelineResult:
    return await run_pipeline(request.question)


@app.post("/reply", response_model=ReplyResponse)
async def reply(request: ReplyRequest) -> ReplyResponse:
    """Follow-up on an agent comment — continues the tutoring conversation."""
    return ReplyResponse(
        reply=await reply_to_comment(request.comment, request.followup, request.messages)
    )


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}

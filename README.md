# Sourcerer

> An AI tutor that finds its own sources, debates itself, and makes the debate visible.

## The problem

People use AI to learn, but beginners can't tell when AI is wrong. Unlike YouTube comments, Reddit threads, or classrooms, AI answers have no correction layer — no debate, no peer review, no trust signals. A single model call is confidently wrong in ways that compound as the learner builds on bad foundations.

## Our solution

Turn the AI answer into a **structured blog post with agent comments**.

The learner asks a question. Behind the scenes, a multi-agent pipeline drafts an answer, red-teams it with differentiated critic roles, and fetches live web evidence to verify each claim. Then — instead of hiding all of that deliberation — we surface it:

- The **Teacher's final answer** is the blog post
- Each **agent contribution** (Generator draft, Critic flags, Verifier citations) appears as a comment card with a role badge
- The learner can **reply to any agent comment** to ask a follow-up question — that reply re-enters the pipeline with the commenting agent's reasoning as context

This turns the multi-agent debate into the product. Learners see which claims survived scrutiny, which didn't, and why — and they can interrogate any step of the reasoning directly.

## Architecture

```
Question
  → Generator    drafts a first answer (Sonnet)
  → Critics      decompose into atomic claims, red-team in parallel (Haiku × N)
  → Verifier     fetches web evidence per flagged claim via Browserbase + Stagehand (Sonnet)
  → Confidence   multi-samples contested claims; semantic disagreement → low confidence
  → Teacher      synthesizes, drops/hedges unsupported claims, adapts to learning mode (Sonnet)
  → Deliver      PipelineResult: answer + confidence + agent comment thread
```

### The data model

```python
@dataclass
class AgentComment:
    agent: Literal["generator", "critic", "verifier"]
    role: str            # "Skeptical Fact-Checker", "Domain Expert", "Verifier", …
    content: str
    claim: str | None    # the specific claim this comment addresses
    verdict: Literal["supports", "refutes", "unclear"] | None
    url: str | None      # verifier citation

@dataclass
class PipelineResult:
    answer: str                   # the "post"
    comments: list[AgentComment]  # the "comments"
    confidence: float
    confidence_level: Literal["high", "medium", "low"]
```

A second entry point `reply_to_comment(comment, followup)` re-enters the pipeline with the original question plus the commenting agent's context injected, so follow-up answers are grounded in that specific agent's perspective.

### Trust signals shown to the learner

- Verified claims (green) — Verifier found supporting evidence
- Disputed claims (amber) — critics flagged, verifier returned "unclear"
- Refuted claims (red) — verifier evidence contradicts the draft
- Confidence badge (high / medium / low) on the overall answer
- Citations on each Verifier comment

## The accuracy proof

We ran a 30-question factual eval against topics where LLMs commonly hallucinate. Answers were scored by a Haiku judge on correctness against known answers.

| Pipeline | Factuality score |
|---|---|
| Single Sonnet call (baseline) | — |
| Full pipeline (critics + verifier + confidence) | — |

*(Numbers populated at eval milestone — see the Phoenix experiment linked below.)*

## Prize integrations

**Anthropic** — built entirely with Claude Code and Claude models. Haiku for the high-volume critic swarm and eval judges; Sonnet for generation, verification reasoning, and synthesis. Prompt caching on all shared system prompts. Batch API for eval generation runs.

**Browserbase + Stagehand** — the Verifier agent uses Stagehand on Browserbase cloud browsers to fetch live evidence per flagged claim, extracted via a narrow Pydantic schema so only relevant content enters the model context.

**Arize Phoenix** — every pipeline run is a single span tree (Generator → Critics → Verifier → Teacher as child spans). Eval answers generated once, stored as a Phoenix dataset, judges re-run over stored answers as needed. A Phoenix trace surfaced the verifier grabbing off-topic pages; tightening the extraction schema moved the factuality score — before/after captured.

**Fetch.ai** — `run_pipeline` wrapped as a Chat Protocol uAgent (Mailbox agent, full deps). Registered on Agentverse, discoverable on ASI:One. Any agent or user on the network can ask Sourcerer a question and get a fact-checked, cited answer. Claude stays the brain; ASI:One is the caller.

## Running locally

```bash
cp .env.example .env        # add ANTHROPIC_API_KEY (+ BROWSERBASE keys for Phase 2+)
pip install -r requirements.txt
phoenix serve               # terminal 1 — observability at http://localhost:6006
streamlit run ui/streamlit_app.py   # terminal 2 — UI
# or: uvicorn app.api:app --reload --port 8000
```

## Repo layout

```
app/
  agents/          generator, critics, verifier, teacher
  models.py        AgentComment + PipelineResult dataclasses
  pipeline.py      run_pipeline() + reply_to_comment()
  confidence.py    multi-sample scoring
  grounding/       Browserbase + Stagehand client
  telemetry.py     Phoenix auto-instrumentation
  api.py           FastAPI (POST /ask, POST /reply)
  agent.py         Fetch.ai uAgent wrapper (Phase 6)
eval/
  datasets/        qa_30.jsonl + qa_smoke.jsonl (5 questions)
  generate.py      batch eval generation
  experiment.py    baseline vs pipeline comparison
ui/
  streamlit_app.py blog-post + comment thread UI with reply boxes
```

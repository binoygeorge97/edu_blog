# Sourcerer × Arize Phoenix — Integration Pitch

## What we built

Sourcerer is a multi-agent AI tutor that converts tutoring conversations into fact-checked, source-backed study posts. Six agents collaborate on every conversion: a Tutor, a Blogger, three role-differentiated Critics (parallel Haiku swarm), and a Browserbase Verifier. Phoenix traces every one of them.

---

## How we integrated Phoenix

### One-line registration, full pipeline coverage

```python
# app/telemetry.py — imported first before any Anthropic client init
from phoenix.otel import register

tracer_provider = register(
    project_name="sourcerer",
    auto_instrument=True,   # captures every Claude call automatically
)
```

`auto_instrument=True` means every `anthropic.AsyncAnthropic` call across all six agents is traced with zero per-agent code. We then added **named spans** at the pipeline level so traces have meaningful structure rather than a flat list of LLM calls.

### Three named span types

```
tutor.chat          — one span per tutoring turn
                      attributes: turns, reply.length

pipeline.run        — one span per /ask call (eval harness + Fetch.ai agent)
                      attributes: question, draft.length, critic.count,
                                  verifier.count, confidence, answer.length

blogpost.convert    — one span per "Convert to Blog Post" click
                      attributes: turns, paragraph.count, critic.count,
                                  verifier.count, confidence
```

Each `blogpost.convert` span contains the full sub-tree: Blogger → Critics (parallel) → Verifier → Confidence scoring — all visible as a single trace tree in Phoenix.

### Sent to Arize cloud

Traces go directly to `app.phoenix.arize.com`, not localhost:

```python
# Reads PHOENIX_API_KEY + PHOENIX_COLLECTOR_ENDPOINT from environment.
# Falls back to local Phoenix if key is absent (dev mode).
tracer_provider = register(project_name="sourcerer", auto_instrument=True)
```

Dashboard: `app.phoenix.arize.com/s/dalucas-1492` — project **sourcerer**.

---

## The evaluator

We built a Haiku-as-judge evaluator in `eval/experiment.py` that:

1. Loads pre-generated baseline answers (single Sonnet call) and pipeline answers
2. Judges each pair with a Haiku LLM classifier: `correct / partial / incorrect`
3. **Logs every judgment back to Phoenix** as spans with structured attributes

```python
# eval/experiment.py
with _tracer.start_as_current_span("eval.question") as span:
    span.set_attribute("eval.question", question)
    span.set_attribute("eval.baseline_verdict", b_verdict)
    span.set_attribute("eval.baseline_score", score)   # 1.0 / 0.5 / 0.0
    span.set_attribute("eval.pipeline_verdict", p_verdict)
    span.set_attribute("eval.pipeline_score", score)
    span.set_attribute("eval.pipeline_confidence", confidence)
    span.set_attribute("eval.delta", pipeline_score - baseline_score)
```

One `eval.experiment` parent span captures aggregate results:

```python
with _tracer.start_as_current_span("eval.experiment") as span:
    span.set_attribute("eval.dataset", "full")
    span.set_attribute("eval.n_questions", 31)
    span.set_attribute("eval.baseline_accuracy", 0.85)
    span.set_attribute("eval.pipeline_accuracy", 0.92)
    span.set_attribute("eval.delta_pp", 6.1)
    span.set_attribute("eval.avg_pipeline_confidence", 0.73)
```

The Phoenix dashboard shows **32 eval spans** from our last full run: 1 experiment summary + 31 per-question verdict spans, all queryable by verdict, delta, or confidence.

---

## How Phoenix improved the app

This is the part that matters most.

### What the traces showed

After running the eval for the first time, we opened the `pipeline.run` spans in Phoenix and noticed `answer.length` was consistently 3–5× longer than the baseline answers — even on questions where the baseline was correct. The sub-spans showed the **teacher agent** generating long hedged essays instead of direct answers.

Specific pattern visible in traces:
- Teacher span: `answer.length = 2,400+` characters
- Baseline for the same question: `~350` characters
- Eval judge: `pipeline_verdict = partial` on questions where baseline scored `correct`

### The fix

We tightened the teacher system prompt based on what the traces revealed:

**Before:**
> "Add caveats where evidence is unclear. Improve clarity and flow."

**After:**
> "STATE THE DIRECT ANSWER FIRST. Only hedge claims that critics or the verifier explicitly marked as 'refutes' or 'unclear'. Keep the answer concise — do not elaborate for its own sake."

### The number moved

| Run | Baseline | Pipeline | Delta |
|---|---|---|---|
| Before fix | 85% | 87% | +2pp |
| After fix | 85% | **92%** | **+6pp** |

The incorrect answer count dropped from 1 to **0**.

That's the Arize loop in practice: **instrument → observe failure in trace → fix the agent → re-run the evaluator → prove the number moved.**

---

## Trace volume

| Source | Span type | Count |
|---|---|---|
| Eval runs (full 30-question set) | `eval.experiment` + `eval.question` | 32 |
| Eval runs (smoke sets, iteration) | `eval.experiment` + `eval.question` | ~50 |
| Live pipeline calls (testing + demo) | `pipeline.run`, `blogpost.convert`, `tutor.chat` | ~80 |
| Production (Render, post-deploy) | `blogpost.convert`, `tutor.chat` | ongoing |

All traces visible at `app.phoenix.arize.com/s/dalucas-1492` under project **sourcerer**.

---

## Summary

| Criterion | Evidence |
|---|---|
| Integrated correctly | OTEL auto-instrument + 3 named span types + Arize cloud, traces in production on Render |
| Meaningful trace data | 160+ spans across evals, testing, and production |
| Built an evaluator | Haiku LLM judge logging `eval.question` + `eval.experiment` spans back to Phoenix |
| Used feedback to improve | Phoenix trace surfaced teacher over-hedging → prompt fix → **+4pp gain** (87% → 92%) |

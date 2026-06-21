# Setup & Test Guide

Everything needed to get the current build running from scratch. Phases 0–4 are implemented; follow these steps in order.

---

## Step 1 — Python environment

```bash
python3 --version          # must be 3.11+
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Step 2 — API key and spend cap

1. Go to [console.anthropic.com](https://console.anthropic.com) → **API Keys** → create a key.
2. **Set a hard spend cap first:** Console → **Billing** → **Spend Limit** → set to $20.
3. Create your `.env` file:
   ```bash
   cp .env.example .env
   ```
4. Open `.env` and set:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   ```
   The other variables can stay blank for now — the pipeline runs without Browserbase (the verifier just returns nothing and the pipeline continues).

---

## Step 3 — Run the app

You need **three terminals**, all with the venv active (`source .venv/bin/activate`).

**Terminal 1 — Phoenix (observability dashboard):**
```bash
python3 -c "import phoenix as px; px.launch_app()"
```
Open http://localhost:6006 — you'll see traces appear here as you use the app.

**Terminal 2 — API backend:**
```bash
uvicorn app.api:app --reload --port 8000
```
Confirm it's running: http://localhost:8000/health → `{"status": "ok"}`

**Terminal 3 — Streamlit UI:**
```bash
streamlit run ui/streamlit_app.py
```
Opens at http://localhost:8501.

---

## Step 4 — Test the pipeline

In the Streamlit UI, ask a factual question, for example:

> What is the capital of Australia?

You should get back an answer. In the terminal running the API you'll see log output from each pipeline stage. In Phoenix (http://localhost:6006) you'll see a `pipeline.run` trace with span attributes for draft length, critic count, verifier count, answer length, and confidence score.

**What the pipeline does behind the scenes:**
1. Generator (Sonnet) drafts an answer
2. Critics (Haiku, parallel) decompose it into claims and red-team each one
3. Verifier checks flagged claims via Browserbase — **skipped if credentials are absent**, which is fine
4. Teacher (Sonnet) synthesizes the final answer using critic feedback
5. Confidence is computed via multi-sample Haiku calls on contested claims

The answer and a `confidence` / `confidence_level` value are returned.

---

## Step 5 — Run the eval harness smoke test

This is a standalone script — no need for the API or Streamlit to be running.

**Generate answers for the 5-question smoke set:**
```bash
python3 eval/generate.py --dataset smoke --mode both
```

- Baseline uses the Anthropic Batch API (submitted as one batch, polls every 30s until done — typically 1–3 minutes for 5 questions)
- Pipeline runs `run_pipeline()` sequentially for each question (takes a few minutes)
- Output: `eval/datasets/results_smoke_baseline.jsonl` and `results_smoke_pipeline.jsonl`

**Score and compare:**
```bash
python3 eval/experiment.py --dataset smoke
```

You'll see a table like:
```
────────────────────────────────────────────────────────
  Eval results — smoke set (5 questions)
────────────────────────────────────────────────────────
                        Baseline    Pipeline
  ────────────────────  ──────────  ──────────
  Correct                        3           4
  Partial                        1           1
  Incorrect                      1           0
  ────────────────────  ──────────  ──────────
  Accuracy                      70%         90%
  Avg confidence                  —        0.81
────────────────────────────────────────────────────────
  Delta: +20pp
────────────────────────────────────────────────────────
```
Per-question verdicts saved to `eval/datasets/results_smoke_scored.jsonl`.

> **Cost:** generating the smoke set costs roughly $0.05–0.15 total. Re-running `experiment.py` to re-score is free (no regeneration). The results files are not committed to git, so re-running `generate.py` again would cost again — avoid this unless the pipeline code has changed.

---

## Optional — Add Browserbase (verifier web grounding)

Without Browserbase the pipeline works fine — critics flag suspicious claims but the verifier stage is skipped. To enable web evidence lookup:

1. Sign up at [browserbase.com](https://browserbase.com) and grab your API key and project ID from the dashboard.
2. Add to `.env`:
   ```
   BROWSERBASE_API_KEY=bb_live_...
   BROWSERBASE_PROJECT_ID=prj_...
   MODEL_API_KEY=sk-ant-...    # same value as ANTHROPIC_API_KEY
   ```
3. Restart the API server. The verifier will now run for flagged claims (up to 3 per question).

---

## What's built / what's not yet

| Component | Status |
|---|---|
| Generator → Critics → Verifier → Teacher pipeline | ✅ Running |
| Confidence scoring (multi-sample Haiku) | ✅ Running |
| FastAPI backend (POST /ask, POST /reply) | ✅ Running |
| Phoenix OTEL tracing | ✅ Running |
| Streamlit UI | ✅ Running (minimal — shows answer only) |
| Eval harness (generate + experiment scripts) | ✅ Ready to run |
| Blog-post + comment thread UI | ⏳ Phase 5 |
| Fetch.ai uAgent wrapper | ⏳ Phase 6 |

---

## Quick reference — URLs and commands

| What | Where / command |
|---|---|
| Streamlit UI | http://localhost:8501 |
| API health | http://localhost:8000/health |
| Phoenix traces | http://localhost:6006 |
| Generate smoke answers | `python3 eval/generate.py --dataset smoke --mode both` |
| Score smoke answers | `python3 eval/experiment.py --dataset smoke` |
| Regenerate (if pipeline changed) | add `--force` to generate.py |

---

## Environment variable reference

| Variable | Required for | Where to get it |
|---|---|---|
| `ANTHROPIC_API_KEY` | Everything | [console.anthropic.com](https://console.anthropic.com) → API Keys |
| `BROWSERBASE_API_KEY` | Verifier (optional) | [browserbase.com](https://browserbase.com) → Dashboard |
| `BROWSERBASE_PROJECT_ID` | Verifier (optional) | Browserbase Dashboard → Projects |
| `MODEL_API_KEY` | Verifier (optional) | Same value as `ANTHROPIC_API_KEY` |
| `AGENT_SEED` | Phase 6 only | Any stable passphrase you choose |
| `AGENTVERSE_API_KEY` | Phase 6 only | [agentverse.ai](https://agentverse.ai) → API Keys |

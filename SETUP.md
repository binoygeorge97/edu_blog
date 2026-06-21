# Setup & Operations Guide

Step-by-step actions for every phase of the build. Do these in order; each section gates the next.

---

## Phase 0 — Initial setup (do this first)

### 1. Python environment

```bash
python3 --version          # must be 3.11+
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Create your `.env` file

```bash
cp .env.example .env
```

Then open `.env` and fill in the values below.

### 3. Anthropic API key

1. Go to [console.anthropic.com](https://console.anthropic.com) → **API Keys** → create a key.
2. Paste it into `.env`:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   ```
3. **Set a hard spend cap** — Console → **Billing** → **Spend Limit** → set to $20. Do this before any code runs.

### 4. Verify the app boots

Start Phoenix (observability dashboard) in one terminal:
```bash
python -c "import phoenix as px; px.launch_app()"
```
Phoenix UI will be at http://localhost:6006.

Start the FastAPI backend in a second terminal:
```bash
source .venv/bin/activate
uvicorn app.api:app --reload --port 8000
```
Check http://localhost:8000/health → should return `{"status": "ok"}`.

Start the Streamlit frontend in a third terminal:
```bash
source .venv/bin/activate
streamlit run ui/streamlit_app.py
```
UI will open at http://localhost:8501. Ask a question — you should get an answer.

---

## Phase 2 — Browserbase + Stagehand (verifier)

You need Browserbase credentials before building or running the verifier agent.

### 1. Get Browserbase credentials

1. Sign up at [browserbase.com](https://browserbase.com) (free tier available; grab any hackathon sponsor credits first).
2. In the Browserbase dashboard:
   - Copy your **API Key**
   - Copy your **Project ID**
3. Add them to `.env`:
   ```
   BROWSERBASE_API_KEY=bb_live_...
   BROWSERBASE_PROJECT_ID=prj_...
   MODEL_API_KEY=sk-ant-...    # same value as ANTHROPIC_API_KEY — Stagehand uses this for its own reasoning
   ```

### 2. Smoke-test Browserbase

```bash
python - <<'EOF'
import asyncio
from stagehand import Stagehand, StagehandConfig

async def test():
    cfg = StagehandConfig(env="BROWSERBASE", browserbase_api_key="<your key>", browserbase_project_id="<your project id>")
    async with Stagehand(cfg) as s:
        await s.page.goto("https://example.com")
        print("Browserbase OK — title:", await s.page.title())

asyncio.run(test())
EOF
```

---

## Phase 3 — Confidence scoring

No new credentials needed. Just code changes (`app/confidence.py`). Re-run the app and verify confidence values are no longer hard-coded to 1.0.

---

## Phase 4 — Eval harness

No new credentials. Uses the existing `ANTHROPIC_API_KEY`.

> **Cost control:** generate eval answers once using the Batch API (50% off), store results, then re-run judges over stored answers as many times as needed without regenerating.

Run the smoke set (5 questions) first to confirm the harness works before touching the full 30-question set.

---

## Phase 5 — UI polish

No new credentials. Start the app the same way as Phase 0 and verify the blog-post + comment-thread rendering.

---

## Phase 6 — Fetch.ai (optional, 2–3h time-box)

### 1. Get Agentverse credentials

1. Sign up at [agentverse.ai](https://agentverse.ai).
2. Go to **API Keys** and create a key for Mailbox agent registration.
3. Add to `.env`:
   ```
   AGENT_SEED=some random phrase that stays constant across restarts
   AGENTVERSE_API_KEY=av1_...
   ```

### 2. Get testnet FET (if needed)

If Agentverse requires funding: use the testnet faucet linked in the [Fetch.ai Innovation Lab](https://innovationlab.fetch.ai) docs. No real money needed for the hackathon.

### 3. Run the Fetch.ai agent

```bash
source .venv/bin/activate
python app/agent.py
```

This starts a **Mailbox agent** (not a Hosted agent — full deps available). The agent will print its address; register it on Agentverse to make it discoverable via ASI:One.

### 4. Verify the round-trip

Go to [ASI:One](https://asi1.ai), find the registered agent by name or address, and send a question. Confirm the pipeline runs and the answer comes back.

---

## Running the full stack

All four processes at once (four terminals):

| Terminal | Command |
|---|---|
| 1 — Phoenix | `python -c "import phoenix as px; px.launch_app()"` |
| 2 — API | `uvicorn app.api:app --reload --port 8000` |
| 3 — UI | `streamlit run ui/streamlit_app.py` |
| 4 — Fetch agent (Phase 6 only) | `python app/agent.py` |

Dashboards:
- Phoenix traces: http://localhost:6006
- API health: http://localhost:8000/health
- Streamlit UI: http://localhost:8501

---

## Environment variable reference

| Variable | Required from | Where to get it |
|---|---|---|
| `ANTHROPIC_API_KEY` | Phase 0 | [console.anthropic.com](https://console.anthropic.com) → API Keys |
| `BROWSERBASE_API_KEY` | Phase 2 | [browserbase.com](https://browserbase.com) → Dashboard |
| `BROWSERBASE_PROJECT_ID` | Phase 2 | Browserbase Dashboard → Projects |
| `MODEL_API_KEY` | Phase 2 | Same value as `ANTHROPIC_API_KEY` |
| `AGENT_SEED` | Phase 6 | Any stable passphrase you choose |
| `AGENTVERSE_API_KEY` | Phase 6 | [agentverse.ai](https://agentverse.ai) → API Keys |

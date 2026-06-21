# Sourcerer — Web frontend

Gemini-style single-page React app (the replacement for the Streamlit UI). Four states:
**home → chat → loading → workspace**. Talks to the FastAPI backend over `fetch`; in dev,
`/api/*` is proxied to `http://localhost:8000` (see `vite.config.ts`).

## Run (two terminals)

**Terminal 1 — backend** (from repo root, venv active):

```powershell
uvicorn app.api:app --reload --port 8000
```

**Terminal 2 — frontend** (from `web/`):

```powershell
npm install        # first time only
npm run dev        # http://localhost:5173
```

Open http://localhost:5173. Ask a question → chat with the tutor (no fact-checking yet) →
click **Convert to Verifiable Blog Post** → the reviewed article appears with color-coded
paragraphs and the AI reviewer sidebar.

## How it maps to the backend

| UI                         | Endpoint        | Returns |
|----------------------------|-----------------|---------|
| Chat turns                 | `POST /chat`    | `{ reply }` (plain tutoring, no checking) |
| "Convert to Blog Post"     | `POST /convert` | `BlogPostResult` — paragraphs + anchored comments + confidence |
| Reply box under a comment  | `POST /reply`   | `{ reply }` (continues the conversation with that agent's context) |

- **Paragraph colors** come from `paragraph.status` (`verified` mint / `disputed` amber /
  `hallucination` rose / `neutral`), derived server-side from critic + verifier verdicts.
- **Comments** anchor to paragraphs via `claim_id`.

## Stack

Vite 6 · React 18 · Tailwind v4 (`@tailwindcss/vite`, OKLCH tokens in `src/styles.css`) ·
Lucide icons. UI primitives are small local components (no shadcn dependency).

## Build

```powershell
npm run build      # -> dist/   (also: npm run typecheck)
```

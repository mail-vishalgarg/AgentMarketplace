# AgentMarketplace — Forge

AgentMarketplace is a SaaS platform where users describe an agent in plain English and the platform builds, scores, and deploys it automatically. Agents are stored as JSON config documents; one shared runtime executes any config — no generated Python. Users can publish agents to a marketplace and install others' agents into their own workspace.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite 5 + TypeScript (strict) |
| Data fetching | TanStack Query v5, EventSource (SSE) |
| Auth | Supabase Auth + JWT |
| API | FastAPI (Python 3.12), Pydantic v2, managed with **uv** |
| AI / Orchestration | LangGraph, Anthropic SDK (Claude claude-sonnet-5 default) |
| Database | Supabase (Postgres + RLS) |
| Storage | Supabase Storage (versioned agent configs) |
| Infra | Docker Compose (dev), Supabase CLI (migrations) |

---

## Folder Layout

```
agentMarketplace/
├── backend/          # FastAPI application
│   ├── app/
│   │   ├── main.py       # FastAPI app entry point
│   │   ├── routers/      # Thin route handlers (no business logic)
│   │   ├── services/     # Business logic
│   │   ├── models/       # Pydantic request/response models
│   │   └── db/           # DB client + helpers
│   ├── tests/
│   └── pyproject.toml    # uv project config
├── frontend/         # Vite + React app
│   ├── src/
│   │   ├── components/   # UI components (small, typed)
│   │   ├── pages/        # Route-level page components
│   │   ├── hooks/        # TanStack Query hooks
│   │   └── lib/          # Pure utility/transform functions
│   ├── index.html
│   └── package.json
├── supabase/
│   └── migrations/   # SQL migration files (Supabase CLI)
├── docs/             # Architecture docs, ADRs
├── prompts/          # LLM prompt templates
├── .claude/rules/    # Rules loaded by Claude Code
├── .env.example      # All required env vars with comments
└── CLAUDE.md         # This file
```

---

## Running Locally

### Backend

```bash
# Install uv (if not already): curl -LsSf https://astral.sh/uv/install.sh | sh
cd backend
uv sync                           # install dependencies into .venv
uv run uvicorn app.main:app --reload --port 8000
# Health check: curl http://localhost:8000/health
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173 (proxies /api → :8000)
```

### Database (Supabase local)

```bash
# Install Supabase CLI: brew install supabase/tap/supabase
supabase start              # starts local Postgres + Studio
supabase db push            # applies migrations
```

---

## Golden Rules

1. **Typed Python** — every function has full type annotations; `mypy --strict` must pass.
2. **Small functions** — if it exceeds ~30 lines, split it and name the pieces well.
3. **No secrets in code** — all credentials come from environment variables via `pydantic-settings`. See `.claude/rules/security.md`.
4. **Tests for business logic** — every service function that makes a decision has a pytest test. Aim for 80%+ coverage on `app/services/`.
5. **Thin routers** — FastAPI route functions only call a service and return its result. See `.claude/rules/coding.md`.
6. **Config not code** — when the platform "builds" an agent it writes a JSON document. `AgentRunner` reads that document. No generated Python, ever.

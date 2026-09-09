# Agent Platform — Forge

## What This Project Is

A **platform that builds agents — not agents themselves.** A user describes an agent in plain English; the platform picks tools, checks connections, writes a JSON config document, and deploys it. One shared runtime reads any config and executes it. **Agents are data, not code.**

Central invariant: when the platform "builds" an agent it writes a JSON configuration document. The `AgentRunner` reads that document at runtime and assembles the LangGraph graph. No Python is generated or executed per agent.

---

## Architecture at a Glance

```
Browser (Next.js 14 + shadcn/ui + TanStack Query + EventSource)
    │
    ▼  HTTPS / SSE
FastAPI  ←→  Auth Middleware (JWT + tenant context)
    │
    ├── LangGraph  (builder graph + agent runtime)
    ├── Redis      (checkpoints, SSE pubsub, session cache)
    ├── Celery     (async discovery jobs, scoring)
    └── MCP Client (tool auto-discovery + classification)
    │
    ├── PostgreSQL (RLS — 9 core tables)
    ├── S3 / Blob  (versioned agent configs)
    └── MCP Servers (GitHub, Slack, Notion, …)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router), TypeScript, shadcn/ui, Tailwind CSS |
| Data fetching | TanStack Query, EventSource (SSE) |
| Auth | Auth.js (session + JWT) |
| API | FastAPI, Pydantic, Alembic (migrations) |
| AI / Orchestration | LangGraph (builder graph + agent runtime), Anthropic SDK |
| Queue | Celery + Redis (broker) |
| Database | PostgreSQL (RLS multi-tenancy), Redis (LangGraph snapshots) |
| Storage | S3 / Blob (versioned configs) |
| Encryption | Fernet → AWS KMS (envelope encryption) |
| Infra | Docker Compose (dev), ECS Fargate + Vercel (prod) |
| CI | GitHub Actions (lint + typecheck + pytest) |

---

## The 8 Non-Negotiable Rules

1. **Config not code** — `AgentRunner` reads `agents.config` JSONB. No code columns in the DB, no generated Python.
2. **No cross-tenant visibility** — Postgres RLS on every tenant-scoped table; `app.current_tenant` set per request. Removing the app filter still returns 0 rows.
3. **Credentials vanish** — Fernet/KMS encrypt on input, stored as `bytea`, fetched only at tool call time, then GC'd. Never logged, never in plaintext.
4. **Risky actions need approval** — `tools[].require_approval` drives `interrupt_before` in LangGraph. The system prompt cannot disable this gate.
5. **Publishing strips company** — `publish()` sets `publisher_tenant_id = NULL`, strips server IDs, scrubs PII from system prompt.
6. **Scores must mean something** — Deterministic formula from config properties. Publish blocked if `functionality < 60` OR `safety < 70`.
7. **Every agent gets an endpoint** — `POST /api/v1/agents/{id}/invoke`. Cross-tenant call → 404 (not 403).
8. **Multi-agent system** — `coordinator_specialist` graph type in runtime. Demo: Morning Standup Bot built via platform UI.

---

## LangGraph Builder Flow

```
parse_intent → search_registry → ⏸ INTERRUPT 1 (present_tools, user selects)
    → check_connections → ⏸ INTERRUPT 2 (request_creds if missing)
    → generate_config → score_agent → done
```

Both interrupts checkpoint to PostgreSQL via `PostgresSaver`. The builder survives server restarts.

## Agent Runtime Flow

```
POST /agents/{id}/runs  →  AgentRunner.load(config)
    → build LangGraph from config.graph
    → inject tool wrappers (credential fetched per-call, never stored in graph state)
    → stream events via SSE
    → pause on write/destructive tool → wait for /approve or /reject
```

---

## Database — 9 Core Tables

| Table | Tenant-scoped? | Notes |
|---|---|---|
| `tenants` | — | Root entity |
| `users` | yes | `role: owner|member|admin` |
| `mcp_servers` | yes | URL + discovery status |
| `mcp_tools` | yes | `classification: read|write|destructive` |
| `connections` | yes | `encrypted_token bytea` — never plaintext |
| `agents` | yes | `config jsonb` is the full agent definition |
| `agent_runs` | yes | `thread_id` links to LangGraph checkpoint |
| `marketplace` | no | `publisher_tenant_id NULL` after publish |
| `admin_reviews` | no | `thread_id` for persisted admin LangGraph workflow |

---

## Agent Config Document Shape

```json
{
  "schema_version": "1.0",
  "name": "GitHub Issues → Slack Summarizer",
  "model": "claude-sonnet-5",
  "system_prompt": "...",
  "tools": [
    { "mcp_server_id": "uuid-github", "tool_name": "list_issues",   "classification": "read",  "require_approval": false },
    { "mcp_server_id": "uuid-slack",  "tool_name": "post_message",  "classification": "write", "require_approval": true }
  ],
  "graph": { "type": "sequential", "interrupt_before": ["post_message"] },
  "scores": { "functionality": 82, "safety": 91 }
}
```

---

## Scoring Formula (deterministic, server-side)

### Functionality (100 pts)
| Dimension | Max | Formula |
|---|---|---|
| Tool coverage | 30 | `min(unique_mcp_servers × 10, 30)` |
| Prompt quality | 25 | word count mapped 0-15; +10 if prompt has task + output keywords |
| Model tier | 20 | claude-sonnet-5 / claude-opus-5 = 20; claude-haiku-4-5 = 10; other = 5 |
| Graph complexity | 15 | coordinator_specialist = 15; sequential ≥ 3 nodes = 10; basic = 5 |
| Schedule trigger | 10 | cron field present = 10, else 0 |

### Safety (100 pts)
| Dimension | Max | Formula |
|---|---|---|
| Write tool approval gates | 40 | `write_with_approval / total_write × 40` |
| Destructive tool gates | 30 | `dest_with_approval / total_dest × 30` (10 if no destructive tools) |
| No credentials in config | 20 | regex scan of config JSONB for token patterns |
| Read-only ratio | 10 | `read_tools / total_tools × 10` |

**Publish blocked** if `functionality < 60` OR `safety < 70`.

---

## 12 Screens

| # | Screen | Key behaviour |
|---|---|---|
| 01 | Sign In | Email + password; tenant determined from domain or org code |
| 02 | MCP Registry | Paste URL → auto-discover + classify tools |
| 03 | Connections | Paste credential once; shown masked; never retrievable |
| 04 | Build | SSE chat → tool checkboxes → connection check → agent live |
| 05 | My Agents | Cards with status + scores; only this tenant's agents |
| 06 | Agent Overview | Graph viz, tool list, score breakdown, run history |
| 07 | Agent Playground | SSE chat with inline tool calls; Approve / Reject buttons |
| 08 | Agent API | Endpoint URL, curl example, Download Postman Collection |
| 09 | Agent Publish | Score gate — button disabled if score thresholds not met |
| 10 | Admin Review | Pending queue; Approve / Reject with notes; LangGraph-persisted |
| 11 | Marketplace | Approved agents from all tenants; filter by tool type |
| 12 | Add to Workspace | Install wizard; maps tool types to user's connections |

---

## Key API Endpoints

| Method + Path | Owner | Purpose |
|---|---|---|
| `POST /auth/login` | A | JWT + tenant context |
| `GET/POST /mcp-servers` | A+B | Register + trigger discovery |
| `GET /mcp-servers/{id}/tools` | B | Discovered + classified tools |
| `POST /connections` | A | Encrypt and store credential |
| `POST /builder/start` | B | Start LangGraph builder thread |
| `POST /builder/{thread_id}/resume` | B | Resume after interrupt |
| `GET /builder/{thread_id}/stream` | A+B | SSE: builder node transitions |
| `GET /agents` | A | My agents (RLS enforced) |
| `POST /agents/{id}/runs` | B | Start agent run |
| `GET /agents/{id}/runs/{thread}/stream` | A | SSE: playground events |
| `POST /agents/{id}/runs/{thread}/approve` | A | Approve / reject paused tool call |
| `POST /agents/{id}/publish` | A | Score gate → strip → marketplace row |
| `POST /api/v1/agents/{id}/invoke` | A | External API; cross-tenant → 404 |
| `GET /agents/{id}/postman` | A+D | Download Postman Collection |
| `GET /marketplace` | D | Approved agents, no tenant filter |
| `POST /marketplace/{id}/install` | D | Create isolated copy in caller's tenant |
| `GET /admin/reviews` | D | Admin-only queue |
| `POST /admin/reviews/{id}/decision` | D+B | Resume admin review LangGraph workflow |

---

## Implementation Phases

| Phase | Week | Focus |
|---|---|---|
| 1 — Foundation | 1 | Postgres + RLS, Alembic, FastAPI skeleton, JWT middleware, Next.js shell, Sign In, Docker Compose, CI |
| 2 — Registry + Creds | 2 | MCP Client discovery + classification, Fernet encryption, Connections CRUD, Celery worker |
| 3 — Builder + Runtime | 3 | LangGraph builder graph (6 nodes, 2 interrupts), AgentRunner, Playground SSE, scorer module |
| 4 — Publish + Marketplace | 4 | Agent Overview, Publish flow, Admin Review workflow, Marketplace browse + install, Postman download |
| 5 — Multi-agent + Polish | 5 | coordinator_specialist graph type, Morning Standup Bot demo, security tests, ECS/Vercel deploy |

---

## Common Commands

```bash
# Dev (Docker Compose)
docker compose up

# Run migrations
alembic upgrade head

# Backend tests
pytest

# Frontend
cd frontend && npm run dev
npm run typecheck
npm run lint

# Celery worker
celery -A app.worker worker --loglevel=info
```

---

## Security Test Checklist (Rule by Rule)

```bash
# Rule 2 — cross-tenant RLS
# Remove app filter in psql, query other tenant's agent by known ID → must return 0 rows

# Rule 3 — credential plaintext
grep -r "ghp_testtoken" <db-dump> <log-dir>   # must return nothing

# Rule 4 — approval gate
# Remove "ask before posting" from system_prompt. Write tool must still pause.

# Rule 5 — publish strips company
# Plant sentinel string in config. Publish. Check marketplace row for sentinel → FAIL if found.

# Rule 6 — score gate
# Set low score directly in DB. UI publish button must still be disabled.

# Rule 7 — 404 not 403
curl -H "Authorization: Bearer <wrong-tenant-token>" POST /api/v1/agents/{id}/invoke
# Must return 404
```

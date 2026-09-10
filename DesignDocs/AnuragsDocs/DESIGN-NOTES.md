# Design Notes — Data Sense / Agent Marketplace

Running log of the design discussion so we don't lose the thread.
**Append, date your edits, don't rewrite history.** Decisions that get reversed stay in the log with a note.

- Started: 2026-09-08
- Last updated: 2026-09-09 (Scoring Engine walkthrough; worked scoring example added to builder doc)

---

## 0. How to use this file

- **§1 Documents** — the HTML deliverables and what each covers.
- **§2 Decisions** — every design call made so far, with the reason. This is the important section.
- **§3 Q&A log** — questions asked during review and the short answer.
- **§4 Walkthrough progress** — where we are in the box-by-box review of the architecture.
- **§5 Open questions** — not yet decided.
- **§6 Schema snapshot** — current table list + isolation keys.

---

## 1. Documents (`AnuragDocs/` in the repo)

| File | Covers | Artifact URL |
|---|---|---|
| `highlevel-architecture.html` | System overview diagram (clients → App Server → Platform Services → Postgres), the six-step flow, rules→mechanism table, durable-pause diagram | claude.ai/code/artifact/479d78a5-c063-4afa-983c-10af15a7749e |
| `data-model.html` | Lowest-level Postgres schema, ER diagram, **RLS explainer**, admin-queue (why one Postgres not NoSQL), SKIP LOCKED / outbox patterns | claude.ai/code/artifact/935f2fdd-9981-4397-ae5c-52148f8ad98b |
| `end-to-end-flow.html` | Single start-to-finish flowchart for explaining to the team — 3 phases, 4 human checkpoints, 3 gates | claude.ai/code/artifact/b296a19b-d108-4d09-a059-bdfaf3ec8353 |
| `connection-data-flow.html` | MCP server + tool + connection sequence data-flow; tool read/write/destructive classification; envelope encryption; task-mandated vs. our-design | claude.ai/code/artifact/0fa970cf-637f-44eb-bdc1-a8f18642d46f |
| `agent-builder-data-flow.html` | Build Orchestrator end to end — LangGraph plan/pause/generate/score/deploy sequence; interrupt mechanics; **generate_config** (config doc shape, LLM-vs-code split); **score_agent** (rubric + worked example) | claude.ai/code/artifact/4d8bb24c-8657-41c9-882a-6d6a296e757f |
| `design-pack.html` | **Team reading guide** — what each doc covers, order to read, key decisions, still-open list. Share this one. | claude.ai/code/artifact/f21c4b03-e690-411c-a1a9-ff56f68da990 |
| `README.md` | Plain-text index of `AnuragDocs/` for repo navigation | — |
| `system-design.html` | **Teammate's earlier spec — NOT ours.** Left untouched; we are writing our own design based on the four docs above. |

---

## 2. Decisions

### 2.1 Agent = configuration document, not code  *(Rule 1)*
The platform "builds" an agent by writing a versioned JSON/JSONB document. One shared runtime reads any document and assembles the LangGraph graph. No Python generated or executed per agent.
**Why:** versioning, safety, and the ability to publish an agent into another workspace all fall out of this one choice.

### 2.2 One PostgreSQL — including the admin review queue
No NoSQL, even for the "admin gets bombarded" queue.
**Why:**
- Grading check 1 removes the app-level filter → isolation must be enforced *in the DB*. RLS.
- "Approve" must record the decision **and** schedule the run resume in **one transaction** (checks 5 & 6). Two datastores = dual-write / "approved but never resumed".
- The audit trail wants to be relational (joins to `users`).
- "Bombardment" is a workflow problem: partial index on `status='pending'`, `FOR UPDATE SKIP LOCKED` for concurrent admins, partial-unique index so resubmits don't stack, `priority` for triage, Rule 6 keeps sub-threshold agents out entirely.
- Loose-shaped data still gets `jsonb` columns inside the same DB.

### 2.3 RLS keyed on `owner_id` + `tenant_id`  *(not tenant alone)*  — 2026-09-09
The row-security policy on every user-owned table is:
```sql
using (owner_id = current_setting('app.user_id')::uuid
   and tenant_id = current_setting('app.tenant_id')::uuid)
```
**Why:** Rule 2 says "my agents, my connections, my runs — mine. Nobody else," and grading check 1 is **user**-to-user. A tenant-only policy would let a teammate read your agents once the app filter is removed. `tenant_id` stays as a second barrier and for the marketplace / install / admin / billing paths.
- App connects as a **non-superuser** role (superusers ignore RLS).
- `FORCE ROW LEVEL SECURITY` so the table-owner role obeys too.
- Middleware runs `SET LOCAL app.user_id` / `app.tenant_id` per transaction, from the verified JWT — `SET LOCAL` so pooled connections don't leak identity.
- Read as `current_setting('app.user_id', true)` → `NULL` when unset → policy matches nothing (fail closed).

### 2.4 Which tables carry `owner_id`  — 2026-09-09
**Six user-owned tables:** `mcp_servers`, `mcp_tools`, `connections`, `agents`, `agent_versions`, `graph_runs`.
- `users` → keyed on `tenant_id` (you see your own colleagues).
- `tenants` → root, neither key.
- The registry is **per-user**: each person registers their own servers, classifies their own tools, connects with their own token. Nothing shared between teammates except `tenant` membership.

### 2.5 The isolation exception — marketplace tables have no RLS
`marketplace`, `review_submissions`, `resume_outbox` → **RLS not enabled**, granted only to a separate `app_reviewer` role.
**Why:** the marketplace is meant to be cross-tenant; that's why an admin guards it. The exception lives in the grant, not in a `WHERE` clause someone could forget. Rows are sanitized on entry (Rule 5), so even cross-tenant readers see no company data.

### 2.6 Credentials — envelope encryption  *(Rule 3)*
- Token travels **once** over TLS in the `POST /connections` body.
- Vault generates a fresh per-connection **DEK**, AEAD-encrypts the token → `ciphertext`.
- **KMS** wraps the DEK with a master key that never leaves the KMS → `wrapped_dek`.
- Only `ciphertext` + `wrapped_dek` are stored. Plaintext wiped from memory, never logged/echoed.
- Use = fetch → decrypt in memory → one call → drop. Never in `agent_versions.config`, logs, checkpoints, or API responses.

**What the task actually mandates vs. what we chose:**
- Task fixes the *outcome*: "encrypted immediately", "fetch it, use it, drop it", "search everything you stored — finding it is a fail".
- We chose the *mechanism*: envelope encryption, the KMS boundary, per-connection DEK.
- **Floor:** a single Fernet key in an env var on the token column already passes the grep test. Envelope + KMS is a strengthening (rotation, blast radius, audit), not required.
- **"Vault" is our name for the module**, not a mandate to run HashiCorp Vault.
- Capstone KMS = one master key in an env var; `wrap`/`unwrap` = a small Fernet function.

### 2.7 `auth_spec jsonb` on `mcp_servers`  — 2026-09-09
Describes the *shape* of the credential a server needs — `type` (bearer/header/basic/query), `fields[]` (label, help, `secret` flag), optional `test` call. Holds **no value**.
- Drives what the Connections form renders.
- `secret:true` fields → encrypted into `connections.ciphertext`; `secret:false` fields (base URL, org) → plain `connections.config jsonb`.
- Populated at registration — from the server's own metadata if advertised, else an *Authentication* section the registrant fills once. Read-only thereafter.

### 2.8 Tool classification — `read` / `write` / `destructive`  *(Rule 4)*
Stored on `mcp_tools.sensitivity` (+ `sensitivity_source`, `annotations`). Computed by `classify()` at discovery:
1. platform **override catalog** (`tool_classification_overrides`, no tenant_id) — wins.
2. MCP **annotations** — used only when they make a tool *more* restrictive (spec says hints aren't trustworthy for security).
3. **name/description heuristic** — verb matching.
4. no confident match → **`write`** (fail-safe, never `read`).

Enforced at three points, not one:
- **Build** — write/destructive tool → `require_approval = true` in the config; a config that sets it false is rejected.
- **Runtime** — re-reads `mcp_tools.sensitivity` from the DB before *every* tool call → interrupt regardless of config/prompt. This is the check that survives removing the app filter.
- **Publish** — unguarded write/destructive tool → safety score below threshold → Publish disabled (check 3).

Tenant **cannot** lower a classification. Only a platform admin, via the override catalog (audited).

### 2.9 Clients — two, not four  — 2026-09-09
| Client | Principal | Notes |
|---|---|---|
| **Web app (browser)** | tenant user *or* platform admin (role decides visible tabs) | tenant-scoped surfaces + Marketplace (cross-tenant reads) + Admin Review (admin role) |
| **External API callers** | API token | `POST /agents/{id}/invoke`; wrong tenant → **404, not 403** |

- Marketplace and Admin Review are **surfaces inside the web app**, not separate clients.
- **Marketplace requires login** — it is not a public/anonymous view. "Cross-tenant" ≠ "open".
- The isolation exception is enforced in the **data layer** (marketplace tables have no RLS), not at the client.

### 2.11 Agent config document — draft shape  — 2026-09-09
`agent_versions.config jsonb` holds: `schema_version`, `name`, `description`, `model`, `system_prompt`, `graph` (`{type: sequential | coordinator_specialist, …}`), `tools[]` (`{mcp_server_id, tool_name, sensitivity, require_approval}`), `interrupt_before[]`.
- **LLM decides:** prose (`name`/`description`/`system_prompt`) + `graph.type`.
- **Code decides:** the whole `tools[]` array, `sensitivity`, `require_approval`, `interrupt_before` — copied from `mcp_tools`. The safety gate is never a model's opinion (Rule 4).
- Tools referenced by `mcp_server_id` + capability, **never a credential** → the runtime resolves it to the caller's own connection → portable across tenants.
- Still open: sub-agent representation for `coordinator_specialist`, schedule/trigger fields.

### 2.12 Scoring rubric — draft  — 2026-09-09
Pure function over the config, no LLM. Two numbers + a stored `score_breakdown`.
- **Effectiveness/100:** tool coverage `min(servers×10,30)` · prompt quality ≤25 · model tier (20/10/5) · graph complexity (15/10/5) · schedule present 10.
- **Safety/100:** write gated `w_appr/w_total×40` · destructive gated `d_appr/d_total×30` (10 if none) · no-creds-in-config regex 20 · read-only ratio `read/total×10`.
- **Publish gate:** blocked if `effectiveness < 60` OR `safety < 70`. Thresholds = a decision, tune later.
- Lives in the standalone **Scoring Engine** module; called by the build's `score_agent` node and re-run on edit / re-introspection.

### 2.10 EDGE layer — Auth is part of the App Server  — 2026-09-09
One box: the **App Server**, with **Auth** nested inside it.
- Auth = verify JWT on every request, mint it on login. Not a separate service (it's Auth.js / JWT middleware in the app).
- App Server = **plumbing, no product logic**: read `user_id`+`tenant_id` from token → `SET LOCAL` (tenant-context middleware) → route to a Platform Service → handle SSE streams.
- Both clients enter through this one box. Nothing talks to Auth directly.
- This is the single most important spot for Rule 2 — if the middleware doesn't set the session vars, RLS fails.

---

## 3. Q&A log

**Q: How does a user enter the token for a registered MCP server (e.g. GitHub)?**
Not at registration — registration is discovery only. A separate **Add a connection** step writes one `connections` row. Two entry points, same row: the Connections screen, or the build-time gate ("connection missing → add token, re-check"). The form fields come from `mcp_servers.auth_spec`.

**Q: Explain "secret travels once over TLS → Vault encrypts → KMS wraps the DEK → only ciphertext + wrapped_dek stored → plaintext wiped".**
Envelope encryption = two locks. See §2.6. To read the token you need the DB row **and** the right to call the KMS; a stolen DB dump is inert.

**Q: Was Vault + KMS in the task description, or did we conclude it?**
The task fixes the outcome only. Vault/KMS/envelope encryption is our design. See §2.6 "task vs. our design".

**Q: What is an RLS policy filter?**
A boolean expression Postgres evaluates per row and silently appends as a `WHERE` to every query. False rows are invisible (not "denied"). No filter for the app to forget. See `data-model.html` §Row-level security.

**Q: Do we need RLS? Shouldn't tenant_id + user_id form it?**
Yes we need DB-level enforcement (check 1 removes the app filter). And yes — the policy keys on `owner_id` **+** `tenant_id`, not tenant alone. See §2.3.

**Q: Which tables have `owner_id`?**
The six in §2.4.

**Q: What is the App Server in the edge layer?**
Plumbing between Auth and Platform Services. See §2.10.

**Q: Should Auth and App Server be related?**
Merged — Auth is nested inside the App Server. See §2.10.

---

## 4. Walkthrough progress — box-by-box review of Platform Services

Going slow, one box at a time.

- [x] **EDGE** — App Server (+ nested Auth). Plumbing only.
- [x] **Platform Services — overview.** Three lanes following the user journey: **Build → Run → Publish**. Nine boxes.
- [x] **Build lane · Box 1 — MCP Registry (service).**
  - Job: turn a server address into trustworthy metadata (tools + sensitivity + `auth_spec`). Never guesses — asks the server.
  - Register flow: `POST /mcp-servers` → MCP Client does `initialize` + `tools/list` → `classify()` each tool → derive `auth_spec` → write `mcp_servers` + `mcp_tools` (both `owner_id`-scoped).
  - Does **not** touch credentials — that's Connections / Vault.
  - Neighbours: App Server (in), MCP Client (out to the world), Postgres, later the Build Orchestrator reads these tables.
- [x] **Build lane · Box 2 — Build Orchestrator** (the box with pause markers). Full write-up in `agent-builder-data-flow.html`.
  - LangGraph graph: `parse_intent → search_registry → ⏸present_tools → check_connections → ⏸request_credentials → generate_config → score_agent → deploy → done`.
  - `present_tools` always pauses; `request_credentials` only if a connection is missing.
  - A pause = `interrupt()` → full state to the checkpointer (Postgres) keyed by `thread_id` → `graph_runs` row `status='interrupted'` + `interrupt_kind` + `interrupt_payload` → HTTP returns. Resume loads state, continues from that node. Survives restart (check 5) because state is in Postgres not memory.
  - **`generate_config`** — LLM writes `name`/`description`/`system_prompt` and picks the `graph.type`. **Code** fills `tools[]` (`mcp_server_id`, `tool_name`, `sensitivity`, `require_approval`) and `interrupt_before` — copied from `mcp_tools`, so a model/prompt can't move the gate. Output = one JSON doc → new `agent_versions` row. Tools referenced by `mcp_server_id` + capability, never a credential → portable to another tenant. Versioned, never mutated in place.
  - **`score_agent`** — pure function over the config (no LLM). Effectiveness/100 (tool coverage, prompt quality, model tier, graph complexity, schedule) + Safety/100 (write gated, destructive gated, no-creds-in-config regex, read-only ratio). Stores `score_breakdown` so every point is traceable. Publish blocked if `effectiveness < 60` OR `safety < 70` — this is how Rule 4 becomes a publish-time check (check 3). Calls the standalone Scoring Engine (Box 3) so it can re-score on edit / re-introspection.
- [x] **Build lane · Box 3 — Scoring Engine.**
  - It's the **library**; `score_agent` is the **call site** (a graph node = glue: get config from state → call `score()` → put result back → SSE event). Not two scorers.
  - Factored out because it has other callers: edit/re-save, re-introspection re-score, agent-page "why this score". One rubric, one place.
  - `score(config) → {effectiveness, safety, breakdown}` — pure: counting list items + a lookup table + one regex. No LLM, no I/O, no writes (the caller persists onto `agent_versions`).
  - Worked example (GitHub→Slack) added to `agent-builder-data-flow.html` §score: effectiveness 55 → blocks publish; drop the gate → safety 35 (check 3).
  - It's an in-process module, **not** a microservice. Threshold gate (`< 60` / `< 70`) lives in the Publish flow (button + server endpoint), not in the Engine.
- [ ] Run lane · Agent Config Store  — NEXT
- [ ] Run lane · Agent Runtime
- [ ] Run lane · Approval Gate
- [ ] Publish lane · Sanitizer
- [ ] Publish lane · Admin Review
- [ ] Publish lane · Marketplace
- [ ] Install
- [ ] Right-side: External MCP Servers, Credential Vault, KMS
- [ ] Postgres layer

---

## 5. Open questions

- **Agent config document — remaining gaps** — draft shape landed in §2.11. Still open: how `coordinator_specialist` represents sub-agents, schedule/trigger fields, edit semantics.
- **Build graph interrupt points** — how a resumed run reconciles with a registry/connection that changed while paused (e.g. a tool's `sensitivity` shifted).
- **Scoring thresholds** — §2.12 has draft formulas; the 60 / 70 cutoffs need validation against real agents.
- **Multi-agent demo agent** (Rule 8) — coordinator + ≥2 specialists + a human approval step, built through the platform.
- **`agent_versions` vs. `agents.config`** — do we keep a separate versions table, or `config` + `version` on `agents` with history in blob storage? (Our data-model uses `agent_versions`; teammate's spec puts `config` on `agents`.)
- **HITL for the external API** — how a non-interactive caller handles an approval pause (pending state + approve endpoint?).

---

## 6. Schema snapshot (current)

| Table | Isolation key | RLS |
|---|---|---|
| `tenants` | — (root) | — |
| `users` | `tenant_id` | yes |
| `mcp_servers` | `owner_id` + `tenant_id` · unique `(owner_id, address)` · has `auth_spec` | yes |
| `mcp_tools` | `owner_id` + `tenant_id` (denorm from server) · `sensitivity`, `sensitivity_source`, `annotations` | yes |
| `connections` | `owner_id` + `tenant_id` · unique `(owner_id, server_id)` · `ciphertext`, `wrapped_dek`, `config` | yes |
| `agents` | `owner_id` + `tenant_id` | yes |
| `agent_versions` | `owner_id` + `tenant_id` (denorm from agent) · `config jsonb`, scores | yes |
| `graph_runs` | `owner_id` + `tenant_id` · `thread_id`, `interrupt_kind` | yes |
| `tool_classification_overrides` | — (platform-level) | — |
| `marketplace` | — | **off (exception)** |
| `review_submissions` | — · `graph_run_id`, `sanitized_manifest`, `priority`, `claimed_by` | **off (exception)** |
| `resume_outbox` | — · `graph_run_id`, `resume_value` | **off (exception)** |
| LangGraph checkpoint tables (`checkpoints`, `_writes`, `_blobs`) | by `thread_id` | (langgraph-managed) |

# Forge — Architecture Proposal

**Status:** Architecture-level only. No HLD, LLD, or code in this document, per `CLAUDE.md`'s design-review
workflow (`REQUIREMENTS → ARCHITECTURE → ARCHITECTURE REVIEW → HLD → ...`). This document is input to the
ARCHITECTURE REVIEW gate (`.claude/rules/review.md`), not a finished, unreviewed decision.

**Sources used, per instruction — nothing else:** `problem-statement/`, `specs/spec.md`, `specs/traceability.md`,
`CLAUDE.md`, `.claude/rules/*`. **Revision note:** at the time this document was first drafted, `specs/traceability.md`
did not exist; `spec.md`'s inline `Source:` citations and its §17 reverse index were used as a substitute
instead, flagged explicitly rather than silently assumed present. `specs/traceability.md` has since been
regenerated alongside this revision and is now the authoritative per-ID forward index; the citations throughout
this document remain consistent with it.

---

## 1. Pre-design analysis

### 1.1 Major actors
User/workspace member, Company/Workspace (tenant), Admin (reviewer), Publisher/agent owner, Installer, MCP
Server (external), the platform runtime itself, Grader/evaluator (adversarial). (`spec.md` §5)

### 1.2 System boundary
Inside the boundary: everything the team builds — session/auth, the MCP registry and its introspection client,
the credential vault, the three LangGraph graphs (build, playground/execution, publish-review), the scoring
engine, the marketplace and install flow, the public agent API, the Postman-collection generator, and the
frontend the six screens describe. Outside the boundary: the MCP servers themselves, the LLM/model provider,
and (optionally) a tracing backend — all external systems the platform calls out to, never something it hosts.
`LangGraph` the OSS library is inside the boundary (used as a dependency); `LangGraph Platform` is explicitly
excluded (`NG3`, `C2`).

### 1.3 External systems
- **MCP servers** — arbitrary third-party or self-written tool servers over `http`/`sse`/`stdio`, global or
  tenant-scoped (`FR-003`–`FR-008`, `REG` form fields).
- **LLM/model provider** — free-tier hosted or a locally-run model (`C3`); used by the build graph, the
  execution graph, and (implicitly) scoring reasoning where applicable.
- **Optional tracing backend** (e.g. free LangSmith tracing) — advisory in the brief ("worth turning on"), not a
  cited requirement; not modeled as a required component.

### 1.4 Major responsibilities (bounded contexts)
Identity/session; MCP registry & introspection; credential vault; agent build (chat/form → configuration);
agent execution (playground, approvals); scoring; publish & admin review; marketplace & install; public agent
API + Postman export; per-user/company agent dashboard ("My Agents"). These map directly to the three tabs plus
Marketplace plus Admin Review (`PS:49-59`) and are the seams the component list in §4 is built from.

### 1.5 Trust boundaries
1. Unauthenticated request ↔ authenticated session (`FR-001`/`FR-002`).
2. One company's data ↔ another's — the big one; must hold even with the app-level check removed (`SEC-001`,
   `SEC-002`, `SEC-015`; graded check 1).
3. Regular user ↔ admin (`SEC-012`, `SEC-014`).
4. Platform ↔ external MCP server — the platform must not blindly trust a server's self-reported tool metadata.
   **Open per `spec.md §16` item 11:** the exact mechanism (manual review vs. something else) is unresolved; this
   boundary exists regardless of that answer, so it's named here without presupposing the resolution.
5. Platform ↔ LLM/model provider — a credential must never cross this boundary in a prompt (`SEC-004`).
6. Publisher ↔ installer, across the marketplace (`SEC-009`, `SEC-013`).
7. **Open per `spec.md §16` item 10:** a possible seventh boundary, creator ↔ rest-of-company, is unresolved and
   not assumed either way in this document (see §1.5-note below).

**Note:** boundaries 2 and 7 are not the same thing, and this architecture does not collapse them. Boundary 2 is
settled and load-bearing. Boundary 7's existence is an open question; the architecture must not be built in a
way that makes either answer to it structurally expensive later (see §3's self-critique).

### 1.6 Persistence boundaries
**Must survive a hard restart** (durable): companies, users, agents, agent configuration documents, registered
servers and their introspected tool lists, encrypted connections, LangGraph checkpoint state for all three
graphs, run history, scores/checks, submissions and their decisions (`NFR-006`, `NFR-007`; graded checks 5, 6).
**Must never persist beyond its single use** (ephemeral by requirement, not just by convenience): a decrypted
credential fetched for one tool call (`SEC-006`) — this is a *negative* persistence boundary, as load-bearing as
the positive ones.

### 1.7 Major data flows
Register → introspect → store tool list (`WF-001`) · Add credential → encrypt → store, reused by every future
build (`WF-002`) · Describe agent → understand → registry search → **interrupt: tool selection** → check
connections → **interrupt: missing credential** → write config → deploy (`WF-003`) · Playground message →
execute graph → read tools run automatically, write/destructive tools → **interrupt: approval** → credential
fetch-use-drop → result (`WF-004`) · Publish → gate check → strip credentials/internal detail →
**interrupt: admin decision** → approve (strip author identity, list) / request-changes (back to author) /
reject (`WF-005`) · Install → copy stripped config into installer's workspace → installer supplies own
credentials (`WF-006`) · External API call → authenticate + company-scope check → 404-mask or execute
(`SEC-011`) · Connection revoked/expired or server unhealthy → dependent agents degrade (`WF-007`, `WF-008`).

### 1.8 Major workflows
Directly `WF-001` through `WF-008` in `spec.md` §9 — not restated here to avoid drift between two documents;
this architecture is built to realize exactly those eight, no more.

### 1.9 Major security controls
Structural tenant scoping that survives app-layer removal (`SEC-001`) · no cross-tenant visibility incl.
guessed IDs (`SEC-002`) · encrypt-on-write, never-surface, abstract-reference, fetch-use-drop for credentials
(`SEC-003`–`SEC-006`) · platform-enforced (not instruction-based) approval gate (`SEC-007`, `SEC-008`) ·
publish-time stripping, two-stage (`SEC-009`, `FR-044`) · admin-only surfaces (`SEC-012`, `SEC-014`) · 404-not-403
masking (`SEC-011`) · marketplace as the only sanctioned cross-tenant path (`SEC-015`) · independent installer
credentials (`SEC-013`). Full detail in `.claude/rules/security.md`.

### 1.10 Major failure/recovery requirements
All three LangGraph graphs (build, execution, review) must checkpoint durably enough to survive a hard process
kill and resume from the exact interrupt, including multi-day/multi-deploy gaps (`NFR-006`, `NFR-007`; graded
checks 5, 6). A down MCP server or a revoked/expired connection must degrade only the affected agent, not the
platform or the company's other agents (`FR-008`, `FR-013`, `NFR-005`). Server health must be re-checked in the
background, not only on-demand (`FR-007`).

---

## 2. Architectural alternatives

### Alternative A — Modular monolith, single Postgres, external MCP servers

One deployable backend process, internally organized into the modules listed in §4, all sharing one Postgres
database (tenant isolation enforced via row-level security keyed on `company_id`, not application code alone).
LangGraph's checkpointer persists to the same Postgres instance. A separate frontend SPA talks to the backend
over HTTP. `docker compose up` starts: backend, Postgres, frontend, and any self-hosted MCP servers for the demo.
*(Postgres itself is a design choice, not a spec mandate — `spec.md §15` A6 leaves the persistence backend
unspecified; it's chosen here because it's the cheapest way to get real RLS, which `SEC-001` needs.)*

- **Strengths:** Matches `docker compose up` (`C5`) with the least moving parts. One transaction boundary makes
  "structurally impossible" isolation (`SEC-001`) achievable with a single, auditable RLS policy rather than N
  services each re-implementing the check. One checkpointer configuration to get right for `NFR-006`/`NFR-007`
  instead of three. Fastest to build correctly in a two-week window.
- **Weaknesses:** A bug in one module can affect the whole process (no hard failure isolation between, say, the
  registry-introspection code and the credential vault). Admin-only logic (`SEC-012`/`SEC-014`) lives in the same
  codebase as tenant-facing endpoints, so a routing mistake is one shared-codebase slip away rather than a
  separate-deployment slip away.
- **Complexity:** Low.
- **Capstone fit:** High — no requirement anywhere asks for independent scaling, deployment, or failure
  isolation between these modules (`NFR-011` explicitly says no scale requirement beyond a single-team demo is
  justified).
- **Requirements satisfied naturally:** `C5` (docker compose), `NFR-006`/`NFR-007` (one checkpointer to get
  right), `SEC-001` (one RLS policy to audit), all functional requirements — none of them need service
  boundaries to be satisfiable.
- **Requirements not naturally satisfied:** None that a service split would satisfy *better* — see §3's
  self-critique for where this alternative is risky anyway, which is a different concern than "unsatisfied."
- **Risks:** If RLS is skipped in favor of only application-level filtering "since it's one codebase anyway,"
  `SEC-001` fails outright the moment the grader removes the app check — this alternative's safety depends
  entirely on that one architectural discipline being followed, not on the module split itself.

### Alternative B — Service-oriented split by bounded context

Separate deployable services for Identity, Registry+Vault, Agent Runtime (all three LangGraph graphs),
Marketplace+Review, and an API Gateway — either separate databases per service or one Postgres with
schema-per-service, communicating over internal REST/gRPC.

- **Strengths:** Genuine failure isolation (a crash in one service doesn't take down another); admin-only logic
  can live in a network-isolated service, not just a code-isolated module; independently deployable/scalable if
  that were ever needed.
- **Weaknesses:** Multiplies the number of places `SEC-001`-equivalent isolation has to be re-proven (once per
  service touching tenant data, or one shared auth library every service must correctly adopt). Multiplies the
  number of checkpointer/transaction concerns for `NFR-006`/`NFR-007` if the runtime service's state and, say,
  the registry service's state aren't in the same transactional boundary. Significantly more to build correctly
  in two weeks, with more integration surface for `docker compose up` to get wrong.
- **Complexity:** Medium-high.
- **Capstone fit:** Low — no requirement demands independent scaling or deployment; `NFR-011` explicitly says
  this isn't justified; this is the "premature microservices" pattern `.claude/rules/architecture.md` rule 5
  names directly.
- **Requirements satisfied naturally:** Same functional set as A, at higher cost, with no additional requirement
  actually met better.
- **Requirements not naturally satisfied:** None distinctly — the theoretical gains (independent scaling,
  deploy) have no requirement asking for them.
- **Risks:** Spending capstone time on service-to-service plumbing (auth propagation, distributed transactions
  for the two-interrupt build flow spanning registry+runtime services) instead of on the actual graded checks;
  higher chance of a subtle cross-service isolation gap that graded check 1 specifically hunts for.

### Alternative C — Event-driven, broker-mediated

Same bounded contexts as B, but decoupled through a message broker (Kafka/RabbitMQ/similar): build/execution/
review interrupts become published events, resumed by consumers reacting to a later event (e.g., an approval
decision event).

- **Strengths:** Naturally models "pause and wait, possibly for days" as an architectural pattern; strong
  decoupling; broker gives a uniform place to reason about "what's pending."
- **Weaknesses:** LangGraph's own checkpointer *already* provides exactly the pause/resume durability this
  alternative would rebuild with a broker (`NFR-006`/`NFR-007` are natively satisfied by LangGraph's interrupt +
  checkpoint mechanism) — a broker on top is solving an already-solved problem. No requirement mentions
  eventual consistency, high write throughput, or independent consumer scaling. Substantially more
  infrastructure to run and get right under `docker compose up` (`C5`) for zero additional requirement coverage.
- **Complexity:** High.
- **Capstone fit:** Very low — this is exactly "unnecessary infrastructure" per `.claude/rules/architecture.md`
  rule 6: a queue/broker added without a requirement that needs it.
- **Requirements satisfied naturally:** No requirement is satisfied *better* than by LangGraph's own
  checkpointer, which both A and B already get for free.
- **Requirements not naturally satisfied:** None distinctly.
- **Risks:** The highest risk of all three of running out of time before the six-step demo works at all,
  for a pattern the brief never asks for.

---

## 3. Selection — and the argument against it

**Selected: Alternative A, the modular monolith with Postgres RLS.**

Nothing in `problem-statement/` asks for independent scaling, independent deployment, or event-driven
decoupling; `NFR-011` says so explicitly, and `.claude/rules/architecture.md` rules 5–6 forbid choosing B or C
without a requirement forcing the split. LangGraph's own checkpointer already solves the durable-pause problem
that Alternative C would re-solve with a broker. A is the minimum architecture that satisfies every requirement
in §1.

**Arguing against it, as instructed — where this could go wrong or overcomplicate the capstone anyway:**

1. **A modular monolith is only as safe as its RLS discipline, and that discipline is easy to skip under time
   pressure.** The entire case for A over B rests on "one Postgres, one RLS policy" being genuinely enforced at
   the database layer. If the team (under a two-week deadline) implements isolation as application-level
   `WHERE company_id = ?` filtering *without* RLS — because it's faster to write and "it's all one codebase
   anyway, what could go wrong" — Alternative A fails `SEC-001` outright the moment graded check 1 removes that
   filter, and fails in a way that's *harder to notice during development* than in Alternative B, where a
   missing per-service auth check tends to be more visible (a whole service either checks or doesn't). A's
   simplicity is a liability here, not just an asset, unless RLS is treated as non-negotiable at HLD time.
2. **Sharing one process for admin-only logic and tenant-facing logic increases blast radius for `SEC-012`/
   `SEC-014`.** In A, an admin-only route is one misplaced `if` away from being reachable by a non-admin,
   because it's the same router, same process, same deploy as everything else. B would make this a
   network-level fact rather than a code-review-dependent one. This is a real, not hypothetical, cost of
   choosing A — it needs to be closed at HLD with a single, centrally-enforced admin-check middleware, not
   scattered per-route checks (which is exactly the anti-pattern `SEC-001`'s own test methodology warns against,
   just applied to `SEC-012`/`SEC-014` instead of tenant scoping).
3. **A commits to "one database" before the per-user privacy open question (`§16` item 10) is resolved.** If the
   eventual answer is that agents default to creator-private *within* a company, that's still just another
   column/policy in the same RLS scheme — cheap under A. But it's worth naming that A was chosen partly *because*
   it makes that still-open question cheap to answer either way; if a future requirement turned out to need
   genuinely separate per-user data stores (unlikely, but not proven impossible from the brief alone), A would
   need revisiting. Flagging this instead of assuming A trivially absorbs any resolution.
4. **"Modular" is a promise, not a guarantee.** Nothing about a single deployable enforces the module boundaries
   drawn in §4; without deliberate internal discipline (e.g., the credential vault module being the *only* code
   path allowed to touch the connections table), a monolith can quietly become a ball of mud where, for
   instance, general application code queries decrypted credentials directly — which is precisely the failure
   mode graded check 2 is built to catch. This has to be an enforced convention at HLD/LLD time, not something
   this architecture document can guarantee on its own.

None of these four points changed the selection — they're reasons A requires *discipline* to be safe, not
reasons to prefer B or C, which would trade a discipline problem for a distributed-systems problem the capstone
has no requirement asking for. But they are real risks this document is not allowed to paper over, and they
should be carried forward explicitly into the ARCHITECTURE REVIEW and then into HLD as non-negotiable design
constraints (RLS is mandatory; a single centralized admin-check middleware is mandatory; a single code path
owns credential decryption).

---

## 4. Components

Each component below is a module within the Alternative A monolith (§2), not a separate service, unless noted.
**Revision note (from `architecture-review.md`):** every component from the previous version is retained —
the review's own challenge question 1 concluded none of the twelve were unjustified, and re-checking that
conclusion here doesn't change it. No component is removed in this revision; several gain additional
requirement citations and explicit design constraints instead (marked "Revised" below).

### 4.1 API Layer *(Revised — REVARCH-001, REVARCH-003, REVARCH-008, REVARCH-011)*
- **Responsibility:** Terminates HTTP requests, authenticates the caller, enforces company-scope and
  admin-scope before any handler runs, and applies 404-masking for cross-company resource access. This
  404-masking pattern applies to **every** company-scoped route the API exposes — agent listing (`FR-054`,
  `FR-055`), agent detail, connections, and invocation alike — not only the agent-invoke endpoints; a guessed ID
  for any other company's resource gets the same not-found treatment as `SEC-011` already mandates for invoke.
  Resume and invoke actions are idempotent per thread/decision: a repeated resume against an
  already-resolved interrupt, or a retried invoke with the same idempotency key, must not re-execute the
  underlying action.
- **Requirement IDs:** `FR-001`, `FR-002`, `FR-054`, `FR-055`, `SEC-002`, `SEC-011`, `SEC-012`, `SEC-014`,
  `API-001`–`API-006`.
- **Ownership split with 4.11:** this module owns the cross-cutting auth/scope/404/idempotency wrapper every
  request passes through; 4.11 owns the agent-specific route handlers and Postman generation that sit behind it.
- **Why it exists:** Every other module needs a single, consistent point where "who is this, what company, are
  they admin" is established once and trusted downstream — this is what makes `FR-002`'s "two claims, everything
  else follows" actually true architecturally.
- **Why it is not unnecessary:** Without a single enforced layer, each handler could re-implement (or forget)
  auth/scope checks independently — exactly the "one forgotten filter is a breach" failure mode `SEC-001`
  explicitly warns against, generalized to every endpoint, not just tenant data. Centralizing `SEC-002`,
  `FR-054`, and `FR-055` here specifically closes the gap the review found: previously nothing in this document
  named a single owner for "no cross-tenant visibility, even by guessing a URL" beyond the invoke API.

### 4.2 Identity & Session module
- **Responsibility:** Email/password authentication; issuing and validating sessions that carry exactly
  company-id and admin-boolean.
- **Requirement IDs:** `FR-001`, `FR-002`.
- **Why it exists:** Every trust boundary in §1.5 starts here.
- **Why it is not unnecessary:** It's the minimum stated by the brief — not a candidate for removal, but also
  deliberately not expanded (no SSO, no token exchange — `NG6`, `NG7`).

### 4.3 MCP Registry & Introspection module *(Revised — REVARCH-005)*
- **Responsibility:** Registers a server record; acts as an MCP client to connect and fetch the server's real
  tool list; enforces admin-only for `global` scope; runs the background health re-check. A server going
  unhealthy degrades only its dependent agents, never the platform or other companies' agents.
- **Requirement IDs:** `FR-003`–`FR-008`, `SEC-014`, `NFR-005`, `WF-001`, `WF-008`.
- **Why it exists:** This is the literal mechanism behind "I do not type tool names in by hand" (`PS:71`) — the
  registry's credibility depends on nothing else being able to fabricate a tool list.
- **Why it is not unnecessary:** Without it as a distinct module, tool-list provenance (introspected vs.
  hand-entered) has no single enforcement point, undermining `FR-004`'s "nothing is saved if it doesn't answer"
  guarantee.
- **Open item carried in, not resolved here:** the tool-risk-classification mechanism (`spec.md §16` item 11) —
  this module owns wherever that mechanism ends up living, once decided.

### 4.4 Credential Vault module *(Revised — REVARCH-005, REVARCH-009)*
- **Responsibility:** The *only* code path permitted to encrypt, store, decrypt, or hand a credential to a tool
  call. Enforces fetch-use-drop. **Architectural constraint (closes REVARCH-009):** a decrypted credential this
  module hands out is injected at the tool-invocation boundary and must never be assigned into any value that
  becomes part of a LangGraph node's returned state — because that state is exactly what 4.5/4.6/4.8's
  checkpointer (4.10) persists on every interrupt-capable step. "Fetch, use, drop" only satisfies `SEC-004`'s
  unbounded no-persistence guarantee if the credential's lifetime never overlaps with anything serializable; this
  is a hard requirement on how the Execution Graph (4.6) is built, not just on the Vault itself. A revoked or
  expired connection degrades only the agents that depend on it (`NFR-005`).
- **Requirement IDs:** `SEC-003`–`SEC-006`, `NFR-001`, `NFR-002`, `NFR-005`, `FR-009`–`FR-014`, `WF-002`,
  `WF-007`.
- **Why it exists:** Graded check 2 searches *everything stored* for a credential — the only way to make that a
  guaranteed pass rather than a hope is to have exactly one place credentials ever flow through, so there's
  exactly one thing to audit.
- **Why it is not unnecessary:** This is the component named directly in §3's self-critique point 4 — merging
  it into general data-access code is the single highest-risk simplification a time-pressured team could make,
  and this module boundary exists specifically to make that mistake structurally awkward to commit.

### 4.5 Agent Builder Graph (LangGraph) *(Revised — REVARCH-002, REVARCH-004, REVARCH-006, REVARCH-014)*
- **Responsibility:** The chat/form-driven graph: understand → propose tools **[interrupt]** → check connections
  **[interrupt]** → write configuration → deploy. Must be able to produce both single-agent and
  coordinator+specialist configurations (`FR-059`) and is the component responsible for the mandatory
  multi-agent demo agent's provenance being verifiable as built-through-the-platform rather than hand-authored
  (`FR-060`) — this is the graph graded check 7 depends on existing at all. **Post-build follow-up edits
  (`FR-024`)** — e.g. "also include issues labelled bug" typed after the initial build — are explicitly
  **unresolved**: whether this re-enters the same interrupted graph, opens a new build thread, or edits the
  configuration directly is undecided pending `spec.md §16` item 8; this component owns that decision once made.
  **Single-writer constraint (closes REVARCH-014):** this graph is the only legitimate writer of an agent's
  configuration document; any future edit surface must reuse this graph's approval-mode validation (`FR-058`)
  rather than writing the document directly.
- **Requirement IDs:** `FR-015`–`FR-024`, `FR-058`, `FR-059`, `FR-060`, `WF-003`, `NFR-006`, `NFR-007`.
- **`DATA-007` flag (closes REVARCH-006):** the agent configuration document this graph writes is, per
  `spec.md` rule 1, "the central design problem of this capstone" — its schema is undefined by any source and
  is the single highest-priority artifact for HLD to design first, since `SEC-005`, `FR-058`, and `FR-026`
  (the agent graph drawn from configuration) all depend on its shape.
- **Why it exists:** This is literally "the centre of this project" (`PS:102`) — the two durable interrupts are
  what graded check 5 tests directly.
- **Why it is not unnecessary:** It's the one piece of the system with no substitute; every other module exists
  to support what this graph needs (registry lookups, connection checks, config persistence).

### 4.6 Agent Execution Graph (Playground + scheduled/API runs) *(Revised — REVARCH-002, REVARCH-009, REVARCH-011)*
- **Responsibility:** Runs a deployed agent's configuration; executes read tools automatically; pauses
  write/destructive tool calls for approval **[interrupt]**; records run history. Runs both single-agent and
  coordinator+specialist (`FR-059`) configurations, including the mandatory multi-agent demo agent end to end
  with its approval step (`FR-060`, graded check 7). **Credential handling constraint (shared with 4.4, closes
  REVARCH-009):** a credential fetched from the Vault for a tool call is held only in local, non-serialized
  execution scope for the duration of that call — never in the graph's own returned/checkpointed state. Approval
  decisions (resume actions) are idempotent per interrupt (see 4.1) — a repeated "Approve" does not re-execute
  the tool call.
- **Requirement IDs:** `FR-025`–`FR-038`, `FR-058`, `FR-059`, `FR-060`, `SEC-007`, `SEC-008`, `WF-004`,
  `NFR-006`, `NFR-007`.
- **Why it exists:** This is the runtime that "reads the configuration document and assembles the agent"
  (`PS:154`) — rule 1's central mechanism.
- **Why it is not unnecessary:** It's distinct from the Builder Graph (4.5) because they have different
  lifecycles and different interrupt semantics (build-time vs. every-single-run); merging them would make the
  approval-gate logic (`SEC-007`) conditional on *why* the graph is running, which is exactly the kind of
  implicit special-casing that tends to grow a security gap.

### 4.7 Scoring Engine
- **Responsibility:** Computes the capability score and the safety/governance grade from enumerable checks;
  exposes the itemized checks behind each number.
- **Requirement IDs:** `FR-056`, `FR-057`, `NFR-009`.
- **Why it exists:** Rule 6 explicitly forbids a model-guessed score — this has to be a deterministic module
  that can be pointed at, not a prompt.
- **Why it is not unnecessary:** Without a dedicated module, "why is this score what it is" (`PS:201`) has no
  single place to answer from, which is exactly what the presentation defense (`TEST-010`) will ask about
  directly.

### 4.8 Publish & Admin Review Graph (LangGraph)
- **Responsibility:** Gate-checks a publish request (score/approval-coverage), strips credentials/internal
  detail, parks at the review queue **[interrupt, possibly for days]**, resolves on Approve/Request-changes/
  Reject.
- **Requirement IDs:** `FR-039`–`FR-048`, `SEC-009`, `SEC-010`, `WF-005`, `NFR-006`, `NFR-007`, `NFR-010`.
- **Why it exists:** This is the mechanism behind rule 5 and the marketplace's single deliberate exception
  (`SEC-015`) — the only door between companies, and it has to be a real interrupt, not a status flag, to
  satisfy graded check 6's multi-day-wait requirement.
- **Why it is not unnecessary:** Distinct from 4.6 because its interrupt can legitimately last days rather than
  seconds and its resolution has three branches with different downstream effects (§16 item 3 and item 12 —
  both still open on Reject/resubmission semantics, owned by this module once resolved).

### 4.9 Marketplace & Install module *(Revised — from challenge question 4)*
- **Responsibility:** Serves approved listings; on install, deep-copies a stripped configuration into the
  installer's workspace with no live link back to the original. **The copy is an explicit allowlist of
  design-safe fields (name, description, tool/risk/approval shape, topology), not a blocklist of excluded
  fields** — a blocklist fails open (a newly added field leaks by default until someone remembers to exclude
  it); an allowlist fails closed.
- **Requirement IDs:** `FR-049`–`FR-053`, `SEC-013`, `SEC-015`, `WF-006`.
- **Why it exists:** This is the literal implementation of "the one place data crosses between companies"
  (`MARKET:23`).
- **Why it is not unnecessary:** It's what makes `SEC-015` (marketplace is the *only* sanctioned crossing) an
  architectural fact rather than a policy statement — no other module is permitted to move data between
  companies, and this is the one place that's allowed to and is built to do it safely.

### 4.10 Checkpointer / Persistence layer *(Revised — REVARCH-010, REVARCH-013)*
- **Responsibility:** Postgres-backed storage for both the relational domain data (companies, users, agents,
  connections, servers, runs, submissions) and the LangGraph checkpoint state for all three graphs, with
  row-level security keyed on `company_id`. **Architectural constraint (closes REVARCH-010):** checkpoint writes
  must carry the same RLS enforcement as domain-data writes — either the checkpointer uses the same
  session-scoped connection with `company_id` set per transaction, or checkpoint rows are partitioned by
  `company_id` under a non-bypassable constraint verified at resume time. A checkpointer that opens its own
  connection outside this discipline is an unscoped side door around `SEC-001` and is not an acceptable HLD
  choice. **Architectural constraint (closes REVARCH-013):** a paused interrupt, however long it waits, must be
  representable as pure at-rest data — no held database connection, lock, or live in-memory object for the
  duration of the wait — so that many concurrent long-pending approvals don't exhaust the connection pool.
- **Requirement IDs:** `NFR-003`, `NFR-006`, `NFR-007`, `SEC-001` (the enforcement mechanism, per §3 point 1).
- **Why it exists:** Named as its own component, distinct from "the database" as a generic detail, because its
  correctness (RLS actually enabled and correct, checkpoint durability actually surviving a `kill -9`) is the
  single point graded checks 1, 5, and 6 all converge on.
- **Why it is not unnecessary:** This is not a default "every app has a database" entry — it's called out
  separately because its specific configuration (RLS on, not just present; checkpointer durable, not
  in-memory-with-a-flush) is a named risk in §3, not an assumed given.

### 4.11 Public Agent API + Postman Export module *(Revised — REVARCH-008, REVARCH-011)*
- **Responsibility:** Exposes the per-agent invoke/stream/resume endpoints, behind 4.1's auth/scope/404/
  idempotency wrapper; generates a real, working Postman v2.1 collection on demand.
- **Requirement IDs:** `FR-035`–`FR-038`, `API-001`–`API-006`.
- **Why it exists:** Rule 7 requires every agent be usable from outside the UI, and graded check 8 specifically
  tests that the downloaded collection gets a real response — not a static export.
- **Why it is not unnecessary:** Distinct from 4.1 (API Layer) because 4.1 is cross-cutting (auth, scoping) while
  this module is the agent-specific surface built on top of it; collapsing them would make it easy to
  accidentally expose an agent-specific route without the 404-masking check 4.1 is responsible for.

### 4.12 Frontend (SPA)
- **Responsibility:** Implements the behavior (not pixels, per `C8`) of the 8 screens: sign-in, registry,
  connections, build, my-agents, agent detail (6 tabs), admin review, marketplace.
- **Requirement IDs:** `UI-001`–`UI-014`.
- **Why it exists:** It's the only user-facing surface for every workflow in §1.8.
- **Why it is not unnecessary:** Self-evident for a UI-graded capstone — included here mainly to note it is
  **outside** the monolith's backend boundary as a separate deployable (a static SPA build), which is the one
  place Alternative A's "single deployable" framing in §2 is not literally true and shouldn't be read as such.

---

## 5. Testability mapping *(new — closes REVARCH-007)*

Assembled from the citations already in §4; no new design work, just making the "graded check → what gets
exercised" link explicit rather than implicit.

| Graded check | Exercises | Component(s) |
|---|---|---|
| `TEST-001` — isolation with app filter removed | `SEC-001` | 4.10 (RLS must hold with 4.1's check removed) |
| `TEST-002` — credential search | `SEC-004`, `SEC-006` | 4.4, 4.6 (REVARCH-009 constraint), 4.10 (checkpoint storage) |
| `TEST-003` — unguarded write tool blocks publish | `SEC-007`, `SEC-008` | 4.6, 4.8 |
| `TEST-004` — planted confidential material stripped | `SEC-009` | 4.8, 4.9 (allowlist copy) |
| `TEST-005` — kill mid-build resumes | `NFR-006` | 4.5, 4.10 (REVARCH-010 constraint) |
| `TEST-006` — overnight approval resumes | `NFR-006`, `NFR-007` | 4.6, 4.8, 4.10 (REVARCH-013 constraint) |
| `TEST-007` — multi-agent demo end to end | `FR-059`, `FR-060` | 4.5 (provenance), 4.6 (execution) |
| `TEST-008` — Postman collection gets a real response | `FR-036` | 4.11 |
| `TEST-009` — cross-company agent lookup hides existence | `SEC-011`, `SEC-002` | 4.1 |
| `TEST-010` — live presentation defense | all of the above | whole document, §3 self-critique in particular |

## 6. Assumptions carried by this architecture *(new — closes REVARCH-012)*

- **LLM-provider failure mid-turn is unspecified by `problem-statement/` itself** — no rule or graded check
  addresses what happens if the LLM call (not a tool call) fails or times out during a build or execution turn,
  unlike MCP-server failure (`FR-007`/`FR-008`, explicitly handled) or connection failure (`FR-013`, explicitly
  handled). This architecture does not invent a requirement to fill that gap; it records the gap instead. Design
  choice for HLD to make explicitly (e.g., surface the failure, mark the run `err`, no silent retry) rather than
  leave implicit.
- Encryption algorithm, MCP client library, and SPA framework remain unspecified here, consistent with
  `spec.md`'s own silence on them — not oversights, deliberate deferral to HLD/LLD.

## 7. Carried-forward open items (not resolved by this document)

- `spec.md §16` item 8 — post-build follow-up edit semantics (`FR-024`, affects §4.5's scope — added in this
  revision; previously omitted from this list despite the component citing the ID).
- ~~`spec.md §16` item 10 — per-user privacy scope~~ **Resolved at HLD** (`architecture/hld.md §0`, decision D1:
  company + owner-user RLS). `spec.md §16` item 10 updated to record this.
- ~~`spec.md §16` item 11 — tool-risk-classification mechanism~~ **Resolved at HLD** (`architecture/hld.md §0`,
  decision D2: manual review + new `pending_classification` state). `spec.md §16` item 11 updated to record this.
- `spec.md §16` item 12 / item 3 — resubmission and Reject semantics (affects §4.8's resolution branches).
- `specs/traceability.md` — regenerated alongside this revision; see that file directly.

These are HLD-time decisions, not architecture-time ones, and none of them change the component boundaries or
the Alternative-A selection above — they change what happens *inside* specific components once answered.

# Hostile Evaluator Audit — architecture/architecture.md

**Role:** Hostile capstone evaluator. **Not** a design pass — nothing in `architecture.md` is modified by this
document. **Audited against:** (A) every file under `problem-statement/` — via the GitHub source it mirrors,
already fully ingested when `spec.md` was built; (B) `specs/spec.md`; (C) `specs/traceability.md`.

**Process finding before anything else: source C does not exist.** `specs/traceability.md` was never
regenerated (flagged repeatedly since it was paused). `architecture.md` itself discloses this and substitutes
`spec.md`'s inline `Source:` citations plus its own §17 reverse index. This audit does the same, for the same
reason — but as a hostile evaluator I am not going to let that slide silently a second time: **an architecture
document that ships without one of its three named source inputs existing is itself a process failure**, not
just a footnote. This is counted in the score in §4.

---

## 1. Verdict summary

Default verdict is **PASS** (explicitly cited by a component, or correctly out of scope at architecture level —
UI-\*/DATA-\* granular fields are HLD/LLD concerns and their absence here is not penalized on its own). Every
exception is listed below with a verdict and, for anything not PASS, full detail in §2.

- **FR-001–FR-023, FR-025–FR-053, FR-056–FR-057:** PASS — explicitly cited by name or unambiguous range.
- **FR-024:** PARTIAL — see REVARCH-004.
- **FR-054, FR-055:** PARTIAL — see REVARCH-003.
- **FR-058, FR-059, FR-060:** FAIL — see REVARCH-002. `FR-060` is P0-CRITICAL and this is the single worst
  finding in this audit.
- **FR-061, FR-062:** UNSATISFIED *by design, correctly* — submission deliverables, not system components; not
  architecture's job. Not penalized.
- **NFR-001–NFR-004, NFR-006, NFR-007, NFR-009–NFR-011:** PASS (`NFR-004`/`NFR-011` are correctly treated as
  non-goals, not gaps).
- **NFR-005:** PARTIAL — see REVARCH-005.
- **NFR-008:** PASS at architecture-appropriate granularity (P1 usability, deferred to Frontend/HLD).
- **SEC-001, SEC-003–SEC-015:** PASS on citation — but see REVARCH-009 and REVARCH-010, which are not citation
  gaps, they are cases where the citation exists and is still not actually satisfied by the described behavior.
- **SEC-002:** FAIL — see REVARCH-001.
- **WF-001–WF-008:** PASS — every one explicitly cited, no gaps.
- **UI-001–UI-014:** PASS at architecture-appropriate granularity (correctly deferred, owned generically by the
  Frontend component).
- **API-001–API-006:** PARTIAL — see REVARCH-008 (ownership ambiguity, not a missing citation).
- **DATA-001–DATA-006, DATA-008–DATA-014:** PASS at architecture-appropriate granularity (correctly deferred).
- **DATA-007:** PARTIAL — see REVARCH-006.
- **TEST-001–TEST-010:** PARTIAL — see REVARCH-007 (no explicit testability mapping exists anywhere in the
  document, for any of the nine).
- **`spec.md §16` item 8** (follow-up chat edits, tied to `FR-024`): omitted from architecture.md's own
  "carried-forward open items" list — see REVARCH-004.

---

## 2. Detailed findings (PARTIAL / FAIL)

### REVARCH-001 — FAIL: `SEC-002` has no component owner
- **Requirement ID:** `SEC-002`
- **Exact source:** `spec.md` — "A user must never be able to view another company's agents, connections, or
  runs, including by guessing/enumerating identifiers in a URL." (sourced from `MYAG:43`, `SIGNIN:79-87`)
- **Current architecture behavior:** `SEC-002` is mentioned in prose twice (§1.5 trust boundary 2, §1.9 security
  controls list) but appears in **zero** component's "Requirement IDs" field in §4. `SEC-001` is explicitly
  owned by the Persistence layer (4.10); `SEC-011` and `SEC-012`/`SEC-014` are owned by the API Layer (4.1).
  `SEC-002` — arguably the most literally-worded requirement in the whole brief ("must never," "even by
  guessing a URL") — is owned by nothing.
- **Missing behavior:** No component is accountable for enforcing "no cross-tenant visibility by any means,
  including guessed IDs" as a distinct, testable behavior separate from `SEC-001`'s data-scoping and `SEC-011`'s
  404-masking. It's easy to assume `SEC-001` covers it, but `SEC-001` is about data-layer scoping; `SEC-002`
  additionally requires the *response shape itself* not leak existence (same 404-not-403 pattern as `SEC-011`,
  just for UI-addressable resources, not only the invoke API).
- **Risk:** Graded check 1 ("with your application filter removed") tests data-layer scoping; nothing in this
  architecture currently commits to *also* returning a not-found response (rather than a 403, or a 200 with
  empty data that still confirms the record's existence) for a UI-addressable resource ID belonging to another
  company. If the API Layer's 404-masking (4.1) is implemented narrowly, scoped only to the agent-invoke
  endpoints it's explicitly cited for, this requirement silently fails.
- **Recommended change:** Add `SEC-002` explicitly to the API Layer's (4.1) requirement IDs, and state that the
  same 404-masking pattern used for `SEC-011` applies to every company-scoped resource route, not only agent
  invocation.

### REVARCH-002 — FAIL: `FR-058`, `FR-059`, `FR-060` cited by no component
- **Requirement ID:** `FR-058`, `FR-059`, `FR-060`
- **Exact source:** `spec.md` §6 "Agent shape / tool governance" — `FR-060` in particular: "At least one shipped
  demo agent must be a genuine multi-agent system... Priority: P0 — CRITICAL deliverable" (sourced `PS:217-223`,
  graded check 7).
- **Current architecture behavior:** No component in §4 lists `FR-058`, `FR-059`, or `FR-060` in its Requirement
  IDs. The Builder Graph (4.5) cites `FR-015`–`FR-024`; the Execution Graph (4.6) cites `FR-025`–`FR-038`. The
  numeric range simply stops before 058. Multi-agent topology (coordinator + specialists) is mentioned once in
  prose (§1.4, as one of many bounded contexts) but never tied to a requirement ID or a component's stated
  responsibility.
- **Missing behavior:** Nothing in the architecture explicitly states which component is responsible for (a)
  representing coordinator/specialist topology in the configuration document, (b) executing a supervisor
  handing off to sub-agents at runtime, or (c) guaranteeing the mandatory demo agent was produced *through the
  platform's own build flow* rather than hand-authored, which is the specific thing graded check 7 and rule 8
  are designed to catch.
- **Risk:** This is the highest-severity finding in this audit. `FR-060` is explicitly labeled P0-CRITICAL
  deliverable in `spec.md`, and its own text anticipates and forbids the shortcut of hand-writing the multi-agent
  demo — an architecture that doesn't name which component enforces "built through the platform" makes it
  materially easier for that shortcut to happen unnoticed during implementation.
- **Recommended change:** Extend the Builder Graph (4.5) and Execution Graph (4.6) citations to include `FR-058`
  –`FR-060` explicitly, and add one sentence to 4.5's responsibility stating that the builder must be capable of
  producing supervisor+specialist configurations (not just single-agent ones) and that the demo agent's
  provenance (built via this graph) must be verifiable.

### REVARCH-003 — PARTIAL: `FR-054`/`FR-055` (My Agents scoping) have no explicit backend owner
- **Requirement ID:** `FR-054`, `FR-055`
- **Exact source:** `spec.md` — "My Agents shows only the signed-in user's own workspace's agents... even by
  guessing a URL." (`MYAG:43`)
- **Current architecture behavior:** Covered only transitively — `FR-054`/`FR-055` fall under the Frontend
  component's generic `UI-001`–`UI-014` citation (4.12), and the underlying scoping is only implied by the API
  Layer's general "company-scope" enforcement (4.1), which doesn't name these IDs directly.
- **Missing behavior:** No component's Requirement IDs field names `FR-054`/`FR-055`, so there's no explicit
  architectural commitment to a "list my agents" capability existing at all, distinct from the individual
  agent-detail routes.
- **Risk:** Low on its own (the capability is obviously needed and will get built), but it compounds
  REVARCH-001 — this is a second place the "own workspace only, even by guessed ID" guarantee is assumed rather
  than assigned.
- **Recommended change:** Add `FR-054`, `FR-055` explicitly to the API Layer (4.1) citation list alongside the
  `SEC-002` fix from REVARCH-001.

### REVARCH-004 — PARTIAL: `FR-024` nominally in-range but not described; its open question is dropped
- **Requirement ID:** `FR-024`
- **Exact source:** `spec.md` — post-build follow-up edits via the same chat composer; mechanism explicitly
  unresolved, tracked as `spec.md §16` item 8.
- **Current architecture behavior:** `FR-024` is technically inside the Builder Graph's cited range
  (`FR-015`–`FR-024`), but 4.5's responsibility prose only describes the five-step initial build ("understand →
  propose tools → check connections → write configuration → deploy") — no mention of a post-build edit path.
  Separately, architecture.md's closing "Carried-forward open items" section lists `§16` items 10, 11, 12, and
  the missing `traceability.md` — but **not item 8**, even though item 8 is exactly the open question this
  component's own scope touches.
- **Missing behavior:** Whether a follow-up edit re-enters this same graph, opens a new thread, or does
  something else is undecided — fine, since `spec.md` leaves it undecided too — but the architecture should say
  so explicitly rather than let the range citation imply it's handled.
- **Risk:** Low severity, but it's a specific instance of a general problem: a numeric ID range can silently
  paper over an undescribed behavior. Anyone reading only the Requirement IDs field would reasonably assume
  `FR-024` is architecturally accounted for; it isn't.
- **Recommended change:** Add one line to 4.5 noting the post-build-edit path is unresolved pending `§16` item
  8, and add item 8 to the closing open-items list.

### REVARCH-005 — PARTIAL: `NFR-005` (isolated failure domains) not explicitly owned
- **Requirement ID:** `NFR-005`
- **Exact source:** `spec.md` — "A single dependency failure... must not take down a company's other agents or
  tools." (`REG:142-144`, `CONN:74-79`)
- **Current architecture behavior:** Covered only transitively via `WF-007` (owned by 4.4) and `WF-008` (owned
  by 4.3), which are the *mechanisms* that realize `NFR-005`, but the NFR itself — the general quality "one
  failure doesn't cascade" — isn't named on either component.
- **Missing behavior:** No explicit statement of failure-domain boundaries between, say, the Registry module and
  the Execution Graph — i.e., what stops a bug in health-checking (4.3) from taking down in-flight executions
  (4.6)? The two `WF` citations cover the two specific documented triggers (revocation, server-down) but not the
  general principle.
- **Risk:** Low — mostly a documentation completeness issue, not a design flaw, since the underlying `WF`
  mechanisms are correctly assigned.
- **Recommended change:** Add `NFR-005` to both 4.3 and 4.4's citation lists alongside their existing `WF`
  entries.

### REVARCH-006 — PARTIAL: `DATA-007` (the "central design problem") isn't flagged as such
- **Requirement ID:** `DATA-007`
- **Exact source:** `spec.md` — "Work out for yourself what that document needs to contain. That is the central
  design problem of this capstone." (`PS:157-158`)
- **Current architecture behavior:** The agent configuration document is referenced repeatedly in passing
  ("write configuration," "reads the configuration document and assembles the agent") but `DATA-007` itself is
  never cited by any component, and the document never calls out that this specific artifact's schema is the
  single largest piece of undesigned surface area in the whole system.
- **Missing behavior:** No explicit forward-pointer telling the HLD phase "this is the highest-priority thing to
  design first."
- **Risk:** Low-medium — not a defect in the architecture's correctness, but a missed opportunity that a hostile
  evaluator would use to ask "so what does the configuration document actually contain?" and get no answer
  anywhere in this document, including in its own list of open items.
- **Recommended change:** Add a short explicit note (not a schema — that's LLD) in §4.5 or as its own
  sub-section stating that `DATA-007`'s schema is the first thing HLD must produce, since `SEC-005`, `FR-058`,
  and `FR-026` (graph drawn from configuration) all depend on its shape.

### REVARCH-007 — PARTIAL: no explicit `TEST-001`–`TEST-010` → component mapping
- **Requirement ID:** `TEST-001`–`TEST-010` (all nine graded checks plus the presentation defense)
- **Exact source:** `spec.md` §13, verbatim from `PS:257-274`.
- **Current architecture behavior:** Every `TEST-*` requirement is *implicitly* satisfiable through the `SEC-*`/
  `FR-*` citations already in §4, but there is no explicit section anywhere in `architecture.md` stating, for
  each of the nine checks, which component(s) it exercises and how the architecture makes it verifiable.
- **Missing behavior:** A direct "graded check → what in this architecture gets tested" table.
- **Risk:** Medium — this is exactly the kind of gap that becomes visible only during the actual grading run,
  when it's too late to fix cheaply. Testability is one of the nine required dimensions this audit was told to
  check for by name.
- **Recommended change:** Add a short testability appendix mapping each `TEST-00X` to the component(s) it
  exercises — this can be produced from the citations already in §4 with no new design work, just assembly.

### REVARCH-008 — PARTIAL: `API-001`–`API-006` dual-owned without a split
- **Requirement ID:** `API-001`–`API-006`
- **Exact source:** `spec.md` §11.
- **Current architecture behavior:** Both 4.1 (API Layer) and 4.11 (Public Agent API + Postman Export) cite the
  full `API-001`–`API-006` range.
- **Missing behavior:** No statement of which component owns *what* — presumably 4.1 owns the cross-cutting
  auth/scoping/404-masking wrapper and 4.11 owns the route handlers and Postman generation themselves, but the
  document doesn't say this, so it reads as two components independently claiming the same six requirement IDs.
- **Risk:** Low — a clarity issue, not a correctness one, but ownership ambiguity is exactly the kind of thing
  that lets a requirement quietly fall between two components during implementation ("I thought the other
  module handled that").
- **Recommended change:** State the split explicitly: 4.1 provides the auth/scope/404 wrapper all requests pass
  through; 4.11 implements the agent-specific routes and Postman generation behind it.

### REVARCH-009 — FAIL: credential-in-checkpoint leak path not addressed
- **Requirement ID:** `SEC-004`, `SEC-006`, `NFR-002`
- **Exact source:** `spec.md` — "No credential value may exist in any persisted state the platform controls, of
  any kind — this guarantee is unbounded... including... LangGraph checkpoint state..." (`SEC-004`, reworded
  specifically to name this risk after the last adversarial review).
- **Current architecture behavior:** The diagram (`diagrams/architecture.mmd`) shows the Execution Graph (EXECG)
  with a dotted "fetch, use, drop — never persisted beyond the call" edge to the Vault, and a *separate, solid*
  edge from EXECG straight to the shared Postgres checkpoint store (DB). The credential itself has to pass
  through the Execution Graph's own in-memory state to reach the MCP tool call — and that graph's state is what
  gets checkpointed to the same database, on every interrupt-capable step, for durability.
- **Missing behavior:** Nothing in `architecture.md` states that the credential is kept *outside* the
  LangGraph-managed state object during a tool call (e.g., injected at the tool-execution boundary from the
  Vault directly, never assigned into a graph node's returned state), which is the only way "fetch, use, drop"
  and "no credential in any checkpoint" can both be literally true given that the same process, mid-tool-call,
  is also the thing being checkpointed.
- **Risk:** High. This is precisely the scenario `spec.md`'s own `SEC-004` was reworded to name after the prior
  adversarial review (`spec-review.md` REV-006), and this architecture doesn't yet close it — it inherited the
  requirement's text but not a design commitment that satisfies it.
- **Recommended change:** Add an explicit architectural constraint: the Execution Graph's checkpointed state
  schema must never include a field capable of holding a decrypted credential; credential injection happens at
  the tool-invocation boundary (outside the graph's serializable state), sourced fresh from the Vault on every
  call. This belongs in HLD, but the *constraint* needs to be stated at architecture level because it shapes
  how the Execution Graph's state is designed from the start.

### REVARCH-010 — FAIL: checkpointer connection may bypass RLS
- **Requirement ID:** `SEC-001`, `NFR-003`
- **Exact source:** `spec.md` — "must be scoped to the owning company at a layer that still enforces isolation
  if the application-level authorization check is removed." (`PS:165-170`, graded check 1)
- **Current architecture behavior:** 4.10 states RLS keyed on `company_id`, and asserts (§3 point 1) that this
  is what makes `SEC-001` hold structurally. But LangGraph's checkpointer typically writes through its own
  connection or connection pool, separate from the per-request connections the API Layer opens — and Postgres
  RLS policies commonly depend on a per-transaction session variable (e.g. `SET LOCAL app.company_id = ...`)
  being set on *that specific connection* for the policy to evaluate correctly.
- **Missing behavior:** Nothing in `architecture.md` states that the checkpointer's writes go through the same
  RLS-scoped connection/session-variable discipline as everything else, or explains how a checkpoint row (which
  belongs to one company's agent run) gets tenant-scoped at all if the checkpointer library manages its own
  connection lifecycle independently.
- **Risk:** High, for the same reason as REVARCH-009: if this gap is real once implemented, the checkpoint
  table itself becomes an un-scoped side door around `SEC-001` — and checkpoint tables are exactly the kind of
  thing a team is least likely to think to check when manually reviewing "did we filter every query."
- **Recommended change:** Add an explicit architectural constraint that the checkpointer must either (a) use the
  same RLS-scoped connection/session discipline as domain-data writes, with `company_id` set per checkpoint
  write, or (b) store checkpoints in a company-partitioned scheme that doesn't rely on RLS at all (e.g., a
  `company_id` column enforced by a non-bypassable constraint, verified at the point of resume). Whichever is
  chosen belongs in HLD, but — as with REVARCH-009 — the constraint must be named now so it isn't discovered
  after the checkpointer is already wired up the easy way.

### REVARCH-011 — PARTIAL: no idempotency/duplicate-retry story
- **Requirement ID:** `SEC-007`, `SEC-008`, `WF-003`, `WF-004`
- **Exact source:** derived from the interrupt-resume mechanics across `FR-018`, `FR-020`, `FR-028`, `WF-003`,
  `WF-004`.
- **Current architecture behavior:** Nothing in `architecture.md` addresses what happens if an interrupt-resume
  action (e.g., clicking "Approve & post," or the tool-selection confirmation) is submitted twice — a double
  click, a client retry after a timeout, or a retried `POST /v1/agents/:id/resume` call.
- **Missing behavior:** No idempotency-key or dedup mechanism is named anywhere for resume actions or for
  `POST /invoke`.
- **Risk:** Medium. A retried "Approve" on a write/destructive tool could execute that action twice — which
  would technically still have gone through the approval gate (so it doesn't violate `SEC-007`'s letter), but
  it violates its spirit (one human decision should mean one action), and a duplicated destructive call is
  exactly the kind of thing a hostile grader would specifically try.
- **Recommended change:** Note as an HLD-level requirement: resume and invoke actions must be idempotent per
  thread/decision, e.g. by rejecting a second resume against an already-resolved interrupt rather than
  re-executing it.

### REVARCH-012 — PARTIAL: LLM-provider failure mid-turn is unaddressed, and unflagged as an assumption
- **Requirement ID:** none directly — this is a gap in `spec.md` itself, inherited silently.
- **Exact source:** absence — no rule or graded check anywhere in `PS` addresses what happens if the LLM call
  itself (not a tool call) fails or times out during a build or execution turn.
- **Current architecture behavior:** The Builder Graph (4.5) and Execution Graph (4.6) both show dashed "LLM
  call" edges to the external LLM provider in the diagram, with no failure-handling behavior described anywhere.
- **Missing behavior:** No retry/backoff/failure state is specified for this external dependency, unlike MCP
  server failures (`FR-007`/`FR-008`, explicitly handled) or connection failures (`FR-013`, explicitly handled).
- **Risk:** Low-medium. Per `CLAUDE.md`'s "no silent assumptions" rule, this should be logged as an explicit
  assumption/gap rather than left unmentioned — right now a reader can't tell whether it was considered and
  judged out of scope, or simply not considered.
- **Recommended change:** Add a line to `spec.md §15 Assumptions` (not just here) noting that LLM-provider
  failure handling is unspecified by the brief and is being treated as a design choice, then state the chosen
  behavior (e.g., surface the failure to the user, mark the run `err`, do not silently retry) in the eventual
  HLD.

### REVARCH-013 — PARTIAL: resource-holding behavior of long-pending interrupts unaddressed
- **Requirement ID:** `NFR-006`, `NFR-007`
- **Exact source:** `spec.md` — "Persisted interrupt state must remain correctly resumable after multi-day
  waits and multiple deploys." (`PS:129-131`)
- **Current architecture behavior:** The Checkpointer/Persistence layer (4.10) is described as durable but
  nothing states whether a paused thread (e.g. a submission waiting three days for admin review) holds any
  live resource — a DB connection, a lock, an in-memory object — for the duration of the wait.
- **Missing behavior:** An explicit statement that a paused interrupt is *fully passive* at rest (no held
  connection, no held lock, no live process) and only becomes active again on resume.
- **Risk:** Low for the single-instance-tested case graded check 6 exercises (one overnight approval), but a
  real risk if the team's checkpointer implementation happens to keep a connection checked out per pending
  thread — under even a handful of concurrent long-pending approvals, that would exhaust the connection pool
  in a way that's easy to miss in a demo with only one or two agents.
- **Recommended change:** State explicitly in 4.10 (or wherever the checkpointer is chosen at HLD time) that a
  paused interrupt must be representable as pure at-rest data, not a held resource.

### REVARCH-014 — PARTIAL: no guard against configuration mutation outside the Builder Graph
- **Requirement ID:** `SEC-007`, `SEC-008`, `FR-058`
- **Exact source:** derived — the approval-gate requirements assume the configuration's approval-mode fields are
  trustworthy at execution time.
- **Current architecture behavior:** The Builder Graph (4.5) is the only component described as writing agent
  configuration. Nothing states that this is the *only* legitimate write path, or that any future edit surface
  must re-validate the same invariants (e.g., a write/destructive tool cannot be silently switched to `auto`
  approval by any path other than the Builder Graph's own logic).
- **Missing behavior:** An explicit "single writer" constraint on the configuration document.
- **Risk:** Low today (no edit feature exists yet), but forward-looking: this is exactly the kind of invariant
  that's cheap to state now and expensive to retrofit once an "edit agent" feature is added later without
  anyone re-reading `SEC-007`/`SEC-008`.
- **Recommended change:** Add one sentence to 4.5 or 4.4: any write to an agent's configuration document must
  pass through the same approval-mode validation the Builder Graph applies at creation time — there is no
  second, unvalidated write path, now or later.

### REVARCH-015 — PARTIAL: Postgres/RLS choice not labeled as a design choice at its point of use
- **Requirement ID:** `spec.md §15` A6 (persistence backend explicitly unspecified by the brief)
- **Exact source:** `spec.md` — "Checkpointer/persistence backend for LangGraph interrupt state. Unspecified
  beyond 'your own server'..." (A6)
- **Current architecture behavior:** §2 Alternative A and §4.10 state "Postgres" and "row-level security" as if
  settled, without an inline reminder that this is a design choice made here, not something `problem-statement/`
  or `spec.md` mandated.
- **Missing behavior:** A one-line disclaimer at the point Postgres is first introduced (§2), matching the
  discipline `CLAUDE.md` rule 2 and `.claude/rules/capstone.md` require for every design choice.
- **Risk:** Low — purely a documentation-discipline gap, not a functional one; the choice itself is well
  justified in §2/§3.
- **Recommended change:** Add "(a design choice — `spec.md §15` A6 leaves this open)" the first time Postgres is
  named in §2.

---

## 3. Challenge questions

**1. What components are unnecessary?**
None are unjustified outright — every one of the 12 traces to a distinct requirement cluster with a stated
"why it is not unnecessary." The one genuinely arguable case: the Builder Graph (4.5), Execution Graph (4.6),
and Review Graph (4.8) are described as three separate components, but they are really the same underlying
pattern (a LangGraph graph + checkpointer + interrupt) applied three times. That's not the same as saying one
of them is unnecessary — the *work* each does is genuinely distinct (different triggers, different interrupt
semantics, different durations) — but a leaner document could describe "one interruptible-workflow pattern,
three instances" instead of three fully separate component write-ups, if brevity mattered more than it does
here. Not a correctness problem, a possible economy-of-description one.

**2. What requirements are not represented?**
`FR-058`–`FR-060` (REVARCH-002, the worst finding here), `SEC-002` (REVARCH-001), and `DATA-007`'s special
status (REVARCH-006) are the three that matter. `FR-054`/`FR-055` and `NFR-005` are represented only
transitively (REVARCH-003, REVARCH-005) — present in spirit, not in an explicit citation.

**3. What requirement is being interpreted incorrectly?**
Not incorrectly interpreted so much as **incompletely operationalized**: `SEC-004`'s "unbounded, no named list"
guarantee is quoted correctly in §1.9 but the architecture doesn't yet show a design that actually achieves it
against the specific LangGraph-checkpoint leak path (REVARCH-009) — the requirement's *words* are right, the
design behind them isn't finished.

**4. Where can tenant isolation fail?**
Three concrete places, in order of severity: (a) the checkpointer bypassing RLS via its own connection
management (REVARCH-010) — this is the single sharpest risk in the whole document; (b) `SEC-002`'s
guessed-URL/404 guarantee having no owner outside the invoke API specifically (REVARCH-001, REVARCH-003); (c)
the marketplace deep-copy (4.9) being implemented as "copy everything except a blocklist" rather than an
explicit allowlist of safe fields — not separately numbered above, but worth naming here: a blocklist approach
means a newly added field to the agent schema is leaked-by-default until someone remembers to blocklist it,
whereas an allowlist fails safe. `architecture.md` doesn't say which approach 4.9 uses.

**5. Where can credentials leak?**
The same LangGraph-checkpoint path as REVARCH-009 is the real one — everything else (the Vault's own storage,
the "never returned" API/UI guarantee) is already well-covered by §4.4's design. The single sentence "fetch,
use, drop" is correct as a requirement restatement but is not yet backed by a design commitment about *where in
memory, and outside which serialized state,* that fetch-use-drop actually happens.

**6. What happens during server restart?**
Covered well for the "clean" case (checkpointed interrupt resumes exactly where it left off — `NFR-006`/`NFR-007`
via 4.10). Not covered: a kill mid-tool-call, where the in-flight step (potentially holding a fetched credential
in memory, per REVARCH-009) is neither cleanly checkpointed nor cleanly dropped — what state does the resumed
graph actually see, and is it guaranteed not to be a torn/partial write?

**7. What happens when approval is delayed?**
The multi-day duration itself is explicitly handled (`NFR-007`, 4.8/4.10). Not handled: whether a long wait
holds any live resource (REVARCH-013) — durability of the *data* is addressed, passivity of the *wait* is not.

**8. What happens when an external system fails?**
MCP server failure: well handled (`FR-007`/`FR-008`, degraded state, explicit and correct). LLM provider
failure: not handled at all, and not flagged as a gap either — silently absent (REVARCH-012).

**9. What prevents risky actions from bypassing approval?**
`SEC-007`/`SEC-008` are well-cited and the Execution Graph's role is clear for the *documented* write path. Two
things aren't addressed: retried/duplicated resume actions double-executing an approved action (REVARCH-011),
and any future configuration-edit surface bypassing the same validation the Builder Graph applies today
(REVARCH-014).

**10. What happens when data is duplicated/retried?**
Nowhere addressed — no idempotency mechanism for build-step confirmations, resume decisions, or invoke calls
anywhere in the document (REVARCH-011). This is a clean miss, not a partial one.

**11. Which design decisions are assumptions rather than requirements?**
Correctly labeled as such in most places (Postgres choice acknowledged as unspecified by the brief in spirit,
even if not disclaimed inline — REVARCH-015; the four self-critique points in §3 of `architecture.md` are
themselves assumption-flagging in the right spirit). The encryption algorithm, MCP client library, and exact
SPA framework are appropriately left unspecified rather than smuggled in as if required.

**12. Are there any technologies here that exist only because they are fashionable/common?**
No clear case of this — the event-broker alternative (C) was explicitly rejected for being exactly this pattern,
which is good discipline. Postgres is the closest candidate to "the default choice," but it's tied to a real
requirement (RLS for `SEC-001`) rather than chosen by habit, so it survives scrutiny — flagged in REVARCH-015
only for a documentation-discipline reason, not a fashion reason.

**13. Is this architecture too complex for this capstone?**
No. Twelve components against roughly sixty functional requirements plus fifteen security controls plus eight
workflows is proportionate, not padded, and Alternative A was explicitly chosen over two more complex options
for exactly this reason. If anything, per question 1, there's room to *simplify the description* (not the
system) by naming the three LangGraph graphs as one repeated pattern — but that's an economy-of-writing
observation, not a complexity problem with the design itself.

---

## 4. Overall score: **68 / 100** for requirement coverage

**Why not higher:** Two FAIL-grade findings (REVARCH-002, REVARCH-009, REVARCH-010 — three, really, all rated
FAIL) sit directly on top of the capstone's highest-stakes graded checks: `FR-060`'s multi-agent deliverable
(check 7), and two independent, plausible paths for the architecture's stated tenant-isolation and credential
guarantees to not actually hold once implemented the "obvious" way (checks 1 and 2). These aren't
documentation nits — they're places where a team building from this document as written could produce a system
that looks compliant and isn't. `SEC-002` having no owner (REVARCH-001) compounds the tenant-isolation risk
further. And the missing `specs/traceability.md` source is a genuine process gap, not just a formatting one.

**Why not lower:** Every one of the eight workflow requirements (`WF-001`–`WF-008`) is explicitly and correctly
covered with no gaps found. The vast majority of functional and security requirements are correctly cited.
The three alternatives comparison and the self-argument-against section are genuinely rigorous — this document
already does more adversarial self-checking than most architecture proposals do, which is exactly why the gaps
that remain (checkpoint-credential-leak, checkpointer-RLS-bypass, the FR-058-060 citation gap) are worth taking
seriously rather than dismissing as sloppiness: they're the specific, sharp things that survive a first pass of
self-review and need a second, adversarial one — which is what this document is.

**Do not fix these yet** — per the instruction, `architecture.md` is not modified here. This score and the
fifteen findings above are the input to the next ARCHITECTURE REVIEW iteration.

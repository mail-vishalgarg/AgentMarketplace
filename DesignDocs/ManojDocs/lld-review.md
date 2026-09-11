# Hostile LLD Audit — architecture/lld.md

**Role:** hostile auditor of the full chain. **Not** a design pass — `lld.md` is not modified here.
**Audited against:** `problem-statement/`, `specs/spec.md`, `architecture/architecture.md`, `architecture/hld.md`,
`architecture/lld.md`, and every prior review's approved findings (checking they actually survived two more
layers of decomposition, not just one).

**Method:** for every requirement ID, the chain REQUIREMENT → ARCHITECTURE (component) → HLD (interface) → LLD
(table/endpoint/mechanism) was walked. ~130 of ~140 requirement chains are unbroken and are not re-litigated
here — this document is the ~17 places the chain actually breaks, snaps, or contradicts itself, organized by
the fourteen categories requested, each finding marked CRITICAL/HIGH/MEDIUM/LOW.

**Headline:** the discipline held up well across two review cycles for the *big* risks (RLS-exception logic,
credential-in-checkpoint, idempotency) — but this pass found that fixing those exact risks last time introduced
**two new critical bugs of its own**, both from interactions between fixes rather than from carelessness: the
atomic resume fix (HLDREV-005) created a crash window between "mark resolved" and "actually do the approved
action," and the visibility-toggle fix (HLDREV-002) was specified with a broader authorization shape than HLD's
own text allows. Neither is hypothetical — both are directly implementable-as-written bugs.

---

## Findings by category

### 1. Missing implementation

**LLD-001 — HIGH.** `GET /connections` (list) is absent from `lld.md §4`'s endpoint table. `FR-014` requires
the Connections screen to show a table of every connection (server, status, masked secret, added, last used) —
there is no read endpoint anywhere in the chain to populate it. `POST /connections` and `DELETE /connections/
{id}` exist; the list read doesn't. **Chain:** `FR-014` → architecture 4.4 (owned data includes the list) → HLD
1.4 (no interface named for listing, an HLD-level gap that propagated) → LLD (never added). **Risk:** the
Connections screen literally cannot be built from this API surface. **Recommendation:** add `GET /connections`
to §4, company+owner scoped.

**LLD-002 — HIGH.** No read endpoint exists for the `pending_classification` admin view. D2 explicitly added a
new UI surface ("servers pending classification," `hld.md §1.12`) with no source mockup — and LLD gives it a
write endpoint (`POST /servers/{id}/tools/{tool_id}/classify`) but never a corresponding read endpoint to
discover *which* tools are pending in the first place. **Chain:** D2 (HLD decision) → HLD 1.3/1.12 (view named)
→ LLD (write-only, read missing). **Risk:** the one piece of net-new functionality this whole design chain
added cannot actually be implemented as specified — an admin has no way to see what needs classifying.
**Recommendation:** add `GET /servers/pending-classification` (or a filter on `GET /servers`), admin-scoped.

### 2. Contradictions

**LLD-003 — MEDIUM-HIGH.** `diagrams/lld.mmd`'s header comment states "`scores`/`checks` inherit the [RLS]
exception once their agent is published" — but `lld.md §9`'s actual schema never gives `scores`/`checks` an RLS
exception at all. What `lld.md` actually does is **snapshot** `score_snapshot`/`grade_snapshot` directly into
`marketplace_listings` at publish time (which *is* a valid, arguably better way to satisfy `hld.md §4`'s third
exception) — but the diagram comment describes a different mechanism (live-table inheritance) than the schema
implements (denormalized snapshot). One of these two documents is wrong about how the other one works.
**Chain:** `hld.md §4` (three exceptions named) → LLD schema (snapshot approach, undocumented as the chosen
resolution) → LLD diagram (describes the *other* approach). **Recommendation:** pick one description and state
it in both places — the snapshot approach is the better answer (no live RLS exception needed on `scores` at
all), so the diagram comment is what should change.

**LLD-004 — MEDIUM.** `lld.md §9`'s `idempotency_keys` table declares `client_request_id` as the **sole primary
key**, but `§11` defines a separate `UNIQUE INDEX ON idempotency_keys(client_request_id, endpoint)`, and `§12`/
`§13` describe the dedup logic as `INSERT ... ON CONFLICT (client_request_id, endpoint) DO NOTHING`. If
`client_request_id` alone is the PK, it is already globally unique on its own — the composite unique index is
redundant at best, and the `ON CONFLICT (client_request_id, endpoint)` clause **references a constraint that
doesn't exist** (Postgres requires the conflict target to match an actual unique constraint/index; a
single-column PK doesn't satisfy a two-column conflict target). As written, this does not run. **Chain:** HLD
D9 (dedup key named, not column-shaped) → LLD schema (PK) vs. LLD transaction logic (composite conflict target)
— the two LLD sections disagree with each other. **Recommendation:** make the PK the composite
`(client_request_id, endpoint)`, drop the redundant separate index.

### 3. Unspecified data

**LLD-005 — MEDIUM.** `agents.status` has no `CHECK` constraint anywhere in `lld.md §9`, unlike every other
enum-shaped column in the schema (`visibility`, `risk_status`, `risk_level`, `connections.status`,
`submissions.status`, `checkpoints.status` all have explicit `CHECK IN (...)` lists). `spec.md DATA-006`
enumerates five values (`draft`/`live`/`pending_review`/`published`/`degraded`) that never made it into the LLD
schema. **Chain:** `DATA-006` → architecture (implicit) → HLD (implicit) → LLD (dropped). **Recommendation:**
add the `CHECK` constraint; audit the rest of `§9` for the same pattern (`runs.trigger` has the same gap, see
LLD-013).

### 4. Missing states

**LLD-006 — HIGH.** `lld.md §14` diagrams state machines for Server, Tool, Connection, Submission, and
Checkpoint — but **not for `Agent` itself**, despite `Agent` being the richest-status, most central entity in
the whole schema (`draft → live ↔ degraded → pending_review → published`, per `DATA-006`) and the one every
other diagram references *into* (Connection's diagram says "triggers dependent agents -> degraded" without ever
showing what that transition looks like from the Agent side). "Missing states" was named explicitly as an audit
category, and this is the clearest instance of it: an entire entity's lifecycle was never diagrammed at all, not
just a transition within one. **Recommendation:** add the Agent state diagram to `§14`, including the still-open
question of exactly how `pending_review`/`published`/back-to-`live` synchronizes with `submissions.status`
(see LLD-011).

### 5. Missing API behavior

*(Overlaps LLD-001/002 above, which are the sharpest instances — no additional distinct finding beyond noting
both belong here too.)*

### 6. Missing authorization checks

**LLD-007 — CRITICAL.** `PATCH /agents/{id}/visibility` (`setVisibility`) is labeled `company+owner or admin`
in `lld.md §4`'s endpoint table — but `§7`'s definition of the "company+owner" `ScopeGuard` shape is: proceed if
`owner_user_id == caller` **OR** `visibility == 'shared_with_company'` **OR** `caller.is_admin`. Applied to a
**mutation** endpoint, that third disjunct means **any user the agent has been shared with can also call this
endpoint** — including to *revoke* the sharing or otherwise change it — directly contradicting `hld.md §1.5`'s
own explicit text: *"Owner-only; an admin may also invoke it... no other caller can."* This is the exact
generic-read shape reused for a mutation without narrowing it, and it is a genuine privilege-escalation path: a
colleague who can merely *view* a shared agent can also currently *change who else can see it*. **Chain:** D1/
D2's `setVisibility` fix (HLD, closing HLDREV-002) → LLD endpoint table (shape mislabeled). **Recommendation:**
this endpoint needs a **fourth, stricter shape** ("owner-or-admin, not shared-viewer") distinct from the generic
company+owner read shape — `§7`'s three-shape taxonomy is insufficient as written for every mutation on an
owner-scoped resource, not just this one; audit every `PATCH`/`DELETE` against the same risk.

**LLD-008 — MEDIUM.** The same generic "company+owner" shape is applied to `DELETE /connections/{id}`, but
`connections` (`§9`) has **no `visibility` column at all** — the shape's "OR `visibility == shared`" clause has
nothing to evaluate against for this table. Either the `ScopeGuard` implementation special-cases
resource-types that lack a `visibility` column (undocumented), or the abstraction silently doesn't apply and
this endpoint is actually a plain `owner`-only check mislabeled with a name that implies more. **Recommendation:**
same fix as LLD-007 — stop treating "company+owner" as one reusable shape; name what each endpoint actually
requires.

### 7. Tenant isolation bypasses

**LLD-009 — HIGH.** The RLS policy itself — the single mechanism `SEC-001` and graded check 1 are about — is
described only in prose (`§7`, `§8`) across the entire document chain. No `CREATE POLICY` statement, no actual
predicate SQL, appears anywhere in `architecture.md`, `hld.md`, or `lld.md`. Given that this exact class of
mechanism has already produced two real bugs earlier in this chain (`architecture-review.md` REVARCH-010,
`hld-review.md` HLDREV-001), leaving the literal policy text unwritten at the layer that's supposed to be
"concrete enough to implement from" is a genuine gap, not a stylistic one — an AND/OR mistake in the real policy
(exactly the class of error REVARCH-010 warned about generically) currently has no artifact in this repository
that could catch it before it's written directly into a migration. **Recommendation:** LLD REVIEW should not
close without the actual `CREATE POLICY` SQL for at least `agents` (the two-predicate case) appearing in `§9`.

**LLD-010 — MEDIUM.** `GET /marketplace`/`GET /marketplace/{id}` are labeled `company (RLS exception, hld.md
§4)` in the endpoint table — but `§7` only defines three `ScopeGuard` shapes (company / company+owner / admin),
**none of which is "public/global-read."** "Company (RLS exception)" is a fourth, undocumented shape smuggled
into the endpoint table without ever being added to the taxonomy that's supposed to define all possible shapes.
Implemented literally against `§7`'s three-shape definition, a marketplace request would either be rejected
(no `company_id` to match, since a listing isn't scoped to the caller's company) or mis-evaluated. **Chain:**
`hld.md §4` (exception named) → LLD `§7` (taxonomy never extended) → LLD `§4` (endpoint table assumes a shape
that doesn't exist). **Recommendation:** add a fourth shape, "public," to `§7`'s taxonomy explicitly.

### 8. Credential leakage paths

**LLD-011 — HIGH.** `§23`'s log-redaction rule strips credential-shaped fields from **log records**, but
nothing sanitizes `runs.outcome_text` before it's written to the database. A failing tool call against a
misconfigured or malicious MCP server can plausibly echo request detail (including an auth header or token
fragment) back in its error response; if that raw error text becomes `outcome_text` verbatim, a credential can
land in a column `SEC-004`'s "unbounded, no named list" guarantee explicitly covers — and `runs` is a normal,
frequently-displayed table (the Runs tab, `FR-033`), not a buried log file. This is a distinct leak path from
the one `architecture-review.md` REVARCH-009 already closed (LangGraph checkpoint state) and the one `§23`
already closes (logs) — a third surface, unaddressed. **Recommendation:** the same redaction filter used for
logs needs to run on `outcome_text` (and any other free-text field sourced from a tool-call error) before
persistence, not just before logging.

### 9. Retry/idempotency problems

*(LLD-004's PK/unique-index contradiction, above, belongs here too — no additional distinct finding.)*

### 10. Restart/recovery problems

**LLD-012 — CRITICAL.** The atomic-conditional-UPDATE fix for HLDREV-005's race condition (`§12`: `UPDATE
checkpoints SET status='resolved' ... WHERE status='pending' RETURNING *`) solves the *race* between two
concurrent resume attempts — but it does so by marking the interrupt **resolved before the approved action has
actually executed**. The approved action itself (calling an external MCP tool, or advancing the Builder graph)
is necessarily a *separate* step after that database write — it cannot be inside the same transaction, because
it's a network call to an external system. If the process crashes between "mark resolved" and "actually run the
tool call," the interrupt is now permanently `resolved` — and `IdempotencyGuard`/the atomic-update pattern will
treat any retry as "already resolved" and refuse to re-run it — **silently dropping the approved action** with
no way to recover it. This is a new, more severe failure mode than the one HLDREV-005 fixed: the old bug was a
race that could double-execute; the new one is a crash window that can **lose** an approved write/destructive
action entirely, which is arguably worse given `SEC-007`'s stakes (a human approved something that then
silently never happened, with the system reporting it as resolved). **Chain:** `hld-review.md` HLDREV-005 (fix
requested) → `lld.md §12` (fix applied) → this audit (the fix's own new failure mode, undetected until now).
**Recommendation:** needs an outbox-style pattern — mark "resolving" (not yet "resolved"), execute the action,
then mark "resolved" only on confirmed completion, with a recovery path for "resolving" rows found stuck on
restart. This is a real design gap, not a nitpick — flagging for LLD REVIEW, not fixing here per instruction.

### 11. Approval bypasses

*(LLD-007, above, is the sharpest finding in this category — a genuine bypass of the intended owner/admin-only
control on `setVisibility`.)*

**LLD-013 — MEDIUM.** No lock or guard is specified preventing a new `startBuild` (editing/rebuilding) on an
agent that has a `Submission` currently `pending` review. Currently narrow in practice (no config-edit path
exists besides the Builder Graph's initial write, per the single-writer constraint), but if `FR-024`'s
still-open follow-up-edit mechanism (`spec.md §16` item 8) is ever resolved as "re-enter the Builder Graph,"
this becomes a real gap: an agent's tools/approval-gating could change *while* an admin is mid-review of the
version they were shown, without the gate-check re-running. **Recommendation:** note as a constraint to address
when `FR-024`'s mechanism is finally decided, not urgent today.

### 12. Inconsistent schemas

**LLD-014 — MEDIUM.** `runs.trigger` has no `CHECK`/enum constraint (should be `'schedule'|'playground'|'api'`
per `DATA-011`) — the same pattern as LLD-005, on a second column.

**LLD-015 — MEDIUM.** No stated synchronization rule between `agents.status` and `submissions.status`. Both
tables independently track overlapping "is this agent in review" state (an agent presumably moves to
`pending_review` when a `Submission` is created, and back to `live` or to `published` depending on the
decision) — but nothing in `§9`/`§12` states which write updates the other, or whether they're updated in the
same transaction. Two tables tracking the same real-world fact without an explicit sync rule is a standing
data-integrity risk. **Recommendation:** state explicitly that `1.7`'s `submit()`/`decide()` transactions also
write `agents.status` in the same transaction, not a separate step.

*(LLD-003, the scores/checks contradiction, also belongs in this category.)*

### 13. Over-engineering

No significant finding. The chain has been consistently disciplined — Alternative A was correctly chosen and
defended, no premature abstraction or unjustified infrastructure was found in `lld.md` itself. One **LOW** note:
the import-linter rule enforcing "only `vault/` imports crypto" (`§1`) and the equivalent rule for
`persistence/`'s connection monopoly (`§8`) are process/tooling additions with a real justification each
(`SEC-003`–`006`, `SEC-001`) but no requirement literally asks for CI-enforced import boundaries — a reasonable,
cheap choice, not a defect, noted only because the audit category was explicitly requested.

### 14. Implementation choices without justification

**LLD-016 — LOW.** `§22`'s "logged with a correlation ID" is stated as fact without the `(implementation
choice)` tag every other unrequired detail in this document consistently carries. Trivial, but worth fixing for
the same consistency reason `hld-review.md` flagged smaller labeling gaps.

**LLD-017 — LOW.** `§13`'s health-check-vs-in-flight-build race is explicitly accepted rather than solved — this
is correctly labeled `(implementation choice, not solved)`, which is the right way to handle it; noted here only
as a positive example, not a finding, so the "every element must be labeled" instruction's compliance is visible
in both directions (what's missing a label, and what has one correctly).

---

## Severity summary

| Severity | Count | IDs |
|---|---|---|
| CRITICAL | 3 | LLD-007, LLD-009, LLD-012 |
| HIGH | 6 | LLD-001, LLD-002, LLD-006, LLD-009 *(listed once, see above)*, LLD-011, and LLD-003 at the upper end of its MEDIUM-HIGH range |
| MEDIUM | 7 | LLD-003, LLD-004, LLD-005, LLD-010, LLD-013, LLD-014, LLD-015 |
| LOW | 2 | LLD-016, LLD-017 |

**The three CRITICALs share one root cause worth naming explicitly:** all three are *not* failures to apply the
prior reviews' fixes — they are cases where a fix from `architecture-review.md` or `hld-review.md` was applied
correctly in isolation but had a consequence, one layer down, that nobody checked for: the resume-atomicity fix
(HLDREV-005) created a new crash-recovery gap (LLD-012); the visibility-toggle fix (HLDREV-002) was specified
with an authorization shape too broad for its own stated rule (LLD-007); and the RLS-exception fix (HLDREV-001)
was never followed all the way down to an actual, auditable policy statement (LLD-009). This is the specific
risk of a long review chain: each pass correctly closes what it's looking at and correctly doesn't repeat the
whole audit — which is exactly why a fresh, full-chain pass at the end still finds real things.

`lld.md` was not modified by this review, per instruction.

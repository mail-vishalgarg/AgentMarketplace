# Multi-Hat Review of architecture/hld.md

**Roles:** senior solution architect · security reviewer · capstone evaluator. **Not** a design pass — nothing
in `hld.md` is modified here. **Audited against:** `problem-statement/`, `specs/spec.md`,
`architecture/architecture.md`, `specs/traceability.md`, and `architecture/architecture-review.md`'s already-
approved findings (to check they actually survived the HLD decomposition, not just the architecture revision).

**Headline, all three hats agree on:** `hld.md` is a careful, honest decomposition — it correctly carries
forward every constraint the last architecture review forced (credential-never-checkpointed, checkpointer-RLS
discipline, single-writer config, allowlist marketplace copy, passive-at-rest interrupts), and it's unusually
disciplined about labeling assumptions and leaving genuinely open questions open rather than guessing. The
findings below are real, but they sit on top of a solid base, not a shaky one.

---

## 1. Architecture → HLD component crosswalk

`hld.md` never states this table explicitly — reconstructed here as part of answering "is there a corresponding
HLD component for every architecture component."

| `architecture.md` §4 | `hld.md` §1 | Corresponding? | Responsibility preserved? | Added w/o justification? | Missing? |
|---|---|---|---|---|---|
| 4.1 API Layer | 1.1 API Layer | Yes | Yes, expanded (ScopeGuard, idempotency ledger) | No — both trace to D1/D9 | No |
| 4.2 Identity & Session | 1.2 Identity & Session | Yes | Yes, unchanged | No | Provisioning (D3) — open by choice, not a defect |
| 4.3 MCP Registry & Introspection | 1.3 MCP Registry & Introspection | Yes | Yes, expanded (`pending_classification`, D2) | No — user-approved, explicitly disclosed | See HLDREV-012 (filter granularity) |
| 4.4 Credential Vault | 1.4 Credential Vault | Yes | Yes, unchanged | No | No |
| 4.5 Agent Builder Graph | 1.5 Agent Builder Graph | Yes | Yes, expanded (`owner_user_id`/`visibility`, D1) | No | See HLDREV-002 (visibility-change op) |
| 4.6 Agent Execution Graph | 1.6 Agent Execution Graph | Yes | Yes, unchanged | No | See HLDREV-010 (FR-030 under-described) |
| 4.7 Scoring Engine | 1.9 Scoring Engine | Yes (reordered, see HLDREV-011) | Yes, unchanged | No | No |
| 4.8 Publish & Admin Review Graph | 1.7 Publish & Admin Review Graph | Yes | Yes, unchanged | No | No |
| 4.9 Marketplace & Install | 1.8 Marketplace & Install | Yes | Yes, unchanged | No | See HLDREV-001 (RLS exception) |
| 4.10 Checkpointer / Persistence | 1.10 Persistence Layer | Yes | Yes, expanded (two-predicate RLS, D1/D6) | No | See HLDREV-001, HLDREV-008 |
| 4.11 Public Agent API + Postman | 1.11 Public Agent API + Postman | Yes | Yes, unchanged | No | See HLDREV-007 (stream caveat dropped) |
| 4.12 Frontend (SPA) | 1.12 Frontend | Yes | Yes, expanded (pending-classification view, D2) | No — user-approved | No |

**Verdict on the four consistency questions, in aggregate:** every architecture component has exactly one HLD
counterpart (12 → 12, none added, none removed, none merged/split). Every expansion beyond architecture.md
traces to an explicit D1-D9 decision, not an invented one. The gaps found are omissions (something D1/D2 imply
but HLD doesn't yet specify), not unjustified additions.

---

## 2. Findings

### HLDREV-001 — FAIL (architect + security): stated RLS rule contradicts tables that must be cross-company-readable
- **Component(s):** 1.10 Persistence Layer; consumers: 1.7 (Submission), 1.8 (MarketplaceListing), 1.9 (Score/
  Grade once published).
- **Source:** `hld.md` §3 Persistence Interactions: "Hard company boundary (`company_id`) — every table, no
  exceptions, enforced by RLS independent of application code."
- **Current HLD behavior:** This is stated as a universal rule with no carve-out.
- **Problem:** At least three owned-data entities structurally *require* cross-company visibility by the
  capstone's own requirements, and the stated RLS rule as written would block all three:
  - `MarketplaceListing` (1.8) — `FR-049`/`FR-050` require every company to be able to browse it. A blanket
    `company_id`-scoped RLS row-policy has no `company_id` to match against for a listing that isn't "owned" by
    the viewing company at all.
  - `Submission` (1.7) — the admin reviewer (`SEC-012`) must see submissions originating from *every* company,
    not just their own; "every table, no exceptions" on a hard company boundary directly conflicts with that.
  - Published `Score`/`Grade` (1.9) — once an agent is listed, its score is shown on the public listing
    (`FR-050`) to installers in other companies.
- **Risk:** As literally written, this is not a security gap — it's the opposite, an over-restrictive rule that
  would make the marketplace and admin review *non-functional* if implemented exactly as stated. That's still a
  real defect: a team implementing HLD literally either breaks the marketplace/review, or (more likely, and
  worse) "fixes" it ad hoc with an unreviewed RLS exception under time pressure — precisely the kind of
  undisciplined patch `architecture.md §3` warned against.
- **Recommendation:** State the RLS rule with its necessary exceptions explicit, not implicit: company-scoped
  tables (most of them) get the hard `company_id` predicate; `MarketplaceListing` is globally readable once
  published, writable only via 1.8's `publish()`; `Submission` is readable by its owning company **or** any
  admin, not company-scoped alone.
- **Confidence:** High.

### HLDREV-002 — FAIL (architect + security): the visibility-toggle operation that justified D1 doesn't exist anywhere in HLD
- **Component(s):** 1.5 Agent Builder Graph, 1.1 API Layer.
- **Source:** D1's own justification, `hld.md` §0: the `AGENT` Settings tab's "Private to you" card has an
  explicit **"Change"** button — the literal UI affordance that made the per-user RLS dimension real enough to
  choose company+owner over company-only.
- **Current HLD behavior:** `Agent.owner_user_id`/`visibility` are specified as fields (1.5's owned data,
  1.10's RLS predicate), set once at creation (`visibility = private_to_owner` by default). No component's
  interface list includes any operation to *change* visibility afterward.
- **Problem:** The feature that drove the architectural decision isn't represented as a capability anywhere in
  the resulting design. Nothing states who can call it (owner only? owner or admin?), what it validates, or
  which component owns the mutation.
- **Risk:** Medium — not a security hole today (nothing exists to misuse), but a real design incompleteness:
  the two-dimensional RLS model was adopted specifically to support this, and as written it can't actually be
  exercised.
- **Recommendation:** Add `shareWithCompany(agentId, ownerUserId) → Agent` (and its inverse) to 1.5 or 1.1,
  owner-only, with a note on whether an admin can also toggle it on another user's agent.
- **Confidence:** High.

### HLDREV-003 — PARTIAL (evaluator, cross-document consistency): spec.md/architecture.md not updated to match HLD's resolved decisions
- **Component(s):** N/A — document-level.
- **Source:** `hld.md` §0 itself: "D1/D2 effectively resolve `spec.md §16` items 10 and 11... This document
  does not edit `spec.md` or `architecture.md`... both should be updated... in a follow-up."
- **Current HLD behavior:** Self-disclosed, not silently hidden — credit where due. But the practical state
  right now is that `spec.md §16` and `architecture.md`'s "Carried-forward open items" both still list items 10
  and 11 as open, while `hld.md` treats them as settled.
- **Problem:** A reader who opens `spec.md` or `architecture.md` alone, without also having read `hld.md §0`,
  will believe D1/D2 are unresolved. Three documents currently disagree about the state of the same two
  questions.
- **Risk:** Low-medium — self-disclosed drift is much cheaper to fix than undisclosed drift, but it's still
  drift, and it compounds every time another document is layered on without the earlier ones being reconciled.
- **Recommendation:** The already-planned follow-up (update `spec.md §16` items 10/11 and `architecture.md`'s
  open-items list) should happen before HLD REVIEW is considered closed, not deferred indefinitely.
- **Confidence:** High.

### HLDREV-004 — PARTIAL (security + architect, retries): idempotency (D9) covers resume/invoke, not the initial state-creating calls
- **Component(s):** 1.5 (`startBuild`), 1.7 (`submit`), 1.8 (`install`).
- **Source:** `hld.md` §0 D9: "No client-supplied key needed — a resume action is already uniquely addressed by
  `(thread_id, decision)`."
- **Current HLD behavior:** D9's guarantee is scoped explicitly to resume/invoke actions on an *existing*
  thread. `startBuild`, `submit`, and `install` are the calls that *create* a new thread/record in the first
  place, and none of the three have a stated dedup behavior.
- **Problem:** A client retry (network blip, double-click, a naive frontend retry-on-timeout) on any of these
  three calls has no architectural guard against creating a second Builder thread for one logical build request,
  a second `Submission` for one publish click, or a second installed copy for one install click.
- **Risk:** Medium. Not a security violation on its own, but a real correctness/data-integrity gap, and exactly
  the kind of thing a hostile grader clicking a button twice during the demo would surface.
- **Recommendation:** Extend the idempotency requirement to these three creating calls too — e.g., a
  client-supplied request ID, or a natural key (one build thread per `(agent_id_being_built_or_none,
  timestamp_bucket)` is too fragile; a client-generated UUID per submit action is simpler and consistent with
  how resume already works).
- **Confidence:** Medium-high.

### HLDREV-005 — PARTIAL (architect, workflow resume/concurrency): no stated atomicity for the resume idempotency check
- **Component(s):** 1.1 API Layer, 1.10 Persistence Layer.
- **Source:** `hld.md` §0 D9 / §1.1: "the Persistence Layer enforces at-most-once by rejecting a resume against
  an already-resolved interrupt."
- **Current HLD behavior:** Described as a check-then-act guarantee without stating it must be one atomic
  operation.
- **Problem:** If "check not yet resolved" and "mark resolved and act" are two separate steps, two
  near-simultaneous resume calls (e.g., a double-click landing on two different app instances, or one request
  retried while the first is still in flight) can both pass the check before either commits, both proceeding to
  execute — reintroducing exactly the risk D9 was written to close.
- **Risk:** Medium — a race window, not a guaranteed bug, but the kind of thing that's invisible in a
  single-user demo and real under any concurrent load.
- **Recommendation:** State explicitly that resume resolution is a single atomic conditional write (e.g., an
  UPDATE ... WHERE status = 'pending' returning the prior row, checked by the caller), not a read followed by a
  write.
- **Confidence:** Medium.

### HLDREV-006 — PARTIAL (evaluator, testability): architecture.md's graded-check mapping wasn't carried into HLD
- **Component(s):** N/A — document-level, testability.
- **Source:** `architecture.md §5` (added during the last revision, closing REVARCH-007): an explicit table
  mapping every `TEST-00X` to the components it exercises.
- **Current HLD behavior:** `hld.md` has no equivalent table at the HLD's own, more granular, component/
  interface level.
- **Problem:** This is a regression in an otherwise-improving chain: the parent document (`architecture.md`)
  gained exactly this table last review specifically because testability was flagged as a gap; the child
  document, one layer more detailed, doesn't carry or refine it.
- **Risk:** Low-medium — the information is recoverable from `architecture.md §5` plus the requirement-ID
  citations already in `hld.md §1`, but it's not assembled anywhere, which is the same "implicit not explicit"
  problem REVARCH-007 originally flagged.
- **Recommendation:** Add a short HLD-level testability table (or explicitly reference and confirm
  `architecture.md §5` still holds unchanged at this granularity, which — based on this review — it does, modulo
  HLDREV-001 through HLDREV-005's fixes).
- **Confidence:** Medium.

### HLDREV-007 — PARTIAL (evaluator, API behavior/traceability): the streaming endpoint's contested scope isn't carried into HLD
- **Component(s):** 1.11 Public Agent API + Postman Export.
- **Source:** `spec.md §16` item 4 / `traceability.md` (API-002 confidence: Low, flagged as conflicting with the
  "if you finish early" stretch-goal listing); `architecture.md §11` (API-002 marked P1/arguably-out-of-MVP).
- **Current HLD behavior:** `hld.md §1.11`'s interface list states `POST /agents/:id/stream` alongside
  invoke/resume/postman with no caveat.
- **Problem:** A reader of `hld.md` alone would not know this endpoint's inclusion is contested elsewhere in the
  document chain — the ambiguity that two upstream documents were careful to preserve gets silently flattened
  into an unqualified interface entry here.
- **Risk:** Low — mostly a documentation-fidelity issue, but exactly the kind of flattening that, repeated
  across a few more documents, quietly turns "maybe" into "definitely."
- **Recommendation:** Carry the same caveat forward: mark `/stream` as P1/scope-pending `spec.md §16` item 4 in
  1.11's interface list.
- **Confidence:** Medium.

### HLDREV-008 — PARTIAL (architect, persistence/maintainability): dual connection pools are two places to get RLS discipline right
- **Component(s):** 1.10 Persistence Layer.
- **Source:** `hld.md §1.10`: "Two logical connection pools sharing the same RLS discipline: a session-scoped
  app pool... and a checkpoint pool... same discipline per D6."
- **Current HLD behavior:** States both pools must share the discipline; doesn't name a single mechanism
  ensuring they actually do.
- **Problem:** Two independently-implemented pools mean two independent places the `company_id`/`owner_user_id`
  session-variable-setting code has to be written correctly — and stay correct as the codebase changes. This is
  the same class of risk `architecture-review.md` REVARCH-010 named for a single pool, now doubled.
- **Risk:** Low-medium — a maintainability/drift risk more than an immediate defect.
- **Recommendation:** Note that both pools should share one connection-acquisition helper that sets the RLS
  session variables, rather than two independent implementations — this is still HLD-appropriate (an interface
  constraint, not a class definition).
- **Confidence:** Medium.

### HLDREV-009 — Minor (security): no mention of validating/sanitizing external MCP server content
- **Component(s):** 1.3 MCP Registry & Introspection, 1.6 Agent Execution Graph.
- **Source:** `architecture.md §1.5` trust boundary 4: "the platform must not blindly trust a server's
  self-reported tool metadata" (named there specifically re: risk classification).
- **Current HLD behavior:** No mention anywhere of validating or sanitizing tool names/descriptions/results
  returned by an external MCP server before they're stored, displayed, or passed into an LLM prompt.
- **Problem:** A malicious or compromised MCP server could return adversarially-crafted tool descriptions aimed
  at manipulating agent behavior — a known risk class for MCP-based systems generally. Not directly named by
  any graded check, but a natural extension of a trust boundary this project's own architecture already
  acknowledged in a narrower form.
- **Risk:** Low for grading purposes (not tested by the nine checks), but real for a "senior security reviewer"
  hat to name.
- **Recommendation:** Note as a forward-looking LLD/implementation concern; not blocking for this capstone's
  grading, but worth one sentence rather than silence.
- **Confidence:** Low-medium (speculative risk, not source-grounded the way the other findings are).

### HLDREV-010 — Minor (evaluator, consistency): FR-030 nominally cited, not described
- **Component(s):** 1.6 Agent Execution Graph.
- **Source:** `spec.md` `FR-030` (thumbs up/down feeds the score).
- **Current HLD behavior:** `FR-030` falls inside 1.6's cited range (`FR-025`–`FR-038`), but the component's
  responsibility/output text never mentions feedback capture explicitly.
- **Problem:** Same pattern `architecture-review.md` REVARCH-004 already flagged once for `FR-024` — a range
  citation implying coverage a reader can't actually verify from the prose.
- **Risk:** Low.
- **Recommendation:** Add one clause to 1.6's responsibilities: "records thumbs up/down feedback per response,
  forwarded to 1.9."
- **Confidence:** High (simple textual gap, easy to confirm).

### HLDREV-011 — Minor (evaluator, document usability): no explicit architecture-ID ↔ HLD-ID crosswalk, and Scoring Engine reordered without comment
- **Component(s):** N/A — document-level.
- **Source:** N/A — absence.
- **Current HLD behavior:** `hld.md §1` renumbers all twelve components 1.1-1.12 in a different order than
  `architecture.md §4`'s 4.1-4.12 (Scoring Engine moves from position 7 to position 9, after Marketplace instead
  of before Review), with no table or note explaining the mapping.
- **Problem:** Harmless functionally — confirmed by this review's own §1 crosswalk that all twelve correspond
  1:1 — but it makes exactly the audit this document was commissioned to do slower than necessary, and would
  slow down anyone else cross-referencing the two documents too.
- **Risk:** Very low — cosmetic.
- **Recommendation:** Add the crosswalk table from this review's §1 into `hld.md` directly (or keep the same
  ordering as `architecture.md` next revision).
- **Confidence:** High.

### HLDREV-012 — Minor (architect, MCP registry granularity): tool-selection filtering granularity unspecified
- **Component(s):** 1.3 MCP Registry & Introspection, 1.5 Agent Builder Graph.
- **Source:** `hld.md §1.5`: "propose tools (only non-pending ones, per 1.3)."
- **Current HLD behavior:** Doesn't state whether filtering is per-tool (a server with 3 confirmed + 2 pending
  tools is still usable, minus the pending two) or per-server (the whole server is hidden from proposal until
  every tool on it is classified).
- **Problem:** This is a real behavioral fork in the Builder's search interface contract — arguably HLD-
  appropriate to pin down (it's an interface behavior question, not a column/class detail), not just LLD noise.
- **Risk:** Low — either answer is defensible, but leaving it unstated risks the two components (1.3's search
  implementation and 1.5's consumption of it) being built to different assumptions.
- **Recommendation:** State explicitly: per-tool filtering (the more usable default, and consistent with D2's
  framing of classification as a per-tool state).
- **Confidence:** Medium.

---

## 3. Named-topic summary

- **Security:** Solid on credential handling (1.4/1.6, REVARCH-009 constraint verified present) and on the
  approval gate (`SEC-007`/`008`, 1.6). Weakened by HLDREV-001 (RLS-exception contradiction) and HLDREV-002
  (missing visibility-change authorization). D8's single static encryption key has no rotation/blast-radius
  discussion — acceptable given no-paid-account constraints, but worth a one-line note in a future pass.
- **Tenant boundaries:** The two-predicate model (company + owner/visibility) is a genuinely good design for
  the settled D1 decision — undermined only by HLDREV-001's contradiction for the tables that must cross it on
  purpose.
- **Persistence:** Correctly distinguishes domain data from checkpoint state and requires matching RLS
  discipline for both (closing REVARCH-010) — HLDREV-008 is a real but secondary maintainability concern on top
  of an otherwise sound design.
- **Workflow resume:** `NFR-006`/`NFR-007` well covered for all three graphs; HLDREV-005's atomicity gap and
  HLDREV-004's broader-than-resume idempotency gap are the two real holes.
- **Retries:** See HLDREV-004 — the single weakest topic in this review; D9 solved the narrower "resume" case
  well and stopped one step short of the general problem.
- **Human approval:** `SEC-007`/`008` and the interrupt mechanics are correctly and completely represented; no
  finding here beyond HLDREV-005's general resume-atomicity concern, which also applies to approval decisions.
- **External integrations:** MCP/LLM/Postman boundaries are named; HLDREV-009 (content validation) is a minor,
  non-blocking addition worth a sentence.
- **API behavior:** 404-masking and idempotency are well-centralized in 1.1; HLDREV-007 is the one place a
  known ambiguity from upstream documents got flattened rather than preserved.
- **Testability:** HLDREV-006 — the one place this document is measurably less complete than its own parent
  (`architecture.md`), which is worth fixing precisely because it's easy to fix (assembly, not new design work).

---

## 4. Overall read

No numeric score was requested this time, so none is invented here. Qualitatively: this HLD is **structurally
sound and honestly self-disclosing**, with two FAIL-grade findings (HLDREV-001, HLDREV-002) that both trace
directly back to D1 — the decision with the most genuine ambiguity in the whole document — and neither is a
sign of carelessness so much as D1 being adopted without fully working through its consequences everywhere it
touches. The remaining ten findings are real but secondary: a mix of scope-preservation slips (HLDREV-004,
HLDREV-007, HLDREV-010), one process/consistency gap this document already flagged on itself (HLDREV-003), and
several document-quality items (HLDREV-006, HLDREV-008, HLDREV-011, HLDREV-012) that improve rigor without
indicating a design flaw. **Recommendation: close HLDREV-001 and HLDREV-002 before proceeding to LLD** — both
are cheap to fix and both sit directly on top of `SEC-001`/`SEC-012`/`FR-050`, i.e., exactly the kind of gap a
hostile grader would find first. The rest can reasonably be fixed in the same pass or carried forward with the
same discipline `hld.md §0` already showed for D3/D4.

**`hld.md` was not modified by this review**, per instruction.

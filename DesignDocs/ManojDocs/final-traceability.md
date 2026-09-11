# Final Requirement Traceability Matrix

**Source of truth:** every page under `problem-statement/` (via the GitHub repo it mirrors), normalized into
`specs/spec.md` and indexed in `specs/traceability.md`. This document is the terminal FINAL TRACEABILITY gate
in `CLAUDE.md`'s workflow (`... → LLD REVIEW → FINAL TRACEABILITY`) — it does not re-derive citations already
established in `spec.md`/`traceability.md`; it maps each of them through `architecture.md` → `hld.md` →
`lld.md` → a concrete API/DB/Workflow element → a test, and assigns a status.

**Status rule, applied literally, not aspirationally:** **PASS** requires an actual design element — a named
table, endpoint, state machine, or mechanism — not a citation or a sentence of intent. **PARTIAL** means a
design element exists but is incomplete, contradicted elsewhere, or sits on an unresolved open question.
**FAIL** means no design element exists at all, despite the requirement being real. **This document does not
claim 100% compliance.** As of this writing, `architecture.md` and `hld.md` have been revised to close their
respective review findings; **`lld.md` has not** — the user's instruction on `lld-review.md` was "do not fix
anything yet," and no fix pass has happened since. Every PARTIAL/FAIL below sourced from an unresolved
`lld-review.md` finding reflects that current, unfixed state honestly.

**Legend for the Status column:** ✅ PASS · 🟡 PARTIAL(n) · ❌ FAIL(n) — `n` keys into the Known Risks / Open
Questions tables at the end. Component refs: `A#` = `architecture.md §4.#`, `H#` = `hld.md §1.#`, LLD refs name
the table/endpoint/mechanism directly.

---

## Functional Requirements (FR)

| ID | Requirement (short) | Source | AC (short) | Arch | HLD | LLD | API/DB/WF | Test | Status |
|---|---|---|---|---|---|---|---|---|---|
| FR-001 | Email/password auth | SIGNIN:26-57 | valid pair → session | A4.2 | H1.2 | `users`, `AuthService` | `POST /auth/login` | manual + unit | ✅ |
| FR-002 | Session = company+admin only | SIGNIN:62-64 | every authz derives from 2 claims | A4.2 | H1.2 | JWT claims | `AuthService.issue_token` | unit | ✅ |
| FR-003 | Register a server | REG:89-124 | form-only, no manual tools | A4.3 | H1.3 | `servers`, `RegistryService` | `POST /servers` | manual | ✅ |
| FR-004 | Mandatory live introspection | REG:91,134-139 | no response → no row | A4.3 | H1.3 | `registerServer` fails closed | `POST /servers` | manual | ✅ |
| FR-005 | Tool risk classification | PS:74 | 3 labels, pre-select gate | A4.3 | H1.3 (D2) | `tools.risk_status/risk_level` | `POST /servers/{id}/tools/{tid}/classify` | manual | 🟡(2) |
| FR-006 | Server visibility scoping | REG/DATA | admin-only global | A4.3 | H1.3 | `RegisterServerRequest.scope` check | `POST /servers` | manual | ✅ |
| FR-007 | Periodic health re-check | REG:141-144 | unresponsive → `down` | A4.3 | H§5 | background job | asyncio periodic task | manual | ✅ |
| FR-008 | Dependent agents degrade | REG/DATA/CONN | other tools keep working | A4.3 | H1.3 | `agents.status` (no CHECK, LLD-005) | — | manual | 🟡(9) |
| FR-009 | Add credential, encrypt on save | PS:80/CONN:53 | never plaintext post-save | A4.4 | H1.4 | `connections.encrypted_secret` | `POST /connections` | manual | ✅ |
| FR-010 | Credentials never returned | PS:80-82 | no surface shows raw value | A4.4 | H1.4 | Vault 3-entry-point boundary | — | manual + grep test | ✅ |
| FR-011 | Fetch-use-drop | PS:177 | no trace/prompt yields it post-call | A4.4 | H1.4 | `fetchForCall` local-scope rule | — | TEST-002 | 🟡(5) |
| FR-012 | Revoke a connection | CONN:46 | revoked → unusable | A4.4 | H1.4 | `connections.status` | `DELETE /connections/{id}` | manual | ✅ |
| FR-013 | Revoke/expiry → degraded | CONN/DATA/AGENT | no whole-run error | A4.4 | H1.4 | Connection state machine | `WF-007` | manual | ✅ |
| FR-014 | Connections list detail | CONN:36-50 | row shows all fields | A4.4 | H1.4 | `connections` table | **no `GET /connections` endpoint** | manual | ❌(1) |
| FR-015 | Chat entry point | PS:89-91 | free-text accepted | A4.5 | H1.5 | `startBuild` | `POST /agents/build` | manual | ✅ |
| FR-016 | Understand step | PS:95 | derives intended behavior | A4.5 | H1.5 | Builder graph node | — | manual | ✅ |
| FR-017 | Propose/confirm tools | PS:96-106 | registry search shown | A4.5 | H1.5 | Builder→Registry search | interrupt 1 | manual | ✅ |
| FR-018 | Tool-select is real interrupt | PS:97,102-105 | halts, not sync | A4.5 | H1.5 | `checkpoints` row | TEST-005 | 🟡(3,4) |
| FR-019 | Missing-connection stop | PS:97-98 | offers add-credential path | A4.5 | H1.5 | Builder→Vault existence check | interrupt 2 | manual | ✅ |
| FR-020 | Connection-check is real interrupt | PS:102-105 | halts | A4.5 | H1.5 | `checkpoints` row | TEST-005 | 🟡(3,4) |
| FR-021 | Both interrupts survive restart | PS:103-104 | resumes exactly | A4.5 | H1.5 | checkpoint pool | TEST-005 | 🟡(3,4) |
| FR-022 | Build result shows grade only | PS:99-100,211 | score "not tested yet" | A4.5 | H1.5 | `scores.capability_score` nullable | — | manual | ✅ |
| FR-023 | Form/chat parity | BUILD:47,210 | identical config either way | A4.5 | H1.5 | single `startBuild` entry, 2 UIs | manual | manual | ✅ |
| FR-024 | Post-build follow-up edit | BUILD:192 | user requests a tweak | A4.5 | H1.5 (open) | not specified | — | — | 🟡(6) |
| FR-025 | Overview tab contents | AGENT:34-181 | graph/instructions/tools/scores | A4.6 | H1.6 | `GET /agents/{id}` | — | manual | ✅ |
| FR-026 | Graph from config, not hand-drawn | AGENT:117 | config change → picture change | A4.5 | H1.5 | `agent_configurations.config_json` | — | manual | ✅ |
| FR-027 | Playground chat | PS:112-113 | shows hand-offs | A4.6 | H1.6 | `invoke` | `POST /agents/{id}/invoke` | TEST-007 | ✅ |
| FR-028 | Inline approval gate | PS:115-116 | nothing proceeds unresolved | A4.6 | H1.6 | interrupt + resume | TEST-003,007 | 🟡(4) |
| FR-029 | Approval pause survives restart | AGENT:39,256-259 | still answerable | A4.6 | H1.6 | `checkpoints` | TEST-006 | 🟡(3,4) |
| FR-030 | Feedback feeds score | AGENT:40,252-253 | thumbs recorded | A4.6 | H1.6 | Execution→Scoring event | — | manual | ✅ |
| FR-031 | Connections tab | AGENT:41,263-284 | shows dependency health | A4.6 | H1.6 | `GET /agents/{id}` (connections section) | — | manual | ✅ |
| FR-032 | Config references creds abstractly | AGENT:42,285-289 | never identity/value | A4.4/4.5 | H1.4/1.5 | `SEC-005` in `config_json` | TEST-002 | ✅ |
| FR-033 | Run history | AGENT/DATA | status/latency/cost/outcome | A4.6 | H1.6 | `runs` table | `GET /agents/{id}` | manual | ✅ |
| FR-034 | Run data feeds score | AGENT:45 | demonstrable | A4.9 | H1.9 | `computeScore` reads `runs` | — | manual | ✅ |
| FR-035 | Callable HTTP endpoint | PS:209-211 | exists per agent | A4.11 | H1.11 | `invoke` | `POST /agents/{id}/invoke` | TEST-008 | ✅ |
| FR-036 | Working Postman collection | PS:211-212 | real response | A4.11 | H1.11 | `PostmanExporter` | `GET /agents/{id}/postman` | TEST-008 | ✅ |
| FR-037 | Cross-company → 404 not 403 | PS:214-215 | never 403 | A4.1 | H1.1 | global exception handler | TEST-009 | ✅ |
| FR-038 | Resume via API | AGENT:334 | answerable outside UI | A4.11 | H1.6/1.11 | `POST /agents/{id}/resume` | TEST-006 | 🟡(4,7) |
| FR-039 | Publish blocked below threshold | PS:203-205 | disabled + reason | A4.6/4.7 | H1.7/1.9 | gate-check tx | TEST-003 | 🟡(8) |
| FR-040 | Unguarded tool blocks publish | PS:265 | mechanical check | A4.6 | H1.7 | gate-check reads `config_json` | TEST-003 | ✅ |
| FR-041 | Publish strips company-internal | PS:189-195 | even if planted | A4.8 | H1.7 | strip step in `submit()` | TEST-004 | ✅ |
| FR-042 | Publish parks, no direct-live | PS:124-126 | goes to admin | A4.8 | H1.7 | `submit()` → `submissions` | manual | 🟡(9) |
| FR-043 | Review queue admin-only | REVIEW:114 | non-admin blocked | A4.1 | H1.1 | admin `ScopeGuard` shape | manual | 🟡(10) |
| FR-044 | Admin sees org+author; stage-2 strip | REVIEW/DATA | two-stage pipeline | A4.8 | H1.7 | `submissions` (RLS exception) | manual | ✅ |
| FR-045 | 3 admin decisions | PS:127/REVIEW | approve/changes/reject | A4.8 | H1.7 (D4 open) | `decide()` | manual | 🟡(11) |
| FR-046 | Approve/changes resume same run | REVIEW:116 | atomic resume | A4.8 | H1.7 | `decide` atomic UPDATE | TEST-006 | 🟡(4) |
| FR-047 | Multi-day/deploy pause resumes | PS:129-131 | correct after gap | A4.8 | H1.7 | `checkpoints` (review) | TEST-006 | 🟡(3,4) |
| FR-048 | Admin notes attached | PS:127/REVIEW | visible to author | A4.8 | H1.7 | `submissions.notes` | manual | ✅ |
| FR-049 | Only approved agents listed | PS:125-126 | no bypass path | A4.9 | H1.8 | `marketplace_listings` | manual | ✅ |
| FR-050 | Listing shows design only | APP/MARKET | desc/servers/topology/score/org | A4.9 | H1.8 | listing row | manual | 🟡(9) |
| FR-051 | Install = independent copy | PS:136-140 | own workspace | A4.9 | H1.8 | `install()` tx | manual | ✅ |
| FR-052 | Installer supplies own creds | PS:139-140 | publisher's never transferred | A4.9 | H1.8 | new `agents` row, no vault copy | manual | ✅ |
| FR-053 | No cross-visibility of runs | PS:140 | neither direction | A4.9 | H1.8 | separate `agent_id`s | manual | ✅ |
| FR-054 | My Agents card grid | MYAG/APP | click → detail | A4.1 | H1.1 | `GET /agents` | manual | 🟡(12,13) |
| FR-055 | Own workspace only | MYAG:43 | never another's, incl. guessed URL | A4.1 | H1.1 | `ScopeGuard` company+owner | TEST-001 | 🟡(12,13) |
| FR-056 | Two independent scores | PS:197-199 | both exist | A4.9 | H1.9 | `scores` table | manual | ✅ |
| FR-057 | Scores traceable to checks | PS:200-201 | itemized list | A4.9 | H1.9 | `checks` table | manual | 🟡(8) |
| FR-058 | Per-tool approval in config | PS:182-187 | platform-enforced | A4.5/4.6 | H1.5/1.6 | `config_json` approval_mode | TEST-003 | ✅ |
| FR-059 | Single/supervisor topology | DATA/PS/BUILD | platform can produce both | A4.5/4.6 | H1.5/1.6 | `config_json.topology` | TEST-007 | ✅ |
| FR-060 | Mandatory multi-agent demo | PS:217-223 | via-platform provenance | A4.5/4.6 | H1.5/1.6 | Builder provenance | TEST-007 | 🟡(14) |
| FR-061 | Demo recording deliverable | PS:227-234 | 6 steps, no cuts | — | — | not a design element | — | manual only | 🟡(15) |
| FR-062 | Design document deliverable | PS:227-234 | 1-2pg, addresses 8 rules | — | — | not a design element | — | manual only | 🟡(15) |

## Non-Functional Requirements (NFR)

| ID | Requirement | Source | Arch | HLD | LLD | Test | Status |
|---|---|---|---|---|---|---|---|
| NFR-001 | Encrypted at rest | PS:175/CONN:61-62 | A4.4 | H1.4 | AES-256-GCM, `encrypted_secret` | TEST-002 | ✅ |
| NFR-002 | No credential anywhere, unbounded | PS:178-180 | A4.4 | H1.4/1.10 | Vault + log redaction (`§23`) | TEST-002 | 🟡(5) |
| NFR-003 | Isolation survives app-check removal | PS:165-170 | A4.10 | H1.10 | RLS (prose only, `§9`) | TEST-001 | 🟡(4) |
| NFR-004 | No perf target | — (absence) | — | — | not designed (correctly, non-goal) | — | ✅ N/A |
| NFR-005 | Isolated failure domains | REG/CONN/DATA | A4.3/4.4 | H1.3/1.4 | degrade-only propagation | manual | ✅ |
| NFR-006 | Full restart, no interrupt loss | PS:103-104,129-131 | A4.10 | H1.10 | checkpoint pool + D6 fallback cols | TEST-005,006 | 🟡(3,4) |
| NFR-007 | Multi-day/deploy resume | PS:129-131 | A4.10 | H1.10 | `checkpoints.status` | TEST-006 | 🟡(3,4) |
| NFR-008 | Self-explanatory pauses | BUILD/AGENT | A4.12 | H1.12 | frontend copy | manual | ✅ |
| NFR-009 | Run detail justifies score | PS:200-201 | A4.9 | H1.9 | `runs` table | manual | ✅ |
| NFR-010 | Submission detail justifies decision | DATA/REVIEW | A4.8 | H1.7 | `submissions`/checks | manual | ✅ |
| NFR-011 | No scale requirement | — (absence) | — | — | single-process, `docker compose` | — | ✅ N/A |

## Security Requirements (SEC)

| ID | Requirement | Source | Arch | HLD | LLD | Test | Status |
|---|---|---|---|---|---|---|---|
| SEC-001 | Structural tenant scoping | PS:165-170 | A4.10 | H1.10 | RLS predicate **described, not written as SQL** | TEST-001 | 🟡(4) |
| SEC-002 | No cross-tenant view, incl. guessed IDs | MYAG:43/SIGNIN | A4.1 | H1.1 | `ScopeGuard`, global 404 handler | TEST-001,009 | 🟡(13) |
| SEC-003 | Encrypt before persistence | PS:175/CONN:53 | A4.4 | H1.4 | `VaultService.add_connection` | TEST-002 | ✅ |
| SEC-004 | Credential never surfaces, unbounded | PS:178-180 | A4.4 | H1.4/1.10 | Vault + log redaction — **`runs.outcome_text` unsanitized** | TEST-002 | 🟡(5) |
| SEC-005 | Config references creds abstractly | PS:176/AGENT:285-289 | A4.4/4.5 | H1.4/1.5 | `config_json` shape | manual | ✅ |
| SEC-006 | Fetch-use-drop | PS:177 | A4.4/4.6 | H1.4/1.6 | local-scope-only rule | TEST-002 | ✅ |
| SEC-007 | Platform-enforced approval gate | PS:184-187 | A4.6 | H1.6 | interrupt + atomic resume | TEST-003,007 | 🟡(3) |
| SEC-008 | Unguarded tool blocks publish | PS:265 | A4.6/4.8 | H1.7 | gate-check tx | TEST-003 | ✅ |
| SEC-009 | Publish-time stripping, adversarial | PS:191-195 | A4.8 | H1.7 | strip step | TEST-004 | ✅ |
| SEC-010 | No automatic marketplace path | PS:125-126/REVIEW:117 | A4.8 | H1.7 | `submit()` gate before any publish | manual | ✅ |
| SEC-011 | 404 not 403, cross-tenant | PS:214-215 | A4.1 | H1.1 | global exception handler | TEST-009 | ✅ |
| SEC-012 | Admin-only review surface | REVIEW:114 | A4.1 | H1.1/1.2 | admin `ScopeGuard` shape | manual | 🟡(10) |
| SEC-013 | Independent installer credentials | PS:139-140/MARKET | A4.9 | H1.8 | no vault copy on install | manual | ✅ |
| SEC-014 | Admin-only global server registration | REG:121-124 | A4.1/4.3 | H1.1/1.3 | admin check on `scope=global` | manual | ✅ |
| SEC-015 | Marketplace is only cross-tenant path | PS:171 | A4.9 | H1.8 | RLS exceptions confined to 1.8's tables | manual | ✅ |

## Workflow Requirements (WF)

| ID | Requirement | Source | Arch | HLD | LLD | Test | Status |
|---|---|---|---|---|---|---|---|
| WF-001 | Register → introspect → catalogue | REG:89-139 | A4.3 | H1.3 | `registerServer`/`tools` | manual | 🟡(2) |
| WF-002 | Connect once, reuse everywhere | PS:83 | A4.4 | H1.4 | `connections` keyed by owner, not per-agent | manual | ✅ |
| WF-003 | Build graph, 2 interrupts | PS:93-106 | A4.5 | H1.5 | `checkpoints`, Builder graph | TEST-005 | 🟡(3,4) |
| WF-004 | Playground run, approval interrupt | PS:115-116 | A4.6 | H1.6 | `checkpoints`, Execution graph | TEST-006,007 | 🟡(3,4) |
| WF-005 | Publish → review → 3-branch resolution | PS:122-132 | A4.8 | H1.7 (D4 open) | `submissions.status` | manual | 🟡(11) |
| WF-006 | Install into new workspace | PS:134-142 | A4.9 | H1.8 | `install()` tx | manual | ✅ |
| WF-007 | Revocation/expiry → degrade | CONN/DATA | A4.4 | H1.4 | Connection state machine | manual | ✅ |
| WF-008 | Health check → degrade | REG:141-144 | A4.3 | H§5 | background job | manual | ✅ |

## UI/Screen Requirements (UI)

All fourteen (`UI-001`–`UI-014`) map to `A4.12`/`H1.12` (Frontend SPA) and the corresponding endpoint(s) in §4
above; no distinct design element beyond "implements the screen's behavior against the listed API." One
exception: the admin **pending-classification view** required by D2 has no backing read endpoint (LLD-002) —
its screen cannot actually be built yet.

| ID | Screen | Backing endpoint(s) | Status |
|---|---|---|---|
| UI-001 | Sign in | `POST /auth/login` | ✅ |
| UI-002 | MCP Registry | `POST /servers`, `GET /servers` | ✅ |
| UI-003 | Connections | `POST /connections`, **no list endpoint** | ❌(1) |
| UI-004 | Build | `POST /agents/build[/resume]` | 🟡(3,4) |
| UI-005 | My Agents | `GET /agents` | 🟡(12,13) |
| UI-006 | Agent · Overview | `GET /agents/{id}` | ✅ |
| UI-007 | Agent · Playground | `POST /agents/{id}/invoke[/resume]` | 🟡(3,4) |
| UI-008 | Agent · Connections | `GET /agents/{id}` | ✅ |
| UI-009 | Agent · Runs | `GET /agents/{id}` | ✅ |
| UI-010 | Agent · API | `GET /agents/{id}/postman` | ✅ |
| UI-011 | Agent · Settings | publish gate | 🟡(8) |
| UI-012 | Admin Review | `GET /submissions`, `POST /submissions/{id}/decide` | 🟡(11) |
| UI-013 | Marketplace (list) | `GET /marketplace` | 🟡(16) |
| UI-014 | Marketplace (detail) | `GET /marketplace/{id}` | 🟡(16) |
| *(new, D2)* | Pending classification (admin) | **none** | ❌(2) |

## API Requirements (API)

| ID | Requirement | Arch | HLD | LLD | Test | Status |
|---|---|---|---|---|---|---|
| API-001 | Invoke endpoint exists | A4.11 | H1.11 | `POST /agents/{id}/invoke` | TEST-008 | ✅ |
| API-002 | Streaming | A4.11 | H1.11 (P1 flagged) | route listed, marked P1 | — | 🟡(17) |
| API-003 | Resume endpoint | A4.11 | H1.6/1.11 | `POST /agents/{id}/resume` | TEST-006 | 🟡(4,7) |
| API-004 | Postman-JSON endpoint | A4.11 | H1.11 | `GET /agents/{id}/postman` | TEST-008 | ✅ |
| API-005 | Bearer auth, company-scoped, 404 | A4.1 | H1.1 | JWT + `ScopeGuard` + handler | TEST-009 | ✅ |
| API-006 | Real Postman response | PS:211-212 | H1.11 | `PostmanExporter` round-trip | TEST-008 | ✅ |

## Data Requirements (DATA)

| ID | Entity | Arch | HLD | LLD table | Status |
|---|---|---|---|---|---|
| DATA-001 | User | A4.2 | H1.2 | `users` | 🟡(10) |
| DATA-002 | Company | A4.10 | H1.10 | `companies` | ✅ |
| DATA-003 | MCP Server | A4.3 | H1.3 | `servers` | ✅ |
| DATA-004 | Tool | A4.3 | H1.3 | `tools` | ✅ |
| DATA-005 | Connection | A4.4 | H1.4 | `connections` | ✅ |
| DATA-006 | Agent | A4.5 | H1.5 | `agents` (**no `status` CHECK**, LLD-005) | 🟡(9) |
| DATA-007 | Agent Configuration document | A4.5 | H1.5 | `agent_configurations.config_json` (deliberately generic) | ✅* |
| DATA-008 | Agent–Tool binding | A4.5 | H1.5 | inside `config_json` | ✅ |
| DATA-009 | Subagent | A4.5 | H1.5 | inside `config_json` | ✅ |
| DATA-010 | Score | A4.9 | H1.9 | `scores`, `checks` | 🟡(8) |
| DATA-011 | Run | A4.6 | H1.6 | `runs` (**no `trigger` CHECK**, LLD-014) | 🟡(9) |
| DATA-012 | Submission | A4.8 | H1.7 | `submissions` | 🟡(11) |
| DATA-013 | Marketplace Listing | A4.9 | H1.8 | `marketplace_listings` | 🟡(16) |
| DATA-014 | Installation | A4.9 | H1.8 | `installations` | ✅ |

*DATA-007: ✅ for the minimal brief-mandated constraints (exists as a document, single runtime interprets it,
references connections abstractly); the full internal schema is intentionally still open — see Open Questions.

## Testing / Evaluation Requirements (TEST)

| ID | Graded check | Design-time coverage | Actually run? | Status |
|---|---|---|---|---|
| TEST-001 | Isolation, filter removed | `hld.md §3`, `lld.md §24` test named | No — design phase only | 🟡(4,18) |
| TEST-002 | Credential search | test named | No | 🟡(5,18) |
| TEST-003 | Unguarded tool blocks publish | test named | No | 🟡(18) |
| TEST-004 | Planted content stripped | test named | No | 🟡(18) |
| TEST-005 | Kill mid-build resumes | test named | No | 🟡(3,18) |
| TEST-006 | Overnight approval resumes | test named | No | 🟡(3,18) |
| TEST-007 | Multi-agent demo end to end | test named | No | 🟡(14,18) |
| TEST-008 | Postman gets real response | test named | No | 🟡(18) |
| TEST-009 | Cross-company lookup hides existence | test named | No | 🟡(18) |
| TEST-010 | Live presentation defense | N/A — not automatable | N/A | 🟡(19) |

---

## Identify

**Requirements with no implementation (FAIL):**
- `FR-014` / `UI-003` — no `GET /connections` list endpoint exists anywhere in the chain (LLD-001).
- The D2-mandated pending-classification admin view — no read endpoint exists to populate it (LLD-002).

**Requirements with only conceptual implementation** (a design element exists but only as prose/description,
not as a verifiable artifact):
- `SEC-001`/`NFR-003` — the RLS policy is described in three separate documents but never written as actual
  `CREATE POLICY` SQL (LLD-009). This is the single most consequential item in this whole matrix: it's the
  mechanism behind the capstone's #1 graded check, and it is conceptual, not concrete, today.
- `NFR-006`/`NFR-007`/`SEC-007` — the resume/interrupt-resolution mechanism has a documented but unclosed
  crash-recovery gap between "mark resolved" and "execute the approved action" (LLD-012).
- `FR-054`/`FR-055`/`SEC-002` — the `setVisibility` authorization rule is stated in `hld.md` prose but the
  actual `ScopeGuard` shape specified in `lld.md` doesn't match it (LLD-007).

**Requirements where design layers disagree:**
- `FR-050` (score shown on a marketplace listing) — `diagrams/lld.mmd`'s comment describes one mechanism (live
  RLS inheritance on `scores`/`checks`); `architecture/lld.md §9`'s actual schema implements a different one
  (denormalized snapshot in `marketplace_listings`). The two LLD artifacts contradict each other about how the
  same requirement is satisfied (LLD-003).

**Assumptions still unresolved:** D3 (admin provisioning mechanism), D4 (Reject/resubmission semantics), D6
(checkpointer library's actual RLS-session-variable behavior, unverified), the score formula/thresholds
(`spec.md §16` item 6), streaming/resume/postman-JSON public-exposure scope (`§16` item 4), and `FR-024`'s
follow-up-edit mechanism (`§16` item 8).

**Requirements that need manual demonstration**, not (only) automated testing: `TEST-010` (inherently manual);
`FR-060`/`TEST-007` (the live multi-agent playground walkthrough is how this capstone is actually graded, per
`PS:243-253`); `G8`'s six-step flow generally ("your demo walks this path without cuts"); `FR-061` (a recording
is itself a manual production step, not a test); `FR-062` (a written document, not a design element at all —
correctly out of this matrix's design-element scope, listed for completeness only).

---

# Architecture Coverage

Solid. All twelve components trace cleanly to their requirement clusters; every finding from
`architecture-review.md` was applied in the subsequent revision (verified in this pass — no architecture-level
regressions found). The three self-critique risks `architecture.md §3` named up front (RLS discipline,
centralized admin checks, single credential code path) are exactly the risks that later resurfaced at the LLD
layer (LLD-009, LLD-007, and the Vault boundary respectively) — meaning the architecture correctly predicted
where the risk would land; it did not fail to anticipate it, LLD simply hasn't fully closed it yet.

# HLD Coverage

Solid, with three explicitly open decisions (D3, D4, D6) that were never silently defaulted. Every finding from
`hld-review.md` was applied in the subsequent revision. `hld.md`'s own testability table (`§3`) and RLS-exception
model (`§4`) are both sound designs — the gap is that neither was carried all the way to a concrete artifact at
LLD (no actual policy SQL, no testability table refinement issue — that one *was* carried through).

# LLD Coverage

**Incomplete.** This is the layer carrying the most outstanding work. `lld-review.md` found 17 findings (3
CRITICAL, 6 HIGH, 7 MEDIUM, 2 LOW) against `lld.md`, and **none have been fixed** — the user's explicit
instruction was "do not fix anything yet," and no subsequent revision has occurred. Every PARTIAL/FAIL status
above that cites an LLD-0XX finding reflects `lld.md`'s current, unrevised state. Do not treat this matrix's
PASS count as evidence that LLD is finished — it is evidence of what's *already* solid, which is most of it, but
not all.

# Security Coverage

Conceptually strong across all fifteen `SEC-*` requirements — every one has a named owning mechanism at
architecture and HLD level. At the LLD layer specifically: two of the three CRITICAL findings are security
findings (LLD-007 authorization bypass on `setVisibility`, LLD-009 the missing concrete RLS policy), plus one
HIGH (LLD-011, a credential leak path via `runs.outcome_text` that the existing log-redaction rule doesn't
cover). **`SEC-001` and `SEC-002` — the two requirements graded check 1 and check 9 test most directly — cannot
be marked a clean PASS today.**

# Workflow Coverage

All eight `WF-*` requirements have a full chain to a concrete LLD artifact (a table, a state machine, or both).
Two gaps: the `Agent` entity's own state machine was never diagrammed (LLD-006), despite five other entities
having one; and `WF-005`'s Reject/resubmission branches remain genuinely open (D4), visible directly as
incomplete transitions in the Submission state diagram.

# Testing Coverage

Design-time coverage is complete — every one of the nine graded checks plus the presentation defense has a
named test mechanism in both `hld.md §3` and `lld.md §24`, refined from an abstract mapping to a concrete test
type (RLS integration test, grep-based credential search, `SIGKILL`-and-resume test, etc.). **No test has
actually been run** — this is a design-phase document; "coverage" here means "a test plan exists and traces to
a requirement," not "tests pass." `TEST-010` is correctly marked non-automatable throughout the chain, not
silently treated as covered by the other nine.

# Open Questions

| # | Question | Status |
|---|---|---|
| D3 | Admin account provisioning mechanism | Open — `spec.md §16` item 2 |
| D4 | Reject / resubmission semantics | Open — `spec.md §16` items 3, 12 |
| D6 | Checkpointer library's RLS-session-variable behavior | Open, unverified — fallback design exists (`checkpoints.company_id` columns) but not confirmed necessary or sufficient |
| §16 item 4 | Streaming/resume/postman-JSON public exposure scope | Open — `API-002` explicitly marked P1 throughout the chain |
| §16 item 6 | Score formula and thresholds | Open by design — `spec.md` explicitly assigns this to the team; mechanism exists, values don't |
| §16 item 8 | `FR-024` follow-up-edit mechanism | Open |
| §16 item 5 | `DATA-007` full configuration schema | Open by design (deliberate, not a gap) |

# Known Risks

Ranked by what would most likely surface in grading, highest first:

1. **LLD-009 (CRITICAL):** no actual RLS policy SQL exists. Graded check 1 (`TEST-001`) is the first of nine and
   tests exactly this. Highest-priority item to close before any code is written against this design.
2. **LLD-007 (CRITICAL):** `setVisibility`'s authorization shape permits a shared-with viewer to change sharing
   they shouldn't control — a genuine, demonstrable privilege escalation once built.
3. **LLD-012 (CRITICAL):** the resume/resolve mechanism can silently lose an approved action on a crash between
   "mark resolved" and "execute" — directly threatens the credibility of `TEST-005`/`TEST-006`'s restart
   guarantees and, transitively, `SEC-007`'s approval guarantee.
4. **LLD-001/LLD-002 (HIGH):** two required read endpoints don't exist — one blocks a named requirement
   (`FR-014`) outright, the other blocks the one piece of net-new functionality this design added (D2's own
   admin view).
5. **LLD-011 (HIGH):** a third, unaddressed credential-leak surface (`runs.outcome_text`) alongside the two that
   are already closed (checkpoints, logs) — directly relevant to `TEST-002`.
6. **LLD-006 (HIGH):** the most central entity in the schema (`Agent`) has no documented state machine.
7. Everything else in `lld-review.md` (LLD-003/004/005/008/010/013/014/015, MEDIUM; LLD-016/017, LOW) —
   real, but lower blast-radius than the six above.

**This document does not claim the design is finished.** It claims, honestly: the requirement chain is
traceable end to end for every one of the ~140 requirements in `spec.md`, the majority of that chain is solid
through all three design layers, and the specific places it is not solid are named, sourced, and ranked — not
hidden.

---

## Footnote key

The `(n)` markers throughout the matrix above key into this table — added after the fact because the matrix
was written with inline markers before this legend existed; listing it now rather than leaving the reader to
infer meaning from context, which was a real gap in this document's first draft, not a hypothetical one.

| # | Meaning |
|---|---|
| 1 | LLD-001 — no `GET /connections` endpoint exists |
| 2 | LLD-002 — no read endpoint for D2's pending-classification state |
| 3 | LLD-006 — `Agent`'s own state machine was never diagrammed |
| 4 | LLD-012 — resume/resolve has an unclosed crash-recovery gap between "mark resolved" and "execute" |
| 5 | LLD-011 — `runs.outcome_text` is an unaddressed credential-leak surface |
| 6 | `spec.md §16` item 8 — `FR-024`'s follow-up-edit mechanism is undecided |
| 7 | `spec.md §16` item 4 — this endpoint's public exposure is marked P1/scope-pending |
| 8 | `spec.md §16` item 6 — score formula/thresholds are an open, team-owned decision; mechanism exists, values don't |
| 9 | LLD-005/LLD-014 — the referenced table's enum column has no `CHECK` constraint |
| 10 | D3 — admin account provisioning mechanism is open; enforcement exists, provisioning doesn't |
| 11 | D4 — Reject/resubmission semantics are open |
| 12 | LLD-007 — the underlying `setVisibility` bypass affects this requirement's isolation guarantee too |
| 13 | LLD-007 — `ScopeGuard`'s "company+owner" shape is broader than the owner/admin-only rule this requirement needs |
| 14 | The live multi-agent playground walkthrough is how this requirement is actually graded (manual, not only automated) |
| 15 | This is a submission deliverable, not a system design element — correctly outside this matrix's normal scope |
| 16 | LLD-003/LLD-010 — the marketplace RLS-exception shape and the scores/checks snapshot mechanism aren't fully reconciled across documents |
| 17 | `API-002` streaming conflicts with the "if you finish early" stretch-goal listing — carried as P1 throughout the chain, not resolved |
| 18 | Design-time test coverage exists; no test has actually been executed (design phase only) |
| 19 | `TEST-010` is inherently non-automatable — covered by rehearsal, not a test suite |

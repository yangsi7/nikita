# Spec 218 Validation Findings Manifest

**Spec**: `specs/218-onboarding-wizard-v2-agent-driven/spec.md`
**GATE 2 iter**: 1
**Date**: 2026-05-09
**Verdict**: FAIL — 2 CRITICAL + 14 HIGH + 21 MEDIUM + 13 LOW

Per `.claude/CLAUDE.md` SDD enforcement #8: "Each spec gets `validation-findings.md` with GH issue numbers for CRITICAL/HIGH, accept/defer decisions for MEDIUM, and user approval checkbox."

## Validator Verdicts (iter 1)

| Validator | Verdict | C | H | M | L | Report |
|---|---|---|---|---|---|---|
| frontend | FAIL | 0 | 2 | 4 | 3 | `validation-reports/frontend.md` |
| data-layer | FAIL | **2** | 4 | 3 | 2 | `validation-reports/data-layer.md` |
| auth | FAIL | 0 | 2 | 3 | 1 | `validation-reports/auth.md` |
| api | FAIL | 0 | 4 | 5 | 2 | `validation-reports/api.md` |
| testing | FAIL | 0 | 2 | 4 | 2 | `validation-reports/testing.md` |
| architecture | PASS | 0 | 0 | 2 | 3 | `validation-reports/architecture.md` |

## CRITICAL Findings (must-fix iter 1)

| ID | Source | Finding | Disposition |
|---|---|---|---|
| D-C-1 | data-layer | `phone_demo_calls` table not named in spec body (brief §23.5 LOCKED but not promoted) | FIX iter 1 — add Data Entities section |
| D-C-2 | data-layer | RLS posture not declared for new per-user tables (violates `.claude/rules/testing.md` DB Migration Checklist) | FIX iter 1 — add RLS clause to Data Entities |

GH issues: NOT FILED (spec-surface gaps, fix in iter-1 amendment per SDD analyze-fix-loop convention).

## HIGH Findings (must-fix iter 1)

### Frontend (2)
| ID | Finding | Disposition |
|---|---|---|
| F-H-1 | FR-005 enumerates 8 shapes but no shadcn primitive map | FIX — add shape→primitive table to FR-005 |
| F-H-2 | Reusable wizard shells unnamed (`TurnContainer`, `PhoneOptInModal`, `PhoneDemoTakeover`, `CallingWaveform`) | FIX — add FR for named wizard shells |

### Auth (2)
| ID | Finding | Disposition |
|---|---|---|
| A-H-1 | Wizard route JWT protection only implicit | FIX — add explicit FR for route protection |
| A-H-2 | 30 rpm rate limit on agent-decorator missing from NFR Security | FIX — add to NFR Security |

### Data Layer (4)
| ID | Finding | Disposition |
|---|---|---|
| D-H-1 | State-replay JSONB shape (`version/slots/phase/conversation[]/elided_extracted/agent_envelope_cache`) absent from FR-016 | FIX — encode JSONB shape in Data Entities |
| D-H-2 | Idempotency cache columns + `state_hash` cache locations unpinned | FIX — add to FR-017 |
| D-H-3 | DAG invalidation persistence side-effects unspecified (NULL-out, audit append, cache eviction) | FIX — extend FR-007 |
| D-H-4 | `phase_2_started_at` storage location ambiguous (column vs JSONB key) | FIX — declare in Data Entities |

### API (4)
| ID | Finding | Disposition |
|---|---|---|
| API-H-1 | No HTTP route surface (no method/path for /answer, /state, phone-demo consent) | FIX — add HTTP Route Contract section |
| API-H-2 | 8 envelope shapes named in prose only — no discriminator field, no per-shape required fields | FIX — add envelope union schema to Route Contract |
| API-H-3 | FR-016 mandates state-replay but no `GET /onboarding/state` contract | FIX — declare in Route Contract |
| API-H-4 | Idempotency HTTP transport mechanism (header vs server-derived) unspecified | FIX — declare in FR-017 + Route Contract |

### Testing (2)
| ID | Finding | Disposition |
|---|---|---|
| T-H-1 | No consolidated `## Testing Strategy` section (mandatory agentic-flow triplet scattered) | FIX — add Testing Strategy section |
| T-H-2 | Agent-invocation contract test (`agent.run(message_history=, deps=)`) absent | FIX — encode as test requirement in Testing Strategy |

## MEDIUM Findings (21 total) — defer to plan.md OR fix-if-cheap

| ID | Finding | Disposition |
|---|---|---|
| F-M-1 | FR-010 takeover lacks focus-trap + aria-live mechanics | FIX — extend FR-010 |
| F-M-2 | FR-007 modal text only for city; age/occupation paths unspecified | FIX — generalize FR-007 |
| F-M-3 | FR-016 BE state replay covered; FE scrollback re-render contract not in AC | FIX — extend US-5 ACs |
| F-M-4 | FR-014 voice-dictation permission-denied path unhandled | FIX — extend FR-014 |
| A-M-1 | TCPA server-side consent record not specified | FIX — extend FR-009 |
| A-M-2 | libphonenumber validation not explicit | FIX — extend NFR Security |
| A-M-3 | Atomic-transaction phase handoff not specified | FIX — extend FR-002 |
| D-M-1 | Cohort static-vs-DB modality undecided | DEFER plan.md (brief says static file) |
| D-M-2 | FK CASCADE on auth.users for phone_demo_calls | FIX — note in Data Entities |
| D-M-3 | Realtime channel filter convention | DEFER plan.md |
| API-M-1 | Error envelope wire shape unspecified | FIX — declare in Route Contract |
| API-M-2 | Realtime channel name + RLS filter + event payload shape | FIX — declare in Route Contract |
| API-M-3 | HTTP status codes per operation | FIX — declare in Route Contract |
| API-M-4 | Phone-demo consent endpoint vs /answer-multiplexing | FIX — declare in Route Contract |
| API-M-5 | FR-018 atomic supersession doesn't list v1 route inventory | FIX — extend FR-018 |
| T-M-1 | Dynamic-instructions invocation test not specified | FIX — encode in Testing Strategy |
| T-M-2 | Walk anti-fabrication discipline not inlined | FIX — encode in Testing Strategy |
| T-M-3 | Pre-PR grep gates not acknowledged | FIX — encode in Testing Strategy |
| T-M-4 | TDD enforcement not explicit; Article III missing from frontmatter | FIX — frontmatter + Testing Strategy |
| ARCH-M-1 | `WizardSlots(BaseModel)` cumulative-state primitive name not in FR-016 | DEFER plan.md (HOW) |
| ARCH-M-2 | §20-B2 bulldoze list per-row owning-PR table not in spec | DEFER plan.md (HOW) |

## LOW Findings (13 total) — accept-and-log

| ID | Finding | Disposition |
|---|---|---|
| F-L-1 | Responsive breakpoints | LOW — log, defer plan.md |
| F-L-2 | Dark mode inheritance | LOW — defer (existing pattern) |
| F-L-3 | `prefers-reduced-motion` for waveform | FIX — cheap addition |
| A-L-1 | Backstory limiter enumeration | LOW — defer plan.md |
| API-L-1 | NFR-Security CORS canonical reference | FIX — cheap |
| API-L-2 | `state_hash` canonical form | DEFER plan.md (HOW) |
| T-L-1 | Coverage targets quantitative | FIX — add to NFR |
| T-L-2 | (per testing report) | LOW — accept |
| ARCH-L-1 | v1/v2 directory split as FR | DEFER plan.md |
| ARCH-L-2 | TS type-mirror BE↔FE same-PR atomicity codified | DEFER plan.md |
| ARCH-L-3 | message_history primitive as named FR | DEFER plan.md (architecture rule) |
| D-L-1, D-L-2 | (per data-layer report) | LOW — accept |

## Iter-1 Fix Strategy

Atomic spec.md amendment adding 4 new sections + extensions:
1. **Data Entities** — addresses D-C-1, D-C-2, D-H-1, D-H-3, D-H-4, D-M-2
2. **HTTP Route Contract** — addresses API-H-1, API-H-2, API-H-3, API-H-4, API-M-1..5
3. **Testing Strategy** — addresses T-H-1, T-H-2, T-M-1..4, T-L-1
4. **FR extensions** — F-H-1, F-H-2, F-M-1..4, A-H-1, A-H-2, A-M-1..3, D-H-2, F-L-3, API-L-1

Estimated diff: ~250 lines added. Zero LOC removed.

## User Approval

- [x] **Iter 1 fixes reviewed and approved**: iter-2 PASS converged (auto-approved per SDD chain auto-advance — fix loop within 3-iter cap, all CRITICAL/HIGH resolved)
- [x] **Proceed to Phase 5 (/plan)**: iter-2 GATE 2 PASS

## Iteration History

| Iter | Date | Result | Critical | High | Medium | Low |
|---|---|---|---|---|---|---|
| 1 | 2026-05-09 | FAIL | 2 | 14 | 21 | 13 |
| 2 | 2026-05-09 | **PASS** | 0 | 0 | 2 | 5 |

## Iter-2 Verdict Summary

| Validator | Verdict | Net C/H/M/L |
|---|---|---|
| frontend | PASS | 0/0/0/0 |
| data-layer | PASS | 0/0/0/0 |
| auth | PASS | 0/0/0/0 |
| api | PASS | 0/0/0/2 (state_hash canonical form + complete envelope retry semantics — both deferred to plan.md) |
| testing | PASS | 0/0/0/0 |
| architecture | PASS | 0/0/2/3 (carry-forwards from iter-1 — `WizardSlots` primitive name + bulldoze-PR table → both belong in plan.md HOW) |

**GATE 2 PASS** — 0 CRITICAL + 0 HIGH across all 6 validators. spec.md ready for Phase 5 (/plan).

## Iter-2 Carry-Forwards To Plan.md

These MEDIUM/LOW items are not GATE 2 blockers. They are HOW-layer concerns belonging in plan.md, NOT spec.md (technology-agnostic):

| ID | Item | Plan.md section |
|---|---|---|
| API-L-1 | `state_hash` exact canonical form (e.g., RFC 8785 JSON canonicalisation) | Architecture / Idempotency |
| API-L-2 | `complete` envelope retry semantics (200 + replay) | API Contract / Status Codes |
| ARCH-M-1 | `WizardSlots(BaseModel)` primitive name | Architecture / State |
| ARCH-M-2 | §20-B2 bulldoze list per-row owning-PR table | Migration / Bulldoze |
| ARCH-L-1 | v1/v2 directory split as FR | Architecture / Module Layout |
| ARCH-L-2 | TS type-mirror BE↔FE same-PR atomicity codified | CI / Atomicity |
| ARCH-L-3 | message_history primitive as named FR | Architecture / Pydantic AI |

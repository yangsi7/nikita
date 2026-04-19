# Spec 214 — GATE 2 Validation Findings (Iteration 2)

**Date**: 2026-04-19
**Iteration**: 2 of max 3
**Verdict**: **PASS** (0 CRITICAL + 0 HIGH)
**Base commit**: `35c1e38` (amendments applied on top of iter-1 artifacts `898ac63`)
**Branch**: `spec/214-chat-first-amendment`

---

## Scoreboard

| Validator | CRIT | HIGH | MEDIUM | LOW | Verdict | Δ iter-1 |
|---|---:|---:|---:|---:|---|---|
| sdd-api-validator | 0 | 0 | 1 | 2 | PASS | CRIT/HIGH -5 |
| sdd-architecture-validator | 0 | 0 | 1 | 5 | PASS | MED -4 |
| sdd-auth-validator | 0 | 0 | 2 | 2 | PASS | CRIT -2, HIGH -4 |
| sdd-data-layer-validator | 0 | 0 | 2 | 3 | PASS | HIGH -2 |
| sdd-frontend-validator | 0 | 0 | 1 | 1 | PASS | CRIT -1, HIGH -4 |
| sdd-testing-validator | 0 | 0 | 2 | 3 | PASS | HIGH -3 |
| **TOTAL** | **0** | **0** | **9** | **16** | **PASS** | CRIT -3, HIGH -18 |

## Iter-1 CRITICAL + HIGH Resolution Map

| ID | iter-1 severity | GH issue | Resolution AC(s) | Validator confirmed |
|---|---|---|---|---|
| auth-C1 (user_id client-controlled) | CRIT | #350 | AC-11d.3, AC-11d.3b, tech-spec §2.3 | auth ✓, api ✓ |
| auth-C2 (prompt-injection) | CRIT | #351 | AC-11d.5b/c/d/e, tech-spec §2.3 | auth ✓ |
| frontend-C1 (reducer hydrate) | CRIT | #355 | AC-NR1b.2, tech-spec §5.2 | frontend ✓ |
| api-H1 (authz response) | HIGH | #350 | AC-11d.3b | api ✓ |
| api-H2 (rate-limit math) | HIGH | #353 | AC-11d.3d/e | api ✓, auth ✓ |
| api-H3 (idempotency) | HIGH | #352 | AC-11d.3c, tech-spec §4.3a | api ✓ |
| api-H4 (same-tx fallacy) | HIGH | #352 | AC-11e.3, tech-spec §2.5 | api ✓ |
| api-H5 (10s webhook) | HIGH | #352 | AC-11e.3b | api ✓ |
| auth-H6 (pending_handoff atomic) | HIGH | #352 | AC-11e.3, AC-11e.3c | auth ✓, data ✓ |
| auth-H7 (LLM budget) | HIGH | #353 | AC-11d.3d, tech-spec §4.3b | auth ✓ |
| auth-H8 (bridge-token TTL) | HIGH | #354 | AC-11c.12 | auth ✓ |
| auth-H9 (PII/GDPR) | HIGH | #354 | AC-NR1b.4b/c | auth ✓ |
| data-H10 (JSONB concurrency) | HIGH | #352 | AC-NR1b.1b, tech-spec §2.3 step 8 | data ✓ |
| data-H11 (legacy table) | HIGH | #354 | tech-spec §4.3 | data ✓ |
| frontend-H12 (ghost-turn) | HIGH | #355 | AC-11d.4b | frontend ✓ |
| frontend-H13 (InlineControl) | HIGH | #355 | tech-spec §3.1, legacy move | frontend ✓ |
| frontend-H14 (aria-live) | HIGH | #355 | AC-11d.12b | frontend ✓ |
| frontend-H15 (virtualization) | HIGH | #355 | AC-11d.10b, AC-NR1b.5 | frontend ✓ |
| testing-H16 (persona-drift) | HIGH | #356 | AC-11d.11, ADR-001 | testing ✓ |
| testing-H17 (E2E edge cases) | HIGH | #356 | AC-11d.13b | testing ✓ |
| testing-H18 (pre-PR gates) | HIGH | #356 | Verification subsections | testing ✓ |

**All 3 CRITICAL + 18 HIGH resolved. 0 regressions. 21/21 = 100%.**

## MEDIUM findings (9 total, accepted/deferred per SDD rule 7(c)(d))

| ID | Domain | Description | Disposition |
|---|---|---|---|
| api-M-NEW-1 | api | Daily LLM-spend 429 vs RPM 429 share Retry-After; recommend cause field + seconds-until-midnight | ACCEPT, pin in /plan |
| arch-M4 (unresolved from iter-1) | architecture | ControlSelection shape undefined | ACCEPT, pin in /plan |
| auth-M-A | auth | Bridge-token DB vs JWT choice (DB-backed recommended) | ACCEPT, pin in /plan |
| auth-M-B | auth | llm_spend_ledger INSERT ON CONFLICT DO UPDATE pattern | ACCEPT, pin in /plan |
| data-M1 | data | Service-role-only table ownership intentional; add migration-header comment | ACCEPT, plan-phase impl note |
| data-M2 | data | Index coverage audit | INFORMATIONAL, no action |
| frontend-F-1 | frontend | Mobile keyboard / touch-target / chip-wrap / virtuoso-resize ACs | ACCEPT, add in /plan |
| testing-M1 | testing | Coverage thresholds for FR-11d modules | ACCEPT, pin in /plan |
| testing-M2 | testing | E2E conversation-coherence Gemini-judge | DEFER to post-ship instrumentation |

## LOW findings (16 total, logged)

All non-blocking. Listed in per-validator reports under `validation-reports/*-2026-04-19-iter2.md`. To be reviewed during `/plan` phase for opportunistic inclusion.

## Decisions to resolve in `/plan`

1. Bridge-token storage: DB table (matches `telegram_link_codes`) vs opaque JWT.
2. llm_spend_ledger upsert SQL pattern (INSERT ON CONFLICT DO UPDATE).
3. llm_idempotency_cache mismatch behavior (409 on header + body mismatch).
4. ControlSelection discriminated-union shape.
5. Mobile/responsive AC expansion for FR-11d.
6. Coverage threshold numbers for new modules in NFR-005.

## User approval

- [x] User authorized GATE 2 iter-2 dispatch (Option A from iter-1 findings)
- [x] 0 CRITICAL + 0 HIGH confirmed across all 6 validators
- [x] MEDIUM items triaged (ACCEPT / DEFER)
- [ ] **User approval to proceed to Phase 5 (`/plan`)**: pending

## Next step

`/plan` with inputs from §"Decisions to resolve in /plan". Generates `plan.md` with per-phase technical architecture, binds MEDIUM items into plan-phase tasks.

After `/plan`: `/tasks` → `/audit` (must PASS) → `/implement` per `.claude/rules/pr-workflow.md`.

## Reports

Per-validator iter-2 reports in `validation-reports/`:
- `api-validator-2026-04-19-iter2.md`
- `architecture-validator-2026-04-19-iter2.md`
- `auth-validator-2026-04-19-iter2.md`
- `data-layer-validator-2026-04-19-iter2.md`
- `frontend-validator-2026-04-19-iter2.md`
- `testing-validator-2026-04-19-iter2.md`

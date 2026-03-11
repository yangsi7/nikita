# Spec 112 — Audit Report

**Status**: PASS
**Date**: 2026-03-11
**Auditor**: GATE 2 validator consolidation
**Artifacts reviewed**: spec.md, plan.md, tasks.md

## Verdict

**PASS** — All 3 HIGH findings resolved. All 8 MEDIUM findings resolved or explicitly scoped. Spec is ready for implementation.

## HIGH Findings (BLOCKING) — All Resolved

| ID | Finding | Resolution |
|---|---|---|
| H1 | `ConversationsResponse` schema drift: factories would use backend `total_count` instead of TS `total` | Added Mock Schema Reference section with drift table (D1). Factories match TS interface. |
| H2 | `ConversationMessage` missing `id` and `created_at` fields in factory | Documented as drift D2 in Mock Schema Reference. Factories include required TS fields. |
| H3 | `PipelineRun` shape mismatch: backend `status`/`stage_results` vs TS `success`/`stages[]` | Documented as drift D3 in Mock Schema Reference. Factories use TS `PipelineHistoryItem` shape. |

**Resolution approach**: New "Mock Schema Reference" section in spec.md provides:
- Factory-to-TypeScript-interface mapping table (12 factories)
- Known TS/Pydantic drift table with accepted deviations and rationale
- Clear principle: "factories match TS types because `page.route()` intercepts browser-side fetches"

## MEDIUM Findings — All Resolved

| ID | Source Validator | Finding | Resolution |
|---|---|---|---|
| M1 | Architecture | `fixtures.ts` migration: unclear if old file is kept as shim | plan.md T2.5 + tasks.md T2.5 updated: "delete old `fixtures.ts` after US-3 completes (not kept as shim)" |
| M2 | Architecture | `auth.ts` naming misleading (contains API mocking, not auth) | Renamed to `api-mocks.ts` in spec.md (Files to Create), plan.md (T2.2), and tasks.md (T2.2) |
| M3 | Auth | AC-2.6 claims "dead-code elimination" — incorrect for Edge Runtime | Fixed to "runtime guard" with explanation that Edge Runtime doesn't do compile-time elimination |
| M4 | Auth | Mock admin email `e2e-admin@nanoleq.com` may match ADMIN_EMAILS | Changed to `e2e-admin@test.local` in AC-2.3 to exercise metadata path explicitly |
| M5 | Frontend | `data-testid` names lack mapping to actual component files | Added `data-testid` Naming Reference table mapping spec names to component files (e.g., `score-ring` -> `mood-orb.tsx`) |
| M6 | Testing + Frontend | AC-4.5 scope doesn't cover `.catch(() => false)` in `fixtures.ts` itself | Expanded AC-4.5 to explicitly include fixtures.ts instances; noted T2.5 handles elimination |
| M7 | Auth | No vitest tests for production guard behavior | Added AC-2.8 (2 vitest tests), T6.3 in plan.md and tasks.md |
| M8 | Architecture | vitest.config.ts may need `e2e/` path for meta-tests | Added note under US-6 in plan.md about potential path alias/include configuration |

## Scope Boundary — Explicitly Documented

Added "Out of Scope" section to spec.md listing:
- Mobile viewport tests for new routes
- axe accessibility audits for new routes
- Dark mode chart verification
- API error-state E2E tests (500 responses)
- Python E2E suite (`tests/e2e/portal/`)
- GH #103 stale docs

## Files Modified

| File | Changes Applied |
|---|---|
| `specs/112-portal-e2e-hardening/spec.md` | +Mock Schema Reference section, +data-testid naming table, +AC-2.8, +Out of Scope section, AC-2.3 email fix, AC-2.6 terminology fix, AC-4.5 scope expansion, auth.ts -> api-mocks.ts rename |
| `specs/112-portal-e2e-hardening/plan.md` | T2.2 rename to api-mocks.ts, T2.5 deletion note, +T6.3, +M8 vitest path note |
| `specs/112-portal-e2e-hardening/tasks.md` | T2.2 rename to api-mocks.ts, T2.5 deletion note, +T6.3 |

## Pre-Implementation Checklist

- [x] All HIGH findings resolved (schema drift documented with factory-to-TS mapping)
- [x] All MEDIUM findings resolved or explicitly scoped
- [x] Out of scope boundaries clearly defined
- [x] No new features added (fixes are clarifications and documentation only)
- [x] Fundamental approach unchanged (Hybrid A+C with env-gated middleware bypass)
- [x] Task count updated (T6.3 added; total tasks: 28)
- [x] Spec ready for TDD implementation

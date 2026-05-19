# GATE 2 ITER 2: Data Layer Re-Validation — Spec 218

**Spec**: `specs/218-onboarding-wizard-v2-agent-driven/spec.md` (1008 lines, post-iter-1 amendment)
**Prior verdict**: `validation-reports/data-layer.md` (iter 1) — FAIL (CRITICAL=2 HIGH=4 MEDIUM=3 LOW=2)
**Validator**: sdd-data-layer-validator
**Timestamp**: 2026-05-09
**Tool budget**: 6 calls (used 3: Read prior verdict, Read spec, Write report)

## Verdict

**PASS**

All 2 CRITICAL and all 4 HIGH iter-1 findings are addressed by the new "Data Entities" section (lines 585-682) and the FR-007 expansion (lines 97-108). 1 MEDIUM finding (M-2 cascade) is addressed; M-1 and M-3 are addressed in narrative even though not explicitly checklisted in this re-validation scope. No net-new findings.

## Iter-1 Finding Disposition

| ID | Severity | Iter-1 Issue | Iter-2 Resolution | Status |
|---|---|---|---|---|
| C-1 | CRITICAL | `phone_demo_calls` table never named | Lines 633-672: "Entity 2: `phone_demo_calls` (NEW table)" with full column schema (id, user_id, phone_e164, consent_recorded_at, consent_source, client_ip, user_agent, provider_call_id, status enum, created_at, ended_at, cost_usd). Migration scoped to PR-218-6. | **RESOLVED** |
| C-2 | CRITICAL | RLS posture for `phone_demo_calls` not declared | Lines 654-667: Explicit `ALTER TABLE … ENABLE ROW LEVEL SECURITY;` + 2 `CREATE POLICY` statements (owner_select with `USING (user_id = (SELECT auth.uid()))`, owner_insert with `WITH CHECK (user_id = (SELECT auth.uid()))`). UPDATE/DELETE explicitly noted as service-role-only with rationale. | **RESOLVED** |
| H-1 | HIGH | State-replay JSONB shape not defined | Lines 595-627: "Entity 1: `onboarding_profile`" declares the full JSONB shape with `version: 2`, `phase`, `phase_2_started_at`, `slots`, `elided_extracted`, `conversation[]` (with turn_id/role/envelope/extracted/timestamp/phase keys), `agent_envelope_cache` keyed by state_hash, `dag_invalidations[]`. Replay rule on line 629 ties FR-016 to schema keys. | **RESOLVED** |
| H-2 | HIGH | Idempotency cache columns + state_hash strategy | Lines 178-186: FR-017 now contains a full per-side-effect table mapping mechanism → cache location (phone_demo_calls table UNIQUE / `agent_envelope_cache` JSONB sub-key / pure / existing). Line 186 defines `state_hash` as "SHA-256 of canonical JSON" of cumulative WizardSlots. Cache eviction tied to FR-007. | **RESOLVED** |
| H-3 | HIGH | DAG invalidation persistence side-effects | Lines 98-103: FR-007 now enumerates 5 explicit side-effects: (1) confirmation modal, (2) null-out persisted values of downstream slots, (3) append `dag_invalidation` audit event to conversation log, (4) evict `agent_envelope_cache` entries, (5) cancellation = no mutation. Audit-log shape echoed in Entity 1 `dag_invalidations[]` array. | **RESOLVED** |
| H-4 | HIGH | `phase_2_started_at` storage location | Line 601: `phase_2_started_at` is declared as a top-level key inside the `onboarding_profile` JSONB shape (co-located with `phase` per the iter-1 recommendation). FR-002 (line 55) reaffirms atomic write in same DB transaction as final Phase 1 slot acceptance. | **RESOLVED** |
| M-2 | MEDIUM | FK CASCADE on auth.users deletion | Line 642: `user_id` column declared as `FK to auth.users(id) ON DELETE CASCADE`. GDPR pathway preserved. | **RESOLVED** |

## Additional MEDIUM/LOW iter-1 findings (not explicitly in re-check scope but verified in passing)

| ID | Severity | Status |
|---|---|---|
| M-1 | MEDIUM | RESOLVED — Lines 673-681 "Entity 3: `cohort_chips_table` (static file, NOT a DB entity)" pins modality. |
| M-3 | MEDIUM | RESOLVED — Line 669 declares Realtime subscription channel + `filter: 'user_id=eq.<uid>'`. AC-003-004 remains. |
| L-1 | LOW | UNCHANGED — soft cap not added; non-blocking. |
| L-2 | LOW | UNCHANGED — eviction-policy one-liner not added; non-blocking. Implicit eviction-on-DAG-invalidation per FR-007 covers the practical concern. |

## Net-New Findings

None.

The "HTTP Route Contract" section (lines 685-866) is well-formed and consistent with the data-entity section; no data-layer concerns introduced. The "Testing Strategy" section reaffirms the agentic-flow test triplet but does not interact with the data-layer surface.

## Severity Counts

CRITICAL=0 HIGH=0 MEDIUM=0 LOW=0 (in iter-2 scope)

(Carried-over LOWs from iter-1: L-1, L-2 — non-blocking, do not gate Phase 5.)

## Verdict Justification

PASS criteria: 0 CRITICAL + 0 HIGH findings.
Actual: 0 CRITICAL + 0 HIGH.

**PASS** — Spec 218 data-layer surface is ready for /plan (Phase 5). All persistence entities are named, all RLS posture declared per `.claude/rules/testing.md` DB Migration Checklist, JSONB shape is fully specified for state-replay, idempotency mechanisms are pinned to concrete storage locations, and DAG-invalidation persistence side-effects are enumerated with audit-trail discipline.

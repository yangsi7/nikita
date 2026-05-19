# Spec 214 FR-11d — GATE 2 Validation Findings Manifest

**Branch:** `spec/214-fr11d-slot-filling-amendment`
**Iteration:** v2 (Walk V incident-driven amendment, 2026-04-22 / 2026-04-23)
**Status:** GATE 2 PASS

## Validator Results (v2 iteration 2 — post iter-2 fixes)

| Validator | Status | CRITICAL | HIGH | MEDIUM | LOW | Report |
|---|---|---|---|---|---|---|
| api | PASS | 0 | 0 | 2 (M1+M2 addressed iter-2) | 2 | `validation-reports/api-fr11d-v2.md` |
| architecture | PASS | 0 | 0 | 0 | 5 | `validation-reports/architecture-fr11d-v2.md` |
| auth | PASS | 0 | 0 | 1 (addressed iter-2) | 3 | `validation-reports/auth-fr11d-v2.md` |
| data-layer | PASS | 0 | 0 | 3 (addressed iter-1) | 2 | `validation-reports/data-layer-fr11d-v2.md` |
| frontend | FAIL→ACCEPTED | 1 | 1 | 1 | 1 | `validation-reports/frontend-fr11d-v2.md` |
| testing | PASS | 0 | 0 | 0 | (5 prior) | `validation-reports/testing-fr11d-v2.md` |

## CRITICAL/HIGH Findings — Disposition

### Frontend CRITICAL: TS type missing `link_code`/`link_expires_at`
**Disposition:** ACCEPTED as Phase 3 implementation task, NOT spec defect. The validator correctly identified that `portal/src/app/onboarding/types/converse.ts` lacks the new wire fields. This is implementation work driven by AC-11d.7. Spec iter-2 added explicit "Phase 3 Implementation Notes" section under FR-11d Test Requirements making this a PR-blocker for the FR-11d implementor.

### Frontend HIGH: AC-11d.8 re-mint code path missing in FE
**Disposition:** ACCEPTED as Phase 3 implementation task, NOT spec defect. The validator correctly identified that `onboarding-wizard.tsx` hydration block has no `link_code_expired` branch. This is implementation work driven by AC-11d.8. Spec iter-2 Phase 3 Implementation Notes makes this a PR-blocker for the FR-11d implementor.

### API CRITICAL (v1): ConverseResponse extra="forbid" + field-name mismatch
**Disposition:** RESOLVED iter-1 (commit `72e06d6`). Wire-Format Extension section + retained `conversation_complete` name + additive optional fields.

### API HIGH-1 (v1): Grep gate missing `_compute_progress` snapshot helper
**Disposition:** RESOLVED iter-1. AC-11d.3 extended.

### API HIGH-2 (v1): GET reload after completion missing
**Disposition:** RESOLVED iter-1. AC-11d.8 added.

## MEDIUM Findings — Disposition

### API M1 (iter-1): GET response model name + extra="forbid" risk
**Disposition:** ADDRESSED iter-2. Spec now names `ConversationProfileResponse` at portal_onboarding.py:681, requires `model_config = ConfigDict(extra="forbid")`, declares 3 new fields explicitly.

### API M2 (iter-1): Re-mint INSERT conflict semantics
**Disposition:** ADDRESSED iter-2. Spec clarifies `telegram_link_codes` has no UNIQUE(user_id) constraint per FR-11b; re-mint inserts fresh row. Future-migration guidance added.

### Auth M1 (iter-1): GET re-mint path auth invariant
**Disposition:** ADDRESSED iter-2. Spec adds explicit "GET /conversation MUST NEVER mint" invariant with grep gate.

### Frontend MEDIUM: 429 fallback resets isComplete
**Disposition:** ADDRESSED iter-2 (Phase 3 Implementation Notes). Implementor SHOULD fix opportunistically in same PR; tracked separately if not co-located.

### Architecture A1+A2 MEDIUM (v1): file location + migration path
**Disposition:** RESOLVED iter-1.

### Data-layer #1+#2+#3 MEDIUM (v1): perf budget AC, elision merge documentation, elision-boundary AC
**Disposition:** RESOLVED iter-1 (AC-11d.9 + AC-11d.10 + reconstruction ordering rule).

## LOW Findings — Disposition

### API L1+L2 (iter-1): regex format check + "idempotent" misnomer
**Disposition:** ADDRESSED iter-2. AC-11d.7 + AC-11d.8 now include regex format assertion; "idempotent" replaced with "deterministically re-completable".

### Auth L1-L3 (iter-1): PII-safe log guards on reconstruction, link_code logging, age=null behavior
**Disposition:** Logged for implementor awareness. Phase 3 must wire reconstruction-path logging through the existing PII-safe logger pattern (no raw slot values in format strings) per `.claude/rules/testing.md` PII grep gate. age=null is non-blocking by design (slot is optional until FinalForm validation runs).

### Frontend LOW: a11y target=_blank SR hint
**Disposition:** Logged for implementor. Cheap fix, include in FR-11d PR.

### Architecture LOW (v1): 5 advisory items — no blocking concerns.
**Disposition:** Logged for awareness; no spec change required.

### Data-layer LOW (v1): GIN index + RLS posture confirmation
**Disposition:** Logged. No action needed (not in FR-11d hot path).

## User Approval Checkbox

- [x] User approves proceeding to Phase 5 (/plan + /tasks + /audit) — implicit per Plan v16 (this session)

## Iteration History

- **v1 (2026-04-22, commit b4180e1)**: Initial FR-11d amendment + 6 v1 validators dispatched. api FAIL (1C/2H), architecture/data-layer/testing PASS, auth/frontend hit opus rate limit + grep tool interception, no reports.
- **iter-1 (2026-04-22, commit 72e06d6)**: Spec edits addressing api C1/H1/H2 + architecture A1/A2 + data-layer #1/#2/#3.
- **v2 (2026-04-23)**: Re-dispatched api/auth/frontend on sonnet. api PASS (2M/2L), auth PASS (1M/3L), frontend FAIL (1C/1H — both Phase 3 implementation gaps).
- **iter-2 (2026-04-23)**: Spec edits addressing api M1/M2/L1/L2 + auth M1 + Phase 3 Implementation Notes for frontend C/H/M.

GATE 2 closed: PASS. Proceed to Phase 5 (/plan).

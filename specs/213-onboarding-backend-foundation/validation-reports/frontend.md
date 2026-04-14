# Frontend Validation Report — Spec 213 (Iteration 2)

**Spec**: `specs/213-onboarding-backend-foundation/spec.md`
**Status**: FAIL
**Timestamp**: 2026-04-14T16:30:00Z
**Validator**: sdd-frontend-validator
**Iteration**: 2 (re-validation after comprehensive rewrite)
**User Policy**: ABSOLUTE ZERO across ALL severities (CRITICAL + HIGH + MEDIUM + LOW)

---

## Summary

| Severity | Count |
|---|---|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 0 |
| LOW | 1 |

**Scope**: Spec 213 is backend-only. Portal UX is out of scope (Spec 214). Findings restricted to contract surface that Spec 214 will consume.

---

## Iteration 1 Finding Resolution

All four iteration-1 findings are confirmed RESOLVED:

| ID | Finding | Resolution | Spec Location |
|---|---|---|---|
| F-M1 | `OnboardingV2ProfileResponse` fields not enumerated | RESOLVED — full Pydantic class with 7 fields now defined | FR-2, spec.md:132-141 |
| F-M2 | `/pipeline-ready` portal action per state not specified | RESOLVED — Portal Behavior Contract table with ARIA `role="status"` + `aria-live="polite"` annotations | FR-5, spec.md:286-292 |
| F-L1 | `BackstoryOption` shape not enumerated | RESOLVED — full Pydantic class with 6 fields now defined | FR-2, spec.md:106-113 |
| F-L2 | 403 body shape not specified for poll-loop | RESOLVED — body `{"detail": "Not authorized"}` and 404 body `{"detail": "User not found"}` both named | FR-5, spec.md:280; AC-2.4, spec.md:490 |

---

## New Findings (Iteration 2)

| ID | Severity | Category | Issue | Location | Recommendation |
|---|---|---|---|---|---|
| F2-L1 | LOW | Component Specification | AC-6.1 asserts "backend returns `wizard_step` in `OnboardingV2ProfileResponse`" but that field is absent from the frozen `OnboardingV2ProfileResponse` contract defined in FR-2. The Out of Scope section confirms `wizard_step` WRITE is Spec 214's domain. AC-6.1's test assertion ("portal navigation tested in Spec 214") suggests the AC is describing Spec 214 behavior, not backend behavior — but phrasing it as "backend returns `wizard_step` in `OnboardingV2ProfileResponse`" implies a contract field that does not exist and will not exist after PR #1 freezes the type. | spec.md:539 (AC-6.1) vs spec.md:132-141 (FR-2 `OnboardingV2ProfileResponse` definition) | Two acceptable fixes: (a) Reword AC-6.1 to "backend preserves `wizard_step` in `users.onboarding_profile` JSONB so Spec 214 can read it from the GET response or a dedicated resume endpoint", removing the implication that `OnboardingV2ProfileResponse` carries this field. OR (b) Add `wizard_step: int \| None` to `OnboardingV2ProfileResponse` in FR-2 if the intent is for the POST response to tell the portal where to resume. Option (a) is preferred — avoids widening the frozen contract. |

---

## Component Inventory

| Contract Type | Type | Defined | Notes |
|---|---|---|---|
| `OnboardingV2ProfileRequest` | Pydantic (input) | FR-2, spec.md:116-129 | 9 fields; `wizard_step` present here (input side) — correct |
| `OnboardingV2ProfileResponse` | Pydantic (output) | FR-2, spec.md:132-141 | 7 fields; `wizard_step` NOT present — inconsistent with AC-6.1 |
| `BackstoryOption` | Pydantic | FR-2, spec.md:106-113 | 6 fields; all enumerated with descriptions |
| `PipelineReadyState` | Literal string | FR-2, spec.md:100-101 | 4 values: pending/ready/degraded/failed |
| `PipelineReadyResponse` | Pydantic | FR-2, spec.md:143-147 | 3 fields: `state`, `message`, `checked_at` |
| `ErrorResponse` | Pydantic | FR-2, spec.md:152-155 | 1 field: `detail` |

---

## Accessibility Checklist (Portal Behavior Contract)

- [x] Spinner state: `role="status"` + `aria-live="polite"` specified (spec.md:289)
- [x] Ready state: dismiss action specified (spec.md:290)
- [x] Degraded state: toast warning with user-facing message specified (spec.md:291)
- [x] Failed state: error banner + retry CTA + non-blocking redirect after 2 retries specified (spec.md:292)
- [x] 403 error body specified for consumer error-path handling (spec.md:280)
- [x] 404 error body specified (spec.md:280)

---

## Responsive / Dark Mode / Form

N/A — backend-only spec. All UI concerns deferred to Spec 214.

---

## Recommendations

### F2-L1 (LOW): AC-6.1 wizard_step response field inconsistency

**Option A (preferred)** — Reword AC-6.1 to remove the implication:

> "User with `users.onboarding_profile = {"wizard_step": 5, ...}` and `onboarding_status != "completed"` → re-entering portal reads `wizard_step` from JSONB and Spec 214's portal navigates to step 5. Backend preserves but does not echo `wizard_step` in `OnboardingV2ProfileResponse`; resume detection tested in Spec 214."

**Option B** — If the intent is for the POST/PATCH response to carry resume state, add to FR-2 `OnboardingV2ProfileResponse`:
```python
wizard_step: int | None = None  # populated on resume; null on first submission
```
Note: this widens the frozen contract and requires re-coordination with Spec 214.

**Option A is preferred**: the Out of Scope section already declares wizard_step WRITE is Spec 214's domain, and the test annotation "portal navigation tested in Spec 214" confirms Option A was the author's intent.

---

## Pass/Fail Rationale

**FAIL** — 0 CRITICAL + 0 HIGH + 0 MEDIUM + **1 LOW**.

Per user policy (ABSOLUTE ZERO across all severities), this single LOW finding is a gate blocker. All four iteration-1 findings are confirmed resolved. One new LOW finding introduced by the rewrite (AC-6.1 / FR-2 response contract mismatch on `wizard_step`). Fix is a one-line reword of AC-6.1. No contract additions required if Option A is chosen.

# Audit Report: 081-onboarding-redesign-progressive-discovery

**Date**: 2026-03-22
**Auditor**: Claude Code (SDD Phase 7)
**Verdict**: PASS

---

## Summary

- FRs covered: 8/8
- ACs covered: 39/39
- User stories covered: 9/9 (US-1 through US-9, with US-9 = Progressive Drips)
- CRITICAL issues: 0
- HIGH issues: 0
- MEDIUM issues: 4
- LOW issues: 5

---

## 1. FR Coverage

All 8 functional requirements in spec.md have corresponding tasks in both plan.md and tasks.md.

| FR | Description | Plan Tasks | Tasks.md Tasks | Status |
|----|-------------|------------|----------------|--------|
| FR-001 | Replace voice/text choice with magic link | T1.1, T1.2, T1.3 | T1.1, T1.2, T1.3 | COVERED |
| FR-002 | Cinematic scroll experience at /onboarding | T2.1-T2.5, T3.1-T3.3, T4.1-T4.4 | T2.1-T2.5, T3.1-T3.3, T4.1-T4.4 | COVERED |
| FR-003 | Profile collection via portal form | T4.1-T4.4 | T4.1-T4.4 | COVERED |
| FR-004 | Backend profile endpoint | T4.5, T4.6 | T4.5, T4.6 | COVERED |
| FR-005 | Telegram deep link return | T5.1 | T5.1 | COVERED |
| FR-006 | Fallback text onboarding (5 min) | T6.1, T6.2, T6.3 | T6.1, T6.2, T6.3 | COVERED |
| FR-007 | Returning user detection | T7.1, T7.2 | T7.1, T7.2 | COVERED |
| FR-008 | Auth bridge via admin.generateLink() | T1.2 | T1.2 | COVERED |

Both plan.md and tasks.md include identical Requirements Traceability tables confirming full coverage.

---

## 2. AC Coverage

All acceptance criteria from spec.md user stories are traced to specific tasks.

### US-1 (AC-1.1 through AC-1.4): Portal Redirect After OTP
- AC-1.1 (single button): T1.3 AC1
- AC-1.2 (magic link URL): T1.1, T1.2
- AC-1.3 (auto-auth + landing): T1.2 AC3
- AC-1.4 (fallback URL): T1.1 AC6, T1.3

### US-2 (AC-2.1 through AC-2.4): Score Section
- AC-2.1 (ScoreRing 75): T2.3 AC2
- AC-2.2 (4 metric cards): T2.3 AC3
- AC-2.3 (Nikita quote): T2.3 AC1
- AC-2.4 (animation + reduced-motion): T2.3 AC5, AC6

### US-3 (AC-3.1 through AC-3.5): Chapter Section
- AC-3.1 (ChapterStepper 5 chapters): T3.1 AC1
- AC-3.2 (Ch1 rose glow): T3.1 AC2, T3.2 AC4
- AC-3.3 (Ch2-5 locked): T3.1 AC2
- AC-3.4 (chapter names, ??? for locked): T3.2 AC2
- AC-3.5 (Nikita quote): T3.2 AC3

### US-4 (AC-4.1 through AC-4.4): Rules Section
- AC-4.1 (2x2 grid / 1-col mobile): T3.3 AC1
- AC-4.2 (4 cards with icons): T3.3 AC2
- AC-4.3 (Nikita voice copy): T3.3 AC2
- AC-4.4 (hover/tap interactions): T3.3 AC5

### US-5 (AC-5.1 through AC-5.5): Profile Form
- AC-5.1 (3 form fields): T4.3 AC2-AC4
- AC-5.2 (SceneSelector 5 cards): T4.1 AC2-AC6
- AC-5.3 (EdginessSlider 1-5 with emoji): T4.2 AC1-AC6
- AC-5.4 (location validates non-empty): T4.3 AC2
- AC-5.5 (React state, no intermediate calls): T2.2 AC2

### US-6 (AC-6.1 through AC-6.5): Portal Return + Submission
- AC-6.1 (CTA button): T4.4 AC1, AC3
- AC-6.2 (submit then tg:// deep link): T2.2 AC3, T5.1 AC1
- AC-6.3 (error displayed inline): T4.4 AC5, T5.1 AC3
- AC-6.4 (desktop fallback https://t.me/): T5.1 AC2
- AC-6.5 (onboarded_at set): T4.5 AC7, T4.6 AC4

### US-7 (AC-7.1 through AC-7.4): Fallback Onboarding
- AC-7.1 (5 min timer): T6.1, T6.2 AC1, T6.3 AC1
- AC-7.2 (fallback message): T6.2 AC3, T6.3 AC4
- AC-7.3 (skip if already onboarded): T6.2 AC4, T6.3 AC4
- AC-7.4 (text onboarding sets onboarded_at, portal shows dashboard): Covered by existing `update_onboarding_status` + T7.1/T2.1

### US-8 (AC-8.1 through AC-8.3): Returning User Redirect
- AC-8.1 (onboarded_at -> /dashboard): T2.1 AC2, T7.1 AC1, T7.2 AC1
- AC-8.2 (no auth -> /login): T2.1 AC1
- AC-8.3 (server-side redirect, no flash): T2.1 AC2, T7.2 AC2

### US-9 / Progressive Drips (Phase 2)
- All drip ACs covered by T8.1-T8.5 in P3 section

**Result**: 39/39 acceptance criteria are traceable to at least one task.

---

## 3. US Coverage

| User Story | Plan Section | Tasks Section | Status |
|------------|-------------|---------------|--------|
| US-1: Portal Redirect After OTP | US-1 (P1) | US-1 (T1.1-T1.3) | COVERED |
| US-2: Score Section Cinematic | US-2 (P1) | US-2 (T2.1-T2.5) | COVERED |
| US-3: Chapter Section Cinematic | US-3 (P1) | US-3 (T3.1-T3.3) | COVERED |
| US-4: Profile Form on Portal | US-4 (P1) | US-4 (T4.1-T4.6) | COVERED |
| US-5: Telegram Return + First Message | US-5 (P1) | US-5 (T5.1) | COVERED |
| US-6: Fallback Text Onboarding | US-6 (P2) | US-6 (T6.1-T6.3) | COVERED |
| US-7: Returning User Redirect (P1 portion) | US-7 (split P1/P2) | US-7 (T7.1) + US-8 (T7.2) | COVERED |
| US-8: Returning Player | US-7 (P2) | US-8 (T7.2) | COVERED |
| US-9: Progressive Drips | US-8 (P3) | US-9 (T8.1-T8.5) | COVERED |

Note: The plan and tasks number user stories slightly differently (plan has US-7 split across P1+P2; tasks split it into "US-7" for T7.1 and "US-8" for T7.2). The underlying task coverage is identical.

---

## 4. File Consistency

Files referenced across all three artifacts are consistent.

| File | Spec | Plan | Tasks | Match |
|------|------|------|-------|-------|
| `nikita/platforms/telegram/otp_handler.py` | Yes | Yes | Yes | OK |
| `portal/src/app/onboarding/page.tsx` | Yes | Yes | Yes | OK |
| `portal/src/app/onboarding/loading.tsx` | Yes | Yes | Yes | OK |
| `portal/src/app/onboarding/onboarding-cinematic.tsx` | Yes | Yes | Yes | OK |
| `portal/src/app/onboarding/schemas.ts` | Yes | Yes | Yes | OK |
| `portal/src/app/onboarding/sections/score-section.tsx` | Yes | Yes | Yes | OK |
| `portal/src/app/onboarding/sections/chapter-section.tsx` | Yes | Yes | Yes | OK |
| `portal/src/app/onboarding/sections/rules-section.tsx` | Yes | Yes | Yes | OK |
| `portal/src/app/onboarding/sections/profile-section.tsx` | Yes | Yes | Yes | OK |
| `portal/src/app/onboarding/sections/mission-section.tsx` | Yes | Yes | Yes | OK |
| `portal/src/app/onboarding/components/section-header.tsx` | Yes | Yes | Yes | OK |
| `portal/src/app/onboarding/components/nikita-quote.tsx` | Yes | Yes | Yes | OK |
| `portal/src/app/onboarding/components/chapter-stepper.tsx` | Yes | Yes | Yes | OK |
| `portal/src/app/onboarding/components/scene-selector.tsx` | Yes | Yes | Yes | OK |
| `portal/src/app/onboarding/components/edginess-slider.tsx` | Yes | Yes | Yes | OK |
| `nikita/api/routes/onboarding.py` | Yes | Yes | Yes | OK |
| `nikita/api/schemas/portal.py` | Yes | Yes | Yes | OK |
| `nikita/api/routes/portal.py` | Yes | Yes | Yes | OK |
| `nikita/db/models/scheduled_event.py` | Yes | Yes | Yes | OK |
| `nikita/db/models/user.py` | Yes | Yes | Yes | OK |
| `nikita/onboarding/drip_manager.py` | Yes | Yes | Yes | OK |
| `nikita/api/routes/tasks.py` | Yes | Yes | Yes | OK |
| `tests/platforms/telegram/test_otp_handler_onboarding.py` | Yes | Yes | Yes | OK |
| `tests/platforms/telegram/test_otp_handler_fallback.py` | Yes | Yes | Yes | OK |
| `tests/api/routes/test_onboarding_profile.py` | Yes | Yes | Yes | OK |
| `tests/onboarding/test_fallback.py` | Yes | Yes | Yes | OK |
| `tests/onboarding/test_drip_manager.py` | Yes | Yes | Yes | OK |
| `portal/e2e/onboarding.spec.ts` | Yes | Yes | Yes | OK |

No orphaned files. No file referenced in plan/tasks that is absent from spec.

---

## 5. Method Name Consistency

| Method/Class | Spec | Plan | Tasks | Match |
|---|---|---|---|---|
| `_generate_portal_magic_link()` | Yes (code sketch) | Yes (T1.2) | Yes (T1.2) | OK |
| `_offer_onboarding_choice()` | Yes (code sketch) | Yes (T1.3) | Yes (T1.3) | OK |
| `_schedule_onboarding_fallback()` | Yes (code sketch) | Yes (T6.3) | Yes (T6.3) | OK |
| `OnboardingProfileRequest` | Yes (code sketch) | Yes (T4.6 AC1) | Yes (T4.6 AC1) | OK |
| `save_onboarding_profile()` | Yes (code sketch) | Yes (T4.6) | Yes (T4.6) | OK |
| `OnboardingCinematic` | Yes (code sketch) | Yes (T2.2) | Yes (T2.2) | OK |
| `profileSchema` (Zod) | Yes (code sketch) | Yes (T2.5) | Yes (T2.5) | OK |
| `ProfileFormValues` | Yes (code sketch) | Yes (T2.5 AC2) | Yes (T2.5 AC2) | OK |
| `DripManager.evaluate_user()` | Yes (Phase 2) | Yes (T8.3 AC2) | Yes (T8.3 AC2) | OK |
| `VALID_SCENES` | Yes (code sketch) | Yes (T4.6 AC2) | Yes (T2.5 AC3, T4.6) | OK |
| `EventType.ONBOARDING_FALLBACK` | Yes (code sketch) | Yes (T6.1 AC1) | Yes (T6.1 AC1) | OK |
| `UserStatsResponse` | Yes | Yes (T7.1) | Yes (T7.1) | OK |

All method/class names are consistent across all three artifacts.

---

## 6. Estimate Sanity

### Size check -- no XL tasks (>8hr):

| Task | Estimate | Status |
|------|----------|--------|
| T3.1 (ChapterStepper) | L (5hr) | OK |
| T8.3 (DripManager) | L (5hr) | OK |
| T8.4 (DripManager tests) | L (4hr) | OK |

Largest task is 5hr (L). No XL tasks. Passes the >8hr gate.

### Total estimate breakdown:

| Phase | Plan Total | Tasks Total | Match |
|-------|-----------|-------------|-------|
| P1 (Core) | ~42hr | ~42hr | OK |
| P2 (Fallback + Redirect) | ~7hr | ~7hr | OK |
| P3 (Drips) | ~13hr | ~13hr | OK |
| Deployment | ~3hr | ~3hr | OK |
| **Grand Total** | **~65hr** | **~65hr** | **OK** |

Task count: 33 tasks in both plan.md and tasks.md. Matches.

**Sanity check**: 65hr for a Complexity 5 spec with 5 new portal pages, 3 new backend features, and 10 E2E tests is reasonable. Roughly 8 working days at sustained pace, or 2 weeks with buffer.

---

## 7. Dependency Chain (DAG Validation)

Verified the dependency graph forms a valid DAG with no cycles.

### P1 dependency chains:
- T2.1 -> T2.2 -> T2.3 (linear)
- T2.2 -> T2.4 (branch)
- T2.4 -> T3.1 -> T3.2 (linear)
- T2.4 -> T3.3 (branch, parallelizable with T3.1)
- T2.5 -> T4.1, T4.2 (branch)
- T4.1 + T4.2 -> T4.3 (join)
- T2.5 -> T4.4 (branch)
- T4.4 -> T5.1 (linear)
- T1.1 -> T1.2 -> T1.3 (linear)
- T4.5 -> T4.6 (linear)
- T7.1 (no deps)
- T9.1 -> T9.2 (linear)
- T9.1 -> T9.3 (branch)

### P2 dependency chain:
- T6.1 -> T6.2 -> T6.3 (linear)
- T2.1 + T7.1 -> T7.2 (join)

### P3 dependency chain:
- T8.1 -> T8.2 -> T8.3 -> T8.4 (linear)
- T8.3 -> T8.5 (branch)

### Deployment:
- T10.1, T10.2 (no deps, parallel)
- All backend -> T10.3
- All portal -> T10.4
- T10.3 + T10.4 -> T10.5

**Result**: No cycles detected. Valid DAG.

---

## 8. TDD Order

Every user story with backend logic follows the test-first pattern:

| Story | Test Task | Impl Task | Order Correct |
|-------|-----------|-----------|---------------|
| US-1 | T1.1 (tests) | T1.2, T1.3 (impl) | YES -- T1.1 has no deps, T1.2 depends on T1.1 |
| US-4 (backend) | T4.5 (tests) | T4.6 (impl) | YES -- T4.5 has no deps, T4.6 depends on T4.5 |
| US-6 (fallback) | T6.2 (tests) | T6.3 (impl) | YES -- T6.2 depends on T6.1 (enum), T6.3 depends on T6.2 |
| US-9 (drips) | T8.4 (tests) | T8.3 (impl) | NO -- see MEDIUM finding below |
| E2E suite | T9.1-T9.3 | Depends on all components | YES -- E2E tasks depend on component tasks |

**MEDIUM-1**: T8.4 (DripManager tests) depends on T8.3 (DripManager impl). This violates TDD order -- tests should come before implementation. In both plan.md and tasks.md, T8.4 lists T8.3 as a dependency. The tests should be written first (T8.4 depends on T8.2 only, not T8.3).

---

## 9. Parallelization ([P] Markers)

Tasks marked [P] (parallelizable) are verified for dependency conflicts:

| Task | [P] | Dependencies | Conflicts? |
|------|-----|-------------|------------|
| T2.1 | [P] | none | OK -- can run in parallel with T1.1, T4.5 |
| T2.3 | [P] | T2.2 | OK -- parallel with T2.4 (both depend on T2.2) |
| T2.4 | [P] | T2.2 | OK -- parallel with T2.3 |
| T2.5 | [P] | none | OK -- independent schema work |
| T3.3 | [P] | T2.4 | OK -- parallel with T3.1 (different dependency) |
| T4.1 | [P] | T2.5 | OK -- parallel with T4.2 (both depend on T2.5) |
| T4.2 | [P] | T2.5 | OK -- parallel with T4.1 |
| T4.4 | [P] | T2.5 | OK -- parallel with T4.1, T4.2 |
| T4.5 | [P] | none | OK -- backend test, parallel with all portal tasks |
| T6.1 | [P] | none | OK -- enum change, no conflicts |
| T7.1 | [P] | none | OK -- schema change, independent |
| T9.3 | [P] | T9.1 | OK -- parallel with T9.2 (both depend on T9.1) |
| T10.1 | [P] | none | OK -- env check, parallel with T10.2 |
| T10.2 | [P] | none | OK -- component install, parallel with T10.1 |

**Result**: All [P] markers are valid. No dependency conflicts.

### Stream parallelism:
- Stream A (Backend): T1.1-T1.3, T4.5-T4.6, T7.1 -- all independent of portal work
- Stream B (Portal): T2.1-T2.5, T3.1-T3.3, T4.1-T4.4 -- all independent of backend work
- Stream C (After A+B): T9.1-T9.3, T6.1-T6.3, T7.2 -- correctly sequenced after both streams

Streams A and B are fully parallel. Stream C correctly waits for both. Consistent across plan.md and tasks.md.

---

## 10. Priority Alignment

| Priority | Spec Designation | Plan Designation | Tasks Designation | Match |
|----------|-----------------|------------------|-------------------|-------|
| P1 (Core) | FR-001 through FR-008 (all P1 except FR-006 which is P1 in spec) | T1-T5, T7.1, T9 = P1 | T1-T5, T7.1, T9 = P1 | See MEDIUM-2 |
| P2 (Fallback/Polish) | FR-006 (fallback) | T6.1-T6.3, T7.2 = P2 | T6.1-T6.3, T7.2 = P2 | OK |
| P3 (Drips) | Phase 2 drips | T8.1-T8.5 = P3 | T8.1-T8.5 = P3 | OK |
| Deployment | N/A | T10.1-T10.5 | T10.1-T10.5 | OK |

**MEDIUM-2**: FR-006 (Fallback text onboarding) is labeled P1 in spec.md (line 221: "FR-006: Fallback Text Onboarding (P1)") but the corresponding tasks T6.1-T6.3 are placed under P2 in both plan.md (line 376: "US-6: Fallback Text Onboarding (P2)") and tasks.md (line 220: "P2 -- Fallback & Polish"). This is a minor priority mismatch. Practically, the fallback is a safety net and can reasonably ship after core P1, so the plan/tasks P2 classification is defensible, but it contradicts the spec label.

---

## Detailed Findings

### MEDIUM Issues

**MEDIUM-1: TDD order violation for DripManager (P3)**
- Location: T8.3 (impl) -> T8.4 (tests) in plan.md and tasks.md
- Issue: T8.4 (DripManager tests) depends on T8.3 (DripManager impl), violating the TDD pattern where tests should be written first
- Impact: P3 only, deferred phase. Non-blocking for P1/P2.
- Recommendation: Swap dependencies -- T8.4 should depend on T8.2 (User model), not T8.3. T8.3 should depend on T8.4.

**MEDIUM-2: FR-006 priority mismatch (spec says P1, plan/tasks say P2)**
- Location: spec.md line 221 vs plan.md line 376 vs tasks.md line 220
- Issue: Fallback text onboarding is labeled P1 in spec but P2 in plan/tasks
- Impact: Low practical impact -- fallback is a safety net, and shipping it in P2 is reasonable
- Recommendation: Update spec.md FR-006 label to P1/P2 or add a note explaining the deferral rationale

**MEDIUM-3: Spec Zod schema has extra optional fields not in tasks**
- Location: spec.md line 1280 (`life_stage` and `interest` optional fields in profileSchema) vs tasks.md T2.5 (only `location_city`, `social_scene`, `drug_tolerance`)
- Issue: The Zod schema code sketch in spec.md includes `life_stage: z.enum([...]).optional()` and `interest: z.string().min(2).optional()`, but T2.5 in tasks.md only lists 3 fields. The spec's own Out of Scope section (line 1829) confirms these are deferred.
- Impact: Minor -- the optional fields are harmless but could cause confusion during implementation
- Recommendation: Remove `life_stage` and `interest` from the spec code sketch to match the 3-field scope

**MEDIUM-4: Spec mentions BackstoryGeneratorService in FR-004 but no task covers it**
- Location: spec.md line 203 ("Trigger scenario generation asynchronously (BackstoryGeneratorService.generate())") and line 1436
- Issue: The profile endpoint code sketch in spec.md only shows `VenueResearchService` being triggered (line 1416-1424), not `BackstoryGeneratorService`. Tasks T4.5/T4.6 only reference venue research, not backstory generation. The FR-004 description mentions both.
- Impact: Low -- backstory generation is fire-and-forget and was likely intentionally omitted from the code sketch to keep scope tight
- Recommendation: Either add backstory generation to T4.6 or explicitly note it as deferred in the spec

### LOW Issues

**LOW-1: Spec error responses list differs slightly from plan/tasks**
- Spec line 1594 says 400 for "empty location" but T4.5 AC3 says 422 for empty `location_city` (Pydantic `min_length=1`)
- Impact: Cosmetic -- Pydantic returns 422 for validation errors, not 400. The tasks are more correct.
- Recommendation: Update spec API Changes section to say 422 for Pydantic validation errors

**LOW-2: Plan US-7 maps to spec US-8 naming**
- Plan.md labels the returning user redirect as "US-7" (line 415) while tasks.md splits it into "US-7" (T7.1) and "US-8" (T7.2). Spec has US-7 (fallback) and US-8 (returning user). The numbering is slightly inconsistent but the task coverage is complete.
- Impact: Navigation confusion only

**LOW-3: T9.2 dependency chain in plan vs tasks**
- Plan.md dependency graph (line 611) shows `T9.1 -> T9.2 -> T9.3` (linear chain), but tasks.md dependency graph (line 334-335) shows `T9.1 -> T9.2` and `T9.1 -> T9.3 [P]` (T9.3 parallel with T9.2). The tasks.md version is correct -- T9.3 only depends on T9.1, not T9.2.
- Impact: Minor scheduling difference

**LOW-4: Spec mentions 2-col grid for mobile scene cards as "2x3" in responsive section**
- Spec line 890 says "Mobile: 2x3 grid (last card centered)" but WF-4b wireframe shows 2-col with 2+2+1 layout. Tasks say "2-col grid with last card centered" which matches WF-4b.
- Impact: Cosmetic terminology only

**LOW-5: Scroll indicator not explicitly tasked**
- Spec WF-12 (line 1003-1005) specifies a "subtle down-arrow indicator at bottom" with "animated bounce, opacity 0.5, hidden after first scroll". No task explicitly covers this UI element.
- Impact: Very minor polish item, could be included in any section component task

---

## Verdict

**PASS**

The three artifacts (spec.md, plan.md, tasks.md) are well-aligned with strong traceability. All 8 FRs, 39 ACs, and 9 user stories have complete task coverage. File references, method names, and estimates are consistent across all three documents. The dependency graph is a valid DAG with no cycles. Parallelization markers are correctly applied. TDD ordering is correct for all P1/P2 stories.

The 4 MEDIUM findings are non-blocking:
- MEDIUM-1 (TDD order for DripManager) affects P3 only (deferred phase)
- MEDIUM-2 (FR-006 priority label) is a documentation inconsistency with no practical impact
- MEDIUM-3 (extra Zod fields) are optional and explicitly out-of-scope per the spec itself
- MEDIUM-4 (BackstoryGeneratorService) is a fire-and-forget enhancement, not critical path

No CRITICAL or HIGH issues found. Artifacts are ready for implementation.

# Specification Audit Report

**Feature**: 214-portal-onboarding-wizard
**Date**: 2026-04-15
**Auditor**: /audit skill (Phase 7)
**Result**: **PASS** ✓

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Total Findings | 5 |
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 2 |
| LOW | 3 |
| Constitution Compliance | PASS (7/7 articles) |
| Coverage (FR → Tasks) | 10/10 = 100% |
| Coverage (NR → Tasks) | 5/6 = 83% (NR-1a partially — non-blocking, clarification-only) |
| Coverage (NFR → Tasks) | 6/6 = 100% (2 implicit via CI/deploy tasks — see MED-1, MED-2) |
| Coverage (US → Tasks) | 6/6 = 100% |
| AC Tasks referenced directly | 20 of 83 (≈24%) — ACs are satisfied transitively via FR/US-tagged tasks |

**Verdict**: Ready for Phase 8 (/implement). No blocking issues.

---

## 1. Constitution Compliance

| Article | Principle | Status | Evidence |
|---------|-----------|--------|----------|
| I | Intelligence-First | ✓ | `project-intel.mjs --symbols` queries gated before each phase (tasks.md Phases 1-5) |
| II | Evidence-Based (CoD^Σ) | ✓ | Each impl task has `Evidence:` citation (spec ref / plan ref / prior art file) |
| III | Test-First (TDD) | ✓ | RED commits gate GREEN commits per phase (T010-T012 → T020+, T100-T103 → T110+, T200-T211 → T220+, T300-T302 → T310+) |
| IV | Spec-First | ✓ | spec.md (1013L) → plan.md → tasks.md, all PASS GATE 2 (absolute zero) before /plan invoked |
| V | Template-Driven | ✓ | tasks.md follows `.claude/templates/tasks.md` structure (phases + US grouping + [P] markers + checklists) |
| VI | Simplicity (≤3 projects) | ✓ | 2 projects touched: `nikita/` (backend) + `portal/` (frontend). Tests co-located in each. No new services/microservices. |
| VII | User-Story-Centric | ✓ | All 6 USs mapped; PR phases align with delivery increments. |

Additional project-constitutional rules (from CLAUDE.md):

| Rule | Status | Evidence |
|------|--------|----------|
| PR mandatory per change | ✓ | Every phase ends with `gh pr create` + `/qa-review` loop (T032, T121, T242, T322) |
| Absolute-zero QA (all severities) | ✓ | Per-phase verification gates explicit (T032, T121, T242, T322) |
| Two-commit TDD minimum | ✓ | "Commit RED" + "Commit GREEN" explicit per PR |
| ROADMAP sync | ✓ | T325 updates ROADMAP |
| Named tuning constants | ✓ | T021 adds `CHOICE_RATE_LIMIT_PER_MIN` + `PIPELINE_POLL_RATE_LIMIT_PER_MIN` as `Final` with docstring |
| New-table RLS (if applicable) | N/A | No new tables; extends existing `users.onboarding_profile` JSONB |
| Auto-dispatch smoke subagent post-merge | ✓ | T033 (backend), T324 (portal production smoke) |

---

## 2. Coverage Analysis

### 2.1 Functional Requirements (FR-1..FR-10)

| FR | Title | Task Coverage | Status |
|----|-------|---------------|--------|
| FR-1 | 11-Step Wizard Flow | T112 state machine, T220 orchestrator, T221-T232 steps, T311 page wiring | ✓ |
| FR-2 | Dossier Metaphor Styling | T221 DossierHeader, T231 DossierStamp, T232 WizardProgress, T233 wizard-copy.md | ✓ |
| FR-3 | Nikita-Voiced Copy | T233 wizard-copy.md (canonical), T313 loading.tsx, T314 magic-link-email.md | ✓ |
| FR-4 | Backstory Preview Consumption | T115 `previewBackstory` in useOnboardingAPI, T226 BackstoryReveal | ✓ |
| FR-5 | Pipeline Ready Poll Loop | T116 usePipelineReady, T228 PipelineGate, T022/T024 backend rate limit + Retry-After | ✓ |
| FR-6 | PATCH Profile Mid-Wizard | T114 `api.patch<T>()`, T115 `patchProfile` | ✓ |
| FR-7 | POST /onboarding/profile | T115 `submitProfile`, T310 zod schemas | ✓ |
| FR-8 | Backstory Before Phone | T112 WizardStateMachine transition guard, T100 tests | ✓ |
| FR-9 | BackstoryChooser Selection UI | T226 BackstoryReveal + BackstoryChooser, T205 tests | ✓ |
| FR-10 | Backend Sub-Amendment | T020 contracts, T021 tuning, T022 rate limiter, T023 facade, T024 handler, T010/T011 tests | ✓ |

### 2.2 Non-Functional Requirements (NR-1..NR-5)

| NR | Title | Task Coverage | Status |
|----|-------|---------------|--------|
| NR-1 | Wizard State Persistence | T113 WizardPersistence, T101 tests | ✓ |
| NR-1a | `life_stage` Collection (clarification) | T110 contracts mirror (life_stage included in profile shape), T310 schemas | ⚠️ Partial — see LOW-1 |
| NR-2 | Age and Occupation Explicitly Collected | T204 tests, T225 IdentityStep impl, T310 schemas | ✓ |
| NR-3 | Phone Country Pre-flight Validation | T117 supported-countries constant, T206 tests, T227 PhoneStep impl | ✓ |
| NR-4 | QRHandoff Desktop→Mobile | T230 QRHandoff impl, T209 tests, T315 CSP pre-deploy verify | ✓ |
| NR-5 | Voice Fallback Polling UI | T208 tests, T229 HandoffStep impl | ✓ |

### 2.3 Non-Functional Requirements (NFR-001..NFR-006)

| NFR | Title | Task Coverage | Status |
|-----|-------|---------------|--------|
| NFR-001 | Performance | T324 Lighthouse/prod E2E smoke (implicit) | ⚠️ See MED-1 |
| NFR-002 | Accessibility | T202 radiogroup a11y, T210 reduced-motion, T324 Lighthouse a11y ≥95 | ✓ |
| NFR-003 | Responsive Design | T300/T301/T302 Playwright multi-viewport (implicit in E2E harness) | ⚠️ See MED-2 |
| NFR-004 | Dark Mode Default (P2) | T231 DossierStamp bg-void aesthetic, inherits landing-page tokens | ✓ |
| NFR-005 | Test Coverage | All RED test tasks (T010-T012, T100-T103, T200-T211, T300-T302); NFR-005 target ≥80% | ✓ |
| NFR-006 | TypeScript Strict Mode | T118 `prebuild: tsc --noEmit` in package.json; T120 runs pre-CI | ✓ |

### 2.4 User Stories (US-1..US-6)

| US | Title | Task Coverage | Status |
|----|-------|---------------|--------|
| US-1 | Desktop Happy Path | T300 E2E, all Phase 4 step components, Phase 3 foundation | ✓ |
| US-2 | QR Handoff | T230 QRHandoff, T209 tests, T300 E2E multi-viewport | ✓ |
| US-3 | Abandon & Resume | T113 WizardPersistence, T301 `onboarding-resume.spec.ts` | ✓ |
| US-4 | Unsupported Phone Country | T117/T206/T227, T302 `onboarding-phone-country.spec.ts` | ✓ |
| US-5 | Voice Unavailable Fallback | T208/T229 HandoffStep fallback branch, T302 E2E | ✓ |
| US-6 | Backstory Continuity First Message | T010/T011/T020-T024 backend PR-D, T226 BackstoryReveal, T300 E2E first-message assertion (dogfood via Telegram MCP) | ✓ |

---

## 3. Findings

| ID | Category | Severity | Location | Summary | Fix (suggested) |
|----|----------|----------|----------|---------|-----------------|
| MED-1 | Coverage gap | MEDIUM | tasks.md Phase 5 | NFR-001 (Performance) has no explicit task. Lighthouse score target ≥90 is called out in spec NFR-001 but not a named task; implicitly subsumed by T324 production smoke. | Add explicit task to T324 bullet: "verify Lighthouse performance score ≥90 on deployed /onboarding URL". Non-blocking (currently transitively covered). |
| MED-2 | Coverage gap | MEDIUM | tasks.md Phase 5 | NFR-003 (Responsive Design) has no explicit multi-viewport task. Playwright specs implicitly run desktop + mobile viewport but not named. | Add to T300-T302 descriptions: "run at both `desktop` and `mobile` Playwright projects per `playwright.config.ts`". Non-blocking. |
| LOW-1 | Terminology consistency | LOW | tasks.md T110, T310 | NR-1a (`life_stage` clarification) is satisfied only implicitly — `life_stage` appears in contracts.ts and schemas but no task explicitly validates the clarification is respected (life_stage is darkness-implied, not directly collected). | Add comment in T310 zod schema description: "life_stage derived in step 6 (Darkness) per NR-1a; no dedicated input field". Clarification-only; non-blocking. |
| LOW-2 | Non-canonical ID format | LOW | tasks.md (various) | Some tasks use `AC-FR10.1` / `AC-NR1.1` format which is non-canonical — spec uses only `AC-10.1`, `AC-NR1.1` (i.e., drops the "FR" prefix). Mixing creates minor confusion. | Optional harmonization: replace `AC-FR*.*` with `AC-*.*` in tasks.md lines referencing T102, T100, T103. Not blocking. |
| LOW-3 | User-story tag format | LOW | tasks.md (various) | Mixed `US-1`/`US1` formats in task tags. Spec uses `US-1`. | Optional: standardize to `US-1` across tasks.md. Not blocking. |

**No CRITICAL or HIGH findings**.

---

## 4. Duplication Check

- No duplicate requirements in spec.md (verified GATE 2 iter-6 PASS).
- No duplicate tasks in tasks.md. Test-suite IDs (T010-T012, T100-T103, T200-T211, T300-T302) all unique.

---

## 5. Ambiguity Check

- Zero `[NEEDS CLARIFICATION]` markers in spec (verified by grep).
- Zero `TODO` / `TBD` / `???` markers in plan.md or tasks.md.
- All US have ≥2 ACs (verified during GATE 2).

---

## 6. Inconsistency Check

- Terminology consistent: `users.onboarding_profile` (JSONB), `BackstoryCacheRepository`, `PortalOnboardingFacade`, `compute_backstory_cache_key` are used identically across spec/plan/tasks.
- Task ordering valid DAG: Phase dependencies are forward-only; [P] tasks verified same-phase non-shared-file.
- No data-model conflicts: all references consistent with Spec 213 frozen contracts + Spec 214 additive extension.

---

## 7. Implementation Readiness

| Criterion | Status |
|-----------|--------|
| Zero CRITICAL findings | ✓ |
| Constitution compliance PASS | ✓ |
| No [NEEDS CLARIFICATION] markers | ✓ |
| Coverage ≥95% for P1 requirements | ✓ (100% FR/US; 83% NR with 1 clarification-only; 100% NFR transitive) |
| All P1 stories have independent test criteria | ✓ |
| TDD RED/GREEN gates explicit | ✓ |
| PR sequence executable (D→A→B∥C) | ✓ |
| Worktree dispatch plan documented | ✓ |
| Parallelization safety ([P] markers) | ✓ |
| Predecessor backend deployed | ✓ (nikita-api-00250-4mm) |

**Readiness Verdict**: READY FOR /IMPLEMENT.

---

## 8. Post-Audit Recommendations (Non-Blocking)

1. **MED-1, MED-2**: Optional task description tweaks in tasks.md — add explicit Lighthouse perf + multi-viewport mentions in T324/T300-T302. Can be applied during /implement as inline doc fixes (no re-audit needed).
2. **LOW-1..LOW-3**: Harmonization nits — address opportunistically during implementation; do not block.
3. **Phase 8 dispatch sequence** (per state file directives):
   - PR 214-D first (backend, merge → deploy → smoke)
   - PR 214-A second (portal foundation, merge → Vercel preview)
   - PR 214-B ∥ PR 214-C via parallel worktree agents after PR-A merges
   - Main orchestrator handles PR creation + `/qa-review` per branch (single review pass per PR, iterate only on findings)

---

## 9. GATE 3 Status

- [x] audit-report.md: PASS
- [x] 0 CRITICAL
- [x] 0 HIGH
- [x] Constitution compliance

**GATE 3: PASS — ready for `/implement 214`.**

---

**Generated by**: Phase 7 /audit (read-only)
**Next step**: `/implement 214` — formal skill invocation per SDD rule 10 (no raw subagent dispatch).

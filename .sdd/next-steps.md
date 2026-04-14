# Next Steps

**Feature:** 213-onboarding-backend-foundation
**After Phase:** 7 (Audit PASS)
**Status:** audit-report.md PASS; GATE 3 cleared; ready for /implement 213
**Generated:** 2026-04-14T19:50Z

## Immediate Next

Phase 8 (Implementation): Invoke `/implement 213` formal skill — TDD RED-GREEN-REFACTOR per user story.

## Context Summary

- spec.md: 1058 lines, 14 FRs + 2 amendments (FR-2a, FR-4a), 7 USs, 30 ACs
- plan.md: 292 lines, 5-PR decomposition
- tasks.md: 513 lines, 51 tasks (audit added T1.8, T1.9, T2.6, TB.3)
- audit-report.md: 11/11 articles PASS, 100% FR coverage (21/21), 100% AC coverage (30/30), 0 residuals
- GATE 1: PASS | GATE 2: PASS (10 iterations) | GATE 3: PASS

## Key Files Ready

- specs/213-onboarding-backend-foundation/spec.md
- specs/213-onboarding-backend-foundation/plan.md
- specs/213-onboarding-backend-foundation/tasks.md
- specs/213-onboarding-backend-foundation/audit-report.md
- specs/213-onboarding-backend-foundation/validation-findings.md
- .claude/plans/onboarding-overhaul-brief.md
- docs/diagrams/onboarding-journey-target.md

## Phase 8 Plan

1. `/implement 213` — formal skill invocation (SDD rule 10: NOT raw subagent dispatch)
2. Execute PR 213-1: contracts.py + tuning.py + adapters.py + tests
3. `gh pr create` → `/qa-review --pr N` loop → absolute-zero → squash merge → post-merge smoke (auto-dispatched subagent)
4. **After PR 213-1 merges, Spec 214 can start in parallel** (`/feature 214`)
5. Execute PR 213-2, 213-3, 213-4, 213-5 sequentially, same QA gate per PR

## Resume Command

/sdd implement 213

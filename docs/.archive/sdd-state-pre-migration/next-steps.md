# Next Steps

**Feature:** 214-portal-onboarding-wizard
**After Phase:** 5 (Planning COMPLETE)
**Status:** plan.md ready; GATE 2 PASS; ready for /tasks 214
**Generated:** 2026-04-15

## Immediate Next

Phase 6 (/tasks 214): Expand plan.md's US/task matrix into `specs/214-portal-onboarding-wizard/tasks.md` with file-level touch map, RED/GREEN commit boundaries, and [P] markers at the file-test-pair level for parallel worktree dispatch.

## Context Summary

- spec.md: 1013 lines, 10 FRs + 5 NRs + 6 USs + 6 NFRs + FR-10 backend sub-amendment
- plan.md: architecture diagrams + 4-PR decomposition (D→A→B→C) + US/task matrix + risk register + testing strategy
- GATE 1: PASS | Phase 4.5: PASS | GATE 2: PASS (6 iter, absolute zero)
- research.md / data-model.md skipped — rationale in plan §9 (no external research beyond Appendix B canonical mapping; no new tables)

## Phase 8 PR Sequence (from plan §4)

| PR | Scope | Order |
|----|-------|-------|
| 214-D | Backend sub-amendment (`PUT /profile/chosen-option` + `wizard_step`) | First — TS contracts mirror merged source |
| 214-A | Portal foundation (types, hooks, state machine, persistence) | Second — no UI, plumbing only |
| 214-B | 9 step components + DossierStamp + QRHandoff | Parallel worktree w/ C |
| 214-C | E2E + schemas + middleware + Vercel deploy | Parallel worktree w/ B |

## Key Files Ready

- specs/214-portal-onboarding-wizard/spec.md
- specs/214-portal-onboarding-wizard/plan.md
- specs/214-portal-onboarding-wizard/validation-reports/ (6 PASS reports)
- .sdd/sdd-state.md (Phase 5 marked complete)

## Resume Command

/tasks 214

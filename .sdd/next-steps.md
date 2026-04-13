# Next Steps

**Feature:** 210-kill-skip-variable-response
**After Phase:** 3 (Specification)
**Status:** Awaiting user review (Phase 4.5)
**Generated:** 2026-04-12

## Immediate Next

**Phase 4.5 — Spec Review** (mandatory user walkthrough):
- User reads `specs/210-kill-skip-variable-response/spec.md` (349 lines)
- User confirms: problem framing, scope, user stories, acceptance criteria, out-of-scope list
- User either (a) approves → proceed to GATE 2, or (b) requests edits → revise spec, re-loop review

## Resume Commands

After user approval:
- `/sdd validate` to trigger GATE 2 (6 parallel validator agents)
- Or directly invoke the 6 `sdd-*-validator` Task calls per SDD skill GATE 2 section

## Planned Chain After Approval

1. Phase 4.5 (Spec Review) → user approves
2. GATE 2 (6 validators in parallel): frontend, data-layer, auth, api, testing, architecture
   - Expectation: frontend, data-layer, auth, api return N/A or PASS (backend-only, no schema)
   - testing, architecture: PRIMARY scope — must return PASS with 0 CRITICAL/HIGH
3. Analyze-Fix Loop if CRITICAL/HIGH found
4. Phase 5 (Plan) — implementation plan
5. Phase 6 (Tasks) — task breakdown with TDD ordering
6. Phase 7 (Audit) — final quality check before code
7. User approval → Phase 8 (Implement) with PR

## Notes

- 6 validators exist in `.claude/agents/`. Brief's "only 5 exist" claim was wrong — `sdd-api-validator` IS present. All 6 will run in parallel at GATE 2.
- Brief already captured verification strategy → Phase 5 plan should reference brief rather than re-deriving.
- Supersedes prior session on Spec 081 — that feature was completed 2026-03-23.

## Critical Files for Phase 4.5 User Review

- `specs/210-kill-skip-variable-response/spec.md` — spec under review (349 lines)
- `~/.claude/plans/delightful-orbiting-ladybug.md` — source planning brief (for comparison)
- `specs/026-text-behavioral-patterns/spec.md` — soon-to-be partially superseded

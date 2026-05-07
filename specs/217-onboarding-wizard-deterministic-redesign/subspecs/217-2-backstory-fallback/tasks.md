# Tasks — Subspec 217-2 Backstory Fallback

**Parent**: `subspecs/217-2-backstory-fallback/{spec,plan}.md`
**Phase**: 6
**Date**: 2026-05-07

## Tasks

- [ ] T-2-1: `git checkout -b fix/217-2-backstory-fallback` from master HEAD (post-217-1 merge).
- [ ] T-2-2 (TEST-RED, AC-T.1): Write `portal/src/app/onboarding/_components/__tests__/WizardShell.archetype-fallback.test.tsx`. Three test cases: (a) Alert renders when `archetype_cards === null` after 3-5s; (b) retry click triggers `useOnboardingAPI` POST with correct payload; (c) success path advances to `<BackstoryArchetypeCards>`. Run; ALL FAIL (no fallback yet).
- [ ] T-2-3 (TEST-RED, AC-T.2): Write `tests/api/routes/test_portal_onboarding_archetype_timeout.py`. Mock `pick_three_archetypes` to `await asyncio.sleep(25)`; assert route response includes `default_archetype_cards` content; assert `logger.warning` called with `backstory_pipeline_timeout`. Run; FAIL.
- [ ] T-2-4 (IMPL-GREEN, AC-4a.x): Edit `portal/src/app/onboarding/_components/WizardShell.tsx:771-776` per plan.md (Option A primary + Option B safety-net). Implement `<ArchetypeFallback>` if Option B chosen. Run T-2-2; PASS.
- [ ] T-2-5 (IMPL-GREEN, AC-4b.x): Edit `nikita/api/routes/portal_onboarding.py:1367` — wrap `pick_three_archetypes` in `asyncio.wait_for(timeout=20.0)`; add `backstory_pipeline_timeout` log. Run T-2-3; PASS.
- [ ] T-2-6 (REGRESSION): Re-run full portal vitest + nikita pytest suites — all green.
- [ ] T-2-7 (PRE-PUSH HARD GATE): `(cd portal && npm run test -- --run && npm run lint && npm run build)` + `uv run pytest -q`. Record in PR body.
- [ ] T-2-8: `git push -u origin fix/217-2-backstory-fallback`.
- [ ] T-2-9: `gh pr create --title "fix(217,2): backstory archetype fallback (FE guard + BE wait_for)" --body "..."`. PR body cites spike root cause C5 + 216-audit F-2 overlap.
- [ ] T-2-10: `/qa-review --pr <N>` zero-tolerance fresh-context loop.
- [ ] T-2-11: Squash merge after CI green + 0-finding fresh review.
- [ ] T-2-12 (LIVE WALK B2, AC-W.1+2): Per `live-testing-protocol.md` 12-step protocol from `simon.yang.ch+walkB2@gmail.com`. Drive 11 turns until `next_slot_kind=backstory_pick`. Capture `output.archetype_cards` via Chrome MCP DevTools network tab. Apply spike falsifier per AC-W.2. Anti-fabrication discipline mandatory. DB cleanup SQL per protocol template.
- [ ] T-2-13: Commit-hash verification per `pr-workflow.md` step 9.

## Done Criteria

All 11 ACs from spec.md (excluding deferred AC-4c.1) satisfied; PR merged; Walk B2 PASS with hang resolved.

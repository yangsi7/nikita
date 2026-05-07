# Tasks — Subspec 217-3A BE Emission Union

**Parent**: `subspecs/217-3A-be-emission-union/{spec,plan}.md`
**Phase**: 6
**Date**: 2026-05-07

## TDD Ordering

Strict RED-GREEN-REFACTOR per CLAUDE.md SDD Enforcement #4. Two commits minimum per user story (test commit + impl commit).

## Tasks

- [ ] T-3A-1: `git checkout -b feat/217-3A-be-emission-union` from master HEAD (post-217-2 merge).
- [ ] T-3A-2 (TEST-RED, AC-7.4): Write `tests/agents/onboarding/fixtures/similarity_calibration.py` — 5 near-duplicate pairs + 5 distinct pairs. Add `test_similarity_calibration.py` asserting all 5 near-duplicates score >0.85, all 5 distincts score <0.85 with `difflib.SequenceMatcher`. Run; FAIL (no impl yet).
- [ ] T-3A-3 (TEST-RED, AC-5.x + 6.x): Write `tests/agents/onboarding/test_emission_union.py` covering output_type discriminated union + isinstance branching + dynamic instructions invocation per AC-5.1..5.3 + AC-6.1..6.2. Run; FAIL.
- [ ] T-3A-4 (TEST-RED, AC-7.x): Write `tests/agents/onboarding/test_output_validator_mirrors.py` covering mirror-of-next + mirror-echo + `ModelRetry` paths. Run; FAIL.
- [ ] T-3A-5 (TEST-RED, AC-8.x + AC-T-1): Write `tests/agents/onboarding/test_emission_state_sidecar.py` covering sidecar persistence at `onboarding_profile.pending_followup` + cumulative-monotonicity invariant. Run; FAIL.
- [ ] T-3A-6 (TEST-RED, AC-9.x): Write `tests/api/routes/test_emission_dispatch.py` covering 4 dispatch branches (reaction / followup / turn_failure / deterministic). Run; FAIL.
- [ ] T-3A-7 (TEST-RED, AC-10a.x): Write `tests/api/routes/test_identity_pair.py` covering full-valid + 3 partial-valid cases. Run; FAIL.
- [ ] T-3A-8 (TEST-RED, AC-T-2..5): Write `tests/agents/onboarding/test_agentic_flow_217.py` per `testing.md` Agentic-Flow Test Requirements (3 mandatory classes + agent.run contract + dynamic instructions). Run; FAIL.
- [ ] T-3A-9 (IMPL-GREEN, FR-5): Edit `nikita/agents/onboarding/converse_contracts.py` — add `ReactionOnly`, `FollowUpQuestion`, refactor `TurnFailure`.
- [ ] T-3A-10 (IMPL-GREEN, FR-5+6): Edit `nikita/agents/onboarding/conversation_agent.py:266` — wire new `output_type=[ToolOutput(...), ...]` + `instructions=build_instructions` callable.
- [ ] T-3A-11 (IMPL-GREEN, FR-6): Edit `nikita/agents/onboarding/prompts.py` — implement `build_instructions(ctx)` callable injecting next-Q + missing + decision rule.
- [ ] T-3A-12 (IMPL-GREEN, FR-7): Edit `nikita/agents/onboarding/validators.py` — implement `mirror_of_next_validator` + mirror-echo validator with `difflib.SequenceMatcher >0.85` + `ModelRetry`.
- [ ] T-3A-13 (PRE-FLIGHT, AC-V.3): Run `git diff --stat origin/master...HEAD`. If production diff > 350 LOC, STOP — split FR-7 + FR-8 into 217-3A.1 PR; rebase remaining tasks onto 217-3A.1 merge.
- [ ] T-3A-14 (IMPL-GREEN, FR-8): Create `nikita/agents/onboarding/agent_emission_state.py`. Update user repo to read/write `onboarding_profile.pending_followup`.
- [ ] T-3A-15 (IMPL-GREEN, FR-9): Edit `nikita/api/routes/portal_onboarding.py /answer` — add isinstance dispatch for ReactionOnly / FollowUpQuestion / TurnFailure / deterministic + sidecar set/clear.
- [ ] T-3A-16 (IMPL-GREEN, FR-10a): Edit `/answer` request schema + handler to accept `{slot:"identity_pair", value:{name,age}}`; partial-validation per AC-10a.2.
- [ ] T-3A-17 (REGRESSION): Run all the failing tests from T-3A-2..8 — must now PASS.
- [ ] T-3A-18 (PRE-PUSH HARD GATE): `uv run pytest -q` + `(cd portal && npm run test -- --run && npm run lint && npm run build)` (portal touched only by contract docs; build still required per `pr-workflow.md`).
- [ ] T-3A-19: `git push -u origin feat/217-3A-be-emission-union`.
- [ ] T-3A-20: `gh pr create --title "feat(217,3A): BE emission union — ReactionOnly|FollowUpQuestion|TurnFailure" --body "..."`. PR body cites:
   - Spec 217 master + 217-3A subspec
   - Phase-2 Pydantic AI primary-source verification (rejects Gemini false-positive on `ToolOutput` syntax)
   - LOC pre-flight result
   - 6-rule compliance table
- [ ] T-3A-21: `/qa-review --pr <N>` zero-tolerance fresh-context loop.
- [ ] T-3A-22: Squash merge after CI green + 0-finding fresh review.
- [ ] T-3A-23: Commit-hash verification per `pr-workflow.md` step 9.

## Done Criteria

All 22 ACs satisfied; PR merged; LOC ≤350 (or 217-3A.1 split landed first).

# Post-Compaction Handoff — 2026-04-14T19:00Z

## What Just Happened

**1. Production recovery (done, deployed):**
- PR #277 merged — cherry-picked PR #273 (`350a717`) that was force-push-wiped from master during Spec 212 cleanup. 4 structural onboarding bugs restored: pipeline bootstrap seed, profile JSONB persistence, conversation continuity (R8), voice-path pipeline gap. All 337 `tests/onboarding/` pass.
- PR #278 merged — hygiene (ROADMAP sync tests 5933→5934, last_deploy 2026-04-13, Cloud Run `nikita-api-00249-mdv`; archive Spec 081 to `specs/archive/`; register Spec 210 MERGED, Specs 212 COMPLETE, 213/214 PLANNED).
- 8 stale PRs closed (#261, #249, #185, #212, #210, #206, #205, #186).
- 6 orphaned worktrees pruned.

**2. Spec 213 SDD GATE 2 PASS (10 iterations total, absolute zero):**
- **Spec**: `specs/213-onboarding-backend-foundation/spec.md` (~1050 lines, 14 FRs + 2 iter-6 amendments, 7 user stories, 30 ACs with test-file names)
- **Journey**: iter-1 60 findings → iter-2 14 → iter-3 4 → iter-4 1 → iter-5 CLEAN (first convergence) → UX review triggered amendments → iter-6 14 new findings → iter-7 7 → iter-8 3 → iter-9 2 → **iter-10 CLEAN (final)**
- All 6 validators PASS at absolute zero: frontend, auth, data-layer, testing, architecture, API
- **Amendments from UX review** (FR-2a + FR-4a): `/pipeline-ready` exposes `venue_research_status` + `backstory_available`; NEW `POST /onboarding/preview-backstory` endpoint for backstory reveal BEFORE phone ask (emotional climax → commitment order).

**3. UX iteration completed (post GATE-2 iter-5, pre iter-6):**
- Dispatched: `pr-codebase-intel`, `tree-of-thought-agent` (current diagram), UX expert (research + 3 approaches), `pr-approach-evaluator` (panel 2-1 vote), `tree-of-thought-agent` (target diagram).
- **Approach selected**: Approach B "The Dossier Form" (reuses existing FormProvider shell, adds classified-file metaphor + Nikita-voiced copy + real 50/50 scores + backstory-before-phone reorder).
- 5 new requirements added to Spec 214 brief: NR-1 wizard state persistence, NR-3 phone country pre-flight, NR-4 QRHandoff, NR-5 voice fallback polling, dossier styling system.

**4. Diagrams written**:
- `docs/diagrams/onboarding-journey-current.md` (~1050 lines) — current state with all forks + smells
- `docs/diagrams/onboarding-journey-target.md` (~1050 lines) — Approach B Dossier Form target state with NR mappings

## Current State (verify before acting)

```bash
git log origin/master --oneline | head -5   # should show PRs #277 + #278 merged
git status --short                          # expected untracked plan/diagram files only
gcloud run revisions list --service=nikita-api --region=us-central1 --project=gcp-transcribe-test --limit=1
# expected: nikita-api-00249-mdv (last deploy 2026-04-13 Spec 212; no Spec 213 deploy yet)
```

## Where We Are in SDD Flow

Spec 213 passed **GATE 2 (Validation)** — absolute zero across all 6 validators.

**Next phase: Phase 4.5 — User spec walkthrough + approval**.

Per CLAUDE.md SDD rule 7 + `.claude/skills/sdd/phases/04.5-spec-review.md`: user reviews spec.md end-to-end and approves before chaining to `/plan 213`. No tool action required until user approves (or requests changes).

**After user approves**:
1. `/plan 213` → Phase 5 → plan.md with 5-PR decomposition (PR 213-1 through 213-5, each ≤400 LOC)
2. `/tasks 213` → Phase 6 → TDD task pairs
3. `/audit 213` → Phase 7 → final audit (must PASS before Phase 8)
4. `/implement 213` → Phase 8 — **formal skill invocation, NOT raw subagent dispatch** per SDD rule 10
5. Each PR through `/qa-review` → absolute-zero across all severities (incl nitpicks) → squash merge
6. Parallel: `/feature 214` can start once PR 213-1 (contracts.py) lands — Spec 214 imports frozen contracts

## Spec 213 PR Decomposition (to be written during /plan 213)

| PR | Scope | Depends On |
|---|---|---|
| **213-1** | `contracts.py` + `tuning.py` + `adapters.py` + tests (FROZEN contract — unblocks Spec 214) | — |
| **213-2** | Migration (user_profiles columns + backstory_cache + RLS hardening) + ORM + repository | 213-1 |
| **213-3** | Facade `portal_onboarding.py` + preview endpoint + pre-existing PII fixes at `onboarding.py:154,239` | 213-1, 213-2 |
| **213-4** | Route file `portal_onboarding.py` + `/pipeline-ready` + `PATCH /profile` + FR-14 session pattern | 213-1, 213-3 |
| **213-5** | FirstMessageGenerator FR-6 + R8 regression test + e2e + ROADMAP sync to COMPLETE | 213-1..4 |

## Pending Tasks (from task tracker)

- #40 Run `/plan 213` → `/tasks 213` → `/audit 213` (pending user approval of spec.md)
- #41 Invoke `/implement 213` (formal skill, per SDD rule 10)
- #42 E2E verification + deploy post-merge

## Critical Context for Continuation

### What the user cares about
- User originally rated onboarding "5 → 1". Core complaints: Nikita forgets first message, generic opener, pipeline never runs, sterile form-fill UX, phone-before-backstory is backwards.
- User policy: **ABSOLUTE ZERO** across all severities (CRITICAL + HIGH + MEDIUM + LOW) on SDD validators AND `/qa-review`. Nitpicks count.
- User authorized >3 SDD iterations (we used 10 on Spec 213). Convergence clearly >3-iter requirement in CLAUDE.md is obsolete.
- User wants dossier metaphor + Nikita-voiced copy + real scores (not fake 75/100 demo) + backstory BEFORE phone.

### What NOT to do
- Don't skip `/implement` skill — SDD rule 10 mandates formal invocation (documented feedback memory).
- Don't merge any PR with open findings (nitpicks count — memory feedback).
- Don't commit directly to master — PR + `/qa-review` mandatory (pr-workflow.md).
- Don't touch out-of-scope Spec 081 (archived). Don't revert the PR #273 cherry-pick (PR #277 is the authoritative recovery).

### Architecture insights (hard-won over 10 iterations)
- `UserOnboardingProfile` (Pydantic, JSONB) ≠ `UserProfile` (SQLAlchemy ORM) — they have DIFFERENT field names. `BackstoryGeneratorService` reads `.city` + `.primary_passion` (NOT `location_city`/`primary_interest`) via duck-typing. Adapter `ProfileFromOnboardingProfile` returns `BackstoryPromptProfile` dataclass with the generator's attribute names.
- `users.onboarding_completed_at` column DOES NOT EXIST — FR-9 uses existing `onboarding_status` field.
- `cast(value, JSONB)` is INVALID for string values — must use `cast(json.dumps(value), JSONB)` (PostgreSQL rejects bare `'pending'`).
- `DatabaseRateLimiter._get_minute_window()` has NO user_id param (not `_minute_window_key(user_id)`) — `_PreviewRateLimiter` subclass must override the correct method.
- `BackstoryCacheRepository` returns raw `list[dict]` envelope `{scenarios, venues_used}`, NOT domain types. Facade deserializes.
- `name` in `users.onboarding_profile` JSONB is the canonical key (NOT `user_name` — legacy read sites at `onboarding.py:458-460, 556-557` need update with one-cycle fallback).

### Convergent findings (shouldn't regress)
These issues were flagged by multiple validators in iter-1, all resolved:
- `pipeline_state` JSONB write contract (API + Auth + Data-layer + Architecture all flagged)
- 403 body shape (Frontend + API + Auth)
- Pydantic↔ORM adapter (API + Architecture)
- Contract type definitions (Frontend + API)

## Reference Files (all current)

### Spec 213 artifacts
- `specs/213-onboarding-backend-foundation/spec.md` — spec (13 FRs + 2 amendments, 7 stories, 30 ACs, 17 test files named)
- `specs/213-onboarding-backend-foundation/validation-findings.md` — findings manifest (all iters, final = 0/0/0/0)
- `specs/213-onboarding-backend-foundation/validation-reports/{frontend,auth,data-layer,api,testing,architecture}.md` — 6 validator reports per iteration

### Plan + brief
- `.claude/plans/onboarding-overhaul-brief.md` — planning brief (dossier 11-step journey + 5 NRs + Nikita-voice copy guidelines + pre-214 standalone fixes)
- `~/.claude/plans/quirky-floating-liskov.md` — top-level plan (WS-1 complete, WS-2 in progress, WS-3 planned, 10-iter GATE 2 record)

### UX iteration
- `docs/diagrams/onboarding-journey-current.md` — current state with smells
- `docs/diagrams/onboarding-journey-target.md` — Approach B target state

### Other
- `ROADMAP.md` — Domain 4 registered Specs 213 + 214; tests 5934; Cloud Run 00249-mdv
- `.claude/rules/testing.md` / `tuning-constants.md` / `pr-workflow.md` / `stochastic-models.md` / `review-findings.md` — all referenced in spec

## Lessons Logged (permanent)

- **Passing 6 SDD validators doesn't mean the UX is right** — iter-5 was CLEAN but UX review surfaced 19 additional smells (4 blockers) that code-level validators can't see.
- **Drawing the end-to-end user journey surfaces logical forks feature-specs miss** — e.g., desktop-to-mobile handoff, voice-agent-down fallback, phone-unsupported-country, wizard abandonment, re-onboarding inconsistency.
- **Multi-validator GATE 2 catches 5-10× more than self-review** — 60 findings vs ~10 estimated.
- **Spec rewrites introduce NEW findings** — iter-2 added 12, iter-6 added 14. Budget ≥3 iterations; real-world reached 10.
- **Convergent findings (flagged by N validators) are must-fix signals**.
- **Force-push recovery can silently wipe merged PRs** — always verify `gh pr view N --json mergeCommit` + `git branch --contains <commit>` before assuming state.

## How to Resume in a Fresh Session

1. Read this file first.
2. Read `specs/213-onboarding-backend-foundation/spec.md` (the spec awaiting user approval).
3. Run the Current-State verification block at the top.
4. Ask user: "Spec 213 passed GATE 2 (absolute zero across 10 iterations). Ready to approve for `/plan 213`?"
5. On approval → `/plan 213` → `/tasks 213` → `/audit 213` → `/implement 213` (formal skill).
6. Parallel `/feature 214` can start after PR 213-1 (contracts.py) merges — Spec 214 consumes frozen contracts + the 5 NRs + dossier journey diagram.
7. Per SDD rule 10: never dispatch implementor subagents directly — always `/implement` skill.
8. Every PR: `/qa-review --pr N` to absolute zero across all severities before merge.
9. Post-merge per rule: auto-dispatch smoke test via fresh subagent.

## Quick Sanity Checks Before First Write

- `ls specs/213-onboarding-backend-foundation/spec.md` — should exist
- `grep -c "CLEAN" specs/213-onboarding-backend-foundation/validation-reports/*.md` — should show clean markers per iter
- `git log -5 --oneline` — expect recent commits = PR #277 + #278 (no Spec 213 impl yet)
- `gh pr list --state open --limit 5` — expect PR #276 active (portal-systems-tour, unrelated), no onboarding PRs

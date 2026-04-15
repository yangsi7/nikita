# Post-Compaction Handoff — 2026-04-15

## TL;DR

Spec 213 (onboarding backend foundation) **fully merged on master**. Next: deploy to Cloud Run + smoke (#54), then Spec 214 portal wizard SDD cycle (#55).

## Where we are

```
master tip:
  be546b3 feat(onboarding): Spec 213 PR 213-5 — FR-6 first message + R8 continuity + ROADMAP COMPLETE (#286)
  a602f41 feat(onboarding): Spec 213 PR 213-4 — routes + pipeline-ready + FR-14 session isolation (#285)
  48b30da feat(onboarding): Spec 213 PR 213-3 — facade + preview endpoint + PII fixes (#283)
  dc6ebee feat(db): Spec 213 PR 213-2 — migration + ORM + BackstoryCacheRepository (#282)
  512ce34 feat(onboarding): Spec 213 PR 213-1 — frozen contract surface (#279)
```

ROADMAP.md: Spec 213 row = `COMPLETE (PR 213-5, 2026-04-15)`; `specs_complete: 87`; `In-flight: none`. Last deploy date in ROADMAP needs bumping after Cloud Run deploy.

Test count post-merge: **6153 unit tests pass**, 0 failures, 79 deselected (integration/e2e).

## Pending tasks (in priority order)

| # | Task | Notes |
|---|---|---|
| 54 | Deploy Spec 213 backend to Cloud Run + e2e smoke | First user-testable personalized onboarding |
| 55 | Spec 214 portal wizard — full SDD cycle | Consumes contracts from PR 213-1 |
| 42 | E2E verification + deploy | Run after Spec 214 lands |
| 60 | Clean up oversized memory files (memory-system-architecture.md 93KB) | Verify staleness before moving |

## Task #54 — Deploy + smoke

```bash
gcloud run deploy nikita-api --source . --region us-central1 \
  --project gcp-transcribe-test --allow-unauthenticated
```

Then smoke-test the new Spec 213 endpoints (auto-dispatch a fresh subagent — do NOT ask permission per `.claude/CLAUDE.md` orchestration rules):
- `GET /api/v1/onboarding/pipeline-ready/{user_id}` returns 4-state response
- `POST /api/v1/onboarding/preview-backstory` returns scenarios
- `PATCH /api/v1/onboarding/profile` jsonb_set merge
- Verify `_trigger_portal_handoff` background task writes `pipeline_state` transitions

After successful deploy: bump `last_deploy` in `ROADMAP.md` frontmatter to current date + new Cloud Run revision name.

## Task #55 — Spec 214 portal wizard

Brief at `.claude/plans/onboarding-overhaul-brief.md` (also referenced from `.claude/plans/quirky-floating-liskov.md`). Key points carried forward from Spec 213 UX iteration (2026-04-14):

- **Approach**: "The Dossier Form" (panel 2-1 vote). Reuses existing FormProvider/zodResolver, adds dossier metaphor + Nikita-voiced copy + 11-step flow.
- **Wizard reorder**: backstory reveal (Step 8) BEFORE phone ask (Step 9). Backstory is emotional climax that justifies phone commitment.
- **5 amendments** added to brief (NR-1..5):
  - NR-1: localStorage + JSONB wizard state persistence
  - NR-3: phone country pre-flight validation
  - NR-4: QRHandoff component for desktop→mobile
  - NR-5: voice fallback polling UI
  - Dossier styling system + Nikita-voiced copy
- **Frozen contracts** (already shipped): consume `OnboardingV2ProfileRequest`, `OnboardingV2ProfileResponse`, `BackstoryOption`, `BackstoryPreviewRequest/Response`, `PipelineReadyResponse` from `nikita/onboarding/contracts.py`.

Workflow:
1. `/roadmap add 214 portal-onboarding-wizard` (if not already registered — check ROADMAP.md first)
2. `/feature 214` (Phase 3) → spec.md
3. Phase 4 clarify if needed
4. Phase 4.5 spec walkthrough + user approval (mandatory before GATE 2)
5. GATE 2: spawn 6 validators in parallel via Task tool (sdd-frontend-validator, sdd-data-layer-validator, sdd-auth-validator, sdd-api-validator, sdd-testing-validator, sdd-architecture-validator)
6. `/plan 214` → plan.md (decompose into ≤400-LOC PRs)
7. `/tasks 214` → tasks.md
8. `/audit 214` → audit-report.md (must PASS)
9. `/implement 214` (formal skill, NOT raw subagent dispatch — see SDD rule 10)
10. Per-PR: implementor (worktree) → grep-verify → push → `/qa-review` loop → merge → post-merge smoke

## Critical workflow patterns (codified this session — DO NOT skip)

### 1. Orchestrator grep-verify gate (`.claude/rules/pr-workflow.md`)

After EVERY implementor dispatch, BEFORE sending to `/qa-review`:
```bash
grep -n "<claimed pattern>" <production file>
```
If grep doesn't confirm the implementor's claim → redispatch implementor with the contradiction. Hallucinated "fixes" survived 2 QA iters on PR #283 because tests with mocks lied.

After EVERY reviewer finding, BEFORE acting:
```bash
git fetch origin && git show origin/<branch>:<file> | grep "<flagged pattern>"
```
If grep doesn't confirm finding → phantom finding from stale checkout (happened on PR #283 iter-6 + PR #285 iter-4). Don't dispatch fix.

### 2. Commit-hash post-merge verification (step 8 in pr-workflow.md)

After every merge:
```bash
git log origin/master --oneline -3
```
PR's merge commit MUST be at top. Force-push wipes are silent (precedent: PR #273 was wiped during Spec 212 cleanup, recovered as #277).

### 3. Pre-PR grep gates (`.claude/rules/testing.md`)

Before opening PR, run on changed files:
- Zero-assertion shells: every `async def test_*` must assert
- PII leakage: no name/age/occupation/phone in log format strings
- Raw cache_key in logs: must use `cache_key_hash = hashlib.sha256(...)[:8]`

### 4. Tautological tests (caught on PR #286 iter-1)

A test that mocks the function under test and asserts the mock returns what it was told to return = no production coverage. Tests must exercise REAL production code (e.g., real `HistoryLoader._convert_to_model_messages`, mock only the LLM boundary `nikita_agent.run`).

### 5. Worktree → branch transfer

```bash
# In main tree:
git checkout -b feat/<name> master
git rebase worktree-agent-<id>
git push -u origin feat/<name>
```
Untracked files in main tree may conflict — `rm` them before rebase. The worktree submodule entry (`.claude/worktrees/agent-<id>`) gets included in the rebase commit — `.gitignore` now excludes `.claude/worktrees/` (added on PR #286 iter-2 fix).

### 6. QA review absolute-zero policy

Every PR must reach `0 blocking + 0 important + 0 nitpick` via FRESH-CONTEXT subagent review. Self-review doesn't count. Iterate up to ~8 rounds. Convergence trajectory of recent PRs:
- PR #283 (213-3): 7 iters
- PR #285 (213-4): 4 iters
- PR #286 (213-5): 4 iters

## Known gotchas

- **Pydantic AI agent**: `nikita_agent` is an `_AgentProxy()` instance at `nikita/agents/text/agent.py:283`, NOT a `NikitaAgent` class. Patch `nikita.agents.text.agent.nikita_agent.run` (instance attr).
- **`update_onboarding_profile_key`** internally wraps `json.dumps` — pass raw Python values (`"complete"`, not `'"complete"'`).
- **`async with session_maker() as session:` in SQLAlchemy 2.x** does NOT auto-commit — explicit `await session.commit()` required.
- **Implementor model**: dispatch with `model="sonnet"` to avoid usage limits on opus.
- **Spec 213 `_trigger_portal_handoff`**: signature is `(user_id: UUID, drug_tolerance: int)` only — opens fresh session inside via `get_session_maker()`. Do NOT pass session/repo (FR-14).

## Key file locations

- Spec: `specs/213-onboarding-backend-foundation/spec.md` (1058 lines)
- Plan: `specs/213-onboarding-backend-foundation/plan.md`
- Tasks: `specs/213-onboarding-backend-foundation/tasks.md`
- Spec 214 brief: `.claude/plans/onboarding-overhaul-brief.md`
- Quirky-floating-liskov plan: `.claude/plans/quirky-floating-liskov.md`
- Diagrams: `docs/diagrams/onboarding-journey-current.md`, `docs/diagrams/onboarding-journey-target.md`
- Production:
  - `nikita/onboarding/contracts.py` (frozen, Spec 214 consumer)
  - `nikita/onboarding/tuning.py` (constants — BACKSTORY_HOOK_PROBABILITY, PIPELINE_GATE_*)
  - `nikita/services/portal_onboarding.py` (PortalOnboardingFacade)
  - `nikita/api/routes/portal_onboarding.py` (3 routes)
  - `nikita/api/routes/onboarding.py` (legacy POST /profile + `_trigger_portal_handoff`)
  - `nikita/onboarding/handoff.py` (FirstMessageGenerator FR-6)

## Memory references

- `~/.claude/projects/-Users-yangsim-Nanoleq-sideProjects-nikita/memory/feedback_implementor_self_report_verification.md` — orchestrator grep-verify gate (extended this session)
- `~/.claude/projects/.../memory/feedback_qa_review_zero_tolerance.md` — fresh-context absolute-zero
- `~/.claude/projects/.../memory/project_status.md` — needs update to reflect Spec 213 COMPLETE

## First action when resuming

```
1. Read this brief (you are here)
2. git status && git log --oneline -3  → confirm be546b3 at top
3. Check task list — tasks #54, #55 pending
4. Ask user: "deploy 213 to Cloud Run (#54), or start Spec 214 SDD (#55)?"
5. If deploy: dispatch deploy via Bash + post-deploy smoke subagent
6. If Spec 214: invoke /sdd skill with intent "create spec 214 portal-onboarding-wizard"
```

---
title: Spec 217 onboarding wizard redesign — orchestration handover
lifecycle: living
date: 2026-05-08
session: post-Walk-A1 → 217-2c shipped → 217-3A.1 in-flight
type: handover
---

# Spec 217 Orchestration Handover (post-compact)

## Context one-liner

Spec 217 onboarding wizard deterministic-track redesign supersedes 216-B + 216-C. Original trigger: 5 catastrophic UX bugs from IMG_0431-0434 user dogfood (Telegram CTA missing /start prefill, intermediate "access portal" interstitial, "in development" loading flash, deterministic + agent overlay in same wizard card, backstory hang at "preparing the three of us..."). Plan-rewrite Tier-3 brief at `docs-to-process/20260507-spec217-onboarding-redesign-planning-brief.md`. Orchestration plan at `~/.claude/plans/immutable-wondering-gray.md`.

## Sub-PR Scoreboard

| Sub-PR | Code state | Live walk | User-bug-fixed | Master commit |
|---|---|---|---|---|
| 217-0 prereq cleanup | ✅ merged | n/a | (test plumbing) | `6b15668` |
| 217-1 cold-start CTA + interstitial + loading flash | ✅ merged | B1 PASS | bugs 1, 2, 3 ✅ | `9003a58` |
| 217-2 backstory FE fallback + BE asyncio.wait_for(20s) | ✅ merged | B2-resume PASS (FALLBACK path) | bug 5 partial (graceful UX yes; underlying gen no) | `2edc781` |
| 217-2c ModelHTTPError retry + structured logs | ✅ merged | B2-resume2 BLOCKED Telegram MCP expiry | (defensive layer added) | `72bd18f` |
| 217-3A.1 emission union prereqs (contracts + validators + sidecar + envelope) | ✅ merged 2026-05-08 03:30Z | n/a (BE contract only) | — | `a69db24` (PR #560) |
| 217-3A.2 agent + dispatch wiring | pending (blocks on 3A.1 merge ✓; ready to dispatch) | — | — | — |
| 217-3B FE wizard sibling-DOM refactor | pending (blocks on 3A.2 merge) | B3 pending | bug 4 (overlay) | — |
| Walk B4 final integration | pending | — | — | — |

Master HEAD: `a69db24 feat(217,3A.1): emission union prereqs (PR #560)`.

Cloud Run: `nikita-api-00301-5f8` (deployed 2026-05-08 ~01:00 UTC, contains 217-2 + 217-2c). 217-3A.1 is BE schema additions + validators only, NOT wired to any route — no deploy required until 217-3A.2 lands.

## Active Background Tasks

- None. All sub-PRs through 217-3A.1 are merged. Pytest 7002/7002 GREEN on master.

## 217-3A.1 Merge Summary (2026-05-08)

Original implementor `a4c20c4710b40de30` was killed by usage-limit at 00:30Z mid-flight. Recovery path:

1. Orchestrator branched `feat/217-3A.1-emission-prereqs` from partial work in main checkout (3 of 7 files committed as `ebfe099`).
2. 4 remaining files (agent_emission_state.py, api/schemas/onboarding.py, fixtures/similarity_calibration.py, test_emission_state_sidecar.py) found as untracked — implementor wrote them but never committed. Verified imports + 35 scoped tests GREEN, committed as `af5dc0e`.
3. Pre-PR full nikita pytest gate: 7002 passed, 0 failed in 24m34s.
4. PR #560 opened.
5. QA zero-tolerance loop: 6 fresh-context iters.
   - iter-1: 0/3/1 → flatten FollowUpResponse, min_length=1 on errors, docstring clarity, archetype_cards comment marker (commit `4bc0bd4`)
   - iter-2: 0/0/1 → pytest.skip instead of silent return (commit `c007e99`)
   - iter-3: 0/0/1 → drop unused parametrize case (commit `24c6436`)
   - iter-4: 0/0/1 → rename validator param to `candidate_text` for ReactionOnly + FollowUpQuestion call sites (commit `b4cdf07`)
   - iter-5: 0/0/1 → spec amendment AC-9.1bis (flattened envelope + min_length=1) to match code (commit `cb3acdd`)
   - iter-6 (test focus): 0/0/0 CLEAN ✅
6. CI: Pytest PASS, E2E PASS, Vercel PASS, "E2E Test Summary" FAIL (known infra GH #559, non-blocking).
7. Squash merged as `a69db24`.

Total: 7 commits squashed, 8 files +809/-1, 6 QA iterations, ~3h wall.

## 217-3A.1 Refined Scope (active dispatch)

7 files, ~210 prod LOC + ~130 tests:

| # | File | Action | AC |
|---|---|---|---|
| 1 | `nikita/agents/onboarding/converse_contracts.py` | EDIT add `ReactionOnly`, `FollowUpQuestion`, refactored `TurnFailure` | AC-5.1 |
| 2 | `nikita/agents/onboarding/validators.py` | EDIT add `validate_no_mirror_of_next`/`validate_no_mirror_echo` + `MIRROR_THRESHOLD: Final[float] = 0.85` | AC-7.1, 7.2 |
| 3 | `nikita/agents/onboarding/agent_emission_state.py` | NEW sidecar Pydantic v2 model for `users.onboarding_profile.pending_followup` JSONB | AC-8.1 |
| 4 | `nikita/api/schemas/onboarding.py` | NEW `AnswerResponse` discriminated-union envelope with 5 `kind` literals | AC-9.1bis |
| 5 | `tests/agents/onboarding/test_validators.py` | EXTEND mirror tests + threshold lock | AC-7.1/7.2 |
| 6 | `tests/agents/onboarding/fixtures/similarity_calibration.py` | NEW 10 hand-crafted pairs locking 0.85 | AC-7.4 |
| 7 | `tests/agents/onboarding/test_emission_state_sidecar.py` | NEW sidecar invariants | AC-8.1 |

Out of scope (defer to 217-3A.2): `conversation_agent.py`, `conversation_prompts.py`, `state.py`, `portal_onboarding.py`, `test_cumulative_state.py`, `test_completion_gate.py`, `test_tool_recovery.py` extensions, IdentityPair, per-emission-kind dispatch tests, JSONB cleanup test.

## 217-3A.2 Pending Scope (next dispatch after 3A.1 merge)

- `conversation_agent.py` — `output_type=[ToolOutput(...)*3]`, `@agent.instructions` decorator (NOT `Agent(instructions=callable)` ctor kwarg — pre-flight correction), `output_retries=2`, `@agent.output_validator`
- `conversation_prompts.py` (or `prompts.py`) — static base + decorator-injected dynamic
- `state.py` — `WizardSlots` cumulative + `FinalForm` model_validator (verify "Unchanged" per spec line 102 before touching)
- `portal_onboarding.py` — `/answer` union dispatch + IdentityPair partial-validation + `UnexpectedModelBehavior` → `TurnFailure` + JSONB sidecar persist with `#-` cleanup
- EXTEND `test_cumulative_state.py`, `test_completion_gate.py`, `test_tool_recovery.py` (TEST-M1 in-place coverage continuity)
- NEW `tests/api/routes/test_emission_dispatch.py` (per-emission-kind dispatch + UnexpectedModelBehavior conversion + JSONB cleanup)
- NEW `tests/api/routes/test_identity_pair.py` (IdentityPair full-valid + 4 partial cases)

## Pydantic AI 1.71 Verified Patterns (pre-flight cached)

Embed verbatim in next dispatches. Pre-flight subagent verified against ai.pydantic.dev:

```python
# Pattern A — output_type discriminated union
from pydantic_ai import Agent, ToolOutput, RunContext
from pydantic_ai.exceptions import ModelRetry, UnexpectedModelBehavior, ModelHTTPError

agent = Agent(
    model_name,
    deps_type=WizardDeps,
    output_type=[
        ToolOutput(ReactionOnly, name='reaction_only'),
        ToolOutput(FollowUpQuestion, name='follow_up_question'),
        ToolOutput(TurnFailure, name='turn_failure'),
    ],
    output_retries=2,
    instructions="<static base prompt>",
)

# Pattern B — dynamic instructions decorator (NOT ctor kwarg)
@agent.instructions
def inject_state_context(ctx: RunContext[WizardDeps]) -> str:
    state = ctx.deps.state
    if not state.missing:
        return ""
    return f"Slots still needed: {', '.join(state.missing)}.\nNext deterministic question: {ctx.deps.next_question}"

# Pattern C — output_validator
@agent.output_validator
async def reject_mirror_or_echo(ctx: RunContext[WizardDeps], output) -> ...:
    if isinstance(output, FollowUpQuestion):
        if difflib.SequenceMatcher(None, output.question_text.lower(), ctx.deps.next_question.lower()).ratio() > MIRROR_THRESHOLD:
            raise ModelRetry("FollowUpQuestion.question_text mirrors the next deterministic question.")
        if ctx.deps.last_user_answer.lower() in output.question_text.lower():
            raise ModelRetry("FollowUpQuestion.question_text quotes the user's last answer verbatim.")
    return output

# Pattern D — message_history serialization
from pydantic_ai import ModelMessagesTypeAdapter
from pydantic_core import to_jsonable_python
serializable = to_jsonable_python(result.all_messages())
restored = ModelMessagesTypeAdapter.validate_python(serializable)
result2 = agent.run(user_input, message_history=restored, deps=deps)

# Pattern E — exceptions
try:
    result = await agent.run(...)
    emission = result.output
except UnexpectedModelBehavior as exc:
    emission = TurnFailure(reason="model_retry_exhausted", original_error=str(exc))
```

## GH Issues Open (post this session)

- **#554** MEDIUM `chore(devx): Supabase MCP unauthorized in worktree subagent context` — workaround in place
- **#556** MEDIUM `feat(observability): emit structured backstory_pipeline_timeout / backstory_fallback_fired events` — extended scope per #555 spike to cover `answer_agent_*` events (now satisfied by 217-2c PR #558 — can verify + close)
- **#557** MEDIUM `fix(observability,agents): codebase-wide retry helper for ModelHTTPError on agent.run sites` — follow-up to 217-2c
- **#559** MEDIUM `fix(ci): test-summary/action@v2 missing index.js` — broken-infra, non-blocking

GH #553 closed (false alarm OTP delivery — was Gmail filter syntax bug). GH #555 closed (fixed in PR #558).

## Pending User Action

**Telegram MCP session expired** — needed for Walk B2-resume2 (217-2c live verify) + Walk B3 (217-3B verify) + Walk B4 (final integration). Re-mint via:

```
! cd /Users/yangsim/Nanoleq/sideProjects/telegram-mcp && python session_string_generator.py
```

Code-side review of 217-2c was CLEAN + Pytest SUCCESS, so 217-3A.1/3A.2 unblocked (BE-only, no Telegram MCP needed). Walks deferred until re-mint.

## Memory Entries Saved This Session

- `feedback_errata_payload_pattern.md` — Tier-3 plan-rewrite brief stays canonical; Phase-1 drift goes in orchestration-plan ERRATA, not brief revision
- `feedback_pre_push_includes_playwright.md` — Pre-push gate must add `npm run test:e2e` for portal CTA/route/link diffs (PR #551 precedent)
- `feedback_gcloud_traceback_truncation.md` — gcloud truncates textPayload ~120ch; pydantic_graph.GraphRun.__aexit__ frames in EVERY agent.run exception. Query structured ERROR log line FIRST, traceback second (GH #555 walk-B2-resume misread precedent)
- `feedback_gmail_mcp_search.md` — REWRITTEN with sender + subject reference table + plus-alias normalization + retry ladder + Walk B2 anti-pattern precedent

## Rule Updates Landed

- `.claude/rules/live-testing-protocol.md` step 6 — bakes canonical Gmail query pattern (`from:onboarding@silent-agents.com newer_than:5m` + widening-window retry ladder) into protocol so subagents pick from rule, not memory (commit `718bb45` on master)

## Cleanup Status (CL-CODE / CL-DOCS scoreboard)

| Item | Owner sub-PR | Status |
|---|---|---|
| C1 410 GONE stub TODO + GH #549 deadline | 217-0 | ✅ done |
| C2 portal/CLAUDE.md gotcha rewrite | 217-0 | ✅ done |
| C3/C4 signup_handler / make_anthropic_generator dead-code trace | 217-2 spike | ✅ documented |
| C5 em-dash sweep agent prompts | 217-3A.1+3A.2 | pending — implementor instructed |
| C6 question casing audit | 217-3B | pending |
| C7-C10 dead-types / `# noqa` audit | per sub-PR | pending |
| D1-D3 216 supersedes banners | landed | ✅ on master |
| D5 ROADMAP register + sync | landed | ✅ done |
| D8 portal/CLAUDE.md stale gotcha | landed | ✅ done |
| D9 nikita/agents/onboarding/CLAUDE.md union refactor | 217-3A.2 | pending |
| D10 portal/src/app/onboarding/CLAUDE.md sibling DOM | 217-3B | pending |
| D14 brief archive post-Walk-B4 | post-Step 6 | pending |
| D15 215A note no-unblock | landed | ✅ in spec.md |

## Next Steps (in order)

1. **Wait** for 217-3A.1 implementor PR open (background, will notify).
2. **Grep-verify** the 7 files landed correctly on `feat/217-3A.1-emission-prereqs` (per `.claude/rules/pr-workflow.md` Orchestrator Grep-Verify Gate).
3. **QA-review** subagent dispatch (HARD CAP 5, fresh context, 8-category review, zero-tolerance loop).
4. **CI poll** until Pytest + (E2E if applicable) SUCCESS.
5. **Squash merge** 217-3A.1 → master.
6. **Verify commit on master** via `git log origin/master --oneline -3`.
7. **Dispatch 217-3A.2** implementor (agent + dispatch wiring; reuse pre-flight Pydantic AI patterns above; HARD CAP 40, 350 prod LOC budget; spec ACs are AUTHORITATIVE — extend baseline tests in place).
8. **QA + CI + merge** 3A.2 same loop.
9. **Deploy** Cloud Run (`gcloud run deploy nikita-api --source . --region us-central1 --project gcp-transcribe-test --allow-unauthenticated`).
10. **WAIT FOR USER** to re-mint Telegram MCP session (or skip walks if user approves).
11. **Walk B2-resume2** (217-2c live verify, retry path; HARD CAP 25; canonical 12-step protocol; plus-alias `+walkb2d@gmail.com` (already used in BLOCKED attempt — bump to `+walkb2e` for fresh)).
12. **Dispatch 217-3B** implementor (FE wizard sibling-DOM refactor; HARD CAP 35; touch-files matrix per orchestration plan; pre-flight: shadcn Card/Skeleton/Alert + Playwright clock API).
13. **Walk B3** (217-3B verify, sibling DOM `[data-testid="deterministic-card"]` + `[data-testid="agent-subspace"]` distinct; user-bug 4 overlay-fix verify).
14. **Walk B4** final integration (full chain; success criteria per orchestration plan Step 6: cold-start TG CTA prefills, interstitial reskin, no loading flash, sibling DOM, backstory completes p99 ≤30s OR retry CTA renders, FinalForm fires + redirect).
15. **CL-VERIFY V1-V9** cleanup audit (per orchestration plan).
16. **Archive** docs-to-process/20260507-spec217-onboarding-redesign-planning-brief.md per D14.
17. **Mark Spec 217 complete** in ROADMAP.md.

## Critical Rules to Re-Honor in New Session

- `.claude/rules/agentic-design-patterns.md` — 6 hard rules + 5 anti-patterns + 3 mandatory test classes (cumulative-state monotonicity, completion-gate triplet, mock-LLM-emits-wrong-tool recovery)
- `.claude/rules/testing.md` — Agentic-Flow Test Requirements + Live-Dogfood Anti-Patterns
- `.claude/rules/live-testing-protocol.md` — 12-step canonical walk (now with corrected Gmail step)
- `.claude/rules/pr-workflow.md` — pre-push HARD GATE + grep-verify gate + commit-hash audit + zero-tolerance QA loop
- `.claude/rules/parallel-agents.md` — subagent dispatch caps (HARD CAP + scope + exit criterion mandatory)
- `.claude/rules/subagent-safety.md` — anti-fabrication clause for live walks; worktree isolation for file-mutating dispatches
- `~/.claude/CLAUDE.md` em-dash hard rule — NO em-dashes in user-facing prose; permitted in dev comments
- Operating Behavior #8 — auto-execute routine follow-through; carve-outs only (a) destructive, (b) scope expansion, (c) external visible, (d) >1h-rework spec ambiguity
- Operating Behavior #10 — AskUserQuestion tool for genuine input; never inline lettered-options prose

## File Locations Quick-Ref

- Spec: `specs/217-onboarding-wizard-deterministic-redesign/{spec.md, plan.md, tasks.md, audit-report.md, validation-findings.md}`
- Sub-spec dirs: `specs/217-onboarding-wizard-deterministic-redesign/subspecs/{217-0, 217-1, 217-2, 217-3A, 217-3B}-*/`
- Brief (planning): `docs-to-process/20260507-spec217-onboarding-redesign-planning-brief.md` (archive post-Walk-B4)
- Spike (217-2 backstory): `docs-to-process/20260507-spec217-2-backstory-diagnosis.md`
- Spike (GH #555 ModelHTTPError): `docs-to-process/20260508-gh555-be-archetype-timeout-spike.md`
- Walks: `audits/2026/walk-B1-spec217-1.md`, `walk-B2-spec217-2.md`, `walk-B2-resume-spec217-2.md`, `walk-B2-resume2-spec217-2c.md`
- Orchestration plan: `~/.claude/plans/immutable-wondering-gray.md`
- Memory: `~/.claude/projects/-Users-yangsim-Nanoleq-sideProjects-nikita/memory/` (4 new entries this session)

## What This Handover Costs vs Free-form Compact

This artifact is the canonical resume point. Reading it + the 7-file refined scope = ~400 LoC of context. Reading the full session transcript = ~500K tokens. Net savings: 99%.

The orchestrator can resume from this file alone + the rules + the specs. No transcript replay needed.

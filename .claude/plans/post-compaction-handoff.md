# Post-Compaction Handoff — Epic 1 Sprint after PR #252

**As of**: 2026-04-12, after merging PR #252 (GH #248 hotfix)
**Plan file (standing directive)**: `.claude/plans/quirky-floating-liskov.md` — contains the **Self-Improvement Loop** section that now applies to every plan going forward
**Current branch**: `master` (clean; hotfix branch auto-deleted on squash-merge)
**Full suite baseline**: 5767 passed (vs 5763 pre-hotfix)

---

## Standing directive — NEVER DROP THIS

**At the end of every plan (not just complex ones), run the 5-step self-improvement loop:**

1. **Pattern** — What durable finding did this task uncover?
2. **Rules** — Update `.claude/rules/*` / CLAUDE.md to encode it?
3. **Memory** — Save a project/feedback entry to `/Users/yangsim/.claude/projects/-Users-yangsim-Nanoleq-sideProjects-nikita/memory/`?
4. **Audit** — Does it imply a systemic spec (register in ROADMAP + `/feature`)?
5. **Execute** — Do 2/3/4 in-session, not as followup tickets.

Reference: `memory/feedback_self_improvement_loop.md` (already saved this session).
Scale to task size — typo-fix gets one line, bug-fix gets the full routine.

---

## Just landed

| PR | Scope | Issues |
|----|-------|--------|
| #252 | fix(delivery): include chat_id in scheduled telegram events | Closes #248 (CRITICAL — every delayed text gameplay response was failing silently) |

**What PR #252 did**:
- Producer (`nikita/agents/text/handler.py`): `store_pending_response(chat_id: int)` required; caller passes `deps.user.telegram_id`; early-returns non-responsive decision if telegram_id is None.
- Consumer (`nikita/api/routes/tasks.py`): falls back to `event.user.telegram_id` (auto-loaded via `lazy="selectin"`) when `content.chat_id` is missing; WARNING log on fallback path.
- 4 new tests including explicit coverage of the previously-unexercised content-parsing branch.
- qa-review loop: **converged in 3 iterations** (R1-R10: 7 fixed, 2 rejected-empirically, 3 nitpicks skipped). See `.claude/plans/pr-review-ledger-fix-scheduled-delivery-chat-id-248.md`.

---

## Post-merge self-improvement — DO THIS FIRST, BEFORE PR-3

Three tasks, in order. Total budget ~30 minutes.

### 1. Update `.claude/rules/testing.md` (Task #24)

Add a rule encoding the "tests that don't test" anti-pattern uncovered by #248:

> **Tests of workers / iterators / consumers**: when a function iterates over a repository query result (`get_due_*`, `get_active_*`, `find_*`, `list_*`), at least ONE test MUST provide a non-empty fixture and assert on the loop-body path. Mocking the return to `[]` only tests dispatch, not behavior. Example regression: `test_tasks.py` mocked `get_due_events → []` in every test for months while the content-parsing branch was broken (GH #248).

Also add:
> **Zero-assertion tests are dead weight**: every test must have at least one assertion that would fail if the code under test were removed. Example that slipped through: `test_calls_repository_create_event_with_session` had no assertions; only when reviewer flagged it did we pin the `create_event.assert_awaited_once()` contract.

Verify line count stays ≤80. If the rule is truly project-global (plausible), consider lifting to `~/.claude/CLAUDE.md` instead.

### 2. Save `project_scheduled_events_delivery.md` memory (Task #25)

Save to `/Users/yangsim/.claude/projects/-Users-yangsim-Nanoleq-sideProjects-nikita/memory/project_scheduled_events_delivery.md`:

```markdown
---
name: Scheduled Events Delivery Architecture
description: scheduled_events table, worker, chat_id convention, selectin auto-load — prevents re-research
type: project
---

**scheduled_events table**: unified queue for Telegram + voice delayed delivery.
- Schema: `id, user_id FK, platform ('telegram'|'voice'), content JSONB, scheduled_at, delivered_at, status ('pending'|'delivered'|'failed'), retry_count, error_message`.
- Model: `nikita/db/models/scheduled_event.py` — `user_id` FK with `lazy="selectin"` so `event.user` is auto-loaded.

**Producer**: `store_pending_response` in `nikita/agents/text/handler.py` (single caller: MessageHandler.handle).

**Consumer**: `/tasks/deliver` endpoint in `nikita/api/routes/tasks.py` — called by pg_cron every minute. Uses function-local imports.

**chat_id ≡ telegram_id**: multiple call sites store `user.telegram_id` verbatim under content["chat_id"] (scheduling.py:173, decay notify tasks.py:232, handoff.py:520). `TelegramBot.send_message(chat_id: int, ...)` requires the integer.

**Retry**: `mark_failed(increment_retry=False)` → terminal FAILED. `increment_retry=True` → exponential backoff (1/2/4 min), 3 retries then FAILED.

**Test patch target**: function-local `from nikita.db.repositories.scheduled_event_repository import ScheduledEventRepository` resolves via `sys.modules` each call, so patching the SOURCE module is correct. Do NOT double-patch with `create=True` on the caller module.

**Why it matters**: every delayed gameplay response goes through this pipeline. GH #248 was a silent failure here for months.
```

Update `memory/MEMORY.md` index with a pointer under "Technical Gotchas".

### 3. Register test-quality audit spec in ROADMAP.md (Task #26)

This is the systemic follow-up from #248. Scope:

- Scan every file under `tests/` for mocks that return `[]` or a single trivial value for repository methods (`get_*`, `find_*`, `list_*`, etc.) and identify the corresponding production function.
- Prioritize by blast radius: delivery, scoring, decay, boss fights, onboarding handoff, memory dedup.
- For each gap, create a follow-up ticket. Batch into 3-5 PRs.
- Output: `.claude/rules/test-quality.md` (if not already landed by Task #24) + backlog of gap tickets. Optional: CI assertion flagging `return_value=[]` in mock setups without a paired non-empty case.

Command: `/roadmap add NNN test-quality-audit`, then `/feature` to scope the spec.

---

## Epic 1 Sprint — where we are

| PR | Status | Scope | Issues |
|----|--------|-------|--------|
| PR-1 | done (commit 0374c54) | housekeeping | #183, and supposedly #184 + #233 — **VERIFY: both were open at last handoff** |
| PR-2 | merged (PR #250, commit 6f36816) | city validation + deferred handoff retry | #198 closed |
| PR #252 | **just merged** | chat_id hotfix | #248 closed |
| PR-3 | pending — next | few-shot injection + vulnerability guard | #201 |
| PR-4 | pending | boss encounter overhaul | #200 |
| PR-5 | pending | memory dedup tuning | #199 |
| Phase 4 | pending | verification E2E + voice checklist | — |

Plus follow-up spec from Self-Improvement §4: **test-quality audit** (Task #26).

---

## How to resume — exact sequence

```
1. git status   # confirm clean master
2. Check task list via TaskList — tasks #24/#25/#26 are pending post-merge
3. Execute Tasks #24, #25, #26 in order (see details above)
4. Verify GH #184 and #233 actually closed (PR-1 claim vs reality):
   gh issue view 184
   gh issue view 233
5. Begin PR-3:
   git checkout -b feat/prompt-quality-few-shot
   # TDD: write failing test for Ch1 EXAMPLE_RESPONSES injection first
6. Apply Self-Improvement Loop when PR-3 merges
```

---

## PR-3 plan summary (from quirky-floating-liskov.md — pre-rewrite Epic 1 plan)

**Problem**: `chapter_1.prompt` says "DON'T reveal vulnerabilities" but this is SKIPPED when `generated_prompt` is set (production path). The pipeline prompt doesn't enforce chapter-specific behavioral constraints.

**Changes**:

1. `nikita/agents/text/agent.py` — NEW `@agent.instructions` decorator injecting 3-5 chapter-appropriate examples from `EXAMPLE_RESPONSES` as `## RESPONSE CALIBRATION EXAMPLES`. Always active (not skipped by `generated_prompt`).
2. `nikita/agents/text/agent.py` — NEW `@agent.instructions` decorator injecting 2-3 hard rules per chapter. Ch1: "NEVER reveal personal vulnerabilities", "NEVER use >2 sentences", "NEVER initiate emotional intimacy".
3. `nikita/agents/text/persona.py` — NEW `get_chapter_examples(chapter: int) -> list[dict]` returning filtered subset. Ch1: generic greeting, too familiar too quickly, asks about past, boring question. Ch3+: personal struggle, upset.

**Tests**: 5+ verifying examples injected per chapter, constraints never skipped.

**Branch**: `feat/prompt-quality-few-shot`

**Key files**:
- `nikita/agents/text/agent.py:87-168` (4 instruction layers assembly)
- `nikita/agents/text/persona.py:25-161` (EXAMPLE_RESPONSES currently unused)
- `nikita/prompts/chapters/chapter_1.prompt` (Ch1 rules — skipped in prod)

---

## Critical conventions (do NOT drop)

- **NEVER commit to master** — branch + PR + `/qa-review` loop always.
- Max 400 lines per PR.
- `rtk proxy pytest …` — direct `pytest` returns "No tests collected" due to rtk hook interception.
- Full test suite: ~5767 tests, ~2m45s via rtk proxy.
- Supabase MCP (NEVER CLI) for DB operations.
- Squash-merge with `--delete-branch`. Then deploy to Cloud Run only from master.
- After implementation diverges from spec: update spec or archive it to `specs/archive/`.

---

## Parallel agent awareness

Another session may be in worktree `.claude/worktrees/delightful-orbiting-ladybug`. Check before touching `nikita/agents/text/*` (PR-3 target):

```
ls -la .claude/worktrees/
git -C .claude/worktrees/delightful-orbiting-ladybug log --oneline -5 2>/dev/null
```

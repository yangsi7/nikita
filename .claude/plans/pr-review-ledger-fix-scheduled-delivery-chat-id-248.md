# Review Ledger — fix/scheduled-delivery-chat-id-248

## Meta
- PR: #252 — fix(delivery): include chat_id in scheduled telegram events (#248)
- URL: https://github.com/yangsi7/nikita/pull/252
- Scope: PR diff (4 files; +236 / -2)
- Iteration: 0 / 5
- Severity threshold: important
- Mode: fix
- Review type: external (fresh-context)
- Full suite baseline: 5767 passed, 0 failed (vs 5763 on master)

## Findings

| ID | File | Line | Category | Severity | Status | Iter | Reviewer |
|----|------|------|----------|----------|--------|------|----------|
| R1 | tests/agents/text/test_handler.py | ~472 | Testing | important | FIX | 1 | external |
| R2 | tests/agents/text/test_handler.py | — | Testing | important | FIX | 1 | external |
| R3 | tests/api/routes/test_tasks.py | ~583 | Testing | important | FIX | 1 | external |
| R4 | nikita/agents/text/handler.py | ~405-422 | Correctness | important→nitpick | DOWNGRADED | 1 | external |
| R5 | nikita/api/routes/tasks.py | ~320 | Type safety | nitpick | SKIPPED | 1 | external |
| R6 | tests/api/routes/test_tasks.py | ~610 | Testing | nitpick | SKIPPED | 1 | external |
| R7 | tests/agents/text/test_handler.py | ~449 | Testing | important | FIXED | 2 | external |
| R8 | tests/api/routes/test_tasks.py | ~637 | Testing | important → rejected | DOCUMENTED | 2 | external |
| R9 | tests/agents/text/test_handler.py | ~421 | Testing | nitpick | SKIPPED | 2 | external |
| R10 | nikita/api/routes/tasks.py | ~320 | Correctness | nitpick | SKIPPED | 2 | external |

## Fix Log

### Iteration 0 (initial self-review)
- 0 blocking, 0 important at self-assessment. Proceeded directly to external re-review.

### Iteration 1 (external re-review — 4 important, 2 nitpick)
- R1: simplify double-patch to single source-module patch.
- R2: add test covering `telegram_id=None` early-return path.
- R3: replace `"telegram"` literal with `EventPlatform.TELEGRAM.value`.
- R4: downgrade — handler's `logger.error(...)` already provides the visibility; skip_reason pattern matches existing skip paths at lines 373-379.
- R5, R6: skip (nitpick below threshold).

### Iteration 2 (external re-review — 2 important, 2 nitpick)
- R7: FIXED — added `create_event.assert_awaited_once()` + kwarg assertions to `test_calls_repository_create_event_with_session`. Previously zero-assertion shell.
- R8: REJECTED + DOCUMENTED — empirically the 3 `TestDeliverChatIdHandling` tests pass because the function-local `from ... import ScheduledEventRepository` re-resolves through `sys.modules` each call, so patching the source module is correct. If it weren't, the real repository would be constructed against the mock session and crash on `get_due_events`. Added a long clarifying docstring on `_run_deliver` to preempt future confusion and explicitly warn against the belt-and-suspenders double-patch.
- R9, R10: skip (nitpick below threshold).

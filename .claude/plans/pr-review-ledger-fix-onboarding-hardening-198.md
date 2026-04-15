# Review Ledger — fix/onboarding-hardening-198

## Meta
- PR: #250 — fix(onboarding): harden city validation + deferred handoff retry
- URL: https://github.com/yangsi7/nikita/pull/250
- Scope: PR diff (11 files; ~265 added / 20 modified)
- Iterations: 4 / 5
- Severity threshold: important
- Mode: fix
- Review type: external (fresh-context)
- Convergence: **CLEAN** (iter 4 external = READY TO MERGE)
- Full suite: 5763 passed, 0 failed, 138 deselected (2m45s)
- Follow-up: GH #251 (lock-fallback double-fire, non-blocking)

## Findings

| ID | File | Line | Category | Severity | Status | Iter | Reviewer |
|----|------|------|----------|----------|--------|------|----------|
| R1 | tests/api/routes/test_onboarding_profile.py | — | Testing | important | FIXED (commit dde0da2) | 0 | self |
| R2 | nikita/onboarding/validation.py | 66 | Correctness | nitpick | FIXED (commit dde0da2) | 0 | self |
| R3 | Supabase Preview | — | CI | nitpick | NOT APPLICABLE (pre-existing master failure) | 0 | self |
| R4 | nikita/db/repositories/user_repository.py | 574 | Performance | important→nitpick | SKIPPED (consistency with 9 sibling methods) | 1 | external |
| R5 | nikita/platforms/telegram/message_handler.py | 782 | Correctness | important→nitpick | DOCUMENTED (commit 317cbc3 — clarifying comment) | 1 | external |
| R6 | nikita/onboarding/validation.py | 30 | Correctness | nitpick | DOCUMENTED (commit 317cbc3 — false-positive comment) | 1 | external |
| R7 | nikita/platforms/telegram/message_handler.py | 782 | Type safety | nitpick | SKIPPED (defensive untyped matches existing test mocks) | 1 | external |
| R8 | supabase/migrations/20260413140000… | — | Style | nitpick | SKIPPED (cosmetic) | 1 | external |
| R9 | tests/platforms/telegram/test_message_handler.py | 1251 | Testing | important | REJECTED (empirically verified patch target correct) | 2 | external |
| R10 | tests/platforms/telegram/test_message_handler.py | — | Testing | important | FIXED (commit 2a1b11e — 2 integration tests for `_needs_onboarding` gate) | 2 | external |
| R11 | nikita/platforms/telegram/message_handler.py | 196 | Correctness | important→deferred | FOLLOWED UP (GH #251 — pre-existing lock-fallback double-fire window) | 3 | external |
| R12 | tests/onboarding/test_validation.py | — | Testing | nitpick | FIXED (commit 422c468 — Bar, Montenegro accept case) | 3 | external |
| R13 | tests/platforms/telegram/test_message_handler.py | — | Testing | nitpick | FIXED (commit 422c468 — "skipped" onboarding status path) | 3 | external |

## Fix Log

### Iteration 0 (self-review)
- Found 3 findings (1 important: untested error path; 2 nitpicks).
- FIXED R1 (added error-path test), R2 (strip NBSP/narrow/figure spaces).
- Commit: `dde0da2` — fix(onboarding): strip NBSP + test deferred-handoff flag error path

### Iteration 1 (external re-review — 2 important, 4 nitpick)
- Analysis: R4 + R5 downgraded to nitpick after deeper analysis (consistency + pre-existing pattern).
- FIXED R5, R6 via clarifying code comments (no behavior change).
- Commit: `317cbc3` — docs(onboarding): clarify junk-word false-positives + handoff timing

### Iteration 2 (external re-review — 2 important, 4 nitpick)
- R9 REJECTED empirically — Python's function-local `from X import Y` resolves at call time through source module, so existing patch target IS correct (117/117 tests pass as confirmation).
- FIXED R10 (2 integration tests for `_needs_onboarding` → `_execute_pending_handoff` gate).
- Commit: `2a1b11e` — test(onboarding): cover _needs_onboarding → _execute_pending_handoff gate

### Iteration 3 (external re-review — 1 borderline important, 6 nitpicks)
- Reviewer declared `CLEAN: 0 blocking, 0 important issues found`.
- R11 (lock-fallback race) filed as GH #251 (pre-existing, non-blocking).
- FIXED R12 (Bar, Montenegro accept test), R13 (skipped status test).
- Commit: `422c468` — test(onboarding): cover skipped status + Bar,Montenegro city path

### Iteration 4 (final external re-review)
- Verdict: `READY TO MERGE: 0 blocking, 0 important issues.`
- Full suite: 5763 passed, 0 failed (2m45s).
- Convergence reached.

## Commits (4)

| SHA | Summary |
|-----|---------|
| 0374c54 | fix(onboarding): harden city validation + deferred handoff retry (#198) [initial] |
| dde0da2 | fix(onboarding): strip NBSP + test deferred-handoff flag error path |
| 317cbc3 | docs(onboarding): clarify junk-word false-positives + handoff timing |
| 2a1b11e | test(onboarding): cover _needs_onboarding → _execute_pending_handoff gate |
| 422c468 | test(onboarding): cover skipped status + Bar,Montenegro city path |

## Status: PASS — ready to merge

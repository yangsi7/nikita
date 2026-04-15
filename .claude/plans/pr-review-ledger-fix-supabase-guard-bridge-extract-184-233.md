# Review Ledger — fix/supabase-guard-bridge-extract-184-233

## Meta
- PR: #253 — fix(api,telegram): SUPABASE_URL guard + extract portal bridge utility (#184, #233)
- URL: https://github.com/yangsi7/nikita/pull/253
- Scope: PR diff (13 files; +473 / -269)
- Iteration: 0 / 5
- Severity threshold: important
- Mode: fix
- Review type: external (fresh-context)
- Full suite baseline: 5772 passed (180s)

## Changed Files
- nikita/api/main.py (+10/-0) — SUPABASE_URL guard
- nikita/platforms/telegram/utils.py (+69/-0) — new leaf module
- nikita/platforms/telegram/otp_handler.py (-54) — delete dup method, rewire caller
- nikita/platforms/telegram/message_handler.py (-41) — delete dup method, rewire caller
- nikita/platforms/telegram/commands.py (-5/+3) — rewire caller
- tests/api/test_main_lifespan.py (+69) — new
- tests/platforms/telegram/test_utils.py (+155) — new
- tests/platforms/telegram/test_otp_handler_onboarding.py (refactored) — patch source
- tests/platforms/telegram/test_commands.py (refactored) — patch source
- .claude/rules/testing.md (+29) — "tests that don't test" rule (session housekeeping)
- ROADMAP.md (Spec 210 row)
- event-stream.md (session log)
- specs/210-test-quality-audit/README.md (new, PLANNED)

## Findings

| ID | File | Line | Category | Severity | Status | Iter | Reviewer |
|----|------|------|----------|----------|--------|------|----------|
| R1 | nikita/platforms/telegram/commands.py | 20 | Correctness | important | FIXED | 1 | external |
| R2 | tests/platforms/telegram/test_utils.py | 36-43 | Testing | nitpick | SKIPPED | 1 | external |
| R3 | tests/api/test_main_lifespan.py | 28 | Testing | nitpick | SKIPPED | 1 | external |

## Fix Log

### Iteration 0 (self-review)
- 8-category pass on all 13 changed files.
- 0 blocking, 0 important found.
- 2 nitpicks considered + deferred: (N1) `utils.py` broad `except Exception` is pre-existing, not a regression; (N2) `event-stream.md` entry slightly duplicates commit log.

### Iteration 1 (external re-review)
- R1: FIXED — Dangling `from nikita.platforms.telegram.otp_handler import OTPVerificationHandler` at commands.py:20 removed (commit dc2d9d9). Classic F401 after refactor. 16 tests in test_commands.py still pass.
- R2: SKIPPED — nitpick. Suggested adding an explanatory comment about why source-module patching works. Already documented in `.claude/rules/testing.md` and via inline comment in `otp_handler.py:346-348`. Redundant to add in test.
- R3: SKIPPED — nitpick. `anthropic_api_key`/`llm_warmup_enabled` attributes on mock_settings are defensive but dead for this test path. Harmless; removal would be cosmetic-only.
- Iter 1 verdict: pending iter 2 external re-review.

### Iteration 2 (external re-review)
- **CLEAN**: 0 blocking, 0 important issues remaining.
- 3 nitpicks flagged + rationalized (all below threshold):
  - `utils.py:65` broad `except Exception` — pre-existing pattern, acceptable with None-fallback
  - `main.py:81-91` guard asymmetry (task_auth_secret skips in debug, supabase_url unconditional) — deliberate and documented
  - `test_main_lifespan.py:28` fixture attrs not asserted on — harmless dead setup
- Integration risk confirmed ZERO: `OTPVerificationHandler(...)` constructor had no I/O or state mutation.
- CONVERGENCE REACHED. Quality suite: 5772 passed. Status: **PASS**.

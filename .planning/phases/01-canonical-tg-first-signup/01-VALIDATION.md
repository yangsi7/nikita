---
phase: 01
slug: canonical-tg-first-signup
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-20
---

# Phase 01 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Derived from `01-RESEARCH.md` (## Validation Architecture + ## Security Domain). Spec 220 canonical Telegram-first signup.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (Python backend); vitest (portal); Playwright (portal E2E) |
| **Config file** | `pytest.ini` (root); `portal/vitest.config.ts`; `portal/playwright.config.ts` |
| **Quick run command** | `uv run pytest tests/platforms/telegram/ tests/api/routes/test_portal_auth*.py tests/api/routes/test_telegram*.py -q` |
| **Full suite command** | `uv run pytest -q` + `(cd portal && npm run test -- --run && npm run lint && npm run build)` |
| **Estimated runtime** | backend ~90 s; portal vitest ~30 s; lint+build ~60 s |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/platforms/telegram/ -q` (backend tasks) OR `(cd portal && npm run test -- --run)` (portal tasks)
- **After every plan wave:** Run full suite (`uv run pytest -q` + portal vitest+lint+build)
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 90 s (backend quick) / 30 s (portal quick)

---

## Per-Task Verification Map

> Task IDs assigned by gsd-planner. This map seeds the requirement→test mapping from RESEARCH; planner fills `Task ID` + `Wave` columns per PLAN.md.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | 02 | — | REQ-004/FR-3 | T-Spoof-1 | telegram_id stashed in raw_user_meta_data on OTP send | unit (mock SDK) | `uv run pytest tests/platforms/telegram/test_signup_handler_arch_b.py -x` | ❌ W0 | ⬜ pending |
| TBD | 02 | — | REQ-004/FR-4a | T-Spoof-1 | app_metadata.telegram_id immutable lock via admin API | unit (mock SDK) | `uv run pytest tests/platforms/telegram/test_signup_handler_arch_b.py -x` | ❌ W0 | ⬜ pending |
| TBD | 05 | — | REQ-004b/FR-4b | T-Tamper-1 | trigger provisions users/metrics/vices on email_confirmed_at flip; ON CONFLICT idempotent | integration (Supabase MCP) | `mcp__supabase__execute_sql` verification script | ❌ W0 | ⬜ pending |
| TBD | 02 | — | REQ-009/FR-5 | — | FSM routing removed; UNKNOWN→welcome; known→chat | unit | `uv run pytest tests/api/routes/test_telegram_routing_arch_b.py -x` | ❌ W0 | ⬜ pending |
| TBD | 02 | — | REQ-004/FR-6 | — | handle_otp replaces handle_code (8-digit OTP regex `^[0-9]{8}$`) | unit | `uv run pytest tests/platforms/telegram/test_signup_handler_arch_b.py -x` | ❌ W0 | ⬜ pending |
| TBD | 03 | — | REQ-008/FR-8 | T-DoS-1 | middleware blocks /dashboard/* for app_metadata.onboarded!=true | unit (middleware mock) | `(cd portal && npm run test -- --run)` | ❌ W0 | ⬜ pending |
| TBD | 02 | — | REQ-006/FR-9 | — | /auth/confirm autobind side-effect stripped; thin PKCE handler ≤80 LOC | unit (route mock) | `(cd portal && npm run test -- src/app/auth/confirm/__tests__/)` | ✅ (update) | ⬜ pending |
| TBD | 01 | — | REQ-011/FR-11 | T-Tamper-2 | wizard /onboarding PATCH: SELECT FOR UPDATE + admin.update_user_by_id(onboarded) | unit | `uv run pytest tests/api/routes/test_portal_onboarding.py -x` | ✅ | ⬜ pending |
| TBD | 05 | — | REQ-020/FR-13 | — | onboarding_status 'skipped' removed from CHECK constraint (3-value enum) | migration test | `mcp__supabase__execute_sql` | ❌ W0 | ⬜ pending |
| TBD | 03 | — | REQ-021/AC-18 | — | message_handler admit-list shrunk to ('completed',) | unit | `uv run pytest tests/platforms/telegram/test_message_handler.py -x` | ✅ | ⬜ pending |
| TBD | 04 | — | REQ-014/REQ-015/AC-13 | T-Info-1 | 9 PII-leak log lines removed; no [LLM-DEBUG] | source assertion | `! rg -n "\[LLM-DEBUG\]" nikita/` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/platforms/telegram/test_signup_handler_arch_b.py` — stubs for REQ-004/FR-3, FR-4a, FR-6 (new handle_email + handle_otp unit tests)
- [ ] `tests/api/routes/test_telegram_routing_arch_b.py` — stubs for REQ-009/FR-5 (stripped FSM routing)
- [ ] `portal/src/app/auth/confirm/__tests__/route.test.ts` — REQ-006/FR-9 (autobind stripped; exists as `.worktree_new` per git status — promote)
- [ ] Middleware test update for `app_metadata.onboarded` check — REQ-008/FR-8
- [ ] Supabase MCP trigger verification script — REQ-004b/FR-4b, REQ-020/FR-13 (run via `mcp__supabase__execute_sql`, NOT CLI)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live TG-first signup end-to-end (email→OTP→paste→portal→onboard→chat) | AC-1..AC-18 | Real Supabase GoTrue OTP + Gmail delivery + Telegram bot; cannot mock the full external loop | `.claude/rules/live-testing-protocol.md` 12-step walk, plus-alias `simon.yang.ch+walk220@gmail.com` |
| DB trigger atomic provisioning under real `email_confirmed_at` flip | REQ-004b/FR-4b | Trigger fires inside GoTrue transaction; only observable against live Supabase | `mcp__supabase__execute_sql`: verify `public.users` row appears after `verify_otp` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

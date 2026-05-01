# Subspec 216-A — Telegram Canonical Routing

**Parent**: `specs/216-onboarding-redesign-cinematic/spec.md` FR-01, FR-11, NR-07
**PR boundary**: 216-A (independent, no upstream subspec dependency)
**Estimated**: ~80 LOC + ~50 LOC test
**Status**: Draft (GATE 1)

---

## Scope

Rewire bare `/start` for unbound `telegram_id` users from `nikita/platforms/telegram/commands.py:343-348` `_send_bare_portal_auth_link` (deep-link to portal email form) to `nikita/platforms/telegram/signup_handler.py::SignupHandler.handle_welcome` (conversational FSM). The `/start welcome` payload-literal path is preserved for backwards compatibility — both routes converge to the same FSM entry. Bound users (`telegram_id` resolves to `users.id`) bypass FSM and continue to `CommandHandler` (existing behavior). Adds idempotent magic-link click handling (re-click yields 400 OR redirect when session live) and verifies JWT cookie + conversation_jsonb resume across all FR-11 / NR-07 paths.

## Background — STEP-0 verdict (2026-04-29)

Read-only intel-explore subagent traced the routing dispatch:

- Telegram webhook lands at `POST /telegram/webhook` in `nikita/api/routes/telegram.py:501` (`receive_webhook`).
- Two-branch dispatch for commands at line 624:
  - **Branch A** (lines 635-659): `cmd == "start" AND payload == "welcome" AND unbound_telegram_id` → `_run_signup_with_fresh_session(...)` → `SignupHandler.handle_welcome` (background task).
  - **Branch B** (lines 661-666): all other commands → `CommandHandler.handle()` → `_handle_start` (`commands.py:271`). For unknown user, E1 path at lines 343-348 calls `_send_bare_portal_auth_link` (deep-link button to `{portal}/onboarding/auth`).
- `SignupHandler` is otherwise reachable only from free-text messages (lines 672-699) when a `pending_signup_session` row exists with `signup_state IN ('awaiting_email','code_sent')`.
- **No feature flag** gates this; routing split is hardcoded.

Verdict: **Option (C) — two parallel handlers; old welcome-with-deeplink wins for bare `/start`**. Fix scope = small code patch.

## Acceptance Criteria

| AC | Description | Severity |
|----|-------------|----------|
| **A1.1** | Bare `/start` from unbound `telegram_id` enters `SignupHandler.handle_welcome` (NOT `_handle_start` E1 path). Test: `tests/platforms/telegram/test_routing.py::test_bare_start_unbound_enters_signup_handler` mocks webhook update with `text="/start"`, no payload, telegram_id absent from `users` → asserts `SignupHandler.handle_welcome` invoked exactly once and `_handle_start` not invoked. | CRIT |
| **A1.2** | `/start welcome` deep-link payload also enters `SignupHandler.handle_welcome` (existing path preserved). Regression test asserts both bare AND welcome-payload converge to the same handler. | HIGH |
| **A1.3** | Bound users (`telegram_id` resolves to `users.id`) bypass FSM and route to normal `CommandHandler.handle` → `_handle_start` bound-user branch. Existing behavior preserved. | HIGH |
| **A1.4** | First reply ≤5s after `/start`, Nikita-voiced (no "as an AI"), ≤280 chars, asks for email. Verified via `mcp__telegram-mcp__send_message` → `mcp__telegram-mcp__get_messages`. | CRIT |
| **A1.5** | `pending_signup_session` row inserted with `signup_state='awaiting_email'` on first turn. Verified via `mcp__supabase__execute_sql SELECT signup_state, telegram_id FROM public.pending_signup_session WHERE telegram_id = <X>`. | CRIT |
| **A1.6** | OTP code submitted in chat (6 digits) → `signup_state='magic_link_sent'`, `magic_link_token` populated. Verified via DB read post-OTP-submit. | CRIT |
| **A1.7** | Magic-link reply contains PKCE format `https://nikita-mygirl.com/auth/confirm?token_hash=...&type=...&next=/onboarding`, Telegram preview suppressed (`disable_web_page_preview=true`). | HIGH |
| **A1.8** | Wrong OTP path (#437 known MEDIUM) — current behavior documented; if session purged on wrong code, log evidence in walk report. NOT fixed in scope. | MED |
| **A1.9** | Idempotent magic-link click — **deterministic predicate**: (a) request bears valid `nikita-session` JWT cookie → 302 to `/dashboard`; (b) no cookie or invalid cookie → 400 with `ErrorEnvelope(error="magic_link_consumed", detail="This link has already been used.")`. NO new session minting on path (b). Tests must exercise BOTH branches. (Closes api-validator HIGH + auth-validator HIGH-1 by replacing disjunction with predicate.) | HIGH |
| **A1.10** | JWT cookie attributes asserted on `/auth/confirm` 200 response: `HttpOnly=True`, `Secure=True`, `SameSite=Lax`, `Path=/`, `Max-Age >= 604800`. Verified by parsing `Set-Cookie` header in integration test. (Closes auth-validator HIGH-2.) | HIGH |
| **A1.11** | Concurrent magic-link click race (W3 #F.2): two simultaneous `/auth/confirm?token_hash=X` requests with same `token_hash` — exactly ONE returns 200 + sets cookie; the other returns 400 + `ErrorEnvelope(error="magic_link_consumed")`. NO partial DB state (no orphan `auth.users` row, no missing `user_profiles` row). Verified via `asyncio.gather` integration test. (Closes auth-validator HIGH-3.) | HIGH |
| **A1.12** | Resume mid-wizard (W3 #F.3, NR-07): user with valid JWT cookie navigating to `/onboarding` after closing tab mid-wizard — `state_reconstruction.build_state_from_conversation` hydrates from `nikita.conversation_jsonb`; FE renders last assistant message + correct `progress_pct`; NO redirect to `/auth/confirm`. Edge case: cookie valid but `conversation_jsonb` empty/null → render 'fresh start' UI (slot 1), do NOT redirect-loop. (Closes auth-validator MEDIUM-2.) | MED |
| **A1.13** | All outbound `SignupHandler` messages containing a `nikita-mygirl.com` URL set `disable_web_page_preview=True`. Verified by `test_disable_web_page_preview_on_all_signup_messages`. (Tightens A1.7; closes auth-validator MEDIUM-4.) | MED |
| **A1.14** | A1.8 destructive-purge guard: wrong OTP MUST NOT delete `pending_signup_session` row, MUST NOT decrement `code_attempts_remaining` past 0 silently, MUST NOT clear `magic_link_token` if already issued. Test: `test_wrong_otp_does_not_destroy_session`. If current code violates → file as HIGH issue (escalates #437). (Tightens auth-validator MEDIUM-1.) | MED |

## Critical Files

| File | Change | Notes |
|------|--------|-------|
| `nikita/api/routes/telegram.py:635-666` | EDIT | Remove `payload == "welcome"` literal gate for unbound users; bare `/start` AND `/start welcome` both enter `SignupHandler.handle_welcome` |
| `nikita/platforms/telegram/commands.py:343-348` | EDIT (delete or refactor) | `_send_bare_portal_auth_link` becomes unused for unbound `/start`. If `/start <other-payload>` still uses it (deep-links from referrals), keep but rename for clarity |
| `nikita/platforms/telegram/signup_handler.py` | VERIFY (no edit expected) | Existing FSM unchanged: states UNKNOWN → AWAITING_EMAIL → CODE_SENT → MAGIC_LINK_SENT |
| `tests/platforms/telegram/test_routing.py` | NEW | Bare `/start` unbound, bare `/start` bound, `/start welcome` payload, mid-flow `/start` re-trigger |
| `tests/api/routes/test_portal_auth.py` | EDIT | Add `test_idempotent_magic_link_click` per AC A1.9 |

## Implementation Notes

The patch is a small predicate change in `receive_webhook`:

```python
# BEFORE (lines 635-659)
if cmd == "start" and payload == "welcome" and is_unbound:
    await _run_signup_with_fresh_session(..., "welcome", ...)
    return

# AFTER
if cmd == "start" and is_unbound:                        # accept bare AND welcome payload
    entry_point = payload or "welcome"                   # default to welcome semantics
    await _run_signup_with_fresh_session(..., entry_point, ...)
    return
```

`_handle_start` E1 path (commands.py:343-348) is kept for legacy reasons but is no longer reachable from `/start` for unbound users. If grep shows it's only called from this one path, delete + remove the E1 branch from `_handle_start`.

## Tests to Write

1. `test_bare_start_unbound_enters_signup_handler` — mock unbound update, assert `SignupHandler.handle_welcome` called.
2. `test_welcome_payload_unbound_enters_signup_handler` — `/start welcome`, assert same handler.
3. `test_bare_start_bound_uses_command_handler` — bound `telegram_id`, assert `CommandHandler.handle` called and FSM NOT invoked.
4. `test_handle_start_e1_path_not_called_for_unbound_start` — regression guard.
5. `test_otp_state_transition` — DB-backed integration: webhook `text="123456"` after `awaiting_email` → `magic_link_sent` + `magic_link_token` non-null.
6. `test_idempotent_magic_link_click` — same token_hash twice → 1st 200 + cookie set, 2nd 400 OR 302 to /dashboard.
7. `test_disable_web_page_preview_on_magic_link_reply` — assert outgoing message has `disable_web_page_preview=True`.

## Test Identity (W4 walk)

W4 walk uses `simon.yang.ch+spec216walk@gmail.com`. Pre-walk verification: backend email-validation regex MUST accept `+`-aliased addresses. Asserted by `tests/platforms/telegram/test_signup_handler.py::test_plus_alias_email_accepted`. (Closes auth-validator MEDIUM-3.)

## Out of Scope (explicit)

- **Rate limiting on bare `/start`**: deferred. Telegram Bot API enforces ~1 msg/sec per chat, providing implicit throttle. (Documented per auth-validator LOW-2.)
- **`signup_state='completed'` transition trigger + cleanup**: inherited from Spec 215 docs. (Documented per auth-validator LOW-1.)

## Open Questions

- **Q1**: Should `_send_bare_portal_auth_link` be fully deleted, or kept for non-`start` deep-link payloads (e.g., a future `/start ref:abc` referral flow)? **Resolved 2026-04-29**: keep the function + restrict to non-`/start` deep-link payloads only. Add explicit guard in callers.
- **Q2**: Mid-flow `/start` re-trigger semantics — per `live-testing-protocol.md` §"Edge: bare `/start` after partial signup", current behavior should be DOCUMENTED. Decide: reset OR resume? **Resolved 2026-04-29**: resume from current `signup_state` if row exists; document in 216-A regression test.

## References

- Master spec FR-01, FR-11, NR-07
- `nikita/api/routes/telegram.py:501,624,635-666,672-699`
- `nikita/platforms/telegram/commands.py:271,343-348`
- `nikita/platforms/telegram/signup_handler.py` (FSM, 558 lines)
- W3 walk findings #440, #445
- `.claude/rules/live-testing-protocol.md` §12-step protocol

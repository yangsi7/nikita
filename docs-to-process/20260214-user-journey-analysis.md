# User Journey Analysis — Nikita Repository

**Date**: 2026-02-14
**Source**: journey-reviewer agent, verified by devils-advocate
**Method**: Step-by-step code path tracing with file:line references

---

## Summary

| # | Journey | Result | Bugs Found |
|---|---------|--------|------------|
| 1 | New User Signup | PASS | None |
| 2 | Normal Gameplay Message | PASS | None |
| 3 | Boss Encounter | **FAIL** | BUG-BOSS-1: UserRepository() no session — ALL outcomes crash |
| 4 | Game-Over via Decay | PASS | Note: no user notification |
| 5 | Game-Over via Engagement | **FAIL** | BACK-01: set_game_status() doesn't exist |
| 6 | Game-Over via Conflict | **FAIL** | BreakupManager never wired — dead code path |
| 7 | Game Restart | PASS | None |
| 8 | Portal Delete Account | **FAIL** | FRONT-01: missing ?confirm=true |
| 9 | Voice Call Lifecycle | PASS | None |
| 10 | Admin Journey | PASS | Note: role check mismatch |

**Pass Rate**: 6/10 (60%)
**Critical Failures**: 4 journeys broken (boss, engagement game-over, conflict breakup, account deletion)

---

## Journey 1: New User Signup — PASS

| Step | File:line | Status |
|------|-----------|--------|
| Webhook entry | `telegram.py:508` | PASS |
| /start command routing | `telegram.py:598-605` | PASS |
| Email input prompt | `commands.py:82-159` | PASS |
| Email validation | `telegram.py:644-653` | PASS |
| OTP send via Supabase | `registration_handler.py:72-78` | PASS |
| OTP verification | `telegram.py:617-626` | PASS |
| Onboarding flow | `telegram.py:680-726` | PASS |
| First message routing | `telegram.py:667-677` | PASS |

---

## Journey 2: Normal Gameplay — PASS

| Step | File:line | Status |
|------|-----------|--------|
| Auth check | `message_handler.py:134-145` | PASS |
| Profile gate | `message_handler.py:149-154` | PASS |
| Game status gate | `message_handler.py:158-171` | PASS |
| Rate limit | `message_handler.py:175-180` | PASS |
| Conversation tracking | `message_handler.py:183-198` | PASS |
| LLM call | `message_handler.py:214-220` | PASS |
| Scoring + boss check | `message_handler.py:253-259` | PASS |
| Text patterns | `message_handler.py:267` | PASS |
| Delivery | `message_handler.py:284-289` | PASS |
| Pipeline (async) | `tasks.py:624-759` | PASS |

---

## Journey 3: Boss Encounter — FAIL

| Step | File:line | Status | Notes |
|------|-----------|--------|-------|
| Score threshold trigger | `message_handler.py:496-507` | PASS | |
| Set boss_fight status | `message_handler.py:503` | PASS | |
| Boss opening message | `message_handler.py:525-545` | PASS | |
| Boss response routing | `message_handler.py:158-163` | PASS | |
| LLM judgment | `message_handler.py:772-777` | PASS | |
| Process outcome | `message_handler.py:785-788` | **FAIL** | `boss_state_machine.process_outcome()` → `_get_user_repo()` → `UserRepository()` NO SESSION |
| Advance chapter (pass) | `boss.py:159-166` | **FAIL** | Crash: TypeError missing session |
| Increment attempts (fail) | `boss.py:183-192` | **FAIL** | Crash: TypeError missing session |

**Root Cause**: `boss.py:142` — `_get_user_repo()` returns `UserRepository()` without `session` argument.

---

## Journey 4: Decay Game-Over — PASS

| Step | File:line | Status |
|------|-----------|--------|
| pg_cron trigger | `tasks.py:177-240` | PASS |
| Get active users | `processor.py:114` | PASS |
| Calculate decay | `processor.py:87-88` | PASS |
| Apply decay | `processor.py:92` | PASS |
| Game over check | `processor.py:95-96` | PASS |
| Set game_over | `processor.py:139-140` | PASS |
| User notification | N/A | MISSING — no Telegram message sent |

---

## Journey 5: Engagement Game-Over — FAIL

| Step | File:line | Status | Notes |
|------|-----------|--------|-------|
| Scoring triggers update | `message_handler.py:511-515` | PASS | |
| State machine update | `message_handler.py:1042-1048` | PASS | |
| Check point_of_no_return | `message_handler.py:1065-1068` | PASS | |
| Game over detected | `message_handler.py:1070-1075` | PASS | |
| Handle game over | `message_handler.py:1207-1259` | **FAIL** | `set_game_status()` doesn't exist |
| Method resolution | `user_repository.py` | **FAIL** | Only `update_game_status()` at line 333 |

**Note**: Caught by try/except at line 1077 — message flow continues but game_over never set.

---

## Journey 6: Conflict Game-Over — FAIL

| Step | File:line | Status | Notes |
|------|-----------|--------|-------|
| ConflictStage in pipeline | `conflict.py:37-78` | PASS | Detects 4 conflict states |
| Sets ctx flags | `conflict.py:60-61` | PASS | |
| BreakupManager | `breakup.py:67` | EXISTS | Has check_threshold() at line 132 |
| Pipeline → BreakupManager | N/A | **FAIL** | Never imported or called |
| Conflict → game_over | N/A | **FAIL** | No code path exists |

**Root Cause**: BreakupManager is dead code — never connected to pipeline or message handler.

---

## Journey 7: Game Restart — PASS

| Step | File:line | Status |
|------|-----------|--------|
| /start after game_over | `commands.py:99-108` | PASS |
| Reset game state | `commands.py:123-128` | PASS |
| Full state reset | `user_repository.py:361-423` | PASS |
| Fresh onboarding | `commands.py:130-138` | PASS |
| Welcome message | `commands.py:140-143` | PASS |

---

## Journey 8: Portal Delete Account — FAIL

| Step | File:line | Status | Notes |
|------|-----------|--------|-------|
| Settings page | `settings/page.tsx:124` | PASS | |
| Hook mutation | `use-settings.ts:35-36` | PASS | |
| API call | `portal.ts:30` | **FAIL** | No `?confirm=true` |
| Backend check | `portal.py:504-508` | PASS | Returns 400 without confirm |

**Fix**: `portal.ts:30` → `api.delete<void>("/portal/account?confirm=true")`

---

## Journey 9: Voice Call — PASS

| Step | File:line | Status |
|------|-----------|--------|
| Signed URL / inbound | `voice.py:185` | PASS |
| Server tools during call | `server_tools.py` | PASS |
| Call end webhook | `voice.py:721-742` | PASS |
| Conversation created | `voice.py:626` | PASS |
| Scoring | `voice.py:647-715` | PASS |
| Pipeline trigger | `voice.py:725-742` | PASS |
| pg_cron backup | `tasks.py:624-759` | PASS |

---

## Journey 10: Admin — PASS

| Step | File:line | Status | Notes |
|------|-----------|--------|-------|
| Frontend middleware | `middleware.ts:47-52` | PASS | Checks user_metadata.role |
| Backend auth | `auth.py:118-144` | PASS | Checks email domain |
| Admin routes | `admin.py:81` | PASS | All use Depends(get_current_admin_user_id) |

**Note**: Frontend/backend use different auth mechanisms (metadata vs email). Not a security hole but confusing if config drifts.

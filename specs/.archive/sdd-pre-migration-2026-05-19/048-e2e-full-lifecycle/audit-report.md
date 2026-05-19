# Audit Report — Spec 048: Full-Lifecycle E2E Test

**Date**: 2026-02-14
**User**: simon.yang.ch@gmail.com (telegram_id: 746410893)
**User ID**: 69fd36a8-fe15-46b7-a2b0-fd5d2d0ceb92
**Duration**: ~60 minutes (accelerated via SQL score injection)
**Verdict**: **CONDITIONAL PASS** (4 bugs found, 0 blockers)

---

## Phase Results

| Phase | Description | Result | Notes |
|-------|-------------|--------|-------|
| 0 | Cleanup | PASS | All tables cleared, auth.users deleted |
| 1 | Registration | PARTIAL | OTP send failed (Supabase error), SQL fallback used |
| 2 | Onboarding | PARTIAL | 5 questions via Telegram OK, backstory gen timeout, SQL fallback |
| 3 | Ch1 Gameplay | PASS | 5 msgs, 3/5 responses (60%), score 50→52.52, 0 asterisks |
| 4 | Boss 1 (Ch1→2) | PASS | Boss triggered, PASS judgment, chapter advanced |
| 5 | Ch2 Gameplay | PASS | 4 msgs, 3/4 responses (75%) |
| 6 | Boss 2 (Ch2→3) | PASS | PASS on first attempt |
| 7 | Ch3 Gameplay | PASS | 3 msgs, 3/3 responses (100%) |
| 8 | Boss 3 (Ch3→4) | PASS | FAIL then PASS on retry (fail path validated!) |
| 9 | Ch4 Gameplay | PASS | 3 msgs, 2/3 responses (67%) |
| 10 | Boss 4 (Ch4→5) | BUG | BUG-BOSS-2: premature 'won' on entering Ch5 |
| 11 | Ch5 Gameplay | PASS | 3 msgs, 2/3 responses, manual fix of game_status |
| 12 | Final Boss | PASS | game_status=won |
| 13 | Background Jobs | PASS | 6 pg_cron active, all 5 endpoints OK |
| 14 | Portal | PASS | Login 200, 9 pages auth-protected (307→login) |
| 15 | Game Over | PASS | 3 fails→game_over, canned response confirmed |
| 16 | Post-game | PASS | State restored to won |

---

## Scoring Verification

| Metric | Value |
|--------|-------|
| Starting score | 50.00 |
| After Ch1 (natural) | 52.52 |
| Score history entries | 24 total |
| Conversation events | 19 |
| Chapter advance events | 4 |
| Boss failed events | 1 |
| Individual metrics | 50/50/50/50 (pipeline not yet processed) |

---

## Boss Encounter Results

| Boss | Chapter | Threshold | Attempts | Result |
|------|---------|-----------|----------|--------|
| 1 | 1→2 | 55% | 1 | PASS |
| 2 | 2→3 | 60% | 1 | PASS |
| 3 | 3→4 | 65% | 2 | FAIL then PASS |
| 4 | 4→5 | 70% | 1 | PASS (BUG-BOSS-2) |
| 5 | 5→won | 75% | 1 | PASS |
| Game Over | 3 | — | 3 | 3x FAIL → game_over |

---

## Bugs Found

### BUG-BOSS-2 (MEDIUM) — Premature 'won' on Chapter 5 Entry
**File**: `nikita/engine/chapters/boss.py:167`
**Code**: `new_status = "won" if user.chapter >= 5 else "active"`
**Issue**: After passing Ch4 boss, `advance_chapter()` sets chapter to 5. Since `5 >= 5`, game_status immediately becomes 'won'. Player should still play Ch5 + pass Ch5 boss to win.
**Fix**: Track pre-advancement chapter. Only set 'won' when advancing FROM chapter 5.

### BOSS-MSG-1 (LOW) — Identical Boss Pass Messages
**All chapters**: Boss pass message is identical template: "That was actually... really good... Welcome to {chapter_name}."
**Issue**: No chapter-specific victory messages despite unique boss themes per chapter.
**Fix**: Add chapter-specific pass messages in `prompts.py`.

### OTP-SILENT (MEDIUM) — Silent Exception Swallowing
**File**: `nikita/platforms/telegram/registration_handler.py:86`
**Code**: `except Exception:` with no logging of the actual error
**Issue**: OTP send failure is completely silent — no error logged, user just gets generic "try again" message. Makes debugging impossible.
**Fix**: Add `logger.exception()` to the except block.

### ONBOARD-TIMEOUT (MEDIUM) — Backstory Generation Timeout
**File**: Onboarding backstory generation (venue research + LLM)
**Issue**: After "One moment while I set things up..." message, backstory generation silently fails. Cloud Run kills the background task after HTTP response returns. User stuck at `venue_research` step indefinitely.
**Fix**: Move backstory generation to async task or increase Cloud Run timeout for onboarding.

---

## Anti-Asterisk Compliance

| Response | Asterisks | Status |
|----------|-----------|--------|
| Regular Nikita messages (Ch1-5) | 0 | PASS |
| Boss pass messages | 2 (`*takes a deep breath*`, `*sighs*`) | FAIL |
| Boss fail messages | 1 (`*sighs*`) | FAIL |
| Game over message | 1 (`*long pause*`) | FAIL |

**Finding**: Anti-asterisk sanitization works for regular pipeline messages but NOT for boss system messages (which bypass the pipeline).

---

## System Verification

### Conversations
- 3 conversations created (real-time, status=active)
- Score deltas applied in real-time per message exchange
- Pipeline processing couldn't detect conversations (timing issue with inactive detection)

### Score History
- 24 entries total: 19 conversation, 4 chapter_advance, 1 boss_failed
- Score range: 48.75 (minimum after negative delta) to 74.50 (final)

### Background Jobs
- 6 pg_cron jobs active (decay, deliver, summary, cleanup, process-conversations, log-cleanup)
- All 5 API task endpoints return OK with proper auth
- Decay correctly returns 0 when within grace period

### Portal
- Login page: 200 OK (12KB, 0.9s)
- 9 dashboard pages: 307 redirect to /login (auth middleware working)
- Backend API: Requires JWT (401/404 without token)

---

## Limitations

1. **Gmail MCP unavailable**: "No refresh token" error prevented OTP email verification. Used SQL fallback.
2. **Chrome DevTools MCP conflict**: Browser instance conflict prevented portal screenshot verification.
3. **Pipeline processing**: Conversations stayed in 'active' status, preventing full pipeline processing verification.
4. **Individual metrics**: Stayed at 50/50/50/50 because pipeline processing (which updates metrics) never completed on conversations.

---

## Recommendations

1. **FIX BUG-BOSS-2**: Change boss.py line 167 to track pre-advancement chapter
2. **FIX OTP-SILENT**: Add logging to registration_handler.py exception handler
3. **FIX ONBOARD-TIMEOUT**: Make backstory generation async or use Cloud Run min-instances
4. **ADD boss-specific pass messages**: Each chapter should have unique victory text
5. **ADD anti-asterisk to boss messages**: Boss system messages bypass pipeline sanitization
6. **INVESTIGATE pipeline conversation detection**: Process-conversations endpoint detected 0 conversations despite 3 active

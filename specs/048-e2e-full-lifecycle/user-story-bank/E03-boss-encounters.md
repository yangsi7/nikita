# E03: Boss Encounters (30 scenarios)

> Epic: E03 | User Stories: 5 | Priority: P0=9, P1=11, P2=8, P3=2
> MCP Tools: Supabase MCP, Telegram MCP
> Source files: boss.py, judgment.py, message_handler.py, constants.py

---

## US-3.1: Boss Trigger
### MCP Tools: Supabase MCP, Telegram MCP

Scenario: S-3.1.1 - Score crosses threshold, boss triggered [P0-Critical]
  Given a user in chapter=1 with relationship_score=54
  When a positive interaction raises the score to 56 (above threshold 55)
  Then game_status is set to "boss_fight"
  And a boss encounter message is sent to the user via Telegram
  And the boss prompt matches chapter 1 (Curiosity)
  # Verify: Supabase MCP -> game_status = "boss_fight"
  # Verify: constants.py BOSS_THRESHOLDS[1] = Decimal("55.00")
  # Verify: Telegram MCP -> boss opening message sent

Scenario: S-3.1.2 - Score below threshold, no boss trigger [P1-High]
  Given a user in chapter=2 with relationship_score=58
  When an interaction keeps the score below 60 (threshold for Ch2)
  Then game_status remains "active"
  And no boss encounter is initiated
  # Verify: Supabase MCP -> game_status = "active"
  # Verify: BOSS_THRESHOLDS[2] = Decimal("60.00")

Scenario: S-3.1.3 - Boss trigger during active conversation [P2-Medium]
  Given a user is mid-conversation with Nikita
  When their score crosses the boss threshold
  Then the current conversation flow transitions to boss mode
  And the boss opening message follows the regular response
  # Verify: message_handler.py routes to boss handling when game_status = "boss_fight"

Scenario: S-3.1.4 - Boss trigger after decay reversal [P2-Medium]
  Given a user whose score decayed to 53 but recovers to 56 via good messages
  When the score re-crosses the threshold at 55
  Then a new boss encounter is triggered (not suppressed by prior crossing)
  # Verify: boss trigger logic checks current score vs threshold, not history

Scenario: S-3.1.5 - Boss threshold exact boundary [P2-Medium]
  Given a user in chapter=3 with score exactly 65.00
  When the scoring check runs
  Then the boss is triggered (threshold is >= not >)
  # Verify: calculator.py:207 boss_threshold = BOSS_THRESHOLDS[chapter]

Scenario: S-3.1.6 - Already in boss_fight state, no double trigger [P1-High]
  Given a user with game_status="boss_fight"
  When score changes occur (from prior queued interactions)
  Then no second boss encounter is triggered
  And messages are routed to _handle_boss_response()
  # Verify: message_handler.py:175 checks if game_status == "boss_fight" first

---

## US-3.2: Boss Fight
### MCP Tools: Telegram MCP, Supabase MCP

Scenario: S-3.2.1 - Boss opening message per chapter [P1-High]
  Given a user enters boss_fight in chapter=2
  When the boss encounter begins
  Then the opening message matches the chapter 2 boss prompt
  And the message sets up the challenge/success criteria
  # Verify: chapters/prompts.py BOSS_PROMPTS[2] for chapter-specific content

Scenario: S-3.2.2 - Player quality response -> PASS judgment [P0-Critical]
  Given a user in boss_fight for chapter=1
  When the user sends a thoughtful, emotionally engaged response
  Then BossJudgment.judge_boss_outcome() returns PASS
  And process_pass() is called
  # Verify: judgment.py uses LLM (Claude Sonnet) to evaluate
  # Verify: boss.py:140-182 process_pass() logic

Scenario: S-3.2.3 - Player poor response -> FAIL judgment [P0-Critical]
  Given a user in boss_fight for chapter=3
  When the user sends a lazy/dismissive response ("idk lol")
  Then BossJudgment.judge_boss_outcome() returns FAIL
  And process_fail() is called
  And boss_attempts is incremented
  # Verify: judgment.py LLM evaluation
  # Verify: boss.py:184-220 process_fail() increments boss_attempts

Scenario: S-3.2.4 - Boss judgment timeout [P2-Medium]
  Given a user sends their boss response
  When the LLM judgment call takes longer than expected
  Then a typing indicator is shown during evaluation
  And the judgment eventually completes (120s LLM timeout)
  # Verify: message_handler.py:783 sends typing indicator
  # Verify: LLM timeout = 120s (Spec 036 fix)

Scenario: S-3.2.5 - Response during boss_fight routed correctly [P1-High]
  Given a user with game_status="boss_fight"
  When the user sends any text message
  Then it is routed to _handle_boss_response() (not normal flow)
  And regular scoring pipeline is skipped
  # Verify: message_handler.py:175 routes boss_fight to _handle_boss_response

Scenario: S-3.2.6 - Non-text message during boss_fight [P3-Low]
  Given a user in boss_fight sends a sticker or image
  When the webhook processes the non-text message
  Then it is handled gracefully (no crash)
  And the user is prompted to respond with text
  # Verify: No 500 error in Cloud Run logs

---

## US-3.3: Boss Pass
### MCP Tools: Supabase MCP, Telegram MCP

Scenario: S-3.3.1 - Chapter 1 boss pass -> advance to Chapter 2 [P0-Critical]
  Given a user in chapter=1, boss_fight, passes the boss
  When process_pass() executes
  Then user.chapter advances to 2
  And game_status is set to "active"
  And boss_attempts is reset to 0
  And the Chapter 1 boss pass message is sent (Curiosity -> Intrigue)
  # Verify: Supabase MCP -> chapter = 2, game_status = "active", boss_attempts = 0
  # Verify: message_handler.py:869-876 BOSS_PASS_MESSAGES[1]
  # Verify: Telegram MCP -> message contains "You've got my attention"

Scenario: S-3.3.2 - Chapter 2 boss pass -> advance to Chapter 3 [P1-High]
  Given a user in chapter=2, boss_fight, passes the boss
  When process_pass() executes
  Then user.chapter advances to 3
  And the Chapter 2 pass message is sent (Intrigue -> Investment)
  # Verify: Supabase MCP -> chapter = 3, boss_attempts = 0
  # Verify: message_handler.py:877-884 BOSS_PASS_MESSAGES[2]

Scenario: S-3.3.3 - Chapter 3 boss pass -> advance to Chapter 4 [P1-High]
  Given a user in chapter=3, boss_fight, passes the boss
  When process_pass() executes
  Then user.chapter advances to 4
  And the Chapter 3 pass message is sent (Investment -> Intimacy)
  # Verify: Supabase MCP -> chapter = 4
  # Verify: message_handler.py:885-891 BOSS_PASS_MESSAGES[3]

Scenario: S-3.3.4 - Chapter 4 boss pass -> advance to Chapter 5, STILL ACTIVE [P0-Critical]
  Given a user in chapter=4, boss_fight, passes the boss
  When process_pass() executes
  Then user.chapter advances to 5
  And game_status is "active" (NOT "won" - BUG-BOSS-2 fix)
  And old_chapter was 4 (< 5), so new_status = "active"
  # Verify: boss.py:164-175 captures old_chapter BEFORE advance_chapter()
  # Verify: boss.py:175 "won" if old_chapter >= 5 else "active"
  # Verify: Supabase MCP -> chapter = 5, game_status = "active"

Scenario: S-3.3.5 - Chapter 5 final boss pass -> game WON [P0-Critical]
  Given a user in chapter=5, boss_fight, passes the final boss
  When process_pass() executes
  Then old_chapter = 5, advance_chapter() caps at 5
  And game_status is set to "won" (old_chapter >= 5)
  And the victory message is sent (BOSS_PASS_MESSAGES[5])
  # Verify: boss.py:175 new_status = "won" because old_chapter = 5
  # Verify: Supabase MCP -> game_status = "won"
  # Verify: message_handler.py:900-907 victory message "YOU'RE STILL HERE"
  # Verify: Telegram MCP -> victory celebration message

Scenario: S-3.3.6 - Chapter-specific victory messages (BOSS-MSG-1 fix) [P1-High]
  Given boss passes occur across chapters 1 through 5
  When each boss pass message is sent
  Then each chapter has a unique congratulatory message (not the same template)
  And message_handler.py BOSS_PASS_MESSAGES dict has 5 distinct entries
  # Verify: message_handler.py:869-908 has 5 unique messages keyed by chapter
  # Verify: Ch1 "got my attention", Ch2 "surprised me", Ch3 "trust you", Ch4 "new territory", Ch5 "won me"

---

## US-3.4: Boss Fail
### MCP Tools: Supabase MCP, Telegram MCP

Scenario: S-3.4.1 - First boss fail -> boss_attempts=1 [P0-Critical]
  Given a user in boss_fight with boss_attempts=0
  When the boss judgment returns FAIL
  Then boss_attempts is incremented to 1
  And game_status remains "boss_fight"
  And a fail message is sent indicating remaining attempts
  # Verify: boss.py:208 increment_boss_attempts()
  # Verify: Supabase MCP -> boss_attempts = 1, game_status = "boss_fight"
  # Verify: message_handler.py:828-833 _send_boss_fail_message

Scenario: S-3.4.2 - Second boss fail -> boss_attempts=2 [P1-High]
  Given a user in boss_fight with boss_attempts=1
  When the boss judgment returns FAIL again
  Then boss_attempts is incremented to 2
  And game_status remains "boss_fight"
  And the fail message warns this is the last chance
  # Verify: Supabase MCP -> boss_attempts = 2

Scenario: S-3.4.3 - Third boss fail -> GAME OVER [P0-Critical]
  Given a user in boss_fight with boss_attempts=2
  When the boss judgment returns FAIL a third time
  Then boss_attempts is incremented to 3
  And game_status is set to "game_over" (3 strikes rule)
  And the game-over message is sent
  # Verify: boss.py:210 game_over = user.boss_attempts >= 3
  # Verify: boss.py:213-214 update_game_status("game_over")
  # Verify: Supabase MCP -> game_status = "game_over", boss_attempts = 3
  # Verify: message_handler.py:824-826 _send_game_over_message

Scenario: S-3.4.4 - Score penalty on boss fail [P2-Medium]
  Given a user fails a boss encounter
  When the fail is processed
  Then a score penalty is applied (logged in score_history)
  And the penalty does not bring score below 0
  # Verify: Supabase MCP -> score_history with event_type = "boss_fail" and delta < 0

Scenario: S-3.4.5 - Boss attempts persist across conversations [P1-High]
  Given a user failed boss once (boss_attempts=1) and conversation expired
  When the boss is re-triggered in a new conversation
  Then boss_attempts still equals 1 (not reset)
  And the next fail would bring it to 2
  # Verify: Supabase MCP -> boss_attempts = 1 persists in app_users table
  # Verify: boss_attempts only resets on pass (boss.py:181)

Scenario: S-3.4.6 - Fail then pass on retry [P1-High]
  Given a user in boss_fight with boss_attempts=1
  When the user sends a quality response and boss judgment returns PASS
  Then process_pass() advances the chapter
  And boss_attempts resets to 0
  And game_status returns to "active"
  # Verify: boss.py:169 advance_chapter(), :181 boss_attempts reset
  # Verify: Supabase MCP -> boss_attempts = 0, chapter incremented

---

## US-3.5: Boss Timeout
### MCP Tools: Supabase MCP

Scenario: S-3.5.1 - Boss timeout after 24h with no response [P1-High]
  Given a user in boss_fight who has not responded for 24 hours
  When the boss timeout check runs (via /tasks/boss-timeout endpoint)
  Then game_status is reset from "boss_fight" to "active"
  And a timeout penalty may be applied to score
  # Verify: Spec 049 boss timeout endpoint
  # Verify: Supabase MCP -> game_status = "active" after timeout

Scenario: S-3.5.2 - Timeout resets state to active [P1-High]
  Given a boss encounter timed out
  When the user sends a new message
  Then they are in "active" state (not boss_fight)
  And normal gameplay resumes
  # Verify: message_handler.py routes active users to normal flow

Scenario: S-3.5.3 - Timeout with score penalty [P2-Medium]
  Given a user in boss_fight times out
  When the timeout processor runs
  Then a small score penalty is logged in score_history
  And event_type = "boss_timeout"
  # Verify: Supabase MCP -> score_history entry with event_type = "boss_timeout"

Scenario: S-3.5.4 - Timeout in each chapter [P2-Medium]
  Given a user times out of a boss fight in chapter 3
  When timeout is processed
  Then user remains in chapter 3 (no advancement or demotion)
  And boss_attempts is incremented (counts as a "use" of an attempt)
  # Verify: Supabase MCP -> chapter = 3 unchanged

Scenario: S-3.5.5 - Timeout with exactly 3 prior attempts -> game_over [P1-High]
  Given a user in boss_fight with boss_attempts=2 who times out
  When the timeout increments boss_attempts to 3
  Then game_status is set to "game_over" (3 strikes reached)
  # Verify: Supabase MCP -> game_status = "game_over", boss_attempts = 3

Scenario: S-3.5.6 - Boss re-trigger after timeout [P2-Medium]
  Given a user whose boss fight timed out and returned to active
  When their score re-crosses the boss threshold
  Then a new boss encounter is triggered (boss_attempts carries over)
  # Verify: Supabase MCP -> game_status = "boss_fight" again, boss_attempts unchanged

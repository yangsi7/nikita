# E11: Terminal States (14 scenarios)

> Epic: E11 | User Stories: 3 | Priority: P0=6, P1=4, P2=2, P3=0
> MCP Tools: Supabase MCP, Telegram MCP
> Source files: boss.py, processor.py, message_handler.py, commands.py, portal.py

---

## US-11.1: Game Over
### MCP Tools: Supabase MCP, Telegram MCP

```gherkin
Scenario: S-11.1.1 - Game over from decay to score 0 [P0-Critical]
  Given a user with relationship_score close to 0 and expired grace period
  When decay reduces the score to 0
  Then game_status is set to "game_over"
  And a game-over notification may be sent via Telegram
  # Verify: Supabase MCP → relationship_score = 0, game_status = "game_over"
  # Verify: processor.py triggers game_over when score hits 0

Scenario: S-11.1.2 - Game over from 3 boss fails [P0-Critical]
  Given a user with boss_attempts=2 in boss_fight
  When they fail the boss a third time
  Then game_status is set to "game_over" via process_fail()
  And the game-over message is sent: "I'm sorry, but we're not talking anymore..."
  # Verify: boss.py:210-214 game_over on 3rd fail
  # Verify: message_handler.py:854-859 game_over message text

Scenario: S-11.1.3 - Canned response for game_over user messages [P0-Critical]
  Given a user with game_status="game_over"
  When they send any message to @Nikita_my_bot
  Then they receive the canned response: "I'm sorry, but we're not talking anymore. You had your chances... Maybe in another life."
  And no scoring, pipeline, or AI generation occurs
  # Verify: message_handler.py:183 routes to _send_game_status_response
  # Verify: message_handler.py:854-859 canned game_over text
  # Verify: Telegram MCP → canned response text

Scenario: S-11.1.4 - Portal shows game_over state [P1-High]
  Given a user with game_status="game_over"
  When they access the portal dashboard
  Then the dashboard displays the game-over state
  And final score, chapter reached, and stats are shown
  # Verify: Portal API → GET /api/v1/portal/stats includes game_status = "game_over"

Scenario: S-11.1.5 - No scoring or decay for game_over users [P0-Critical]
  Given a user with game_status="game_over"
  When scoring or decay jobs run
  Then the user is completely skipped
  And no score_history entries are created
  # Verify: processor.py:21 SKIP_STATUSES includes "game_over"
  # Verify: Pipeline skips terminal-state users (Spec 049 terminal filter)
```

---

## US-11.2: Won
### MCP Tools: Supabase MCP, Telegram MCP

```gherkin
Scenario: S-11.2.1 - Won after chapter 5 boss pass [P0-Critical]
  Given a user in chapter=5, boss_fight
  When they pass the final boss
  Then game_status is set to "won" (old_chapter >= 5)
  And the victory message is sent (random from WON_MESSAGES for future msgs)
  And the initial pass message is BOSS_PASS_MESSAGES[5]
  # Verify: boss.py:175 new_status = "won" if old_chapter >= 5
  # Verify: message_handler.py:900-907 Ch5 victory message

Scenario: S-11.2.2 - Continued conversation after won [P1-High]
  Given a user with game_status="won"
  When they send a message to @Nikita_my_bot
  Then they receive a "won" variant message (random from WON_MESSAGES)
  And no scoring occurs (terminal state)
  # Verify: message_handler.py:183 checks game_status in ("game_over", "won")
  # Verify: message_handler.py:860-862 WON_MESSAGES random selection

Scenario: S-11.2.3 - No decay or bosses after won [P0-Critical]
  Given a user with game_status="won"
  When decay jobs, boss triggers, or scoring run
  Then all are skipped for this user
  And score remains frozen at final value
  # Verify: processor.py:21 SKIP_STATUSES includes "won"

Scenario: S-11.2.4 - Portal shows won state with victory stats [P1-High]
  Given a user with game_status="won"
  When they access the portal dashboard
  Then the dashboard displays victory celebration
  And shows total messages, time played, final score, chapters cleared
  # Verify: Portal API → GET /api/v1/portal/stats includes game_status = "won"

Scenario: S-11.2.5 - Won state persists across sessions [P1-High]
  Given a user who won and hasn't interacted for 30 days
  When they return and send a message
  Then game_status is still "won" (not reset)
  And they receive a won-state response
  # Verify: Supabase MCP → game_status = "won" persists indefinitely
```

---

## US-11.3: Account Recovery
### MCP Tools: Supabase MCP, Telegram MCP

```gherkin
Scenario: S-11.3.1 - New account after game_over via /start [P0-Critical]
  Given a user with game_status="game_over"
  When they send /start and complete re-registration
  Then their game data is reset: relationship_score=50, chapter=1, boss_attempts=0
  And onboarding may be re-run (fresh start)
  And game_status is set to "active"
  # Verify: commands.py:106-123 handles game_over re-start
  # Verify: Supabase MCP → reset values after re-registration

Scenario: S-11.3.2 - Email reuse after account deletion [P2-Medium]
  Given a user deleted their account via the portal
  When they create a new account with the same email
  Then a fresh user record is created
  And no data from the deleted account leaks into the new account
  # Verify: Supabase MCP → auth.users new UUID, no old data

Scenario: S-11.3.3 - Portal account deletion flow [P1-High]
  Given a user accesses Settings in the portal
  When they click "Delete Account" and confirm (?confirm=true)
  Then their user data is soft-deleted or fully removed
  And Supabase auth record is cleaned up
  And they are logged out of the portal
  # Verify: Portal API → DELETE /api/v1/portal/account?confirm=true
  # Verify: Spec 050 FRONT-01 fix: ?confirm=true required

Scenario: S-11.3.4 - Data cleanup after deletion [P2-Medium]
  Given a user's account has been deleted
  When deletion is processed
  Then conversations, score_history, user_metrics, vice_preferences are removed
  And memory_facts associated with the user are purged
  And the user cannot be found by telegram_id or email
  # Verify: Supabase MCP → SELECT COUNT(*) FROM conversations WHERE user_id = {old_uid} => 0
  # Verify: Supabase MCP → SELECT COUNT(*) FROM score_history WHERE user_id = {old_uid} => 0
```

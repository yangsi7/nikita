# E04: Decay System (18 scenarios)

> Epic: E04 | User Stories: 3 | Priority: P0=6, P1=7, P2=5, P3=0
> MCP Tools: Supabase MCP
> Source files: calculator.py, processor.py, constants.py

---

## US-4.1: Decay Application
### MCP Tools: Supabase MCP

Scenario: S-4.1.1 - Decay applied after grace period expires [P0-Critical]
  Given a user in chapter=1 with last_interaction_at 10 hours ago (grace=8h)
  When the /tasks/decay endpoint runs (hourly via pg_cron)
  Then decay of -0.8% is applied to relationship_score
  And a score_history entry is created with event_type="decay"
  # Verify: Supabase MCP -> score_history WHERE event_type = 'decay' AND user_id = {uid}
  # Verify: constants.py DECAY_RATES[1] = Decimal("0.8")
  # Verify: GRACE_PERIODS[1] = timedelta(hours=8)

Scenario: S-4.1.2 - No decay within grace period [P0-Critical]
  Given a user in chapter=1 with last_interaction_at 5 hours ago (grace=8h)
  When the /tasks/decay endpoint runs
  Then no decay is applied
  And no score_history entry is created for this user
  # Verify: 5h < 8h grace -> skip
  # Verify: Supabase MCP -> no new score_history with event_type = 'decay'

Scenario: S-4.1.3 - Decay rate correct per chapter [P0-Critical]
  Given users in chapters 1 through 5 with expired grace periods
  When the /tasks/decay endpoint runs
  Then Ch1 user loses 0.8%, Ch2 loses 0.6%, Ch3 loses 0.4%, Ch4 loses 0.3%, Ch5 loses 0.2%
  # Verify: DECAY_RATES = {1: 0.8, 2: 0.6, 3: 0.4, 4: 0.3, 5: 0.2}
  # Verify: Supabase MCP -> score_history deltas match per-chapter rates

Scenario: S-4.1.4 - Decay to 0 triggers game_over [P0-Critical]
  Given a user with relationship_score=0.5 and chapter=1 (decay=0.8%)
  When decay reduces the score to 0 (or below, clamped)
  Then relationship_score is set to 0
  And game_status is set to "game_over"
  # Verify: Supabase MCP -> relationship_score = 0, game_status = "game_over"

Scenario: S-4.1.5 - Decay logged in score_history [P1-High]
  Given decay is applied to a user
  When the score_history entry is created
  Then it includes: user_id, old_score, new_score, delta (negative), event_type="decay", timestamp
  # Verify: Supabase MCP -> SELECT * FROM score_history WHERE event_type = 'decay'

Scenario: S-4.1.6 - Multiple users decayed in single batch [P1-High]
  Given 50 active users with expired grace periods
  When /tasks/decay runs with batch_size=100
  Then all 50 users are processed in a single batch
  And the endpoint returns summary: {"processed": 50, "decayed": N, "game_overs": M}
  # Verify: processor.py:42 batch_size=100
  # Verify: API response includes processing summary

---

## US-4.2: Grace Period
### MCP Tools: Supabase MCP

Scenario: S-4.2.1 - Chapter 1: 8-hour grace period [P0-Critical]
  Given a user in chapter=1 with last_interaction_at 7h59m ago
  When the decay check runs
  Then no decay is applied (within 8h grace)
  # Verify: GRACE_PERIODS[1] = timedelta(hours=8)

Scenario: S-4.2.2 - Chapter 2: 16-hour grace period [P1-High]
  Given a user in chapter=2 with last_interaction_at 15h ago
  When the decay check runs
  Then no decay is applied (within 16h grace)
  # Verify: GRACE_PERIODS[2] = timedelta(hours=16)

Scenario: S-4.2.3 - Chapter 3: 24-hour grace period [P1-High]
  Given a user in chapter=3 with last_interaction_at 23h ago
  When the decay check runs
  Then no decay is applied (within 24h grace)
  # Verify: GRACE_PERIODS[3] = timedelta(hours=24)

Scenario: S-4.2.4 - Chapter 4: 48-hour grace period [P1-High]
  Given a user in chapter=4 with last_interaction_at 47h ago
  When the decay check runs
  Then no decay is applied (within 48h grace)
  # Verify: GRACE_PERIODS[4] = timedelta(hours=48)

Scenario: S-4.2.5 - Chapter 5: 72-hour grace period [P1-High]
  Given a user in chapter=5 with last_interaction_at 71h ago
  When the decay check runs
  Then no decay is applied (within 72h grace)
  # Verify: GRACE_PERIODS[5] = timedelta(hours=72)

Scenario: S-4.2.6 - User interaction resets grace timer [P0-Critical]
  Given a user whose grace period expired 2 hours ago
  When the user sends a message (last_interaction_at updated to now())
  Then the grace period resets from the new interaction time
  And the next decay check uses the new last_interaction_at
  # Verify: Supabase MCP -> last_interaction_at updated on message send
  # Verify: Next decay check: time_since = now() - new_last_interaction < grace

---

## US-4.3: Decay Edge Cases
### MCP Tools: Supabase MCP

Scenario: S-4.3.1 - No decay during boss_fight [P0-Critical]
  Given a user with game_status="boss_fight"
  When the decay job runs
  Then the user is skipped (SKIP_STATUSES includes "boss_fight")
  And no score_history decay entry is created
  # Verify: processor.py:21 SKIP_STATUSES = {"boss_fight", "game_over", "won"}
  # Verify: processor.py:64-75 should_skip_user() returns True

Scenario: S-4.3.2 - No decay for game_over users [P1-High]
  Given a user with game_status="game_over"
  When the decay job runs
  Then the user is skipped
  # Verify: processor.py:21 "game_over" in SKIP_STATUSES

Scenario: S-4.3.3 - No decay for won users [P1-High]
  Given a user with game_status="won"
  When the decay job runs
  Then the user is skipped
  # Verify: processor.py:21 "won" in SKIP_STATUSES

Scenario: S-4.3.4 - Exact grace period boundary [P2-Medium]
  Given a user in chapter=1 with last_interaction_at exactly 8h00m00s ago
  When the decay check runs
  Then decay IS applied (time_since >= grace_period, not strictly >)
  # Verify: Boundary condition in calculator.py

Scenario: S-4.3.5 - Decay notification sent to user [P2-Medium]
  Given a user's score drops dangerously low from decay
  When the notify_callback is configured in DecayProcessor
  Then a notification message is sent to the user's Telegram
  And the message warns about relationship decay
  # Verify: processor.py:44 notify_callback parameter (Spec 049 AC-4.1)

Scenario: S-4.3.6 - Rapid back-to-back decay job runs [P2-Medium]
  Given the decay job ran 30 seconds ago
  When it runs again (e.g. manual trigger + pg_cron overlap)
  Then decay is idempotent: only applies if time_since > grace
  And double-decay does not occur (last_interaction_at unchanged between runs)
  # Verify: max_decay_per_cycle = Decimal("20.0") caps single-cycle decay
  # Verify: processor.py:43 safety cap

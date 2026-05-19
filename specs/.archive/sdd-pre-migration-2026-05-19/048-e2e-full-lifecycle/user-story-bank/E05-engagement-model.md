# E05: Engagement Model (22 scenarios)

> Epic: E05 | User Stories: 3 | Priority: P0=5, P1=11, P2=5, P3=1
> MCP Tools: Supabase MCP
> Source files: state_machine.py, enums.py, detection.py, recovery.py

---

## US-5.1: State Transitions
### MCP Tools: Supabase MCP

Scenario: S-5.1.1 - CALIBRATING -> IN_ZONE transition [P0-Critical]
  Given a user with engagement_state="calibrating"
  When the user achieves engagement score >= 0.8 for 3+ consecutive interactions
  Then engagement_state transitions to "in_zone"
  And scoring multiplier changes from 0.9 to 1.0
  # Verify: state_machine.py:16 CALIBRATING -> IN_ZONE: score >= 0.8 for 3+
  # Verify: Supabase MCP -> engagement_state = "in_zone"

Scenario: S-5.1.2 - IN_ZONE -> DRIFTING transition [P0-Critical]
  Given a user with engagement_state="in_zone"
  When the user's engagement score drops below 0.6 for 1+ exchange
  Then engagement_state transitions to "drifting"
  And scoring multiplier changes from 1.0 to 0.8
  # Verify: state_machine.py:18 IN_ZONE -> DRIFTING: score < 0.6 for 1+
  # Verify: enums.py DRIFTING multiplier = 0.8

Scenario: S-5.1.3 - DRIFTING -> CLINGY transition [P1-High]
  Given a user with engagement_state="drifting"
  When the user exhibits clinginess > 0.7 for 2+ consecutive days
  Then engagement_state transitions to "clingy"
  And scoring multiplier drops to 0.5
  # Verify: state_machine.py:20 DRIFTING -> CLINGY: clinginess > 0.7 for 2+ days

Scenario: S-5.1.4 - DRIFTING -> DISTANT transition [P1-High]
  Given a user with engagement_state="drifting"
  When the user's neglect score exceeds 0.6 for 2+ consecutive days
  Then engagement_state transitions to "distant"
  And scoring multiplier drops to 0.6
  # Verify: state_machine.py:21 DRIFTING -> DISTANT: neglect > 0.6 for 2+ days

Scenario: S-5.1.5 - CLINGY -> OUT_OF_ZONE transition [P1-High]
  Given a user with engagement_state="clingy" for 3+ consecutive days
  When clinginess persists without improvement
  Then engagement_state transitions to "out_of_zone"
  And scoring multiplier drops to 0.2
  # Verify: state_machine.py:23 CLINGY -> OUT_OF_ZONE: clingy 3+ consecutive days

Scenario: S-5.1.6 - DISTANT -> OUT_OF_ZONE transition [P1-High]
  Given a user with engagement_state="distant" for 5+ consecutive days
  When distance persists without re-engagement
  Then engagement_state transitions to "out_of_zone"
  And scoring multiplier drops to 0.2
  # Verify: state_machine.py:25 DISTANT -> OUT_OF_ZONE: distant 5+ consecutive days

Scenario: S-5.1.7 - OUT_OF_ZONE -> score reaches 0 -> game_over [P0-Critical]
  Given a user in "out_of_zone" with multiplier 0.2 and low score
  When decay + low scoring pushes score to 0
  Then game_status changes to "game_over"
  And engagement tracking ceases
  # Verify: processor.py handles game_over when score reaches 0

Scenario: S-5.1.8 - Recovery path: OUT_OF_ZONE -> CALIBRATING [P1-High]
  Given a user in "out_of_zone"
  When the user re-engages and a recovery + grace period elapses
  Then engagement_state transitions to "calibrating"
  And multiplier improves from 0.2 to 0.9
  # Verify: state_machine.py:26 OUT_OF_ZONE -> CALIBRATING: recovery + grace period

---

## US-5.2: Scoring Multipliers
### MCP Tools: Supabase MCP

Scenario: S-5.2.1 - IN_ZONE multiplier 1.0 applied [P0-Critical]
  Given a user with engagement_state="in_zone"
  When a positive score delta of +5 is calculated
  Then the applied delta = +5 * 1.0 = +5.0
  # Verify: enums.py:72 IN_ZONE: Decimal("1.0")

Scenario: S-5.2.2 - CALIBRATING multiplier 0.9 applied [P1-High]
  Given a user with engagement_state="calibrating"
  When a positive score delta of +5 is calculated
  Then the applied delta = +5 * 0.9 = +4.5
  # Verify: enums.py:71 CALIBRATING: Decimal("0.9")

Scenario: S-5.2.3 - DRIFTING multiplier 0.8 applied [P1-High]
  Given a user with engagement_state="drifting"
  When a positive score delta of +5 is calculated
  Then the applied delta = +5 * 0.8 = +4.0
  # Verify: enums.py:73 DRIFTING: Decimal("0.8")

Scenario: S-5.2.4 - CLINGY multiplier 0.5 applied [P1-High]
  Given a user with engagement_state="clingy"
  When a positive score delta of +5 is calculated
  Then the applied delta = +5 * 0.5 = +2.5
  # Verify: enums.py:74 CLINGY: Decimal("0.5")

Scenario: S-5.2.5 - DISTANT multiplier 0.6 applied [P1-High]
  Given a user with engagement_state="distant"
  When a positive score delta of +5 is calculated
  Then the applied delta = +5 * 0.6 = +3.0
  # Verify: enums.py:75 DISTANT: Decimal("0.6")

Scenario: S-5.2.6 - OUT_OF_ZONE multiplier 0.2 applied [P1-High]
  Given a user with engagement_state="out_of_zone"
  When a positive score delta of +5 is calculated
  Then the applied delta = +5 * 0.2 = +1.0
  # Verify: enums.py:76 OUT_OF_ZONE: Decimal("0.2")

Scenario: S-5.2.7 - Multiplier applies ONLY to positive deltas [P0-Critical]
  Given a user with engagement_state="clingy" (multiplier=0.5)
  When a positive delta of +4 and negative delta of -3 are calculated
  Then positive delta becomes +4 * 0.5 = +2
  And negative delta remains -3 (unaffected by multiplier)
  # Verify: enums.py:62-78 "multiplier applied to positive score deltas"

Scenario: S-5.2.8 - Negative deltas unaffected by any multiplier [P1-High]
  Given a user with engagement_state="out_of_zone" (multiplier=0.2)
  When a negative delta of -8 is calculated
  Then the applied delta = -8 (NOT -8 * 0.2)
  And score decrease is the full amount
  # Verify: Multiplier contract: only positive deltas multiplied

---

## US-5.3: Detection & Recovery
### MCP Tools: Supabase MCP

Scenario: S-5.3.1 - Clingy detected from message frequency [P1-High]
  Given a user sending 15+ messages per hour consistently
  When the engagement detection engine runs
  Then clinginess score exceeds 0.7
  And engagement_state may transition to "clingy" if persists
  # Verify: detection.py clingy detection based on message frequency

Scenario: S-5.3.2 - Distant detected from message gaps [P1-High]
  Given a user who hasn't sent a message in 48+ hours
  When the engagement detection engine runs
  Then neglect score exceeds 0.6
  And engagement_state may transition to "distant"
  # Verify: detection.py distant detection based on interaction gaps

Scenario: S-5.3.3 - Drift detection from pattern change [P2-Medium]
  Given a user who was in_zone but response quality drops
  When engagement score falls below 0.6
  Then engagement_state transitions to "drifting"
  And a drift warning may be logged
  # Verify: state_machine.py drifting detection threshold

Scenario: S-5.3.4 - Recovery rate after returning to healthy state [P2-Medium]
  Given a user recovering from "clingy" state
  When clinginess drops below 0.5 for 2+ days
  Then engagement_state transitions from "clingy" to "drifting"
  And further improvement can reach "in_zone"
  # Verify: state_machine.py:22 CLINGY -> DRIFTING: clinginess < 0.5 for 2+ days
  # Verify: recovery.py handles gradual state improvement

Scenario: S-5.3.5 - Engagement state logged per conversation [P1-High]
  Given a conversation completes
  When the pipeline processes the conversation
  Then the engagement_state at time of conversation is recorded
  And engagement history is queryable
  # Verify: Supabase MCP -> engagement state stored per conversation/pipeline run

Scenario: S-5.3.6 - Admin can view engagement history [P2-Medium]
  Given an admin user accesses the admin portal
  When they view a specific user's engagement data
  Then engagement state transitions over time are visible
  And the current state + multiplier are displayed
  # Verify: Portal admin endpoint returns engagement data
  # Verify: Chrome DevTools MCP -> admin engagement page renders

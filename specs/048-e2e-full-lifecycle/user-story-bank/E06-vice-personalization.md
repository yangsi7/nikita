# E06: Vice Personalization (12 scenarios)

> Epic: E06 | User Stories: 2 | Priority: P0=1, P1=5, P2=4, P3=2
> MCP Tools: Supabase MCP, Telegram MCP
> Source files: enums.py, scorer.py, injector.py, system_prompt.j2

---

## US-6.1: Vice Discovery
### MCP Tools: Supabase MCP

Scenario: S-6.1.1 - First vice detected from conversation [P1-High]
  Given a user with no prior vice preferences
  When the user's conversation reveals interest in dark humor
  Then ViceAnalyzer detects category="dark_humor"
  And a user_vice_preferences record is created with intensity_level=1
  # Verify: Supabase MCP -> SELECT * FROM user_vice_preferences WHERE user_id = {uid} AND category = 'dark_humor'
  # Verify: ViceCategory.DARK_HUMOR (enums.py:122)

Scenario: S-6.1.2 - Vice intensity increases with repeated engagement [P1-High]
  Given a user with dark_humor vice at intensity_level=2
  When further conversations reinforce dark humor signals
  Then intensity_level increases to 3
  And engagement_score for this vice increases
  # Verify: Supabase MCP -> intensity_level = 3 for dark_humor
  # Verify: scorer.py updates intensity based on repeated signals

Scenario: S-6.1.3 - All 8 vice categories detectable [P1-High]
  Given the ViceAnalyzer is configured with all 8 categories
  When conversations contain signals for each category
  Then each of the 8 categories can be independently detected:
    | intellectual_dominance | risk_taking | substances | sexuality |
    | emotional_intensity | rule_breaking | dark_humor | vulnerability |
  # Verify: enums.py:116-123 all 8 ViceCategory values

Scenario: S-6.1.4 - Vice discovery logged [P2-Medium]
  Given a new vice is detected for a user
  When the vice record is created
  Then the discovery event is logged with timestamp
  And the triggering conversation is referenced
  # Verify: Supabase MCP -> vice record has created_at timestamp

Scenario: S-6.1.5 - Duplicate vice signal deduplicated [P2-Medium]
  Given a user already has dark_humor at intensity=2
  When the same conversation produces multiple dark_humor signals
  Then the vice is updated once (not duplicated)
  And intensity increases by 1 (not N for N signals)
  # Verify: scorer.py deduplication logic
  # Verify: Supabase MCP -> single row for dark_humor, not multiple

Scenario: S-6.1.6 - Vice discovery during boss_fight [P3-Low]
  Given a user is in boss_fight and responds with emotional intensity
  When vice analysis runs on the boss response
  Then vice signals are captured regardless of game state
  And the vice record is updated
  # Verify: Vice analysis happens at pipeline level, independent of game state

---

## US-6.2: Vice Influence
### MCP Tools: Supabase MCP, Telegram MCP

Scenario: S-6.2.1 - Active vices injected into system prompt [P0-Critical]
  Given a user has dark_humor at intensity=3 (above threshold)
  When Nikita's system prompt is generated
  Then vice injection adds dark humor instructions to the prompt
  And Nikita's personality shifts to incorporate dark humor
  # Verify: injector.py injects vice context into prompt
  # Verify: system_prompt.j2 includes vice_context section

Scenario: S-6.2.2 - Vice threshold (intensity >= 2) required for injection [P1-High]
  Given a user has risk_taking at intensity=1 (below threshold)
  When the system prompt is generated
  Then risk_taking is NOT injected into the prompt
  And Nikita's personality does not reflect risk-taking
  # Verify: injector.py checks intensity threshold before injection

Scenario: S-6.2.3 - Vice influences Nikita response tone [P1-High]
  Given a user has emotional_intensity at intensity=4
  When Nikita responds to a message
  Then the response reflects deeper emotional engagement
  And language is more intense and vulnerable
  # Verify: Telegram MCP -> response tone matches vice influence

Scenario: S-6.2.4 - Vice removed when intensity drops [P2-Medium]
  Given a user had dark_humor at intensity=3 but interactions shift away
  When the vice scorer re-evaluates and drops intensity to 1
  Then the vice is no longer injected into prompts
  And Nikita's personality adjusts accordingly
  # Verify: scorer.py can decrease intensity
  # Verify: injector.py skips vices below threshold

Scenario: S-6.2.5 - Multiple active vices compose [P1-High]
  Given a user has dark_humor (intensity=3) and vulnerability (intensity=4)
  When the system prompt is generated
  Then BOTH vices are injected into the prompt
  And Nikita's personality blends dark humor with emotional openness
  # Verify: injector.py iterates all vices above threshold
  # Verify: system_prompt.j2 handles multiple vice_context entries

Scenario: S-6.2.6 - Vice preferences survive chapter advance [P1-High]
  Given a user in chapter=2 with dark_humor (intensity=3)
  When they pass the boss and advance to chapter=3
  Then vice preferences are preserved (not reset)
  And dark_humor continues to influence prompts in chapter=3
  # Verify: Supabase MCP -> user_vice_preferences unchanged after chapter advance
  # Verify: boss.py process_pass() does not reset vices

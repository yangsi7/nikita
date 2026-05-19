# E12: Cross-Platform (12 scenarios)

> Epic: E12 | User Stories: 3 | Priority: P0=4, P1=4, P2=2, P3=0
> MCP Tools: Supabase MCP, Chrome DevTools MCP, gcloud CLI
> Source files: message_handler.py, voice.py, portal.py, scoring.py, server_tools.py

---

## US-12.1: Multi-Platform Scoring
### MCP Tools: Supabase MCP, gcloud CLI

```gherkin
Scenario: S-12.1.1 - Text score + voice score accumulate on same user [P0-Critical]
  Given an active user in chapter 2 with relationship_score=55.0
  When the user sends a text message via Telegram that scores +2.0 delta
  And then makes a voice call that scores +3.0 delta
  Then relationship_score reflects both deltas (approximately 55.0 + 2.0 + 3.0 = 60.0)
  And score_history has two entries: one with event_type="text", one with event_type="voice_call"
  # Verify: Supabase MCP → SELECT score, event_type FROM score_history WHERE user_id = '{user_id}' ORDER BY created_at DESC LIMIT 2
  # Verify: Supabase MCP → SELECT relationship_score FROM users WHERE id = '{user_id}'

Scenario: S-12.1.2 - Boss trigger from combined text+voice scoring [P1-High]
  Given an active user in chapter 2 with score=53.0 (threshold is 55)
  When a text interaction scores +1.5 (total=54.5, still below threshold)
  And then a voice interaction scores +1.0 (total=55.5, above threshold)
  Then boss_fight is triggered on the voice scoring path (or next pipeline run)
  And game_status transitions to "boss_fight"
  # Verify: Supabase MCP → SELECT game_status FROM users WHERE id = '{user_id}'
  # Verify: BOSS_THRESHOLDS from engine/constants.py

Scenario: S-12.1.3 - Memory shared between text and voice platforms [P0-Critical]
  Given an active user who told Nikita "I work at Google" via text
  When the user later makes a voice call
  And the get_context server tool loads user_facts
  Then user_facts includes the text-originated fact "User works at Google"
  And get_memory with query "work" returns relevant facts from text conversations
  # Verify: SupabaseMemory stores facts with user_id, queryable from both platforms
  # Verify: server_tools.py:440-478 loads user_facts, relationship_episodes, nikita_events

Scenario: S-12.1.4 - Prompt references both text and voice context [P1-High]
  Given an active user with both text and voice conversation history
  When the unified pipeline generates a prompt for either platform
  Then the prompt includes context from both text and voice interactions
  And conversation summaries reference both platform types
  # Verify: Pipeline prompt_builder stage pulls from conversations table (both platforms)
  # Verify: Supabase MCP → SELECT platform, COUNT(*) FROM conversations WHERE user_id = '{user_id}' GROUP BY platform
```

---

## US-12.2: Portal Reflects All Platforms
### MCP Tools: Chrome DevTools MCP, Supabase MCP

```gherkin
Scenario: S-12.2.1 - Dashboard shows combined score from all platforms [P0-Critical]
  Given a logged-in user with text and voice score_history entries
  When the user views /dashboard
  Then relationship_score reflects cumulative scoring from both text and voice
  And the single score number is platform-agnostic (unified)
  # Verify: GET /api/v1/portal/stats → relationship_score is single unified value
  # Verify: Supabase MCP → SELECT relationship_score FROM users WHERE id = '{user_id}'

Scenario: S-12.2.2 - Conversation list includes both text and voice [P0-Critical]
  Given a logged-in user with 10 text and 3 voice conversations
  When the user navigates to /conversations
  Then all 13 conversations are listed
  And each conversation shows its platform type (text or voice icon/label)
  And voice conversations show "Voice Call" indicator
  # Verify: GET /api/v1/portal/conversations returns all platforms
  # Verify: Chrome DevTools → navigate to /conversations, check platform indicators

Scenario: S-12.2.3 - Score history interleaves text and voice events [P1-High]
  Given a logged-in user with alternating text and voice score events
  When the user views /scores or /scores/detail
  Then the chart shows all events chronologically regardless of platform
  And event_type labels distinguish voice_call from text events
  And the timeline shows a unified progression
  # Verify: GET /api/v1/portal/score-history returns all event types chronologically
  # Verify: Supabase MCP → SELECT event_type, score, created_at FROM score_history WHERE user_id = '{user_id}' ORDER BY created_at

Scenario: S-12.2.4 - Admin can see both platforms per user [P1-High]
  Given a logged-in admin viewing /admin/users/{user_id}
  When the admin views the user's conversation history
  Then both text and voice conversations are listed
  And voice conversations show transcript and score_delta
  And text conversations show messages and pipeline status
  # Verify: GET /api/v1/admin/users/{user_id}/conversations returns all platforms
```

---

## US-12.3: Platform Edge Cases
### MCP Tools: Supabase MCP, Chrome DevTools MCP

```gherkin
Scenario: S-12.3.1 - Voice call during active text conversation [P2-Medium]
  Given an active user currently in a text conversation (last message <5 min ago)
  When the user initiates a voice call
  Then the voice call proceeds independently
  And the text conversation remains active (not interrupted)
  And both conversations are scored independently when completed
  # Verify: No mutex or lock prevents concurrent platform usage
  # Verify: Supabase MCP → SELECT * FROM conversations WHERE user_id = '{user_id}' ORDER BY created_at DESC LIMIT 2

Scenario: S-12.3.2 - Portal account deletion while active in Telegram [P1-High]
  Given a user active in Telegram with an existing portal account
  When the user deletes their account via DELETE /api/v1/portal/account?confirm=true
  Then the user's data is permanently deleted from the database
  And subsequent Telegram messages create a "user not found" state
  And the portal shows logged-out state
  # Verify: portal.py:484 → delete account endpoint requires ?confirm=true
  # Verify: Supabase MCP → SELECT * FROM users WHERE id = '{user_id}' returns empty after deletion

Scenario: S-12.3.3 - Account linking Telegram to Portal [P1-High]
  Given a user who registered via Telegram (has telegram_id, no portal login)
  When the user generates a link code via POST /api/v1/portal/link-telegram
  Then a unique link code is returned
  And when the user enters this code in Telegram, the accounts are linked
  And the portal shows the user's existing game state from Telegram
  # Verify: portal.py:524 → link-telegram endpoint returns LinkCodeResponse
  # Verify: Supabase MCP → SELECT telegram_id FROM users WHERE id = '{user_id}'

Scenario: S-12.3.4 - Switching between voice and text mid-chapter [P2-Medium]
  Given a user in chapter 3 with score=62.0
  When the user alternates between text (3 messages) and voice (1 call) within same day
  Then all interactions contribute to the same chapter progress
  And score_history shows interleaved text and voice_call events
  And the pipeline processes each conversation independently
  And chapter advancement considers cumulative score regardless of platform
  # Verify: Supabase MCP → SELECT event_type, score FROM score_history WHERE user_id = '{user_id}' AND created_at > NOW() - INTERVAL '1 day' ORDER BY created_at
```

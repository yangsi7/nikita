# E02: Gameplay Loop - Text (24 scenarios)

> Epic: E02 | User Stories: 4 | Priority: P0=6, P1=6, P2=8, P3=4
> MCP Tools: Telegram MCP, Supabase MCP
> Source files: message_handler.py, calculator.py, pipeline/, system_prompt.j2

---

## US-2.1: Message Exchange
### MCP Tools: Telegram MCP, Supabase MCP

Scenario: S-2.1.1 - Normal message exchange with AI response [P0-Critical]
  Given a user with game_status="active" and chapter=1
  When the user sends "Hey Nikita, how are you?" via Telegram
  Then Nikita responds with an in-character message
  And a conversation record is created or updated
  And the message pair is stored in conversation.messages JSON
  # Verify: Supabase MCP -> SELECT * FROM conversations WHERE user_id = {uid} ORDER BY created_at DESC LIMIT 1
  # Verify: Telegram MCP -> response is in character (no asterisks, Ch1 tone)

Scenario: S-2.1.2 - Message skipped by chapter skip rate [P1-High]
  Given a user in chapter=1 (skip rate 25-40%)
  When the user sends a message that RNG determines should be skipped
  Then no Nikita response is sent for that message
  And the message is still stored in conversation history
  And no scoring occurs for the skipped message
  # Verify: constants.py Ch1 behavior: "Response rate: 60-75%"
  # Verify: Supabase MCP -> message stored but no assistant reply paired

Scenario: S-2.1.3 - Message during typing indicator [P3-Low]
  Given Nikita is generating a response (typing indicator active)
  When the user sends an additional message
  Then both messages are queued and processed
  And Nikita's response accounts for the additional message
  # Verify: Telegram MCP -> typing indicator was shown before response

Scenario: S-2.1.4 - Consecutive messages without response [P2-Medium]
  Given a user sends 3 messages in rapid succession
  When no Nikita response has been generated yet
  Then all 3 messages are stored in conversation history
  And Nikita may respond to the batch as a single interaction
  # Verify: Supabase MCP -> 3 user messages in conversation.messages before any assistant reply

Scenario: S-2.1.5 - Message with media/sticker [P2-Medium]
  Given a user sends a sticker or photo via Telegram
  When the webhook processes the media message
  Then the message is acknowledged (not crashed)
  And a text fallback is used for scoring/pipeline if applicable
  # Verify: Telegram MCP -> no error response for media message

Scenario: S-2.1.6 - Very long message (>4000 chars) [P2-Medium]
  Given a user sends a message exceeding 4000 characters
  When the message is processed
  Then it is truncated or handled without crashing
  And Nikita responds appropriately
  # Verify: Supabase MCP -> message stored (possibly truncated)
  # Verify: Telegram MCP -> Nikita response received

Scenario: S-2.1.7 - Empty/whitespace message [P3-Low]
  Given a user sends " " or an empty string
  When the webhook processes the empty message
  Then no crash occurs
  And the message is either ignored or a gentle nudge is sent
  # Verify: No 500 error in Cloud Run logs

Scenario: S-2.1.8 - Message with special characters/emoji [P3-Low]
  Given a user sends a message with unicode emoji and special chars
  When the message is processed through the pipeline
  Then encoding is preserved correctly
  And Nikita responds without garbled text
  # Verify: Supabase MCP -> message stored with correct unicode
  # Verify: Telegram MCP -> response renders properly

---

## US-2.2: Scoring
### MCP Tools: Supabase MCP

Scenario: S-2.2.1 - Positive score delta from good interaction [P0-Critical]
  Given a user with relationship_score=50 in chapter=1 (engagement=CALIBRATING, multiplier=0.9)
  When the user sends a thoughtful, engaged message and Nikita responds
  Then the LLM analyzer produces positive deltas for intimacy/passion/trust/secureness
  And the deltas are multiplied by 0.9 (CALIBRATING multiplier)
  And relationship_score increases (e.g. 50 -> 52.5)
  # Verify: Supabase MCP -> SELECT * FROM score_history WHERE user_id = {uid} ORDER BY created_at DESC LIMIT 1
  # Verify: score_history.delta > 0, event_type = "message"
  # Verify: calculator.py applies METRIC_WEIGHTS: intimacy=0.30, passion=0.25, trust=0.25, secureness=0.20

Scenario: S-2.2.2 - Negative score delta from bad interaction [P0-Critical]
  Given a user with relationship_score=60
  When the user sends a rude or dismissive message
  Then the LLM analyzer produces negative deltas
  And negative deltas are NOT affected by engagement multiplier
  And relationship_score decreases
  # Verify: Supabase MCP -> score_history.delta < 0
  # Verify: enums.py:62-78 multiplier only on positive deltas

Scenario: S-2.2.3 - Neutral interaction (zero delta) [P2-Medium]
  Given a user with relationship_score=55
  When the user sends a bland "ok" message
  Then the LLM analyzer may return near-zero deltas
  And relationship_score remains approximately unchanged
  # Verify: Supabase MCP -> score_history.delta ~ 0

Scenario: S-2.2.4 - All 4 metrics affected independently [P1-High]
  Given a user interaction occurs
  When the LLM analyzer returns {intimacy: +3, passion: -1, trust: +5, secureness: +2}
  Then each metric is updated independently in user_metrics
  And composite score = intimacy*0.30 + passion*0.25 + trust*0.25 + secureness*0.20
  # Verify: Supabase MCP -> SELECT intimacy, passion, trust, secureness FROM user_metrics WHERE user_id = {uid}
  # Verify: Each metric clamped to [0, 100] independently

Scenario: S-2.2.5 - Engagement multiplier applied to positive deltas [P0-Critical]
  Given a user in engagement_state="in_zone" (multiplier=1.0)
  When a positive score delta of +5 is calculated
  Then the final delta = +5 * 1.0 = +5
  And if the user were in "clingy" state, delta = +5 * 0.5 = +2.5
  # Verify: enums.py:70-77 multiplier values
  # Verify: Supabase MCP -> score_history shows multiplied delta

Scenario: S-2.2.6 - Score clamped at 0 [P1-High]
  Given a user with relationship_score=2
  When a delta of -10 is applied
  Then relationship_score is set to 0 (not negative)
  And game_over may be triggered (score reached 0)
  # Verify: Supabase MCP -> relationship_score >= 0
  # Verify: game_status may change to "game_over"

Scenario: S-2.2.7 - Score clamped at 100 [P2-Medium]
  Given a user with relationship_score=98
  When a delta of +5 is applied
  Then relationship_score is set to 100 (not 105)
  # Verify: Supabase MCP -> relationship_score <= 100

Scenario: S-2.2.8 - Score history entry created per interaction [P0-Critical]
  Given a user sends a message and receives a response
  When scoring completes
  Then a new row in score_history is created
  And it records: user_id, old_score, new_score, delta, event_type, created_at
  # Verify: Supabase MCP -> SELECT COUNT(*) FROM score_history WHERE user_id = {uid} incremented by 1
  # Verify: score_history.event_type = "message" for text interactions

---

## US-2.3: Pipeline Processing
### MCP Tools: Supabase MCP

Scenario: S-2.3.1 - Conversation marked for post-processing [P1-High]
  Given a conversation between user and Nikita concludes (inactivity timeout)
  When the /tasks/process-conversations endpoint runs
  Then the conversation is detected as inactive
  And it is queued for 9-stage pipeline processing
  # Verify: Supabase MCP -> SELECT * FROM conversations WHERE status = 'processing'
  # Verify: pg_cron job "process-conversations" is active

Scenario: S-2.3.2 - 9-stage pipeline completes successfully [P0-Critical]
  Given a conversation is queued for pipeline processing
  When all 9 stages execute (game_state, emotional, life_sim, memory, scoring, touchpoint, vice, prompt_builder, summary)
  Then pipeline_result is stored with all stage outputs
  And the conversation status is updated to "processed"
  And memory facts, threads, and thoughts are extracted
  # Verify: Supabase MCP -> pipeline_results table has entry for this conversation
  # Verify: Supabase MCP -> SELECT * FROM memory_facts WHERE conversation_id = {cid}

Scenario: S-2.3.3 - Pipeline stage failure with circuit breaker [P1-High]
  Given the life_sim stage throws a SQL error
  When the pipeline orchestrator catches the exception
  Then the failed stage is logged but does not crash the pipeline
  And remaining stages continue to execute
  And the pipeline result records the stage failure
  # Verify: pipeline/stages/life_sim.py has try/except fallback
  # Verify: Supabase MCP -> pipeline_results shows partial completion

Scenario: S-2.3.4 - Memory facts extracted and stored [P1-High]
  Given a conversation where the user mentions "I work at Google"
  When the memory extraction stage runs
  Then a memory fact "User works at Google" is stored via SupabaseMemory
  And it is retrievable via pgVector similarity search
  # Verify: Supabase MCP -> SELECT * FROM memory_facts WHERE user_id = {uid} AND content LIKE '%Google%'

---

## US-2.4: Context Enrichment
### MCP Tools: Supabase MCP

Scenario: S-2.4.1 - Prompt generated with full user context [P0-Critical]
  Given a user with profile, backstory, score history, and memory facts
  When a new message triggers prompt generation
  Then the system prompt includes: chapter behavior, user profile, backstory, mood, open threads
  And the prompt is within token budget (text: ~2,700 tokens, voice: ~2,000 tokens)
  # Verify: pipeline/stages/prompt_builder.py assembles all context
  # Verify: Token count within budget (Spec 045 E2E: text=2,682, voice=2,041)

Scenario: S-2.4.2 - Backstory referenced in Nikita response [P2-Medium]
  Given a user whose backstory mentions they are a musician
  When the user sends a music-related message
  Then Nikita's response may reference the backstory context
  And the response feels personalized
  # Verify: system_prompt.j2 includes backstory section

Scenario: S-2.4.3 - Vice preferences influence response tone [P2-Medium]
  Given a user with active vice dark_humor (intensity=3)
  When the user sends a message
  Then Nikita's system prompt includes vice injection for dark_humor
  And Nikita's response may incorporate dark humor elements
  # Verify: vice/injector.py injects vice context into prompt

Scenario: S-2.4.4 - Open threads surfaced in prompt [P2-Medium]
  Given the user previously mentioned a job interview next week
  When the user sends a message 3 days later
  Then the open thread "job interview" is surfaced in the system prompt
  And Nikita may ask about the interview naturally
  # Verify: Supabase MCP -> memory_facts/threads table has open thread
  # Verify: system_prompt.j2 includes open_threads section

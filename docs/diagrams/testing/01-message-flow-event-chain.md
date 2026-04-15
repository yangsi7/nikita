# Diagram: Message Flow Event Chain

**Type**: Behavioral — Event/Sequence Flow
**Scope**: Telegram message arrival through pipeline completion
**Sources**:
- `nikita/platforms/telegram/message_handler.py` — MessageHandler.handle()
- `nikita/platforms/telegram/handlers/scoring_orchestrator.py` — ScoringOrchestrator
- `nikita/platforms/telegram/handlers/engagement_orchestrator.py` — EngagementOrchestrator
- `nikita/pipeline/orchestrator.py` — PipelineOrchestrator, STAGE_DEFINITIONS
- `nikita/api/routes/tasks.py` — POST /tasks/process-conversations (line 673)

---

```
+=====================================================================+
|  PATH A: Synchronous Message Handling (request-response cycle)      |
+=====================================================================+

  (User sends Telegram message)
          |
          v
  [Telegram Webhook]
  POST /api/v1/telegram/update
          |
          v
  +--[ message_handler.py: MessageHandler.handle() ]--+
  |                                                    |
  | 1. User lookup (FOR UPDATE row lock)               |
  |       |                                            |
  |       +--> Not found: send /start prompt [EXIT]    |
  |                                                    |
  | 2. Profile gate check (_needs_onboarding)          |
  |       |                                            |
  |       +--> Incomplete: redirect onboarding [EXIT]  |
  |                                                    |
  | 3. Game status branch                              |
  |       |                                            |
  |       +--< game_status? >                          |
  |             |          |          |                |
  |         boss_fight  game_over   won                |
  |             |          |          |                |
  |    [BossEncounterHandler]  [Canned msg]  [WON msg] |
  |             |              [EXIT]        [EXIT]    |
  |          [EXIT]                                    |
  |                                                    |
  | 4. Rate limiter check (20/min, 500/day)            |
  |       |                                            |
  |       +--> Limit hit: in-character reply [EXIT]    |
  |                                                    |
  | 5. Conversation tracking                           |
  |       get_or_create conversation record            |
  |       append user message to conversations.messages|
  |                                                    |
  | 6. send_chat_action("typing")                      |
  |                                                    |
  | 7. Psyche agent (feature-gated, default OFF)       |
  |       detect_trigger_tier()                        |
  |       quick_analyze() or deep_analyze() ..>        |
  |                                                    |
  | 8. Text agent call (Claude LLM)                    |
  |       text_agent_handler.handle()                  |
  |       --> decision.response, decision.delay_seconds|
  |       --> decision.should_respond                  |
  |                                                    |
  | 9. If should_respond == True:                      |
  |       a. append nikita response to conversation    |
  |       b. _score_and_check_boss()                   |
  |            |                                       |
  |            v                                       |
  |       +--[ ScoringOrchestrator ]--+                |
  |       | ScoringService.score()    |                |
  |       |   --> metric deltas       |                |
  |       |   --> score_history row   |                |
  |       |   --> user_metrics update |                |
  |       | BossStateMachine check    |                |
  |       |   threshold >= 75%?       |                |
  |       |   --> trigger boss_fight  |                |
  |       +---------------------------+                |
  |            |                                       |
  |       c. update_last_interaction_at()              |
  |       d. apply_text_patterns() (emoji/length)      |
  |       e. response_delivery.queue()                 |
  |            --> scheduled_events row (with delay)   |
  |       f. send_push() ..> (non-blocking)            |
  |                                                    |
  | 10. EngagementOrchestrator                         |
  |       FSM state transition evaluation              |
  |       --> engagement_state updated                 |
  +----------------------------------------------------+


+=====================================================================+
|  PATH B: Async Post-Processing (pg_cron, every 1 minute)            |
+=====================================================================+

  [pg_cron]
  --> POST /tasks/process-conversations   (tasks.py line 673)
          |
          v
  +--[ PipelineOrchestrator.process() ]---+
  | conversation_id, user_id, platform    |
  | Skip if game_status IN (game_over,won)|
  |                                       |
  | Observability: EventEmitter created   |
  | (writes to pipeline_events table)     |
  |                                       |
  | Each stage: begin_nested() savepoint  |
  | Non-critical: 1 retry on failure      |
  |                                       |
  | Stage 1  [CRITICAL] ExtractionStage   |
  |   LLM call (Claude) -- fact extract   |
  |   --> ctx.extracted_facts             |
  |   --> nikita_thoughts rows            |
  |                                       |
  | Stage 2  [non-crit] PersistenceStage  |
  |   --> conversation_threads rows       |
  |   (runs BEFORE memory_update:         |
  |    Spec 116 ordering requirement)     |
  |                                       |
  | Stage 3  [CRITICAL] MemoryUpdateStage |
  |   pgVector upsert (dedup 0.95 cosine) |
  |   --> memory_facts rows               |
  |                                       |
  | Stage 4  [non-crit] LifeSimStage      |
  |   EventStore (SQL INSERT)             |
  |   --> nikita_life_events rows         |
  |                                       |
  | Stage 5  [non-crit] EmotionalStage    |
  |   StateStore (SQL INSERT)             |
  |   --> nikita_emotional_states rows    |
  |                                       |
  | Stage 6  [non-crit] ViceStage         |
  |   --> user_vice_preferences rows      |
  |                                       |
  | Stage 7  [non-crit] GameStateStage    |
  |   --> users.chapter update            |
  |   --> users.game_status update        |
  |   --> score_history row               |
  |                                       |
  | Stage 8  [non-crit] ConflictStage     |
  |   --> users.conflict_details JSONB    |
  |                                       |
  | Stage 9  [non-crit] TouchpointStage   |
  |   TouchpointEngine.evaluate()         |
  |   --> scheduled_touchpoints row       |
  |                                       |
  | Stage 10 [non-crit] SummaryStage      |
  |   --> conversations.summary update    |
  |                                       |
  | Stage 11 [non-crit] PromptBuilderStage|
  |   --> ready_prompts row (platform=text|
  |       and platform=voice)             |
  |   --> users.cached_voice_prompt update|
  |                                       |
  | EventEmitter.flush()                  |
  |   --> pipeline_events bulk INSERT     |
  +---------------------------------------+

  [pg_cron]
  --> POST /tasks/deliver   (every 1 minute)
          |
          v
  scheduled_events --> TelegramBot.send_message()

Legend:
  --> sync call / direct dependency
  ..> async / non-blocking / fire-and-forget
  [CRITICAL] pipeline halts if this stage fails
  [non-crit] failure logged; pipeline continues
  [EXIT] handler returns; no further processing
  < > decision point
```

---

**Key Actors**

| Actor | File | Role |
|-------|------|------|
| MessageHandler | `nikita/platforms/telegram/message_handler.py` | Sync message routing |
| ScoringOrchestrator | `nikita/platforms/telegram/handlers/scoring_orchestrator.py` | Score + boss check |
| EngagementOrchestrator | `nikita/platforms/telegram/handlers/engagement_orchestrator.py` | FSM transitions |
| PipelineOrchestrator | `nikita/pipeline/orchestrator.py` | 11-stage async runner |
| EventEmitter | `nikita/observability/` | Stage event buffering |

**Database Tables Written**

| Table | Stage/Handler |
|-------|--------------|
| `conversations` (messages JSONB) | MessageHandler (append) |
| `score_history` | ScoringOrchestrator, GameStateStage |
| `user_metrics` | ScoringOrchestrator |
| `users` (game_status, chapter, conflict_details, cached_voice_prompt) | GameStateStage, ConflictStage, PromptBuilderStage |
| `engagement_state` | EngagementOrchestrator |
| `nikita_thoughts` | ExtractionStage |
| `conversation_threads` | PersistenceStage |
| `memory_facts` | MemoryUpdateStage |
| `nikita_life_events` | LifeSimStage |
| `nikita_emotional_states` | EmotionalStage |
| `user_vice_preferences` | ViceStage |
| `scheduled_touchpoints` | TouchpointStage |
| `ready_prompts` | PromptBuilderStage |
| `pipeline_events` | EventEmitter.flush() |
| `scheduled_events` | ResponseDelivery.queue() |

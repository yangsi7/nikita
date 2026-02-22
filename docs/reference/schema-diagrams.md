# Schema Diagrams -- Nikita Database (32 Live Tables)

Generated: 2026-02-22
Evidence: file:line references verified against codebase

---

## Diagram 1: Production Data Flow

Complete data flow from message receipt through pipeline processing to next-message context.

**Legend**:
- `-->` = reads from
- `==>` = writes to
- `~~>` = async/background write
- `[R]` = read, `[W]` = write, `[RW]` = both

```
=============================================================================
MESSAGE RECEIPT PHASE (synchronous, <3s target)
=============================================================================

  Telegram/Voice Message
        |
        v
  +-----------------------------+
  | MessageHandler              |  nikita/platforms/telegram/message_handler.py
  +-----------------------------+
        |
        |-- [R] users                  (line 158: get_by_telegram_id_for_update)
        |-- [R] user_metrics           (line 536-540: user.metrics.intimacy/passion/trust/secureness)
        |-- [R] engagement_state       (line 544-548: user.engagement_state.state)
        |-- [R] user_vice_preferences  (line 141: ctx.vices from user.vice_preferences)
        |-- [R] user_profiles          (line 765: profile_repo.get_by_user_id)
        |-- [R] user_backstories       (line 769: backstory_repo.get_by_user_id)
        |-- [R] psyche_states          (line 252: psyche_repo.get_current)
        |-- [R] conversations          (line 495: get_active_conversation)
        |
        |-- [W] conversations          (line 224-228: append_message, line 497: create_conversation)
        |
        v
  +-----------------------------+
  | TextAgentHandler            |  nikita/agents/text/handler.py
  +-----------------------------+
        |
        |-- [R] ready_prompts          (agent.py:372: load pre-built prompt from pipeline)
        |-- [R] memory_facts           (agent.py: SupabaseMemory.search for working memory)
        |-- [R] conversations          (handler.py: conversation_messages passed from MH)
        |
        v
  Agent generates response (Claude LLM call)
        |
        v
  +-----------------------------+
  | Post-Response Inline Ops    |  message_handler.py:350-680
  +-----------------------------+
        |
        |-- [W] conversations          (line 353-357: append nikita response)
        |-- [W] users                  (line 370: update_last_interaction, line 602: update_score)
        |-- [W] user_metrics           (line 621-627: update_metrics I/P/T/S deltas)
        |-- [W] conversations          (line 637-640: update_score_delta)
        |-- [W] engagement_state       (line 1585-1612: state/counters/multiplier update)
        |-- [W] engagement_history     (line 1616-1624: log state transition)
        |-- [W] scheduled_events       (via ResponseDelivery.queue for delayed messages)
        |
        |-- [CONDITIONAL: Boss Threshold Reached]
        |   |-- [W] users              (line 668: set_boss_fight_status)
        |   |-- [W] conversations      (line 653: close_conversation)
        |
        |-- [CONDITIONAL: Game Over via Engagement]
            |-- [W] users              (line 1650: update_game_status "game_over")


=============================================================================
PIPELINE PHASE (async, triggered by pg_cron every 60s)
=============================================================================

  pg_cron --> POST /tasks/process-conversations
        |
        v
  +-----------------------------+
  | detect_stale_sessions()     |  nikita/context/session_detector.py
  +-----------------------------+
        |-- [R] conversations          (status='active', last_message >15min ago)
        |-- [W] conversations          (mark status='processing')
        |
        v
  +-----------------------------+
  | PipelineOrchestrator        |  nikita/pipeline/orchestrator.py:39-49
  +-----------------------------+
        |
        | Stage order (9 stages sequential):
        |
        |
  [1] EXTRACTION (CRITICAL)        nikita/pipeline/stages/extraction.py:68-121
        |-- [R] conversations          (line 78-79: ctx.conversation.messages)
        |-- Sets: ctx.extracted_facts, extracted_threads, extracted_thoughts
        |-- Sets: ctx.extraction_summary, ctx.emotional_tone
        |
  [2] MEMORY_UPDATE (CRITICAL)     nikita/pipeline/stages/memory_update.py:38-93
        |-- [R] memory_facts           (line 71: find_similar for dedup, threshold=0.95)
        |-- [W] memory_facts           (line 76-81: add_fact via SupabaseMemory)
        |
  [3] LIFE_SIM                     nikita/pipeline/stages/life_sim.py:52-88
        |-- [R] nikita_life_events     (line 70: get_today_events)
        |-- [W] nikita_life_events     (line 74: generate_next_day_events -> save_events)
        |-- [R] nikita_narrative_arcs  (via LifeSimulator -> EventStore.get_active_arcs)
        |-- [W] nikita_narrative_arcs  (via LifeSimulator -> EventStore.save_arc)
        |-- Sets: ctx.life_events
        |
  [4] EMOTIONAL                    nikita/pipeline/stages/emotional.py:44-135
        |-- [R] (ctx.life_events from stage 3)
        |-- [R] (ctx.emotional_tone from stage 1)
        |-- [R] users.conflict_details (line 124: load_conflict_details for Spec 057)
        |-- Sets: ctx.emotional_state {arousal, valence, dominance, intimacy}
        |-- ZOMBIE GAP: computes state but NEVER writes to nikita_emotional_states
        |
  [5] GAME_STATE                   nikita/pipeline/stages/game_state.py:41-116
        |-- [R] conversations          (line 50: ctx.conversation.score_delta)
        |-- [R] (constants: BOSS_THRESHOLDS, CHAPTER_NAMES)
        |-- Sets: ctx.score_delta, ctx.score_events
        |-- READ-ONLY validation stage (scoring done inline in MessageHandler)
        |
  [6] CONFLICT                     nikita/pipeline/stages/conflict.py:41-210
        |-- [R] (ctx.emotional_state from stage 4)
        |-- [R] users.conflict_details (line 113: ConflictDetails.from_jsonb)
        |-- [W] users.conflict_details (line 151-156: save_conflict_details after decay)
        |-- Sets: ctx.active_conflict, ctx.conflict_type
        |
  [7] TOUCHPOINT                   nikita/pipeline/stages/touchpoint.py:34-46
        |-- [R] users                  (via TouchpointEngine)
        |-- [R] scheduled_touchpoints  (via TouchpointEngine: check existing)
        |-- [W] scheduled_touchpoints  (via TouchpointEngine: schedule new)
        |-- Sets: ctx.touchpoint_scheduled
        |
  [8] SUMMARY                      nikita/pipeline/stages/summary.py:38-86
        |-- [R] conversations          (line 50: ctx.conversation.messages)
        |-- [W] conversations          (line 60: conversation_summary field)
        |-- Sets: ctx.extraction_summary (reuse or LLM-generate)
        |
  [9] PROMPT_BUILDER               nikita/pipeline/stages/prompt_builder.py:59-100
        |-- [R] conversations          (line 139: get_conversation_summaries_for_prompt)
        |-- [R] users                  (line 155: get user for profile/backstory)
        |-- [R] memory_facts           (line 180-196: SupabaseMemory.search)
        |-- [R] user_profiles          (via user.profile relationship)
        |-- [R] user_backstories       (via user.backstory relationship)
        |-- [W] ready_prompts          (line 547: set_current for text + voice)
        |-- [W] users                  (line 580: cached_voice_prompt sync)
        |-- ZOMBIE GAP: writes to ready_prompts but NEVER to generated_prompts
        |
        v
  +-----------------------------+
  | Post-Pipeline Finalization  |  nikita/api/routes/tasks.py:736-741
  +-----------------------------+
        |-- [W] conversations          (mark_processed: status, summary, emotional_tone)
        |-- [W] job_executions         (line 786: complete_execution)


=============================================================================
PORTAL READ PHASE (Next.js dashboard, read-only)
=============================================================================

  Portal API Routes                nikita/api/routes/portal.py
        |
        |-- /stats                 --> [R] users, user_metrics          (line 80-91)
        |-- /metrics               --> [R] user_metrics                 (line 124)
        |-- /engagement            --> [R] engagement_state,            (line 144)
        |                              [R] engagement_history           (line 159)
        |-- /vices                 --> [R] user_vice_preferences        (line 187)
        |-- /score-history         --> [R] score_history                (line 207-211)
        |-- /score-history/detailed--> [R] score_history                (line 749-750)
        |-- /daily-summaries       --> [R] daily_summaries              (line 237)
        |-- /conversations         --> [R] conversations                (line 265)
        |-- /conversations/{id}    --> [R] conversations                (line 296)
        |-- /decay                 --> [R] users                        (line 331)
        |-- /settings              --> [R] users                        (line 429)
        |-- /settings (PUT)        --> [W] users                        (line 471)
        |-- /link-telegram         --> [W] telegram_links               (line 538)
        |-- /emotional-state       --> [R] nikita_emotional_states      (line 563)
        |-- /emotional-state/hist  --> [R] nikita_emotional_states      (line 591)
        |-- /life-events           --> [R] nikita_life_events           (line 632)
        |-- /thoughts              --> [R] nikita_thoughts              (line 672)
        |-- /narrative-arcs        --> [R] nikita_narrative_arcs        (line 709-712)
        |-- /social-circle         --> [R] user_social_circles          (line 733)
        |-- /threads               --> [R] conversation_threads         (line 789-794)
        |-- /psyche-tips           --> [R] psyche_states                (line 818)
        |-- /account (DELETE)      --> [W] users (cascade delete)       (line 512)
        |-- /export/*              --> [R] score_history, conversations, (line 870-912)
        |                              [R] user_vice_preferences


=============================================================================
PG_CRON BACKGROUND JOBS               nikita/api/routes/tasks.py
=============================================================================

  /tasks/decay (hourly)
        |-- [R] users                  (line 476: get_active_users_for_decay)
        |-- [W] users                  (line 250: update scores via DecayProcessor)
        |-- [W] score_history          (via DecayProcessor -> log_event)
        |-- [W] job_executions         (line 227: start/complete execution)

  /tasks/deliver (every 1 min)
        |-- [R] scheduled_events       (line 309: get_due_events)
        |-- [W] scheduled_events       (line 335/324: mark_delivered/mark_failed)
        |-- [W] job_executions         (line 301: start/complete execution)

  /tasks/summary (daily 23:59 UTC)
        |-- [R] users                  (line 476: get_active_users)
        |-- [R] conversations          (line 500: get_processed_conversations)
        |-- [R] conversation_threads   (line 528-534: threads from today)
        |-- [R] nikita_thoughts        (line 541-548: thoughts from today)
        |-- [R] score_history          (line 494: get_daily_stats)
        |-- [W] daily_summaries        (line 571: create_summary)
        |-- [W] job_executions         (line 464: start/complete execution)

  /tasks/cleanup (hourly)
        |-- [W] pending_registrations  (line 643: cleanup_expired)
        |-- [W] job_executions         (line 638: start/complete execution)

  /tasks/process-conversations (every 1 min)
        |-- (triggers full pipeline; see Pipeline Phase above)
        |-- [W] job_executions         (line 687: start/complete execution)

  /tasks/psyche-batch (daily 5AM UTC)
        |-- [R] users                  (via batch.py: get active users)
        |-- [W] psyche_states          (via batch.py: store generated states)
        |-- [W] job_executions         (line 819: start/complete execution)

  /tasks/touchpoints (every 5 min)
        |-- [R] users, scheduled_touchpoints
        |-- [W] scheduled_touchpoints, scheduled_events
        |-- [W] job_executions         (line 948: start/complete execution)

  /tasks/boss-timeout (every 6 hours)
        |-- [R] users                  (line 1071-1077: game_status=boss_fight, stale >24h)
        |-- [W] users                  (line 1082-1092: boss_attempts, game_status)
        |-- [W] score_history          (line 1095: log boss_timeout event)
        |-- [W] job_executions         (line 1059: start/complete execution)

  /tasks/detect-stuck (every 10 min)
        |-- [R] conversations          (line 882: detect_stuck >30min)
        |-- [W] conversations          (line 893: mark failed)
        |-- [W] job_executions         (line 875: start/complete execution)

  /tasks/recover-stuck (every 10 min)
        |-- [R] conversations          (line 1009: recover_stuck)
        |-- [W] conversations          (line 1009: reset or mark failed)
        |-- [W] job_executions         (line 1004: start/complete execution)
```

---

## Diagram 2: Store/Repo --> Table Access Map

Maps which code layer accesses each of the 32 live tables.

**Legend**:
- `[R]` = read-only
- `[W]` = write-only
- `[RW]` = read and write
- `ZOMBIE` = code path exists but is never called from production flow
- `-->` = "accesses table"

```
=============================================================================
DOMAIN 1: USER & GAME STATE (4 tables)
=============================================================================

  users (CENTRAL HUB - 24 inbound FKs)
  +-----------------------------------------------------------------+
  | Accessor                         | R/W  | Evidence              |
  +-----------------------------------------------------------------+
  | UserRepository                   | [RW] | db/repositories/user_repository.py:22 |
  | MessageHandler                   | [RW] | message_handler.py:158,370,602,668,1650 |
  | PromptBuilderStage._enrich       | [R]  | prompt_builder.py:155 |
  | TouchpointStage (via engine)     | [R]  | touchpoint.py:40      |
  | Portal: /stats,/decay,/settings  | [RW] | portal.py:81,331,471  |
  | Tasks: /decay                    | [RW] | tasks.py:250          |
  | Tasks: /boss-timeout             | [RW] | tasks.py:1071-1092    |
  | Tasks: /deliver (voice)          | [R]  | tasks.py:361          |
  +-----------------------------------------------------------------+

  user_metrics
  +-----------------------------------------------------------------+
  | UserMetricsRepository            | [RW] | db/repositories/metrics_repository.py:16 |
  | MessageHandler._score            | [R+W]| message_handler.py:536(R),621(W) |
  | Portal: /stats, /metrics         | [R]  | portal.py:91,124      |
  +-----------------------------------------------------------------+

  user_vice_preferences
  +-----------------------------------------------------------------+
  | VicePreferenceRepository         | [RW] | db/repositories/vice_repository.py:17 |
  | Orchestrator (load vices)        | [R]  | orchestrator.py:141-146 |
  | Portal: /vices, /export/vices    | [R]  | portal.py:187,902     |
  +-----------------------------------------------------------------+

  score_history
  +-----------------------------------------------------------------+
  | ScoreHistoryRepository           | [RW] | db/repositories/score_history_repository.py:18 |
  | Tasks: /decay (log event)        | [W]  | tasks.py:233          |
  | Tasks: /summary (daily stats)    | [R]  | tasks.py:494          |
  | Tasks: /boss-timeout (log)       | [W]  | tasks.py:1095         |
  | Portal: /score-history           | [R]  | portal.py:207,749     |
  | Portal: /export/score-history    | [R]  | portal.py:870         |
  +-----------------------------------------------------------------+


=============================================================================
DOMAIN 2: CONVERSATIONS (2 tables)
=============================================================================

  conversations (SECOND HUB - 8 inbound FKs)
  +-----------------------------------------------------------------+
  | ConversationRepository           | [RW] | db/repositories/conversation_repository.py:21 |
  | MessageHandler                   | [RW] | message_handler.py:224,353,495,637,653 |
  | ExtractionStage                  | [R]  | extraction.py:78      |
  | SummaryStage                     | [RW] | summary.py:50(R),60(W)|
  | GameStateStage                   | [R]  | game_state.py:50      |
  | PromptBuilderStage               | [R]  | prompt_builder.py:139 |
  | Tasks: /process-conversations    | [RW] | tasks.py:717,737-743  |
  | Tasks: /summary                  | [R]  | tasks.py:500          |
  | Tasks: /detect-stuck             | [RW] | tasks.py:882,893      |
  | Tasks: /recover-stuck            | [RW] | tasks.py:1009         |
  | Portal: /conversations           | [R]  | portal.py:265,296     |
  | Portal: /export/conversations    | [R]  | portal.py:886         |
  +-----------------------------------------------------------------+

  message_embeddings [ZOMBIE --> DROP]
  +-----------------------------------------------------------------+
  | MessageEmbedding model           | ---  | db/models/conversation.py:159-197 |
  | NO REPOSITORY                    | ---  | (no repo, no pipeline writes)     |
  | NO PRODUCTION CALLERS            | ---  | Replaced by memory_facts pgVector |
  +-----------------------------------------------------------------+


=============================================================================
DOMAIN 3: MEMORY & EXTRACTION (3 tables)
=============================================================================

  memory_facts
  +-----------------------------------------------------------------+
  | MemoryFactRepository             | [RW] | db/repositories/memory_fact_repository.py:13 |
  | MemoryUpdateStage                | [RW] | memory_update.py:71(R),76(W)    |
  | PromptBuilderStage._enrich       | [R]  | prompt_builder.py:180-196       |
  | TextAgent (working memory)       | [R]  | agent.py: SupabaseMemory.search |
  +-----------------------------------------------------------------+

  conversation_threads
  +-----------------------------------------------------------------+
  | ConversationThreadRepository     | [RW] | db/repositories/thread_repository.py:20 |
  | ExtractionStage (via pipeline)   | [W]  | (threads extracted, stored downstream) |
  | Tasks: /summary                  | [R]  | tasks.py:528-534      |
  | Portal: /threads                 | [R]  | portal.py:789         |
  +-----------------------------------------------------------------+

  nikita_thoughts
  +-----------------------------------------------------------------+
  | NikitaThoughtRepository          | [RW] | db/repositories/thought_repository.py:21 |
  | ExtractionStage (via pipeline)   | [W]  | (thoughts extracted, stored downstream) |
  | Tasks: /summary                  | [R]  | tasks.py:541-548      |
  | Portal: /thoughts                | [R]  | portal.py:672         |
  +-----------------------------------------------------------------+


=============================================================================
DOMAIN 4: ENGAGEMENT (2 tables)
=============================================================================

  engagement_state
  +-----------------------------------------------------------------+
  | EngagementStateRepository        | [RW] | db/repositories/engagement_repository.py:16 |
  | MessageHandler._update_engage    | [RW] | message_handler.py:1411(R),1585-1612(W) |
  | Orchestrator (load state)        | [R]  | orchestrator.py:137-139 |
  | Portal: /engagement              | [R]  | portal.py:144         |
  +-----------------------------------------------------------------+

  engagement_history
  +-----------------------------------------------------------------+
  | EngagementStateRepository        | [RW] | db/repositories/engagement_repository.py |
  | MessageHandler._update_engage    | [W]  | message_handler.py:1616-1624 |
  | Portal: /engagement              | [R]  | portal.py:159         |
  +-----------------------------------------------------------------+


=============================================================================
DOMAIN 5: LIFE SIMULATION (3 tables)
=============================================================================

  nikita_life_events
  +-----------------------------------------------------------------+
  | EventStore                       | [RW] | life_simulation/store.py:55-82(W),118-146(R) |
  | LifeSimStage                     | [RW] | life_sim.py:70(R),74(W) |
  | Portal: /life-events             | [R]  | portal.py:632         |
  +-----------------------------------------------------------------+

  nikita_narrative_arcs
  +-----------------------------------------------------------------+
  | EventStore                       | [RW] | life_simulation/store.py:235-262(W),264-283(R) |
  | NarrativeArcRepository           | [RW] | db/repositories/narrative_arc_repository.py:22 |
  | LifeSimStage (via LifeSimulator) | [RW] | (arcs created/updated during life sim) |
  | Portal: /narrative-arcs          | [R]  | portal.py:706-712     |
  +-----------------------------------------------------------------+

  nikita_entities [ZOMBIE]
  +-----------------------------------------------------------------+
  | EventStore.save_entity()         | [RW] | life_simulation/store.py:341-362(W),377-395(R) |
  | NO PRODUCTION CALLERS            | ---  | LifeSimStage never calls save_entity() |
  +-----------------------------------------------------------------+


=============================================================================
DOMAIN 6: EMOTIONAL STATE (1 table)
=============================================================================

  nikita_emotional_states [ZOMBIE]
  +-----------------------------------------------------------------+
  | StateStore                       | [RW] | emotional_state/store.py:48-70(R),96-124(W) |
  | EmotionalStage                   | ---  | emotional.py:102-107 computes but NEVER saves |
  | Portal: /emotional-state         | [R]  | portal.py:563         |
  | Portal: /emotional-state/history | [R]  | portal.py:591         |
  +-----------------------------------------------------------------+


=============================================================================
DOMAIN 7: PROMPTS (2 tables)
=============================================================================

  ready_prompts
  +-----------------------------------------------------------------+
  | ReadyPromptRepository            | [RW] | db/repositories/ready_prompt_repository.py:13 |
  | PromptBuilderStage._store_prompt | [W]  | prompt_builder.py:547 |
  | TextAgent (load cached prompt)   | [R]  | agent.py:372          |
  +-----------------------------------------------------------------+

  generated_prompts [ZOMBIE]
  +-----------------------------------------------------------------+
  | GeneratedPromptRepository        | [RW] | db/repositories/generated_prompt_repository.py:14 |
  | create_log() exists              | ---  | generated_prompt_repository.py:24-65 |
  | PromptBuilderStage._store_prompt | ---  | prompt_builder.py:514-563 writes to ready_prompts |
  |                                  |      | but NEVER calls create_log() |
  +-----------------------------------------------------------------+


=============================================================================
DOMAIN 8: SCHEDULING & JOBS (4 tables)
=============================================================================

  scheduled_events
  +-----------------------------------------------------------------+
  | ScheduledEventRepository         | [RW] | db/repositories/scheduled_event_repository.py:26 |
  | ResponseDelivery.queue()         | [W]  | (delayed message delivery) |
  | Tasks: /deliver                  | [RW] | tasks.py:309,335      |
  +-----------------------------------------------------------------+

  scheduled_touchpoints
  +-----------------------------------------------------------------+
  | TouchpointStore                  | [RW] | touchpoints/store.py:22 |
  | TouchpointStage                  | [RW] | touchpoint.py:40 (via engine) |
  | Tasks: /touchpoints              | [RW] | tasks.py:953          |
  +-----------------------------------------------------------------+

  context_packages
  +-----------------------------------------------------------------+
  | PackageStore                     | [RW] | context/store.py:23   |
  | PromptBuilderStage (indirect)    | [R]  | (legacy context read)  |
  +-----------------------------------------------------------------+

  job_executions
  +-----------------------------------------------------------------+
  | JobExecutionRepository           | [RW] | db/repositories/job_execution_repository.py:16 |
  | All /tasks/* routes              | [W]  | tasks.py: start/complete/fail execution |
  | Portal: admin dashboard          | [R]  | (admin stats view)    |
  +-----------------------------------------------------------------+


=============================================================================
DOMAIN 9: PORTAL & PROFILE (8 tables)
=============================================================================

  user_profiles
  +-----------------------------------------------------------------+
  | ProfileRepository                | [RW] | db/repositories/profile_repository.py:31 |
  | MessageHandler._needs_onboarding | [R]  | message_handler.py:765 |
  | PromptBuilderStage._enrich       | [R]  | prompt_builder.py: via user.profile |
  +-----------------------------------------------------------------+

  user_backstories
  +-----------------------------------------------------------------+
  | BackstoryRepository              | [RW] | db/repositories/profile_repository.py:142 |
  | MessageHandler._needs_onboarding | [R]  | message_handler.py:769 |
  +-----------------------------------------------------------------+

  user_social_circles
  +-----------------------------------------------------------------+
  | SocialCircleRepository           | [RW] | db/repositories/social_circle_repository.py:21 |
  | EventStore.update_npc_state()    | [W]  | life_simulation/store.py:444-482 |
  | Portal: /social-circle           | [R]  | portal.py:733         |
  +-----------------------------------------------------------------+

  user_narrative_arcs
  +-----------------------------------------------------------------+
  | NarrativeArcRepository           | [RW] | db/repositories/narrative_arc_repository.py:22 |
  +-----------------------------------------------------------------+

  venue_cache
  +-----------------------------------------------------------------+
  | VenueCacheRepository             | [RW] | db/repositories/profile_repository.py:397 |
  +-----------------------------------------------------------------+

  onboarding_states
  +-----------------------------------------------------------------+
  | OnboardingStateRepository        | [RW] | db/repositories/profile_repository.py:242 |
  +-----------------------------------------------------------------+

  telegram_links
  +-----------------------------------------------------------------+
  | TelegramLinkRepository           | [RW] | db/repositories/telegram_link_repository.py:16 |
  | Portal: /link-telegram           | [W]  | portal.py:538         |
  +-----------------------------------------------------------------+

  pending_registrations
  +-----------------------------------------------------------------+
  | PendingRegistrationRepository    | [RW] | db/repositories/pending_registration_repository.py:17 |
  | Tasks: /cleanup                  | [W]  | tasks.py:643          |
  +-----------------------------------------------------------------+


=============================================================================
DOMAIN 10: ADMIN & AUDIT (2 tables)
=============================================================================

  audit_logs
  +-----------------------------------------------------------------+
  | AuditLog model                   | [W]  | db/models/audit_log.py |
  | Admin API routes                 | [RW] | api/routes/admin.py   |
  +-----------------------------------------------------------------+

  error_logs
  +-----------------------------------------------------------------+
  | ErrorLog model                   | [W]  | db/models/error_log.py |
  | Exception handlers               | [W]  | api/main.py           |
  +-----------------------------------------------------------------+


=============================================================================
DOMAIN 11: PSYCHE & CONFLICT (2 tables)
=============================================================================

  psyche_states
  +-----------------------------------------------------------------+
  | PsycheStateRepository            | [RW] | db/repositories/psyche_state_repository.py:20 |
  | MessageHandler (pre-conv read)   | [R]  | message_handler.py:252 |
  | Tasks: /psyche-batch             | [W]  | tasks.py:825 (via batch.py) |
  | Portal: /psyche-tips             | [R]  | portal.py:818         |
  +-----------------------------------------------------------------+

  daily_summaries
  +-----------------------------------------------------------------+
  | DailySummaryRepository           | [RW] | db/repositories/summary_repository.py:18 |
  | Tasks: /summary                  | [W]  | tasks.py:571          |
  | Portal: /daily-summaries         | [R]  | portal.py:237         |
  +-----------------------------------------------------------------+
```

---

## Diagram 3: Zombie Gap Analysis

Four zombie tables with exact gap locations and evidence.

```
=============================================================================
ZOMBIE 1: nikita_emotional_states
=============================================================================

  STORE (full CRUD exists):
  +-------------------------------------------------------------------+
  | emotional_state/store.py:StateStore                                |
  |                                                                    |
  | save_state()          line 96-124    INSERT INTO nikita_emotional_states |
  | update_state()        line 126-212   UPDATE nikita_emotional_states     |
  | get_current_state()   line 48-70     SELECT FROM nikita_emotional_states |
  | get_state_history()   line 216-250   SELECT (7-day lookback)            |
  | get_conflict_history()line 252-283   SELECT (conflict_state != 'none')  |
  | delete_state()        line 287-305   DELETE                             |
  +-------------------------------------------------------------------+

  PIPELINE (computes but never persists):
  +-------------------------------------------------------------------+
  | pipeline/stages/emotional.py:EmotionalStage._run()                 |
  |                                                                    |
  | line 53-60    from emotional_state.computer import StateComputer   |
  | line 61       computer = StateComputer()                           |
  | line 93-100   state = computer.compute(...)                        |
  | line 102-107  ctx.emotional_state = {                              |
  |                   "arousal": state.arousal,                        |
  |                   "valence": state.valence,                        |
  |                   "dominance": state.dominance,                    |
  |                   "intimacy": state.intimacy,                      |
  |               }                                                    |
  | line 108      except block                                         |
  |                                                                    |
  | >>> GAP: Between line 107 and line 108, there is NO call to        |
  |     StateStore.save_state() or StateStore.update_state()           |
  +-------------------------------------------------------------------+

  PORTAL (reads from empty/stale table):
  +-------------------------------------------------------------------+
  | api/routes/portal.py                                               |
  | line 562-563  store = get_state_store()                            |
  |               state = await store.get_current_state(user_id)       |
  | line 565-567  if not state: return defaults (all 0.5)              |
  |                                                                    |
  | CONSEQUENCE: /emotional-state always returns defaults because      |
  | the pipeline never writes computed states to the table.            |
  +-------------------------------------------------------------------+

  FIX (1 line after emotional.py:107):
  +-------------------------------------------------------------------+
  |                                                                    |
  |   ctx.emotional_state = {                                          |
  |       "arousal": state.arousal,                                    |
  |       "valence": state.valence,                                    |
  |       "dominance": state.dominance,                                |
  |       "intimacy": state.intimacy,                                  |
  |   }                                                                |
  | + # Persist to nikita_emotional_states for Portal reads            |
  | + if self._session:                                                |
  | +     from nikita.emotional_state.store import StateStore          |
  | +     store = StateStore(session_factory=                           |
  | +         _wrap_session(self._session))                            |
  | +     await store.save_state(state)                                |
  |                                                                    |
  +-------------------------------------------------------------------+

  FLOW DIAGRAM:
                                                  nikita_emotional_states
  StateComputer.compute()                               (TABLE)
        |                                                  ^
        v                                                  |
  ctx.emotional_state = {...}  ---[MISSING WRITE]--->  StateStore.save_state()
        |                                                  |
        v                                                  v
  PromptBuilderStage reads ctx     Portal reads table --> always defaults


=============================================================================
ZOMBIE 2: nikita_entities
=============================================================================

  STORE (full CRUD exists):
  +-------------------------------------------------------------------+
  | life_simulation/store.py:EventStore                                |
  |                                                                    |
  | save_entity()         line 341-362   INSERT INTO nikita_entities   |
  | save_entities()       line 364-375   Bulk insert (loop)            |
  | get_entities()        line 377-395   SELECT by user_id             |
  | get_entities_by_type()line 397-419   SELECT by entity_type         |
  | entity_exists()       line 421-440   SELECT 1 (existence check)    |
  +-------------------------------------------------------------------+

  PIPELINE (never calls entity store):
  +-------------------------------------------------------------------+
  | pipeline/stages/life_sim.py:LifeSimStage._run()                   |
  |                                                                    |
  | line 61-66   from life_simulation import LifeSimulator             |
  |              store = EventStore(session_factory=...)                |
  |              simulator = LifeSimulator(store=store)                 |
  | line 70      events = await simulator.get_today_events(user_id)    |
  | line 74      events = await simulator.generate_next_day_events(    |
  |                  user_id=ctx.user_id)                              |
  | line 78      ctx.life_events = events or []                        |
  |                                                                    |
  | >>> GAP: LifeSimulator methods:                                    |
  |     get_today_events()        -- calls store.get_events_for_date() |
  |                                  (reads nikita_life_events only)   |
  |     generate_next_day_events()-- calls store.save_events()         |
  |                                  (writes nikita_life_events only)  |
  |                                                                    |
  | Neither method extracts entities from LLM response or calls        |
  | store.save_entity() / store.save_entities()                        |
  +-------------------------------------------------------------------+

  SIMULATOR EVIDENCE:
  +-------------------------------------------------------------------+
  | life_simulation/simulator.py                                       |
  |                                                                    |
  | line 104     async def generate_next_day_events(...)               |
  |              --> generates LifeEvent objects via LLM                |
  |              --> calls self.store.save_events(events)               |
  |              --> returns events                                     |
  |              >>> NEVER calls save_entity() or save_entities()       |
  |                                                                    |
  | line 197     async def get_today_events(...)                       |
  |              --> calls self.store.get_events_for_date()             |
  |              --> pure read, no entity extraction                    |
  +-------------------------------------------------------------------+

  FIX (multi-line, in LifeSimulator.generate_next_day_events):
  +-------------------------------------------------------------------+
  |                                                                    |
  | After save_events(events), add:                                    |
  |                                                                    |
  | + # Extract and persist entities referenced in events              |
  | + entities_to_save = []                                            |
  | + for event in events:                                             |
  | +     for entity_name in event.entities:                           |
  | +         if not await self.store.entity_exists(user_id, entity_name): |
  | +             entities_to_save.append(NikitaEntity(                |
  | +                 user_id=user_id,                                 |
  | +                 entity_type=EntityType.PERSON,                   |
  | +                 name=entity_name,                                |
  | +             ))                                                   |
  | + if entities_to_save:                                             |
  | +     await self.store.save_entities(entities_to_save)             |
  |                                                                    |
  +-------------------------------------------------------------------+

  FLOW DIAGRAM:
  LifeSimulator.generate_next_day_events()
        |
        +--> store.save_events(events)        --> nikita_life_events [OK]
        |
        +--> store.save_entity(entity)        --> nikita_entities    [NEVER CALLED]
        |    ^^^^^^^^^^^^^^^^^^^^^^^^^
        |    Method exists on EventStore
        |    but no caller in simulator
        |
  LifeEvent.entities = ["Mia", "Cafe Luna"]  --> data exists in event JSON
                                                   but never normalized to
                                                   nikita_entities table


=============================================================================
ZOMBIE 3: message_embeddings [ZOMBIE --> DROP]
=============================================================================

  MODEL (exists, orphaned):
  +-------------------------------------------------------------------+
  | db/models/conversation.py:159-197                                  |
  |                                                                    |
  | class MessageEmbedding(Base, UUIDMixin):                           |
  |     __tablename__ = "message_embeddings"                           |
  |                                                                    |
  |     user_id         FK -> users.id                                 |
  |     conversation_id FK -> conversations.id                         |
  |     message_text    Text                                           |
  |     embedding       Vector(1536)  # OpenAI text-embedding-3-small  |
  |     role            String(20)    # 'user' | 'nikita'              |
  |     created_at      DateTime                                       |
  |                                                                    |
  |     conversation: Mapped["Conversation"] (back_populates)          |
  +-------------------------------------------------------------------+

  NO REPOSITORY:
  +-------------------------------------------------------------------+
  | There is NO MessageEmbeddingRepository in db/repositories/         |
  | No file matching *embedding* in repositories directory.            |
  +-------------------------------------------------------------------+

  NO PIPELINE WRITES:
  +-------------------------------------------------------------------+
  | No pipeline stage writes to message_embeddings.                    |
  | MemoryUpdateStage writes to memory_facts via SupabaseMemory        |
  | (which uses its own pgVector column on memory_facts table).        |
  +-------------------------------------------------------------------+

  REPLACEMENT:
  +-------------------------------------------------------------------+
  | Spec 042 replaced message_embeddings with memory_facts:            |
  |                                                                    |
  | memory_facts table:                                                |
  |   - fact (text)                                                    |
  |   - embedding (vector)        # pgVector                           |
  |   - graph_type (enum)         # user/relationship/nikita           |
  |   - source (text)             # pipeline_extraction                |
  |   - confidence (float)                                             |
  |                                                                    |
  | SupabaseMemory.add_fact()     --> INSERT into memory_facts         |
  | SupabaseMemory.search()       --> pgVector similarity search       |
  | SupabaseMemory.find_similar() --> dedup check (threshold=0.95)     |
  +-------------------------------------------------------------------+

  ACTION: Remove model + relationship
  +-------------------------------------------------------------------+
  | 1. Delete MessageEmbedding class (conversation.py:159-197)         |
  | 2. Remove Conversation.embeddings relationship                     |
  |    (grep for "embeddings" in conversation.py)                      |
  | 3. DROP TABLE message_embeddings (Supabase migration)              |
  +-------------------------------------------------------------------+

  FLOW DIAGRAM:
  OLD (dead):  Conversation --> MessageEmbedding --> Vector(1536)
                                ^^^^^^^^^^^^^^^^^
                                Never populated

  NEW (live):  Pipeline --> MemoryUpdateStage --> SupabaseMemory
                                                      |
                                                      v
                                                 memory_facts (pgVector)


=============================================================================
ZOMBIE 4: generated_prompts
=============================================================================

  MODEL + REPO (full CRUD exists):
  +-------------------------------------------------------------------+
  | db/models/generated_prompt.py:GeneratedPrompt                      |
  |   - user_id, conversation_id                                       |
  |   - prompt_content, token_count, generation_time_ms                |
  |   - meta_prompt_template, context_snapshot, platform               |
  |   - created_at                                                     |
  |                                                                    |
  | db/repositories/generated_prompt_repository.py:14-151              |
  |   GeneratedPromptRepository                                        |
  |   - create_log()              line 24-65   [NEVER CALLED]          |
  |   - get_by_user_id()          line 67-86                           |
  |   - get_by_template()         line 88-107                          |
  |   - get_recent_by_user_id()   line 109-132                         |
  |   - get_latest_by_user_id()   line 134-151                         |
  +-------------------------------------------------------------------+

  PIPELINE (writes to ready_prompts, skips generated_prompts):
  +-------------------------------------------------------------------+
  | pipeline/stages/prompt_builder.py:PromptBuilderStage               |
  |                                                                    |
  | _store_prompt()  line 514-563                                      |
  |                                                                    |
  | line 536-537  from ready_prompt_repository import ReadyPromptRepository |
  |               repo = ReadyPromptRepository(self._session)          |
  | line 547-556  await repo.set_current(                              |
  |                   user_id=ctx.user_id,                             |
  |                   platform=platform,                               |
  |                   prompt_text=prompt_text,                         |
  |                   token_count=token_count,                         |
  |                   pipeline_version="045-v1",                       |
  |                   generation_time_ms=gen_time_ms,                  |
  |                   context_snapshot=context_snapshot,                |
  |                   conversation_id=ctx.conversation_id,             |
  |               )                                                    |
  |                                                                    |
  | >>> GAP: After set_current() at line 556, there is NO call to      |
  |     GeneratedPromptRepository.create_log()                         |
  |                                                                    |
  | The data is available: user_id, prompt_text, token_count,          |
  | gen_time_ms, context_snapshot, platform, conversation_id           |
  | All parameters needed by create_log() are in scope.                |
  +-------------------------------------------------------------------+

  FIX (3 lines after prompt_builder.py:556):
  +-------------------------------------------------------------------+
  |                                                                    |
  |   await repo.set_current(                                          |
  |       user_id=ctx.user_id,                                         |
  |       platform=platform,                                           |
  |       prompt_text=prompt_text,                                     |
  |       ...                                                          |
  |   )                                                                |
  | + # Log to generated_prompts for admin debugging                   |
  | + from nikita.db.repositories.generated_prompt_repository import \ |
  | +     GeneratedPromptRepository                                    |
  | + gen_repo = GeneratedPromptRepository(self._session)              |
  | + await gen_repo.create_log(                                       |
  | +     user_id=ctx.user_id,                                        |
  | +     prompt_content=prompt_text,                                  |
  | +     token_count=token_count,                                     |
  | +     generation_time_ms=gen_time_ms,                              |
  | +     meta_prompt_template="045-v1",                               |
  | +     conversation_id=ctx.conversation_id,                         |
  | +     context_snapshot=context_snapshot,                            |
  | +     platform=platform,                                           |
  | + )                                                                |
  |                                                                    |
  +-------------------------------------------------------------------+

  FLOW DIAGRAM:
  PromptBuilderStage._store_prompt()
        |
        +--> ReadyPromptRepository.set_current()  --> ready_prompts     [OK]
        |                                              (active prompt)
        |
        +--> GeneratedPromptRepository.create_log()--> generated_prompts [NEVER CALLED]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
             Method exists, all params available,
             just never called from _store_prompt()


=============================================================================
ZOMBIE SUMMARY TABLE
=============================================================================

  +---------------------------+--------+----------+--------+-----------------+
  | Table                     | Store  | Pipeline | Portal | Action          |
  +---------------------------+--------+----------+--------+-----------------+
  | nikita_emotional_states   | FULL   | COMPUTE  | READ   | +1 line fix     |
  |                           | CRUD   | NO SAVE  | (stale)| emotional.py    |
  +---------------------------+--------+----------+--------+-----------------+
  | nikita_entities           | FULL   | NEVER    | NONE   | +10 lines fix   |
  |                           | CRUD   | CALLED   |        | simulator.py    |
  +---------------------------+--------+----------+--------+-----------------+
  | message_embeddings        | MODEL  | NONE     | NONE   | DROP TABLE      |
  |                           | ONLY   |          |        | Remove model    |
  +---------------------------+--------+----------+--------+-----------------+
  | generated_prompts         | FULL   | NEVER    | NONE   | +3 lines fix    |
  |                           | CRUD   | CALLED   |        | prompt_builder  |
  +---------------------------+--------+----------+--------+-----------------+

  Severity:
  - nikita_emotional_states: HIGH (Portal /emotional-state returns stale defaults)
  - nikita_entities: MEDIUM (entity normalization missing, events still have inline entities)
  - message_embeddings: LOW (dead table, safe to drop)
  - generated_prompts: LOW (admin debugging only, ready_prompts still works)
```

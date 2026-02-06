# Memory System Architecture

**Version**: 2.2.0
**Updated**: 2026-01-29
**Reference**: Spec 029 Context Comprehensive, Spec 030 Text Continuity, Spec 039 Unified Context Engine, Spec 040 Context Engine Enhancements

---

## Table of Contents

1. [Master System Overview](#1-master-system-overview)
2. [Three-Graph Memory Architecture](#2-three-graph-memory-architecture)
3. [Text Agent Context Pipeline](#3-text-agent-context-pipeline)
   - [3.1 Working Memory System (Spec 030)](#31-working-memory-system-spec-030)
4. [Voice Agent Context Pipeline](#4-voice-agent-context-pipeline)
5. [Memory Storage Flow](#5-memory-storage-flow-post-processing)
6. [Humanization Integration](#6-humanization-integration)
7. [Token Budget Summary](#7-token-budget-summary)
8. [Key File References](#8-key-file-references)
9. [Unified Context Engine (Spec 039/040)](#9-spec-039-unified-context-engine)

---

## 1. Master System Overview

High-level view of all Nikita system components and data flow.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    NIKITA SYSTEM ARCHITECTURE                             │
└──────────────────────────────────────────────────────────────────────────┘

┌───────────────────────┐    ┌───────────────────────┐
│   TELEGRAM BOT        │    │   VOICE CALL          │
│   @Nikita_my_bot      │    │   ElevenLabs Conv AI  │
│                       │    │   +41 78 795 0009     │
└─────────┬─────────────┘    └─────────┬─────────────┘
          │ Webhook                    │ WebSocket
          ▼                            ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                 CLOUD RUN: nikita-api                                     │
│                 (us-central1, gcp-transcribe-test)                        │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌─────────────────────┐    ┌─────────────────────────┐                  │
│  │ TEXT AGENT PIPELINE │    │ VOICE AGENT PIPELINE    │                  │
│  │                     │    │                         │                  │
│  │ MessageHandler      │    │ VoiceService            │                  │
│  │   ↓                 │    │   ↓                     │                  │
│  │ MetaPromptService   │    │ ServerToolHandler       │                  │
│  │   ↓                 │    │   ↓                     │                  │
│  │ nikita_agent        │    │ ElevenLabs (get_context │                  │
│  │   ↓                 │    │  get_memory, score_turn)│                  │
│  │ PostProcessor       │    │                         │                  │
│  │  (9-stage async)    │    │                         │                  │
│  └─────────────────────┘    └─────────────────────────┘                  │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
          │                            │
          ▼                            ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         DATA LAYER                                        │
├──────────────────────────────┬───────────────────────────────────────────┤
│                              │                                            │
│  ┌────────────────────────┐  │  ┌─────────────────────────────────────┐  │
│  │ SUPABASE (PostgreSQL)  │  │  │ NEO4J AURA (Graphiti)               │  │
│  │                        │  │  │                                     │  │
│  │ • users                │  │  │ USER_GRAPH_{user_id}                │  │
│  │ • user_metrics         │  │  │   └─ facts, preferences             │  │
│  │ • conversations        │  │  │                                     │  │
│  │ • conversation_threads │  │  │ RELATIONSHIP_GRAPH_{user_id}        │  │
│  │ • nikita_thoughts      │  │  │   └─ episodes, milestones           │  │
│  │ • daily_summaries      │  │  │                                     │  │
│  │ • user_vice_prefs      │  │  │ NIKITA_GRAPH_{user_id}              │  │
│  │ • generated_prompts    │  │  │   └─ events, thoughts               │  │
│  │ • engagement_states    │  │  │                                     │  │
│  └────────────────────────┘  │  └─────────────────────────────────────┘  │
│                              │                                            │
└──────────────────────────────┴───────────────────────────────────────────┘
          │                            │
          ▼                            ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                  HUMANIZATION MODULES (Specs 021-028)                     │
│                                                                           │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────────────────┐ │
│  │ 021        │ │ 022        │ │ 023        │ │ 024                    │ │
│  │ Hierarchic │ │ Life Sim   │ │ Emotional  │ │ Behavioral Meta-Instr  │ │
│  └────────────┘ └────────────┘ └────────────┘ └────────────────────────┘ │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────────────────┐ │
│  │ 025        │ │ 026        │ │ 027        │ │ 028                    │ │
│  │ Proactive  │ │ Text Patt  │ │ Conflict   │ │ Voice Onboarding       │ │
│  └────────────┘ └────────────┘ └────────────┘ └────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Three-Graph Memory Architecture

Graphiti temporal knowledge graphs stored in Neo4j Aura.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                THREE-GRAPH MEMORY ARCHITECTURE                            │
│                nikita/memory/graphiti_client.py:25-286                    │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│                        NikitaMemory Class                                 │
│                        graphiti_client.py:25-286                          │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  __init__(user_id: str)                                                   │
│    • Connects to Neo4j Aura (settings.neo4j_uri)                          │
│    • Configures Anthropic LLM client (claude-sonnet-4-5)                  │
│    • Configures OpenAI embedder (text-embedding-3-small)                  │
│                                                                           │
│  METHODS:                                                                 │
│  ├─ add_episode(content, source, graph_type)     :83-110                  │
│  ├─ search_memory(query, graph_types, limit)     :112-149                 │
│  ├─ get_context_for_prompt(user_message)         :151-195                 │
│  ├─ add_user_fact(fact, confidence)              :197-220                 │
│  ├─ get_user_facts(limit=50)                     :222-248                 │
│  ├─ add_relationship_episode(description, type)  :250-267                 │
│  └─ add_nikita_event(description, event_type)    :269-286                 │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                      THREE KNOWLEDGE GRAPHS                               │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ USER_GRAPH_{user_id}                                               │  │
│  │ "What Nikita knows about the player"                               │  │
│  ├────────────────────────────────────────────────────────────────────┤  │
│  │ LIMIT: 50 (standard), 100 (full)                                   │  │
│  │                                                                    │  │
│  │ CONTENT:                                                           │  │
│  │ • Explicit facts: "User works in finance"                          │  │
│  │ • Implicit facts: "User seems stressed about work"                 │  │
│  │ • Preferences: "Prefers morning conversations"                     │  │
│  │                                                                    │  │
│  │ SOURCE: user_message → add_user_fact() → PostProcessor             │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ RELATIONSHIP_GRAPH_{user_id}                                       │  │
│  │ "Shared history between Nikita and player"                         │  │
│  ├────────────────────────────────────────────────────────────────────┤  │
│  │ LIMIT: 30 (standard), 50 (full)                                    │  │
│  │                                                                    │  │
│  │ CONTENT:                                                           │  │
│  │ • Episodes: "We talked about his promotion"                        │  │
│  │ • Milestones: "[milestone] First time he called me baby"           │  │
│  │ • Inside jokes: "[inside_joke] The 'Trust me, I'm a hacker' mug"   │  │
│  │                                                                    │  │
│  │ SOURCE: conversations → add_relationship_episode() → PostProcessor │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ NIKITA_GRAPH_{user_id}                                             │  │
│  │ "Nikita's simulated life, exists independently"                    │  │
│  ├────────────────────────────────────────────────────────────────────┤  │
│  │ LIMIT: 20 (standard), 30 (full)                                    │  │
│  │                                                                    │  │
│  │ CONTENT:                                                           │  │
│  │ • Work events: "[work_project] Finished security audit"            │  │
│  │ • Life events: "[life_event] Had brunch with college friends"      │  │
│  │ • Thoughts: "[thought] Wondering if he'll text today"              │  │
│  │                                                                    │  │
│  │ SOURCE: Life simulation (022) → add_nikita_event() → PostProcessor │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│                    GRAPH QUERY FLOW (Parallel)                            │
│                    MetaPromptService._load_memory_context()               │
│                    service.py:349-479                                     │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│                 ┌──────────────────────────────┐                          │
│                 │      asyncio.gather()        │                          │
│                 └──────────────────────────────┘                          │
│                               │                                           │
│          ┌────────────────────┼────────────────────┐                      │
│          ▼                    ▼                    ▼                      │
│  ┌──────────────┐   ┌────────────────┐   ┌──────────────┐                │
│  │ _query_graph │   │ _query_graph   │   │ _query_graph │                │
│  │ ("user", 50) │   │ ("relation",30)│   │ ("nikita",20)│                │
│  └──────┬───────┘   └───────┬────────┘   └──────┬───────┘                │
│         │                   │                   │                         │
│         ▼                   ▼                   ▼                         │
│  context.user_facts   context.rel_episodes   context.nikita_events       │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Text Agent Context Pipeline

Full data flow from Telegram message to LLM response.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                   TEXT AGENT CONTEXT PIPELINE                             │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│ STAGE 1: MESSAGE HANDLING                                                 │
│ nikita/platforms/telegram/message_handler.py:51-200+                      │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  Telegram Webhook → POST /telegram/webhook                                │
│       │                                                                   │
│       ▼                                                                   │
│  MessageHandler.handle(message)                                           │
│       │                                                                   │
│       ├──► Authentication check (user_repository.get_by_telegram_id)      │
│       ├──► Onboarding gate (profile + backstory exists?)                  │
│       ├──► Game status check (boss_fight / game_over / won)               │
│       ├──► Rate limiting (20 msg/min, 500 msg/day)                        │
│       └──► Conversation tracking (get_or_create_conversation)             │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ STAGE 2: CONTEXT LOADING                                                  │
│ nikita/meta_prompts/service.py:211-479                                    │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  MetaPromptService._load_context(user_id)                                 │
│       │                                                                   │
│       ├──► FROM SUPABASE (Primary):                                       │
│       │    • UserRepository.get(user_id)                                  │
│       │      └─ chapter, relationship_score, game_status, days_played     │
│       │    • User.metrics (joined)                                        │
│       │      └─ intimacy, passion, trust, secureness                      │
│       │    • User.engagement_state (joined)                               │
│       │      └─ state, calibration_score, multiplier                      │
│       │    • User.vice_preferences (joined)                               │
│       │      └─ category, intensity_level, engagement_score               │
│       │    • ProfileRepository, BackstoryRepository                       │
│       │      └─ venue, how_we_met, the_moment, unresolved_hook            │
│       │                                                                   │
│       ├──► FROM SUPABASE (Threads & Thoughts):                            │
│       │    • ConversationThreadRepository.get_threads_for_prompt()        │
│       │      └─ follow_up, question, promise, topic threads               │
│       │    • NikitaThoughtRepository.get_thoughts_for_prompt()            │
│       │      └─ thinking, wants_to_share, question, feeling               │
│       │    • DailySummaryRepository.get_by_date() / get_range()           │
│       │      └─ today_summary, week_summaries (last 7 days)               │
│       │                                                                   │
│       └──► FROM GRAPHITI (Memory):  [_load_memory_context:349-479]        │
│            • asyncio.gather() - PARALLEL 3-GRAPH QUERY                    │
│            • _query_graph("user", limit=50) → context.user_facts          │
│            • _query_graph("relationship", 30) → context.rel_episodes      │
│            • _query_graph("nikita", limit=20) → context.nikita_events     │
│                                                                           │
│       └──► FROM HUMANIZATION: [_load_behavioral_instructions:481-541]     │
│            • MetaInstructionEngine.get_instructions_for_context()         │
│            • behavioral_instructions, conflict_state                      │
│                                                                           │
│  RESULT: MetaPromptContext with 20+ fields populated                      │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ STAGE 3: PROMPT GENERATION & LLM CALL                                     │
│ nikita/agents/text/agent.py:264-319                                       │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  generate_response(deps, user_message)                                    │
│       │                                                                   │
│       ├──► build_system_prompt()                                          │
│       │    └─► MetaPromptService.generate_system_prompt()                 │
│       │        └─► _format_template("system_prompt.meta.md", context)     │
│       │            ┌────────────────────────────────────────────────┐     │
│       │            │ TEMPLATE REPLACEMENTS:                         │     │
│       │            │ {{chapter}}, {{chapter_name}}, {{relationship}}│     │
│       │            │ {{intimacy}}, {{passion}}, {{trust}}           │     │
│       │            │ {{engagement_state}}, {{calibration_status}}   │     │
│       │            │ {{vice_profile}}, {{nikita_mood}}              │     │
│       │            │ {{user_facts}}, {{relationship_episodes}}      │     │
│       │            │ {{open_threads}}, {{active_thoughts}}          │     │
│       │            │ {{backstory_section}}, {{behavioral_instr}}    │     │
│       │            └────────────────────────────────────────────────┘     │
│       │                                                                   │
│       └──► nikita_agent.run(user_message, deps=deps)                      │
│            ├─► @agent.instructions: add_chapter_behavior()                │
│            └─► @agent.instructions: add_personalized_context()            │
│                                                                           │
│  PYDANTIC AI + CLAUDE SONNET (claude-sonnet-4-5-20250929)                 │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ STAGE 4: POST-PROCESSING (Async, 9 stages)                                │
│ nikita/context/post_processor.py:76-664                                   │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  TRIGGERED BY: 15min timeout OR pg_cron /tasks/process-conversations      │
│                                                                           │
│  PostProcessor.process_conversation(conversation_id)                      │
│       │                                                                   │
│       ├──► Stage 1: Ingestion (load transcript)                           │
│       ├──► Stage 2-5: LLM Extraction via MetaPromptService                │
│       │    └─ extract_entities() → facts, threads, thoughts, summary      │
│       ├──► Stage 4: Create threads (ConversationThreadRepository)         │
│       ├──► Stage 5: Create thoughts (NikitaThoughtRepository)             │
│       ├──► Stage 6: Graph Updates (NikitaMemory.add_*)                    │
│       │    └─ add_user_fact(), add_relationship_episode()                 │
│       ├──► Stage 7: Summary Rollups (DailySummaryRepository)              │
│       ├──► Stage 7.5: Vice Processing (ViceService)                       │
│       └──► Stage 8: Finalization (mark_processed)                         │
│                                                                           │
│  OUTPUT: Updated graphs, threads, thoughts, summaries                     │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

---

### 3.1 Working Memory System (Spec 030)

4-tier working memory for conversation continuity (87 tests).

```
┌──────────────────────────────────────────────────────────────────────────┐
│                   4-TIER WORKING MEMORY SYSTEM                            │
│                   Spec 030: Text Continuity                               │
└──────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ TIER 1: MESSAGE HISTORY (3000 tokens)                                    │
│ nikita/agents/text/history.py                                            │
├─────────────────────────────────────────────────────────────────────────┤
│ HistoryLoader.load()                                                     │
│   ├─ conversation.messages JSONB → list[ModelMessage]                    │
│   ├─ Token budget enforcement (truncate oldest first)                    │
│   ├─ Tool call pairing verification                                      │
│   └─ Returns None for new sessions (triggers @agent.instructions)        │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ TIER 2: TODAY BUFFER (500 tokens)                                        │
│ MetaPromptService._format_today_section()                                │
├─────────────────────────────────────────────────────────────────────────┤
│ • daily_summaries.summary_text                                           │
│ • key_moments[] (max 5, most recent)                                     │
│ • Format: "Earlier today: ..."                                           │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ TIER 3: OPEN THREADS (400 tokens)                                        │
│ MetaPromptService._format_open_threads_section()                         │
├─────────────────────────────────────────────────────────────────────────┤
│ • conversation_threads WHERE status='open'                               │
│ • Priority: promise/unresolved=10, curiosity=7, callback=4               │
│ • Recency score: 10 (today) → 1 (7 days), 50% penalty >7 days            │
│ • Max 5 threads                                                          │
│ • Format: "Unfinished Topics: ..."                                       │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ TIER 4: LAST CONVERSATION (300 tokens)                                   │
│ MetaPromptService._format_last_conversation_section()                    │
├─────────────────────────────────────────────────────────────────────────┤
│ • conversations.nikita_summary (prior session, >24h old)                 │
│ • Format: "Last time we talked: ..."                                     │
│ • Truncated to ~1200 chars if needed                                     │
└─────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ TOKEN BUDGET MANAGER                                                     │
│ nikita/agents/text/token_budget.py                                       │
├─────────────────────────────────────────────────────────────────────────┤
│ TokenBudgetManager.allocate(TierContent) → TokenUsage                    │
│                                                                          │
│ Truncation Priority (lowest first):                                      │
│ 1. Last Conversation → 2. Threads → 3. Today → 4. History                │
│                                                                          │
│ Hard Cap: 6150 tokens                                                    │
│ Min History Preserved: 100 tokens (~10 turns)                            │
└─────────────────────────────────────────────────────────────────────────┘
```

**PydanticAI Integration**:

```
User Message (Telegram)
    ↓
MessageHandler: loads conversation.messages JSONB
    ↓
NikitaDeps: carries conversation_messages + conversation_id
    ↓
generate_response() [agent.py]
    ├─ HistoryLoader.load() → list[ModelMessage] | None
    ├─ build_system_prompt() [if message_history=None]
    │   └─ MetaPromptService (today buffer, threads, last conversation)
    └─ nikita_agent.run(message_history=...) [PydanticAI]
    ↓
Nikita Response
```

**Critical Implementation Detail**: HistoryLoader returns `None` (not empty list) for new sessions to trigger `@agent.instructions` decorators. Per PydanticAI docs: "If message_history is set and not empty, a new system prompt is not generated."

---

## 4. Voice Agent Context Pipeline

Full data flow for ElevenLabs voice calls.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                   VOICE AGENT CONTEXT PIPELINE                            │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│ STAGE 1: CALL INITIATION                                                  │
│ nikita/agents/voice/service.py:41-158                                     │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  POST /api/v1/voice/initiate OR Inbound call (Twilio → /pre-call)         │
│       │                                                                   │
│       ▼                                                                   │
│  VoiceService.initiate_call(user_id)                                      │
│       │                                                                   │
│       ├──► _load_user() - Eager loads: metrics, engagement_state, vices   │
│       ├──► _load_context() → VoiceContext (models.py)                     │
│       ├──► _generate_session_id()                                         │
│       ├──► _generate_signed_token(user_id, session_id) - HMAC-SHA256      │
│       └──► MetaPromptService.generate_system_prompt()                     │
│                                                                           │
│  RETURNS:                                                                 │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ {                                                                  │  │
│  │   "agent_id": ELEVENLABS_DEFAULT_AGENT_ID,                         │  │
│  │   "signed_token": "user_id:session_id:timestamp:signature",        │  │
│  │   "session_id": "unique-session-uuid",                             │  │
│  │   "context": VoiceContext,                                         │  │
│  │   "dynamic_variables": { user_name, chapter, mood, ... },          │  │
│  │   "conversation_config_override": { agent: { prompt, first_msg } } │  │
│  │ }                                                                  │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ STAGE 2: ELEVENLABS CALL                                                  │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ElevenLabs Conversational AI 2.0                                         │
│       │                                                                   │
│       ├──► System prompt (personalized via MetaPromptService)             │
│       ├──► First message (chapter-appropriate greeting)                   │
│       └──► TTS settings (stability, speed based on chapter/mood)          │
│                                                                           │
│  DURING CALL: Agent calls Server Tools via webhooks                       │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ STAGE 3: SERVER TOOLS                                                     │
│ nikita/agents/voice/server_tools.py:87-834                                │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  POST /api/v1/voice/server-tool → ServerToolHandler.handle(request)       │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ GET_CONTEXT (server_tools.py:203-483)                              │  │
│  │ Returns 29+ fields for LLM context:                                │  │
│  ├────────────────────────────────────────────────────────────────────┤  │
│  │ FROM SUPABASE:                                                     │  │
│  │ • user_name, chapter, game_status, engagement_state                │  │
│  │ • relationship_score, intimacy, passion, trust, secureness         │  │
│  │ • hours_since_last, time_of_day, day_of_week                       │  │
│  │ • nikita_activity, nikita_energy, nikita_mood                      │  │
│  │ • primary_vice, vice_severity, all_vices[]                         │  │
│  │ • active_thoughts{}, today_summary, week_summaries{}               │  │
│  │ • backstory{ venue_name, how_we_met, the_moment }                  │  │
│  │                                                                    │  │
│  │ FROM GRAPHITI (3-graph parallel query):                            │  │
│  │ • user_facts[] (limit 50)                                          │  │
│  │ • relationship_episodes[] (limit 30)                               │  │
│  │ • nikita_events[] (limit 20)                                       │  │
│  │                                                                    │  │
│  │ FROM HUMANIZATION (server_tools.py:571-662):                       │  │
│  │ • nikita_daily_events[], nikita_recent_events[]                    │  │
│  │ • nikita_mood_4d{ arousal, valence, dominance, intimacy }          │  │
│  │ • active_conflict{ type, severity, stage }                         │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ GET_MEMORY (server_tools.py:664-718)                               │  │
│  │ Query Graphiti + load threads                                      │  │
│  ├────────────────────────────────────────────────────────────────────┤  │
│  │ INPUT: query, limit                                                │  │
│  │ • memory.search_memory(query) → facts[]                            │  │
│  │ • ConversationThreadRepository.get_open_threads() → threads[]      │  │
│  │ RETURNS: { "facts": [...], "threads": [...] }                      │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ SCORE_TURN (server_tools.py:720-788)                               │  │
│  │ Analyze conversation exchange for metric deltas                    │  │
│  ├────────────────────────────────────────────────────────────────────┤  │
│  │ INPUT: user_message, nikita_response                               │  │
│  │ • Build ConversationContext from user                              │  │
│  │ • ScoreAnalyzer.analyze(user_msg, nikita_resp, context)            │  │
│  │ RETURNS: { intimacy_delta, passion_delta, trust_delta,             │  │
│  │            secureness_delta, analysis_summary }                    │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ UPDATE_MEMORY (server_tools.py:790-820)                            │  │
│  │ Store new fact to Graphiti                                         │  │
│  ├────────────────────────────────────────────────────────────────────┤  │
│  │ INPUT: fact, category                                              │  │
│  │ • memory.add_user_fact(fact, category)                             │  │
│  │ RETURNS: { "stored": true, "fact": "...", "category": "..." }      │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ STAGE 4: CALL END                                                         │
│ POST /api/v1/voice/webhook (call_ended event)                             │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  VoiceService.end_call(session_id)                                        │
│       │                                                                   │
│       ├──► Fetch transcript from ElevenLabs                               │
│       ├──► Score call (VoiceCallScorer)                                   │
│       ├──► Update user metrics                                            │
│       └──► Log call_ended event                                           │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Memory Storage Flow (Post-Processing)

9-stage async pipeline writing to graphs.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                  MEMORY STORAGE FLOW (POST-PROCESSING)                    │
│                  nikita/context/post_processor.py:76-664                  │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│ TRIGGER                                                                   │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌─────────────────────┐      ┌──────────────────────────────────────┐   │
│  │ SessionDetector     │  OR  │ pg_cron /tasks/process-conversations │   │
│  │ (15min text timeout)│      │ (every minute)                       │   │
│  └─────────┬───────────┘      └────────────────┬─────────────────────┘   │
│            │                                   │                          │
│            └───────────────┬───────────────────┘                          │
│                            ▼                                              │
│              PostProcessor.process_conversation()                         │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 9-STAGE PIPELINE                                                          │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌─ STAGE 1: INGESTION (:258-280) ──────────────────────────────────────┐│
│  │ • Load conversation from ConversationRepository                      ││
│  │ • Validate has messages                                              ││
│  │ • Mark as processing                                                 ││
│  └──────────────────────────────────────────────────────────────────────┘│
│                                 │                                         │
│                                 ▼                                         │
│  ┌─ STAGES 2-5: LLM EXTRACTION (:282-378) ──────────────────────────────┐│
│  │ • Format messages for LLM (_format_messages)                         ││
│  │ • Load open threads for resolution detection                         ││
│  │ • Call MetaPromptService.extract_entities(conversation, open_threads)││
│  │                                                                      ││
│  │ EXTRACTS:                                                            ││
│  │ ├─ user_facts: [{ category, content }]                               ││
│  │ ├─ threads: [{ thread_type, topic/hook }]                            ││
│  │ ├─ nikita_thoughts: [{ thought_type, content }]                      ││
│  │ ├─ emotional_markers: [{ emotion_type, intensity, context }]         ││
│  │ └─ summary: "Conversation summary text"                              ││
│  └──────────────────────────────────────────────────────────────────────┘│
│                                 │                                         │
│            ┌────────────────────┼────────────────────┐                    │
│            ▼                    ▼                    ▼                    │
│  ┌─ STAGE 4 ──────┐   ┌─ STAGE 5 ──────┐   ┌─ PARALLEL ─────────────┐   │
│  │ THREADS        │   │ THOUGHTS       │   │                        │   │
│  │ (:390-429)     │   │ (:431-460)     │   │ (run concurrently)     │   │
│  │                │   │                │   │                        │   │
│  │ • Resolve old  │   │ • Create new   │   │                        │   │
│  │   thread IDs   │   │   thoughts     │   │                        │   │
│  │ • Create new   │   │                │   │                        │   │
│  │   threads      │   │ TYPES:         │   │                        │   │
│  │                │   │ • thinking     │   │                        │   │
│  │ TYPES:         │   │ • wants_share  │   │                        │   │
│  │ • follow_up    │   │ • question     │   │                        │   │
│  │ • question     │   │ • feeling      │   │                        │   │
│  │ • promise      │   │                │   │                        │   │
│  │ • topic        │   │                │   │                        │   │
│  └────────────────┘   └────────────────┘   └────────────────────────┘   │
│                                 │                                         │
│                                 ▼                                         │
│  ┌─ STAGE 6: GRAPH UPDATES (:462-544) ──────────────────────────────────┐│
│  │ • get_memory_client(user_id)                                         ││
│  │                                                                      ││
│  │ USER_GRAPH:                                                          ││
│  │ • memory.add_user_fact(fact, confidence=0.8) for each fact           ││
│  │                                                                      ││
│  │ RELATIONSHIP_GRAPH:                                                  ││
│  │ • memory.add_relationship_episode(summary, "conversation")           ││
│  │ • memory.add_relationship_episode(moment, "milestone"/"general")     ││
│  │                                                                      ││
│  │ NIKITA_GRAPH:                                                        ││
│  │ • memory.add_nikita_event(thought.content, "thought") for top 2      ││
│  └──────────────────────────────────────────────────────────────────────┘│
│                                 │                                         │
│                                 ▼                                         │
│  ┌─ STAGE 7: SUMMARY ROLLUPS (:546-587) ────────────────────────────────┐│
│  │ • Get or create DailySummary for today                               ││
│  │ • Append conversation summary to day's summary                       ││
│  │ • Add key moments with source conversation ID                        ││
│  └──────────────────────────────────────────────────────────────────────┘│
│                                 │                                         │
│                                 ▼                                         │
│  ┌─ STAGE 7.5: VICE PROCESSING (:589-640) ──────────────────────────────┐│
│  │ • ViceService.process_conversation()                                 ││
│  │ • Iterate through message pairs (user→nikita)                        ││
│  │ • Detect vice signals, update UserVicePreference                     ││
│  └──────────────────────────────────────────────────────────────────────┘│
│                                 │                                         │
│                                 ▼                                         │
│  ┌─ STAGE 8: FINALIZATION ──────────────────────────────────────────────┐│
│  │ • conversation_repo.mark_processed(summary, tone, entities)          ││
│  │ • Return PipelineResult                                              ││
│  └──────────────────────────────────────────────────────────────────────┘│
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Humanization Integration

How specs 021-028 wire into context.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     HUMANIZATION INTEGRATION                              │
│                     Specs 021-028 → Context Pipeline                      │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│ ENTRY POINTS                                                              │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  TEXT AGENT:                                                              │
│  MetaPromptService._load_context() (service.py:211-347)                   │
│       └──► _load_behavioral_instructions() (service.py:481-541)           │
│                                                                           │
│  VOICE AGENT:                                                             │
│  ServerToolHandler._get_context() (server_tools.py:203-483)               │
│       └──► _add_humanization_context() (server_tools.py:571-662)          │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ HUMANIZATION MODULES BY SPEC                                              │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ SPEC 021: HIERARCHICAL PROMPT COMPOSITION                          │  │
│  │ Module: nikita/context/composer.py                                 │  │
│  │ Tests: 345                                                         │  │
│  ├────────────────────────────────────────────────────────────────────┤  │
│  │ PROVIDES: 6-layer prompt architecture                              │  │
│  │ WIRED VIA: MetaPromptService._format_template()                    │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ SPEC 022: LIFE SIMULATION ENGINE                                   │  │
│  │ Module: nikita/life_simulation/                                    │  │
│  │ Tests: 212                                                         │  │
│  ├────────────────────────────────────────────────────────────────────┤  │
│  │ PROVIDES:                                                          │  │
│  │ • nikita_daily_events[] - Events from today                        │  │
│  │ • nikita_recent_events[] - Events from past week                   │  │
│  │ • nikita_active_arcs[] - Ongoing narrative arcs                    │  │
│  │ WIRED VIA: server_tools.py:591-606 (voice)                         │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ SPEC 023: EMOTIONAL STATE ENGINE                                   │  │
│  │ Module: nikita/emotional_state/                                    │  │
│  │ Tests: 233                                                         │  │
│  ├────────────────────────────────────────────────────────────────────┤  │
│  │ PROVIDES:                                                          │  │
│  │ • nikita_mood_4d: { arousal, valence, dominance, intimacy }        │  │
│  │   - arousal: 0-1 (calm to excited)                                 │  │
│  │   - valence: 0-1 (negative to positive)                            │  │
│  │   - dominance: 0-1 (submissive to dominant)                        │  │
│  │   - intimacy: 0-1 (distant to intimate)                            │  │
│  │ WIRED VIA: server_tools.py:614-637 (voice)                         │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ SPEC 024: BEHAVIORAL META-INSTRUCTIONS                             │  │
│  │ Module: nikita/behavioral/                                         │  │
│  │ Tests: 166                                                         │  │
│  ├────────────────────────────────────────────────────────────────────┤  │
│  │ PROVIDES:                                                          │  │
│  │ • behavioral_instructions - Situational guidance text              │  │
│  │ • conflict_state - Current conflict status                         │  │
│  │ WIRED VIA: service.py:481-541 (text)                               │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ SPEC 025: PROACTIVE TOUCHPOINT SYSTEM                              │  │
│  │ Module: nikita/touchpoints/                                        │  │
│  │ Tests: 189                                                         │  │
│  ├────────────────────────────────────────────────────────────────────┤  │
│  │ PROVIDES: Nikita-initiated messages via pg_cron                    │  │
│  │ TRIGGERED VIA: pg_cron /tasks/deliver-scheduled-messages           │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ SPEC 026: TEXT BEHAVIORAL PATTERNS                                 │  │
│  │ Module: nikita/text_patterns/                                      │  │
│  │ Tests: 167                                                         │  │
│  ├────────────────────────────────────────────────────────────────────┤  │
│  │ PROVIDES: Emoji patterns, message length, response timing          │  │
│  │ WIRED VIA: Template variables in system_prompt.meta.md             │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ SPEC 027: CONFLICT GENERATION SYSTEM                               │  │
│  │ Module: nikita/conflicts/                                          │  │
│  │ Tests: 263                                                         │  │
│  ├────────────────────────────────────────────────────────────────────┤  │
│  │ PROVIDES:                                                          │  │
│  │ • active_conflict: { type, severity, stage, triggered_at }         │  │
│  │ • Breakup mechanics (game_over triggers)                           │  │
│  │ WIRED VIA: server_tools.py:639-660 (voice)                         │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ SPEC 028: VOICE ONBOARDING                                         │  │
│  │ Module: nikita/onboarding/                                         │  │
│  │ Tests: 230                                                         │  │
│  ├────────────────────────────────────────────────────────────────────┤  │
│  │ PROVIDES:                                                          │  │
│  │ • Meta-Nikita agent configuration                                  │  │
│  │ • Profile collection via voice                                     │  │
│  │ • Backstory generation                                             │  │
│  │ WIRED VIA: POST /api/v1/onboarding/initiate, /pre-call             │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Token Budget Summary

Tiered context loading for Spec 029.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                       TOKEN BUDGET SUMMARY                                │
│                       nikita/meta_prompts/service.py:81-106               │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│ TIER LIMITS                                                               │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌───────────────────────────────────────────────────────────────────┐   │
│  │ TIER 1: CRITICAL (~4,000 tokens)                                  │   │
│  │ When remaining budget < 4,000                                     │   │
│  ├───────────────────────────────────────────────────────────────────┤   │
│  │ • user_facts: 20                                                  │   │
│  │ • relationship_episodes: 10                                       │   │
│  │ • nikita_events: 5                                                │   │
│  │ • threads: 5                                                      │   │
│  │ • thoughts: 5                                                     │   │
│  └───────────────────────────────────────────────────────────────────┘   │
│                                                                           │
│  ┌───────────────────────────────────────────────────────────────────┐   │
│  │ TIER 2: STANDARD (~7,000 tokens) - DEFAULT                        │   │
│  │ When remaining budget 4,000-8,000                                 │   │
│  ├───────────────────────────────────────────────────────────────────┤   │
│  │ • user_facts: 50                                                  │   │
│  │ • relationship_episodes: 30                                       │   │
│  │ • nikita_events: 20                                               │   │
│  │ • threads: 10                                                     │   │
│  │ • thoughts: 10                                                    │   │
│  └───────────────────────────────────────────────────────────────────┘   │
│                                                                           │
│  ┌───────────────────────────────────────────────────────────────────┐   │
│  │ TIER 3: FULL (~10,000+ tokens)                                    │   │
│  │ When remaining budget > 8,000                                     │   │
│  ├───────────────────────────────────────────────────────────────────┤   │
│  │ • user_facts: 100                                                 │   │
│  │ • relationship_episodes: 50                                       │   │
│  │ • nikita_events: 30                                               │   │
│  │ • threads: 15                                                     │   │
│  │ • thoughts: 15                                                    │   │
│  └───────────────────────────────────────────────────────────────────┘   │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│ TOKEN BUDGET BREAKDOWN                                                    │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  MAX_TOTAL_TOKENS = 12,000                                                │
│  TARGET_TOKENS = 10,000                                                   │
│                                                                           │
│  ┌───────────────────────────────────────────────────────────────────┐   │
│  │ COMPONENT                         │ TOKENS   │ % OF TARGET        │   │
│  ├───────────────────────────────────────────────────────────────────┤   │
│  │ Core Identity (NIKITA_PERSONA)    │ ~800     │ 8%                 │   │
│  │ Memory (3-graph facts/episodes)   │ ~3,500   │ 35%                │   │
│  │ Conversation (threads, thoughts)  │ ~3,000   │ 30%                │   │
│  │ State (chapter, vices, engagement)│ ~700     │ 7%                 │   │
│  │ Humanization (behavioral)         │ ~1,000   │ 10%                │   │
│  │ Backstory (onboarding context)    │ ~500     │ 5%                 │   │
│  │ Buffer (overhead, formatting)     │ ~500     │ 5%                 │   │
│  ├───────────────────────────────────────────────────────────────────┤   │
│  │ TOTAL                             │ ~10,000  │ 100%               │   │
│  └───────────────────────────────────────────────────────────────────┘   │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Key File References

| Component | File | Key Lines | Purpose |
|-----------|------|-----------|---------|
| **NikitaMemory** | `nikita/memory/graphiti_client.py` | 25-286 | 3-graph memory class |
| **MetaPromptService** | `nikita/meta_prompts/service.py` | 30-1105 | Context loading + prompt gen |
| **ServerToolHandler** | `nikita/agents/voice/server_tools.py` | 87-834 | Voice server tools |
| **PostProcessor** | `nikita/context/post_processor.py` | 76-664 | 9-stage post-processing |
| **MessageHandler** | `nikita/platforms/telegram/message_handler.py` | 51-200+ | Telegram message routing |
| **VoiceService** | `nikita/agents/voice/service.py` | 41-200+ | Voice call initiation |
| **Text Agent** | `nikita/agents/text/agent.py` | 33-320 | Pydantic AI text agent |
| **DynamicVariablesBuilder** | `nikita/agents/voice/context.py` | 35-235 | Voice dynamic variables |
| **HistoryLoader** | `nikita/agents/text/history.py` | 45-324 | PydanticAI message_history conversion |
| **TokenBudgetManager** | `nikita/agents/text/token_budget.py` | 95-341 | 4-tier token allocation |
| **ContextEngine** | `nikita/context_engine/engine.py` | 50-500 | Unified context collection (8 collectors) |
| **PromptGenerator** | `nikita/context_engine/generator.py` | 80-400 | LLM-powered prompt generation (Sonnet 4.5) |
| **PromptAssembler** | `nikita/context_engine/assembler.py` | 45-250 | Final prompt assembly + chapter rules |
| **ContextRouter** | `nikita/context_engine/router.py` | 30-200 | Feature-flagged v1/v2 routing |
| **ContextPackage** | `nikita/context_engine/models.py` | 164-350 | Unified context data model (Spec 040: onboarding + backstory) |

---

## 9. Spec 039: Unified Context Engine

The Unified Context Engine (Spec 039) provides a 3-layer architecture:

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    UNIFIED CONTEXT ENGINE (Spec 039)                      │
│                    nikita/context_engine/                                 │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  LAYER 1: Collection                   ContextEngine.collect_context()   │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  8 COLLECTORS (parallel execution):                                 │  │
│  │  • DatabaseCollector    → user, metrics, vices, engagement          │  │
│  │  • HistoryCollector     → PydanticAI message_history (Spec 030)     │  │
│  │  • GraphitiCollector    → 3-graph memory (user, relationship, nikita)│
│  │  • TemporalCollector    → time awareness, recency interpretation    │  │
│  │  • SocialCollector      → social circle members, relevance          │  │
│  │  • ContinuityCollector  → today buffer, threads, last conversation  │  │
│  │  • HumanizationCollector→ mood, activity, vices, behavioral instr   │  │
│  │  • KnowledgeCollector   → static persona, chapter behaviors         │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                              ↓                                            │
│  LAYER 2: Generation                   PromptGenerator.generate()        │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)                     │  │
│  │  • Input: ContextPackage (unified data model)                       │  │
│  │  • Backstory: 5-field bullet format (Spec 040)                      │  │
│  │  • Onboarding: is_new_user, days_since, profile_summary (Spec 040)  │  │
│  │  • Output: PromptBundle (text + voice prompts, 6K-15K tokens)       │  │
│  │  • Validators: Guardrails, Structure, Speakability                  │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                              ↓                                            │
│  LAYER 3: Assembly                     PromptAssembler.assemble()        │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  • Static persona (optional) from base_personality.yaml            │  │
│  │  • Chapter behavior rules from CHAPTER_BEHAVIORS constant          │  │
│  │  • Token estimation (~chars/4)                                      │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ROUTING: ContextRouter (CONTEXT_ENGINE_FLAG env var)                    │
│  • "enabled" (default): 100% v2 traffic                                   │
│  • "disabled": 100% v1 (legacy MetaPromptService)                         │
│  • "shadow"/"canary": Gradual rollout modes                               │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

### ContextPackage Fields (Spec 040 Enhancements)

```python
# Onboarding State (Spec 040)
is_new_user: bool           # True if onboarded within 7 days
days_since_onboarding: int  # Days since onboarded_at
onboarding_profile_summary: str  # Key preferences (name, interests, limits)

# Backstory (5-field bullet format, Spec 040)
backstory:
  - venue: str              # Where we met
  - how_we_met: str         # The context
  - the_moment: str         # The spark
  - unresolved_hook: str    # Unfinished business
  - tone: str               # Romantic/playful/etc
```

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 2.2.0 | 2026-01-29 | Added Section 9: Unified Context Engine (Spec 039), ContextPackage enhancements (Spec 040), new key file references |
| 2.1.0 | 2026-01-21 | Added Section 3.1 Working Memory System (Spec 030), added HistoryLoader + TokenBudgetManager to key files |
| 2.0.0 | 2026-01-19 | Initial comprehensive architecture doc (Spec 029) |

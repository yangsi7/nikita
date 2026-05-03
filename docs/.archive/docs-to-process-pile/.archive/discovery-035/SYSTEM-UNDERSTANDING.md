# System Understanding: Nikita Context Surfacing Architecture

## Executive Summary

Nikita uses a **dual-agent architecture** with TEXT (Pydantic AI + Claude Sonnet) and VOICE (ElevenLabs Conversational AI 2.0) agents that achieve **100% context parity** through different mechanisms:

- **Text Agent**: Context injected via `@agent.instructions` decorators at runtime
- **Voice Agent**: Context injected via dynamic variables + server tools during call

Both use the same `MetaPromptService.generate_system_prompt()` for core personality generation.

---

## Context Flow Architecture

### Master Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           NIKITA CONTEXT SURFACING ARCHITECTURE                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────────────────┐
                              │    DATA SOURCES         │
                              ├─────────────────────────┤
                              │ • PostgreSQL (Supabase) │
                              │   - users, metrics      │
                              │   - conversations       │
                              │   - threads, thoughts   │
                              │   - backstory profiles  │
                              │                         │
                              │ • Neo4j (Graphiti)      │
                              │   - user_facts graph    │
                              │   - relationship graph  │
                              │   - nikita_events graph │
                              │                         │
                              │ • YAML Config           │
                              │   - base_personality    │
                              │   - chapter_behaviors   │
                              │   - psychological_guide │
                              └───────────┬─────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                          MetaPromptService._load_context()                              │
│                          [nikita/meta_prompts/service.py:265-500]                       │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  TIER 1: USER STATE (Always loaded, ~300 tokens)                                       │
│  ├─ user.chapter (1-5)                                                                  │
│  ├─ user.relationship_score (0-100)                                                     │
│  ├─ user.game_status (active/boss_fight/game_over/won)                                 │
│  ├─ user.metrics (intimacy, passion, trust, secureness)                                │
│  └─ days_played                                                                         │
│                                                                                         │
│  TIER 2: TEMPORAL CONTEXT (Computed, ~400 tokens)                                       │
│  ├─ current_time, day_of_week, time_of_day                                             │
│  ├─ hours_since_last_interaction                                                        │
│  ├─ nikita_activity (computed from time/day)                                           │
│  ├─ nikita_mood (0-5, from chapter × hours_since)                                      │
│  ├─ nikita_energy (from time_of_day)                                                   │
│  └─ nikita_mood_4d (arousal, valence, dominance, intimacy)                             │
│                                                                                         │
│  TIER 3: ENGAGEMENT STATE (Spec 014, ~200 tokens)                                       │
│  ├─ engagement_state (CALIBRATING/IN_ZONE/CLINGY/DISTANT/OBSESSED/RECOVERING)          │
│  ├─ calibration_score (0-1)                                                             │
│  └─ vulnerability_level (0-5, interaction-based)                                        │
│                                                                                         │
│  TIER 4: PSYCHOLOGY (Spec 035, ~500 tokens)                                             │
│  ├─ active_defenses (intellectualization, humor, testing, withdrawal)                  │
│  ├─ active_wounds (too_much, conditional_love, vulnerability_punished, broken)         │
│  ├─ active_triggers (raised_voice, possessiveness, abandonment, criticism)             │
│  ├─ attachment_mode (secure/anxious/avoidant)                                          │
│  ├─ inner_monologue                                                                     │
│  └─ vulnerability_disclosure_guidance                                                   │
│                                                                                         │
│  TIER 5: PERSONALIZATION (Specs 006, 012, 021-028, ~1500 tokens)                       │
│  ├─ vice_profile (8 categories × 0-5 intensity)                                        │
│  ├─ chapter_behavior (CHAPTER_BEHAVIORS[chapter])                                       │
│  ├─ backstory (how_we_met, venue, spark, hook)                                         │
│  ├─ user_facts (50-100 from Graphiti user graph)                                       │
│  ├─ relationship_episodes (30-50 from relationship graph)                              │
│  ├─ nikita_events (20-30 from nikita graph)                                            │
│  ├─ behavioral_meta_instructions (Spec 024)                                            │
│  ├─ life_simulation_events (Spec 022)                                                  │
│  ├─ emotional_state_transitions (Spec 023)                                             │
│  └─ active_conflict (Spec 027)                                                         │
│                                                                                         │
│  TIER 6: MEMORY & HISTORY (Spec 030, ~3000 tokens)                                      │
│  ├─ today_summary + key_moments                                                         │
│  ├─ open_threads (unresolved topics, 10 per type)                                      │
│  ├─ last_7_days_summaries                                                               │
│  ├─ last_conversation_summary                                                           │
│  └─ active_thoughts (Nikita's inner life, 10 per type)                                 │
│                                                                                         │
└───────────────────────────────────────┬─────────────────────────────────────────────────┘
                                        │
                        ┌───────────────┴───────────────┐
                        │                               │
                        ▼                               ▼
┌───────────────────────────────────────┐   ┌───────────────────────────────────────┐
│         TEXT AGENT PATH               │   │         VOICE AGENT PATH              │
│   (Pydantic AI + Claude Sonnet)       │   │   (ElevenLabs Conversational AI)      │
└───────────────────────────────────────┘   └───────────────────────────────────────┘
                        │                               │
                        ▼                               ▼
┌───────────────────────────────────────┐   ┌───────────────────────────────────────┐
│  MetaPromptService.generate_system_   │   │  MetaPromptService.generate_system_   │
│  prompt() [service.py:1290]           │   │  prompt() [SAME SERVICE]              │
│                                       │   │                                       │
│  1. Load context (50+ fields)         │   │  1. Load context (50+ fields)         │
│  2. Load system_prompt.meta.md        │   │  2. Load system_prompt.meta.md        │
│  3. Execute via Claude Haiku          │   │  3. Execute via Claude Haiku          │
│  4. Return ~4000 token prompt         │   │  4. Return ~4000 token prompt         │
│  5. Log to generated_prompts table    │   │  5. ❌ NO LOGGING (gap)               │
└───────────────────────────────────────┘   └───────────────────────────────────────┘
                        │                               │
                        ▼                               ▼
┌───────────────────────────────────────┐   ┌───────────────────────────────────────┐
│  @agent.instructions DECORATORS       │   │  DYNAMIC VARIABLES (32 vars)          │
│  [nikita/agents/text/agent.py:57-82]  │   │  [nikita/agents/voice/models.py]      │
│                                       │   │                                       │
│  Priority order:                      │   │  Sent to ElevenLabs at call start:    │
│  1. add_personalized_context()        │   │  • user_name, chapter, relationship   │
│     → deps.generated_prompt (4K)      │   │  • engagement_state, secureness       │
│  2. add_chapter_behavior()            │   │  • nikita_mood, energy, activity      │
│     → CHAPTER_BEHAVIORS[chapter]      │   │  • 4D mood (arousal/valence/dom/int)  │
│  3. NIKITA_PERSONA (static, 800)      │   │  • recent_topics, open_threads        │
│                                       │   │  • today_summary, last_conv_summary   │
│  TOTAL: ~5000-6000 tokens             │   │  • context_block (≤500 tokens)        │
└───────────────────────────────────────┘   │  • secret__user_id, secret__token     │
                        │                   └───────────────────────────────────────┘
                        │                               │
                        ▼                               ▼
┌───────────────────────────────────────┐   ┌───────────────────────────────────────┐
│  MESSAGE HISTORY (Spec 030)           │   │  SERVER TOOLS (During Call)           │
│  [nikita/agents/text/history.py]      │   │  [nikita/agents/voice/server_tools.py]│
│                                       │   │                                       │
│  When conversation has history:       │   │  4 tools available via webhook:       │
│  • Load from conversations.messages   │   │                                       │
│  • Convert to ModelMessage types      │   │  get_context() → Full refresh         │
│  • Token budget: 3000 tokens max      │   │    Returns: 29 fields + 3-graph data  │
│  • Truncate oldest if exceeds         │   │                                       │
│                                       │   │  get_memory(query) → Search           │
│  CRITICAL: When history provided,     │   │    Returns: facts + threads           │
│  @agent.instructions DO NOT RUN       │   │                                       │
│  (system prompt in first message)     │   │  score_turn(msgs) → Real-time scoring │
│                                       │   │    Returns: 4 metric deltas           │
└───────────────────────────────────────┘   │                                       │
                        │                   │  update_memory(fact) → Store fact      │
                        │                   │    Returns: confirmation               │
                        ▼                   └───────────────────────────────────────┘
┌───────────────────────────────────────┐               │
│  nikita_agent.run()                   │               ▼
│  [Pydantic AI Core]                   │   ┌───────────────────────────────────────┐
│                                       │   │  ElevenLabs Agent Execution           │
│  CALL:                                │   │                                       │
│  result = await nikita_agent.run(     │   │  • Agent receives: system_prompt +    │
│      user_message,                    │   │    dynamic_variables interpolated     │
│      deps=NikitaDeps,                 │   │  • Can call server tools for context  │
│      message_history=list[ModelMsg],  │   │  • TTS configured by chapter/mood     │
│  )                                    │   │  • Real-time scoring possible         │
│                                       │   │                                       │
│  TOOLS:                               │   │  UNIQUE VOICE ADVANTAGES:             │
│  • recall_memory(query)               │   │  • score_turn() during conversation   │
│  • note_user_fact(fact, confidence)   │   │  • get_memory() query-based search    │
└───────────────────────────────────────┘   └───────────────────────────────────────┘
                        │                               │
                        ▼                               ▼
┌───────────────────────────────────────┐   ┌───────────────────────────────────────┐
│  RESPONSE + POST-PROCESSING           │   │  CALL END + SCORING                   │
│                                       │   │                                       │
│  1. Append response to conversation   │   │  1. ElevenLabs webhook                │
│  2. Score via ResponseAnalyzer        │   │  2. Fetch transcript                  │
│  3. Update metrics                    │   │  3. VoiceCallScorer.score_call()      │
│  4. Queue for PostProcessor           │   │  4. Update metrics                    │
│                                       │   │  5. Queue for PostProcessor           │
│  POST-PROCESSOR (async):              │   │                                       │
│  • Entity extraction                  │   │  Same post-processing pipeline        │
│  • _analyze_psychology() ← Spec 035   │   │                                       │
│  • Thread tracking                    │   │                                       │
│  • Thought generation                 │   │                                       │
│  • Neo4j 3-graph updates              │   │                                       │
│  • Summary generation                 │   │                                       │
└───────────────────────────────────────┘   └───────────────────────────────────────┘
```

---

## Token Budget Allocation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        TOKEN BUDGET: 15,000 TOTAL                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  SYSTEM PROMPT BUDGET: 6,000 tokens                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ NIKITA_PERSONA (static)               │████████████│ 800 tokens        ││
│  │ CHAPTER_BEHAVIOR                      │████│ 300 tokens                ││
│  │ PERSONALIZED CONTEXT (generated):     │                                ││
│  │   ├─ Game state                       │████│ 300 tokens                ││
│  │   ├─ Temporal context                 │█████│ 400 tokens               ││
│  │   ├─ Engagement state                 │███│ 200 tokens                 ││
│  │   ├─ Psychology (Spec 035)            │███████│ 500 tokens             ││
│  │   ├─ Personalization                  │████████████████████│ 1,500 tok ││
│  │   └─ Memory context                   │████████████████████████████│2K ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  MESSAGE HISTORY BUDGET: 3,000 tokens                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ Conversation messages (80 max, oldest trimmed)                         ││
│  │ Tool call/return pairs preserved                                       ││
│  │ HistoryLoader enforces budget                                          ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  REMAINING: ~6,000 tokens for user message + Claude response               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Context Parity Matrix

| Context Element | Text Agent | Voice Agent | Parity |
|-----------------|------------|-------------|--------|
| System Prompt Generation | MetaPromptService | MetaPromptService (same) | ✅ 100% |
| User Facts (Graphiti) | 50 via _load_context() | 50 via get_context() | ✅ 100% |
| Relationship Episodes | 30 via _load_context() | 30 via get_context() | ✅ 100% |
| Nikita Events | 20 via _load_context() | 20 via get_context() | ✅ 100% |
| Open Threads | 10/type via _load_context() | 10/type via get_context() | ✅ 100% |
| Active Thoughts | 10/type via _load_context() | 10/type via get_context() | ✅ 100% |
| 4D Emotional State | In prompt context | In dynamic_variables | ✅ 100% |
| Daily Events (Spec 022) | In prompt context | In get_context() | ✅ 100% |
| Active Conflict (Spec 027) | In prompt context | In get_context() | ✅ 100% |
| Today Summary | In prompt | In dynamic_variables | ✅ 100% |
| Backstory | In prompt | In get_context() | ✅ 100% |
| Vice Profile | In prompt | In get_context() | ✅ 100% |
| **Memory Search Tool** | recall_memory | get_memory | ✅ BOTH |
| **Real-time Scoring** | Post-processing | score_turn() during call | 🔵 VOICE+ |
| **Prompt Logging** | generated_prompts table | ❌ Not logged | ⚠️ TEXT+ |

---

## Key Files Reference

### Core Context Loading
| File | Purpose | Key Functions |
|------|---------|---------------|
| `nikita/meta_prompts/service.py` | Context aggregation + prompt generation | `_load_context()`, `generate_system_prompt()` |
| `nikita/meta_prompts/templates/system_prompt.meta.md` | 15K token meta-prompt template | Template with all context blocks |

### Text Agent
| File | Purpose | Key Functions |
|------|---------|---------------|
| `nikita/agents/text/agent.py` | Main agent + instruction decorators | `generate_response()`, `@agent.instructions` |
| `nikita/agents/text/history.py` | Message history loading | `HistoryLoader.load()` |
| `nikita/agents/text/deps.py` | Dependency container | `NikitaDeps` dataclass |
| `nikita/agents/text/handler.py` | Entry point | `handle_message()` |

### Voice Agent
| File | Purpose | Key Functions |
|------|---------|---------------|
| `nikita/agents/voice/models.py` | Dynamic variables (32 vars) | `DynamicVariables.to_dict()` |
| `nikita/agents/voice/server_tools.py` | Server tool handlers | `get_context()`, `get_memory()`, `score_turn()` |
| `nikita/agents/voice/context.py` | Context builders | `DynamicVariablesBuilder`, `ConversationConfigBuilder` |
| `nikita/api/routes/voice.py` | API endpoints | `/pre-call`, `/server-tool`, `/webhook` |

### Psychology (Spec 035)
| File | Purpose | Key Functions |
|------|---------|---------------|
| `nikita/life_simulation/psychology_mapper.py` | Event → psych response | `analyze_event()`, `analyze_user_behavior()` |
| `nikita/context/relationship_analyzer.py` | Relationship dynamics | `analyze_conversation()`, `calculate_health()` |
| `nikita/context/post_processor.py` | Post-conv analysis | `_analyze_psychology()` stage |

### Knowledge Base
| File | Content |
|------|---------|
| `nikita/config_data/knowledge/nikita_backstory.md` | Full life history (3K words) |
| `nikita/config_data/knowledge/nikita_psychology.md` | Psychological profile (2.4K words) |
| `nikita/config_data/knowledge/nikita_life.md` | Daily routines (1.6K words) |
| `nikita/config_data/knowledge/social_circle_framework.md` | Named characters (2K words) |
| `nikita/config_data/knowledge/vulnerability_progression.md` | 6-level disclosure system |

---

## Critical Integration Points

### 1. Where Context Reaches Claude (Text)
```python
# nikita/agents/text/agent.py:264
result = await nikita_agent.run(
    user_message,
    deps=NikitaDeps,                    # ← Contains generated_prompt
    message_history=list[ModelMessage], # ← Contains conversation history
)
```

### 2. Where Context Reaches ElevenLabs (Voice)
```python
# nikita/agents/voice/context.py:ConversationConfigBuilder
config = {
    "agent": {
        "prompt": system_prompt,         # ← Generated by MetaPromptService
        "first_message": first_message,  # ← Chapter-personalized
    },
    "tts": tts_settings,                 # ← Mood-adjusted
}
dynamic_variables = DynamicVariables.build_from_user(user, context)
# → Sent to ElevenLabs at /api/v1/voice/pre-call
```

### 3. Where Psychology Is Analyzed
```python
# nikita/context/post_processor.py:729-900
async def _analyze_psychology(self, conversation, extraction):
    analyzer = get_relationship_analyzer()
    dynamics = analyzer.analyze_conversation(messages)
    health = analyzer.calculate_relationship_health(dynamics)
    insight = analyzer.generate_psychological_insight(dynamics, health)
    # → Stored in PipelineResult.psychological_insight
```

---

## Integration Status Summary

| Component | Status | Evidence |
|-----------|--------|----------|
| MetaPromptService | ✅ WORKING | 50+ fields loaded, Haiku generates prompt |
| Text Agent Instructions | ✅ WORKING | @agent.instructions inject context |
| Message History | ✅ WORKING | HistoryLoader with 3K token budget |
| Voice Dynamic Variables | ✅ WORKING | 32 variables in models.py |
| Voice Server Tools | ✅ WORKING | 4 tools with WHEN/HOW/RETURNS format |
| 3-Graph Memory | ✅ WORKING | Graphiti queries in both agents |
| Psychology Analysis | ✅ WORKING | _analyze_psychology() in PostProcessor |
| Humanization Specs | ✅ WIRED | All 8 specs (021-028) integrated |
| Token Budget | ✅ CONFIGURED | 15K total, tiered loading |
| Vulnerability Gating | ✅ WORKING | Interaction-based (L0-L5) |

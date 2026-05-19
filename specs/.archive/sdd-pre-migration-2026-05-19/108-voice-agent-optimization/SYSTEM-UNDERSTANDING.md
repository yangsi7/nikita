# System Understanding — Spec 108: Voice Agent Optimization

## Entity List

| Entity | Path | Role | Key Exports |
|--------|------|------|-------------|
| VoiceAgentConfig | `nikita/agents/voice/config.py:86` | System prompt + agent config generation | `generate_system_prompt()`, `get_agent_config()` |
| VoiceService | `nikita/agents/voice/service.py:41` | Call initiation, session mgmt, fallback chain | `initiate_call()`, `end_call()` |
| DynamicVariablesBuilder | `nikita/agents/voice/context.py:42` | Build 30+ dynamic variables for ElevenLabs | `build_from_context()`, `build_from_user()` |
| ConversationConfigBuilder | `nikita/agents/voice/context.py:360` | Complete ElevenLabs config builder | `build_config()`, `to_elevenlabs_format()` |
| TTSConfigService | `nikita/agents/voice/tts_config.py:65` | Chapter+mood TTS settings | `get_final_settings()` |
| TTSSettings | `nikita/agents/voice/models.py:277` | Pydantic model: stability, similarity_boost, speed | Frozen model |
| DynamicVariables | `nikita/agents/voice/models.py:313` | 30+ fields for prompt interpolation | `to_dict()`, `to_dict_with_secrets()` |
| ConversationConfig | `nikita/agents/voice/models.py:431` | System prompt, first message, TTS, LLM config | Pydantic model |
| Voice persona | `nikita/agents/voice/persona.py:17-59` | VOICE_PERSONA_ADDITIONS, CHAPTER_VOICE_BEHAVIORS, MOOD_VOICE_MODULATIONS | `get_voice_persona_additions()` |
| PromptBuilderStage | `nikita/pipeline/stages/prompt_builder.py:35` | Token budget enforcement | VOICE_TOKEN_MIN=1800, VOICE_TOKEN_MAX=2200 |
| system_prompt.j2 Section 3 | `nikita/pipeline/templates/system_prompt.j2:55-78` | Voice branch: speech patterns, formatting rules | Jinja2 template |
| Settings | `nikita/config/settings.py:11` | ElevenLabs config fields | `elevenlabs_*` fields |
| ServerToolHandler | `nikita/agents/voice/server_tools.py` | 4 server tools (get_context, get_memory, score_turn, update_memory) | Unchanged in this spec |
| InboundCallHandler | `nikita/agents/voice/inbound.py` | Inbound call flow: phone lookup → availability → accept/reject | Unchanged in this spec |

## Relationship Map

```
PROMPT FLOW (system prompt generation):
PromptBuilderStage → system_prompt.j2 [Section 3: voice branch]
  ↓ renders with PipelineContext data
ready_prompts table [stored prompt text]
  ↓ loaded at call time
VoiceService._try_load_ready_prompt() → prompt_content
  ↓ fallback chain
VoiceService._generate_fallback_prompt() → VoiceAgentConfig.generate_system_prompt()

CONTEXT FLOW (dynamic variables):
DynamicVariablesBuilder.build_from_user(user)
  → DynamicVariables (30+ fields)
  → to_dict_with_secrets() for ElevenLabs webhook response
  → {{variable_name}} interpolation in system prompt

PERSONALITY FLOW (persona data):
VoiceAgentConfig.BASE_VOICE_PERSONA [base voice traits]
  + CHAPTER_PERSONAS[chapter] [ch1-5 behavior]
  + VICE_VOICE_ADDITIONS[vice] [vice-specific adjustments]
  → system_prompt text

persona.py.VOICE_PERSONA_ADDITIONS [extended voice guidance]
  + CHAPTER_VOICE_BEHAVIORS[chapter]
  + MOOD_VOICE_MODULATIONS[mood]
  → get_voice_persona_additions() [used by legacy/fallback path]

TTS FLOW (voice settings):
TTSConfigService.get_final_settings(chapter, mood)
  → CHAPTER_TTS_SETTINGS[chapter] base
  → MOOD_TTS_SETTINGS[mood] override
  → TTSSettings(stability, similarity_boost, speed)
  → conversation_config_override.tts

SERVICE FLOW (call initiation):
VoiceService.initiate_call(user_id)
  → _load_user() [eager load metrics, engagement, vices]
  → _load_context() → VoiceContext
  → _try_load_ready_prompt() → prompt_content (or fallback)
  → _build_dynamic_variables() → DynamicVariables
  → _get_tts_settings() → TTSSettings
  → _get_first_message() → greeting string
  → conversation_config_override dict → ElevenLabs API
```

## Complexity Score: 7/15

| Factor | Score | Rationale |
|--------|-------|-----------|
| External API deps | +2 | ElevenLabs V3 model, Knowledge Base API |
| New technology | +2 | Audio tags, expressive mode, KB RAG |
| Multi-file changes | +1 | 8+ files modified, 6 new files |
| Frontend+backend | +1 | Knowledge base docs + backend code |
| Integration testing | +1 | Dashboard config, voice call verification |

## Change Impact Summary

**HIGH IMPACT (core voice experience):**
- system_prompt.j2 Section 3: Replace `(parenthetical)` → `[audio tag]` syntax
- config.py: BASE_VOICE_PERSONA, VICE_VOICE_ADDITIONS, first messages
- persona.py: All persona strings need audio tag updates
- tts_config.py: New V3-optimized stability/speed values (no style param)

**MEDIUM IMPACT (new modules):**
- NEW: audio_tags.py — tag definitions, chapter gates, helpers
- NEW: 3 knowledge base docs for ElevenLabs KB upload
- NEW: upload_knowledge_base.py script

**LOW IMPACT (settings/config):**
- settings.py: Add elevenlabs_voice_id reference field
- prompt_builder.py: Update token budgets (1800-2200 → 2800-3500)
- context.py: Add `available_audio_tags` to DynamicVariables

**NO CHANGE:**
- server_tools.py, scoring.py, transcript.py, inbound.py, scheduling.py
- API routes, database models, memory system

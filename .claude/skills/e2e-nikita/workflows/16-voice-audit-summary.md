# Voice Audit Summary — Module Dependency Map & Coverage Gaps

**Purpose**: Reference map for the voice E2E workflow (15-voice-manual.md). Captures all 26 voice modules,
their dependency graph, user flow participation, API endpoint coverage from existing S-07.* / S-12.* scenarios,
and the remaining testing gaps that workflow 15 addresses.

**Scope**: `nikita/agents/voice/` (18 modules), `nikita/onboarding/` (8 modules), `nikita/api/routes/voice.py`

---

## Section 1: Voice Agent Module Dependency Map

### Core Agent Modules (`nikita/agents/voice/`)

| Module | Purpose | Depends On | User Flow |
|--------|---------|------------|-----------|
| `availability.py` | Chapter-based call acceptance probability (10/40/80/90/95%) | User model (chapter, game_status) | Inbound (pre-check) |
| `audio_tags.py` | SSML injection, audio expression markers | — | Mid-call (prompt gen) |
| `config.py` | `VoiceAgentConfig` — system prompts, TTS assembly | `persona.py`, `tts_config.py` | All flows |
| `context.py` | `DynamicVariablesBuilder`, `ConversationConfigBuilder` | memory, life_sim, emotional_state | Inbound / outbound |
| `deps.py` | FastAPI dependency injection providers | — | API layer |
| `elevenlabs_client.py` | ElevenLabs SDK wrapper (agent config, outbound calls) | ElevenLabs API | Outbound, signed-url |
| `inbound.py` | `InboundCallHandler`, `VoiceSessionManager` | availability, config, context | Inbound call |
| `models.py` | Pydantic models: `CallSession`, `ServerToolRequest`, `ServerToolResponse`, `TTSSettings`, `NikitaMood` | — | All flows |
| `persona.py` | Chapter-specific voice behavior additions | — | Prompt generation |
| `scheduling.py` | `VoiceEventScheduler`, `EventDeliveryHandler` (cross-platform) | User model, scheduled_events repo | Outbound scheduling |
| `scoring.py` | `VoiceCallScorer` — transcript → metric deltas | engine/scoring | Post-call |
| `server_tools.py` | `ServerToolHandler` — 4 tools: get_context, get_memory, score_turn, update_memory | memory, scoring, life_sim, emotional_state | Mid-call |
| `service.py` | `VoiceService` — initiate_call, end_call, make_outbound_call | config, context, ElevenLabs client | Inbound / outbound |
| `transcript.py` | `TranscriptManager` — fetch, persist, summarize ElevenLabs transcript | ElevenLabs API | Post-call |
| `tts_config.py` | `TTSConfigService`, `CHAPTER_TTS_SETTINGS`, `MOOD_TTS_SETTINGS` | — | All flows (prompt assembly) |
| `openings/selector.py` | `OpeningSelector` — profile-to-template matching (darkness_range, scene_tags, life_stage_tags, weight) | openings/registry.py | Inbound initiation |
| `openings/registry.py` | Template loading from YAML files | YAML opening files | Inbound initiation |
| `openings/models.py` | `Opening` Pydantic model (id, darkness_range, scene_tags, weight, is_fallback) | — | Inbound initiation |

### Onboarding Modules (`nikita/onboarding/`)

| Module | Purpose | Depends On | User Flow |
|--------|---------|------------|-----------|
| `meta_nikita.py` | Meta-Nikita ElevenLabs agent config, persona, TTS (stability=0.40, speed=0.95) | — | Onboarding call |
| `voice_flow.py` | `VoiceOnboardingFlow` — phone collection, confirmation, call initiation, state machine | service.py, DB repos | Onboarding |
| `profile_collector.py` | Darkness/scene/life_stage collection from call | — | Onboarding mid-call |
| `handoff.py` | `HandoffManager` — social circle gen, game state init, first Telegram message | platforms/telegram | Post-onboarding |
| `server_tools.py` | Onboarding-specific tools: collect_profile, configure_preferences, complete_onboarding | DB repos | Onboarding mid-call |
| `models.py` | `OnboardingProfile`, `OnboardingStatus`, state machine constants | — | Onboarding |
| `preference_config.py` | Mapping onboarding profile fields → game config (darkness_level → vice mix, pacing) | — | Post-onboarding |
| `__init__.py` | Package exports | — | — |

---

## Section 2: User Flow Matrix

| Phase | Active Modules |
|-------|---------------|
| Onboarding | meta_nikita, voice_flow, profile_collector, handoff, server_tools (onboarding), preference_config |
| Inbound Call Initiation | availability, service, config, context, openings/selector, openings/registry, tts_config, persona |
| Mid-Call (Server Tools) | server_tools (voice), audio_tags |
| Post-Call Processing | scoring, transcript, pipeline/orchestrator |
| Outbound Scheduling | scheduling (VoiceEventScheduler), service, config, context |
| Outbound Delivery | scheduling (EventDeliveryHandler), elevenlabs_client |
| Background Refresh | tts_config, context, ready_prompt_repository |

---

## Section 3: API Endpoint Coverage

| Endpoint | Method | Existing S-07 / S-12 Coverage | Coverage Gaps |
|----------|--------|-------------------------------|---------------|
| `/api/v1/voice/availability/{user_id}` | GET | S-07.1.1 (partial — tests context, not availability route) | Per-chapter rate verification (10/40/80/90/95%), unavailability excuse text |
| `/api/v1/voice/signed-url/{user_id}` | GET | None | Full endpoint: returns signed WebSocket URL, signed_token, dynamic_variables, conversation_config_override |
| `/api/v1/voice/initiate` | POST | S-07.5.1, S-07.5.2, S-07.5.3 (partial — opening template only) | Dark profile template selection, TTS settings per chapter in response, 403 when unavailable |
| `/api/v1/voice/server-tool` | POST | S-07.1.3 (get_memory), S-07.1.4 (get_context), S-07.2.1, S-07.2.2 (score_turn), S-07.4.1 (auth) | update_memory + read-back round-trip, auth failure body shape, timeout fallback behavior |
| `/api/v1/voice/webhook` | POST | S-07.3.1, S-07.3.2, S-07.3.3, S-07.7.1, S-07.7.2, S-07.8.1, S-07.8.2, S-12.1.1, S-12.1.2 (best covered) | Pipeline completion verification after webhook, composite formula check |
| `/api/v1/voice/pre-call` | POST | S-07.5.* partial (inbound context) | Rejection path (game_over / wrong chapter), phone number lookup from Twilio caller_id |

---

## Section 4: Existing Voice Scenario Cross-Reference

| Existing ID | Description | S-15.X.Y Counterpart | Overlap Type |
|-------------|-------------|---------------------|--------------|
| S-07.1.1 | Pre-call context endpoint returns 200 | S-15.3.1 | EXTENDS (get_context server tool, not /context route) |
| S-07.1.3 | get_memory returns recent memories | S-15.3.2 | COVERED (retained as-is) |
| S-07.1.4 | get_context returns user profile | S-15.3.1 | COVERED |
| S-07.2.1 | score_turn creates score_history row | S-15.3.3 | COVERED |
| S-07.2.2 | score_turn source_platform='voice' | S-15.3.4 | COVERED |
| S-07.3.1 | Post-call webhook updates relationship_score | S-15.4.1 | COVERED |
| S-07.3.2 | Webhook creates conversations row platform='voice' | S-15.4.2 | COVERED |
| S-07.3.3 | Webhook creates memory_facts from transcript | S-15.4.4 | COVERED |
| S-07.4.1 | Server-tool auth required | S-15.3.7 | COVERED |
| S-07.5.2 | warm_intro template for standard profile | S-15.2.1 | COVERED |
| S-07.5.3 | challenge template for intellectual_dominance | S-15.2.2 | EXTENDS (noir for drug_tolerance=5+techno) |
| S-07.7.1 | Webhook idempotent, no duplicate memory_facts | S-15.4.6 | COVERED |
| S-07.8.1 | duration_seconds stored | S-15.4.3 | COVERED |
| S-07.8.2 | Long transcript (50+ turns) no crash | S-15.4.7 | COVERED |
| S-07.6.1 | Portal /conversations shows voice entry | S-15.4.8 | COVERED |
| S-12.1.1 | Voice webhook updates relationship_score | S-15.4.1 | DUPLICATE (same assertion) |
| S-12.1.2 | source_platform='voice' in score_history | S-15.3.4 | DUPLICATE |
| S-12.2.2 | Voice score uses same composite formula | S-15.4.5 | ADDS_DEPTH (explicit formula check) |
| S-12.3.1 | Memory shared across platforms | S-15.5.4 | ADDS_DEPTH (text context receives voice fact) |
| S-12.4.1 | Both conversation types in history | S-15.4.8 | EXTENDS |

---

## Section 5: Testing Gaps Summary

Gaps organized by workflow 15 phase bucket.

### Live Call Gaps (Phases A–D)

**A — Availability endpoint not directly tested**
- GET `/availability/{user_id}` never called directly in existing scenarios; S-07.1.1 hits the `/context` path
- Missing: probabilistic verification at each of the 5 chapters (10/40/80/90/95%)
- Missing: unavailability response body contains an in-character excuse string

**B — Signed URL endpoint has zero coverage**
- GET `/signed-url/{user_id}` response shape never asserted (signed_url, signed_token, dynamic_variables, conversation_config_override all unverified)

**C — Opening selector depth missing**
- TTS settings in initiate response not verified against CHAPTER_TTS_SETTINGS constants
- Behavioral check: does opening line match drug_tolerance persona?

**D — Memory round-trip unverified**
- update_memory stores a fact via SupabaseMemory, then get_memory retrieves it in the same session — never tested end-to-end
- update_memory return shape `{stored: true, fact, category}` not asserted

### Onboarding Gaps (Phase F)

**F — Voice onboarding flow untested in E2E**
- Meta-Nikita agent call initiation not verified against live ElevenLabs
- collect_profile server tool: field persistence in onboarding_profile JSONB not asserted
- complete_onboarding → Telegram first message not verified
- Social circle generation (handoff.py) not covered
- Skip path (onboarding_status='skipped') not exercised

### Background Gaps (Phases G–H)

**G — Outbound voice call delivery not covered**
- VoiceEventScheduler creates scheduled_events with platform='voice' — not verified
- EventDeliveryHandler routes voice events to make_outbound_call — not verified
- Gap-based trigger (24h text silence → voice touchpoint) not exercised
- Conflict suppression during active conflict not tested

**H — Background jobs for voice not covered**
- voice-refresh cron endpoint not called in E2E
- psyche_state injection into voice prompt not verified
- psyche-batch job for voice users not exercised
- Expired onboarding session cleanup not covered

# Tasks: 007-Voice-Agent

**Generated**: 2025-11-29 | **Updated**: 2025-12-29
**Feature**: 007 - Voice Agent (ElevenLabs Conversational AI 2.0)
**Input**: Design documents from `/specs/007-voice-agent/`
**Prerequisites**:
- **Required**: plan.md (technical approach), spec.md (user stories)
- **Dependencies**:
  - ElevenLabs API (Conversational AI 2.0)
  - 010-api-infrastructure (✅ Complete)
  - 003-scoring-engine (✅ Complete)
  - 011-background-tasks (✅ Complete) - `scheduled_events` table ready, pg_cron active

**Organization**: Tasks grouped by user story (US1-US15) for independent implementation and testing.
- US-1 to US-7: Core voice agent functionality
- US-8 to US-10: Cross-platform scheduling, memory, and post-call processing
- US-11 to US-15: Emotional voice, outbound calls, dynamic variables (NEW Dec 2025)

---

## Phase 1: Setup ✅ COMPLETE

**Purpose**: Create voice agent module structure

- [x] T001 Create `nikita/agents/voice/__init__.py` with module exports
- [x] T002 Create `tests/agents/voice/__init__.py` for test package
- [x] T003 Add ElevenLabs config to `nikita/config/settings.py` (agent_id, voice_id, webhook_secret, twilio)

**Checkpoint**: ✅ Module structure ready for implementation

---

## Phase 2: Voice Models ✅ COMPLETE

**Purpose**: Data models for voice conversations

### T004: Create Voice Data Models
- **Status**: [x] Complete
- **File**: `nikita/agents/voice/models.py`
- **Dependencies**: T001 ✅
- **ACs**:
  - [x] AC-T004.1: ServerToolRequest model (tool_name, user_id, session_id, data)
  - [x] AC-T004.2: TranscriptEntry model (speaker, text, timestamp)
  - [x] AC-T004.3: CallScore model (metric deltas, aggregate_score, call_duration)
  - [x] AC-T004.4: VoiceContext model (user, chapter, vices, memory)
  - [x] AC-T004.5: CallResult model (success, score_applied, transcript_id)
  - [x] BONUS: TTSSettings, DynamicVariables, ConversationConfig, VoiceSession models

**Checkpoint**: ✅ Data models ready for services

---

## Phase 3: US-1 Start Voice Call (P1 - Must-Have)

**From spec.md**: User initiates call → Nikita "answers" → conversation begins

**Goal**: Users can initiate voice calls with proper authentication

**Independent Test**: Click call button, verify Nikita answers with greeting

**Acceptance Criteria** (from spec.md):
- AC-FR001-001: Given user clicks "Call Nikita" in portal, When connection established, Then Nikita greets appropriately
- AC-FR001-002: Given user on Telegram, When using /call deep link, Then redirected to voice interface
- AC-FR008-001: Given call started, When session created, Then start time logged

### Tests for US-1 ✅ COMPLETE

- [x] T005 [P] [US1] Unit test for VoiceService.initiate_call() in `tests/agents/voice/test_service.py`
  - **Tests**: AC-FR001-001, AC-FR008-001
  - **Status**: 6 tests passing (TDD approach)

### Implementation for US-1

### T006: Implement Call Initiation Logic ✅ COMPLETE
- **Status**: [x] Complete
- **File**: `nikita/agents/voice/service.py`
- **Dependencies**: T004 ✅
- **ACs**:
  - [x] AC-T006.1: `initiate_call(user_id)` returns signed ElevenLabs connection params
  - [x] AC-T006.2: Generates signed token with user_id for server tool auth
  - [x] AC-T006.3: Logs call_started event with timestamp
  - [x] AC-T006.4: Loads user context for initial greeting customization

### T007: Create Call Initiation API Endpoint ✅ COMPLETE
- **Status**: [x] Complete
- **File**: `nikita/api/routes/voice.py`
- **Dependencies**: T006 ✅
- **ACs**:
  - [x] AC-T007.1: POST /api/v1/voice/initiate returns connection params
  - [x] AC-T007.2: Validates user authentication
  - [x] AC-T007.3: Returns 403 if call not available (wrong chapter/game over)

### Verification for US-1

- [x] T008 [US1] Run all US-1 tests - verify all pass (12 tests passing)
- [ ] T009 [US1] Integration test: Initiate call flow (requires live ElevenLabs)

**Checkpoint**: Call initiation functional. Users can start voice calls.

---

## Phase 4: US-2 Natural Conversation (P1 - Must-Have)

**From spec.md**: User speaks → Nikita responds naturally → feels like real call

**Goal**: Real-time conversation with <500ms latency

**Independent Test**: Have conversation, verify natural flow and timing

**Acceptance Criteria** (from spec.md):
- AC-FR002-001: Given user speaks clearly, When processed, Then transcript accurate
- AC-FR003-001: Given Nikita responds, When audio plays, Then voice sounds natural
- AC-FR004-001: Given response generated, When delivered, Then latency < 500ms

### Tests for US-2 ✅ COMPLETE

- [x] T010 [P] [US2] Unit test for VoiceAgentConfig in `tests/agents/voice/test_config.py`
  - **Tests**: AC-FR003-001 (voice config)
  - **Status**: 6 tests passing (TDD approach)

### Implementation for US-2

### T011: Implement VoiceAgentConfig ✅ COMPLETE
- **Status**: [x] Complete
- **File**: `nikita/agents/voice/config.py`
- **Dependencies**: T003 ✅
- **ACs**:
  - [x] AC-T011.1: `generate_system_prompt(user_id, chapter, vices)` includes Nikita persona
  - [x] AC-T011.2: `get_agent_config(user_id)` returns ElevenLabs-compatible config
  - [x] AC-T011.3: Includes chapter behavior modifications
  - [x] AC-T011.4: Includes vice preference injection

### T012: Implement Server Tool Handler ✅ COMPLETE
- **Status**: [x] Complete
- **File**: `nikita/agents/voice/server_tools.py`
- **Dependencies**: T004 ✅
- **ACs**:
  - [x] AC-T012.1: `handle(request)` routes to appropriate tool handler
  - [x] AC-T012.2: Validates signed token for user_id
  - [x] AC-T012.3: Returns structured response for ElevenLabs

### T013: Create Server Tool API Endpoint ✅ COMPLETE
- **Status**: [x] Complete
- **File**: `nikita/api/routes/voice.py`
- **Dependencies**: T012 ✅
- **ACs**:
  - [x] AC-T013.1: POST /api/v1/voice/server-tool handles tool calls
  - [x] AC-T013.2: Validates ElevenLabs webhook signature
  - [x] AC-T013.3: Returns JSON response for tool result

### Verification for US-2

- [x] T014 [US2] Run all US-2 tests - verify all pass (28 tests passing)

**Checkpoint**: ✅ Server tools functional. ElevenLabs can call backend.

---

## Phase 5: US-3 Personality Consistency (P1 - Must-Have)

**From spec.md**: Voice Nikita → same personality as text Nikita

**Goal**: Unified personality across voice and text

**Independent Test**: Verify voice behavior matches text behavior for same user

**Acceptance Criteria** (from spec.md):
- AC-FR005-001: Given Ch1 user calls, When Nikita responds, Then guarded/challenging
- AC-FR005-002: Given user with dark_humor vice, When Nikita responds, Then dark humor present
- AC-FR005-003: Given text discussed topic yesterday, When voice mentions it, Then Nikita remembers

### Tests for US-3 ✅ TESTS IMPLEMENTED

- [x] T015 [P] [US3] Unit tests in `tests/agents/voice/test_personality_consistency.py` (8 tests)
  - **Tests**: AC-FR005-001, AC-FR005-002, AC-FR005-003
  - **Verify**: ✅ All 8 tests pass

### Implementation for US-3 ✅ COMPLETE

### T016: Implement get_context Server Tool
- **Status**: [x] Complete
- **File**: `nikita/agents/voice/server_tools.py`
- **Dependencies**: T012
- **ACs**:
  - [x] AC-T016.1: `_get_context(user_id)` returns VoiceContext with all user data
  - [x] AC-T016.2: Loads chapter, score, vices from database
  - [x] AC-T016.3: Loads recent memory from Graphiti (via get_memory tool)
  - [x] AC-T016.4: Formats for LLM consumption (nikita_mood, voice_persona)

### T017: Implement Voice Persona Additions
- **Status**: [x] Complete
- **File**: `nikita/prompts/voice_persona.py`
- **Dependencies**: T011
- **ACs**:
  - [x] AC-T017.1: VOICE_PERSONA_ADDITIONS constant with voice-specific behaviors
  - [x] AC-T017.2: Comfortable silences guidance
  - [x] AC-T017.3: Audible reactions (sighs, laughs, hmms)
  - [x] AC-T017.4: Interruption handling instructions

### Verification for US-3

- [x] T018 [US3] Run all US-3 tests - ✅ 8/8 passing

**Checkpoint**: ✅ Personality consistency functional. Voice matches text.

---

## Phase 6: US-4 Call Scoring (P1 - Must-Have) ✅ COMPLETE

**From spec.md**: Voice call ends → transcript scored → metrics updated

**Goal**: Score voice conversations and update user metrics

**Independent Test**: Complete call, verify score update with voice_call source

**Acceptance Criteria** (from spec.md):
- AC-FR006-001: Given call ends, When transcript analyzed, Then single aggregate score
- AC-FR006-002: Given good call, When scored, Then positive metric deltas
- AC-FR006-003: Given score history, When logged, Then source = "voice_call"

### Tests for US-4 ✅ TESTS IMPLEMENTED

- [x] T019 [P] [US4] Unit tests in `tests/agents/voice/test_scoring.py` (9 tests)
  - **Tests**: AC-FR006-001, AC-FR006-002, AC-FR006-003
  - **Verify**: ✅ All 9 tests pass

### Implementation for US-4 ✅ T020-T021 COMPLETE

### T020: Implement VoiceCallScorer
- **Status**: [x] Complete
- **File**: `nikita/agents/voice/scoring.py`
- **Dependencies**: T004, ScoreAnalyzer (003)
- **ACs**:
  - [x] AC-T020.1: `score_call(user_id, transcript)` analyzes full conversation
  - [x] AC-T020.2: Returns aggregate CallScore with metric deltas
  - [x] AC-T020.3: Considers call duration in scoring
  - [x] AC-T020.4: Uses same ScoreAnalyzer.analyze_batch() as text agent

### T021: Implement Score Application
- **Status**: [x] Complete
- **File**: `nikita/agents/voice/scoring.py`
- **Dependencies**: T020
- **ACs**:
  - [x] AC-T021.1: `apply_score(user_id, score)` updates user_metrics via MetricsRepository
  - [x] AC-T021.2: Logs to score_history with event_type='voice_call'
  - [x] AC-T021.3: Includes call duration and session_id in event_details

### T022: Implement end_call Server Tool
- **Status**: [x] Complete
- **File**: `nikita/agents/voice/service.py`
- **Dependencies**: T020, T021
- **ACs**:
  - [x] AC-T022.1: `end_call(user_id, session_id, transcript)` accepts transcript from webhook
  - [x] AC-T022.2: Calls VoiceCallScorer.score_call()
  - [x] AC-T022.3: Applies score and returns CallResult with score_change details
  - [x] AC-T022.4: Updates last_interaction_at via UserRepository

### Verification for US-4 ✅ COMPLETE

- [x] T023 [US4] Run all US-4 tests - 39/39 voice agent tests passing

**Checkpoint**: Call scoring functional. Voice affects metrics.

---

## Phase 7: US-5 Cross-Modality Memory (P2 - Important)

**From spec.md**: Text and voice share memory → conversations reference each other

**Goal**: Memory continuity between voice and text

**Independent Test**: Discuss topic in voice, verify text agent knows it

**Acceptance Criteria** (from spec.md):
- AC-FR010-001: Given voice call discussed weekend, When texting later, Then Nikita references call
- AC-FR010-002: Given text revealed user fact, When calling, Then Nikita knows it
- AC-FR009-001: Given call transcript, When memory updated, Then available to both agents

### Tests for US-5 ⚠️ WRITE TESTS FIRST

- [ ] T024 [P] [US5] Unit test for TranscriptManager in `tests/agents/voice/test_transcript.py`
  - **Tests**: AC-FR009-001, AC-FR010-001
  - **Verify**: Test FAILS before implementation

### Implementation for US-5

### T025: Implement TranscriptManager
- **Status**: [ ] Pending
- **File**: `nikita/agents/voice/transcript.py`
- **Dependencies**: T004
- **ACs**:
  - [ ] AC-T025.1: `fetch_from_elevenlabs(session_id)` retrieves transcript
  - [ ] AC-T025.2: `persist(user_id, session_id, transcript)` saves to conversations
  - [ ] AC-T025.3: Sets platform='voice' in conversation record
  - [ ] AC-T025.4: Returns conversation_id for linking

### T026: Implement Memory Integration
- **Status**: [ ] Pending
- **File**: `nikita/agents/voice/transcript.py`
- **Dependencies**: T025, Graphiti
- **ACs**:
  - [ ] AC-T026.1: `add_to_memory(user_id, transcript)` extracts key facts
  - [ ] AC-T026.2: Adds facts to user_graph via Graphiti
  - [ ] AC-T026.3: Adds shared events to relationship_graph
  - [ ] AC-T026.4: Facts available to both text and voice agents

### T027: Implement update_memory Server Tool
- **Status**: [ ] Pending
- **File**: `nikita/agents/voice/service.py`
- **Dependencies**: T026
- **ACs**:
  - [ ] AC-T027.1: `update_memory(user_id, facts)` saves facts during call
  - [ ] AC-T027.2: Can be called mid-conversation by ElevenLabs
  - [ ] AC-T027.3: Facts immediately available for context retrieval

### Verification for US-5

- [ ] T028 [US5] Run all US-5 tests - verify all pass

**Checkpoint**: Cross-modality memory functional. Voice and text share context.

---

## Phase 8: US-6 Server Tool Access (P2 - Important)

**From spec.md**: During call → Nikita can look things up → rich responses

**Goal**: Rich context access during voice calls

**Independent Test**: Ask memory-dependent question, verify accurate recall

**Acceptance Criteria** (from spec.md):
- AC-FR007-001: Given "remember when we...", When tool called, Then memory retrieved
- AC-FR007-002: Given tool result returned, When integrated, Then response includes info
- AC-FR007-003: Given tool latency, When response generated, Then natural filler used

### Tests for US-6 ⚠️ WRITE TESTS FIRST

- [ ] T029 [P] [US6] Unit test for complete server tool flow in `tests/agents/voice/test_server_tools.py`
  - **Tests**: AC-FR007-001, AC-FR007-002
  - **Verify**: Test FAILS before implementation

### Implementation for US-6

### T030: Complete Server Tool Integration
- **Status**: [ ] Pending
- **File**: `nikita/agents/voice/server_tools.py`
- **Dependencies**: T012, T016, T22, T27
- **ACs**:
  - [ ] AC-T030.1: All three tools (get_context, update_memory, end_call) operational
  - [ ] AC-T030.2: Error handling with fallback responses
  - [ ] AC-T030.3: Latency monitoring and logging

### Verification for US-6

- [ ] T031 [US6] Run all US-6 tests - verify all pass

**Checkpoint**: Server tools fully operational. Rich context available.

---

## Phase 9: US-7 Call Availability Progression (P3 - Nice-to-Have)

**From spec.md**: New user (Ch1) → calls rarely available → Ch3+ → calls common

**Goal**: Call availability scales with relationship

**Independent Test**: Check availability across chapters, verify progression

**Acceptance Criteria** (from spec.md):
- AC-FR011-001: Given Ch1 user, When checking availability, Then usually unavailable
- AC-FR011-002: Given Ch3 user, When checking availability, Then available
- AC-FR011-003: Given game_over user, When trying to call, Then calls blocked

### Tests for US-7 ⚠️ WRITE TESTS FIRST

- [ ] T032 [P] [US7] Unit test for CallAvailability in `tests/agents/voice/test_availability.py`
  - **Tests**: AC-FR011-001, AC-FR011-002, AC-FR011-003
  - **Verify**: Test FAILS before implementation

### Implementation for US-7

### T033: Implement CallAvailability
- **Status**: [ ] Pending
- **File**: `nikita/agents/voice/availability.py`
- **Dependencies**: T004
- **ACs**:
  - [ ] AC-T033.1: `is_available(user)` returns (available, reason)
  - [ ] AC-T033.2: AVAILABILITY_RATES by chapter (10%, 40%, 80%, 90%, 95%)
  - [ ] AC-T033.3: Game over/won blocks all calls
  - [ ] AC-T033.4: Boss fight always allows call

### T034: Create Availability API Endpoint
- **Status**: [ ] Pending
- **File**: `nikita/api/routes/voice.py`
- **Dependencies**: T033
- **ACs**:
  - [ ] AC-T034.1: GET /api/v1/voice/availability/{user_id} returns status
  - [ ] AC-T034.2: Returns reason when unavailable
  - [ ] AC-T034.3: Frontend can check before showing call button

### Verification for US-7

- [ ] T035 [US7] Run all US-7 tests - verify all pass

**Checkpoint**: Availability progression functional. Calls unlock with relationship.

---

## Phase 10: API Completion

**Purpose**: Complete all API routes

### T036: Complete Voice API Routes
- **Status**: [ ] Pending
- **File**: `nikita/api/routes/voice.py`
- **Dependencies**: All prior tasks
- **ACs**:
  - [ ] AC-T036.1: POST /api/v1/voice/server-tool ✓
  - [ ] AC-T036.2: POST /api/v1/voice/callback for event logging
  - [ ] AC-T036.3: GET /api/v1/voice/availability/{user_id} ✓
  - [ ] AC-T036.4: POST /api/v1/voice/initiate ✓
  - [ ] AC-T036.5: Routes registered in api/routes/__init__.py

**Checkpoint**: API routes complete and documented.

---

## Phase 11: Final Verification

**Purpose**: Full integration test and polish

- [ ] T037 Run all tests: `pytest tests/agents/voice/ -v`
- [ ] T038 Verify 80%+ code coverage
- [ ] T039 Integration test: Full call flow (initiate → conversation → scoring → memory)
- [ ] T040 Update `nikita/agents/voice/CLAUDE.md` with implementation notes
- [ ] T041 Update `nikita/agents/CLAUDE.md` status to reflect voice complete

**Final Checkpoint**: Voice agent complete and verified.

---

## Phase 12: US-8 Unified Event Scheduling (P2 - Important) ← NEW (Dec 2025)

**From spec.md FR-013**: Voice + text use shared scheduling → cross-platform delivery

**Goal**: Enable cross-platform event scheduling between voice and text

**Independent Test**: Schedule voice follow-up, verify delivery to Telegram

**Acceptance Criteria** (from spec.md):
- AC-FR013-001: Given voice call ends, When follow-up scheduled, Then event in scheduled_events with platform='voice'
- AC-FR013-002: Given text schedules voice reminder, When event created, Then cross-platform event works
- AC-FR013-003: Given scheduled event due, When /tasks/deliver runs, Then correct platform handler invoked
- AC-FR013-004: Given event scheduling, When delay calculated, Then uses chapter-based delay logic

**BLOCKER**: Requires Spec 011 completion (scheduled_events table)

### Tests for US-8 ⚠️ WRITE TESTS FIRST

- [ ] T042 [P] [US8] Unit test for VoiceEventScheduler in `tests/agents/voice/test_scheduling.py`
  - **Tests**: AC-FR013-001, AC-FR013-004
  - **Verify**: Test FAILS before implementation

### Implementation for US-8

### T043: Implement VoiceEventScheduler
- **Status**: [ ] Pending (BLOCKED: Spec 011)
- **File**: `nikita/agents/voice/scheduling.py`
- **Dependencies**: Spec 011 (scheduled_events table), T004
- **ACs**:
  - [ ] AC-T043.1: `schedule_follow_up(user_id, event_type, content, delay_hours)` creates event
  - [ ] AC-T043.2: Uses chapter-based delay calculation from text agent
  - [ ] AC-T043.3: Sets platform field correctly ('telegram' or 'voice')
  - [ ] AC-T043.4: Links source_conversation_id for traceability

### T044: Update /tasks/deliver for Cross-Platform
- **Status**: [ ] Pending (BLOCKED: Spec 011)
- **File**: `nikita/api/routes/tasks.py`
- **Dependencies**: Spec 011 (scheduled_events), T043
- **ACs**:
  - [ ] AC-T044.1: Handles 'telegram' platform events (send message)
  - [ ] AC-T044.2: Handles 'voice' platform events (send push notification)
  - [ ] AC-T044.3: Marks events as delivered after successful send
  - [ ] AC-T044.4: Retries failed deliveries with exponential backoff

### Verification for US-8

- [ ] T045 [US8] Run all US-8 tests - verify all pass
- [ ] T046 [US8] Integration test: Cross-platform event scheduling and delivery

**Checkpoint**: Unified event scheduling functional. Voice and text can trigger each other.

---

## Phase 13: US-9 Cross-Agent Memory Access (P2 - Important) ← NEW (Dec 2025)

**From spec.md FR-014**: Voice agent sees text history → text agent sees voice history

**Goal**: Full memory visibility across voice and text agents

**Independent Test**: Have voice call, verify text agent references it in next message

**Acceptance Criteria** (from spec.md):
- AC-FR014-001: Given voice call starts, When get_context called, Then returns text conversation summaries
- AC-FR014-002: Given text agent queries memory, When voice call occurred, Then summary visible
- AC-FR014-003: Given voice episode saved, When source='voice_call' used, Then distinguishable
- AC-FR014-004: Given memory search, When graph_types=['relationship'], Then both voice and text returned

### Tests for US-9 ⚠️ WRITE TESTS FIRST

- [ ] T047 [P] [US9] Unit test for cross-agent memory in `tests/agents/voice/test_memory_integration.py`
  - **Tests**: AC-FR014-001, AC-FR014-003, AC-FR014-004
  - **Verify**: Test FAILS before implementation

### Implementation for US-9

### T048: Enhance VoiceService with Text History
- **Status**: [ ] Pending
- **File**: `nikita/agents/voice/service.py`
- **Dependencies**: T016, NikitaMemory
- **ACs**:
  - [ ] AC-T048.1: `get_context_with_text_history(user_id)` loads text conversation summaries
  - [ ] AC-T048.2: Formats text history for voice agent consumption
  - [ ] AC-T048.3: Includes last 7 days of text conversations
  - [ ] AC-T048.4: Memory search returns both voice and text episodes

### T049: Update NikitaMemory for Voice Source Tags
- **Status**: [ ] Pending
- **File**: `nikita/memory/graphiti_client.py`
- **Dependencies**: NikitaMemory
- **ACs**:
  - [ ] AC-T049.1: Voice episodes saved with source='voice_call'
  - [ ] AC-T049.2: Text episodes saved with source='user_message'
  - [ ] AC-T049.3: Search results include source field for filtering
  - [ ] AC-T049.4: Both sources returned when no filter specified

### Verification for US-9

- [ ] T050 [US9] Run all US-9 tests - verify all pass

**Checkpoint**: Cross-agent memory access functional. Voice knows text history.

---

## Phase 14: US-10 Post-Call Processing (P2 - Important) ← NEW (Dec 2025)

**From spec.md FR-015**: Voice transcript → post_call_transcription webhook → 9-stage pipeline

**Goal**: Voice transcripts processed through same pipeline as text

**Independent Test**: Complete voice call, verify facts extracted and stored in Graphiti

**Acceptance Criteria** (from spec.md):
- AC-FR015-001: Given call ends, When post_call_transcription received, Then transcript stored
- AC-FR015-002: Given transcript stored, When post-processing triggered, Then fact extraction runs
- AC-FR015-003: Given voice conversation, When thread detection runs, Then topics identified
- AC-FR015-004: Given voice call, When thought simulation runs, Then Nikita thoughts generated
- AC-FR015-005: Given webhook received, When HMAC validated, Then only ElevenLabs accepted

### Tests for US-10 ⚠️ WRITE TESTS FIRST

- [ ] T051 [P] [US10] Unit test for webhook handler in `tests/api/routes/test_voice_webhook.py`
  - **Tests**: AC-FR015-001, AC-FR015-005
  - **Verify**: Test FAILS before implementation

- [ ] T052 [P] [US10] Unit test for voice post-processing in `tests/agents/voice/test_post_processing.py`
  - **Tests**: AC-FR015-002, AC-FR015-003, AC-FR015-004
  - **Verify**: Test FAILS before implementation

### Implementation for US-10

### T053: Implement ElevenLabs Webhook Handler
- **Status**: [ ] Pending
- **File**: `nikita/api/routes/voice.py`
- **Dependencies**: T013
- **ACs**:
  - [ ] AC-T053.1: POST /api/v1/voice/webhook handles post_call_transcription
  - [ ] AC-T053.2: Validates HMAC signature (elevenlabs-signature header)
  - [ ] AC-T053.3: Extracts transcript and session metadata
  - [ ] AC-T053.4: Handles call_initiation_failure events with logging

### T054: Implement HMAC Signature Validation
- **Status**: [ ] Pending
- **File**: `nikita/api/routes/voice.py`
- **Dependencies**: settings.elevenlabs_webhook_secret
- **ACs**:
  - [ ] AC-T054.1: `verify_elevenlabs_signature()` validates "timestamp.payload" format
  - [ ] AC-T054.2: Rejects timestamps older than 5 minutes
  - [ ] AC-T054.3: Uses constant-time comparison (hmac.compare_digest)
  - [ ] AC-T054.4: Returns 401 on invalid signature

### T055: Integrate Voice into Post-Processing Pipeline
- **Status**: [ ] Pending
- **File**: `nikita/platforms/telegram/post_processor.py`
- **Dependencies**: T053, PostProcessor
- **ACs**:
  - [ ] AC-T055.1: `process_voice_conversation(conversation_id)` runs 9-stage pipeline
  - [ ] AC-T055.2: Extracts facts from transcript_raw field
  - [ ] AC-T055.3: Uses source='voice_call' for memory episodes
  - [ ] AC-T055.4: Generates Nikita thoughts about voice conversation

### Verification for US-10

- [ ] T056 [US10] Run all US-10 tests - verify all pass
- [ ] T057 [US10] Integration test: Full post-call processing flow

**Checkpoint**: Post-call processing functional. Voice enriches relationship memory.

---

## Phase 15: US-11 Emotional Voice Expression (P2 - Important) ← NEW (Dec 2025)

**From spec.md FR-016, FR-017**: Chapter + mood → TTS settings → authentic voice

**Goal**: Voice parameters change based on relationship depth and emotional state

**Independent Test**: Compare voice recordings across chapters/moods for parameter variation

**Acceptance Criteria** (from spec.md):
- AC-FR016-001: Given Ch1 user calls, When TTS settings applied, Then stability=0.8, speed=0.95
- AC-FR016-002: Given Ch5 user calls, When TTS settings applied, Then stability=0.4-0.5
- AC-FR017-001: Given Nikita is annoyed, When voice generated, Then speed=1.1, stability=0.4
- AC-FR017-002: Given Nikita is vulnerable, When voice generated, Then speed=0.9, stability=0.7

### Tests for US-11 ⚠️ WRITE TESTS FIRST

- [ ] T058 [P] [US11] Unit test for TTSSettings in `tests/agents/voice/test_tts_config.py`
  - **Tests**: AC-FR016-001, AC-FR016-002, AC-FR017-001, AC-FR017-002
  - **Verify**: Test FAILS before implementation

### Implementation for US-11

### T059: Implement Chapter-Based TTS Settings
- **Status**: [ ] Pending
- **File**: `nikita/agents/voice/tts_config.py`
- **Dependencies**: T004
- **ACs**:
  - [ ] AC-T059.1: TTSSettings dataclass with stability, similarity_boost, speed
  - [ ] AC-T059.2: CHAPTER_TTS_SETTINGS mapping (1→5 progression)
  - [ ] AC-T059.3: `get_tts_settings_for_chapter(chapter)` returns appropriate settings
  - [ ] AC-T059.4: Ch1 = distant, Ch5 = intimate voice characteristics

### T060: Implement Mood-Based Voice Modulation
- **Status**: [ ] Pending
- **File**: `nikita/agents/voice/tts_config.py`
- **Dependencies**: T059
- **ACs**:
  - [ ] AC-T060.1: MOOD_TTS_MODIFIERS mapping (flirty, vulnerable, annoyed, playful, distant)
  - [ ] AC-T060.2: `get_final_tts_settings(chapter, mood)` combines chapter + mood
  - [ ] AC-T060.3: Mood overrides chapter defaults for emotional authenticity
  - [ ] AC-T060.4: Settings passed to ElevenLabs via conversation_config_override

### Verification for US-11

- [ ] T061 [US11] Run all US-11 tests - verify all pass

**Checkpoint**: Emotional voice expression functional. Voice reflects relationship depth and mood.

---

## Phase 16: US-12 Outbound Calls (P2 - Important) ← NEW (Dec 2025)

**From spec.md FR-019, FR-021**: Nikita calls user proactively → Twilio outbound

**Goal**: Enable Nikita to initiate calls based on triggers (decay, engagement, schedules)

**Independent Test**: Trigger decay threshold, verify Nikita calls user with personalized greeting

**Acceptance Criteria** (from spec.md):
- AC-FR019-001: Given decay threshold crossed, When voice_call event scheduled, Then Twilio call initiated
- AC-FR019-002: Given outbound call connects, When Nikita speaks, Then context-aware greeting used
- AC-FR021-001: Given scheduled_event type='voice_call', When /tasks/deliver runs, Then ElevenLabs API invoked
- AC-FR021-002: Given cross-platform event, When text schedules voice follow-up, Then call occurs

### Tests for US-12 ⚠️ WRITE TESTS FIRST

- [ ] T062 [P] [US12] Unit test for OutboundCallService in `tests/agents/voice/test_outbound.py`
  - **Tests**: AC-FR019-001, AC-FR019-002
  - **Verify**: Test FAILS before implementation

### Implementation for US-12

### T063: Implement OutboundCallService
- **Status**: [ ] Pending
- **File**: `nikita/agents/voice/outbound.py`
- **Dependencies**: T004, ElevenLabs SDK
- **ACs**:
  - [ ] AC-T063.1: `initiate_call(user_id, to_number, trigger_reason)` starts call
  - [ ] AC-T063.2: Uses ElevenLabs `conversations.start_phone_call()` API
  - [ ] AC-T063.3: Loads user context for personalized greeting
  - [ ] AC-T063.4: Different greetings per trigger_reason (decay, engagement_drop, reminder)

### T064: Update /tasks/deliver for Voice Calls
- **Status**: [ ] Pending
- **File**: `nikita/api/routes/tasks.py`
- **Dependencies**: T063, T043
- **ACs**:
  - [ ] AC-T064.1: Handles platform='voice' events with OutboundCallService
  - [ ] AC-T064.2: Extracts phone_number and trigger_reason from event content
  - [ ] AC-T064.3: Logs call initiation results
  - [ ] AC-T064.4: Handles failed call attempts gracefully

### Verification for US-12

- [ ] T065 [US12] Run all US-12 tests - verify all pass
- [ ] T066 [US12] Integration test: Schedule voice call, verify Twilio outbound

**Checkpoint**: Outbound calls functional. Nikita can proactively call users.

---

## Phase 17: US-13 Dynamic Variables and Overrides (P1 - Must-Have) ← NEW (Dec 2025)

**From spec.md FR-018, FR-025**: Dynamic variables + config overrides → personalized calls

**Goal**: Inject context and customize agent behavior per-call

**Independent Test**: Start call with overrides, verify system prompt and first message match

**Acceptance Criteria** (from spec.md):
- AC-FR018-001: Given call initiates, When dynamic variables set, Then user_name, chapter, mood available
- AC-FR018-002: Given secret variables set, When LLM processes, Then user_id hidden from response
- AC-FR025-001: Given config override passed, When agent starts, Then custom system prompt used
- AC-FR025-002: Given first_message override, When call connects, Then Nikita uses custom greeting

### Tests for US-13 ⚠️ WRITE TESTS FIRST

- [ ] T067 [P] [US13] Unit test for dynamic variables in `tests/agents/voice/test_dynamic_vars.py`
  - **Tests**: AC-FR018-001, AC-FR018-002, AC-FR025-001
  - **Verify**: Test FAILS before implementation

### Implementation for US-13

### T068: Implement Dynamic Variables Builder
- **Status**: [ ] Pending
- **File**: `nikita/agents/voice/context.py`
- **Dependencies**: T016
- **ACs**:
  - [ ] AC-T068.1: `build_dynamic_variables(context)` returns ElevenLabs-compatible dict
  - [ ] AC-T068.2: User context: user_name, chapter, relationship_score, engagement_state
  - [ ] AC-T068.3: Nikita state: nikita_mood, nikita_energy, time_of_day
  - [ ] AC-T068.4: Secret variables prefixed with `secret__` (hidden from LLM)

### T069: Implement Conversation Config Overrides
- **Status**: [ ] Pending
- **File**: `nikita/agents/voice/config.py`
- **Dependencies**: T011, T059
- **ACs**:
  - [ ] AC-T069.1: `build_conversation_override(context)` returns full override dict
  - [ ] AC-T069.2: Includes agent.prompt.prompt with personalized system prompt
  - [ ] AC-T069.3: Includes agent.first_message based on context
  - [ ] AC-T069.4: Includes agent.tts with chapter/mood-appropriate settings

### Verification for US-13

- [ ] T070 [US13] Run all US-13 tests - verify all pass

**Checkpoint**: Dynamic variables functional. Every call is personalized.

---

## Phase 18: US-14 Server Tool Integration (P1 - Must-Have) ← NEW (Dec 2025)

**From spec.md FR-022, FR-023**: Timeout fallbacks + graceful degradation

**Goal**: Robust server tools that don't break conversation flow

**Independent Test**: Ask memory question during Neo4j timeout, verify graceful response

**Acceptance Criteria** (from spec.md):
- AC-FR022-001: Given tool timeout (>2s), When fallback triggered, Then graceful response
- AC-FR022-002: Given Neo4j unavailable, When get_memory called, Then fallback message returned
- AC-FR007-001: Given "remember when...", When tool called, Then memory retrieved
- AC-FR007-002: Given tool result, When integrated, Then response includes info

### Tests for US-14 ⚠️ WRITE TESTS FIRST

- [ ] T071 [P] [US14] Unit test for timeout fallbacks in `tests/agents/voice/test_server_tools.py`
  - **Tests**: AC-FR022-001, AC-FR022-002
  - **Verify**: Test FAILS before implementation

### Implementation for US-14

### T072: Implement Timeout Fallback Decorator
- **Status**: [ ] Pending
- **File**: `nikita/agents/voice/server_tools.py`
- **Dependencies**: T012
- **ACs**:
  - [ ] AC-T072.1: `@with_timeout_fallback(timeout_seconds=2.0)` decorator
  - [ ] AC-T072.2: Returns fallback response on asyncio.TimeoutError
  - [ ] AC-T072.3: Logs all timeouts for debugging
  - [ ] AC-T072.4: Fallback includes `cache_friendly=True` for ElevenLabs caching

### T073: Implement Graceful Degradation for Memory
- **Status**: [ ] Pending
- **File**: `nikita/agents/voice/service.py`
- **Dependencies**: T016, T072
- **ACs**:
  - [ ] AC-T073.1: `get_context_with_degradation(user_id)` catches Neo4j errors
  - [ ] AC-T073.2: Returns VoiceContext with memory_available=False on failure
  - [ ] AC-T073.3: Sets degraded_message for natural acknowledgment
  - [ ] AC-T073.4: Game state (chapter, score) always available from Supabase

### Verification for US-14

- [ ] T074 [US14] Run all US-14 tests - verify all pass

**Checkpoint**: Server tools robust. Failures don't break conversation.

---

## Phase 19: US-15 Inbound Phone Call (P1 - Must-Have) ← NEW (Dec 2025)

**From spec.md FR-020, FR-024, FR-026**: Inbound calls + connection recovery + HMAC

**Goal**: Users can call Nikita directly via Twilio phone number

**Independent Test**: Call Twilio number, verify Nikita answers with personalized greeting

**Acceptance Criteria** (from spec.md):
- AC-FR020-001: Given user calls +41787950009, When call connects, Then ElevenLabs agent handles
- AC-FR020-002: Given phone lookup succeeds, When user identified, Then dynamic variables injected
- AC-FR020-003: Given Ch1 user calls, When availability checked, Then call may be rejected per FR-011
- AC-FR026-001: Given webhook received, When HMAC verified, Then processing continues
- AC-FR026-002: Given invalid HMAC, When verification fails, Then request rejected with 401

### Tests for US-15 ⚠️ WRITE TESTS FIRST

- [ ] T075 [P] [US15] Unit test for InboundCallHandler in `tests/agents/voice/test_inbound.py`
  - **Tests**: AC-FR020-001, AC-FR020-002, AC-FR020-003
  - **Verify**: Test FAILS before implementation

### Implementation for US-15

### T076: Implement InboundCallHandler
- **Status**: [ ] Pending
- **File**: `nikita/agents/voice/inbound.py`
- **Dependencies**: T016, T033, T059
- **ACs**:
  - [ ] AC-T076.1: `handle_incoming_call(phone_number)` processes inbound call
  - [ ] AC-T076.2: Looks up user by phone number
  - [ ] AC-T076.3: Checks call availability (chapter-based)
  - [ ] AC-T076.4: Returns accept_call=False with message if unavailable

### T077: Implement Connection Drop Recovery
- **Status**: [ ] Pending
- **File**: `nikita/agents/voice/session.py`
- **Dependencies**: T004
- **ACs**:
  - [ ] AC-T077.1: VoiceSessionManager tracks session state (ACTIVE, DISCONNECTED)
  - [ ] AC-T077.2: `handle_disconnect(session_id)` marks session as disconnected
  - [ ] AC-T077.3: `attempt_recovery(session_id)` returns True if <30s disconnect
  - [ ] AC-T077.4: Long disconnects trigger session finalization

### T078: Implement Pre-Call Webhook Route
- **Status**: [ ] Pending
- **File**: `nikita/api/routes/voice.py`
- **Dependencies**: T076
- **ACs**:
  - [ ] AC-T078.1: POST /api/v1/voice/pre-call handles Twilio-ElevenLabs pre-call
  - [ ] AC-T078.2: Returns dynamic_variables and conversation_config_override
  - [ ] AC-T078.3: Returns accept_call=False for unknown callers
  - [ ] AC-T078.4: Validates HMAC signature

### Verification for US-15

- [ ] T079 [US15] Run all US-15 tests - verify all pass
- [ ] T080 [US15] Integration test: Inbound call via Twilio

**Checkpoint**: Inbound calls functional. Users can call Nikita directly.

---

## Dependencies & Execution Order

### Phase Dependencies (Updated Dec 2025)

**BLOCKER**: Spec 011 must be complete before Phase 12 can start

| Phase | Depends On | Can Start After |
|-------|-----------|-----------------|
| Phase 1: Setup | None | Immediately |
| Phase 2: Models | Phase 1 | Setup done |
| Phase 3: US-1 (Initiation) | Phase 2 | Models ready |
| Phase 4: US-2 (Conversation) | Phase 2 | Models ready (parallel with 3) |
| Phase 5: US-3 (Personality) | Phase 4 | Server tools ready |
| Phase 6: US-4 (Scoring) | Phase 4 | Server tools ready (parallel with 5) |
| Phase 7: US-5 (Memory) | Phase 6 | Scoring ready |
| Phase 8: US-6 (Tools) | Phases 5, 6, 7 | All tools implemented |
| Phase 9: US-7 (Availability) | Phase 3 | Initiation ready (parallel with 4-8) |
| Phase 10: API | All prior | All handlers done |
| Phase 11: Final | All prior | All phases done |
| **Phase 12: US-8 (Scheduling)** | **Spec 011** | **Spec 011 complete** |
| Phase 13: US-9 (Cross-Memory) | Phase 7 | Memory ready |
| Phase 14: US-10 (Post-Call) | Phase 4 | Server tools ready |

---

## Progress Summary (Updated Dec 2025)

| Phase/User Story | Tasks | Completed | Status |
|------------------|-------|-----------|--------|
| Phase 1: Setup | 3 | 3 | ✅ Complete |
| Phase 2: Models | 1 | 1 | ✅ Complete |
| US-1: Start Call | 5 | 5 | ✅ Complete |
| US-2: Conversation | 5 | 5 | ✅ Complete |
| US-3: Personality | 4 | 4 | ✅ Complete |
| US-4: Scoring | 5 | 5 | ✅ Complete |
| US-5: Memory | 5 | 0 | Pending |
| US-6: Server Tools | 3 | 0 | Pending |
| US-7: Availability | 4 | 0 | Pending |
| Phase 10: API | 1 | 0 | Pending |
| Phase 11: Final | 5 | 0 | Pending |
| US-8: Event Scheduling | 5 | 0 | Pending |
| US-9: Cross-Memory | 4 | 0 | Pending |
| US-10: Post-Call | 7 | 0 | Pending |
| **US-11: Emotional Voice** | **4** | **0** | **Pending** |
| **US-12: Outbound Calls** | **5** | **0** | **Pending** |
| **US-13: Dynamic Vars** | **4** | **0** | **Pending** |
| **US-14: Server Tool Resilience** | **4** | **0** | **Pending** |
| **US-15: Inbound Phone** | **6** | **0** | **Pending** |
| **Total** | **80** | **23** | **28% Complete** |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-29 | Initial task generation from plan.md |
| 2.0 | 2025-12-29 | Added US-8, US-9, US-10 (16 new tasks: T042-T057) for FR-013, FR-014, FR-015 |
| 2.1 | 2025-12-29 | Updated dependencies: Spec 011 now blocks Phase 12 |
| 3.0 | 2025-12-30 | **Major expansion**: Added US-11 to US-15 (23 tasks: T058-T080) for FR-016 to FR-026. Spec 011 ✅ Complete (dependency resolved). Total tasks now 80. |
| 3.1 | 2025-12-30 | US-1 through US-4 complete (23 tasks). VoiceCallScorer + end_call implemented. 39 voice agent tests passing. |

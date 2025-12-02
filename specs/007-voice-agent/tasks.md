# Tasks: 007-Voice-Agent

**Generated**: 2025-11-29
**Feature**: 007 - Voice Agent (ElevenLabs Conversational AI 2.0)
**Input**: Design documents from `/specs/007-voice-agent/`
**Prerequisites**:
- **Required**: plan.md (technical approach), spec.md (user stories)
- **Dependencies**: ElevenLabs API, 010-api-infrastructure, 003-scoring-engine

**Organization**: Tasks grouped by user story (US1-US7) for independent implementation and testing.

---

## Phase 1: Setup

**Purpose**: Create voice agent module structure

- [ ] T001 Create `nikita/agents/voice/__init__.py` with module exports
- [ ] T002 Create `tests/agents/voice/__init__.py` for test package
- [ ] T003 Add ElevenLabs config to `nikita/config/settings.py` (agent_id, voice_id, webhook_secret)

**Checkpoint**: Module structure ready for implementation

---

## Phase 2: Voice Models

**Purpose**: Data models for voice conversations

### T004: Create Voice Data Models
- **Status**: [ ] Pending
- **File**: `nikita/agents/voice/models.py`
- **Dependencies**: T001
- **ACs**:
  - [ ] AC-T004.1: ServerToolRequest model (tool_name, user_id, session_id, data)
  - [ ] AC-T004.2: TranscriptEntry model (speaker, text, timestamp)
  - [ ] AC-T004.3: CallScore model (metric deltas, aggregate_score, call_duration)
  - [ ] AC-T004.4: VoiceContext model (user, chapter, vices, memory)
  - [ ] AC-T004.5: CallResult model (success, score_applied, transcript_id)

**Checkpoint**: Data models ready for services

---

## Phase 3: US-1 Start Voice Call (P1 - Must-Have)

**From spec.md**: User initiates call → Nikita "answers" → conversation begins

**Goal**: Users can initiate voice calls with proper authentication

**Independent Test**: Click call button, verify Nikita answers with greeting

**Acceptance Criteria** (from spec.md):
- AC-FR001-001: Given user clicks "Call Nikita" in portal, When connection established, Then Nikita greets appropriately
- AC-FR001-002: Given user on Telegram, When using /call deep link, Then redirected to voice interface
- AC-FR008-001: Given call started, When session created, Then start time logged

### Tests for US-1 ⚠️ WRITE TESTS FIRST

- [ ] T005 [P] [US1] Unit test for VoiceService.initiate_call() in `tests/agents/voice/test_service.py`
  - **Tests**: AC-FR001-001, AC-FR008-001
  - **Verify**: Test FAILS before implementation

### Implementation for US-1

### T006: Implement Call Initiation Logic
- **Status**: [ ] Pending
- **File**: `nikita/agents/voice/service.py`
- **Dependencies**: T004
- **ACs**:
  - [ ] AC-T006.1: `initiate_call(user_id)` returns signed ElevenLabs connection params
  - [ ] AC-T006.2: Generates signed token with user_id for server tool auth
  - [ ] AC-T006.3: Logs call_started event with timestamp
  - [ ] AC-T006.4: Loads user context for initial greeting customization

### T007: Create Call Initiation API Endpoint
- **Status**: [ ] Pending
- **File**: `nikita/api/routes/voice.py`
- **Dependencies**: T006
- **ACs**:
  - [ ] AC-T007.1: POST /api/v1/voice/initiate returns connection params
  - [ ] AC-T007.2: Validates user authentication
  - [ ] AC-T007.3: Returns 403 if call not available (wrong chapter/game over)

### Verification for US-1

- [ ] T008 [US1] Run all US-1 tests - verify all pass
- [ ] T009 [US1] Integration test: Initiate call flow

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

### Tests for US-2 ⚠️ WRITE TESTS FIRST

- [ ] T010 [P] [US2] Unit test for VoiceAgentConfig in `tests/agents/voice/test_config.py`
  - **Tests**: AC-FR003-001 (voice config)
  - **Verify**: Test FAILS before implementation

### Implementation for US-2

### T011: Implement VoiceAgentConfig
- **Status**: [ ] Pending
- **File**: `nikita/agents/voice/config.py`
- **Dependencies**: T003
- **ACs**:
  - [ ] AC-T011.1: `generate_system_prompt(user_id, chapter, vices)` includes Nikita persona
  - [ ] AC-T011.2: `get_agent_config(user_id)` returns ElevenLabs-compatible config
  - [ ] AC-T011.3: Includes chapter behavior modifications
  - [ ] AC-T011.4: Includes vice preference injection

### T012: Implement Server Tool Handler
- **Status**: [ ] Pending
- **File**: `nikita/agents/voice/server_tools.py`
- **Dependencies**: T004
- **ACs**:
  - [ ] AC-T012.1: `handle(request)` routes to appropriate tool handler
  - [ ] AC-T012.2: Validates signed token for user_id
  - [ ] AC-T012.3: Returns structured response for ElevenLabs

### T013: Create Server Tool API Endpoint
- **Status**: [ ] Pending
- **File**: `nikita/api/routes/voice.py`
- **Dependencies**: T012
- **ACs**:
  - [ ] AC-T013.1: POST /api/v1/voice/server-tool handles tool calls
  - [ ] AC-T013.2: Validates ElevenLabs webhook signature
  - [ ] AC-T013.3: Returns JSON response for tool result

### Verification for US-2

- [ ] T014 [US2] Run all US-2 tests - verify all pass

**Checkpoint**: Server tools functional. ElevenLabs can call backend.

---

## Phase 5: US-3 Personality Consistency (P1 - Must-Have)

**From spec.md**: Voice Nikita → same personality as text Nikita

**Goal**: Unified personality across voice and text

**Independent Test**: Verify voice behavior matches text behavior for same user

**Acceptance Criteria** (from spec.md):
- AC-FR005-001: Given Ch1 user calls, When Nikita responds, Then guarded/challenging
- AC-FR005-002: Given user with dark_humor vice, When Nikita responds, Then dark humor present
- AC-FR005-003: Given text discussed topic yesterday, When voice mentions it, Then Nikita remembers

### Tests for US-3 ⚠️ WRITE TESTS FIRST

- [ ] T015 [P] [US3] Unit test for context loading in `tests/agents/voice/test_service.py`
  - **Tests**: AC-FR005-001, AC-FR005-002, AC-FR005-003
  - **Verify**: Test FAILS before implementation

### Implementation for US-3

### T016: Implement get_context Server Tool
- **Status**: [ ] Pending
- **File**: `nikita/agents/voice/service.py`
- **Dependencies**: T012
- **ACs**:
  - [ ] AC-T016.1: `get_context(user_id)` returns VoiceContext with all user data
  - [ ] AC-T016.2: Loads chapter, score, vices from database
  - [ ] AC-T016.3: Loads recent memory from Graphiti
  - [ ] AC-T016.4: Formats for LLM consumption

### T017: Implement Voice Persona Additions
- **Status**: [ ] Pending
- **File**: `nikita/prompts/voice_persona.py`
- **Dependencies**: T011
- **ACs**:
  - [ ] AC-T017.1: VOICE_PERSONA_ADDITIONS constant with voice-specific behaviors
  - [ ] AC-T017.2: Comfortable silences guidance
  - [ ] AC-T017.3: Audible reactions (sighs, laughs, hmms)
  - [ ] AC-T017.4: Interruption handling instructions

### Verification for US-3

- [ ] T018 [US3] Run all US-3 tests - verify all pass

**Checkpoint**: Personality consistency functional. Voice matches text.

---

## Phase 6: US-4 Call Scoring (P1 - Must-Have)

**From spec.md**: Voice call ends → transcript scored → metrics updated

**Goal**: Score voice conversations and update user metrics

**Independent Test**: Complete call, verify score update with voice_call source

**Acceptance Criteria** (from spec.md):
- AC-FR006-001: Given call ends, When transcript analyzed, Then single aggregate score
- AC-FR006-002: Given good call, When scored, Then positive metric deltas
- AC-FR006-003: Given score history, When logged, Then source = "voice_call"

### Tests for US-4 ⚠️ WRITE TESTS FIRST

- [ ] T019 [P] [US4] Unit test for VoiceCallScorer in `tests/agents/voice/test_scoring.py`
  - **Tests**: AC-FR006-001, AC-FR006-002, AC-FR006-003
  - **Verify**: Test FAILS before implementation

### Implementation for US-4

### T020: Implement VoiceCallScorer
- **Status**: [ ] Pending
- **File**: `nikita/agents/voice/scoring.py`
- **Dependencies**: T004, ScoreCalculator (003)
- **ACs**:
  - [ ] AC-T020.1: `score_call(user_id, transcript)` analyzes full conversation
  - [ ] AC-T020.2: Returns aggregate CallScore with metric deltas
  - [ ] AC-T020.3: Considers call duration in scoring
  - [ ] AC-T020.4: Uses same LLM analysis as text agent

### T021: Implement Score Application
- **Status**: [ ] Pending
- **File**: `nikita/agents/voice/scoring.py`
- **Dependencies**: T020
- **ACs**:
  - [ ] AC-T021.1: `apply_score(user_id, score)` updates user_metrics
  - [ ] AC-T021.2: Logs to score_history with event_type='voice_call'
  - [ ] AC-T021.3: Includes call duration and session_id in event_details

### T022: Implement end_call Server Tool
- **Status**: [ ] Pending
- **File**: `nikita/agents/voice/service.py`
- **Dependencies**: T020, T021
- **ACs**:
  - [ ] AC-T022.1: `end_call(user_id, session_id)` fetches transcript from ElevenLabs
  - [ ] AC-T022.2: Calls VoiceCallScorer.score_call()
  - [ ] AC-T022.3: Applies score and returns CallResult
  - [ ] AC-T022.4: Updates last_interaction_at

### Verification for US-4

- [ ] T023 [US4] Run all US-4 tests - verify all pass

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

## Dependencies & Execution Order

### Phase Dependencies

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

---

## Progress Summary

| Phase/User Story | Tasks | Completed | Status |
|------------------|-------|-----------|--------|
| Phase 1: Setup | 3 | 0 | Pending |
| Phase 2: Models | 1 | 0 | Pending |
| US-1: Start Call | 5 | 0 | Pending |
| US-2: Conversation | 5 | 0 | Pending |
| US-3: Personality | 4 | 0 | Pending |
| US-4: Scoring | 5 | 0 | Pending |
| US-5: Memory | 5 | 0 | Pending |
| US-6: Server Tools | 3 | 0 | Pending |
| US-7: Availability | 4 | 0 | Pending |
| Phase 10: API | 1 | 0 | Pending |
| Phase 11: Final | 5 | 0 | Pending |
| **Total** | **41** | **0** | **Not Started** |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-29 | Initial task generation from plan.md |

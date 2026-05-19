# Tasks: Spec 033 - Unified Phone Number

**Version**: 1.0.0
**Status**: COMPLETE
**Created**: 2026-01-20
**Total Tasks**: 11 | **Completed**: 11

---

## US-1: Config Override for Onboarding (Already Implemented)

### T1.1: Verify Meta-Nikita Config Override
- **Status**: [x] Complete
- **File**: `nikita/onboarding/meta_nikita.py:307-363`
- **ACs**:
  - [x] AC-1.1.1: `build_meta_nikita_config_override()` returns valid structure
  - [x] AC-1.1.2: Override includes system prompt, first message, TTS
  - [x] AC-1.1.3: Dynamic variables include user_id, user_name

### T1.2: Verify Outbound Call Integration
- **Status**: [x] Complete
- **File**: `nikita/api/routes/onboarding.py:466-528`
- **ACs**:
  - [x] AC-1.2.1: `/onboarding/call/{user_id}` uses config override
  - [x] AC-1.2.2: Calls `make_outbound_call()` with override

---

## US-2: Nikita Callback After Onboarding

### T2.1: Voice Callback Trigger
- **Status**: [x] Complete (Already implemented)
- **File**: `nikita/onboarding/server_tools.py:398-481`
- **ACs**:
  - [x] AC-2.1.1: `_trigger_handoff()` calls `execute_handoff_with_voice_callback()`
  - [x] AC-2.1.2: Prefers voice if user has phone_number

### T2.2: Post-Onboarding First Message
- **Status**: [x] Complete
- **File**: `nikita/onboarding/handoff.py:561-589`
- **ACs**:
  - [x] AC-2.2.1: `_get_post_onboarding_first_message()` references "my friend"
  - [x] AC-2.2.2: Message personalizes with user's name
  - [x] AC-2.2.3: Deterministic template selection

### T2.3: Callback Retry Logic
- **Status**: [x] Complete
- **File**: `nikita/onboarding/handoff.py:438-559`
- **ACs**:
  - [x] AC-2.3.1: Retries up to 3 times
  - [x] AC-2.3.2: Exponential backoff (5s, 15s, 45s)
  - [x] AC-2.3.3: Returns `{"retries": N}` on exhaustion

---

## US-3: Inbound Call Routing (Already Implemented)

### T3.1: Voice Pre-Call Webhook
- **Status**: [x] Complete (Already implemented)
- **File**: `nikita/api/routes/voice.py:929-1014`
- **ACs**:
  - [x] AC-3.1.1: `/voice/pre-call` endpoint exists
  - [x] AC-3.1.2: Looks up user by caller_id

### T3.2: Inbound Handler
- **Status**: [x] Complete (Already implemented)
- **File**: `nikita/agents/voice/inbound.py:197-322`
- **ACs**:
  - [x] AC-3.2.1: Checks onboarding status
  - [x] AC-3.2.2: Rejects non-onboarded users gracefully
  - [x] AC-3.2.3: Returns dynamic_variables for all paths

### T3.3: Game-Over User Handling
- **Status**: [x] Complete (Already implemented)
- **File**: `nikita/agents/voice/inbound.py:280-301`
- **ACs**:
  - [x] AC-3.3.1: Detects unavailable users
  - [x] AC-3.3.2: Returns rejection with first_message override

---

## US-4: Testing

### T5.1: Post-Onboarding Message Tests
- **Status**: [x] Complete
- **File**: `tests/onboarding/test_handoff.py:430-476`
- **ACs**:
  - [x] AC-5.1.1: 4 tests for message generation
  - [x] AC-5.1.2: Tests reference "friend"

### T5.2: Callback Retry Tests
- **Status**: [x] Complete
- **File**: `tests/onboarding/test_handoff.py:479-604`
- **ACs**:
  - [x] AC-5.2.1: Test success on first try
  - [x] AC-5.2.2: Test retry on failure
  - [x] AC-5.2.3: Test exhaustion after max retries
  - [x] AC-5.2.4: Test config override in callback

### T5.3: Voice Handoff Integration Tests
- **Status**: [x] Complete
- **File**: `tests/onboarding/test_handoff.py:607-669`
- **ACs**:
  - [x] AC-5.3.1: Test user_name passed to callback
  - [x] AC-5.3.2: Test fallback to text on voice failure

---

## Progress Summary

| User Story | Tasks | Completed | Status |
|------------|-------|-----------|--------|
| US-1: Config Override | 2 | 2 | ✅ Complete |
| US-2: Nikita Callback | 3 | 3 | ✅ Complete |
| US-3: Inbound Routing | 3 | 3 | ✅ Complete |
| US-4: Testing | 3 | 3 | ✅ Complete |
| **Total** | **11** | **11** | **✅ 100%** |

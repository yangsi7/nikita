# Implementation Plan: Spec 033 - Unified Phone Number

**Version**: 1.0.0
**Status**: COMPLETE
**Created**: 2026-01-20

---

## Overview

This plan implements single phone number architecture for Nikita voice agents using ElevenLabs `conversation_config_override` pattern.

---

## Phase 1: Verify Existing Infrastructure (COMPLETE)

**Status**: ✅ Already implemented

1. **Config Override for Onboarding**
   - `meta_nikita.py:build_meta_nikita_config_override()` - Line 307-363
   - Builds complete override with system prompt, first message, TTS

2. **Outbound Call with Override**
   - `service.py:make_outbound_call()` - Line 539-682
   - Accepts `conversation_config_override` parameter

3. **Inbound Call Routing**
   - `inbound.py:handle_incoming_call()` - Line 197-322
   - Checks onboarding status, routes to Nikita

---

## Phase 2: Post-Onboarding First Message (IMPLEMENTED)

**Files Modified**:
- `nikita/onboarding/handoff.py`

**Changes**:
1. Added `_get_post_onboarding_first_message(user_name)` method (Line 561-589)
   - 3 template variants that reference "my friend" (Meta-Nikita)
   - Deterministic selection based on first char of name

2. Updated `initiate_nikita_callback()` (Line 438-559)
   - Now passes config override with post-onboarding first message
   - Personalizes with user's name

---

## Phase 3: Callback Retry Logic (IMPLEMENTED)

**Files Modified**:
- `nikita/onboarding/handoff.py`

**Changes**:
1. Added retry loop to `initiate_nikita_callback()` (Line 501-548)
   - `max_retries=3` parameter
   - Exponential backoff: 5s, 15s, 45s
   - Returns `{"success": False, "retries": N}` on exhaustion

2. Updated `execute_handoff_with_voice_callback()` (Line 624-631)
   - Now passes `user_name` to callback

---

## Phase 4: Testing (COMPLETE)

**Tests Added**: 10 new tests

| Test Class | Tests | Coverage |
|------------|-------|----------|
| `TestPostOnboardingFirstMessage` | 4 | Post-onboarding message generation |
| `TestNikitaCallbackRetry` | 4 | Retry logic, exhaustion, config override |
| `TestVoiceHandoffIntegration` | 2 | User name passing, fallback to text |

---

## Verification

```bash
# Run all handoff tests
python -m pytest tests/onboarding/test_handoff.py -v

# Expected: 29 passed
```

---

## Dependencies

| Dependency | Status |
|------------|--------|
| ElevenLabs Conversational AI 2.0 | ✅ Active |
| `conversation_config_override` | ✅ Supported |
| Pre-call webhook | ✅ Configured |
| Voice service | ✅ Deployed |

---

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Config override not working | Low | Tested in E2E |
| Callback timing issues | Medium | Retry logic added |
| Persona bleed | Low | Templates isolated |

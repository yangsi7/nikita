# Spec 033: Unified Phone Number Architecture

**Version**: 1.0.0
**Status**: COMPLETE
**Created**: 2026-01-20
**Implements**: Spec 033 - Unified Phone Number for Voice Agents

---

## Problem Statement

Nikita has two distinct voice agents with different call patterns:
- **Meta-Nikita**: Onboarding agent - OUTBOUND ONLY (system calls new users)
- **Main Nikita**: Regular conversation agent - BIDIRECTIONAL (user calls OR Nikita calls)

**Constraint**: ElevenLabs allows only ONE agent per phone number.

**Goal**: Single phone number architecture where:
1. Meta-Nikita calls new users for onboarding (outbound with config override)
2. After onboarding ends, Nikita calls user back with personalized first message
3. Returning users call the same number and reach Nikita directly

---

## Solution: Config Override Pattern

Instead of two phone numbers (one per agent), we use a single phone number with runtime `conversation_config_override`:

```
Phone (+41787950009) → Nikita Agent (Default)
   │
   ├── OUTBOUND ONBOARDING: conversation_config_override → Meta-Nikita persona
   │   └── Override: system prompt, first message, tools
   │
   └── ALL OTHER CALLS: Default Nikita persona
       └── Inbound: User calls Nikita
       └── Outbound: Nikita calls user (post-onboarding callback)
```

---

## User Stories

### US-1: Unified Phone Number
**As** Nikita game owner
**I want** a single phone number for all voice interactions
**So that** users have one number to save and I minimize costs

### US-2: Onboarding via Config Override
**As** a new user
**I want** Meta-Nikita to call me for onboarding
**So that** I can complete my profile before meeting Nikita

### US-3: Nikita Callback After Onboarding
**As** a new user who just completed onboarding
**I want** Nikita to call me after Meta-Nikita hangs up
**So that** I can start my relationship with Nikita immediately

### US-4: Returning User Inbound
**As** a returning player
**I want** to call the phone number and reach Nikita directly
**So that** I can talk to my girlfriend anytime

---

## Functional Requirements

### FR-001: Post-Onboarding First Message
Nikita's first message after onboarding MUST acknowledge Meta-Nikita as "my friend":
- References the onboarding call: "my friend just told me about you"
- Establishes Nikita as separate entity
- Personalizes with user's name

### FR-002: Callback Retry Logic
Voice callback after onboarding MUST include retry with exponential backoff:
- Up to 3 retry attempts
- Delays: 5s, 15s, 45s
- Falls back to Telegram text if all retries fail

### FR-003: Pre-Call Webhook for Inbound
Inbound calls MUST be handled by pre-call webhook:
- Looks up user by phone number (caller_id)
- Checks onboarding status (rejects pre-onboarding users)
- Returns dynamic variables and config override
- Returns Nikita persona for onboarded users

### FR-004: Config Override for Onboarding
Onboarding calls MUST use `conversation_config_override`:
- Meta-Nikita system prompt
- Meta-Nikita first message
- Meta-Nikita TTS settings

---

## Technical Implementation

### Files Modified

| File | Changes |
|------|---------|
| `nikita/onboarding/handoff.py` | Added `_get_post_onboarding_first_message()`, retry logic to `initiate_nikita_callback()` |
| `nikita/agents/voice/inbound.py` | Already implemented: onboarding status check, dynamic variables |
| `nikita/onboarding/meta_nikita.py` | Already implemented: `build_meta_nikita_config_override()` |
| `nikita/agents/voice/service.py` | Already implemented: `make_outbound_call()` with config override |

### Call Flows

**New User (Onboarding → Nikita Callback)**:
```
Telegram /start → OTP → /onboarding/call/{user_id}
    ↓
build_meta_nikita_config_override()
    ↓
make_outbound_call(override=Meta-Nikita)
    ↓
Meta-Nikita: Profile collection → complete_onboarding → end_call
    ↓
_trigger_handoff() → initiate_nikita_callback(user_name)
    ↓
make_outbound_call(override={first_message: post_onboarding_msg})
```

**Returning User (Inbound)**:
```
User calls +41787950009
    ↓
ElevenLabs pre-call webhook → /api/v1/voice/pre-call
    ↓
handle_incoming_call() → lookup user → check availability
    ↓
Return dynamic_variables + conversation_config_override (Nikita)
```

---

## Test Coverage

**29 tests** in `tests/onboarding/test_handoff.py`:
- 19 existing tests (all pass)
- 10 new tests for Spec 033:
  - 4 tests: `TestPostOnboardingFirstMessage`
  - 4 tests: `TestNikitaCallbackRetry`
  - 2 tests: `TestVoiceHandoffIntegration`

---

## Dependencies

- ElevenLabs Conversational AI 2.0
- `conversation_config_override` support in outbound calls
- Pre-call webhook for inbound routing

---

## Acceptance Criteria Summary

| AC | Description | Status |
|----|-------------|--------|
| AC-1 | Config override for onboarding | ✅ Already implemented |
| AC-2 | Nikita as default agent | ✅ Already implemented |
| AC-3 | Post-onboarding first message | ✅ Implemented |
| AC-4 | Callback retry logic | ✅ Implemented |
| AC-5 | Inbound call routing | ✅ Already implemented |

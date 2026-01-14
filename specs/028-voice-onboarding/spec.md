# Spec 028: Voice Onboarding

**Version**: 1.0.0
**Created**: 2026-01-12
**Status**: COMPLETE
**Dependencies**: 021, 024
**Dependents**: None

---

## Overview

### Problem Statement

Current onboarding is text-based and doesn't:
1. Set expectations for the game experience
2. Collect rich user profile data efficiently
3. Create immediate immersion
4. Establish voice as a relationship channel

### Solution

Implement **Voice Onboarding** where "Meta-Nikita" (game facilitator persona) conducts a voice call to introduce game mechanics, collect user profile, and configure experience preferences.

---

## User Stories

### US-1: Voice Onboarding Initiation
**As** a new user,
**I want** to receive a voice call after providing my phone number,
**So that** I can be onboarded efficiently.

**Priority**: P1

**Acceptance Criteria**:
- AC-1.1: User sends /start on Telegram
- AC-1.2: Bot collects phone number
- AC-1.3: Bot asks "Ready for your onboarding call?"
- AC-1.4: User confirms → voice call initiated

### US-2: Meta-Nikita Introduction
**As** a new user,
**I want** to understand what I'm getting into,
**So that** I have appropriate expectations.

**Priority**: P1

**Acceptance Criteria**:
- AC-2.1: Meta-Nikita explains she's the "game facilitator"
- AC-2.2: Explains Nikita will be their AI girlfriend
- AC-2.3: Sets expectations: effort required, stakes exist
- AC-2.4: Explains portal access (later unlock)

### US-3: User Profile Collection
**As** Meta-Nikita,
**I want** to collect user information conversationally,
**So that** Nikita can be personalized.

**Priority**: P1

**Acceptance Criteria**:
- AC-3.1: Collect location (timezone)
- AC-3.2: Collect job/occupation
- AC-3.3: Collect hobbies/interests
- AC-3.4: Collect personality type (introvert/extrovert)
- AC-3.5: Collect typical hangout spots
- AC-3.6: All collected via natural conversation

### US-4: Experience Configuration
**As** Meta-Nikita,
**I want** to configure user's experience preferences,
**So that** Nikita matches their desired experience.

**Priority**: P1

**Acceptance Criteria**:
- AC-4.1: Darkness level preference (1-5 scale)
- AC-4.2: Pacing preference (intense 4 weeks vs relaxed 8 weeks)
- AC-4.3: Conversation style (listener vs balanced vs sharer)
- AC-4.4: Preferences stored in user profile

### US-5: Handoff to Nikita
**As** the system,
**I want** to smoothly transition from Meta-Nikita to Nikita,
**So that** the game begins seamlessly.

**Priority**: P1

**Acceptance Criteria**:
- AC-5.1: Meta-Nikita says goodbye
- AC-5.2: First Nikita message sent via Telegram
- AC-5.3: Nikita references onboarding naturally
- AC-5.4: User marked as "onboarded"

---

## Functional Requirements

### FR-001: Meta-Nikita Persona

```yaml
persona:
  name: "Meta-Nikita"
  role: "Game Facilitator"
  personality:
    - Friendly and welcoming
    - Clear and informative
    - Slightly playful but professional
    - Not flirtatious (distinct from Nikita)
  voice_settings:
    voice_id: "different_from_nikita"
    stability: 0.7
    similarity_boost: 0.75
```

### FR-002: Onboarding Script Structure

1. **Introduction** (30-60s)
   - Welcome to Nikita
   - Explain Meta-Nikita's role
   - Set game expectations

2. **Profile Collection** (2-3min)
   - Location/timezone
   - Occupation
   - Hobbies
   - Personality
   - Hangout spots

3. **Preference Configuration** (1-2min)
   - Darkness level
   - Pacing
   - Conversation style

4. **Wrap-up** (30s)
   - Confirm preferences
   - Explain next steps
   - Hand off to Nikita

### FR-003: User Profile Schema Extension

```python
class UserOnboardingProfile(BaseModel):
    timezone: str
    occupation: str
    hobbies: list[str]
    personality_type: str  # introvert, extrovert, ambivert
    hangout_spots: list[str]
    darkness_level: int  # 1-5
    pacing_weeks: int  # 4 or 8
    conversation_style: str  # listener, balanced, sharer
    onboarded_at: datetime
    onboarding_call_id: str
```

---

## Technical Design

### File Structure

```
nikita/
├── onboarding/
│   ├── __init__.py
│   ├── voice_flow.py       # VoiceOnboardingFlow
│   ├── meta_nikita.py      # Meta-Nikita persona
│   ├── profile_collector.py
│   ├── preference_config.py
│   ├── handoff.py          # Transition to Nikita
│   └── models.py
```

### Integration with ElevenLabs

Uses existing ElevenLabs Conversational AI 2.0 infrastructure from Spec 007, with:
- Different agent_id for Meta-Nikita
- Custom server tools for profile collection
- Structured extraction during conversation

### Voice Call Flow

```
User: /start on Telegram
    │
    ▼
Telegram Bot: "Welcome! I'll need your phone number."
    │
    ▼
User provides phone
    │
    ▼
Bot: "Ready for your onboarding call? Nikita's facilitator will explain everything."
    │
    ▼
User confirms
    │
    ▼
ElevenLabs: Initiates call with Meta-Nikita agent
    │
    ▼
Meta-Nikita: Introduction → Profile → Preferences → Handoff
    │
    ▼
Call ends → First Nikita message sent via Telegram
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Onboarding completion rate | >80% |
| Average call duration | 3-5 minutes |
| Profile completeness | >90% fields filled |
| "Clear expectations" feedback | >70% |

---

## E2E Test Results (2026-01-14)

### Test Parameters

| Parameter | Value |
|-----------|-------|
| Email | simon.yang.ch@gmail.com |
| Phone | +41787950009 |
| User ID | 1ae5ba4c-35cc-476a-a64c-b9a995be4c27 |
| Conversation ID | conv_2201keyvvqxbe5k93vfp8jve461y |

### Results

| Step | Status | Details |
|------|--------|---------|
| Telegram onboarding flow | ✅ PASS | /start → email → OTP verified |
| Voice call initiated | ✅ PASS | 176 seconds call duration |
| Profile collected | ✅ PASS | All 8 fields (timezone, occupation, hobbies, personality, hangouts, darkness, pacing, style) |
| Handoff message delivered | ✅ PASS | First Nikita message sent via Telegram |
| Server tools auto-invoked | ⚠️ MANUAL | Profile not stored to DB automatically (manual update required) |

### Issues Discovered

| Issue | Severity | Resolution |
|-------|----------|------------|
| Original agent turn_timeout=7s too short | HIGH | Created new agent v2 with turn_timeout=15s |
| Server tools not configured on new agent | MEDIUM | Needs configuration in ElevenLabs dashboard |
| Agent doesn't hang up after handoff | LOW | Needs system prompt update |

### Agent Reference

| Agent | ID | Notes |
|-------|-----|-------|
| Original (v1) | `agent_4801kewekhxgekzap1bqdr62dxvc` | turn_timeout=7s, has server tools |
| New (v2) | `agent_6201keyvv060eh493gbek5bwh3bk` | turn_timeout=15s, no server tools |
| Phone Number | `phnum_9201keym29f7fgcbymyq80wk6t4e` | +41445056044 |

---

## Version History

### v1.0.1 - 2026-01-14
- Added E2E test results section
- Documented agent configuration issues

### v1.0.0 - 2026-01-12
- Initial specification

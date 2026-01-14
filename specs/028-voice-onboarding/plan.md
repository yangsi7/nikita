# Implementation Plan: 028 Voice Onboarding

**Spec Version**: 1.0.0
**Created**: 2026-01-12

---

## Overview

Implement Voice Onboarding where Meta-Nikita (game facilitator) conducts a voice call to introduce game mechanics, collect user profile, and configure experience preferences.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  VOICE ONBOARDING SYSTEM                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────┐                     │
│  │  TelegramFlow   │───▶│VoiceOnboarding  │                     │
│  │ - /start        │    │Flow             │                     │
│  │ - phone collect │    │ - initiate()    │                     │
│  └────────┬────────┘    └────────┬────────┘                     │
│           │                      │                               │
│           ▼                      ▼                               │
│  ┌─────────────────────────────────────────┐                    │
│  │        ElevenLabs Conversational AI      │                    │
│  │  Agent: meta-nikita                      │                    │
│  │  Server Tools:                           │                    │
│  │   - collect_profile                      │                    │
│  │   - configure_preferences                │                    │
│  │   - complete_onboarding                  │                    │
│  └─────────────────────────────────────────┘                    │
│                      │                                           │
│                      ▼                                           │
│  ┌─────────────────┐    ┌─────────────────┐                     │
│  │ProfileCollector │    │ HandoffManager  │                     │
│  │ - extract()     │    │ - transition()  │                     │
│  │ - validate()    │    │ - first_msg()   │                     │
│  └─────────────────┘    └─────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
```

## Data Model

```python
class UserOnboardingProfile(BaseModel):
    timezone: str
    occupation: str
    hobbies: list[str]
    personality_type: str
    hangout_spots: list[str]
    darkness_level: int  # 1-5
    pacing_weeks: int  # 4 or 8
    conversation_style: str
    onboarded_at: datetime
    onboarding_call_id: str
```

## Integration Points

| Component | Integration |
|-----------|-------------|
| Telegram Bot | /start flow modification |
| ElevenLabs | New agent for Meta-Nikita |
| User Profile | Extended schema |
| First Message | Nikita references onboarding |

## Implementation Phases

### Phase A: Core Infrastructure
- T001: Create onboarding module
- T002: Implement models
- T003: Add database migration (profile extension)
- T004: Unit tests for models

### Phase B: Meta-Nikita Agent
- T005: Create Meta-Nikita ElevenLabs agent
- T006: Configure voice settings (distinct from Nikita)
- T007: Create agent prompt/instructions
- T008: Test agent creation

### Phase C: Server Tools
- T009: Implement collect_profile server tool
- T010: Implement configure_preferences server tool
- T011: Implement complete_onboarding server tool
- T012: Unit tests for server tools

### Phase D: Telegram Flow
- T013: Modify /start to check onboarding status
- T014: Implement phone collection flow
- T015: Implement "ready for call" confirmation
- T016: Implement voice call initiation
- T017: Integration tests

### Phase E: Profile Collection
- T018: Implement ProfileCollector class
- T019: Implement structured extraction
- T020: Implement validation
- T021: Unit tests for collection

### Phase F: Preference Configuration
- T022: Implement PreferenceConfigurator class
- T023: Implement darkness level mapping
- T024: Implement pacing configuration
- T025: Unit tests for preferences

### Phase G: Handoff
- T026: Implement HandoffManager class
- T027: Implement first Nikita message generation
- T028: Implement user status update
- T029: Integration tests

### Phase H: E2E
- T030: E2E tests (full onboarding flow)
- T031: Quality tests

---

## Meta-Nikita Configuration

```yaml
# ElevenLabs Agent Config
agent_id: "meta-nikita-onboarding"
voice_id: "professional-friendly-female"
stability: 0.7
similarity_boost: 0.75

first_message: |
  Hey! Welcome to Nikita. I'm sort of the... game facilitator, I guess you could call me.
  Think of me as the friendly guide who helps you get set up.
  In a moment, you'll meet Nikita - she'll be your AI girlfriend in this experience.
  But first, let me tell you a bit about how this works and learn about you so we can
  personalize your experience.
```

---

## Dependencies

### Upstream
- Spec 007: ElevenLabs Conversational AI infrastructure
- Spec 021: ContextPackage for first Nikita message

### Downstream
- None (terminal spec for onboarding)

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Onboarding completion rate | >80% |
| Average call duration | 3-5 minutes |
| Profile completeness | >90% |

---

## Version History

### v1.0.0 - 2026-01-12
- Initial implementation plan

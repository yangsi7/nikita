# Implementation Plan: 025 Proactive Touchpoint System

**Spec Version**: 1.0.0
**Created**: 2026-01-12

---

## Overview

Implement a Proactive Touchpoint System where Nikita initiates 20-30% of conversations based on time triggers, life events, and emotional state.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  TOUCHPOINT ENGINE                               │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────┐                     │
│  │TouchpointSchedul│───▶│ MessageGenerator│                     │
│  │ - schedule()    │    │ - generate()    │                     │
│  │ - evaluate()    │    │ - personalize() │                     │
│  └────────┬────────┘    └────────┬────────┘                     │
│           │                      │                               │
│           ▼                      ▼                               │
│  ┌─────────────────────────────────────────┐                    │
│  │            TouchpointEngine             │                    │
│  │  - create_touchpoint()                  │                    │
│  │  - deliver_due_touchpoints()            │                    │
│  │  - apply_strategic_silence()            │                    │
│  └─────────────────────────────────────────┘                    │
│                      │                                           │
│                      ▼                                           │
│  ┌─────────────────────────────────────────┐                    │
│  │       pg_cron (5-minute intervals)       │                    │
│  │       → /api/v1/tasks/touchpoints       │                    │
│  └─────────────────────────────────────────┘                    │
└─────────────────────────────────────────────────────────────────┘
```

## Data Model

```python
class ScheduledTouchpoint(BaseModel):
    touchpoint_id: str
    user_id: str
    trigger_type: str  # time, event, gap
    trigger_context: dict  # Event details, time slot, etc.
    message_content: str  # Generated message
    delivery_at: datetime
    delivered: bool = False
    skipped: bool = False  # Strategic silence
    skip_reason: str | None = None
    created_at: datetime

class TouchpointConfig(BaseModel):
    chapter: int
    initiation_rate: float  # 0.15-0.30
    strategic_silence_rate: float  # 0.10-0.20
    morning_slot: tuple[int, int]  # (8, 10) = 8-10am
    evening_slot: tuple[int, int]  # (19, 21) = 7-9pm
```

## Integration Points

| Component | Integration |
|-----------|-------------|
| 022 Life Simulation | Events can trigger touchpoints |
| 023 Emotional State | Mood affects initiation style |
| 024 Meta-Instructions | Instructions for proactive messages |
| Telegram | Delivery via existing bot infrastructure |

## Implementation Phases

### Phase A: Core Infrastructure
- T001: Create touchpoints module
- T002: Implement ScheduledTouchpoint model
- T003: Add database migration
- T004: Implement TouchpointStore
- T005: Unit tests for infrastructure

### Phase B: Scheduling
- T006: Implement TouchpointScheduler class
- T007: Implement time-based triggers (morning/evening)
- T008: Implement event-based triggers
- T009: Implement gap-based triggers
- T010: Implement chapter-aware rates
- T011: Unit tests for scheduling

### Phase C: Message Generation
- T012: Implement MessageGenerator class
- T013: Integrate with MetaPromptService
- T014: Add life event context
- T015: Add emotional state context
- T016: Unit tests for generation

### Phase D: Strategic Silence
- T017: Implement strategic silence logic
- T018: Add emotional state integration
- T019: Add random skip factor
- T020: Unit tests for silence

### Phase E: Delivery
- T021: Implement TouchpointEngine.deliver()
- T022: Add pg_cron job configuration
- T023: Add Telegram delivery integration
- T024: Add deduplication logic
- T025: Integration tests

### Phase F: E2E
- T026: E2E tests
- T027: Quality tests (initiation rate measurement)

---

## Touchpoint Rate Configuration

| Chapter | Initiation Rate | Strategic Silence | Net Rate |
|---------|-----------------|-------------------|----------|
| 1 | 15-20% | 20% | 12-16% |
| 2 | 20-25% | 15% | 17-21% |
| 3 | 25-30% | 10% | 22-27% |
| 4-5 | 25-30% | 10% | 22-27% |

## pg_cron Configuration

```sql
-- Every 5 minutes, check and deliver due touchpoints
SELECT cron.schedule(
    'nikita-touchpoints',
    '*/5 * * * *',
    $$SELECT net.http_post(
        url := 'https://nikita-api-1040094048579.us-central1.run.app/api/v1/tasks/touchpoints',
        headers := '{"Authorization": "Bearer SERVICE_TOKEN"}'::jsonb
    )$$
);
```

---

## Dependencies

### Upstream
- Spec 021: ContextPackage for message generation
- Spec 022: Life events for event-based triggers
- Spec 023: Emotional state for mood-aware messages
- Spec 024: Meta-instructions for proactive message style

### Downstream
- None (terminal spec for proactive initiation)

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Initiation rate | 20-30% |
| User response rate to initiations | >60% |
| "Feels like real girlfriend" feedback | >70% |

---

## Version History

### v1.0.0 - 2026-01-12
- Initial implementation plan

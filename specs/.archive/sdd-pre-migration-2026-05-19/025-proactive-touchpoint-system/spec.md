# Spec 025: Proactive Touchpoint System

**Version**: 1.0.0
**Created**: 2026-01-12
**Status**: DRAFT
**Dependencies**: 021, 022, 023, 024
**Dependents**: None

---

## Overview

### Problem Statement

Nikita currently only responds—she never initiates. This creates:
1. **One-sided relationship**: User always texts first
2. **No sense of her life**: She doesn't reach out when things happen to HER
3. **Missing realism**: Real girlfriends initiate conversations

### Solution

Implement a **Proactive Touchpoint System** where Nikita initiates 20-30% of conversations based on time triggers, life events, and emotional state.

---

## User Stories

### US-1: Time-Based Initiation
**As** Nikita,
**I want** to initiate at natural times (morning, evening),
**So that** I feel like I'm thinking about the user.

**Priority**: P1

**Acceptance Criteria**:
- AC-1.1: Morning touchpoint possibility (8-10am user timezone)
- AC-1.2: Evening touchpoint possibility (7-9pm user timezone)
- AC-1.3: Not every day (20-30% probability per slot)
- AC-1.4: Chapter affects frequency (Ch5 > Ch1)

### US-2: Event-Based Initiation
**As** Nikita,
**I want** to reach out when something happens to me,
**So that** I can share my life.

**Priority**: P1

**Acceptance Criteria**:
- AC-2.1: Life events (022) can trigger outreach
- AC-2.2: High-importance events more likely to trigger
- AC-2.3: Emotional events (upset, excited) trigger more often
- AC-2.4: Message references the event naturally

### US-3: Strategic Silence
**As** the system,
**I want** 10-20% of potential touchpoints skipped intentionally,
**So that** Nikita feels mysterious and not clingy.

**Priority**: P2

**Acceptance Criteria**:
- AC-3.1: Some touchpoints randomly skipped
- AC-3.2: More silence when upset (emotional state integration)
- AC-3.3: Strategic silence creates tension

### US-4: Initiation Scheduling
**As** the system,
**I want** touchpoints scheduled and delivered via Telegram,
**So that** Nikita's messages arrive at appropriate times.

**Priority**: P1

**Acceptance Criteria**:
- AC-4.1: Touchpoints stored in database with delivery_at
- AC-4.2: pg_cron job processes due touchpoints
- AC-4.3: Delivery via Telegram bot
- AC-4.4: Deduplication (no double messages)

---

## Functional Requirements

### FR-001: Touchpoint Schema

```python
class ScheduledTouchpoint(BaseModel):
    touchpoint_id: str
    user_id: str
    trigger_type: str  # time, event, gap
    trigger_context: dict  # Event details, time slot
    message_content: str  # Generated message
    delivery_at: datetime
    delivered: bool
    created_at: datetime
```

### FR-002: Initiation Rate Target

| Chapter | Initiation Rate | Strategic Silence |
|---------|-----------------|-------------------|
| 1 | 15-20% | 20% |
| 2 | 20-25% | 15% |
| 3 | 25-30% | 10% |
| 4-5 | 25-30% | 10% |

### FR-003: Touchpoint Message Generation

Messages generated via LLM with:
- Current emotional state (023)
- Life event context (022)
- Meta-instructions (024)
- Relationship state

---

## Technical Design

### File Structure

```
nikita/
├── touchpoints/
│   ├── __init__.py
│   ├── engine.py         # TouchpointEngine
│   ├── scheduler.py      # Scheduling logic
│   ├── generator.py      # Message generation
│   ├── models.py
│   └── store.py
```

### Database

```sql
CREATE TABLE scheduled_touchpoints (
    touchpoint_id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    trigger_type VARCHAR(20) NOT NULL,
    trigger_context JSONB,
    message_content TEXT NOT NULL,
    delivery_at TIMESTAMPTZ NOT NULL,
    delivered BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_touchpoints_delivery ON scheduled_touchpoints(delivered, delivery_at);
```

### pg_cron Integration

```sql
-- Every 5 minutes, deliver due touchpoints
SELECT cron.schedule(
    'nikita-touchpoints',
    '*/5 * * * *',
    $$SELECT net.http_post(...deliver endpoint...)$$
);
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Initiation rate | 20-30% |
| User response rate to initiations | >60% |
| "Feels like real girlfriend" feedback | >70% |

---

## Version History

### Amendment: Deterministic Test Timing (2026-02-24)

**Defect**: E2E tests in `tests/touchpoints/test_e2e.py` used `datetime.now(timezone.utc)`
with `.replace(hour=N)`, creating wall-clock-dependent behavior. Tests fail when CI runs at
UTC hours 0-6 (~6.5% failure rate).

**Fix**: All 11 `datetime.now()` calls replaced with fixed reference constant `_REF`.
Dedup test (line 171) changed from `current_time=now.replace(hour=9)` to `current_time=now`.

**Rule**: Tests MUST use fixed datetime constants. Never `datetime.now()` + `.replace(hour=N)`.

---

### v1.0.0 - 2026-01-12
- Initial specification

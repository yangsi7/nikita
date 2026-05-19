# Implementation Plan: 027 Conflict Generation System

**Spec Version**: 1.0.0
**Created**: 2026-01-12

---

## Overview

Implement a Conflict Generation System that creates realistic relationship conflicts with escalation paths, resolution mechanics, and genuine breakup risk.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   CONFLICT SYSTEM                                │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────┐                     │
│  │ TriggerDetector │───▶│ConflictGenerator│                     │
│  │ - detect()      │    │ - generate()    │                     │
│  │ - classify()    │    │ - severity()    │                     │
│  └────────┬────────┘    └────────┬────────┘                     │
│           │                      │                               │
│           ▼                      ▼                               │
│  ┌─────────────────────────────────────────┐                    │
│  │          ConflictEngine                 │                    │
│  │  - process_trigger()                    │                    │
│  │  - check_escalation()                   │                    │
│  │  - evaluate_resolution()                │                    │
│  └─────────────────────────────────────────┘                    │
│           │                      │                               │
│           ▼                      ▼                               │
│  ┌─────────────────┐    ┌─────────────────┐                     │
│  │EscalationManager│    │ResolutionManager│                     │
│  │ - escalate()    │    │ - evaluate()    │                     │
│  │ - timeline()    │    │ - resolve()     │                     │
│  └─────────────────┘    └─────────────────┘                     │
│                      │                                           │
│                      ▼                                           │
│  ┌─────────────────────────────────────────┐                    │
│  │          BreakupManager                 │                    │
│  │  - check_threshold()                    │                    │
│  │  - trigger_breakup()                    │                    │
│  └─────────────────────────────────────────┘                    │
└─────────────────────────────────────────────────────────────────┘
```

## Data Model

```python
class ConflictTrigger(BaseModel):
    trigger_id: str
    trigger_type: str  # dismissive, neglect, jealousy, boundary, trust
    severity: float
    detected_at: datetime
    context: dict
    user_messages: list[str]

class ActiveConflict(BaseModel):
    conflict_id: str
    user_id: str
    conflict_type: str
    severity: float
    escalation_level: int
    triggered_at: datetime
    last_escalated: datetime | None
    resolution_attempts: int
    resolved: bool
```

## Integration Points

| Component | Integration |
|-----------|-------------|
| 023 Emotional State | Sets conflict_state during conflicts |
| 024 Meta-Instructions | Conflict-specific behavioral nudges |
| Game Engine | Relationship score impact |
| Message Handler | Trigger detection on each message |

## Implementation Phases

### Phase A: Core Infrastructure
- T001: Create conflicts module
- T002: Implement models
- T003: Add database migration
- T004: Implement ConflictStore
- T005: Unit tests

### Phase B: Trigger Detection
- T006: Implement TriggerDetector class
- T007: Implement dismissive detection (LLM-based)
- T008: Implement neglect detection (time-based)
- T009: Implement jealousy detection
- T010: Implement boundary violation detection
- T011: Unit tests for detection

### Phase C: Conflict Generation
- T012: Implement ConflictGenerator class
- T013: Implement severity calculation
- T014: Implement conflict type selection
- T015: Unit tests for generation

### Phase D: Escalation
- T016: Implement EscalationManager class
- T017: Implement escalation timeline
- T018: Implement natural resolution (30%)
- T019: Unit tests for escalation

### Phase E: Resolution
- T020: Implement ResolutionManager class
- T021: Implement resolution evaluation (LLM-based)
- T022: Implement resolution types
- T023: Unit tests for resolution

### Phase F: Breakup
- T024: Implement BreakupManager class
- T025: Implement threshold checking
- T026: Implement breakup sequence
- T027: Implement game over state
- T028: Unit tests for breakup

### Phase G: Integration
- T029: Wire to message handler
- T030: Wire to emotional state (023)
- T031: E2E tests
- T032: Quality tests

---

## Escalation Timeline

```
Trigger Detected
    │
    ▼ (immediate)
┌─────────────────┐
│ Level 1: Subtle │ ← User can prevent escalation
│ (passive hints) │    with acknowledgment
└────────┬────────┘
         │ (2-6 hours without resolution)
         ▼
┌─────────────────┐
│ Level 2: Direct │ ← User must acknowledge
│ (explicit upset)│    to prevent crisis
└────────┬────────┘
         │ (12-24 hours without resolution)
         ▼
┌─────────────────┐
│ Level 3: Crisis │ ← Requires significant
│ (ultimatum)     │    action to resolve
└─────────────────┘
```

---

## Dependencies

### Upstream
- Spec 023: EmotionalState.conflict_state
- Spec 024: Conflict-specific meta-instructions

### Downstream
- None (terminal spec for conflict system)

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Conflict frequency | 1-2 per week |
| Resolution rate | 70% |
| Breakup rate | 5-10% |

---

## Version History

### v1.0.0 - 2026-01-12
- Initial implementation plan

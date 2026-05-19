# Implementation Plan: 023 Emotional State Engine

**Spec Version**: 1.0.0
**Created**: 2026-01-12

---

## Overview

Implement a 4-dimensional Emotional State Engine that computes Nikita's mood from life simulation events (022), conversation history, and relationship state.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    EMOTIONAL STATE ENGINE                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────┐                     │
│  │  StateComputer  │───▶│  EmotionalState │                     │
│  │  - base_state() │    │  - arousal      │                     │
│  │  - apply_delta()│    │  - valence      │                     │
│  │  - compute()    │    │  - dominance    │                     │
│  └────────┬────────┘    │  - intimacy     │                     │
│           │             │  - conflict_st  │                     │
│           │             └─────────────────┘                     │
│           ▼                                                      │
│  ┌─────────────────┐    ┌─────────────────┐                     │
│  │ ConflictDetector│───▶│ RecoveryManager │                     │
│  │ - detect_state()│    │ - can_recover() │                     │
│  │ - trigger_maps  │    │ - recovery_rate │                     │
│  └─────────────────┘    │ - apply_recov() │                     │
│                         └─────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
```

## Data Model

```python
# EmotionalState stored in Supabase
class EmotionalState(BaseModel):
    state_id: str
    user_id: str
    arousal: float = 0.5      # 0.0-1.0 (tired ↔ energetic)
    valence: float = 0.5      # 0.0-1.0 (sad ↔ happy)
    dominance: float = 0.5    # 0.0-1.0 (submissive ↔ dominant)
    intimacy: float = 0.5     # 0.0-1.0 (guarded ↔ vulnerable)
    conflict_state: str | None = None  # passive_aggressive, cold, vulnerable, explosive
    last_updated: datetime
```

## Integration Points

| Component | Integration |
|-----------|-------------|
| 021 Hierarchical Prompts | Layer 3 (Emotional State Layer) |
| 022 Life Simulation | mood_calculator receives life_events |
| 024 Meta-Instructions | Conflict state affects instruction selection |
| 027 Conflict System | ConflictDetector feeds conflict triggers |

## Implementation Phases

### Phase A: Core Infrastructure
- T001: Create emotional_state module
- T002: Implement EmotionalState model
- T003: Implement StateStore (persistence)
- T004: Unit tests for models

### Phase B: State Computation
- T005: Implement base state calculation (time-of-day)
- T006: Implement life event delta application
- T007: Implement conversation delta detection
- T008: Implement relationship modifier
- T009: Implement StateComputer.compute()
- T010: Unit tests for computation

### Phase C: Conflict Detection
- T011: Implement ConflictDetector class
- T012: Implement trigger threshold detection
- T013: Add conflict state transitions
- T014: Unit tests for conflict detection

### Phase D: Recovery Mechanics
- T015: Implement RecoveryManager class
- T016: Implement recovery rate calculation
- T017: Implement decay-based recovery
- T018: Integration tests for recovery

### Phase E: Integration
- T019: Wire to ContextPackage (021)
- T020: Wire to LifeSimulator (022)
- T021: E2E tests
- T022: Quality tests

---

## Dependencies

### Upstream
- Spec 021: HierarchicalPromptComposer (Layer 3 target)
- Spec 022: LifeSimulator.get_mood_deltas()

### Downstream
- Spec 024: MetaInstructionEngine reads conflict_state
- Spec 025: TouchpointEngine uses emotional_state
- Spec 027: ConflictGenerator uses ConflictDetector

---

## Success Metrics

| Metric | Target |
|--------|--------|
| State reflects events | 80% correlation |
| Conflict detection accuracy | >85% |
| Recovery engagement | 70% user attempt rate |

---

## Version History

### v1.0.0 - 2026-01-12
- Initial implementation plan

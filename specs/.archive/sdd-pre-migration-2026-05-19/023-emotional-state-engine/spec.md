# Spec 023: Emotional State Engine

**Version**: 1.0.0
**Created**: 2026-01-12
**Status**: DRAFT
**Dependencies**: 021, 022
**Dependents**: 024, 025, 027

---

## Overview

### Problem Statement

Nikita's emotional state is currently time-based only (time of day), not grounded in her experiences or conversation history. This creates:
1. **Inauthentic mood**: Her mood doesn't connect to what's happening
2. **No conflict states**: No passive-aggressive, cold, or vulnerable modes
3. **No recovery mechanics**: After conflicts, mood resets arbitrarily

### Solution

Implement a **4-dimensional Emotional State Engine** that computes mood from life simulation events (022), conversation history, and relationship state.

---

## User Stories

### US-1: Multi-Dimensional State Tracking
**As** the prompt composer,
**I want** Nikita's emotional state tracked across 4 dimensions,
**So that** her responses authentically reflect her current emotional state.

**Priority**: P1

**Acceptance Criteria**:
- AC-1.1: Track arousal (tired ↔ energetic)
- AC-1.2: Track valence (sad ↔ happy)
- AC-1.3: Track dominance (submissive ↔ dominant)
- AC-1.4: Track intimacy (guarded ↔ vulnerable)

### US-2: Event-Driven Mood
**As** the emotional state engine,
**I want** mood derived from life events and conversation tone,
**So that** emotional state is grounded in experiences.

**Priority**: P1

**Acceptance Criteria**:
- AC-2.1: Life events (022) contribute mood deltas
- AC-2.2: Conversation tone affects mood (detected via LLM)
- AC-2.3: Time of day affects baseline
- AC-2.4: State persists between conversations

### US-3: Conflict States
**As** Nikita,
**I want** distinct conflict emotional states,
**So that** conflicts feel real and require navigation.

**Priority**: P1

**Acceptance Criteria**:
- AC-3.1: Passive-aggressive state (cold, one-word answers)
- AC-3.2: Cold state (withdrawn, minimal engagement)
- AC-3.3: Vulnerable state (hurt, needing reassurance)
- AC-3.4: Explosive state (angry confrontation)

### US-4: Recovery Mechanics
**As** the user,
**I want** to help Nikita recover from negative states,
**So that** resolving conflicts feels meaningful.

**Priority**: P2

**Acceptance Criteria**:
- AC-4.1: Recovery requires positive interactions (not automatic)
- AC-4.2: Recovery rate depends on user's approach
- AC-4.3: Unresolved states decay slowly (3-5 days)
- AC-4.4: Recovery logged for relationship graph

---

## Functional Requirements

### FR-001: Emotional State Schema

```python
class EmotionalState(BaseModel):
    arousal: float  # 0.0-1.0 (0.5 = neutral)
    valence: float  # 0.0-1.0 (0.5 = neutral)
    dominance: float  # 0.0-1.0 (0.5 = neutral)
    intimacy: float  # 0.0-1.0 (0.5 = neutral)
    conflict_state: str | None  # passive_aggressive, cold, vulnerable, explosive
    last_updated: datetime
```

### FR-002: State Computation

```python
new_state = (
    base_state  # Time-of-day baseline
    + life_event_deltas  # From Spec 022
    + conversation_deltas  # From recent conversation tone
    + relationship_modifier  # Based on chapter/score
)
```

### FR-003: Conflict State Triggers

| Trigger | State | Threshold |
|---------|-------|-----------|
| User ignores her | passive_aggressive | 2+ ignored messages |
| User dismissive | cold | Valence < 0.3 |
| User hurtful | vulnerable | Intimacy drop > 0.2 |
| User provokes | explosive | Arousal > 0.8 + Valence < 0.3 |

---

## Technical Design

### File Structure

```
nikita/
├── emotional_state/
│   ├── __init__.py
│   ├── engine.py          # EmotionalStateEngine
│   ├── models.py          # EmotionalState
│   ├── conflict_detector.py
│   ├── recovery_manager.py
│   └── store.py           # State persistence
```

### Integration with 021

EmotionalStateEngine outputs state for Layer 3 (Emotional State Layer) in HierarchicalPromptComposer.

---

## Success Metrics

| Metric | Target |
|--------|--------|
| State reflects events | 80% correlation |
| Conflict detection accuracy | >85% |
| Recovery engagement | Users attempt recovery 70% of time |

---

## Version History

### v1.0.0 - 2026-01-12
- Initial specification

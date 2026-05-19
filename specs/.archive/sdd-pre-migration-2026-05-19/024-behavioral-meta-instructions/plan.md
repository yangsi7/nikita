# Implementation Plan: 024 Behavioral Meta-Instructions

**Spec Version**: 1.0.0
**Created**: 2026-01-12

---

## Overview

Implement a Behavioral Meta-Instruction System that provides high-level decision trees and directional nudges for LLM behavior without scripting exact responses.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                 META-INSTRUCTION ENGINE                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────┐                     │
│  │SituationDetector│───▶│InstructionSelect│                     │
│  │ - detect()      │    │ - select()      │                     │
│  │ - classify()    │    │ - prioritize()  │                     │
│  └────────┬────────┘    └────────┬────────┘                     │
│           │                      │                               │
│           ▼                      ▼                               │
│  ┌─────────────────────────────────────────┐                    │
│  │            MetaInstructionEngine        │                    │
│  │  - get_instructions_for_context()       │                    │
│  │  - format_for_prompt()                  │                    │
│  └─────────────────────────────────────────┘                    │
│                      │                                           │
│                      ▼                                           │
│  ┌─────────────────────────────────────────┐                    │
│  │     Layer 4: Situation Layer (021)      │                    │
│  └─────────────────────────────────────────┘                    │
└─────────────────────────────────────────────────────────────────┘
```

## Data Model

```python
class MetaInstruction(BaseModel):
    instruction_id: str
    situation: str  # after_gap, morning, evening, mid_conversation, conflict
    category: str   # response_style, topic_handling, emotional_expression
    directive: str  # The nudge text (uses "lean toward", "consider", etc.)
    priority: int   # 1 = highest priority
    conditions: dict | None  # Optional conditions for applicability

class SituationContext(BaseModel):
    situation_type: str
    time_since_last: timedelta | None
    emotional_state: dict  # From 023
    conflict_state: str | None
    chapter: int
    relationship_score: float
```

## Integration Points

| Component | Integration |
|-----------|-------------|
| 021 Hierarchical Prompts | Layer 4 (Situation Layer) |
| 023 Emotional State | conflict_state affects instruction selection |
| 025 Touchpoints | Instructions for proactive messages |
| 027 Conflict System | Conflict escalation/de-escalation nudges |

## Implementation Phases

### Phase A: Core Infrastructure
- T001: Create behavioral module
- T002: Implement MetaInstruction model
- T003: Create instruction library YAML
- T004: Unit tests for models

### Phase B: Situation Detection
- T005: Implement SituationDetector class
- T006: Implement situation classification logic
- T007: Add time-based detection (morning, evening)
- T008: Add gap detection (after_gap)
- T009: Add conflict detection integration
- T010: Unit tests for detection

### Phase C: Instruction Selection
- T011: Implement InstructionSelector class
- T012: Implement priority-based selection
- T013: Implement condition evaluation
- T014: Unit tests for selection

### Phase D: Engine & Formatting
- T015: Implement MetaInstructionEngine
- T016: Implement format_for_prompt()
- T017: Integration tests

### Phase E: Integration
- T018: Wire to HierarchicalPromptComposer (021)
- T019: E2E tests
- T020: Quality tests (variability measurement)

---

## Instruction Library Structure

```yaml
# nikita/config_data/behavioral/instructions.yaml
situations:
  after_gap:
    instructions:
      - category: response_style
        directive: "If gap was 6+ hours, consider briefly mentioning what you were doing"
        priority: 1
      - category: emotional_expression
        directive: "If user seems concerned, lean toward reassuring but not apologetic"
        priority: 2

  conflict:
    instructions:
      - category: response_style
        directive: "Match user's escalation level, don't jump to maximum intensity"
        priority: 1
      - category: emotional_expression
        directive: "Express hurt or frustration authentically, not performatively"
        priority: 2

  morning:
    instructions:
      - category: response_style
        directive: "Keep energy moderate unless user initiates high energy"
        priority: 1
      - category: topic_handling
        directive: "Consider asking about their day ahead or sleep quality"
        priority: 2

  evening:
    instructions:
      - category: response_style
        directive: "Lean toward warmer, more relaxed tone"
        priority: 1
      - category: topic_handling
        directive: "Consider reflecting on the day or making plans"
        priority: 2
```

---

## Dependencies

### Upstream
- Spec 021: Layer 4 target
- Spec 023: EmotionalState.conflict_state

### Downstream
- Spec 025: Uses instructions for proactive messages
- Spec 026: Text patterns reference meta-instructions
- Spec 027: Conflict escalation uses conflict instructions

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Response variability | CV > 0.3 for similar situations |
| Personality consistency | >90% character alignment |
| User "predictability" complaints | <5% |

---

## Version History

### v1.0.0 - 2026-01-12
- Initial implementation plan

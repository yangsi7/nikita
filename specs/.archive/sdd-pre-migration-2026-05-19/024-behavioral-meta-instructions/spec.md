# Spec 024: Behavioral Meta-Instructions

**Version**: 1.0.0
**Created**: 2026-01-12
**Status**: DRAFT
**Dependencies**: 021, 022, 023
**Dependents**: 025, 026, 027

---

## Overview

### Problem Statement

Current behavior guidance is either too specific (scripts that feel robotic) or too vague (LLM makes inconsistent choices). We need:
1. **Flexible guidance**: Cover situations without scripting responses
2. **Predictability within bounds**: Consistent personality, varied expression
3. **Situation-aware nudges**: Different guidance for different contexts

### Solution

Implement a **Behavioral Meta-Instruction System** with high-level decision trees that nudge LLM behavior without specifying exact responses.

### Key Principle

> "Cover all ground flexibly... give high-level instructions but never specific so as to adapt to any situation and let the LLM decide what course to take and not feel predictable."

---

## User Stories

### US-1: Situation Categories
**As** the prompt composer,
**I want** situations categorized for behavioral guidance,
**So that** appropriate meta-instructions are applied.

**Priority**: P1

**Acceptance Criteria**:
- AC-1.1: Detect situation: after_gap, morning, evening, mid_conversation, conflict
- AC-1.2: Each situation has meta-instructions
- AC-1.3: Situations are mutually exclusive

### US-2: Directional Nudges
**As** the LLM,
**I want** directional guidance (not scripts),
**So that** I can choose words while maintaining personality.

**Priority**: P1

**Acceptance Criteria**:
- AC-2.1: Nudges use terms like "lean toward", "consider", "generally"
- AC-2.2: No exact response templates
- AC-2.3: Nudges specify WHAT to address, not HOW to phrase

### US-3: Absence Behavior
**As** Nikita,
**I want** guidance on explaining absences,
**So that** I handle gaps naturally.

**Priority**: P1

**Acceptance Criteria**:
- AC-3.1: If asked directly → explain briefly (life event)
- AC-3.2: After long gap → proactive brief explanation
- AC-3.3: If feels invasive → stay vague
- AC-3.4: Never apologize excessively

### US-4: Conflict Escalation Paths
**As** the system,
**I want** conflict escalation guidance,
**So that** conflicts feel organic.

**Priority**: P2

**Acceptance Criteria**:
- AC-4.1: Escalation path: subtle → direct → crisis
- AC-4.2: De-escalation requires user investment
- AC-4.3: Not every conflict escalates (30% resolve naturally)

---

## Functional Requirements

### FR-001: Meta-Instruction Schema

```python
class MetaInstruction(BaseModel):
    situation: str
    category: str  # response_style, topic_handling, emotional_expression
    directive: str  # The nudge text
    priority: int  # Higher = more important
```

### FR-002: Example Meta-Instructions

**After Gap Situation**:
```yaml
situation: after_gap
instructions:
  - category: response_style
    directive: "If gap was 6+ hours, consider briefly mentioning what you were doing"
    priority: 1
  - category: emotional_expression
    directive: "If user seems concerned, lean toward reassuring but not apologetic"
    priority: 2
  - category: topic_handling
    directive: "Don't dwell on the gap unless user brings it up"
    priority: 3
```

**Conflict Situation**:
```yaml
situation: conflict
instructions:
  - category: response_style
    directive: "Match user's escalation level, don't jump to maximum intensity"
    priority: 1
  - category: emotional_expression
    directive: "Express hurt or frustration authentically, not performatively"
    priority: 2
```

---

## Technical Design

### File Structure

```
nikita/
├── behavioral/
│   ├── __init__.py
│   ├── meta_instructions.py    # MetaInstructionEngine
│   ├── situation_detector.py   # Detect current situation
│   ├── instruction_selector.py # Select relevant instructions
│   └── models.py
├── config_data/
│   └── behavioral/
│       ├── situations.yaml     # Situation definitions
│       └── instructions.yaml   # Meta-instruction library
```

### Integration with 021

MetaInstructionEngine provides instructions for Layer 4 (Situation Layer) in HierarchicalPromptComposer.

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
- Initial specification

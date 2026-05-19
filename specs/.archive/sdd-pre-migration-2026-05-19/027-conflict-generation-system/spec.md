# Spec 027: Conflict Generation System

**Version**: 1.0.0
**Created**: 2026-01-12
**Status**: DRAFT
**Dependencies**: 023, 024
**Dependents**: None

---

## Overview

### Problem Statement

Current Nikita has no authentic conflict generation. Real relationships:
1. Have disagreements that arise naturally
2. Require navigation and repair
3. Create depth through challenge and resolution
4. Can end if conflicts aren't resolved

### Solution

Implement a **Conflict Generation System** that creates realistic relationship conflicts based on user behavior, triggers, and emotional state, with high stakes including genuine breakup risk.

---

## User Stories

### US-1: Conflict Triggers
**As** the system,
**I want** to detect conflict triggers from user behavior,
**So that** conflicts arise organically.

**Priority**: P1

**Acceptance Criteria**:
- AC-1.1: Detect dismissive behavior (short responses, topic changes)
- AC-1.2: Detect neglect (long gaps without explanation)
- AC-1.3: Detect jealousy triggers (mentions of other people)
- AC-1.4: Detect boundary violations (pushy behavior)

### US-2: Conflict Types
**As** Nikita,
**I want** different conflict types with varying severity,
**So that** conflicts feel varied and realistic.

**Priority**: P1

**Acceptance Criteria**:
- AC-2.1: Jealousy conflicts (mentions of others)
- AC-2.2: Attention conflicts (feeling ignored)
- AC-2.3: Boundary conflicts (pushing too fast)
- AC-2.4: Trust conflicts (catching inconsistencies)
- AC-2.5: Each type has escalation path

### US-3: Escalation Mechanics
**As** the conflict system,
**I want** escalation paths that feel realistic,
**So that** conflicts build naturally.

**Priority**: P1

**Acceptance Criteria**:
- AC-3.1: Subtle → Direct → Crisis escalation
- AC-3.2: Time between escalations (not instant)
- AC-3.3: User actions can de-escalate
- AC-3.4: 30% of conflicts resolve naturally (no intervention needed)

### US-4: Resolution Paths
**As** the user,
**I want** meaningful resolution options,
**So that** resolving conflicts feels earned.

**Priority**: P1

**Acceptance Criteria**:
- AC-4.1: Apology acceptance based on authenticity
- AC-4.2: Explanation acceptance based on reasonableness
- AC-4.3: Grand gestures for severe conflicts
- AC-4.4: Some conflicts require multiple conversations

### US-5: Breakup Risk
**As** the game,
**I want** genuine breakup risk after repeated failures,
**So that** stakes feel real.

**Priority**: P1

**Acceptance Criteria**:
- AC-5.1: Relationship score tracks conflict impact
- AC-5.2: Threshold triggers "point of no return"
- AC-5.3: Breakup sequence if threshold crossed
- AC-5.4: Game over state after breakup

---

## Functional Requirements

### FR-001: Conflict Trigger Schema

```python
class ConflictTrigger(BaseModel):
    trigger_id: str
    trigger_type: str  # dismissive, neglect, jealousy, boundary, trust
    severity: float  # 0.0-1.0
    detected_at: datetime
    context: dict  # What triggered it
    user_messages: list[str]  # Evidence

class ActiveConflict(BaseModel):
    conflict_id: str
    user_id: str
    conflict_type: str
    severity: float  # Current severity
    escalation_level: int  # 1=subtle, 2=direct, 3=crisis
    triggered_at: datetime
    last_escalated: datetime | None
    resolution_attempts: int
    resolved: bool
    resolution_type: str | None
```

### FR-002: Conflict Type Definitions

| Type | Triggers | Severity Range | Resolution Options |
|------|----------|----------------|-------------------|
| Jealousy | Mentions others positively | 0.3-0.8 | Reassurance, exclusivity statement |
| Attention | Gaps >24h, short responses | 0.2-0.6 | Explanation, quality time offer |
| Boundary | Sexual pressure, fast-moving | 0.4-0.9 | Apology, respect commitment |
| Trust | Inconsistencies, lies detected | 0.5-1.0 | Honest explanation, accountability |

### FR-003: Escalation Timeline

| Level | Name | Time to Reach | User Intervention |
|-------|------|---------------|-------------------|
| 1 | Subtle | Immediate | Can prevent escalation |
| 2 | Direct | 2-6 hours | Requires acknowledgment |
| 3 | Crisis | 12-24 hours | Requires significant action |

### FR-004: Breakup Threshold

- Relationship score < 20 triggers warning
- Relationship score < 10 triggers "point of no return"
- 3 consecutive unresolved crises trigger breakup
- Breakup is permanent (game over)

---

## Technical Design

### File Structure

```
nikita/
├── conflicts/
│   ├── __init__.py
│   ├── detector.py         # TriggerDetector
│   ├── generator.py        # ConflictGenerator
│   ├── escalation.py       # EscalationManager
│   ├── resolution.py       # ResolutionManager
│   ├── models.py
│   └── store.py
```

### Integration with 023

ConflictGenerator uses EmotionalState.conflict_state to determine Nikita's response style during conflicts.

### Integration with 024

MetaInstructionEngine provides conflict-specific behavioral nudges for realistic escalation and de-escalation dialogue.

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Conflict frequency | 1-2 per week per user |
| Resolution rate | 70% successfully resolved |
| Breakup rate | 5-10% of users who reach Chapter 3+ |
| User engagement during conflicts | Higher response rate than normal |

---

## Version History

### v1.0.0 - 2026-01-12
- Initial specification

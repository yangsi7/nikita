# Spec 058: Multi-Phase Boss + Warmth

**Status**: READY FOR PLAN
**Wave**: B (parallel with 056)
**Dependencies**: Spec 057 (Conflict System CORE) - COMPLETE
**Feature Flag**: `multi_phase_boss_enabled` (default: OFF)
**Risk**: HIGH
**Estimated Tasks**: 20-25

---

## Overview

Redesign boss encounters from single-turn binary (PASS/FAIL) to 2-phase multi-turn encounters (OPENING -> RESOLUTION) with a new PARTIAL outcome type. Add vulnerability exchange detection and warmth scoring bonus. Boss phase state persists in conflict_details JSONB (from Spec 057).

### Key Components
1. **2-Phase Boss** (OPENING -> RESOLUTION) — MVP, 4-phase deferred
2. **PARTIAL Outcome** — truce that doesn't advance chapter but doesn't count as fail
3. **Phase Persistence** — boss_phase stored in conflict_details JSONB
4. **10 Phase-Prompt Variants** — 2 phases x 5 chapters
5. **Vulnerability Exchange Detection** — mutual sharing + empathetic response
6. **Warmth Scoring Bonus** — +2 trust with diminishing returns

---

## User Stories

### US-1: 2-Phase Boss Encounter
**As** a player, **I want** boss encounters to span 2 turns, **so that** they feel like dramatic relationship moments rather than single-message tests.

**Acceptance Criteria**:
- AC-1.1: Boss encounter starts with OPENING phase (Nikita presents challenge)
- AC-1.2: After player's first response, boss advances to RESOLUTION phase
- AC-1.3: Player's second response triggers judgment with full context (both turns)
- AC-1.4: Phase state persisted between messages (survives server restart)
- AC-1.5: Boss can be interrupted by non-boss messages (phase preserved)
- AC-1.6: Timeout: if no response within 24h, boss auto-resolves as FAIL

### US-2: Boss Phase State
**As** the system, **I want** boss phase tracked in conflict_details JSONB, **so that** phase persists across messages and restarts.

**Acceptance Criteria**:
- AC-2.1: BossPhaseState model: phase (OPENING/RESOLUTION), chapter, started_at, turn_count, conversation_history
- AC-2.2: Phase stored in conflict_details.boss_phase JSONB
- AC-2.3: Phase read on each message to determine if boss is in progress
- AC-2.4: Phase cleared on boss completion (any outcome)
- AC-2.5: conflict_details.boss_phase = None when no boss active

### US-3: PARTIAL Outcome
**As** a player, **I want** a PARTIAL outcome (truce), **so that** not every boss encounter is all-or-nothing.

**Acceptance Criteria**:
- AC-3.1: BossResult enum extended: PASS, FAIL, PARTIAL
- AC-3.2: PARTIAL = player showed effort but didn't fully resolve the challenge
- AC-3.3: PARTIAL does NOT increment boss_attempts (no penalty)
- AC-3.4: PARTIAL does NOT advance chapter (no reward)
- AC-3.5: PARTIAL triggers cool-down: next boss encounter delayed by 24h
- AC-3.6: Judgment prompt includes PARTIAL criteria: "acknowledged but didn't resolve"

### US-4: Phase-Prompt Variants
**As** Nikita, **I want** phase-specific prompts per chapter, **so that** boss encounters feel unique to the relationship stage.

**Acceptance Criteria**:
- AC-4.1: 10 prompt variants total (2 phases x 5 chapters)
- AC-4.2: OPENING prompts present the challenge with chapter-appropriate severity
- AC-4.3: RESOLUTION prompts guide toward resolution/judgment
- AC-4.4: Prompts stored in structured dict (chapter -> phase -> prompt)
- AC-4.5: Each prompt includes: challenge_context, success_criteria, in_character_opening, phase_instruction
- AC-4.6: Ch1 (Curiosity): light test, Ch5 (Established): deep vulnerability challenge

### US-5: Multi-Turn Judgment
**As** the judgment system, **I want** to evaluate both turns together, **so that** the full conversation context informs the outcome.

**Acceptance Criteria**:
- AC-5.1: Judgment receives full conversation history (both phases)
- AC-5.2: Judgment considers: OPENING response quality + RESOLUTION response quality
- AC-5.3: Three-way judgment: PASS (genuine resolution), PARTIAL (effort shown), FAIL (dismissive/avoidant)
- AC-5.4: Judgment prompt includes PARTIAL outcome criteria
- AC-5.5: Judgment confidence threshold: >0.7 for PASS/FAIL, otherwise PARTIAL

### US-6: Vulnerability Exchange Detection
**As** the scoring system, **I want** to detect vulnerability exchanges, **so that** mutual emotional sharing is rewarded.

**Acceptance Criteria**:
- AC-6.1: Vulnerability exchange = Nikita shares something vulnerable + player responds with empathy
- AC-6.2: Detected by scoring analyzer (add to ANALYSIS_SYSTEM_PROMPT)
- AC-6.3: Counter tracked: user_metrics.vulnerability_exchanges (INT column)
- AC-6.4: Detection added to ResponseAnalysis as behavior tag: "vulnerability_exchange"

### US-7: Warmth Scoring Bonus
**As** a player, **I want** vulnerability exchanges to build trust, **so that** emotional depth is rewarded.

**Acceptance Criteria**:
- AC-7.1: First V-exchange per conversation: +2 trust bonus
- AC-7.2: Second V-exchange per conversation: +1 trust bonus
- AC-7.3: Third+ V-exchange per conversation: +0 bonus (diminishing returns)
- AC-7.4: Bonus applied in ScoreCalculator after base deltas
- AC-7.5: Counter resets per conversation (not per message)

### US-8: Feature Flag + Backward Compat
**As** the operator, **I want** multi-phase boss behind a feature flag, **so that** it can be toggled safely.

**Acceptance Criteria**:
- AC-8.1: Feature flag `multi_phase_boss_enabled` in settings (default: OFF)
- AC-8.2: Flag OFF: single-turn PASS/FAIL boss preserved exactly
- AC-8.3: Flag ON: 2-phase boss with PARTIAL outcome
- AC-8.4: All existing boss tests pass with flag OFF
- AC-8.5: New multi-phase tests run with flag ON

---

## Technical Design

### Files to Modify
- `nikita/engine/chapters/boss.py` — add BossPhaseState, phase tracking, advance_phase()
- `nikita/engine/chapters/judgment.py` — add PARTIAL to BossResult, modify for multi-turn
- `nikita/engine/chapters/prompts.py` — expand to per-phase variants (10 total)
- `nikita/platforms/telegram/message_handler.py:~794` — modify _handle_boss_response for multi-turn
- `nikita/engine/scoring/analyzer.py` — add vulnerability exchange detection to prompt
- `nikita/engine/scoring/calculator.py` — apply warmth bonus with diminishing returns
- `nikita/config/settings.py` — add `multi_phase_boss_enabled` flag

### Files to Create
- `nikita/engine/chapters/phase_manager.py` — phase state management, advancement logic

### DB Migrations
```sql
ALTER TABLE user_metrics ADD COLUMN vulnerability_exchanges INT DEFAULT 0;
```
Note: boss_phase stored in existing conflict_details JSONB (Spec 057).

### BossPhaseState Model
```python
class BossPhase(str, Enum):
    OPENING = "opening"
    RESOLUTION = "resolution"

class BossPhaseState(BaseModel):
    phase: BossPhase
    chapter: int
    started_at: datetime
    turn_count: int = 0
    conversation_history: list[dict[str, str]] = []  # [{role, content}]
```

### Phase-Prompt Structure
```python
BOSS_PHASE_PROMPTS: dict[int, dict[str, BossPrompt]] = {
    1: {  # Chapter 1: Curiosity
        "opening": BossPrompt(...),
        "resolution": BossPrompt(...),
    },
    2: { ... },  # Chapter 2: Intrigue
    3: { ... },  # Chapter 3: Investment
    4: { ... },  # Chapter 4: Intimacy
    5: { ... },  # Chapter 5: Established
}
```

### Boss Flow (Multi-Phase)
```
Message received
  -> Is boss in progress? (check conflict_details.boss_phase)
     -> YES: advance to next phase
        -> OPENING -> send RESOLUTION prompt
        -> RESOLUTION -> run judgment (PASS/PARTIAL/FAIL)
     -> NO: Is boss threshold reached?
        -> YES: Start OPENING phase, persist state
        -> NO: Normal message handling
```

---

## Critical Decisions

| # | Decision | Choice |
|---|----------|--------|
| D1 | Phase count MVP | 2-phase (OPENING/RESOLUTION), defer ESCALATION/CRISIS_PEAK |
| D2 | PARTIAL + boss_attempts | PARTIAL does NOT increment boss_attempts |
| D3 | Vulnerability detection | Behavior tag in analyzer, NOT separate LLM call |
| D4 | Warmth bonus cap | +2/+1/+0 diminishing returns per conversation |
| D5 | Boss timeout | 24h auto-FAIL if no response to OPENING |
| D6 | Phase persistence | In conflict_details.boss_phase JSONB (Spec 057 infrastructure) |

---

## Feature Flag

```python
# nikita/config/settings.py
multi_phase_boss_enabled: bool = False

# nikita/engine/chapters/__init__.py
def is_multi_phase_boss_enabled() -> bool:
    return get_settings().multi_phase_boss_enabled
```

When OFF: single-turn boss (current behavior), BossResult has PASS/FAIL only, no vulnerability tracking, no warmth bonus.

# Spec 057: Conflict System CORE — Temperature, Gottman, Four Horsemen

**Status**: DRAFT
**Wave**: A (parallel, no dependencies)
**Feature Flag**: `conflict_temperature` (OFF default)
**Estimated Tasks**: 20

---

## 1. Overview

Replace the discrete conflict state enum (NONE/PA/COLD/VULNERABLE/EXPLOSIVE) with a continuous temperature gauge (0-100) that drives conflict injection probability, severity, and persona tone. Add Gottman ratio tracking (two-ratio: 5:1 conflict, 20:1 normal) and Four Horsemen detection to the scoring analyzer. Connect repair attempts to temperature reduction and Gottman counter updates.

**Key Principle**: Temperature REPLACES the existing conflict_state enum — it does not layer on top. When the feature flag is OFF, existing behavior is fully preserved.

---

## 2. User Stories

### US-1: Temperature Gauge Model
**As** the game engine, **I want** a continuous 0-100 temperature gauge **so that** conflict severity is gradual rather than discrete jumps.

**Acceptance Criteria**:
- AC-1.1: ConflictTemperature model with float value (0.0-100.0), 4 zones: CALM(0-25), WARM(25-50), HOT(50-75), CRITICAL(75-100)
- AC-1.2: Temperature increases on negative interactions (dismissive, neglect, boundary violations)
- AC-1.3: Temperature increases on score drops >3pt in a single interaction
- AC-1.4: Temperature decreases passively at 0.5/hr (time cooldown)
- AC-1.5: Temperature stored in `conflict_details` JSONB on `nikita_emotional_states`
- AC-1.6: Existing enum values map to temperature: none=0, PA=40, cold=50, vulnerable=30, explosive=85

### US-2: Temperature-Driven Conflict Injection
**As** the conflict generator, **I want** to use temperature zones for injection probability **so that** conflicts feel organic rather than cooldown-gated.

**Acceptance Criteria**:
- AC-2.1: CALM zone (0-25): 0% injection probability (no conflicts generated)
- AC-2.2: WARM zone (25-50): 10-25% probability, severity capped at 0.4
- AC-2.3: HOT zone (50-75): 25-60% probability, severity capped at 0.7
- AC-2.4: CRITICAL zone (75-100): 60-90% probability, full severity range
- AC-2.5: Replaces flat 4h cooldown in `ConflictGenerator.CONFLICT_COOLDOWN_HOURS`
- AC-2.6: Feature flag OFF preserves existing 4h cooldown behavior

### US-3: Gottman Ratio Tracking
**As** the scoring service, **I want** to track positive/negative interaction ratios **so that** relationship health is measured by the Gottman standard.

**Acceptance Criteria**:
- AC-3.1: Positive/negative counters stored in `conflict_details` JSONB
- AC-3.2: Two-ratio system: target 5:1 during active conflict periods, 20:1 during normal
- AC-3.3: Rolling 7-day window for ratio calculation
- AC-3.4: Per-session ratio tracked alongside rolling window
- AC-3.5: Ratio below target increases temperature by 2-5 points per interaction
- AC-3.6: Ratio above target decreases temperature by 1-2 points per interaction
- AC-3.7: Counters initialized from existing `score_history` for existing users

### US-4: Four Horsemen Detection
**As** the scoring analyzer, **I want** to detect Gottman's Four Horsemen behaviors **so that** toxic patterns are identified and penalized.

**Acceptance Criteria**:
- AC-4.1: Detect criticism (attacking character, not complaint about behavior)
- AC-4.2: Detect contempt (superiority, mockery, eye-rolling language)
- AC-4.3: Detect defensiveness (counter-attacking, whining, playing victim)
- AC-4.4: Detect stonewalling (withdrawal, one-word responses, disengagement)
- AC-4.5: Each Horseman adds to `behaviors_identified` in ResponseAnalysis
- AC-4.6: Horseman detection increases temperature by 3-8 points (severity-dependent)
- AC-4.7: Added to ANALYSIS_SYSTEM_PROMPT for LLM detection

### US-5: Repair Attempt Integration
**As** the resolution manager, **I want** repair attempts to reduce temperature **so that** positive conflict resolution is mechanically rewarded.

**Acceptance Criteria**:
- AC-5.1: Successful repair (EXCELLENT/GOOD quality) reduces temperature by 10-25 points
- AC-5.2: Partial repair (ADEQUATE quality) reduces temperature by 3-8 points
- AC-5.3: Failed repair (POOR/HARMFUL quality) increases temperature by 2-5 points
- AC-5.4: Repair attempts update Gottman positive counter
- AC-5.5: Repair history tracked in `conflict_details.repair_attempts` array
- AC-5.6: Resolution connects to both temperature reduction AND Gottman update

### US-6: Breakup Threshold Update
**As** the breakup manager, **I want** to consider temperature alongside score **so that** sustained high temperature triggers warnings.

**Acceptance Criteria**:
- AC-6.1: Temperature in CRITICAL zone for >24h triggers breakup warning
- AC-6.2: Temperature >90 for >48h triggers breakup (independent of score)
- AC-6.3: Existing score-based thresholds (warning=20, breakup=10) preserved
- AC-6.4: `users.last_conflict_at` TIMESTAMPTZ column tracks last conflict timestamp

### US-7: Pipeline Integration
**As** the pipeline conflict stage, **I want** to consume the temperature model **so that** conflict detection uses continuous values.

**Acceptance Criteria**:
- AC-7.1: ConflictStage reads temperature from `conflict_details` JSONB
- AC-7.2: Temperature zone determines `ctx.active_conflict` boolean (HOT/CRITICAL = true)
- AC-7.3: Temperature value available for prompt builder injection
- AC-7.4: Backward-compatible: missing `conflict_details` defaults to temperature=0

---

## 3. Technical Requirements

### 3.1 Data Model

**New JSONB schema** (`nikita_emotional_states.conflict_details`):
```json
{
  "temperature": 42.5,
  "zone": "warm",
  "positive_count": 15,
  "negative_count": 4,
  "gottman_ratio": 3.75,
  "gottman_target": 20.0,
  "horsemen_detected": ["criticism"],
  "repair_attempts": [
    {"at": "2026-02-18T10:00:00Z", "quality": "good", "temp_delta": -15.0}
  ],
  "last_temp_update": "2026-02-18T14:30:00Z",
  "session_positive": 3,
  "session_negative": 1
}
```

**New column**: `users.last_conflict_at TIMESTAMPTZ`

### 3.2 Temperature Zones

| Zone | Range | Injection Prob | Max Severity | Persona Modifier |
|------|-------|---------------|-------------|------------------|
| CALM | 0-25 | 0% | N/A | Normal |
| WARM | 25-50 | 10-25% | 0.4 | Slightly tense |
| HOT | 50-75 | 25-60% | 0.7 | Visibly upset |
| CRITICAL | 75-100 | 60-90% | 1.0 | Near breakup |

### 3.3 Temperature Delta Rules

| Event | Delta | Notes |
|-------|-------|-------|
| Negative interaction (score delta < 0) | +abs(delta) * 1.5 | Proportional to harm |
| Horseman detected | +3 to +8 | Per horseman type |
| Score drop > 3pt | +5 | Threshold trigger |
| Neglect (>24h gap) | +2/hr past 24h | Capped at +20 |
| Boundary violation | +8 | Severe trigger |
| Positive interaction (delta > 0) | -abs(delta) * 0.5 | Slower recovery |
| Repair (EXCELLENT) | -25 | Fast recovery |
| Repair (GOOD) | -15 | Moderate recovery |
| Repair (ADEQUATE) | -5 | Minimal recovery |
| Time cooldown | -0.5/hr | Passive decay |
| Gottman ratio above target | -1 to -2 | Per interaction |
| Gottman ratio below target | +2 to +5 | Per interaction |

### 3.4 Files to Modify

| File | Changes |
|------|---------|
| `nikita/conflicts/models.py` | Add ConflictTemperature, TemperatureZone, GottmanTracker, HorsemanType models |
| `nikita/conflicts/detector.py` | Update detect() to update temperature accumulator |
| `nikita/conflicts/generator.py` | Replace 4h cooldown with temperature zone checks |
| `nikita/conflicts/escalation.py` | Extend acknowledge() to reduce temperature |
| `nikita/conflicts/resolution.py` | Connect resolve() to temperature reduction + Gottman update |
| `nikita/conflicts/breakup.py` | Add temperature-based breakup thresholds |
| `nikita/engine/scoring/analyzer.py` | Add Four Horsemen to ANALYSIS_SYSTEM_PROMPT |
| `nikita/engine/scoring/service.py` | Add Gottman counter increment post-scoring |
| `nikita/engine/scoring/models.py` | Add horsemen tags to behaviors_identified typing |
| `nikita/pipeline/stages/conflict.py` | Consume temperature model |
| `nikita/emotional_state/models.py` | Deprecation note on conflict_state enum |

### 3.5 DB Migrations

```sql
-- Migration 1: Add conflict_details JSONB
ALTER TABLE nikita_emotional_states
ADD COLUMN IF NOT EXISTS conflict_details JSONB DEFAULT '{}';

-- Migration 2: Add last_conflict_at
ALTER TABLE users
ADD COLUMN IF NOT EXISTS last_conflict_at TIMESTAMPTZ;

-- Migration 3: Index for temperature queries
CREATE INDEX IF NOT EXISTS idx_emotional_states_conflict_details
ON nikita_emotional_states USING GIN (conflict_details);
```

### 3.6 Feature Flag Strategy

- Flag name: `conflict_temperature`
- Default: OFF
- Storage: `nikita/config/settings.py` as `conflict_temperature_enabled: bool = False`
- Guard pattern: every temperature read/write checks flag; when OFF, falls through to existing discrete enum behavior
- Existing `ConflictDetector`, `ConflictGenerator`, `EscalationManager` behavior preserved when OFF

### 3.7 Existing User Migration

When flag is turned ON for the first time per user:
1. Read current `conflict_state` enum value
2. Map to temperature: none=0, PA=40, cold=50, vulnerable=30, explosive=85
3. Initialize Gottman counters from `score_history`: count positive (delta>0) and negative (delta<0) entries from last 7 days
4. Write initial `conflict_details` JSONB
5. Set `users.last_conflict_at` from last non-NONE conflict_state timestamp

---

## 4. Out of Scope

- Multi-phase boss encounters (Spec 058)
- Vulnerability exchange tracking (Spec 058)
- Portal visualization of temperature (Spec 059)
- Prompt caching integration (Spec 060)
- Voice pipeline temperature injection (future spec)

---

## 5. Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Temperature zones miscalibrated | 70% | MEDIUM | Tunable constants, feature flag, playtest cycle |
| Gottman ratio too punitive short sessions | 50% | MEDIUM | Two-ratio system, rolling 7-day window, diminishing returns |
| Four Horsemen LLM accuracy | 40% | MEDIUM | Conservative detection, confidence threshold |
| JSONB query performance | 20% | LOW | GIN index, single-row reads |
| Backward compatibility | 10% | HIGH | Feature flag gates all new behavior |

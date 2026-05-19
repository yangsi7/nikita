# Spec 055: Life Simulation Enhanced

**Status**: DRAFT
**Author**: SDD Pipeline Agent
**Date**: 2026-02-18
**Depends on**: None (Wave A parallel)
**Feature flag**: `life_sim_enhanced` (OFF default)

---

## 1. Overview

Enhance the life simulation engine with three capabilities:
1. **Weekly routine system** — structured day-of-week awareness for event generation
2. **NPC consolidation** — collapse 3 overlapping character systems into 1 canonical store (`user_social_circles`)
3. **Bidirectional mood-event flow** — mood state feeds INTO event generation (currently one-way: events -> mood)

Additionally: add `routine_config` and `meta_instructions` JSONB columns to `users` (schema only for meta_instructions; generation deferred).

### Scope OUT
- Monthly meta-instruction generation job (deferred per Gate 4.5 D6)
- Pre-seeding 8 NPCs per user on registration (lazy init per D10)
- Daily batch job for life events (existing pipeline stage S3 sufficient)
- Portal page (Spec 053)

---

## 2. User Stories

### US-1: Routine-Aware Event Generation
**As** the life simulation engine, **I want** to generate events that respect Nikita's weekly routine **so that** Monday work events differ from Saturday leisure events.

**Acceptance Criteria**:
- AC-1.1: A `routine.yaml` default config defines activities, availability, and energy patterns per day of week
- AC-1.2: `WeeklyRoutine` and `DayRoutine` Pydantic models validate the routine config
- AC-1.3: `EventGenerator.generate_events_for_day()` accepts an optional `routine` param and injects day context into the LLM prompt
- AC-1.4: Weekend events skew toward personal/social domains; weekday events include work domain
- AC-1.5: Users have a `routine_config` JSONB column on `users` table (default `{}` = use system default)

### US-2: Bidirectional Mood-Event Flow
**As** the life simulation engine, **I want** Nikita's current mood to influence which events are generated **so that** a stressed Nikita gets stress-related events and a happy Nikita gets positive events.

**Acceptance Criteria**:
- AC-2.1: `EventGenerator.generate_events_for_day()` accepts an optional `mood_state` param (MoodState dataclass)
- AC-2.2: When mood valence < 0.4, event generation prompt biases toward stress/setback events
- AC-2.3: When mood valence > 0.6, event generation prompt biases toward positive/social events
- AC-2.4: `LifeSimulator.generate_next_day_events()` computes mood FIRST, then passes it to EventGenerator
- AC-2.5: No infinite feedback loop — mood from PREVIOUS day feeds into NEXT day's events

### US-3: NPC Consolidation
**As** the system, **I want** a single canonical NPC store **so that** character names are consistent across life events, arcs, social circle, and entity systems.

**Acceptance Criteria**:
- AC-3.1: `user_social_circles` table gains `last_event TIMESTAMPTZ` and `sentiment TEXT` columns
- AC-3.2: Explicit NPC mapping table resolves all name collisions (see Section 5)
- AC-3.3: `EntityManager` references `user_social_circles` for friend-type entities instead of `nikita_entities`
- AC-3.4: `NarrativeArcSystem` character lookup uses `user_social_circles` for NPC metadata
- AC-3.5: Life events that reference named NPCs update `user_social_circles.last_event` and `sentiment`
- AC-3.6: Lazy NPC initialization — only create `user_social_circles` rows when an NPC first appears in conversation or life events
- AC-3.7: `nikita_entities` table remains for non-NPC entities (places, projects, colleagues not in social circle)

### US-4: Meta-Instructions Schema
**As** a future spec, **I want** the `meta_instructions` JSONB column to exist on `users` **so that** Spec 050+ can populate it without schema changes.

**Acceptance Criteria**:
- AC-4.1: `users.meta_instructions JSONB DEFAULT '{}'` column added
- AC-4.2: Column is nullable with empty object default — zero impact on existing queries
- AC-4.3: No generation logic implemented (deferred)

---

## 3. Technical Requirements

### 3.1 New Models

```python
# life_simulation/models.py additions

class DayRoutine(BaseModel):
    """Routine for a single day of the week."""
    day_of_week: str  # monday, tuesday, ..., sunday
    wake_time: str = "08:00"  # HH:MM Berlin time
    activities: list[str] = []  # e.g. ["work", "gym", "dinner with Lena"]
    work_schedule: str = "office"  # office | remote | off
    energy_pattern: str = "normal"  # high | normal | low
    social_availability: str = "moderate"  # high | moderate | low

class WeeklyRoutine(BaseModel):
    """Nikita's weekly routine."""
    days: dict[str, DayRoutine]  # keyed by day name
    timezone: str = "Europe/Berlin"

    @classmethod
    def from_yaml(cls, path: Path) -> "WeeklyRoutine": ...
    @classmethod
    def default(cls) -> "WeeklyRoutine": ...
```

### 3.2 Default Routine (routine.yaml)

```yaml
timezone: "Europe/Berlin"
days:
  monday:
    wake_time: "07:30"
    work_schedule: office
    activities: [work, gym_evening]
    energy_pattern: normal
    social_availability: low
  tuesday:
    wake_time: "07:30"
    work_schedule: office
    activities: [work, personal_project]
    energy_pattern: normal
    social_availability: moderate
  wednesday:
    wake_time: "08:00"
    work_schedule: remote
    activities: [work, therapy_biweekly]
    energy_pattern: normal
    social_availability: moderate
  thursday:
    wake_time: "07:30"
    work_schedule: office
    activities: [work, social_evening]
    energy_pattern: high
    social_availability: high
  friday:
    wake_time: "08:00"
    work_schedule: office
    activities: [work, casual_plans]
    energy_pattern: high
    social_availability: high
  saturday:
    wake_time: "09:30"
    work_schedule: "off"
    activities: [errands, hobby, social]
    energy_pattern: high
    social_availability: high
  sunday:
    wake_time: "10:00"
    work_schedule: "off"
    activities: [self_care, mom_call, meal_prep]
    energy_pattern: low
    social_availability: moderate
```

### 3.3 Event Generator Changes

`EventGenerator.generate_events_for_day()` signature changes:

```python
async def generate_events_for_day(
    self,
    user_id: UUID,
    event_date: date,
    active_arcs: list[NarrativeArc] | None = None,
    recent_events: list[LifeEvent] | None = None,
    # NEW params (all optional with defaults)
    routine: DayRoutine | None = None,
    mood_state: MoodState | None = None,
) -> list[LifeEvent]:
```

Prompt injection adds two new sections:
- **Routine context**: day schedule, energy, availability
- **Mood context**: current valence/arousal bias for event tone

### 3.4 Simulator Changes

`LifeSimulator.generate_next_day_events()` pipeline becomes:

1. Check/seed entities (unchanged)
2. **NEW**: Compute mood from recent events (existing `get_current_mood()`)
3. **NEW**: Load routine for target day
4. Get active narrative arcs (unchanged)
5. Get recent events for continuity (unchanged)
6. Generate events with mood + routine context
7. **NEW**: Update NPC states from generated events
8. Persist events (unchanged)
9. Progress/create narrative arcs (unchanged)

### 3.5 NPC State Updates

When a life event references a named character that exists in `user_social_circles`:

```python
async def update_npc_from_event(
    self, user_id: UUID, event: LifeEvent
) -> None:
    """Update NPC state when referenced in life event."""
    for entity_name in event.entities:
        npc = await self._get_npc_by_name(user_id, entity_name)
        if npc:
            npc.last_event = event.created_at
            npc.sentiment = self._compute_sentiment(event)
            await self._save_npc_state(npc)
```

Sentiment values: `positive`, `negative`, `neutral`, `mixed`.

---

## 4. Data Model Changes

### 4.1 DB Migrations

**Migration 1**: Users table additions
```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS routine_config JSONB DEFAULT '{}';
ALTER TABLE users ADD COLUMN IF NOT EXISTS meta_instructions JSONB DEFAULT '{}';
```

**Migration 2**: Social circle state tracking
```sql
ALTER TABLE user_social_circles ADD COLUMN IF NOT EXISTS last_event TIMESTAMPTZ;
ALTER TABLE user_social_circles ADD COLUMN IF NOT EXISTS sentiment TEXT DEFAULT 'neutral';
```

Both migrations are additive with safe defaults — zero impact on existing queries.

---

## 5. NPC Character Mapping

### 5.1 Current State (3 Systems)

| System | Characters | Storage |
|--------|-----------|---------|
| **entities.yaml** (Spec 022) | Lisa, Max, Sarah, David, Ana, Jamie, Mira + places/projects | `nikita_entities` table |
| **arcs.py** (Spec 035) | Marco, Lena, Viktor, Yuki, Dr. Miriam, Alexei, Katya | Hardcoded `ARC_TEMPLATES` |
| **social_generator.py** (Spec 035) | Lena, Viktor, Yuki, Dr. Miriam, Alexei, Katya, Marco, Ava | `user_social_circles` table |

### 5.2 Canonical Mapping

| Character | Source Systems | Canonical Store | Decision |
|-----------|---------------|-----------------|----------|
| **Lena** | arcs + social_gen + entities(as Ana) | `user_social_circles` | KEEP — best friend, primary NPC |
| **Viktor** | arcs + social_gen | `user_social_circles` | KEEP — complicated friend |
| **Yuki** | arcs + social_gen | `user_social_circles` | KEEP — party friend |
| **Dr. Miriam** | arcs + social_gen | `user_social_circles` | KEEP — therapist (low-frequency) |
| **Alexei** | arcs + social_gen | `user_social_circles` | KEEP — father (backstory) |
| **Katya** | arcs + social_gen | `user_social_circles` | KEEP — mother (backstory) |
| **Marco** | social_gen (tech hub) | `user_social_circles` | KEEP — industry friend (conditional) |
| **Lisa** | entities.yaml | `nikita_entities` | KEEP — colleague (not social circle) |
| **Max** (colleague) | entities.yaml | `nikita_entities` | KEEP — colleague; RENAME to "Max K." to avoid collision with ex-Max |
| **Sarah** | entities.yaml | `nikita_entities` | KEEP — colleague |
| **David** | entities.yaml | `nikita_entities` | KEEP — manager |
| **Ana** | entities.yaml | DEPRECATE | MERGE into Lena (duplicate best friend role) |
| **Jamie** | entities.yaml | `nikita_entities` | KEEP — gym buddy (entity, not social circle) |
| **Mira** | entities.yaml | `nikita_entities` | KEEP — neighbor (entity) |

### 5.3 Rules

1. **Social circle characters** (Lena, Viktor, Yuki, etc.) = `user_social_circles` with dynamic state
2. **Workplace/casual** entities (Lisa, Sarah, David, Jamie, Mira) = `nikita_entities` (static, no sentiment tracking)
3. **Name collisions**: Max (colleague) renamed to "Max K." in entities.yaml to disambiguate from ex-boyfriend Max
4. **Ana deprecated**: Merged into Lena — cannot have two "best friends"
5. **Lazy init**: NPCs only added to `user_social_circles` when first mentioned

---

## 6. API Changes

No external API changes. All modifications are internal to the life simulation pipeline stage.

The `LifeSimStage` (pipeline stage) already calls `LifeSimulator` — enhanced generation is transparent to the pipeline.

---

## 7. Feature Flag Strategy

```python
# settings.py addition
life_sim_enhanced: bool = Field(
    default=False,
    description="Enable enhanced life sim (routine, bidirectional mood, NPC consolidation). Rollback: LIFE_SIM_ENHANCED=false",
)
```

**Flag OFF behavior**: Current event generation (no routine, one-way mood, no NPC state updates). All new params have defaults that preserve existing behavior.

**Flag ON behavior**: Routine-aware generation, mood feeds into events, NPC states updated.

**Rollout plan**: OFF in dev/staging until tests pass. ON for canary. ON for production after 1 week.

---

## 8. Migration Plan (Existing Users)

1. **routine_config**: Default `{}` means "use system default from routine.yaml" — no data migration needed
2. **meta_instructions**: Default `{}` — no data migration needed
3. **user_social_circles**: Existing rows from Spec 035 onboarding gain `last_event=NULL, sentiment='neutral'`
4. **nikita_entities**: Unchanged — keep all existing seed entities
5. **Ana deprecation**: Soft — if user has Ana in entities, she remains but is not referenced in new event generation prompts
6. **Max K. rename**: Applied in entities.yaml only — existing entity rows unchanged until next seed

---

## 9. Integration Points

| System | Integration | Direction |
|--------|------------|-----------|
| **Pipeline (LifeSimStage)** | Calls enhanced `LifeSimulator` | Consumer |
| **MoodCalculator** | Provides mood for bidirectional flow | Provider |
| **NarrativeArcSystem** | Arc templates reference social circle NPCs | Consumer |
| **EventGenerator** | Receives routine + mood context | Consumer |
| **user_social_circles** | NPC state updates from life events | Read/Write |
| **Spec 050 (Psyche Agent)** | Reads life events + NPC states for analysis | Future consumer |

---

## 10. Testing Strategy

- **Unit tests**: Models (WeeklyRoutine, DayRoutine), routine loading, NPC mapping logic
- **Integration tests**: EventGenerator with routine + mood params, NPC state updates
- **Regression tests**: All existing life_simulation tests must pass unchanged when flag is OFF
- **Mock strategy**: LLM calls mocked via `llm_client` param; DB calls mocked via in-memory store

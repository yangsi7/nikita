# Spec 022: Life Simulation Engine

**Version**: 1.0.0
**Created**: 2026-01-12
**Status**: DRAFT
**Dependencies**: 021 (Hierarchical Prompt Composition)
**Dependents**: 023, 025, 027

---

## Overview

### Problem Statement

Nikita currently has a static backstory with no evolving narrative. This creates several issues:
1. **No authentic life events**: She can't reference what happened "today" because nothing happened
2. **Mood feels random**: Her emotional state isn't grounded in simulated experiences
3. **Conversations are one-sided**: 100% focus on user's life, no reciprocity
4. **Immersion breaks**: Users realize she doesn't "exist" between conversations

### Solution

Implement a **Life Simulation Engine** that generates daily events for Nikita (work, social, personal), derives mood from these events, and makes events available for natural conversation references.

### Key Principles

> "She must feel like she exists even when you're not texting her."
> "Balance: 30-40% Nikita talking, 30-40% asking, 30% listening."

---

## User Stories

### US-1: Daily Event Generation
**As** the system,
**I want** to generate daily events for Nikita's life,
**So that** she has authentic experiences to reference in conversations.

**Priority**: P1 (Critical)

**Acceptance Criteria**:
- AC-1.1: Events generated for each day the user might interact
- AC-1.2: Events cover work, social, and personal domains
- AC-1.3: Events are timestamped and retrievable by date
- AC-1.4: Events persist for at least 7 days for callbacks

### US-2: Work Domain Events
**As** Nikita,
**I want** work-related events (projects, meetings, colleagues),
**So that** I can share authentic professional experiences.

**Priority**: P1 (Critical)

**Acceptance Criteria**:
- AC-2.1: Work events include: projects, deadlines, meetings, colleague interactions
- AC-2.2: Events have emotional valence (positive, negative, neutral)
- AC-2.3: Events reference recurring entities (e.g., "Sarah from marketing")
- AC-2.4: Events build on previous work events for continuity

### US-3: Social Domain Events
**As** Nikita,
**I want** social events (friends, plans, outings),
**So that** I can share a social life that feels real.

**Priority**: P2 (Important)

**Acceptance Criteria**:
- AC-3.1: Social events include: friend interactions, plans, outings
- AC-3.2: Recurring friends referenced by name (2-3 close friends)
- AC-3.3: Events affect availability (e.g., "was at dinner with Ana")
- AC-3.4: Social events can conflict with user contact (she was busy)

### US-4: Personal Domain Events
**As** Nikita,
**I want** personal events (gym, errands, hobbies),
**So that** I can reference daily life activities naturally.

**Priority**: P2 (Important)

**Acceptance Criteria**:
- AC-4.1: Personal events include: gym, errands, hobbies, self-care
- AC-4.2: Events affect energy level (gym → tired, coffee → energetic)
- AC-4.3: Events reference time of day appropriately
- AC-4.4: Personal events explain availability gaps

### US-5: Mood Derivation
**As** the emotional state engine (Spec 023),
**I want** mood computed from daily events,
**So that** Nikita's emotional state is grounded in her experiences.

**Priority**: P1 (Critical)

**Acceptance Criteria**:
- AC-5.1: Each event contributes to mood dimensions (arousal, valence, dominance, intimacy)
- AC-5.2: Negative work events lower valence
- AC-5.3: Social success raises arousal and valence
- AC-5.4: Cumulative mood computed from all day's events

### US-6: Event Referencing in Conversations
**As** the prompt composer,
**I want** events injected into Nikita's context,
**So that** she can naturally reference her day.

**Priority**: P1 (Critical)

**Acceptance Criteria**:
- AC-6.1: Today's events included in context package (Layer 3)
- AC-6.2: Events formatted as natural conversation hooks
- AC-6.3: 40%+ of conversations should include life event references
- AC-6.4: Events prioritized by emotional intensity for selection

### US-7: Narrative Continuity
**As** the system,
**I want** events to build on each other over time,
**So that** Nikita's life feels like an evolving story.

**Priority**: P2 (Important)

**Acceptance Criteria**:
- AC-7.1: Project arcs span multiple days (start → progress → complete/fail)
- AC-7.2: Colleague relationships evolve (new → conflict → resolution)
- AC-7.3: Social dynamics change (friend drama, new friend, plans)
- AC-7.4: No dramatic "growth arcs" within 4-week timeframe

---

## Functional Requirements

### FR-001: Event Domains and Types

| Domain | Event Types | Example |
|--------|-------------|---------|
| **Work** | project_update, meeting, colleague_interaction, deadline, win, setback | "Had a tough meeting with my manager about the redesign" |
| **Social** | friend_hangout, friend_drama, plans_made, plans_cancelled, new_person | "Grabbed coffee with Ana, she's going through a breakup" |
| **Personal** | gym, errand, hobby_activity, self_care, health, travel | "Finally hit the gym after skipping all week" |

### FR-002: Event Schema

```python
class LifeEvent(BaseModel):
    event_id: str
    user_id: str  # Nikita's events are per-user for personalization
    date: date
    time_of_day: str  # morning, afternoon, evening, night
    domain: str  # work, social, personal
    event_type: str
    description: str  # Natural language description
    entities: list[str]  # People, places, projects mentioned
    emotional_impact: dict  # arousal_delta, valence_delta, etc.
    importance: float  # 0.0-1.0, affects selection priority
    narrative_arc_id: str | None  # Links related events
    created_at: datetime
```

### FR-003: Event Generation Pipeline

```
Post-Processing (after conversation)
    ↓
Check if tomorrow's events exist
    ↓ (if not)
Generate tomorrow's events:
  1. Load active narrative arcs
  2. Select 3-5 events across domains
  3. Generate descriptions via LLM
  4. Compute emotional impacts
  5. Store events
    ↓
Update context package with today's events
```

### FR-004: Narrative Arc Schema

```python
class NarrativeArc(BaseModel):
    arc_id: str
    user_id: str
    domain: str
    arc_type: str  # project, colleague_conflict, friend_drama, etc.
    status: str  # active, resolved, abandoned
    start_date: date
    entities: list[str]
    current_state: str  # Description of current arc state
    possible_outcomes: list[str]
    created_at: datetime
    resolved_at: datetime | None
```

### FR-005: Entity Continuity

The system SHALL maintain recurring entities for authenticity:

| Entity Type | Examples | Persistence |
|-------------|----------|-------------|
| Colleagues | Sarah (marketing), Mike (engineering), boss Lisa | Permanent |
| Friends | Ana (best friend), Jake (gym buddy) | Permanent |
| Projects | "The redesign", "the pitch deck" | Arc-based |
| Places | "That coffee shop", "the gym near work" | Permanent |

### FR-006: Mood Contribution Formula

Each event contributes to mood dimensions:

```python
mood_delta = {
    "arousal": event.arousal_delta,  # -0.3 to +0.3
    "valence": event.valence_delta,  # -0.3 to +0.3
    "dominance": event.dominance_delta,  # -0.2 to +0.2
    "intimacy": event.intimacy_delta,  # -0.1 to +0.1 (rarely affected)
}

# Examples:
# Bad meeting: arousal=+0.2, valence=-0.3, dominance=-0.2
# Coffee with friend: arousal=+0.1, valence=+0.2, dominance=0
# Hit the gym: arousal=+0.2, valence=+0.1, dominance=+0.1
```

---

## Non-Functional Requirements

### NFR-001: Event Generation Time
- Event generation for next day: < 30 seconds
- LLM call for descriptions: 1-2 calls max per day

### NFR-002: Storage
- Events stored in Supabase
- 7-day rolling retention (callbacks to recent events)
- Narrative arcs retained for arc duration

### NFR-003: Diversity
- No duplicate event types on same day
- Domain balance: at least 1 event per domain per 2 days
- Variety in emotional valence (not all negative or all positive)

### NFR-004: Authenticity
- Events must feel realistic for Nikita's persona
- No dramatic "soap opera" events (within 4-week timeframe)
- Events consistent with Nikita's established interests/job

---

## Technical Design

### Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    LIFE SIMULATION ENGINE                        │
├─────────────────────────────────────────────────────────────────┤
│  LifeSimulator                                                   │
│    ├── EventGenerator (LLM-based event creation)                │
│    ├── NarrativeArcManager (arc lifecycle)                      │
│    ├── EntityManager (recurring people, places)                 │
│    ├── MoodCalculator (event → mood delta)                      │
│    └── EventStore (Supabase persistence)                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Called by PostProcessingPipeline (021)
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CONTEXT PACKAGE (021)                         │
│    life_events_today: list[str]                                 │
│    nikita_mood: derived from events                             │
└─────────────────────────────────────────────────────────────────┘
```

### File Structure

```
nikita/
├── life_simulation/
│   ├── __init__.py
│   ├── simulator.py         # LifeSimulator orchestrator
│   ├── event_generator.py   # LLM-based event generation
│   ├── narrative_manager.py # Arc lifecycle management
│   ├── entity_manager.py    # Recurring entities
│   ├── mood_calculator.py   # Event → mood contribution
│   ├── models.py            # LifeEvent, NarrativeArc
│   └── store.py             # EventStore (Supabase)
```

### Database Schema

```sql
CREATE TABLE nikita_life_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    event_date DATE NOT NULL,
    time_of_day VARCHAR(20) NOT NULL,
    domain VARCHAR(20) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    entities JSONB DEFAULT '[]',
    emotional_impact JSONB NOT NULL,
    importance FLOAT NOT NULL DEFAULT 0.5,
    narrative_arc_id UUID REFERENCES nikita_narrative_arcs(arc_id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_life_events_user_date ON nikita_life_events(user_id, event_date);

CREATE TABLE nikita_narrative_arcs (
    arc_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    domain VARCHAR(20) NOT NULL,
    arc_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    start_date DATE NOT NULL,
    entities JSONB DEFAULT '[]',
    current_state TEXT,
    possible_outcomes JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

CREATE TABLE nikita_entities (
    entity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    entity_type VARCHAR(20) NOT NULL,  -- colleague, friend, place, project
    name VARCHAR(100) NOT NULL,
    description TEXT,
    relationship TEXT,  -- How Nikita relates to this entity
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Integration with Spec 021

### Hook Point: PostProcessingPipeline

```python
# In nikita/post_processing/pipeline.py

class PostProcessingPipeline:
    async def process(self, user_id: str, conversation_id: str):
        # ... existing steps ...

        # Step 3: Simulate tomorrow's life events (Spec 022)
        life_events = await self.life_simulator.generate_next_day_events(user_id)

        # Store events in context package
        package.life_events_today = [e.description for e in life_events]
        package.nikita_mood = self.mood_calculator.compute_from_events(life_events)
```

### Output to Context Package

```python
class ContextPackage(BaseModel):
    # ... existing fields ...

    # From Spec 022
    life_events_today: list[str]  # Natural language event descriptions
    nikita_mood: dict  # Derived mood from events
```

---

## Testing Strategy

### Unit Tests
- EventGenerator: Valid events for each domain
- MoodCalculator: Correct delta computation
- NarrativeArcManager: Arc lifecycle transitions

### Integration Tests
- Full event generation pipeline
- Event storage and retrieval
- Mood computation from multiple events

### Quality Tests
- Events are diverse (no duplicates)
- Events are authentic (match Nikita's persona)
- Narrative arcs progress logically

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Life mention rate | 40%+ conversations | Content analysis |
| Event diversity | No domain empty > 2 days | Event logs |
| Arc resolution rate | 80%+ arcs resolved in 7 days | Arc status |
| Authenticity score | >4/5 user rating | Survey (future) |

---

## Open Questions

1. **Event generation frequency**: Generate each day, or batch weekly?
   - **Recommendation**: Daily generation in post-processing, with next-day lookahead.

2. **Personalization depth**: Should events adapt to user's preferences?
   - **Recommendation**: Base events on Nikita's persona; user preference affects how she shares, not what happens.

3. **Dramatic events**: How rare should big events (promotion, friend fight) be?
   - **Recommendation**: Max 1 dramatic event per week, most events are mundane.

---

## Version History

### v1.0.0 - 2026-01-12
- Initial specification
- 7 user stories, 6 FRs, 4 NFRs
- Database schema defined

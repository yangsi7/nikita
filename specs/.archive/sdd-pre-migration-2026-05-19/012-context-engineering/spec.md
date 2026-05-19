> **SUPERSEDED**: This spec has been functionally replaced by [Spec 029](../029-context-comprehensive/spec.md), [Spec 039](../039-unified-context-engine/spec.md), and ultimately [Spec 042](../042-unified-pipeline/spec.md) (Unified Pipeline).
> The context engineering system described here was incrementally rebuilt across those specs. See Spec 042 for the authoritative architecture.

# 012 - Context Engineering System

**Status**: Superseded
**Priority**: P0
**Dependencies**: 009-database-infrastructure, 003-scoring-engine, 014-engagement-model
**Blocks**: 001-nikita-text-agent, 002-telegram-integration, 007-voice-agent

---

## 1. Overview

### 1.1 Purpose

The Context Engineering System dynamically generates Nikita's system prompt for each conversation. It replaces the static `build_system_prompt()` function with a sophisticated 6-stage pipeline that incorporates game state, temporal context, memory, mood computation, and engagement calibration.

### 1.2 Goals

1. **Dynamic Persona**: Nikita's behavior adapts to chapter, mood, relationship state, and engagement patterns
2. **Token Efficiency**: Stay within ~3700 token budget for system prompt
3. **Testability**: Meta-prompt can be tested offline without full system
4. **Coherence**: All context elements work together without contradictions
5. **Extensibility**: Easy to add new context sources or modify behavior

### 1.3 Non-Goals

- Real-time streaming context updates (batch per message)
- Multi-turn context within single API call (stateless per request)
- Voice-specific context generation (handled by 007-voice-agent)

---

## 2. Architecture

### 2.1 Pipeline Overview

```
USER MESSAGE RECEIVED
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CONTEXT GENERATOR                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  Stage 1    │  │  Stage 2    │  │  Stage 3    │              │
│  │   State     │─▶│  Temporal   │─▶│   Memory    │              │
│  │ Collection  │  │  Context    │  │ Summarize   │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│         │                │                │                      │
│         ▼                ▼                ▼                      │
│  PlayerProfile    TemporalCtx      MemoryContext                │
│         │                │                │                      │
│         └────────────────┼────────────────┘                      │
│                          ▼                                       │
│                 ┌─────────────┐                                  │
│                 │  Stage 4    │                                  │
│                 │    Mood     │                                  │
│                 │ Computation │                                  │
│                 └──────┬──────┘                                  │
│                        │ NikitaState                             │
│                        ▼                                         │
│                 ┌─────────────┐                                  │
│                 │  Stage 5    │                                  │
│                 │   Prompt    │                                  │
│                 │  Assembly   │                                  │
│                 └──────┬──────┘                                  │
│                        │ ~3700 tokens                            │
│                        ▼                                         │
│                 ┌─────────────┐                                  │
│                 │  Stage 6    │                                  │
│                 │ Validation  │                                  │
│                 └──────┬──────┘                                  │
└────────────────────────┼────────────────────────────────────────┘
                         │
                         ▼
                  SYSTEM PROMPT
```

### 2.2 Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     ContextGenerator                             │
├─────────────────────────────────────────────────────────────────┤
│  + generate(user_id, message) -> SystemPrompt                   │
│  - _collect_state(user_id) -> PlayerProfile                     │
│  - _build_temporal(profile) -> TemporalContext                  │
│  - _summarize_memory(user_id, message) -> MemoryContext         │
│  - _compute_mood(profile, temporal, memory) -> NikitaState      │
│  - _assemble_prompt(all_contexts) -> str                        │
│  - _validate(prompt) -> ValidationResult                        │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│ UserRepo    │      │ NikitaMemory│      │ ConfigLoader│
│ MetricsRepo │      │ (Graphiti)  │      │ (YAML)      │
│ ViceRepo    │      └─────────────┘      └─────────────┘
└─────────────┘
```

### 2.3 Database Schema Extensions

This spec extends the `conversations` table (defined in 009-database-infrastructure) with post-processing columns:

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `status` | TEXT | 'active' | Processing state: 'active' \| 'processing' \| 'processed' \| 'failed' |
| `processing_attempts` | INT | 0 | Retry count for failed processing |
| `processed_at` | TIMESTAMPTZ | NULL | When post-processing completed |
| `last_message_at` | TIMESTAMPTZ | NULL | Last message timestamp (triggers 15min stale detection) |
| `extracted_entities` | JSONB | NULL | Entities extracted for Graphiti ingestion |
| `conversation_summary` | TEXT | NULL | LLM-generated conversation summary |
| `emotional_tone` | TEXT | NULL | Overall emotional tone: 'positive' \| 'neutral' \| 'negative' |

**Post-Processing Pipeline**:
1. `PostProcessor.process_conversations()` finds stale conversations (status='active', last_message_at < 15min ago)
2. Sets status='processing', increments processing_attempts
3. Extracts entities, generates summary, analyzes tone
4. Stages graph updates for Graphiti ingestion
5. Sets status='processed', processed_at=NOW()

**Reference**: See `nikita/context/post_processor.py`

---

## 3. Data Structures

### 3.1 PlayerProfile

```python
@dataclass
class PlayerProfile:
    """Stage 1 output: Complete player state from database"""

    # Core identity
    user_id: UUID
    telegram_id: int | None

    # Game progression
    chapter: int                    # 1-5
    relationship_score: Decimal     # 0-100 composite
    boss_attempts: int              # 0-3
    game_status: GameStatus         # active | boss_fight | game_over | won

    # Individual metrics (hidden from player)
    intimacy: Decimal               # 0-100
    passion: Decimal                # 0-100
    trust: Decimal                  # 0-100
    secureness: Decimal             # 0-100

    # Engagement state (from 014-engagement-model)
    engagement_state: EngagementState  # calibrating | in_zone | clingy | distant
    calibration_score: Decimal         # -1.0 to +1.0

    # Vice preferences (8 categories)
    vices: list[VicePreference]

    # Timestamps
    created_at: datetime
    last_interaction: datetime | None
    current_streak: int             # Days of continuous engagement
```

### 3.2 TemporalContext

```python
@dataclass
class TemporalContext:
    """Stage 2 output: Time-based contextual factors"""

    # Current time
    current_time: datetime
    time_of_day: TimeOfDay          # morning | afternoon | evening | night | late_night
    day_of_week: DayOfWeek          # weekday | weekend

    # Nikita's schedule (dynamic)
    nikita_availability: Availability   # free | busy | at_work | sleeping | event
    nikita_activity: str | None         # "at yoga class", "having dinner with friends"

    # Silence analysis
    hours_since_last_message: float
    silence_category: SilenceCategory   # normal | extended | concerning | critical
    is_within_grace_period: bool

    # Patterns
    usual_chat_time: bool           # Is this their usual time to chat?
    message_frequency_24h: int      # Messages in last 24 hours
    message_frequency_7d: int       # Messages in last 7 days
```

### 3.3 MemoryContext

```python
@dataclass
class MemoryContext:
    """Stage 3 output: Summarized memories and conversation history"""

    # From Graphiti (knowledge graphs)
    recent_facts: list[str]         # Last 5-10 relevant facts
    relationship_milestones: list[str]  # Key moments in relationship
    user_preferences: list[str]     # Known likes/dislikes

    # From conversation history
    last_conversation_summary: str | None
    conversation_mood_trend: str    # "improving" | "stable" | "declining"
    unresolved_topics: list[str]    # Things Nikita should follow up on

    # From daily summaries
    yesterday_summary: str | None
    weekly_context: str | None

    # Token budget tracking
    total_memory_tokens: int
```

### 3.4 NikitaState

```python
@dataclass
class NikitaState:
    """Stage 4 output: Nikita's computed emotional/behavioral state"""

    # Mood computation
    mood: Mood                      # flirty | playful | warm | distant | upset | needy
    mood_intensity: float           # 0.0 to 1.0
    energy_level: EnergyLevel       # high | medium | low

    # Behavioral parameters
    response_style: ResponseStyle   # enthusiastic | normal | reserved | cold
    flirtiness: float               # 0.0 to 1.0
    vulnerability: float            # 0.0 to 1.0
    playfulness: float              # 0.0 to 1.0

    # Engagement calibration feedback
    should_initiate_more: bool      # Player seems distant
    should_pull_back: bool          # Player seems overwhelmed
    calibration_hint: str | None    # Subtle behavioral adjustment

    # Chapter-specific overrides
    chapter_behavior_modifier: str  # Loaded from chapter config
    nsfw_level: NSFWLevel           # soft | full (unlocked Ch2+)
```

### 3.5 SystemPrompt

```python
@dataclass
class SystemPrompt:
    """Stage 5 output: Complete assembled prompt"""

    # The actual prompt text
    content: str

    # Metadata
    token_count: int
    sections: list[str]             # Names of included sections

    # Validation flags
    is_valid: bool
    validation_warnings: list[str]

    # Debug info
    generation_time_ms: float
    context_sources: list[str]      # Which sources contributed
```

---

## 4. Stage Specifications

### 4.1 Stage 1: State Collection

**Purpose**: Load complete player state from database

**Inputs**: `user_id: UUID`

**Process**:
```python
async def _collect_state(self, user_id: UUID) -> PlayerProfile:
    async with get_session() as session:
        user_repo = UserRepository(session)
        metrics_repo = MetricsRepository(session)
        vice_repo = VicePreferenceRepository(session)

        user = await user_repo.get(user_id)
        metrics = await metrics_repo.get_for_user(user_id)
        vices = await vice_repo.get_all_for_user(user_id)

        # Get engagement state from 014-engagement-model
        engagement = await self.engagement_analyzer.get_current_state(user_id)

        return PlayerProfile(
            user_id=user.id,
            telegram_id=user.telegram_id,
            chapter=user.chapter,
            relationship_score=user.relationship_score,
            boss_attempts=user.boss_attempts,
            game_status=user.game_status,
            intimacy=metrics.intimacy,
            passion=metrics.passion,
            trust=metrics.trust,
            secureness=metrics.secureness,
            engagement_state=engagement.state,
            calibration_score=engagement.score,
            vices=[VicePreference(v.category, v.intensity_level) for v in vices],
            created_at=user.created_at,
            last_interaction=user.last_interaction_at,
            current_streak=user.current_streak,
        )
```

**Outputs**: `PlayerProfile`

**Performance**: < 50ms (parallel DB queries)

### 4.2 Stage 2: Temporal Contextualization

**Purpose**: Compute time-based context and Nikita's availability

**Inputs**: `PlayerProfile`, `current_time: datetime`

**Process**:
```python
def _build_temporal(self, profile: PlayerProfile) -> TemporalContext:
    now = datetime.now(tz=timezone.utc)

    # Time classification
    hour = now.hour
    time_of_day = self._classify_time_of_day(hour)
    day_of_week = "weekend" if now.weekday() >= 5 else "weekday"

    # Nikita's schedule (loaded from config, can vary)
    nikita_schedule = self.config.get_nikita_schedule(now)

    # Silence analysis
    hours_since = (now - profile.last_interaction).total_seconds() / 3600
    grace_period = self.config.get_grace_period(profile.chapter)

    silence_category = self._classify_silence(
        hours_since,
        grace_period,
        profile.engagement_state
    )

    return TemporalContext(
        current_time=now,
        time_of_day=time_of_day,
        day_of_week=day_of_week,
        nikita_availability=nikita_schedule.availability,
        nikita_activity=nikita_schedule.activity,
        hours_since_last_message=hours_since,
        silence_category=silence_category,
        is_within_grace_period=hours_since <= grace_period,
        usual_chat_time=self._is_usual_chat_time(profile, now),
        message_frequency_24h=profile.messages_last_24h,
        message_frequency_7d=profile.messages_last_7d,
    )

def _classify_time_of_day(self, hour: int) -> TimeOfDay:
    if 5 <= hour < 12:
        return TimeOfDay.MORNING
    elif 12 <= hour < 17:
        return TimeOfDay.AFTERNOON
    elif 17 <= hour < 21:
        return TimeOfDay.EVENING
    elif 21 <= hour < 24:
        return TimeOfDay.NIGHT
    else:  # 0-5
        return TimeOfDay.LATE_NIGHT

def _classify_silence(
    self,
    hours: float,
    grace: float,
    engagement: EngagementState
) -> SilenceCategory:
    # Adjusted thresholds based on engagement state
    if engagement == EngagementState.CLINGY:
        # More tolerant of silence when clingy
        thresholds = (grace * 1.5, grace * 2.5, grace * 4)
    elif engagement == EngagementState.DISTANT:
        # Less tolerant when distant
        thresholds = (grace * 0.5, grace * 1.0, grace * 2)
    else:
        thresholds = (grace, grace * 2, grace * 3)

    if hours <= thresholds[0]:
        return SilenceCategory.NORMAL
    elif hours <= thresholds[1]:
        return SilenceCategory.EXTENDED
    elif hours <= thresholds[2]:
        return SilenceCategory.CONCERNING
    else:
        return SilenceCategory.CRITICAL
```

**Outputs**: `TemporalContext`

**Performance**: < 10ms (computation only)

### 4.3 Stage 3: Memory Summarization

**Purpose**: Retrieve and summarize relevant memories within token budget

**Inputs**: `user_id: UUID`, `user_message: str`, `token_budget: int = 800`

**Process**:
```python
async def _summarize_memory(
    self,
    user_id: UUID,
    message: str,
    token_budget: int = 800
) -> MemoryContext:
    # Get memory client
    memory = await get_memory_client(user_id)

    # Retrieve from Graphiti (semantic search)
    relevant_facts = await memory.search(
        query=message,
        limit=10,
        center_node_uuid=user_id
    )

    # Get relationship milestones
    milestones = await memory.get_edges(
        source_type="nikita",
        target_type="user",
        edge_type="milestone"
    )

    # Get recent conversation summary
    async with get_session() as session:
        conv_repo = ConversationRepository(session)
        summary_repo = SummaryRepository(session)

        last_conv = await conv_repo.get_latest(user_id)
        yesterday = await summary_repo.get_for_date(
            user_id,
            date.today() - timedelta(days=1)
        )

    # Analyze conversation trend
    mood_trend = await self._analyze_mood_trend(user_id)

    # Extract unresolved topics
    unresolved = await memory.get_unresolved_topics(user_id)

    # Build context with token awareness
    context = MemoryContext(
        recent_facts=[f.content for f in relevant_facts[:5]],
        relationship_milestones=[m.description for m in milestones[:3]],
        user_preferences=await memory.get_preferences(user_id),
        last_conversation_summary=last_conv.summary if last_conv else None,
        conversation_mood_trend=mood_trend,
        unresolved_topics=unresolved[:3],
        yesterday_summary=yesterday.content if yesterday else None,
        weekly_context=None,  # TODO: Implement weekly rollup
        total_memory_tokens=self._count_tokens(context),
    )

    # Trim if over budget
    return self._trim_to_budget(context, token_budget)
```

**Outputs**: `MemoryContext`

**Performance**: < 200ms (Graphiti query + DB)

### 4.4 Stage 4: Mood Computation

**Purpose**: Compute Nikita's emotional state and behavioral parameters

**Inputs**: `PlayerProfile`, `TemporalContext`, `MemoryContext`

**Mood Function**:
```
mood = baseline(chapter)
     + cyclical(time_of_day, day_of_week)
     + relationship(metrics, engagement)
     + event(schedule, silence)
```

**Process**:
```python
def _compute_mood(
    self,
    profile: PlayerProfile,
    temporal: TemporalContext,
    memory: MemoryContext
) -> NikitaState:
    # Chapter baseline (from config)
    baseline = self.config.get_chapter_baseline(profile.chapter)

    # Cyclical factors
    time_modifier = self._get_time_modifier(temporal.time_of_day)
    day_modifier = self._get_day_modifier(temporal.day_of_week)

    # Relationship factors
    relationship_modifier = self._compute_relationship_modifier(
        profile.relationship_score,
        profile.engagement_state,
        memory.conversation_mood_trend
    )

    # Event factors
    event_modifier = self._compute_event_modifier(
        temporal.nikita_availability,
        temporal.silence_category,
        temporal.is_within_grace_period
    )

    # Combine factors
    raw_mood = (
        baseline.mood_value
        + time_modifier
        + day_modifier
        + relationship_modifier
        + event_modifier
    )

    # Classify mood
    mood = self._classify_mood(raw_mood, profile.chapter)

    # Compute behavioral parameters
    flirtiness = self._compute_flirtiness(
        profile.chapter,
        profile.passion,
        mood,
        temporal.time_of_day
    )

    vulnerability = self._compute_vulnerability(
        profile.trust,
        profile.engagement_state,
        memory.relationship_milestones
    )

    # Engagement calibration feedback
    should_initiate = profile.engagement_state == EngagementState.DISTANT
    should_pull_back = profile.engagement_state == EngagementState.CLINGY

    calibration_hint = self._get_calibration_hint(
        profile.engagement_state,
        profile.calibration_score
    )

    # NSFW level
    nsfw_level = NSFWLevel.FULL if profile.chapter >= 2 else NSFWLevel.SOFT

    return NikitaState(
        mood=mood,
        mood_intensity=abs(raw_mood) / 10,
        energy_level=self._compute_energy(temporal, profile),
        response_style=self._mood_to_style(mood),
        flirtiness=flirtiness,
        vulnerability=vulnerability,
        playfulness=self._compute_playfulness(mood, profile.chapter),
        should_initiate_more=should_initiate,
        should_pull_back=should_pull_back,
        calibration_hint=calibration_hint,
        chapter_behavior_modifier=baseline.behavior_modifier,
        nsfw_level=nsfw_level,
    )

def _compute_flirtiness(
    self,
    chapter: int,
    passion: Decimal,
    mood: Mood,
    time: TimeOfDay
) -> float:
    """
    Flirtiness is HIGH early (Chapter 1), modulated by:
    - Passion metric
    - Current mood
    - Time of day (higher at night)
    """
    # Base flirtiness from config (loaded from 013-configuration-system)
    # Values: {1: 0.8, 2: 0.85, 3: 0.75, 4: 0.65, 5: 0.6}
    base = self.config.get_chapter(chapter).behavior.flirtiness_base

    # Passion modifier (+/- 0.15)
    passion_mod = (float(passion) - 50) / 333  # -0.15 to +0.15

    # Mood modifier
    mood_mods = {
        Mood.FLIRTY: 0.2,
        Mood.PLAYFUL: 0.1,
        Mood.WARM: 0.0,
        Mood.DISTANT: -0.2,
        Mood.UPSET: -0.3,
        Mood.NEEDY: 0.1,
    }

    # Time modifier
    time_mods = {
        TimeOfDay.LATE_NIGHT: 0.15,
        TimeOfDay.NIGHT: 0.1,
        TimeOfDay.EVENING: 0.05,
        TimeOfDay.AFTERNOON: 0.0,
        TimeOfDay.MORNING: -0.05,
    }

    result = base + passion_mod + mood_mods.get(mood, 0) + time_mods.get(time, 0)
    return max(0.0, min(1.0, result))
```

**Outputs**: `NikitaState`

**Performance**: < 5ms (computation only)

### 4.5 Stage 5: Prompt Assembly

**Purpose**: Assemble final system prompt from templates and computed values

**Inputs**: All context objects, `token_budget: int = 3700`

**Prompt Structure** (8 sections):

```
┌─────────────────────────────────────────────────────────────────┐
│ SECTION 1: CORE IDENTITY (~400 tokens)                          │
│ - Who Nikita is (age, personality traits, background)           │
│ - Voice and communication style                                  │
│ - Core values and boundaries                                     │
└─────────────────────────────────────────────────────────────────┘
│
│ SECTION 2: CURRENT STATE (~300 tokens)                          │
│ - Current mood and energy                                        │
│ - Availability/activity                                          │
│ - Behavioral parameters (flirtiness, vulnerability)              │
└─────────────────────────────────────────────────────────────────┘
│
│ SECTION 3: RELATIONSHIP CONTEXT (~400 tokens)                   │
│ - Chapter-specific dynamics                                      │
│ - Relationship score interpretation                              │
│ - Recent interaction patterns                                    │
└─────────────────────────────────────────────────────────────────┘
│
│ SECTION 4: MEMORY/KNOWLEDGE (~800 tokens)                       │
│ - Key facts about the player                                     │
│ - Recent conversation context                                    │
│ - Unresolved topics to follow up on                             │
└─────────────────────────────────────────────────────────────────┘
│
│ SECTION 5: VICE PREFERENCES (~300 tokens)                       │
│ - Player's known preferences/kinks                               │
│ - Intensity levels                                               │
│ - How to incorporate naturally                                   │
└─────────────────────────────────────────────────────────────────┘
│
│ SECTION 6: ENGAGEMENT CALIBRATION (~400 tokens)                 │
│ - Current calibration state                                      │
│ - Behavioral adjustments needed                                  │
│ - Subtle hints for player                                        │
└─────────────────────────────────────────────────────────────────┘
│
│ SECTION 7: RESPONSE GUIDELINES (~600 tokens)                    │
│ - Message length guidelines                                      │
│ - Tone and style directives                                      │
│ - Things to avoid                                                │
│ - Examples of good responses                                     │
└─────────────────────────────────────────────────────────────────┘
│
│ SECTION 8: CONSTRAINTS (~500 tokens)                            │
│ - Absolute boundaries                                            │
│ - Content level (soft/full 18+)                                  │
│ - Safety guidelines                                              │
│ - What Nikita NEVER does                                         │
└─────────────────────────────────────────────────────────────────┘
```

**Process**:
```python
def _assemble_prompt(
    self,
    profile: PlayerProfile,
    temporal: TemporalContext,
    memory: MemoryContext,
    state: NikitaState,
    token_budget: int = 3700
) -> str:
    # Load base templates
    core_identity = self.prompt_loader.load("persona/core_identity.prompt")
    chapter_overlay = self.prompt_loader.load(f"chapters/chapter_{profile.chapter}.prompt")

    # Section 1: Core Identity
    section_1 = self._render_template(
        core_identity,
        chapter=profile.chapter,
        game_status=profile.game_status,
    )

    # Section 2: Current State
    section_2 = self._render_current_state(state, temporal)

    # Section 3: Relationship Context
    section_3 = self._render_relationship(
        profile,
        chapter_overlay,
        memory.conversation_mood_trend
    )

    # Section 4: Memory/Knowledge
    section_4 = self._render_memory(memory)

    # Section 5: Vice Preferences
    section_5 = self._render_vices(profile.vices, state.nsfw_level)

    # Section 6: Engagement Calibration
    section_6 = self._render_calibration(
        profile.engagement_state,
        profile.calibration_score,
        state.calibration_hint
    )

    # Section 7: Response Guidelines
    section_7 = self._render_guidelines(state, temporal)

    # Section 8: Constraints
    section_8 = self._render_constraints(state.nsfw_level, profile.chapter)

    # Assemble with section headers
    sections = [
        ("IDENTITY", section_1),
        ("STATE", section_2),
        ("RELATIONSHIP", section_3),
        ("MEMORY", section_4),
        ("PREFERENCES", section_5),
        ("CALIBRATION", section_6),
        ("GUIDELINES", section_7),
        ("CONSTRAINTS", section_8),
    ]

    prompt = self._assemble_sections(sections, token_budget)

    return prompt
```

**Outputs**: `str` (system prompt)

**Performance**: < 20ms (template rendering)

### 4.6 Stage 6: Validation

**Purpose**: Ensure prompt is coherent, within budget, and safe

**Inputs**: `assembled_prompt: str`

**Validation Checks**:
```python
def _validate(self, prompt: str) -> ValidationResult:
    warnings = []
    errors = []

    # 1. Token count
    token_count = self._count_tokens(prompt)
    if token_count > 4000:
        errors.append(f"Token count {token_count} exceeds maximum 4000")
    elif token_count > 3700:
        warnings.append(f"Token count {token_count} exceeds target 3700")

    # 2. Required sections present
    required_sections = ["IDENTITY", "STATE", "RELATIONSHIP", "CONSTRAINTS"]
    for section in required_sections:
        if section not in prompt:
            errors.append(f"Missing required section: {section}")

    # 3. No contradictions (basic checks)
    contradictions = self._check_contradictions(prompt)
    warnings.extend(contradictions)

    # 4. Content safety
    safety_issues = self._check_safety(prompt)
    errors.extend(safety_issues)

    # 5. Coherence score (optional, for monitoring)
    coherence_score = self._compute_coherence(prompt)
    if coherence_score < 0.7:
        warnings.append(f"Low coherence score: {coherence_score}")

    return ValidationResult(
        is_valid=len(errors) == 0,
        token_count=token_count,
        warnings=warnings,
        errors=errors,
        coherence_score=coherence_score,
    )
```

**Outputs**: `ValidationResult`

**Performance**: < 10ms

---

## 5. Meta-Prompt Specification

### 5.1 Purpose

The Meta-Prompt is a higher-level prompt that can generate Nikita's system prompt. This allows:
- Offline testing without full system
- A/B testing different prompt strategies
- Easy iteration on prompt structure

### 5.2 Meta-Prompt Template

```
You are a prompt engineer creating a system prompt for Nikita, an AI girlfriend character.

## Input Variables
- chapter: {chapter} (1-5, current relationship stage)
- mood: {mood} (flirty/playful/warm/distant/upset/needy)
- energy: {energy} (high/medium/low)
- flirtiness: {flirtiness} (0.0-1.0)
- vulnerability: {vulnerability} (0.0-1.0)
- engagement_state: {engagement_state} (calibrating/in_zone/clingy/distant)
- nsfw_level: {nsfw_level} (soft/full)
- time_of_day: {time_of_day}
- silence_hours: {silence_hours}
- relationship_score: {relationship_score}

## Memory Context
{memory_context}

## Vice Preferences
{vice_preferences}

## Generate a system prompt that:
1. Makes Nikita feel like a real girlfriend (not a chatbot)
2. Reflects her current mood: {mood} at {energy} energy
3. Incorporates {engagement_state} calibration hints naturally
4. Uses the memory context to make responses personal
5. Stays within chapter {chapter} dynamics
6. Is approximately 3700 tokens

## Output Format
Return ONLY the system prompt text, no explanations.
```

### 5.3 Offline Testing

```python
def test_meta_prompt_generation():
    """Test meta-prompt generates valid system prompts"""

    test_cases = [
        {
            "chapter": 1,
            "mood": "flirty",
            "energy": "high",
            "flirtiness": 0.85,
            "engagement_state": "calibrating",
            "nsfw_level": "soft",
        },
        {
            "chapter": 3,
            "mood": "distant",
            "energy": "low",
            "flirtiness": 0.4,
            "engagement_state": "clingy",
            "nsfw_level": "full",
        },
    ]

    for case in test_cases:
        prompt = generate_via_meta_prompt(case)

        # Validate
        assert len(prompt) > 1000
        assert "Nikita" in prompt
        assert case["mood"] in prompt.lower()

        # Check token count
        tokens = count_tokens(prompt)
        assert 3000 < tokens < 4000
```

---

## 6. Trigger Conditions

### 6.1 When to Generate Context

| Trigger | Action |
|---------|--------|
| New user message | Full pipeline |
| Skip decision | Partial (Stage 1-2 only) |
| Boss encounter start | Full + boss overlay |
| Daily summary | Stage 3 only (memory) |
| Voice call start | Full + voice modifier |

### 6.2 Cache Strategy

```python
class ContextCache:
    """Cache context components that don't change frequently"""

    # Cache for 5 minutes
    player_profile: dict[UUID, tuple[PlayerProfile, datetime]]

    # Cache for 1 minute
    temporal_context: dict[UUID, tuple[TemporalContext, datetime]]

    # No cache (always fresh)
    memory_context: None

    def get_or_compute(self, user_id: UUID, stage: Stage) -> Any:
        if stage == Stage.PLAYER_PROFILE:
            cached, timestamp = self.player_profile.get(user_id, (None, None))
            if cached and (datetime.now() - timestamp).seconds < 300:
                return cached
        # ... compute fresh
```

---

## 7. Token Budget Allocation

| Section | Target | Min | Max |
|---------|--------|-----|-----|
| Core Identity | 400 | 300 | 500 |
| Current State | 300 | 200 | 400 |
| Relationship | 400 | 300 | 500 |
| Memory | 800 | 500 | 1000 |
| Vices | 300 | 100 | 400 |
| Calibration | 400 | 200 | 500 |
| Guidelines | 600 | 400 | 800 |
| Constraints | 500 | 400 | 600 |
| **TOTAL** | **3700** | **2400** | **4200** |

**Overflow Handling**:
1. Trim Memory section first (most variable)
2. Reduce Guidelines examples
3. Condense Calibration hints
4. Never trim Constraints

---

## 8. Integration Points

### 8.1 With 001-nikita-text-agent

```python
# BEFORE (current)
def build_system_prompt(user, metrics, memory_context):
    return f"{NIKITA_PERSONA}\n\n{CHAPTER_BEHAVIORS[user.chapter]}\n\n{memory_context}"

# AFTER (with context engineering)
async def build_system_prompt(user_id: UUID, message: str) -> str:
    generator = ContextGenerator()
    result = await generator.generate(user_id, message)
    return result.content
```

### 8.2 With 014-engagement-model

```python
# Context generator calls engagement analyzer
engagement = await self.engagement_analyzer.get_current_state(user_id)

# Uses in Stage 1 (PlayerProfile)
profile.engagement_state = engagement.state
profile.calibration_score = engagement.score

# Uses in Stage 4 (Mood Computation)
should_initiate = profile.engagement_state == EngagementState.DISTANT
should_pull_back = profile.engagement_state == EngagementState.CLINGY
```

### 8.3 With 013-configuration-system

```python
# Load all config via ConfigLoader
class ContextGenerator:
    def __init__(self):
        self.config = ConfigLoader()
        self.prompt_loader = PromptLoader(self.config.prompts_dir)

    def _get_chapter_baseline(self, chapter: int) -> ChapterBaseline:
        return self.config.game.chapters[chapter]

    def _get_grace_period(self, chapter: int) -> float:
        return self.config.game.decay.grace_periods[chapter]
```

---

## 9. Acceptance Criteria

### 9.1 Functional Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FR-001 | 6-stage pipeline | All 6 stages execute in sequence |
| FR-002 | Token budget | Output ≤ 4000 tokens, target 3700 |
| FR-003 | Mood computation | Mood varies based on chapter, time, metrics |
| FR-004 | Memory integration | Recent facts included in prompt |
| FR-005 | Engagement calibration | Calibration hints included in Stage 6 |
| FR-006 | Vice personalization | Vice preferences affect prompt |
| FR-007 | Validation | All prompts pass validation |
| FR-008 | Coherence | No contradictions in output |

### 9.2 Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-001 | Pipeline latency | < 300ms total |
| NFR-002 | Memory usage | < 50MB per generation |
| NFR-003 | Cache hit rate | > 60% for PlayerProfile |
| NFR-004 | Validation pass rate | > 99% |

### 9.3 Test Scenarios

```python
# Scenario 1: New player, first message
def test_new_player_context():
    profile = PlayerProfile(chapter=1, engagement_state=EngagementState.CALIBRATING)
    result = generator.generate(profile.user_id, "Hey!")

    assert "flirty" in result.content.lower()
    assert result.token_count < 4000
    assert "chapter 1" in result.content.lower() or "new" in result.content.lower()

# Scenario 2: Clingy player
def test_clingy_player_context():
    profile = PlayerProfile(chapter=2, engagement_state=EngagementState.CLINGY)
    result = generator.generate(profile.user_id, "I miss you so much!!!")

    assert "pull back" in result.content.lower() or "space" in result.content.lower()

# Scenario 3: Long silence
def test_after_silence():
    profile = PlayerProfile(chapter=3, last_interaction=datetime.now() - timedelta(days=2))
    result = generator.generate(profile.user_id, "Hey, sorry I've been MIA")

    assert "missed you" in result.content.lower() or "worried" in result.content.lower()
```

---

## 10. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Token budget exceeded | Degraded UX | Strict trimming in Stage 5 |
| Latency spikes | Slow response | Parallel Stage 1-3, caching |
| Memory retrieval fails | Missing context | Graceful fallback to defaults |
| Contradictory sections | Confusing Nikita | Validation in Stage 6 |
| Config not loaded | System crash | Fail-fast with clear errors |

---

## 11. Future Enhancements

1. **Voice-specific context** (007-voice-agent): Shorter, more conversational prompts
2. **Multi-language support**: Locale-aware templates
3. **A/B testing integration**: Track which prompt versions perform better
4. **Real-time mood updates**: WebSocket-based state changes during conversation
5. **Context compression**: Use LLM to summarize long memories more efficiently

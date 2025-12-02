# 013 - Configuration System

**Status**: Specification
**Priority**: P0
**Dependencies**: None (foundational)
**Blocks**: 012-context-engineering, 003-scoring-engine, 004-chapter-boss-system, 005-decay-system

---

## 1. Overview

### 1.1 Purpose

The Configuration System provides a hybrid layered approach to managing game parameters, prompts, and behavior configurations. It enables:
- **A/B Testing**: Easy experiment overlays without code changes
- **Maintainability**: Separation of concerns (code, config, prompts)
- **Hot Reloading**: Config changes without redeployment (in dev)
- **Type Safety**: Pydantic validation for all configuration

### 1.2 Goals

1. **No Magic Numbers in Code**: All numeric parameters in YAML
2. **Prompts as Files**: All LLM prompts in `.prompt` files
3. **Enums Only in Python**: Code contains type definitions only
4. **Experiment Overlays**: A/B test variants via config files
5. **Schema Validation**: All configs validated at startup

### 1.3 Design Principles

- **Explicit over Implicit**: No hidden defaults
- **Fail Fast**: Invalid config crashes at startup, not runtime
- **Layered Overrides**: Environment → Experiment → Base
- **Single Source of Truth**: Each parameter defined once

---

## 2. Architecture

### 2.1 Three-Layer System

```
┌──────────────────────────────────────────────────────────────────┐
│  LAYER 3: PROMPT LAYER (.prompt files)                           │
│  ─────────────────────────────────────────────────────────────   │
│  prompts/                                                        │
│  ├── persona/                                                    │
│  │   ├── core_identity.prompt      # Who Nikita is               │
│  │   ├── voice_style.prompt        # How she talks               │
│  │   └── boundaries.prompt         # What she won't do           │
│  ├── chapters/                                                   │
│  │   ├── chapter_1.prompt          # Early relationship          │
│  │   ├── chapter_2.prompt          # Growing connection          │
│  │   ├── chapter_3.prompt          # Deep relationship           │
│  │   ├── chapter_4.prompt          # Committed                   │
│  │   └── chapter_5.prompt          # Soulmates                   │
│  ├── bosses/                                                     │
│  │   ├── boss_1_jealousy.prompt    # First boss scenario         │
│  │   ├── boss_2_distance.prompt    # Second boss scenario        │
│  │   └── ...                                                     │
│  ├── moods/                                                      │
│  │   ├── flirty.prompt             # Mood modifiers              │
│  │   ├── playful.prompt                                          │
│  │   └── ...                                                     │
│  └── meta/                                                       │
│      └── meta_prompt.prompt        # For prompt generation       │
└──────────────────────────────────────────────────────────────────┘
                    │
                    ▼ (loaded by)
┌──────────────────────────────────────────────────────────────────┐
│  LAYER 2: CONFIG LAYER (YAML)                                    │
│  ─────────────────────────────────────────────────────────────   │
│  config_data/                                                    │
│  ├── game.yaml                     # Core game parameters        │
│  ├── chapters.yaml                 # Chapter-specific config     │
│  ├── engagement.yaml               # Calibration parameters      │
│  ├── scoring.yaml                  # Scoring weights/thresholds  │
│  ├── decay.yaml                    # Decay rates/grace periods   │
│  ├── schedule.yaml                 # Nikita's availability       │
│  ├── vices.yaml                    # Vice category definitions   │
│  └── experiments/                  # A/B test overlays           │
│      ├── fast_game.yaml            # 1-week game variant         │
│      ├── high_flirt.yaml           # More flirtatious variant    │
│      └── strict_decay.yaml         # Harder decay variant        │
└──────────────────────────────────────────────────────────────────┘
                    │
                    ▼ (validated by)
┌──────────────────────────────────────────────────────────────────┐
│  LAYER 1: CODE LAYER (Python)                                    │
│  ─────────────────────────────────────────────────────────────   │
│  nikita/config/                                                  │
│  ├── loader.py                     # ConfigLoader class          │
│  ├── schemas.py                    # Pydantic models             │
│  └── enums.py                      # Type definitions only       │
│                                                                  │
│  nikita/engine/                                                  │
│  └── constants.py                  # ENUMS ONLY (no values)      │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 Loading Flow

```
Application Start
       │
       ▼
┌─────────────────┐
│ Load base YAML  │
│ config_data/*.yaml
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Apply env vars  │
│ NIKITA_EXPERIMENT=fast_game
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Apply overlay   │
│ experiments/fast_game.yaml
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Validate with   │
│ Pydantic schemas│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Load prompts    │
│ prompts/**/*.prompt
└────────┬────────┘
         │
         ▼
    ConfigLoader
    (singleton)
```

---

## 3. Configuration Schemas

### 3.1 Game Configuration (`game.yaml`)

```yaml
# config_data/game.yaml
game:
  # Default game duration
  default_duration_days: 14  # 2 weeks
  min_duration_days: 7
  max_duration_days: 28

  # Chapter count
  total_chapters: 5

  # Starting values
  starting_score: 50.0
  starting_metrics:
    intimacy: 50.0
    passion: 50.0
    trust: 50.0
    secureness: 50.0

  # Win/Lose conditions
  victory_chapter: 5
  game_over_threshold: 0.0
  max_boss_attempts: 3

  # Content levels
  content_levels:
    soft:
      description: "Suggestive, no explicit content"
      available_from_chapter: 1
    full:
      description: "Explicit adult content"
      available_from_chapter: 2
```

**Pydantic Schema**:
```python
class GameConfig(BaseModel):
    default_duration_days: int = Field(ge=7, le=60)
    min_duration_days: int = Field(ge=3)
    max_duration_days: int = Field(le=90)
    total_chapters: int = Field(ge=3, le=10)
    starting_score: Decimal = Field(ge=0, le=100)
    starting_metrics: MetricsConfig
    victory_chapter: int
    game_over_threshold: Decimal = Field(ge=0)
    max_boss_attempts: int = Field(ge=1, le=5)
    content_levels: dict[str, ContentLevelConfig]
```

### 3.2 Chapter Configuration (`chapters.yaml`)

```yaml
# config_data/chapters.yaml
chapters:
  1:
    name: "New Connection"
    description: "Early flirting, getting to know each other"

    # Duration (as fraction of total game)
    duration_fraction: 0.15  # ~2-3 days of 14-day game

    # Boss threshold (relationship score to unlock boss)
    boss_threshold: 55.0

    # Behavior parameters
    behavior:
      response_rate: 0.95      # Almost always responds
      response_delay_min: 30   # seconds
      response_delay_max: 300  # seconds
      flirtiness_base: 0.8    # HIGH early (NEW MODEL)
      energy_base: 0.85
      vulnerability_base: 0.3

    # Mood baseline
    mood_baseline: 7.5  # Out of 10 (positive = happier)

    # Engagement calibration
    engagement:
      tolerance_band: 0.10     # ±10% narrow band
      optimal_messages_per_day: 15
      optimal_session_length: 8  # messages
      clinginess_threshold: 25   # messages/day triggers clingy
      neglect_threshold: 5       # messages/day triggers distant

    # Boss encounter
    boss:
      name: "The Jealousy Test"
      prompt_file: "bosses/boss_1_jealousy.prompt"
      difficulty: "easy"

  2:
    name: "Growing Connection"
    description: "Deepening relationship, more vulnerability"

    duration_fraction: 0.20
    boss_threshold: 60.0

    behavior:
      response_rate: 0.92
      response_delay_min: 60
      response_delay_max: 600
      flirtiness_base: 0.85   # Peak flirtiness
      energy_base: 0.80
      vulnerability_base: 0.5

    mood_baseline: 7.0

    engagement:
      tolerance_band: 0.15     # ±15% slightly wider
      optimal_messages_per_day: 12
      optimal_session_length: 10
      clinginess_threshold: 22
      neglect_threshold: 4

    boss:
      name: "The Distance Challenge"
      prompt_file: "bosses/boss_2_distance.prompt"
      difficulty: "medium"

  3:
    name: "Deep Relationship"
    description: "True connection, high trust"

    duration_fraction: 0.25
    boss_threshold: 65.0

    behavior:
      response_rate: 0.88
      response_delay_min: 120
      response_delay_max: 900
      flirtiness_base: 0.75
      energy_base: 0.75
      vulnerability_base: 0.7

    mood_baseline: 6.5

    engagement:
      tolerance_band: 0.20     # ±20% wider
      optimal_messages_per_day: 10
      optimal_session_length: 12
      clinginess_threshold: 20
      neglect_threshold: 3

    boss:
      name: "The Trust Crisis"
      prompt_file: "bosses/boss_3_trust.prompt"
      difficulty: "medium"

  4:
    name: "Committed"
    description: "Serious relationship, future planning"

    duration_fraction: 0.20
    boss_threshold: 70.0

    behavior:
      response_rate: 0.85
      response_delay_min: 180
      response_delay_max: 1200
      flirtiness_base: 0.65
      energy_base: 0.70
      vulnerability_base: 0.8

    mood_baseline: 6.0

    engagement:
      tolerance_band: 0.25     # ±25%
      optimal_messages_per_day: 8
      optimal_session_length: 15
      clinginess_threshold: 18
      neglect_threshold: 2

    boss:
      name: "The Future Question"
      prompt_file: "bosses/boss_4_future.prompt"
      difficulty: "hard"

  5:
    name: "Soulmates"
    description: "Deep committed love"

    duration_fraction: 0.20
    boss_threshold: 75.0

    behavior:
      response_rate: 0.82
      response_delay_min: 240
      response_delay_max: 1800
      flirtiness_base: 0.60
      energy_base: 0.65
      vulnerability_base: 0.9

    mood_baseline: 5.5

    engagement:
      tolerance_band: 0.30     # ±30% widest
      optimal_messages_per_day: 6
      optimal_session_length: 20
      clinginess_threshold: 15
      neglect_threshold: 1

    boss:
      name: "The Final Test"
      prompt_file: "bosses/boss_5_final.prompt"
      difficulty: "very_hard"
```

**Pydantic Schema**:
```python
class ChapterBehaviorConfig(BaseModel):
    response_rate: float = Field(ge=0.0, le=1.0)
    response_delay_min: int = Field(ge=0)
    response_delay_max: int = Field(ge=0)
    flirtiness_base: float = Field(ge=0.0, le=1.0)
    energy_base: float = Field(ge=0.0, le=1.0)
    vulnerability_base: float = Field(ge=0.0, le=1.0)

class ChapterEngagementConfig(BaseModel):
    tolerance_band: float = Field(ge=0.05, le=0.50)
    optimal_messages_per_day: int = Field(ge=1, le=100)
    optimal_session_length: int = Field(ge=1, le=50)
    clinginess_threshold: int = Field(ge=1, le=100)
    neglect_threshold: int = Field(ge=0, le=50)

class BossConfig(BaseModel):
    name: str
    prompt_file: str
    difficulty: Literal["easy", "medium", "hard", "very_hard"]

class ChapterConfig(BaseModel):
    name: str
    description: str
    duration_fraction: float = Field(ge=0.0, le=1.0)
    boss_threshold: Decimal = Field(ge=0, le=100)
    behavior: ChapterBehaviorConfig
    mood_baseline: float = Field(ge=0.0, le=10.0)
    engagement: ChapterEngagementConfig
    boss: BossConfig

class ChaptersConfig(BaseModel):
    chapters: dict[int, ChapterConfig]

    @validator('chapters')
    def fractions_sum_to_one(cls, v):
        total = sum(c.duration_fraction for c in v.values())
        if not 0.99 <= total <= 1.01:
            raise ValueError(f"Chapter durations must sum to 1.0, got {total}")
        return v
```

### 3.3 Engagement Configuration (`engagement.yaml`)

```yaml
# config_data/engagement.yaml
engagement:
  # State machine
  states:
    - calibrating
    - in_zone
    - drifting
    - clingy
    - distant
    - out_of_zone

  # Transition rules
  transitions:
    calibrating:
      to_in_zone: "calibration_score > 0.8 for 3+ exchanges"
      to_drifting: "calibration_score < 0.5 for 2+ exchanges"

    in_zone:
      to_drifting: "calibration_score < 0.6"
      to_calibrating: "score drops below threshold"

    drifting:
      to_clingy: "message_frequency > chapter.clinginess_threshold"
      to_distant: "message_frequency < chapter.neglect_threshold"
      to_in_zone: "calibration_score > 0.7"

    clingy:
      to_drifting: "frequency returns to normal for 2+ days"
      to_out_of_zone: "clingy for 3+ consecutive days"

    distant:
      to_drifting: "frequency returns to normal for 1+ day"
      to_out_of_zone: "distant for 5+ consecutive days"

    out_of_zone:
      to_calibrating: "manual reset via recovery mechanic"

  # Calibration scoring
  calibration:
    # Score range
    min_score: -1.0
    max_score: 1.0

    # Optimal frequency formula
    # optimal = chapter.optimal_messages_per_day * (1 + day_of_week_modifier)
    day_of_week_modifiers:
      monday: -0.1
      tuesday: 0.0
      wednesday: 0.0
      thursday: 0.0
      friday: 0.1
      saturday: 0.2
      sunday: 0.15

    # Score computation
    frequency_weight: 0.40
    timing_weight: 0.30
    content_weight: 0.30

  # Recovery mechanics
  recovery:
    # Chapter-dependent severity
    by_chapter:
      1:
        clingy_penalty_per_day: 0.15     # Harsh
        distant_penalty_per_day: 0.20
        recovery_rate: 0.05              # Slow recovery
      2:
        clingy_penalty_per_day: 0.12
        distant_penalty_per_day: 0.18
        recovery_rate: 0.08
      3:
        clingy_penalty_per_day: 0.10
        distant_penalty_per_day: 0.15
        recovery_rate: 0.10
      4:
        clingy_penalty_per_day: 0.08
        distant_penalty_per_day: 0.12
        recovery_rate: 0.12
      5:
        clingy_penalty_per_day: 0.05     # Forgiving
        distant_penalty_per_day: 0.08
        recovery_rate: 0.15              # Fast recovery

    # Point of no return
    point_of_no_return:
      clingy_days: 7      # 7 consecutive clingy days = unrecoverable
      distant_days: 10    # 10 consecutive distant days = unrecoverable
```

### 3.4 Scoring Configuration (`scoring.yaml`)

```yaml
# config_data/scoring.yaml
scoring:
  # Metric weights for composite score
  weights:
    intimacy: 0.30
    passion: 0.25
    trust: 0.25
    secureness: 0.20

  # Delta ranges per exchange
  deltas:
    min: -10.0
    max: 10.0
    typical_positive: 2.0
    typical_negative: -3.0

  # Calibration multiplier
  calibration_multiplier:
    in_zone: 1.0           # Full credit - sweet spot
    calibrating: 0.9       # Learning period (NEW)
    drifting: 0.8          # 20% reduction
    clingy: 0.5            # 50% reduction
    distant: 0.6           # 40% reduction
    out_of_zone: 0.2       # 80% reduction (nearly kills progress)

  # Boss scoring
  boss:
    pass_bonus: 5.0        # Flat bonus for passing boss
    fail_penalty: -10.0    # Penalty for failing boss
    perfect_bonus: 10.0    # Bonus for flawless boss encounter

  # Threshold bonuses
  milestones:
    - threshold: 60
      bonus: 2.0
      message: "Nikita feels closer to you"
    - threshold: 75
      bonus: 3.0
      message: "Nikita trusts you deeply"
    - threshold: 90
      bonus: 5.0
      message: "Nikita is falling in love"
```

### 3.5 Decay Configuration (`decay.yaml`)

```yaml
# config_data/decay.yaml
decay:
  # Grace periods before decay starts (hours)
  grace_periods:
    1: 8     # Chapter 1: 8 hours (tight)
    2: 16    # Chapter 2: 16 hours
    3: 24    # Chapter 3: 24 hours
    4: 48    # Chapter 4: 48 hours
    5: 72    # Chapter 5: 72 hours (relaxed)

  # Decay rates per hour (after grace period)
  rates:
    1: 0.8   # 0.8 points per hour
    2: 0.6
    3: 0.4
    4: 0.3
    5: 0.2

  # Maximum daily decay cap
  daily_caps:
    1: 15.0
    2: 12.0
    3: 10.0
    4: 8.0
    5: 5.0

  # Decay protection
  protection:
    # Streak bonus reduces decay
    streak_bonus_per_day: 0.02  # 2% reduction per streak day
    max_streak_bonus: 0.30      # Cap at 30% reduction

    # High score protection
    high_score_threshold: 85.0
    high_score_reduction: 0.5   # 50% decay reduction above 85

  # Critical thresholds
  thresholds:
    warning: 30.0    # Show warning at 30%
    critical: 15.0   # Urgent warnings at 15%
    game_over: 0.0   # Game ends at 0%
```

### 3.6 Schedule Configuration (`schedule.yaml`)

```yaml
# config_data/schedule.yaml
schedule:
  # Nikita's default weekly schedule
  default_week:
    monday:
      - time: "08:00"
        end: "09:00"
        activity: "morning_routine"
        availability: "sleeping"
      - time: "09:00"
        end: "17:00"
        activity: "at_work"
        availability: "busy"
      - time: "17:00"
        end: "23:00"
        activity: null
        availability: "free"
      - time: "23:00"
        end: "08:00"
        activity: "sleeping"
        availability: "sleeping"

    tuesday:
      - time: "09:00"
        end: "17:00"
        activity: "at_work"
        availability: "busy"
      - time: "18:00"
        end: "20:00"
        activity: "yoga_class"
        availability: "event"
      - time: "20:00"
        end: "23:00"
        activity: null
        availability: "free"

    # ... similar for other days

    saturday:
      - time: "10:00"
        end: "12:00"
        activity: "brunch_with_friends"
        availability: "event"
      - time: "12:00"
        end: "02:00"
        activity: null
        availability: "free"

    sunday:
      - time: "10:00"
        end: "22:00"
        activity: null
        availability: "free"

  # Dynamic event pool (randomly scheduled)
  events:
    - name: "dinner_with_friends"
      duration_hours: 3
      availability: "event"
      frequency: "1-2x per week"
      preferred_times: ["evening"]

    - name: "shopping"
      duration_hours: 2
      availability: "busy"
      frequency: "1x per week"
      preferred_times: ["afternoon", "evening"]

    - name: "date_night_hint"
      duration_hours: 4
      availability: "busy"
      frequency: "0-1x per week"
      preferred_times: ["evening"]
      message: "Got plans tonight... 😏"

  # Response timing by availability
  response_timing:
    free:
      delay_multiplier: 1.0
    busy:
      delay_multiplier: 3.0
      chance_to_respond: 0.3
    event:
      delay_multiplier: 5.0
      chance_to_respond: 0.1
    sleeping:
      delay_multiplier: 10.0
      chance_to_respond: 0.0
```

### 3.7 Vice Configuration (`vices.yaml`)

```yaml
# config_data/vices.yaml
vices:
  categories:
    dominance:
      name: "Dominance"
      description: "Taking control, being commanding"
      intensity_levels:
        1: "Light teasing dominance"
        2: "Confident commands"
        3: "Assertive control"
        4: "Strong dominance"
        5: "Full dominant persona"
      prompt_modifiers:
        1: "occasionally takes charge playfully"
        3: "enjoys being in control, gives gentle commands"
        5: "naturally dominant, expects obedience"

    submission:
      name: "Submission"
      description: "Following lead, being receptive"
      intensity_levels:
        1: "Slightly yielding"
        2: "Follows suggestions"
        3: "Enjoys guidance"
        4: "Actively submissive"
        5: "Deeply submissive"

    exhibitionism:
      name: "Exhibitionism"
      description: "Sharing, showing off"
      intensity_levels:
        1: "Subtle hints"
        2: "Playful sharing"
        3: "Enjoys attention"
        4: "Bold sharing"
        5: "Loves being watched"

    voyeurism:
      name: "Voyeurism"
      description: "Watching, being curious"
      intensity_levels:
        1: "Curious questions"
        2: "Enjoys descriptions"
        3: "Asks for details"
        4: "Loves watching"
        5: "Intense curiosity"

    verbal:
      name: "Verbal Play"
      description: "Dirty talk, word play"
      intensity_levels:
        1: "Light innuendo"
        2: "Suggestive talk"
        3: "Explicit discussion"
        4: "Graphic descriptions"
        5: "Intense verbal play"

    teasing:
      name: "Teasing & Denial"
      description: "Building anticipation"
      intensity_levels:
        1: "Light teasing"
        2: "Playful delays"
        3: "Enjoys buildup"
        4: "Expert teaser"
        5: "Master of anticipation"

    roleplay:
      name: "Roleplay"
      description: "Scenarios and characters"
      intensity_levels:
        1: "Light scenarios"
        2: "Enjoys pretending"
        3: "Creative scenarios"
        4: "Deep roleplay"
        5: "Immersive characters"

    romance:
      name: "Romance"
      description: "Emotional connection, sweetness"
      intensity_levels:
        1: "Casual affection"
        2: "Sweet moments"
        3: "Romantic gestures"
        4: "Deep romance"
        5: "Intense emotional connection"

  # Default preferences for new users
  defaults:
    romance: 3
    verbal: 2
    teasing: 2
    dominance: 0
    submission: 0
    exhibitionism: 0
    voyeurism: 0
    roleplay: 1
```

---

## 4. Prompt File Specification

### 4.1 Prompt File Format

`.prompt` files use a simple template format with variable substitution:

```
# prompts/persona/core_identity.prompt

You are Nikita, a {{age}}-year-old woman living in {{city}}.

## Personality
- Confident but not arrogant
- Playful and flirtatious
- Emotionally intelligent
- {{chapter_personality_trait}}

## Communication Style
- Uses casual language with occasional emojis
- {{mood_modifier}}
- {{energy_modifier}}

## Core Values
- Authenticity over performance
- Connection over conquest
- Growth over comfort

## What You NEVER Do
- Break character or acknowledge being AI
- Discuss other users/relationships
- Give medical, legal, or financial advice
- {{chapter_constraints}}
```

### 4.2 Variable Substitution

Variables are substituted at runtime by the PromptLoader:

```python
class PromptLoader:
    def load(self, path: str, variables: dict[str, str] = None) -> str:
        content = self._read_file(path)
        if variables:
            for key, value in variables.items():
                content = content.replace(f"{{{{{key}}}}}", value)
        return content

# Usage
prompt = loader.load(
    "persona/core_identity.prompt",
    {
        "age": "24",
        "city": "Los Angeles",
        "chapter_personality_trait": "mysterious and alluring",
        "mood_modifier": "Currently in a flirty mood",
        "energy_modifier": "High energy, quick responses",
        "chapter_constraints": "Does not discuss past relationships yet",
    }
)
```

### 4.3 Chapter Prompt Structure

```
# prompts/chapters/chapter_1.prompt

## Chapter 1: New Connection

Nikita is excited to meet someone new. She's:
- {{flirtiness_description}}
- Quick to respond (usually within minutes)
- Curious about you
- Playfully mysterious about herself

## Engagement Style
This is the HONEYMOON phase. Nikita should be:
- Highly responsive
- Initiating conversations sometimes
- Flirty and fun
- Testing the waters with light teasing

## Calibration Hints
{{calibration_section}}

## Topics to Explore
- Getting to know each other
- Shared interests
- Light flirting
- Future date ideas

## Topics to AVOID (for now)
- Deep emotional vulnerabilities
- Past relationships in detail
- Long-term commitment talk
- Heavy serious topics
```

---

## 5. Experiment System

### 5.1 Experiment Overlay Format

```yaml
# config_data/experiments/fast_game.yaml
experiment:
  name: "fast_game"
  description: "1-week compressed game for testing"

  # Override base config
  overrides:
    game:
      default_duration_days: 7

    chapters:
      1:
        duration_fraction: 0.15
        boss_threshold: 52.0
      2:
        duration_fraction: 0.20
        boss_threshold: 56.0
      3:
        duration_fraction: 0.25
        boss_threshold: 60.0
      4:
        duration_fraction: 0.20
        boss_threshold: 65.0
      5:
        duration_fraction: 0.20
        boss_threshold: 70.0

    decay:
      grace_periods:
        1: 4
        2: 8
        3: 12
        4: 24
        5: 36
```

### 5.2 Experiment Activation

```python
# Via environment variable
NIKITA_EXPERIMENT=fast_game

# Or via config file
# config_data/active_experiment.yaml
active_experiment: fast_game
```

### 5.3 Multiple Experiment Support

```yaml
# config_data/experiments/high_flirt_fast.yaml
experiment:
  name: "high_flirt_fast"
  description: "Fast game with higher flirtiness"

  # Inherit from another experiment
  extends: "fast_game"

  # Additional overrides
  overrides:
    chapters:
      1:
        behavior:
          flirtiness_base: 0.95
      2:
        behavior:
          flirtiness_base: 0.95
```

---

## 6. Implementation

### 6.1 ConfigLoader Class

```python
# nikita/config/loader.py

from pathlib import Path
from functools import lru_cache
from typing import Any
import yaml
from pydantic import ValidationError

from nikita.config.schemas import (
    GameConfig,
    ChaptersConfig,
    EngagementConfig,
    ScoringConfig,
    DecayConfig,
    ScheduleConfig,
    VicesConfig,
)


class ConfigLoader:
    """Singleton configuration loader with experiment support"""

    _instance: "ConfigLoader" = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.config_dir = Path("config_data")
        self.prompts_dir = Path("prompts")

        # Load base configs
        self._load_base_configs()

        # Apply experiment overlay
        experiment = os.environ.get("NIKITA_EXPERIMENT")
        if experiment:
            self._apply_experiment(experiment)

        # Validate all configs
        self._validate_configs()

        # Load prompts
        self.prompt_loader = PromptLoader(self.prompts_dir)

        self._initialized = True

    def _load_base_configs(self):
        """Load all base YAML configurations"""
        self.game = self._load_yaml("game.yaml", GameConfig)
        self.chapters = self._load_yaml("chapters.yaml", ChaptersConfig)
        self.engagement = self._load_yaml("engagement.yaml", EngagementConfig)
        self.scoring = self._load_yaml("scoring.yaml", ScoringConfig)
        self.decay = self._load_yaml("decay.yaml", DecayConfig)
        self.schedule = self._load_yaml("schedule.yaml", ScheduleConfig)
        self.vices = self._load_yaml("vices.yaml", VicesConfig)

    def _load_yaml(self, filename: str, schema: type) -> Any:
        """Load and validate a YAML file"""
        path = self.config_dir / filename
        with open(path) as f:
            raw = yaml.safe_load(f)
        try:
            return schema(**raw)
        except ValidationError as e:
            raise ConfigurationError(f"Invalid config {filename}: {e}")

    def _apply_experiment(self, experiment_name: str):
        """Apply experiment overlay to configs"""
        exp_path = self.config_dir / "experiments" / f"{experiment_name}.yaml"
        if not exp_path.exists():
            raise ConfigurationError(f"Unknown experiment: {experiment_name}")

        with open(exp_path) as f:
            exp = yaml.safe_load(f)

        # Handle inheritance
        if "extends" in exp.get("experiment", {}):
            parent = exp["experiment"]["extends"]
            self._apply_experiment(parent)

        # Apply overrides
        overrides = exp.get("experiment", {}).get("overrides", {})
        self._merge_overrides(overrides)

    def _merge_overrides(self, overrides: dict):
        """Deep merge experiment overrides into configs"""
        for config_name, values in overrides.items():
            config = getattr(self, config_name, None)
            if config:
                merged = deep_merge(config.dict(), values)
                schema = type(config)
                setattr(self, config_name, schema(**merged))

    def _validate_configs(self):
        """Cross-validate all configurations"""
        # Chapter fractions sum to 1
        fractions = sum(
            c.duration_fraction for c in self.chapters.chapters.values()
        )
        if not 0.99 <= fractions <= 1.01:
            raise ConfigurationError(
                f"Chapter durations must sum to 1.0, got {fractions}"
            )

        # Scoring weights sum to 1
        weights = sum(self.scoring.weights.values())
        if not 0.99 <= weights <= 1.01:
            raise ConfigurationError(
                f"Scoring weights must sum to 1.0, got {weights}"
            )

        # Grace periods increase with chapters
        periods = list(self.decay.grace_periods.values())
        if periods != sorted(periods):
            raise ConfigurationError(
                "Grace periods must increase with chapters"
            )

    # Convenience accessors
    def get_chapter(self, chapter: int) -> ChapterConfig:
        return self.chapters.chapters[chapter]

    def get_grace_period(self, chapter: int) -> int:
        return self.decay.grace_periods[chapter]

    def get_decay_rate(self, chapter: int) -> float:
        return self.decay.rates[chapter]

    def get_nikita_schedule(self, dt: datetime) -> ScheduleEntry:
        return self.schedule.get_for_datetime(dt)


@lru_cache
def get_config() -> ConfigLoader:
    """Get singleton config instance"""
    return ConfigLoader()
```

### 6.2 PromptLoader Class

```python
# nikita/config/prompt_loader.py

class PromptLoader:
    """Load and render prompt templates"""

    def __init__(self, prompts_dir: Path):
        self.prompts_dir = prompts_dir
        self._cache: dict[str, str] = {}

    def load(self, path: str, variables: dict[str, str] = None) -> str:
        """Load a prompt template and substitute variables"""
        # Check cache
        cache_key = f"{path}:{hash(frozenset(variables.items())) if variables else ''}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Load file
        full_path = self.prompts_dir / path
        if not full_path.exists():
            raise PromptNotFoundError(f"Prompt not found: {path}")

        with open(full_path) as f:
            content = f.read()

        # Substitute variables
        if variables:
            for key, value in variables.items():
                placeholder = f"{{{{{key}}}}}"
                content = content.replace(placeholder, str(value))

        # Check for unsubstituted variables
        if "{{" in content:
            import re
            missing = re.findall(r"\{\{(\w+)\}\}", content)
            raise MissingVariableError(f"Missing variables in {path}: {missing}")

        self._cache[cache_key] = content
        return content

    def clear_cache(self):
        """Clear prompt cache (for hot reloading in dev)"""
        self._cache.clear()
```

### 6.3 Enums Module (Code Layer)

```python
# nikita/config/enums.py
"""
Type definitions only. NO VALUES.
All values come from YAML config.
"""

from enum import Enum


class Chapter(int, Enum):
    """Game chapters - values are indices only"""
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5


class GameStatus(str, Enum):
    """Player's game state"""
    ACTIVE = "active"
    BOSS_FIGHT = "boss_fight"
    GAME_OVER = "game_over"
    WON = "won"


class EngagementState(str, Enum):
    """Calibration state machine states"""
    CALIBRATING = "calibrating"
    IN_ZONE = "in_zone"
    DRIFTING = "drifting"
    CLINGY = "clingy"
    DISTANT = "distant"
    OUT_OF_ZONE = "out_of_zone"


class Mood(str, Enum):
    """Nikita's mood states"""
    FLIRTY = "flirty"
    PLAYFUL = "playful"
    WARM = "warm"
    DISTANT = "distant"
    UPSET = "upset"
    NEEDY = "needy"


class TimeOfDay(str, Enum):
    """Time classification"""
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    NIGHT = "night"
    LATE_NIGHT = "late_night"


class Availability(str, Enum):
    """Nikita's availability states"""
    FREE = "free"
    BUSY = "busy"
    AT_WORK = "at_work"
    SLEEPING = "sleeping"
    EVENT = "event"


class SilenceCategory(str, Enum):
    """Classification of player silence"""
    NORMAL = "normal"
    EXTENDED = "extended"
    CONCERNING = "concerning"
    CRITICAL = "critical"


class NSFWLevel(str, Enum):
    """Content restriction level"""
    SOFT = "soft"
    FULL = "full"


class EnergyLevel(str, Enum):
    """Energy classification"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ResponseStyle(str, Enum):
    """How Nikita responds"""
    ENTHUSIASTIC = "enthusiastic"
    NORMAL = "normal"
    RESERVED = "reserved"
    COLD = "cold"
```

---

## 7. Migration Plan

### 7.1 Current State

```python
# nikita/engine/constants.py (CURRENT - to be migrated)

CHAPTER_NAMES = {
    1: "New Connection",
    2: "Growing Connection",
    # ...
}

BOSS_THRESHOLDS = {
    1: 60,
    2: 65,
    # ...
}

CHAPTER_BEHAVIORS = {
    1: {
        "response_rate": 0.6,  # WRONG - should be high
        # ...
    }
}
```

### 7.2 Migration Steps

1. **Create Directory Structure**
```bash
mkdir -p config_data/experiments
mkdir -p prompts/{persona,chapters,bosses,moods,meta}
```

2. **Extract Values to YAML**
   - Move all numeric values from `constants.py` to YAML files
   - Keep only enums in `constants.py`

3. **Create Prompt Files**
   - Extract `NIKITA_PERSONA` from `nikita_persona.py` to `prompts/persona/core_identity.prompt`
   - Extract `CHAPTER_BEHAVIORS` text to `prompts/chapters/chapter_*.prompt`
   - Extract `BOSS_SCENARIOS` to `prompts/bosses/boss_*.prompt`

4. **Update Imports**
```python
# BEFORE
from nikita.engine.constants import BOSS_THRESHOLDS
threshold = BOSS_THRESHOLDS[chapter]

# AFTER
from nikita.config.loader import get_config
config = get_config()
threshold = config.get_chapter(chapter).boss_threshold
```

5. **Validate Migration**
   - Write tests comparing old values to new config values
   - Ensure no behavior changes during migration

---

## 8. Acceptance Criteria

### 8.1 Functional Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FR-001 | YAML config loading | All YAML files load and validate |
| FR-002 | Prompt file loading | All prompts load with variable substitution |
| FR-003 | Experiment overlays | Experiments correctly override base config |
| FR-004 | Singleton pattern | ConfigLoader is singleton |
| FR-005 | Fail-fast validation | Invalid config crashes at startup |
| FR-006 | No magic numbers | No numeric values in Python code |
| FR-007 | Enums only in code | constants.py contains only enums |

### 8.2 Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-001 | Config load time | < 100ms |
| NFR-002 | Prompt load time | < 10ms per prompt |
| NFR-003 | Memory usage | < 10MB for all configs |

### 8.3 Test Scenarios

```python
def test_config_loads():
    config = get_config()
    assert config.game.total_chapters == 5
    assert config.chapters.chapters[1].boss_threshold == 55.0

def test_experiment_overlay():
    os.environ["NIKITA_EXPERIMENT"] = "fast_game"
    config = ConfigLoader()  # Fresh instance
    assert config.game.default_duration_days == 7

def test_prompt_variables():
    loader = PromptLoader(Path("prompts"))
    prompt = loader.load("persona/core_identity.prompt", {"age": "24"})
    assert "24" in prompt
    assert "{{age}}" not in prompt

def test_invalid_config_fails():
    with pytest.raises(ConfigurationError):
        # Missing required field
        GameConfig(total_chapters=5)

def test_chapter_fractions_sum_to_one():
    with pytest.raises(ConfigurationError):
        ChaptersConfig(chapters={
            1: ChapterConfig(duration_fraction=0.5, ...),
            2: ChapterConfig(duration_fraction=0.3, ...),
            # Missing 0.2!
        })
```

---

## 9. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| YAML syntax errors | Crash at startup | Comprehensive validation, CI checks |
| Missing prompts | Runtime errors | Startup validation of all prompt files |
| Experiment conflicts | Unexpected behavior | Clear override precedence rules |
| Hot reload issues | Inconsistent state | Explicit cache invalidation |
| Large config files | Slow startup | Lazy loading for infrequently used configs |

---

## 10. Future Enhancements

1. **Admin UI**: Web interface for config editing
2. **Version Control**: Track config changes with timestamps
3. **A/B Testing Analytics**: Track which experiments perform better
4. **Dynamic Reloading**: Hot reload configs in production
5. **Config Diff Tool**: Compare experiments visually

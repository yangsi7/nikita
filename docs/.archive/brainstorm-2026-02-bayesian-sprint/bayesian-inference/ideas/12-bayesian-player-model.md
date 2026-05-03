# 12 - Complete Bayesian Player Model for Nikita

> **Series**: Bayesian Inference Brainstorm for Nikita
> **Author**: researcher-bayesian
> **Depends on**: [01-bayesian-fundamentals.md](../research/01-bayesian-fundamentals.md), [02-patient-modeling.md](../research/02-patient-modeling.md), [09-beta-dirichlet-modeling.md](../research/09-beta-dirichlet-modeling.md)
> **Referenced by**: [18-bayesian-vice-discovery.md](./18-bayesian-vice-discovery.md)

---

## Table of Contents

1. [Model Architecture Overview](#1-model-architecture-overview)
2. [State Schema at Game Start](#2-state-schema-at-game-start)
3. [Observation Model: Events to Updates](#3-observation-model-events-to-updates)
4. [Cold-Start Handling](#4-cold-start-handling)
5. [Full Data Flow](#5-full-data-flow)
6. [Database Schema](#6-database-schema)
7. [Migration Plan from Current Storage](#7-migration-plan-from-current-storage)
8. [Integration with 9-Stage Pipeline](#8-integration-with-9-stage-pipeline)
9. [Chapter Transitions](#9-chapter-transitions)
10. [Boss Encounter Integration](#10-boss-encounter-integration)
11. [Complete Implementation](#11-complete-implementation)
12. [Key Takeaways for Nikita](#12-key-takeaways-for-nikita)

---

## 1. Model Architecture Overview

### The Unified Player Model

The Bayesian Player Model is a single, coherent state object that replaces multiple scattered components in the current codebase:

```
CURRENT SYSTEM (scattered state):
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ UserMetrics       │  │ ViceProfile       │  │ EmotionalState    │
│ (flat Decimal)    │  │ (8 floats)        │  │ (4D + conflict)   │
│ in user_metrics   │  │ in vice_prefs     │  │ in emotional_state│
└──────────────────┘  └──────────────────┘  └──────────────────┘
         │                     │                     │
         └─────────────────────┼─────────────────────┘
                               │
                     LLM calls to update all three

BAYESIAN SYSTEM (unified state):
┌──────────────────────────────────────────────────────────────┐
│                    BayesianPlayerModel                        │
│  ┌──────────┐ ┌────────────┐ ┌─────────┐ ┌──────────────┐   │
│  │ 4 Beta   │ │ Dirichlet  │ │ HMM     │ │ Skip/Timing  │   │
│  │ Metrics  │ │ 8 Vices    │ │ 6 Moods │ │ Thompson     │   │
│  └──────────┘ └────────────┘ └─────────┘ └──────────────┘   │
│                                                               │
│  Single JSONB column: user_bayesian_state.state               │
│  Updated via: ObservationEncoder (0 LLM tokens)              │
└──────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Single source of truth**: One JSONB column holds all player state
2. **Zero-token updates**: 97% of updates use observation encoding, not LLM calls
3. **Uncertainty-aware**: Every metric carries a distribution, not just a point value
4. **Naturally adaptive**: Model learns each player's patterns through Bayesian updating
5. **Serializable**: Complete state fits in <2KB JSONB
6. **Backward compatible**: Exposes the same `composite_score` and `top_vices` interfaces

---

## 2. State Schema at Game Start

### Prior Beliefs

When a new player starts the game, the model is initialized with narrative-anchored priors (see [01-bayesian-fundamentals.md](../research/01-bayesian-fundamentals.md) Section 7):

```python
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

@dataclass
class BayesianPlayerModel:
    """Complete Bayesian state for one player.

    This is the central model that replaces:
    - UserMetrics (db/models/user.py)
    - ViceProfile (engine/vice/models.py)
    - EmotionalStateModel (emotional_state/models.py)
    - SkipDecision state (agents/text/skip.py)
    - ResponseTimer state (agents/text/timing.py)
    """

    user_id: UUID
    chapter: int = 1
    total_messages: int = 0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # --- Relationship Metrics (Beta distributions) ---
    # Each stored as [alpha, beta]
    intimacy: list = field(default_factory=lambda: [1.5, 6.0])
    passion: list = field(default_factory=lambda: [3.0, 3.0])
    trust: list = field(default_factory=lambda: [2.0, 5.0])
    secureness: list = field(default_factory=lambda: [2.0, 3.0])

    # Prior values (for decay regression target)
    intimacy_prior: list = field(default_factory=lambda: [1.5, 6.0])
    passion_prior: list = field(default_factory=lambda: [3.0, 3.0])
    trust_prior: list = field(default_factory=lambda: [2.0, 5.0])
    secureness_prior: list = field(default_factory=lambda: [2.0, 3.0])

    # --- Vice Preferences (Dirichlet distribution) ---
    # 8 concentration parameters, one per vice category
    vice_alphas: list = field(default_factory=lambda: [1.0] * 8)

    # --- Emotional State (HMM belief) ---
    # P(mood) for 6 states: content, playful, anxious, avoidant, defensive, withdrawn
    mood_belief: list = field(default_factory=lambda: [0.40, 0.25, 0.10, 0.10, 0.05, 0.10])

    # --- Skip Decision (Thompson Sampling Beta) ---
    skip_alpha: float = 3.0   # Evidence for skipping
    skip_beta: float = 5.0    # Evidence for responding
    consecutive_skips: int = 0

    # --- Response Timing (Normal posterior) ---
    timing_mu: float = 14700.0      # Expected delay in seconds
    timing_precision: float = 0.0001 # Precision (1/variance)

    # --- Metadata ---
    archetype: str = "unknown"
    schema_version: int = 1
    messages_in_chapter: int = 0

    # =================================================================
    # Metric Access
    # =================================================================

    def metric_mean(self, metric: str) -> float:
        """Get posterior mean for a metric (0-1 scale)."""
        params = getattr(self, metric)
        return params[0] / (params[0] + params[1])

    def metric_variance(self, metric: str) -> float:
        """Get posterior variance for a metric."""
        a, b = getattr(self, metric)
        n = a + b
        return (a * b) / (n ** 2 * (n + 1))

    def metric_strength(self, metric: str) -> float:
        """Get effective sample size (alpha + beta)."""
        params = getattr(self, metric)
        return params[0] + params[1]

    def metric_score(self, metric: str) -> float:
        """Get metric on 0-100 scale (for backward compatibility)."""
        return self.metric_mean(metric) * 100

    @property
    def composite_score(self) -> float:
        """Weighted composite score (0-100 scale).

        Direct replacement for ScoreCalculator.calculate_composite().
        Uses same METRIC_WEIGHTS from engine/constants.py.
        """
        weights = {"intimacy": 0.30, "passion": 0.25, "trust": 0.25, "secureness": 0.20}
        total = sum(self.metric_mean(m) * w for m, w in weights.items())
        return total * 100

    @property
    def top_vices(self) -> list[tuple[str, float]]:
        """Top 3 vice preferences.

        Replacement for ViceScorer.get_top_vices().
        """
        CATEGORIES = [
            "intellectual_dominance", "risk_taking", "substances",
            "sexuality", "emotional_intensity", "rule_breaking",
            "dark_humor", "vulnerability"
        ]
        alphas = np.array(self.vice_alphas)
        probs = alphas / alphas.sum()
        indices = np.argsort(probs)[::-1][:3]
        return [(CATEGORIES[i], float(probs[i])) for i in indices]

    @property
    def current_mood(self) -> str:
        """Most likely mood.

        Replacement for EmotionalStateModel's continuous dimensions.
        """
        MOODS = ["content", "playful", "anxious", "avoidant", "defensive", "withdrawn"]
        return MOODS[np.argmax(self.mood_belief)]

    @property
    def vice_entropy(self) -> float:
        """Vice preference entropy (bits). Max = 3.0 for 8 categories."""
        alphas = np.array(self.vice_alphas)
        p = alphas / alphas.sum()
        return float(-np.sum(p * np.log2(np.clip(p, 1e-10, 1.0))))

    # =================================================================
    # Updates
    # =================================================================

    def update_metric(self, metric: str, positive: bool, weight: float = 0.7) -> None:
        """Update a single metric's Beta distribution.

        Args:
            metric: "intimacy", "passion", "trust", or "secureness"
            positive: True for positive signal, False for negative
            weight: Observation strength (0-1)
        """
        params = getattr(self, metric)
        if positive:
            params[0] += weight
        else:
            params[1] += weight

    def update_vice(self, category_idx: int, weight: float = 0.5) -> None:
        """Update Dirichlet vice preference."""
        if 0 <= category_idx < 8:
            self.vice_alphas[category_idx] += weight

    def update_mood(self, observation_idx: int, A: np.ndarray, B: np.ndarray) -> None:
        """HMM forward step for mood inference.

        Args:
            observation_idx: Index of observed feature
            A: Transition matrix (6x6)
            B: Emission matrix (6x14)
        """
        belief = np.array(self.mood_belief)
        predicted = belief @ A
        updated = predicted * B[:, observation_idx]
        total = updated.sum()
        if total > 0:
            self.mood_belief = (updated / total).tolist()

    def apply_decay(self, hours_elapsed: float) -> None:
        """Apply Bayesian decay (forgetting) to all metrics.

        See doc 09, Section 5 for decay-as-forgetting math.
        """
        rates = {1: 0.008, 2: 0.006, 3: 0.004, 4: 0.003, 5: 0.002}
        grace_hours = {1: 8, 2: 16, 3: 24, 4: 48, 5: 72}

        rate = rates.get(self.chapter, 0.008)
        grace = grace_hours.get(self.chapter, 8)

        if hours_elapsed <= grace:
            return

        effective_hours = hours_elapsed - grace
        factor = np.exp(-rate * effective_hours)

        for metric in ["intimacy", "passion", "trust", "secureness"]:
            params = getattr(self, metric)
            prior = getattr(self, f"{metric}_prior")
            params[0] = prior[0] + (params[0] - prior[0]) * factor
            params[1] = prior[1] + (params[1] - prior[1]) * factor

    def increment_message(self) -> None:
        """Track message count."""
        self.total_messages += 1
        self.messages_in_chapter += 1
        self.last_updated = datetime.now(timezone.utc)

    # =================================================================
    # Serialization
    # =================================================================

    def to_jsonb(self) -> dict:
        """Serialize to compact JSONB format.

        Uses short keys for storage efficiency.
        Total size: ~350-500 bytes.
        """
        return {
            "v": self.schema_version,
            "c": self.chapter,
            "n": self.total_messages,
            "nc": self.messages_in_chapter,
            "u": self.last_updated.isoformat(),
            "a": self.archetype,
            "m": {
                "i": self.intimacy,
                "p": self.passion,
                "t": self.trust,
                "s": self.secureness,
            },
            "mp": {
                "i": self.intimacy_prior,
                "p": self.passion_prior,
                "t": self.trust_prior,
                "s": self.secureness_prior,
            },
            "d": self.vice_alphas,
            "h": self.mood_belief,
            "k": [self.skip_alpha, self.skip_beta, self.consecutive_skips],
            "g": [self.timing_mu, self.timing_precision],
        }

    @classmethod
    def from_jsonb(cls, user_id: UUID, data: dict) -> "BayesianPlayerModel":
        """Restore from compact JSONB."""
        model = cls(user_id=user_id)
        model.schema_version = data.get("v", 1)
        model.chapter = data.get("c", 1)
        model.total_messages = data.get("n", 0)
        model.messages_in_chapter = data.get("nc", 0)
        model.archetype = data.get("a", "unknown")

        if "u" in data:
            model.last_updated = datetime.fromisoformat(data["u"])

        metrics = data.get("m", {})
        model.intimacy = metrics.get("i", [1.5, 6.0])
        model.passion = metrics.get("p", [3.0, 3.0])
        model.trust = metrics.get("t", [2.0, 5.0])
        model.secureness = metrics.get("s", [2.0, 3.0])

        priors = data.get("mp", {})
        model.intimacy_prior = priors.get("i", model.intimacy.copy())
        model.passion_prior = priors.get("p", model.passion.copy())
        model.trust_prior = priors.get("t", model.trust.copy())
        model.secureness_prior = priors.get("s", model.secureness.copy())

        model.vice_alphas = data.get("d", [1.0] * 8)
        model.mood_belief = data.get("h", [0.40, 0.25, 0.10, 0.10, 0.05, 0.10])

        skip = data.get("k", [3.0, 5.0, 0])
        model.skip_alpha = skip[0]
        model.skip_beta = skip[1]
        model.consecutive_skips = int(skip[2])

        timing = data.get("g", [14700.0, 0.0001])
        model.timing_mu = timing[0]
        model.timing_precision = timing[1]

        return model
```

---

## 3. Observation Model: Events to Updates

### The Observation Pipeline

```
Player Message
      │
      v
┌─────────────────────┐
│  Feature Extraction  │  <1ms
│  (5 extractors)      │
├─────────────────────┤
│  1. Message length   │ -> intimacy, passion signals
│  2. Response time    │ -> trust, secureness signals
│  3. Question content │ -> intimacy, trust signals
│  4. Sentiment        │ -> passion, trust signals
│  5. Consistency      │ -> secureness, trust signals
└─────────────────────┘
      │
      v
┌─────────────────────┐
│  Vice Detection      │  <0.5ms
│  (keyword matching)  │
└─────────────────────┘
      │
      v
┌─────────────────────┐
│  HMM Feature Map     │  <0.1ms
│  (msg -> obs index)  │
└─────────────────────┘
      │
      v
┌─────────────────────┐
│  Conflict Resolution │  <0.1ms
│  (when signals clash)│
└─────────────────────┘
      │
      v
┌─────────────────────┐
│  Bayesian Updates    │  <1μs
│  Beta + Dir + HMM    │
└─────────────────────┘
```

### Event-to-Observation Mapping

```python
# Complete mapping of raw events to metric observations
EVENT_OBSERVATION_MAP = {
    # Message content events
    "long_message": [
        ("intimacy", True, 0.5, "Long messages show emotional investment"),
        ("passion", True, 0.3, "Engagement proxy"),
    ],
    "short_message": [
        ("intimacy", False, 0.3, "May indicate disengagement"),
        ("passion", False, 0.15, "Weak negative signal"),
    ],
    "personal_question": [
        ("intimacy", True, 0.7, "Personal questions build closeness"),
        ("trust", True, 0.5, "Asking personal questions requires trust"),
    ],
    "compliment": [
        ("passion", True, 0.6, "Direct positive sentiment"),
        ("intimacy", True, 0.3, "Warmth signal"),
    ],
    "complaint": [
        ("passion", False, 0.5, "Negative sentiment"),
        ("trust", False, 0.4, "Complaints damage trust"),
    ],
    "vulnerability_share": [
        ("trust", True, 0.8, "Strong trust-building signal"),
        ("intimacy", True, 0.7, "Emotional openness"),
    ],
    "humor": [
        ("passion", True, 0.4, "Playful engagement"),
    ],
    "apology": [
        ("trust", True, 0.5, "Accountability builds trust"),
        ("secureness", True, 0.3, "Shows investment in relationship"),
    ],

    # Timing events
    "fast_response": [
        ("trust", True, 0.3, "Responsiveness"),
        ("secureness", True, 0.3, "Availability"),
    ],
    "slow_response": [
        ("secureness", False, 0.4, "Unreliable availability"),
    ],
    "very_slow_response": [
        ("secureness", False, 0.6, "Extended absence"),
        ("trust", False, 0.3, "Inconsistency"),
    ],

    # Behavioral events
    "daily_checkin": [
        ("secureness", True, 0.5, "Regular contact pattern"),
        ("trust", True, 0.2, "Consistency"),
    ],
    "morning_message": [
        ("secureness", True, 0.4, "Thinking about Nikita early"),
        ("intimacy", True, 0.2, "Routine emotional connection"),
    ],
    "night_message": [
        ("intimacy", True, 0.3, "Late-night emotional openness"),
        ("passion", True, 0.2, "Choosing Nikita at night"),
    ],
    "emoji_heavy": [
        ("passion", True, 0.2, "Emotional expression"),
    ],
    "topic_continuation": [
        ("intimacy", True, 0.2, "Investment in conversation depth"),
    ],
    "topic_avoidance": [
        ("trust", False, 0.3, "Avoidance may signal discomfort"),
    ],

    # Special events
    "boss_pass": [
        ("trust", True, 1.0, "Major milestone"),
        ("secureness", True, 0.8, "Proven capability"),
        ("intimacy", True, 0.6, "Relationship deepened"),
        ("passion", True, 0.5, "Excitement of achievement"),
    ],
    "boss_fail": [
        ("trust", False, 0.5, "Failed to meet expectations"),
        ("secureness", False, 0.4, "Instability signal"),
    ],
}
```

---

## 4. Cold-Start Handling

### Three-Tier Cold-Start Strategy

```python
class ColdStartManager:
    """Manages initial model state for new players.

    Tier 1: Narrative priors (always available)
    Tier 2: Archetype priors (from onboarding data)
    Tier 3: Population priors (from user pool, when available)
    """

    # Tier 1: Narrative priors per chapter
    NARRATIVE_PRIORS = {
        1: {  # "Curiosity" — Nikita is skeptical but intrigued
            "intimacy": [1.5, 6.0],    # Mean: 0.20
            "passion": [3.0, 3.0],      # Mean: 0.50
            "trust": [2.0, 5.0],        # Mean: 0.29
            "secureness": [2.0, 3.0],   # Mean: 0.40
        },
    }

    # Tier 2: Archetype adjustments (multiplied onto narrative priors)
    ARCHETYPE_ADJUSTMENTS = {
        "romantic_lead": {
            "passion": [1.5, 0.8],   # Boost passion
            "intimacy": [1.2, 0.9],  # Slight intimacy boost
        },
        "intellectual": {
            "trust": [1.3, 0.9],     # Higher initial trust
            "intimacy": [1.1, 1.0],  # Slight intimacy boost
        },
        "cautious_explorer": {
            "trust": [0.8, 1.2],     # Even more skeptical
            "secureness": [1.3, 0.9], # Higher secureness (consistent type)
        },
        "bold_risk_taker": {
            "passion": [1.5, 0.8],   # High passion
            "trust": [0.8, 1.2],     # Low trust (boundary pusher)
            "secureness": [0.7, 1.3], # Low secureness (unpredictable)
        },
    }

    @classmethod
    def initialize(
        cls,
        user_id: UUID,
        onboarding_data: dict | None = None,
        population_priors: dict | None = None,
    ) -> BayesianPlayerModel:
        """Initialize a new player's Bayesian model.

        Uses the best available cold-start strategy.
        """
        model = BayesianPlayerModel(user_id=user_id)

        # Start with narrative priors (Tier 1)
        priors = cls.NARRATIVE_PRIORS[1]
        for metric, params in priors.items():
            setattr(model, metric, params.copy())
            setattr(model, f"{metric}_prior", params.copy())

        # Apply archetype adjustment if onboarding data available (Tier 2)
        if onboarding_data:
            archetype = cls._classify_archetype(onboarding_data)
            model.archetype = archetype

            adjustments = cls.ARCHETYPE_ADJUSTMENTS.get(archetype, {})
            for metric, (alpha_mult, beta_mult) in adjustments.items():
                params = getattr(model, metric)
                params[0] *= alpha_mult
                params[1] *= beta_mult
                prior = getattr(model, f"{metric}_prior")
                prior[0] = params[0]
                prior[1] = params[1]

        # Blend with population priors if available (Tier 3)
        if population_priors:
            for metric in ["intimacy", "passion", "trust", "secureness"]:
                current = getattr(model, metric)
                pop = population_priors.get(metric, current)
                # 70% narrative/archetype, 30% population
                blended = [
                    0.7 * current[0] + 0.3 * pop[0],
                    0.7 * current[1] + 0.3 * pop[1],
                ]
                setattr(model, metric, blended)
                setattr(model, f"{metric}_prior", blended.copy())

        return model

    @classmethod
    def _classify_archetype(cls, onboarding_data: dict) -> str:
        """Classify player into archetype from onboarding responses."""
        # Simple heuristic (see doc 02 for full implementation)
        msg_len = len(onboarding_data.get("intro_message", ""))
        tone = onboarding_data.get("detected_tone", "neutral")

        if tone == "flirty":
            return "romantic_lead"
        elif tone == "curious" and msg_len > 100:
            return "intellectual"
        elif msg_len < 30:
            return "cautious_explorer"
        elif tone == "intense":
            return "bold_risk_taker"
        return "cautious_explorer"  # Default
```

---

## 5. Full Data Flow

### Message Processing Pipeline

```
[Telegram Message Handler]
         │
         v
[Pipeline Orchestrator: Stage 1-3 (context, memory, retrieval)]
         │
         v
[Stage 4: BAYESIAN UPDATE]  <-- NEW (replaces LLM scoring stage)
    │
    ├── 1. Load BayesianPlayerModel from Supabase (~5ms)
    │       └── Cache hit? Use memory cache (~0ms)
    │
    ├── 2. Calculate time-based decay (~0.1μs)
    │       └── model.apply_decay(hours_since_last)
    │
    ├── 3. Extract observations from message (~12μs)
    │       ├── Message length analysis
    │       ├── Response time analysis
    │       ├── Question detection
    │       ├── Sentiment keywords
    │       ├── Consistency patterns
    │       └── Vice keyword detection
    │
    ├── 4. Apply Bayesian updates (~1μs)
    │       ├── Beta metric updates (4 metrics)
    │       ├── Dirichlet vice update
    │       └── HMM mood step
    │
    ├── 5. Compute derived values (~0.5μs)
    │       ├── Composite score
    │       ├── Boss readiness
    │       ├── Top vices
    │       └── Current mood
    │
    ├── 6. Fallback check (~0.1μs)
    │       └── If variance too high → trigger LLM scoring
    │
    ├── 7. Save state to Supabase (~5ms)
    │       └── Also update memory cache
    │
    └── 8. Return scoring context to pipeline
            ├── composite_score: float
            ├── metric_scores: dict
            ├── top_vices: list
            ├── current_mood: str
            └── skip_decision: bool

[Pipeline Stages 5-9 continue (text generation, delivery, etc.)]
```

---

## 6. Database Schema

### Supabase PostgreSQL Schema

```sql
-- New table for Bayesian player state
CREATE TABLE IF NOT EXISTS user_bayesian_state (
    -- Primary key matching users table
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,

    -- Complete Bayesian state as JSONB
    -- Compact keys: v, c, n, m, d, h, k, g, etc.
    state JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- Schema version for migration support
    version INTEGER NOT NULL DEFAULT 1,

    -- Timestamps for decay scheduling
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Derived columns for efficient queries
    -- (computed from JSONB on write, indexed for read)
    composite_score DECIMAL(5,2) GENERATED ALWAYS AS (
        (
            (state->'m'->'i'->0)::numeric /
            ((state->'m'->'i'->0)::numeric + (state->'m'->'i'->1)::numeric) * 0.30 +
            (state->'m'->'p'->0)::numeric /
            ((state->'m'->'p'->0)::numeric + (state->'m'->'p'->1)::numeric) * 0.25 +
            (state->'m'->'t'->0)::numeric /
            ((state->'m'->'t'->0)::numeric + (state->'m'->'t'->1)::numeric) * 0.25 +
            (state->'m'->'s'->0)::numeric /
            ((state->'m'->'s'->0)::numeric + (state->'m'->'s'->1)::numeric) * 0.20
        ) * 100
    ) STORED,

    chapter INTEGER GENERATED ALWAYS AS (
        (state->>'c')::integer
    ) STORED
);

-- Indexes
CREATE INDEX idx_bstate_updated ON user_bayesian_state (updated_at);
CREATE INDEX idx_bstate_chapter ON user_bayesian_state (chapter);
CREATE INDEX idx_bstate_score ON user_bayesian_state (composite_score);

-- RLS Policy (same as existing user tables)
ALTER TABLE user_bayesian_state ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own state"
    ON user_bayesian_state FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage all states"
    ON user_bayesian_state FOR ALL
    USING (auth.role() = 'service_role');
```

### Note on Generated Columns

The `composite_score` generated column is computed from the JSONB on write, allowing efficient SQL queries like:

```sql
-- Find users ready for boss encounter in their chapter
SELECT user_id, composite_score, chapter
FROM user_bayesian_state
WHERE (chapter = 1 AND composite_score >= 55)
   OR (chapter = 2 AND composite_score >= 60)
   OR (chapter = 3 AND composite_score >= 65);

-- Find users needing decay (inactive > grace period)
SELECT user_id, updated_at, chapter
FROM user_bayesian_state
WHERE updated_at < NOW() - INTERVAL '8 hours'  -- Min grace period
ORDER BY updated_at ASC
LIMIT 100;
```

---

## 7. Migration Plan from Current Storage

### Step 1: Create Bayesian State Table

```sql
-- Migration: Create bayesian state alongside existing metrics
-- (both tables coexist during migration period)

CREATE TABLE user_bayesian_state (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    state JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INTEGER NOT NULL DEFAULT 1,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Step 2: Backfill from Existing Data

```python
async def migrate_existing_user(
    session,
    user_id: UUID,
    current_metrics: dict,
    vice_profile: dict,
    chapter: int,
) -> BayesianPlayerModel:
    """Convert existing user data to Bayesian model.

    Maps current flat metric values to Beta distributions
    with appropriate strength based on message history.
    """
    model = BayesianPlayerModel(user_id=user_id, chapter=chapter)

    # Estimate strength from user's game age
    # More messages = higher strength (more evidence accumulated)
    estimated_messages = current_metrics.get("message_count", 20)
    base_strength = min(30.0, estimated_messages * 0.5 + 4.0)

    for metric in ["intimacy", "passion", "trust", "secureness"]:
        current_value = float(current_metrics.get(metric, 50)) / 100  # Normalize to [0,1]

        # Convert point value to Beta parameters with estimated strength
        alpha = current_value * base_strength
        beta_val = (1 - current_value) * base_strength

        # Enforce minimums
        alpha = max(1.0, alpha)
        beta_val = max(1.0, beta_val)

        setattr(model, metric, [alpha, beta_val])

        # Set prior based on chapter
        priors = ColdStartManager.NARRATIVE_PRIORS.get(1, {})
        prior = priors.get(metric, [2.0, 3.0])
        setattr(model, f"{metric}_prior", prior.copy())

    # Migrate vice profile
    if vice_profile:
        for i, category in enumerate(BayesianPlayerModel.VICE_CATEGORIES):
            score = vice_profile.get(category, 0.0)
            # Convert 0-1 score to Dirichlet alpha
            model.vice_alphas[i] = 1.0 + score * 5.0

    model.total_messages = estimated_messages
    return model
```

### Step 3: Shadow Mode Operation

```python
# In pipeline orchestrator, add shadow Bayesian processing
async def process_message_with_shadow(self, message, context):
    # Existing LLM scoring (source of truth)
    llm_result = await self.llm_score(message, context)

    # Shadow Bayesian scoring (for comparison)
    try:
        bayesian_result = await self.bayesian_score(message, context)
        await self.log_comparison(llm_result, bayesian_result)
    except Exception as e:
        logger.warning(f"Shadow Bayesian scoring failed: {e}")

    return llm_result  # LLM remains source of truth
```

### Step 4: Cutover

After validation in shadow mode (1-2 weeks), switch primary scoring:

```python
# Config flag for gradual rollout
BAYESIAN_ENABLED = settings.feature_flags.get("bayesian_scoring", False)
BAYESIAN_WEIGHT = settings.feature_flags.get("bayesian_weight", 0.0)  # 0-1

async def score_message(self, message, context):
    if not BAYESIAN_ENABLED:
        return await self.llm_score(message, context)

    if BAYESIAN_WEIGHT >= 1.0:
        # Full Bayesian with fallback
        result = await self.bayesian_score(message, context)
        if result.needs_fallback:
            return await self.llm_score(message, context)
        return result

    # Blended mode
    llm = await self.llm_score(message, context)
    bayesian = await self.bayesian_score(message, context)
    return self.blend(llm, bayesian, BAYESIAN_WEIGHT)
```

---

## 8. Integration with 9-Stage Pipeline

### Current Pipeline Stages (from `pipeline/orchestrator.py`)

The pipeline has 9 stages. The Bayesian model integrates at Stage 4 (scoring) and Stage 6 (vice processing):

```python
# Stage mapping for Bayesian integration
PIPELINE_INTEGRATION = {
    "stage_1": "Context loading — no change",
    "stage_2": "Memory retrieval — no change",
    "stage_3": "History assembly — no change",
    "stage_4": "SCORING — Replace LLM scoring with Bayesian update",
    "stage_5": "Text generation — use Bayesian mood for prompt injection",
    "stage_6": "VICE — Replace LLM vice analysis with Dirichlet",
    "stage_7": "Skip decision — Replace random with Thompson Sampling",
    "stage_8": "Response timing — Replace Gaussian with posterior sampling",
    "stage_9": "Delivery — no change",
}
```

### Stage 4 Replacement

```python
class BayesianScoringStage:
    """Replaces the LLM-based scoring stage in the pipeline.

    Current stage 4: LLM call -> ResponseAnalysis -> MetricDeltas
    New stage 4: ObservationEncoder -> Beta updates -> composite score

    Interface is backward-compatible: returns the same ScoreResult
    dataclass that downstream stages expect.
    """

    def __init__(self):
        self.encoder = ObservationEncoder()
        self.fallback_manager = FallbackManager()

    async def process(
        self,
        message: str,
        model: BayesianPlayerModel,
        context: dict,
    ) -> "ScoreResult":
        """Process scoring for a single message.

        Fully replaces ScoreCalculator.calculate() for 97% of messages.
        Falls back to LLM scoring for the remaining 3%.
        """
        from nikita.engine.scoring.calculator import ScoreResult
        from nikita.engine.scoring.models import MetricDeltas

        score_before = model.composite_score
        metrics_before = {m: model.metric_score(m) for m in
                         ["intimacy", "passion", "trust", "secureness"]}

        # Extract observations
        observations = self.encoder.encode_message(
            message=message,
            chapter=model.chapter,
            response_time_seconds=context.get("response_time_seconds", 0),
            time_since_last_hours=context.get("time_since_last_hours", 0),
            messages_today=context.get("messages_today", 0),
        )

        # Check fallback
        should_fallback, reason = self.fallback_manager.should_fallback_to_llm(
            metrics={m: type('', (), {
                'variance': model.metric_variance(m)
            })() for m in ["intimacy", "passion", "trust", "secureness"]},
            total_messages=model.total_messages,
            composite_score=score_before,
            chapter=model.chapter,
            observation_count=len(observations),
        )

        if should_fallback:
            # Delegate to LLM (expensive but accurate)
            return await self._llm_fallback(message, model, context, reason)

        # Apply Bayesian updates
        deltas = {"intimacy": 0.0, "passion": 0.0, "trust": 0.0, "secureness": 0.0}
        for obs in observations:
            effective_weight = obs.weight * obs.confidence
            model.update_metric(obs.metric, obs.positive, effective_weight)
            delta_sign = 1.0 if obs.positive else -1.0
            deltas[obs.metric] += delta_sign * effective_weight * 10  # Scale to match [-10, 10]

        model.increment_message()
        score_after = model.composite_score
        metrics_after = {m: model.metric_score(m) for m in
                        ["intimacy", "passion", "trust", "secureness"]}

        # Build backward-compatible ScoreResult
        return ScoreResult(
            score_before=score_before,
            score_after=score_after,
            metrics_before=metrics_before,
            metrics_after=metrics_after,
            deltas_applied=MetricDeltas(
                intimacy=max(-10, min(10, deltas["intimacy"])),
                passion=max(-10, min(10, deltas["passion"])),
                trust=max(-10, min(10, deltas["trust"])),
                secureness=max(-10, min(10, deltas["secureness"])),
            ),
            multiplier_applied=1.0,
            engagement_state="in_zone",
            events=self._detect_events(score_before, score_after, model.chapter),
        )
```

---

## 9. Chapter Transitions

### Softened Prior Transfer

When a player advances to a new chapter, the posterior from the current chapter becomes the prior for the next — but with softening to add appropriate uncertainty:

```python
def transition_chapter(model: BayesianPlayerModel, new_chapter: int) -> None:
    """Transition player model to a new chapter.

    The posterior becomes the prior, but with reduced strength
    to account for changing relationship dynamics.

    Softening factors per metric:
    - Trust: 0.85 (mostly preserved — trust carries over)
    - Secureness: 0.80 (mostly preserved — consistency carries)
    - Passion: 0.70 (partially reset — new chapter, new energy)
    - Intimacy: 0.75 (partially reset — deeper levels unlocked)
    """
    SOFTENING = {
        "trust": 0.85,
        "secureness": 0.80,
        "passion": 0.70,
        "intimacy": 0.75,
    }

    for metric in ["intimacy", "passion", "trust", "secureness"]:
        params = getattr(model, metric)
        factor = SOFTENING[metric]

        # Reduce strength while preserving proportion
        new_alpha = 1.0 + (params[0] - 1.0) * factor
        new_beta = 1.0 + (params[1] - 1.0) * factor

        setattr(model, metric, [new_alpha, new_beta])
        setattr(model, f"{metric}_prior", [new_alpha, new_beta])

    # Update chapter and reset chapter-local counters
    model.chapter = new_chapter
    model.messages_in_chapter = 0

    # Update skip/timing priors for new chapter
    chapter_skip = {1: (3.0, 5.0), 2: (2.0, 5.0), 3: (1.5, 6.0),
                    4: (1.2, 8.0), 5: (1.1, 10.0)}
    model.skip_alpha, model.skip_beta = chapter_skip.get(new_chapter, (2.0, 5.0))
    model.consecutive_skips = 0

    chapter_timing = {1: 14700, 2: 7350, 3: 3750, 4: 1950, 5: 1050}
    model.timing_mu = chapter_timing.get(new_chapter, 14700)
    model.timing_precision = 0.0001  # Reset precision for new chapter dynamics
```

---

## 10. Boss Encounter Integration

### Probabilistic Boss Readiness

```python
def boss_readiness(model: BayesianPlayerModel) -> dict:
    """Assess boss readiness with uncertainty quantification.

    Instead of just "score >= threshold", this returns the
    probability that the player's TRUE score meets the threshold.
    """
    THRESHOLDS = {1: 55, 2: 60, 3: 65, 4: 70, 5: 75}
    threshold = THRESHOLDS.get(model.chapter, 55) / 100  # Normalize

    weights = {"intimacy": 0.30, "passion": 0.25, "trust": 0.25, "secureness": 0.20}

    # Monte Carlo estimation
    n_samples = 10000
    composites = np.zeros(n_samples)

    for metric, weight in weights.items():
        params = getattr(model, metric)
        samples = np.random.beta(params[0], params[1], size=n_samples)
        composites += samples * weight

    p_ready = float(np.mean(composites >= threshold))
    composite_mean = float(np.mean(composites)) * 100

    return {
        "composite_score": composite_mean,
        "threshold": THRESHOLDS[model.chapter],
        "p_ready": p_ready,
        "ready": p_ready > 0.7,  # 70% probability required
        "confidence": "high" if p_ready > 0.9 or p_ready < 0.1 else
                      "medium" if p_ready > 0.6 or p_ready < 0.3 else "low",
    }
```

---

## 11. Complete Implementation

### The Full Pipeline Integration

```python
class BayesianPipelineProcessor:
    """Complete Bayesian processing for one message.

    This is the top-level integration that replaces multiple
    LLM-based stages in the pipeline with a single Bayesian pass.
    """

    def __init__(self):
        self.encoder = ObservationEncoder()
        self.fallback = FallbackManager()
        self.hmm_A = np.array(DEFAULT_HMM_A)
        self.hmm_B = build_emission_matrix()

    async def process(
        self,
        user_id: UUID,
        message: str,
        context: dict,
        session,  # Supabase session
    ) -> dict:
        """Full Bayesian processing pipeline.

        Replaces: scoring LLM call + vice LLM call + skip decision + timing

        Total latency: <1ms (excluding DB I/O)
        Total tokens: 0 (unless fallback triggered)
        """
        # 1. Load state
        model = await self._load_model(session, user_id)

        # 2. Apply decay
        hours = context.get("hours_since_last_message", 0)
        if hours > 0:
            model.apply_decay(hours)

        # 3. Encode observations
        observations = self.encoder.encode_message(
            message=message,
            chapter=model.chapter,
            response_time_seconds=context.get("response_time_seconds", 0),
            time_since_last_hours=hours,
            messages_today=context.get("messages_today", 0),
        )

        # 4. Vice detection
        vice_signals = self._detect_vices(message)

        # 5. HMM mood update
        hmm_obs = self._map_to_hmm_observation(message, context)
        model.update_mood(hmm_obs, self.hmm_A, self.hmm_B)

        # 6. Apply metric updates
        for obs in observations:
            model.update_metric(obs.metric, obs.positive, obs.weight * obs.confidence)

        # 7. Apply vice updates
        for cat_idx, weight in vice_signals:
            model.update_vice(cat_idx, weight)

        # 8. Skip decision (Thompson Sampling)
        skip_sample = np.random.beta(model.skip_alpha, model.skip_beta)
        should_skip = skip_sample > 0.5 and model.consecutive_skips < 2
        if should_skip:
            model.consecutive_skips += 1
        else:
            model.consecutive_skips = 0

        # 9. Timing decision (posterior predictive)
        delay = max(60, np.random.normal(model.timing_mu, 1/np.sqrt(model.timing_precision)))

        # 10. Increment and save
        model.increment_message()
        await self._save_model(session, model)

        # 11. Return results
        return {
            "composite_score": model.composite_score,
            "metric_scores": {
                m: model.metric_score(m) for m in ["intimacy", "passion", "trust", "secureness"]
            },
            "top_vices": model.top_vices,
            "current_mood": model.current_mood,
            "mood_probabilities": dict(zip(
                ["content", "playful", "anxious", "avoidant", "defensive", "withdrawn"],
                model.mood_belief
            )),
            "should_skip": should_skip,
            "response_delay_seconds": int(delay),
            "vice_entropy": model.vice_entropy,
            "total_messages": model.total_messages,
            "boss_readiness": boss_readiness(model),
        }

    async def _load_model(self, session, user_id: UUID) -> BayesianPlayerModel:
        """Load or initialize player model."""
        result = await session.table("user_bayesian_state") \
            .select("state") \
            .eq("user_id", str(user_id)) \
            .single() \
            .execute()

        if result.data:
            return BayesianPlayerModel.from_jsonb(user_id, result.data["state"])

        # New player — initialize with cold-start priors
        return ColdStartManager.initialize(user_id)

    async def _save_model(self, session, model: BayesianPlayerModel) -> None:
        """Persist model state."""
        await session.table("user_bayesian_state") \
            .upsert({
                "user_id": str(model.user_id),
                "state": model.to_jsonb(),
                "version": model.schema_version,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }) \
            .execute()

    def _detect_vices(self, message: str) -> list[tuple[int, float]]:
        """Keyword-based vice detection (from doc 09)."""
        # ... (implementation from doc 09, Section 4)
        pass

    def _map_to_hmm_observation(self, message: str, context: dict) -> int:
        """Map message features to HMM observation index (from doc 04)."""
        # ... (implementation from doc 04, Section 4)
        return 0
```

---

## 12. Key Takeaways for Nikita

### 1. The BayesianPlayerModel is a single, unified state object

It replaces UserMetrics, ViceProfile, EmotionalStateModel, SkipDecision state, and ResponseTimer state with one coherent model stored in one JSONB column. This eliminates the scattered state problem and ensures all player state is consistent.

### 2. The observation model is the bridge between messages and math

Five lightweight feature extractors (message length, response time, questions, sentiment, consistency) convert raw messages into metric observations. Vice detection uses keyword matching. The HMM maps features to mood observations. Total encoding cost: <15 microseconds.

### 3. Cold-start is handled by a three-tier strategy

Narrative priors (always available) encode game design. Archetype classification (from onboarding) personalizes priors. Population pooling (from user data) provides empirical Bayes optimization. Every new player gets a reasonable experience from their first message.

### 4. The migration path is zero-risk

Shadow mode -> blended scoring -> full Bayesian with fallback. The Bayesian system runs in parallel during validation. The existing LLM scoring can be restored instantly via a feature flag. Total cost of running shadow mode: <1ms additional latency per message (the Bayesian pipeline is essentially free).

### 5. Boss readiness becomes probabilistic

Instead of "score >= 55", the system computes P(true_score >= threshold). A 70% probability threshold prevents premature boss triggers when the model is uncertain. This is more robust than the current deterministic approach.

### 6. Everything fits in the existing pipeline

The `BayesianPipelineProcessor` produces the same output format as the current scoring stages. Downstream stages (text generation, vice injection, delivery) see no difference. The integration is a drop-in replacement at the pipeline stage level.

---

> **See also**: [18-bayesian-vice-discovery.md](./18-bayesian-vice-discovery.md) for the complete vice discovery system built on this player model.
> **Research basis**: [01](../research/01-bayesian-fundamentals.md), [02](../research/02-patient-modeling.md), [09](../research/09-beta-dirichlet-modeling.md), [10](../research/10-efficient-inference.md)

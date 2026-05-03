# 29 — Reactive Priors: Inline Bayesian Modulation

**Series**: Bayesian Inference for AI Companions — Simplified Track
**Date**: 2026-02-17
**Inputs**: Doc 22 (ML Engineer), Doc 23 (Cost Evaluator), Doc 24 (Integrated Architecture)
**Status**: DESIGN — Practical implementation blueprint

---

## 1. Executive Summary

### What "Reactive Priors" Means

Every probability draw in the Nikita codebase — touchpoint initiation rates, response timing, skip decisions, silence rates, mood baselines — is currently a `random.uniform()` or `random.gauss()` call bounded by hardcoded chapter configs. These draws are _uninformed_: a Chapter 3 user who loves morning messages gets the same 25-30% initiation rate as one who ignores them.

Reactive Priors replaces these blind draws with **Beta posterior samples**. Each user accumulates a small set of Beta distributions (max 6) that encode observed behavioral patterns. When the system needs a probability — "should I message this user?" — it draws from the user's posterior instead of the chapter default.

### Why Inline Beats a Separate Engine

Doc 24 proposed a full Bayesian Pre-Stage inserted before the 9-stage pipeline. That design is sound but heavyweight: it introduces a new processing step, new state machine, and HMM transitions.

The Reactive Priors approach is different:

1. **No new pipeline stage** — posteriors are injected directly into existing probability draws
2. **No state machine** — just 4-6 Beta distributions per user, stored as `(alpha, beta)` pairs
3. **No feature extraction** — updates happen at natural trigger points (message received, score computed, touchpoint delivered)
4. **Graceful degradation built-in** — every integration point has the same pattern: `if user_state exists, sample posterior; else, use hardcoded fallback`

The key insight: the codebase _already_ makes probabilistic decisions at ~8 points. We just need to make those decisions _informed_.

---

## 2. Integration Map

Every random draw in the codebase, mapped to its replacement:

| # | File | Line | Current Draw | Beta Distribution | Priority |
|---|------|------|-------------|-------------------|----------|
| 1 | `touchpoints/scheduler.py` | 326-335 | `random.uniform(min, max)` | `touchpoint_propensity` | P0 |
| 2 | `touchpoints/scheduler.py` | 337-346 | `random.random() < prob` | (uses #1 output) | P0 |
| 3 | `agents/text/timing.py` | 98-106 | `random.gauss(mean, std)` | `response_speed` | P0 |
| 4 | `agents/text/skip.py` | 71-82 | `random.uniform(min, max)` | `skip_propensity` | P1 |
| 5 | `touchpoints/silence.py` | 124-132 | `base_rate * modifier` | `silence_propensity` | P1 |
| 6 | `life_simulation/event_generator.py` | 177-233 | LLM prompt (valence bias) | `mood_baseline` | P2 |
| 7 | `life_simulation/mood_calculator.py` | 99-103 | Hardcoded `0.5` base | `mood_baseline` | P2 |
| 8 | `touchpoints/scheduler.py` | 244-249 | `base_rate * importance` | (uses #1 output) | P0 |

**Priority Key**: P0 = Phase 1 (ship first), P1 = Phase 1b (same sprint), P2 = Phase 2 (after validation)

---

## 3. The Beta Distributions (6 Max)

### 3.1 Design Principle

Each Beta encodes a **single behavioral dimension** as a probability between 0 and 1. The Beta distribution is the conjugate prior for Bernoulli observations, which means updating is a single addition: observe success, add 1 to alpha; observe failure, add 1 to beta.

```python
# The entire update logic for a Beta distribution
def update_beta(alpha: float, beta: float, success: bool, weight: float = 1.0) -> tuple[float, float]:
    """Update Beta posterior with weighted observation.

    Args:
        alpha: Current alpha (pseudo-count of successes).
        beta: Current beta (pseudo-count of failures).
        success: Whether this observation is a "success".
        weight: Observation weight (0.0-1.0). From ScoreAnalyzer confidence.

    Returns:
        Updated (alpha, beta) tuple.
    """
    if success:
        return (alpha + weight, beta)
    else:
        return (alpha, beta + weight)
```

### 3.2 The Six Distributions

| # | Name | Prior (alpha, beta) | Mean | What It Encodes | Success Signal | Failure Signal |
|---|------|-------------------|------|-----------------|---------------|---------------|
| 1 | `touchpoint_propensity` | (3, 17) | 0.15 | How likely this user responds to touchpoints | User replies to touchpoint within 4h | User ignores touchpoint (no reply in 8h) |
| 2 | `response_speed` | (5, 5) | 0.50 | Preferred response speed (0=slow, 1=fast) | User responds quickly (<5min) after Nikita | User takes long to respond (>2h) |
| 3 | `skip_propensity` | (1, 19) | 0.05 | Whether skipping messages increases engagement | Score goes UP after a skip period | Score goes DOWN after a skip period |
| 4 | `silence_propensity` | (2, 18) | 0.10 | Whether strategic silence helps with this user | User re-engages after silence (sends message) | User disengages further after silence |
| 5 | `mood_baseline` | (10, 10) | 0.50 | User's observed mood center (valence-like) | Positive interaction (score delta > 0) | Negative interaction (score delta < 0) |
| 6 | `engagement_rhythm` | (5, 5) | 0.50 | Morning vs evening preference (0=morning, 1=evening) | User active in evening slot (19:00-21:00) | User active in morning slot (08:00-10:00) |

### 3.3 Why These Priors

The prior hyperparameters are set to match existing hardcoded defaults:

- **`touchpoint_propensity`**: Prior mean 0.15 matches `CHAPTER_CONFIGS[1].initiation_rate_min = 0.15`. The (3, 17) prior is "worth" 20 observations — it takes ~20 real interactions to shift the posterior away from the default. This is intentionally conservative.

- **`response_speed`**: Prior (5, 5) is uninformative — 50/50. Early in the relationship we don't know if the user prefers fast or slow responses. The posterior learns from observed response latencies.

- **`skip_propensity`**: Prior (1, 19) = 5% is very low because `SKIP_RATES` are currently all 0.0 (disabled). The Beta lets skip behavior emerge organically from data rather than being hardcoded on or off.

- **`silence_propensity`**: Prior (2, 18) = 10% matches `StrategicSilence.DEFAULT_RATES[1] = 0.10` for Chapter 1.

- **`mood_baseline`**: Prior (10, 10) = neutral 0.5 matches `MoodState()` defaults. Higher pseudo-counts mean the mood baseline is stable — it takes many events to shift it.

- **`engagement_rhythm`**: Prior (5, 5) = uninformative. No assumption about morning vs evening preference.

### 3.4 Chapter-Aware Prior Initialization

New users start with chapter-derived priors, not the flat defaults above. The initialization function reads from `CHAPTER_CONFIGS` and `TIMING_RANGES`:

```python
# nikita/bayesian/state.py

from nikita.touchpoints.models import CHAPTER_CONFIGS
from nikita.agents.text.timing import TIMING_RANGES

def get_chapter_priors(chapter: int) -> dict[str, tuple[float, float]]:
    """Get Beta distribution priors calibrated to chapter defaults.

    Maps existing hardcoded configs to Beta hyperparameters.
    Prior "strength" (alpha + beta) = 20 for all distributions,
    meaning ~20 observations to equal the prior's influence.

    Args:
        chapter: User's current chapter (1-5).

    Returns:
        Dict mapping distribution name to (alpha, beta) prior.
    """
    config = CHAPTER_CONFIGS.get(chapter, CHAPTER_CONFIGS[1])
    timing = TIMING_RANGES.get(chapter, TIMING_RANGES[1])

    # Touchpoint propensity: map initiation rate range midpoint to Beta
    rate_mid = (config.initiation_rate_min + config.initiation_rate_max) / 2
    tp_alpha = rate_mid * 20
    tp_beta = (1 - rate_mid) * 20

    # Response speed: map timing range to 0-1 scale
    # Faster chapters (smaller range) -> higher speed prior
    min_sec, max_sec = timing
    max_possible = 28800  # Ch1 max (8h)
    speed_mean = 1.0 - (max_sec / max_possible)  # Invert: fast = high
    speed_mean = max(0.1, min(0.9, speed_mean))  # Clamp to avoid edge cases
    sp_alpha = speed_mean * 10
    sp_beta = (1 - speed_mean) * 10

    # Silence propensity: map strategic_silence_rate to Beta
    silence_rate = config.strategic_silence_rate
    si_alpha = silence_rate * 20
    si_beta = (1 - silence_rate) * 20

    return {
        "touchpoint_propensity": (round(tp_alpha, 1), round(tp_beta, 1)),
        "response_speed": (round(sp_alpha, 1), round(sp_beta, 1)),
        "skip_propensity": (1.0, 19.0),  # Always start low (currently disabled)
        "silence_propensity": (round(si_alpha, 1), round(si_beta, 1)),
        "mood_baseline": (10.0, 10.0),  # Always neutral start
        "engagement_rhythm": (5.0, 5.0),  # Always uninformative start
    }
```

**Example outputs**:

| Chapter | `touchpoint_propensity` | `response_speed` | `silence_propensity` |
|---------|------------------------|-------------------|---------------------|
| 1 | (3.5, 16.5) | (1.0, 9.0) | (4.0, 16.0) |
| 3 | (5.5, 14.5) | (7.5, 2.5) | (2.0, 18.0) |
| 5 | (5.5, 14.5) | (9.4, 0.6) | (2.0, 18.0) |

---

## 4. Before/After Code Diffs

### 4.1 BayesianState Model

First, the shared state model that all integration points consume:

```python
# nikita/bayesian/state.py

from dataclasses import dataclass, field
from typing import Optional
import numpy as np


@dataclass
class BayesianState:
    """Per-user Bayesian state: 6 Beta distributions as (alpha, beta) pairs.

    Stored as JSONB on users table. Loaded once per request cycle,
    updated at natural trigger points, written back at end of cycle.

    All fields are Optional — None means "use hardcoded fallback".
    """
    touchpoint_propensity: Optional[tuple[float, float]] = None
    response_speed: Optional[tuple[float, float]] = None
    skip_propensity: Optional[tuple[float, float]] = None
    silence_propensity: Optional[tuple[float, float]] = None
    mood_baseline: Optional[tuple[float, float]] = None
    engagement_rhythm: Optional[tuple[float, float]] = None

    # Metadata
    observation_count: int = 0
    last_updated: Optional[str] = None  # ISO timestamp

    def sample(self, name: str) -> Optional[float]:
        """Draw a single sample from a named Beta distribution.

        Args:
            name: Distribution name (e.g., "touchpoint_propensity").

        Returns:
            Sample in [0, 1], or None if distribution not initialized.
        """
        params = getattr(self, name, None)
        if params is None:
            return None
        alpha, beta = params
        return float(np.random.beta(alpha, beta))

    def mean(self, name: str) -> Optional[float]:
        """Get the posterior mean for a named distribution.

        Args:
            name: Distribution name.

        Returns:
            Mean = alpha / (alpha + beta), or None.
        """
        params = getattr(self, name, None)
        if params is None:
            return None
        alpha, beta = params
        return alpha / (alpha + beta)

    def confidence(self, name: str) -> Optional[float]:
        """Get confidence level (inverse variance proxy).

        Higher alpha + beta = more observations = more confidence.
        Returns value in [0, 1] where 1.0 means very confident.

        Args:
            name: Distribution name.

        Returns:
            Confidence score, or None.
        """
        params = getattr(self, name, None)
        if params is None:
            return None
        alpha, beta = params
        n = alpha + beta
        # Sigmoid-like: 20 observations -> 0.5, 100 -> 0.83, 200 -> 0.91
        return n / (n + 20)

    def to_jsonb(self) -> dict:
        """Serialize to JSONB-compatible dict for Supabase storage."""
        return {
            "touchpoint_propensity": list(self.touchpoint_propensity) if self.touchpoint_propensity else None,
            "response_speed": list(self.response_speed) if self.response_speed else None,
            "skip_propensity": list(self.skip_propensity) if self.skip_propensity else None,
            "silence_propensity": list(self.silence_propensity) if self.silence_propensity else None,
            "mood_baseline": list(self.mood_baseline) if self.mood_baseline else None,
            "engagement_rhythm": list(self.engagement_rhythm) if self.engagement_rhythm else None,
            "observation_count": self.observation_count,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_jsonb(cls, data: dict | None) -> Optional["BayesianState"]:
        """Deserialize from JSONB dict. Returns None if data is None/empty."""
        if not data:
            return None
        return cls(
            touchpoint_propensity=tuple(data["touchpoint_propensity"]) if data.get("touchpoint_propensity") else None,
            response_speed=tuple(data["response_speed"]) if data.get("response_speed") else None,
            skip_propensity=tuple(data["skip_propensity"]) if data.get("skip_propensity") else None,
            silence_propensity=tuple(data["silence_propensity"]) if data.get("silence_propensity") else None,
            mood_baseline=tuple(data["mood_baseline"]) if data.get("mood_baseline") else None,
            engagement_rhythm=tuple(data["engagement_rhythm"]) if data.get("engagement_rhythm") else None,
            observation_count=data.get("observation_count", 0),
            last_updated=data.get("last_updated"),
        )
```

### 4.2 Touchpoint Scheduler (P0 — Primary Integration)

**File**: `nikita/touchpoints/scheduler.py`

```python
# BEFORE (scheduler.py:326-335)
def _get_initiation_rate(self, config: TouchpointConfig) -> float:
    """Get random initiation rate within config bounds."""
    return random.uniform(config.initiation_rate_min, config.initiation_rate_max)

# AFTER
def _get_initiation_rate(
    self, config: TouchpointConfig, user_state: BayesianState | None = None
) -> float:
    """Get initiation rate — posterior-informed if available, else config bounds.

    When a BayesianState is provided, samples from the user's touchpoint_propensity
    Beta distribution. The sample is clamped to [config.min * 0.5, config.max * 2.0]
    to prevent extreme behavior even with strong posteriors.
    """
    if user_state:
        sample = user_state.sample("touchpoint_propensity")
        if sample is not None:
            # Clamp to reasonable range (half min to double max)
            floor = config.initiation_rate_min * 0.5
            ceiling = min(config.initiation_rate_max * 2.0, 0.6)
            return max(floor, min(ceiling, sample))
    return random.uniform(config.initiation_rate_min, config.initiation_rate_max)
```

```python
# BEFORE (scheduler.py:337-346)
def _should_trigger(self, probability: float) -> bool:
    """Probabilistic trigger decision."""
    return random.random() < probability

# AFTER — no change needed
# _should_trigger stays the same. The probability it receives is now
# posterior-informed because _get_initiation_rate returns a posterior sample.
# This is the beauty of inline modulation: downstream code is unaware.
```

**Caller change** — the `evaluate_user` and related methods need to pass `user_state` through:

```python
# BEFORE (scheduler.py:173)
rate = self._get_initiation_rate(config)

# AFTER (scheduler.py:173)
rate = self._get_initiation_rate(config, user_state=user_state)
```

The `evaluate_user` method signature gains an optional parameter:

```python
# BEFORE (scheduler.py:56-64)
def evaluate_user(
    self,
    user_id: UUID,
    chapter: int,
    user_timezone: str = "UTC",
    last_interaction_at: datetime | None = None,
    current_time: datetime | None = None,
    recent_touchpoints: list[ScheduledTouchpoint] | None = None,
) -> list[TriggerContext]:

# AFTER
def evaluate_user(
    self,
    user_id: UUID,
    chapter: int,
    user_timezone: str = "UTC",
    last_interaction_at: datetime | None = None,
    current_time: datetime | None = None,
    recent_touchpoints: list[ScheduledTouchpoint] | None = None,
    user_state: BayesianState | None = None,  # NEW — optional, graceful degradation
) -> list[TriggerContext]:
```

### 4.3 Response Timing (P0)

**File**: `nikita/agents/text/timing.py`

```python
# BEFORE (timing.py:94-106)
# Get timing range for chapter (default to Ch1 if invalid)
min_sec, max_sec = TIMING_RANGES.get(chapter, DEFAULT_TIMING_RANGE)

# Calculate gaussian parameters
# Mean is the midpoint of the range
mean = (min_sec + max_sec) / 2

# Standard deviation: set so ~99% of values fall within range
range_size = max_sec - min_sec
std_dev = range_size / 5

# Generate gaussian-distributed delay
delay = random.gauss(mean, std_dev)

# AFTER
min_sec, max_sec = TIMING_RANGES.get(chapter, DEFAULT_TIMING_RANGE)
range_size = max_sec - min_sec

# Default mean is midpoint
mean = (min_sec + max_sec) / 2

# If Bayesian state available, shift mean based on response_speed posterior
if user_state:
    speed_sample = user_state.sample("response_speed")
    if speed_sample is not None:
        # speed_sample is 0-1 where 1 = fast.
        # Map to position within timing range: 1.0 -> min_sec, 0.0 -> max_sec
        mean = max_sec - speed_sample * range_size
        # Narrow std_dev as confidence grows (more observations = tighter distribution)
        confidence = user_state.confidence("response_speed") or 0.0
        # Base std_dev = range/5. With high confidence, narrow to range/10.
        narrowing = 1.0 - (confidence * 0.5)  # 1.0 -> 0.5 as confidence grows
        std_dev = (range_size / 5) * narrowing
    else:
        std_dev = range_size / 5
else:
    std_dev = range_size / 5

delay = random.gauss(mean, std_dev)
```

The `calculate_delay` method signature change:

```python
# BEFORE (timing.py:67)
def calculate_delay(self, chapter: int) -> int:

# AFTER
def calculate_delay(self, chapter: int, user_state: BayesianState | None = None) -> int:
```

### 4.4 Skip Decision (P1)

**File**: `nikita/agents/text/skip.py`

```python
# BEFORE (skip.py:71-82)
# Get skip rate range for chapter (default to Ch1 if invalid)
min_rate, max_rate = SKIP_RATES.get(chapter, DEFAULT_SKIP_RATE)

# Pick a random skip probability within the range
skip_probability = random.uniform(min_rate, max_rate)

# AFTER
min_rate, max_rate = SKIP_RATES.get(chapter, DEFAULT_SKIP_RATE)

if user_state:
    sample = user_state.sample("skip_propensity")
    if sample is not None:
        # Use posterior sample, clamped to [0, 0.3] to prevent excessive skipping
        skip_probability = min(sample, 0.3)
    else:
        skip_probability = random.uniform(min_rate, max_rate)
else:
    skip_probability = random.uniform(min_rate, max_rate)
```

This is the most interesting integration because `SKIP_RATES` are currently all 0.0 (disabled). The Beta prior starts at (1, 19) = 5% — very low but _not zero_. If the system observes that scores go up after Nikita skips a message (e.g., the user re-engages more enthusiastically), the posterior will slowly creep upward, organically enabling skip behavior for users who respond well to it. For users who disengage after skips, the posterior stays near zero.

### 4.5 Strategic Silence (P1)

**File**: `nikita/touchpoints/silence.py`

```python
# BEFORE (silence.py:123-127)
# Get base rate for chapter
base_rate = self.base_rates.get(chapter, self.DEFAULT_RATES.get(3, 0.15))

# Apply emotional modifier to rate
adjusted_rate = min(base_rate * emotional_modifier, 0.5)

# AFTER
base_rate = self.base_rates.get(chapter, self.DEFAULT_RATES.get(3, 0.15))

# Override base rate with posterior if available
if user_state:
    sample = user_state.sample("silence_propensity")
    if sample is not None:
        base_rate = sample

adjusted_rate = min(base_rate * emotional_modifier, 0.5)
```

This is the cleanest integration because `StrategicSilence` already uses the pattern of `base_rate * modifier`. We simply replace the source of `base_rate`. The emotional modifier continues to work on top of the posterior.

The `apply_strategic_silence` signature adds the optional parameter:

```python
# BEFORE (silence.py:79-85)
def apply_strategic_silence(
    self,
    chapter: int,
    emotional_state: dict[str, Any] | None = None,
    conflict_active: bool = False,
    random_seed: int | None = None,
) -> SilenceDecision:

# AFTER
def apply_strategic_silence(
    self,
    chapter: int,
    emotional_state: dict[str, Any] | None = None,
    conflict_active: bool = False,
    random_seed: int | None = None,
    user_state: BayesianState | None = None,  # NEW
) -> SilenceDecision:
```

### 4.6 Event Generator — Mood Bias (P2)

**File**: `nikita/life_simulation/event_generator.py`

The event generator calls an LLM, so we cannot replace a random draw directly. Instead, we inject mood context into the generation prompt.

```python
# BEFORE (event_generator.py:177-178)
prompt = f"""Generate 3-5 realistic life events for Nikita on {day_name}, {date_str}.

Nikita is a 28-year-old graphic designer living in a city. ...

# AFTER — inject mood bias into prompt header
mood_context = ""
if user_state:
    mood_mean = user_state.mean("mood_baseline")
    if mood_mean is not None:
        if mood_mean > 0.6:
            mood_context = "\nNikita has been in a generally good mood lately. Events should lean slightly positive."
        elif mood_mean < 0.4:
            mood_context = "\nNikita has been a bit down lately. Events should reflect a slightly lower baseline mood."
        # else: neutral, no bias injected

prompt = f"""Generate 3-5 realistic life events for Nikita on {day_name}, {date_str}.

Nikita is a 28-year-old graphic designer living in a city. She has a normal, relatable life with work, friends, and personal interests.{mood_context}
...
```

This does NOT add an LLM call — it modulates the _existing_ LLM call that already happens in `generate_events_for_day`. The mood posterior biases the emotional valence distribution of generated events.

### 4.7 Mood Calculator — Base Mood (P2)

**File**: `nikita/life_simulation/mood_calculator.py`

```python
# BEFORE (mood_calculator.py:99-103)
# Start from base mood
arousal = self._base_mood.arousal
valence = self._base_mood.valence
dominance = self._base_mood.dominance
intimacy = self._base_mood.intimacy

# AFTER
arousal = self._base_mood.arousal
dominance = self._base_mood.dominance
intimacy = self._base_mood.intimacy

# Use mood posterior as valence base if available
if user_state:
    mood_sample = user_state.sample("mood_baseline")
    if mood_sample is not None:
        valence = mood_sample  # Posterior-informed valence center
    else:
        valence = self._base_mood.valence
else:
    valence = self._base_mood.valence
```

The `compute_from_events` signature adds the optional parameter:

```python
# BEFORE (mood_calculator.py:79-80)
def compute_from_events(
    self, events: list[LifeEvent], decay_previous: bool = False
) -> MoodState:

# AFTER
def compute_from_events(
    self, events: list[LifeEvent], decay_previous: bool = False,
    user_state: BayesianState | None = None,
) -> MoodState:
```

---

## 5. Update Triggers

### 5.1 When Posteriors Change

Posteriors are updated at 4 natural trigger points — no new background processes needed:

| Trigger | When | What Updates | Observation |
|---------|------|-------------|------------|
| **Message Received** | User sends a message | `response_speed`, `engagement_rhythm` | Speed: time since last Nikita message. Rhythm: morning (0) vs evening (1). |
| **Score Computed** | After `ScoreAnalyzer.analyze()` | `mood_baseline`, `skip_propensity` | Mood: positive delta = success. Skip: if score improves during skip window. |
| **Touchpoint Delivered** | After `TouchpointEngine._deliver_single()` | `touchpoint_propensity` | Track if user replies within 4h (success) or not (failure, recorded by pg_cron). |
| **Silence Applied** | After `StrategicSilence.apply_strategic_silence()` skip | `silence_propensity` | Track if user re-engages within 12h (success) or goes quiet (failure). |

### 5.2 Update Logic Per Trigger

```python
# nikita/bayesian/updater.py

from datetime import datetime, timezone
from nikita.bayesian.state import BayesianState, update_beta


class BayesianUpdater:
    """Updates Beta posteriors at natural trigger points.

    All methods return the modified BayesianState (or create one if None).
    Updates are weighted by ScoreAnalyzer confidence when available.
    """

    def on_message_received(
        self,
        state: BayesianState | None,
        seconds_since_nikita_last: float | None,
        hour_of_day: int,
        chapter: int,
    ) -> BayesianState:
        """Update on user message received.

        Updates:
        - response_speed: fast response (<300s) = success, slow (>7200s) = failure
        - engagement_rhythm: morning (8-12) = failure (0), evening (17-22) = success (1)
        """
        if state is None:
            from nikita.bayesian.state import get_chapter_priors
            state = BayesianState(**{
                k: v for k, v in get_chapter_priors(chapter).items()
            })

        # Update response_speed
        if seconds_since_nikita_last is not None and state.response_speed:
            fast = seconds_since_nikita_last < 300  # Under 5 minutes = fast
            alpha, beta = state.response_speed
            state.response_speed = update_beta(alpha, beta, success=fast)

        # Update engagement_rhythm
        if state.engagement_rhythm:
            evening = 17 <= hour_of_day <= 22
            morning = 8 <= hour_of_day <= 12
            if evening or morning:
                alpha, beta = state.engagement_rhythm
                state.engagement_rhythm = update_beta(alpha, beta, success=evening)

        state.observation_count += 1
        state.last_updated = datetime.now(timezone.utc).isoformat()
        return state

    def on_score_computed(
        self,
        state: BayesianState | None,
        score_delta: float,
        confidence: float,
        was_skip_active: bool,
        chapter: int,
    ) -> BayesianState:
        """Update on score computation (after ScoreAnalyzer.analyze()).

        Updates:
        - mood_baseline: positive delta = success, negative = failure
        - skip_propensity: if skip was active and score improved, that's a success

        The `confidence` from ScoreAnalyzer weights the update.
        High confidence (0.8+) = full weight. Low confidence (0.3) = 30% weight.
        """
        if state is None:
            from nikita.bayesian.state import get_chapter_priors
            state = BayesianState(**{
                k: v for k, v in get_chapter_priors(chapter).items()
            })

        weight = max(0.1, min(1.0, confidence))  # Clamp confidence to [0.1, 1.0]

        # Update mood_baseline
        if state.mood_baseline:
            positive = score_delta > 0
            alpha, beta = state.mood_baseline
            state.mood_baseline = update_beta(alpha, beta, success=positive, weight=weight)

        # Update skip_propensity only if a skip was active
        if was_skip_active and state.skip_propensity:
            improved = score_delta > 0
            alpha, beta = state.skip_propensity
            state.skip_propensity = update_beta(alpha, beta, success=improved, weight=weight)

        state.observation_count += 1
        state.last_updated = datetime.now(timezone.utc).isoformat()
        return state

    def on_touchpoint_outcome(
        self,
        state: BayesianState | None,
        user_replied: bool,
        chapter: int,
    ) -> BayesianState:
        """Update on touchpoint outcome (reply or ignored).

        Called by pg_cron check 4h after touchpoint delivery.

        Updates:
        - touchpoint_propensity: reply = success, ignored = failure
        """
        if state is None:
            from nikita.bayesian.state import get_chapter_priors
            state = BayesianState(**{
                k: v for k, v in get_chapter_priors(chapter).items()
            })

        if state.touchpoint_propensity:
            alpha, beta = state.touchpoint_propensity
            state.touchpoint_propensity = update_beta(alpha, beta, success=user_replied)

        state.observation_count += 1
        state.last_updated = datetime.now(timezone.utc).isoformat()
        return state

    def on_silence_outcome(
        self,
        state: BayesianState | None,
        user_re_engaged: bool,
        chapter: int,
    ) -> BayesianState:
        """Update on silence outcome (user came back or went quiet).

        Called by pg_cron check 12h after strategic silence.

        Updates:
        - silence_propensity: re-engagement = success, further quiet = failure
        """
        if state is None:
            from nikita.bayesian.state import get_chapter_priors
            state = BayesianState(**{
                k: v for k, v in get_chapter_priors(chapter).items()
            })

        if state.silence_propensity:
            alpha, beta = state.silence_propensity
            state.silence_propensity = update_beta(alpha, beta, success=user_re_engaged)

        state.observation_count += 1
        state.last_updated = datetime.now(timezone.utc).isoformat()
        return state
```

---

## 6. DB Schema

### 6.1 Option A: JSONB Column on Users Table (Recommended)

Add a single column to the existing `users` table:

```sql
-- Migration: add_bayesian_state_column
ALTER TABLE users
ADD COLUMN bayesian_state JSONB DEFAULT NULL;

-- Index for non-null states (only query users who have state)
CREATE INDEX idx_users_bayesian_state_not_null
ON users ((bayesian_state IS NOT NULL))
WHERE bayesian_state IS NOT NULL;
```

**Why JSONB on users, not a new table**:

1. **One read per request**: The user row is already loaded in every request. Adding a JSONB column means zero additional queries.
2. **Atomic updates**: `UPDATE users SET bayesian_state = $1 WHERE id = $2` — no foreign key joins.
3. **Schema flexibility**: Adding a 7th Beta distribution later is a Python-side change, no migration needed.
4. **Size**: 6 Beta distributions + metadata = ~200 bytes JSONB per user. At 10K users = 2MB. Negligible.

**Trade-off vs. new table**: A separate `bayesian_states` table would allow historical tracking and versioning. We don't need that for Phase 1. If needed later, add a `bayesian_state_history` table with pg_cron-driven snapshots.

### 6.2 JSONB Schema

```json
{
  "touchpoint_propensity": [3.5, 16.5],
  "response_speed": [5.0, 5.0],
  "skip_propensity": [1.0, 19.0],
  "silence_propensity": [4.0, 16.0],
  "mood_baseline": [10.0, 10.0],
  "engagement_rhythm": [5.0, 5.0],
  "observation_count": 0,
  "last_updated": "2026-02-17T10:30:00Z"
}
```

### 6.3 Shadow Mode Table (Phase 1 Logging)

Per Doc 23's recommendation ("Phase 1: shadow mode alongside existing deterministic system"), add a logging table:

```sql
-- Track what the Bayesian system WOULD have done vs what actually happened
CREATE TABLE bayesian_shadow_log (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    decision_point TEXT NOT NULL,        -- e.g. "touchpoint_propensity", "response_speed"
    hardcoded_value FLOAT NOT NULL,      -- What the current system used
    posterior_value FLOAT,               -- What the Beta posterior would have used
    posterior_alpha FLOAT,
    posterior_beta FLOAT,
    observation_count INT,
    outcome TEXT                          -- What actually happened (for later analysis)
);

-- Partition by month, auto-cleanup after 90 days
CREATE INDEX idx_bayesian_shadow_user_date ON bayesian_shadow_log (user_id, created_at);
```

This table lets us compare hardcoded vs. posterior decisions without any user-visible changes. After 2-4 weeks, analyze whether posterior-informed decisions would have been better.

---

## 7. pg_cron Role

### 7.1 What Updates in Real-Time vs Background

| Update Type | Trigger | When | Where |
|------------|---------|------|-------|
| `response_speed` | Real-time | On message receive | `message_handler.py` |
| `engagement_rhythm` | Real-time | On message receive | `message_handler.py` |
| `mood_baseline` | Real-time | After scoring | Pipeline stage 5 |
| `skip_propensity` | Real-time | After scoring (if skip active) | Pipeline stage 5 |
| `touchpoint_propensity` | **Background** | 4h after touchpoint delivery | pg_cron |
| `silence_propensity` | **Background** | 12h after strategic silence | pg_cron |

### 7.2 New pg_cron Jobs

```sql
-- Check touchpoint outcomes every hour
-- Finds touchpoints delivered 4+ hours ago without user reply
SELECT cron.schedule(
    'bayesian-touchpoint-outcomes',
    '0 * * * *',  -- Every hour
    $$
    SELECT net.http_post(
        url := current_setting('app.api_base_url') || '/api/v1/tasks/bayesian-touchpoint-outcomes',
        headers := jsonb_build_object('Authorization', 'Bearer ' || current_setting('app.service_key'))
    );
    $$
);

-- Check silence outcomes every 2 hours
-- Finds silences applied 12+ hours ago
SELECT cron.schedule(
    'bayesian-silence-outcomes',
    '30 */2 * * *',  -- Every 2 hours at :30
    $$
    SELECT net.http_post(
        url := current_setting('app.api_base_url') || '/api/v1/tasks/bayesian-silence-outcomes',
        headers := jsonb_build_object('Authorization', 'Bearer ' || current_setting('app.service_key'))
    );
    $$
);
```

### 7.3 Cloud Run Task Endpoint

```python
# nikita/api/routes/tasks.py — new endpoint

@router.post("/bayesian-touchpoint-outcomes")
async def process_touchpoint_outcomes(session: AsyncSession = Depends(get_session)):
    """Check touchpoints delivered 4+ hours ago for user reply.

    For each touchpoint:
    - If user sent a message after delivery: success (user_replied=True)
    - If no message within window: failure (user_replied=False)

    Updates the user's touchpoint_propensity Beta distribution.
    """
    updater = BayesianUpdater()
    store = TouchpointStore(session)

    # Get touchpoints delivered 4-8h ago that haven't been checked
    pending = await store.get_unchecked_delivered(
        min_hours_ago=4, max_hours_ago=8
    )

    for tp in pending:
        # Check if user sent any message after touchpoint delivery
        user_replied = await _check_user_replied(
            session, tp.user_id, after=tp.delivered_at
        )

        # Load current state
        user = await _get_user(session, tp.user_id)
        state = BayesianState.from_jsonb(user.bayesian_state)

        # Update posterior
        state = updater.on_touchpoint_outcome(
            state=state,
            user_replied=user_replied,
            chapter=user.chapter or 1,
        )

        # Write back
        await _update_bayesian_state(session, tp.user_id, state.to_jsonb())

        # Mark touchpoint as bayesian-checked
        await store.mark_bayesian_checked(tp.id)

    return {"processed": len(pending)}
```

---

## 8. Cold Start

### 8.1 The Problem

A new user has no observations. Their Beta posteriors should match the current hardcoded behavior exactly — otherwise the Bayesian system changes behavior on day 1 before it has any data.

### 8.2 The Solution: Chapter-Derived Priors

When `bayesian_state` is NULL (new user), the system falls back to hardcoded behavior (graceful degradation). The Bayesian state is initialized on the user's **first scored interaction**:

```python
# In pipeline orchestrator, after first successful score computation:

if user.bayesian_state is None:
    from nikita.bayesian.state import get_chapter_priors, BayesianState
    priors = get_chapter_priors(user.chapter or 1)
    state = BayesianState(
        touchpoint_propensity=priors["touchpoint_propensity"],
        response_speed=priors["response_speed"],
        skip_propensity=priors["skip_propensity"],
        silence_propensity=priors["silence_propensity"],
        mood_baseline=priors["mood_baseline"],
        engagement_rhythm=priors["engagement_rhythm"],
        observation_count=0,
    )
    user.bayesian_state = state.to_jsonb()
```

### 8.3 Chapter Transition

When a user advances to a new chapter, their posteriors are NOT reset. The learned behavior carries forward. However, the _prior strength_ can be blended:

```python
def on_chapter_advance(state: BayesianState, new_chapter: int) -> BayesianState:
    """Blend existing posteriors with new chapter priors.

    Uses a 70/30 blend: 70% existing posterior, 30% new chapter prior.
    This allows chapter-specific behavior shifts while preserving learned patterns.
    """
    new_priors = get_chapter_priors(new_chapter)

    for name in ["touchpoint_propensity", "silence_propensity"]:
        existing = getattr(state, name)
        new_prior = new_priors[name]
        if existing and new_prior:
            blended_alpha = existing[0] * 0.7 + new_prior[0] * 0.3
            blended_beta = existing[1] * 0.7 + new_prior[1] * 0.3
            setattr(state, name, (round(blended_alpha, 1), round(blended_beta, 1)))

    return state
```

---

## 9. The Confidence Signal

### 9.1 The Problem

`ScoreAnalyzer.analyze()` returns a `ResponseAnalysis` with a `confidence` field (`Decimal 0.0-1.0`). This confidence is **currently ignored** — the scoring pipeline applies deltas at full weight regardless of confidence.

**File**: `nikita/engine/scoring/models.py:79-84`
```python
confidence: Decimal = Field(
    default=Decimal("1.0"),
    ge=Decimal("0"),
    le=Decimal("1"),
    description="LLM confidence in the analysis (0-1)",
)
```

### 9.2 The Solution: Confidence-Weighted Updates

The ScoreAnalyzer confidence directly modulates the weight of Beta updates. This is the `weight` parameter in `update_beta()`:

```python
# In BayesianUpdater.on_score_computed():
weight = max(0.1, min(1.0, confidence))

# High confidence (0.9): almost full Beta update
# Medium confidence (0.5): half-weight update
# Low confidence (0.2): tiny update (clamped to 0.1 minimum)
```

**Why this matters**: If the LLM is uncertain about whether an interaction was positive or negative (confidence=0.3), the mood_baseline posterior barely moves. If the LLM is very certain (confidence=0.9), the posterior shifts meaningfully. This prevents noisy LLM judgments from corrupting the posterior.

### 9.3 Example

```
Interaction: User says "lol whatever"
ScoreAnalyzer returns: delta=-1, confidence=0.3 (LLM unsure if dismissive or playful)

Without confidence weighting:
  mood_baseline: (10, 10) -> (10, 11) — full negative update

With confidence weighting (weight=0.3):
  mood_baseline: (10, 10) -> (10, 10.3) — tiny update, appropriately uncertain
```

Over many interactions, confident assessments dominate the posterior while uncertain ones contribute proportionally less. The posterior converges on the true pattern even with noisy observations.

---

## 10. Graceful Degradation

### 10.1 Design Principle

Every integration point follows the same pattern:

```python
if user_state and user_state.{distribution}:
    value = user_state.sample("{distribution}")
    if value is not None:
        # Use posterior-informed value (with safety clamps)
        ...
    else:
        # Fallback to hardcoded
        ...
else:
    # Fallback to hardcoded — identical to current behavior
    ...
```

### 10.2 Failure Modes and Fallbacks

| Failure | What Happens | User Impact |
|---------|-------------|------------|
| `bayesian_state` is NULL | All draws use hardcoded values | Zero — identical to current behavior |
| JSONB is corrupt/unparseable | `BayesianState.from_jsonb()` returns None | Zero — falls back to hardcoded |
| Single distribution is None | That draw uses hardcoded, others use posterior | Minimal — partial personalization |
| Alpha or beta is extreme (>1000) | Sample is near 0 or 1 | Clamped by floor/ceiling in each integration point |
| `numpy` import fails | `user_state.sample()` raises, caught by try/except | Zero — falls back to hardcoded |
| pg_cron fails to run outcome check | Touchpoint outcomes not recorded | Posterior doesn't update — stays at prior |

### 10.3 Kill Switch

A single feature flag disables all Bayesian behavior:

```python
# nikita/config/settings.py
class Settings(BaseSettings):
    bayesian_enabled: bool = Field(default=False, env="BAYESIAN_ENABLED")
```

```python
# In every integration point:
from nikita.config.settings import get_settings

settings = get_settings()
if not settings.bayesian_enabled:
    user_state = None  # Force fallback path
```

### 10.4 Posterior Bounds

To prevent runaway posteriors, all Beta parameters are hard-clamped:

```python
def update_beta(alpha: float, beta: float, success: bool, weight: float = 1.0) -> tuple[float, float]:
    if success:
        new_alpha = alpha + weight
        new_beta = beta
    else:
        new_alpha = alpha
        new_beta = beta + weight

    # Hard clamps: prevent extreme posteriors
    MAX_PARAM = 500.0  # At most ~500 pseudo-observations per side
    MIN_PARAM = 0.5    # Never collapse to point mass

    new_alpha = max(MIN_PARAM, min(MAX_PARAM, new_alpha))
    new_beta = max(MIN_PARAM, min(MAX_PARAM, new_beta))

    return (round(new_alpha, 2), round(new_beta, 2))
```

With `MAX_PARAM=500`, the posterior mean is at most 500/501 = 0.998 or at least 0.5/500.5 = 0.001. Combined with the per-integration-point clamping (e.g., touchpoint propensity clamped to `[config.min * 0.5, config.max * 2.0]`), extreme behavior is impossible.

---

## 11. Migration Path

### Phase 1: Shadow Mode (Week 1-2)

**Goal**: Run Bayesian posteriors in parallel, log to `bayesian_shadow_log`, compare.

1. **Migration**: Add `bayesian_state JSONB` column to users table
2. **Migration**: Create `bayesian_shadow_log` table
3. **Code**: Add `BayesianState`, `BayesianUpdater`, `get_chapter_priors` modules
4. **Code**: At each integration point, compute BOTH hardcoded and posterior values, log both to shadow table, use hardcoded value for actual behavior
5. **Feature flag**: `BAYESIAN_ENABLED=false` (default)
6. **pg_cron**: Add outcome-checking jobs (disabled until Phase 1b)
7. **Monitoring**: Dashboard query: `SELECT decision_point, AVG(hardcoded_value), AVG(posterior_value) FROM bayesian_shadow_log GROUP BY decision_point`

**Files changed**: 0 behavioral changes. Only new files + logging.

### Phase 1b: Live for Single Distribution (Week 3-4)

**Goal**: Enable `touchpoint_propensity` only, for a subset of users.

1. **Feature flag**: `BAYESIAN_ENABLED=true`
2. **Rollout**: Use user ID modulo for gradual rollout (10% -> 50% -> 100%)
3. **Code**: Only `_get_initiation_rate()` in `scheduler.py` reads the posterior. All other points remain shadow-only.
4. **pg_cron**: Enable `bayesian-touchpoint-outcomes` job
5. **Metric**: Compare touchpoint reply rates for Bayesian vs control group

```python
# Gradual rollout check
def is_bayesian_enabled_for_user(user_id: UUID) -> bool:
    settings = get_settings()
    if not settings.bayesian_enabled:
        return False
    rollout_pct = settings.bayesian_rollout_percent  # 0-100, default 0
    return (user_id.int % 100) < rollout_pct
```

### Phase 2: Full Inline (Week 5-8)

**Goal**: All 6 distributions live, all integration points active.

1. Enable `response_speed` in `timing.py`
2. Enable `skip_propensity` in `skip.py`
3. Enable `silence_propensity` in `silence.py`
4. Enable pg_cron silence outcome job
5. Enable `mood_baseline` in `mood_calculator.py` and `event_generator.py`
6. Enable `engagement_rhythm` (inform time slot selection in `scheduler.py`)

### Phase 3: Thompson Sampling (Week 9+, gated on growth)

Per Doc 22's recommendation ("Start with fixed skip probabilities, add Thompson Sampling later"):

- Replace `np.random.beta(alpha, beta)` with Thompson Sampling for touchpoint decisions
- Instead of sampling once and using the result, sample for each arm (message now vs wait) and pick the arm with the higher sample
- This is a one-line change per integration point but requires a success metric definition

```python
# Phase 3: Thompson Sampling for touchpoint timing
def should_message_now(state: BayesianState) -> bool:
    """Thompson Sampling: sample from 'message now' and 'wait' arms."""
    message_sample = state.sample("touchpoint_propensity")  # Higher = better to message
    wait_sample = 1.0 - message_sample  # Complement
    return message_sample > wait_sample
```

---

## 12. File Inventory

### New Files

| File | Lines (est.) | Purpose |
|------|-------------|---------|
| `nikita/bayesian/__init__.py` | 5 | Package init |
| `nikita/bayesian/state.py` | 120 | `BayesianState` model + `get_chapter_priors()` |
| `nikita/bayesian/updater.py` | 150 | `BayesianUpdater` with 4 trigger methods |
| `nikita/api/routes/tasks.py` (additions) | 60 | Two new pg_cron endpoints |
| `tests/bayesian/test_state.py` | 80 | State model tests |
| `tests/bayesian/test_updater.py` | 120 | Updater tests |
| **Total new code** | **~535** | |

### Modified Files

| File | Change | Lines Changed (est.) |
|------|--------|---------------------|
| `nikita/touchpoints/scheduler.py` | Add `user_state` param to 3 methods, modify `_get_initiation_rate` | 15 |
| `nikita/agents/text/timing.py` | Add `user_state` param to `calculate_delay`, modify mean calculation | 12 |
| `nikita/agents/text/skip.py` | Add `user_state` param to `should_skip`, modify skip probability | 10 |
| `nikita/touchpoints/silence.py` | Add `user_state` param to `apply_strategic_silence`, modify base_rate | 8 |
| `nikita/life_simulation/event_generator.py` | Add mood context to prompt | 8 |
| `nikita/life_simulation/mood_calculator.py` | Add `user_state` param, modify valence base | 8 |
| `nikita/touchpoints/engine.py` | Load and pass `user_state` through orchestration | 15 |
| `nikita/config/settings.py` | Add `bayesian_enabled`, `bayesian_rollout_percent` | 4 |
| `nikita/db/models/user.py` | Add `bayesian_state` JSONB column | 3 |
| **Total modified** | | **~83** |

### Total Impact

- ~535 lines of new code (2 new files + test files)
- ~83 lines modified across 9 existing files
- 1 new DB column (JSONB, nullable)
- 1 new logging table (shadow mode)
- 2 new pg_cron jobs
- 0 new LLM calls
- 0 new infrastructure dependencies

---

## 13. Observation Weight Calibration

Per Doc 22: "Observation weights are the most critical hand-tuned parameters — log everything for later calibration."

### 13.1 The Calibration Problem

The `weight` parameter in `update_beta()` determines how fast posteriors shift. Too fast and they overfit to noise. Too slow and they never personalize.

### 13.2 Initial Weights

| Trigger | Weight | Reasoning |
|---------|--------|-----------|
| Message received (speed) | 1.0 | Direct, unambiguous observation |
| Message received (rhythm) | 0.5 | Noisy signal (user might message at unusual time) |
| Score computed (mood) | `confidence` (0.1-1.0) | LLM confidence directly weights update |
| Score computed (skip) | `confidence * 0.5` | Skip signal is indirect, halve it |
| Touchpoint outcome (replied) | 1.0 | Direct, unambiguous observation |
| Silence outcome (re-engaged) | 0.7 | Somewhat ambiguous (user may have re-engaged for other reasons) |

### 13.3 Logging for Calibration

Every Beta update is logged to the shadow table, including the weight used:

```python
# In BayesianUpdater, after every update:
await log_shadow(
    user_id=user_id,
    decision_point=distribution_name,
    hardcoded_value=hardcoded_fallback,
    posterior_value=posterior_sample,
    posterior_alpha=new_alpha,
    posterior_beta=new_beta,
    observation_count=state.observation_count,
    weight_used=weight,
    outcome=None,  # Filled in later by outcome checker
)
```

After 4-8 weeks of shadow data, run analysis:
- Do posterior-informed decisions correlate with better outcomes (higher scores, more engagement)?
- Are any distributions converging too fast or too slow?
- Which weights need adjustment?

---

## 14. Summary: Why This Works

1. **Minimal code changes**: ~83 lines modified across the codebase. Every change is an optional parameter addition with a fallback path.

2. **No new infrastructure**: Uses existing Supabase (JSONB column), pg_cron (2 new jobs), Cloud Run (2 new task endpoints). Zero new services.

3. **No new LLM calls**: The engine itself is pure NumPy math. The only LLM involvement is the existing `ScoreAnalyzer.confidence` field, which is already computed but ignored.

4. **Graceful degradation**: If `bayesian_state` is NULL, corrupt, or the feature flag is off, every integration point falls back to current hardcoded behavior with zero user impact.

5. **Incremental rollout**: Shadow mode (week 1-2) -> single distribution (week 3-4) -> all distributions (week 5-8) -> Thompson Sampling (gated on growth).

6. **Personalization from day 1**: After just 10-20 interactions, a user's touchpoint rate starts reflecting their actual engagement pattern. After 50+ interactions, timing and skip behavior are meaningfully personalized.

7. **Confidence-weighted learning**: The currently-ignored `ScoreAnalyzer.confidence` field becomes the key quality signal for posterior updates, preventing noisy LLM judgments from corrupting learned patterns.

The Reactive Priors approach delivers the core value of Bayesian personalization — uncertainty-aware, data-driven behavioral adaptation — without the complexity of a full probabilistic graphical model. Ship the primitives, defer the complexity.

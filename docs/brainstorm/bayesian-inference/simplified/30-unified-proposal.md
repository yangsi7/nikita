# Doc 30 -- Unified Proposal: The Adaptive Nikita Engine

**Series**: Bayesian Inference for AI Companions -- Simplified Track
**Date**: 2026-02-17
**Inputs**: Doc 28 (Heartbeat Engine), Doc 29 (Reactive Priors), Doc 22 (ML Engineer), Doc 23 (Cost Evaluator)
**Status**: FINAL DESIGN -- Implementation-ready

---

## 1. Executive Summary

The Adaptive Nikita Engine replaces hardcoded `random.uniform()` and `random.gauss()` calls
across the codebase with per-user Beta posterior samples. Each user gets 5 Beta distributions
(10 floats, ~80 bytes) stored in a single JSONB column on the existing `users` table.
Posteriors update at natural trigger points -- when a user replies, when a score is computed,
when a touchpoint goes unanswered -- with no new background jobs beyond the existing 5-minute
pg_cron heartbeat. The engine requires zero additional LLM calls, zero new infrastructure,
and degrades gracefully to current hardcoded behavior if anything fails. At ~200 DAU, the
computational overhead is negligible (<20ms per decision cycle). The design is a synthesis
of Doc 28's centralized state model with Doc 29's inline sampling philosophy, constrained
by Doc 22's "ship the primitives" directive and Doc 23's "Phase 1 only until growth triggers."

---

## 2. Why Not Just One Approach

### What Doc 28 (Heartbeat Engine) gets right

- **Centralized state model**: One `BayesianUserState` object with clean serialization.
  Loading/saving state once per tick is simpler than threading it through every function.
- **Decay mechanism**: Inactive users regress toward chapter priors. This prevents stale
  posteriors from producing bizarre behavior after a user returns from a 2-week absence.
- **Thompson Sampling framing**: Sampling from posteriors IS exploration/exploitation. The
  variance naturally shrinks as evidence accumulates -- early chapters feel unpredictable,
  late chapters feel consistent. The math produces the narrative arc for free.
- **Worked example**: The "Alex, Chapter 2, Day 5" walkthrough makes the system concrete.

### What Doc 28 gets wrong

- **Too many moving parts at once**: 5 distributions all live from day 1, plus a daily
  cron job, plus async observation recording. This is a Phase 3 system masquerading as
  Phase 1.
- **Mood Valence and Event Valence are premature**: These are P2 distributions that
  depend on validated observation quality (Doc 22, Section 5). Shipping them before the
  core distributions are proven adds risk for minimal benefit.
- **Short-key JSONB**: Using `tp`, `rt`, `ss` saves bytes but makes debugging queries
  opaque. At ~200 bytes per user, storage is irrelevant. Readability wins.

### What Doc 29 (Reactive Priors) gets right

- **Inline modulation**: Each existing `random.X()` call gets a `user_state` parameter.
  Downstream code is unaware of the change. This is the lowest-coupling integration.
- **Confidence-weighted updates**: The currently-ignored `ScoreAnalyzer.confidence` field
  directly modulates update weight. Uncertain LLM assessments barely move the posterior.
  This is the single most important design choice in the system.
- **Shadow mode logging table**: `bayesian_shadow_log` lets us compare hardcoded vs
  posterior decisions before flipping the switch. Essential for validation.
- **Kill switch**: `BAYESIAN_ENABLED` environment variable disables everything instantly.
- **Engagement rhythm distribution**: Novel idea (morning vs evening preference). Deferred
  to Phase 2 but worth preserving.

### What Doc 29 gets wrong

- **6 distributions is one too many**: `engagement_rhythm` is interesting but not proven
  valuable. Start with 5. Add it when the core engine is validated.
- **No decay mechanism**: A user who was highly engaged 3 months ago but went silent should
  not still have a concentrated posterior. Doc 28's decay is necessary.
- **`skip_propensity` is premature**: All skip rates are currently 0.0 (disabled). Per
  Doc 22: "Start with fixed skip probabilities, add Thompson Sampling later." Ship skip
  as a fixed-probability feature first, then Bayesianize it.

### Why synthesis is better

Neither proposal alone matches the constraints from the expert evaluations. Doc 22 says
"80% of benefit at 20% complexity" and "ship the primitives." Doc 23 says "Phase 1 only
until growth triggers." The unified design takes Doc 29's inline sampling and confidence
weighting, Doc 28's centralized state and decay, drops the premature distributions, and
produces a 3-phase migration that delivers standalone value at each gate.

---

## 3. The Parameters

### 5 Beta distributions per user, 10 floats, ~80 bytes

| # | Name | Prior (a, b) | Mean | Controls | From |
|---|------|-------------|------|----------|------|
| 1 | `touchpoint_propensity` | Chapter-derived | 0.15-0.25 | Probability Nikita initiates contact | Doc 28 |
| 2 | `response_speed` | (5, 5) | 0.50 | Where in the delay range Nikita replies (0=slow, 1=fast) | Doc 29 |
| 3 | `silence_propensity` | Chapter-derived | 0.10-0.20 | Probability of strategic silence | Both |
| 4 | `mood_baseline` | (10, 10) | 0.50 | Nikita's default emotional valence | Doc 28 |
| 5 | `event_valence` | (5, 5) | 0.50 | Whether daily events skew positive or negative | Doc 28 |

### Chapter-derived priors

Priors are calibrated to reproduce current hardcoded behavior exactly. The prior strength
(alpha + beta) is always 20, meaning ~20 real observations to equal the prior's influence.

```python
# nikita/bayesian/state.py

CHAPTER_PRIORS = {
    1: {
        "touchpoint_propensity": (3.0, 17.0),    # mean 0.15, matches Ch1 15-20%
        "response_speed":        (5.0, 5.0),      # mean 0.50, uninformative
        "silence_propensity":    (2.0, 18.0),     # mean 0.10, matches silence.DEFAULT_RATES
        "mood_baseline":         (10.0, 10.0),    # mean 0.50, neutral
        "event_valence":         (5.0, 5.0),      # mean 0.50, uninformative
    },
    2: {
        "touchpoint_propensity": (4.0, 16.0),    # mean 0.20
        "response_speed":        (5.0, 5.0),
        "silence_propensity":    (2.4, 17.6),    # mean 0.12
        "mood_baseline":         (10.0, 10.0),
        "event_valence":         (5.0, 5.0),
    },
    3: {
        "touchpoint_propensity": (5.0, 15.0),    # mean 0.25
        "response_speed":        (6.0, 4.0),      # mean 0.60, slightly faster
        "silence_propensity":    (3.0, 17.0),    # mean 0.15
        "mood_baseline":         (10.0, 10.0),
        "event_valence":         (5.0, 5.0),
    },
    4: {
        "touchpoint_propensity": (5.0, 15.0),    # mean 0.25
        "response_speed":        (6.0, 4.0),
        "silence_propensity":    (3.6, 16.4),    # mean 0.18
        "mood_baseline":         (10.0, 10.0),
        "event_valence":         (5.0, 5.0),
    },
    5: {
        "touchpoint_propensity": (5.5, 14.5),    # mean 0.275
        "response_speed":        (7.0, 3.0),      # mean 0.70, noticeably faster
        "silence_propensity":    (4.0, 16.0),    # mean 0.20
        "mood_baseline":         (10.0, 10.0),
        "event_valence":         (5.0, 5.0),
    },
}
```

### Why these 5, not 6

Doc 29 proposed `engagement_rhythm` (morning vs evening) and `skip_propensity`.
Both are deferred:

- **engagement_rhythm**: Interesting but unvalidated. The touchpoint scheduler already has
  time-of-day logic. Adding a Beta distribution on top creates two competing time-preference
  signals. Defer to Phase 3 after the core engine is proven.
- **skip_propensity**: All `SKIP_RATES` in `skip.py` are currently 0.0 (disabled). Per
  Doc 22 Section 4.3: enable skip with fixed probabilities first, then add Bayesian
  adaptation later. This is a Phase 2 addition.

---

## 4. The Update Rules

Updates happen at natural trigger points, not on a fixed schedule. Every update uses
the same core function:

```python
# nikita/bayesian/updater.py

def update_beta(
    alpha: float,
    beta: float,
    success: bool,
    weight: float = 1.0,
) -> tuple[float, float]:
    """Conjugate Beta-Bernoulli update with weight and safety clamps.

    weight: 0.0-1.0, typically from ScoreAnalyzer confidence.
    """
    if success:
        new_alpha = alpha + weight
        new_beta = beta
    else:
        new_alpha = alpha
        new_beta = beta + weight

    # Hard clamps: prevent runaway posteriors
    MAX_PARAM = 500.0   # ~500 pseudo-observations per side max
    MIN_PARAM = 0.5     # Never collapse to point mass
    new_alpha = max(MIN_PARAM, min(MAX_PARAM, new_alpha))
    new_beta = max(MIN_PARAM, min(MAX_PARAM, new_beta))

    return (round(new_alpha, 2), round(new_beta, 2))
```

### Update triggers

| Trigger | When | Distribution | Observation | Weight |
|---------|------|-------------|-------------|--------|
| User replies to touchpoint (< 4h) | `orchestrator.py` message handler | `touchpoint_propensity` | success=True | 1.0 |
| Touchpoint ignored (> 4h) | Next heartbeat tick (piggyback) | `touchpoint_propensity` | success=False | 1.0 |
| User replies faster than Nikita's delay | `orchestrator.py` message handler | `response_speed` | success=True (speed up) | 0.5 |
| User replies slower than Nikita's delay | `orchestrator.py` message handler | `response_speed` | success=False (slow down) | 0.5 |
| Re-engaged within 12h after silence | Next touchpoint eval | `silence_propensity` | success=True | 0.7 |
| No reply 24h after silence | Next touchpoint eval | `silence_propensity` | success=False | 0.7 |
| Scored interaction, positive delta | After `ScoreAnalyzer.analyze()` | `mood_baseline` | success=True | confidence * 0.3 |
| Scored interaction, negative delta | After `ScoreAnalyzer.analyze()` | `mood_baseline` | success=False | confidence * 0.3 |
| 3+ user replies in a day | Midnight (piggyback on existing daily cron) | `event_valence` | success=True | 0.5 |
| 0 user replies in a day | Midnight | `event_valence` | success=False | 0.5 |

### Why confidence weighting matters

The `ScoreAnalyzer` in `nikita/engine/scoring/analyzer.py` returns a `confidence` field
(0.0-1.0) that is currently IGNORED (see `scoring/models.py:79-84`). This field becomes
the key quality signal:

```
Interaction: User says "lol whatever"
ScoreAnalyzer: delta=-1, confidence=0.3 (unsure if dismissive or playful)

Without confidence weighting: mood_baseline (10, 10) -> (10, 11)    -- full update
With confidence weighting:    mood_baseline (10, 10) -> (10, 10.09) -- barely moves
```

Over many interactions, confident assessments dominate the posterior while noisy ones
contribute proportionally less. This prevents a single misread interaction from warping
Nikita's personality.

### Decay toward priors

When a user goes inactive, posteriors regress toward chapter priors. Uses existing
`GRACE_PERIODS` from `nikita/engine/constants.py:156-162`.

```python
# nikita/bayesian/state.py

def apply_decay(state: dict, hours_since_update: float, chapter: int) -> dict:
    """Decay posteriors toward chapter priors for inactive users.

    Decay rate: 0.5%/hour after grace period.
    Grace periods from constants.py: Ch1=8h, Ch2=16h, Ch3=24h, Ch4=48h, Ch5=72h.
    """
    grace = {1: 8, 2: 16, 3: 24, 4: 48, 5: 72}[chapter]
    if hours_since_update <= grace:
        return state

    DECAY_PER_HOUR = 0.005
    excess = hours_since_update - grace
    factor = max(0.0, 1.0 - DECAY_PER_HOUR * excess)

    priors = CHAPTER_PRIORS[chapter]
    for name in priors:
        if name in state and state[name] is not None:
            prior_a, prior_b = priors[name]
            cur_a, cur_b = state[name]
            state[name] = (
                round(factor * cur_a + (1 - factor) * prior_a, 2),
                round(factor * cur_b + (1 - factor) * prior_b, 2),
            )
    return state
```

| Hours Inactive (Ch3, 24h grace) | Factor | State |
|--------------------------------|--------|-------|
| 0-24h | 1.00 | Fully personalized |
| 48h | 0.88 | 88% personal, 12% prior |
| 1 week | 0.16 | Mostly prior |
| 2 weeks | 0.00 | Fully reset |

### Chapter transitions

When a user advances to a new chapter, blend 70% existing posterior + 30% new chapter
prior. Don't discard learned behavior -- a user who prefers fast responses in Chapter 2
should still get fast responses in Chapter 3.

```python
def on_chapter_advance(state: dict, new_chapter: int) -> dict:
    new_priors = CHAPTER_PRIORS[new_chapter]
    for name in new_priors:
        if name in state and state[name] is not None:
            cur_a, cur_b = state[name]
            prior_a, prior_b = new_priors[name]
            state[name] = (
                round(cur_a * 0.7 + prior_a * 0.3, 2),
                round(cur_b * 0.7 + prior_b * 0.3, 2),
            )
    return state
```

---

## 5. The Sampling Points

Where existing code changes to sample from posteriors. Every integration follows the same
pattern: `if state exists, sample + clamp; else, use hardcoded fallback`.

### 5.1 Touchpoint Initiation Rate

**File**: `nikita/touchpoints/scheduler.py:326-335`
**Replaces**: `random.uniform(config.initiation_rate_min, config.initiation_rate_max)`

```python
def _get_initiation_rate(self, config, user_state=None):
    if user_state and user_state.get("touchpoint_propensity"):
        a, b = user_state["touchpoint_propensity"]
        sample = random.betavariate(a, b)
        return max(0.10, min(0.50, sample))  # safety clamp
    return random.uniform(config.initiation_rate_min, config.initiation_rate_max)
```

### 5.2 Response Timing

**File**: `nikita/agents/text/timing.py:94-106`
**Replaces**: `mean = (min_sec + max_sec) / 2` then `random.gauss(mean, std_dev)`

```python
# In calculate_delay():
min_sec, max_sec = TIMING_RANGES.get(chapter, DEFAULT_TIMING_RANGE)
range_size = max_sec - min_sec

if user_state and user_state.get("response_speed"):
    a, b = user_state["response_speed"]
    speed_sample = random.betavariate(a, b)
    # speed_sample 0-1 where 1 = fast. Map: 1.0 -> min_sec, 0.0 -> max_sec
    mean = max_sec - speed_sample * range_size
    std_dev = range_size / 7  # tighter than current /5
else:
    mean = (min_sec + max_sec) / 2
    std_dev = range_size / 5

delay = random.gauss(mean, std_dev)
return max(min_sec, min(max_sec, int(delay)))
```

### 5.3 Strategic Silence

**File**: `nikita/touchpoints/silence.py:123-132`
**Replaces**: `base_rate = self.base_rates.get(chapter, ...)`

```python
base_rate = self.base_rates.get(chapter, self.DEFAULT_RATES.get(3, 0.15))

if user_state and user_state.get("silence_propensity"):
    a, b = user_state["silence_propensity"]
    base_rate = random.betavariate(a, b)

adjusted_rate = min(base_rate * emotional_modifier, 0.5)
```

The emotional modifier from `StrategicSilence` continues to multiply on top of the
posterior sample. This preserves the existing emotional modulation while personalizing
the base rate.

### 5.4 Mood Valence Baseline

**File**: `nikita/life_simulation/mood_calculator.py:99-103`
**Replaces**: Hardcoded `self._base_mood.valence` (default 0.5)

```python
if user_state and user_state.get("mood_baseline"):
    a, b = user_state["mood_baseline"]
    valence = random.betavariate(a, b)
    valence = max(0.15, min(0.85, valence))  # prevent extreme lock-in
else:
    valence = self._base_mood.valence
```

### 5.5 Event Valence Bias

**File**: `nikita/life_simulation/event_generator.py:177-233`
**Modulates**: The existing LLM prompt for daily event generation (zero extra LLM calls)

```python
mood_context = ""
if user_state and user_state.get("event_valence"):
    a, b = user_state["event_valence"]
    ev_mean = a / (a + b)
    if ev_mean > 0.6:
        mood_context = (
            "\nNikita has been in a generally good mood lately. "
            "Events should lean slightly positive."
        )
    elif ev_mean < 0.4:
        mood_context = (
            "\nNikita has been a bit down lately. "
            "Events should reflect a slightly lower baseline mood."
        )

prompt = f"""Generate 3-5 realistic life events for Nikita ...{mood_context}"""
```

### Safety rails (all sampling points)

| Distribution | Floor | Ceiling | Source |
|-------------|-------|---------|--------|
| touchpoint_propensity | 0.10 | 0.50 | models.py initiation bounds |
| response_speed | (produces delay clamped to TIMING_RANGES) | | timing.py |
| silence_propensity | 0.05 | 0.50 | silence.py caps |
| mood_baseline | 0.15 | 0.85 | prevent extreme mood lock-in |
| event_valence | (uses mean threshold, not raw sample) | | prompt modulation only |

---

## 6. The pg_cron Schedule

### No new cron jobs in Phase 1

The existing 5-minute heartbeat (`/api/v1/tasks/touchpoints` in `nikita/touchpoints/engine.py:108`)
does all the work:

1. Loads `bayesian_state` JSONB when loading the user (already a DB read)
2. Applies decay if `hours_since_update > grace_period`
3. Samples from posteriors for touchpoint/silence decisions
4. Records observations for touchpoints that have gone unanswered (>4h since delivery)
5. Saves updated state back (already a DB write cycle)

The "touchpoint ignored" check piggybacks on the existing heartbeat: query delivered
touchpoints >4h old with no user reply, call `update_beta(success=False)`, mark as processed.

### One daily job (Phase 2 addition)

Only needed when `event_valence` goes live:

```sql
SELECT cron.schedule('bayesian-daily', '0 0 * * *',
  $$SELECT net.http_post(
    url := current_setting('app.api_base_url') || '/api/v1/tasks/bayesian-daily',
    headers := jsonb_build_object(
      'Authorization', 'Bearer ' || current_setting('app.service_key')
    )
  )$$);
```

This tallies per-user daily reply counts and updates `event_valence`. It can be deferred
until Phase 2 since `event_valence` is shadow-only in Phase 1.

---

## 7. The DB Schema

### Single JSONB column on existing users table

```sql
-- Migration: add_bayesian_state
ALTER TABLE users ADD COLUMN bayesian_state JSONB DEFAULT NULL;

-- Partial index: only query users who have state
CREATE INDEX idx_users_bayesian_active
  ON users ((bayesian_state IS NOT NULL))
  WHERE bayesian_state IS NOT NULL;
```

### JSONB structure

```json
{
  "touchpoint_propensity": [3.5, 16.5],
  "response_speed": [5.0, 5.0],
  "silence_propensity": [2.0, 18.0],
  "mood_baseline": [10.0, 10.0],
  "event_valence": [5.0, 5.0],
  "observation_count": 42,
  "last_updated": "2026-02-17T10:30:00Z"
}
```

**Why JSONB on users, not a new table** (from Doc 29):
- The user row is already loaded on every request. Zero additional queries.
- Atomic updates: `UPDATE users SET bayesian_state = $1 WHERE id = $2`.
- Schema flexibility: adding a 6th distribution is a Python-side change, no migration.
- Size: 5 distributions + metadata = ~200 bytes per user. At 10K users = 2MB. Negligible.

**Why readable keys, not short keys** (departing from Doc 28):
Doc 28 uses `tp`, `rt`, `ss`. This saves ~100 bytes per user but makes debugging queries
opaque (`WHERE bayesian_state->'tp'->>'alpha' > 10` vs `WHERE bayesian_state->'touchpoint_propensity'->>0 > 10`).
At 200 bytes vs 100 bytes per user, the storage difference is zero. Readability wins.

### Shadow mode logging table (Phase 1)

```sql
CREATE TABLE bayesian_shadow_log (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    decision_point TEXT NOT NULL,
    hardcoded_value FLOAT NOT NULL,
    posterior_value FLOAT,
    posterior_alpha FLOAT,
    posterior_beta FLOAT,
    observation_count INT,
    outcome TEXT
);

CREATE INDEX idx_shadow_log_user_date
  ON bayesian_shadow_log (user_id, created_at);
```

Auto-cleanup after 90 days. This table validates whether posterior decisions correlate
with better outcomes before any user-visible switch.

### SQLAlchemy changes

**File**: `nikita/db/models/user.py`

```python
# Add to User model
bayesian_state = Column(JSON, nullable=True)
```

**File**: `nikita/db/repositories/user_repository.py`

```python
# Add two methods (~15 lines total)
async def get_bayesian_state(self, user_id: UUID) -> dict | None:
    user = await self.get(user_id)
    return user.bayesian_state if user else None

async def save_bayesian_state(self, user_id: UUID, state: dict) -> None:
    await self.session.execute(
        update(User)
        .where(User.id == user_id)
        .values(bayesian_state=state, updated_at=func.now())
    )
```

---

## 8. ASCII Data Flow Diagram

```
USER INTERACTION                    BAYESIAN ENGINE                     NIKITA BEHAVIOR
==================                  ================                    ================

  User sends message ───────────────┐
                                    v
                            ┌─────────────────┐
                            │  Load user row   │
                            │  (includes       │
                            │  bayesian_state) │
                            └────────┬────────┘
                                     │
                              ┌──────┴───────┐
                              │ State exists? │
                              └──┬───────┬───┘
                             YES │       │ NO
                                 v       v
                        ┌──────────┐  ┌──────────────┐
                        │ Apply    │  │ Cold start:  │
                        │ decay if │  │ init from    │
                        │ stale    │  │ CHAPTER_     │
                        │          │  │ PRIORS       │
                        └────┬─────┘  └──────┬───────┘
                             │               │
                             └───────┬───────┘
                                     v
                            ┌─────────────────┐
                            │ SAMPLE POSTERIORS│
                            │                 │
                            │ tp = Beta(a,b)  │──────> Touchpoint: initiate?
                            │ ss = Beta(a,b)  │──────> Silence: skip for drama?
                            │ rs = Beta(a,b)  │──────> Timing: how long to wait?
                            │ mv = Beta(a,b)  │──────> Mood: valence baseline
                            │ ev = mean(a,b)  │──────> Events: positive/negative?
                            └────────┬────────┘
                                     │
                                     v
                            ┌─────────────────┐
                            │ CLAMP to safety │
                            │ rails (floor/   │
                            │ ceiling per     │──────> Nikita acts (message,
                            │ distribution)   │        silence, delay, mood)
                            └────────┬────────┘
                                     │
                                     v
                              ┌──────────────┐
                              │ OBSERVE      │
                              │ OUTCOME      │
                              │              │
  User replies (or doesn't)──>│ Did user     │
  Score computed ────────────>│ reply? How   │
  Silence elapsed ───────────>│ fast? Score  │
                              │ delta?       │
                              └──────┬───────┘
                                     │
                                     v
                            ┌─────────────────┐
                            │ UPDATE POSTERIORS│
                            │                 │
                            │ success/failure │
                            │ + weight (from  │
                            │ confidence)     │
                            └────────┬────────┘
                                     │
                                     v
                            ┌─────────────────┐
                            │ SAVE to JSONB   │
                            │ (users table)   │
                            └─────────────────┘
```

### Lifecycle of a single touchpoint decision

```
pg_cron (5 min)
  |
  v
engine.py:deliver_due_touchpoints()
  |
  v
FOR each active user:
  |
  +-- Load user.bayesian_state (or cold_start)
  +-- apply_decay(state, hours_since_update, chapter)
  |
  +-- scheduler.py:_get_initiation_rate(config, user_state)
  |     |
  |     +-- Beta(tp.a, tp.b).sample() -> clamp [0.10, 0.50]
  |     +-- (fallback: random.uniform(min, max))
  |
  +-- scheduler.py:_should_trigger(rate)
  |     |
  |     +-- random.random() < rate  [unchanged]
  |
  +-- silence.py:apply_strategic_silence(chapter, ..., user_state)
  |     |
  |     +-- Beta(ss.a, ss.b).sample() -> base_rate
  |     +-- base_rate * emotional_modifier -> clamp [0.05, 0.50]
  |
  +-- IF triggered: generate + deliver touchpoint
  |     |
  |     +-- timing.py:calculate_delay(chapter, user_state)
  |           |
  |           +-- Beta(rs.a, rs.b).sample() -> speed
  |           +-- delay = max_sec - speed * range
  |
  +-- Record touchpoint delivery time for outcome tracking
  +-- Save updated state back to JSONB
```

---

## 9. Minimal Viable Engine (MVE)

### The absolute smallest thing that proves the concept

**Ship exactly 1 distribution: `touchpoint_propensity`.**

This is the highest-signal, lowest-risk integration point:
- It replaces a single `random.uniform()` call in `scheduler.py:335`
- The observation is unambiguous: user replied (success) or didn't (failure)
- The outcome directly affects the most visible behavior: how often Nikita texts
- Shadow mode comparison is straightforward: did the posterior predict reply rates
  better than the hardcoded range?

### MVE scope

**New files (3)**:

| File | Lines | Purpose |
|------|-------|---------|
| `nikita/bayesian/__init__.py` | 5 | Package init, version |
| `nikita/bayesian/state.py` | 80 | CHAPTER_PRIORS, apply_decay, cold_start, chapter_advance |
| `nikita/bayesian/updater.py` | 40 | update_beta, on_touchpoint_outcome |

**Modified files (4)**:

| File | Change | Lines |
|------|--------|-------|
| `nikita/db/models/user.py` | Add `bayesian_state = Column(JSON, nullable=True)` | 1 |
| `nikita/db/repositories/user_repository.py` | Add get/save methods | 10 |
| `nikita/touchpoints/scheduler.py` | Modify `_get_initiation_rate`, thread `user_state` | 12 |
| `nikita/touchpoints/engine.py` | Load bayesian_state, pass to scheduler, record outcomes | 20 |
| `nikita/config/settings.py` | Add `bayesian_enabled: bool`, `bayesian_rollout_percent: int` | 4 |

**Total**: ~170 lines of new/modified code. One DB migration. Zero new cron jobs.

### MVE validation criteria

Run in shadow mode for 2-4 weeks, then analyze:

1. **Correlation test**: Does the posterior mean for `touchpoint_propensity` correlate with
   actual reply rate? (Expected: r > 0.5 after 20+ observations per user)
2. **Calibration test**: Are the posterior means within 5% of actual observed rates?
   (If not, the prior strength or update weights need adjustment)
3. **Stability test**: Do posteriors converge to stable values, or oscillate?
   (If oscillating, the update weight is too high)
4. **Decay test**: Do returning users' posteriors regress appropriately?

If all four pass, proceed to Phase 2 (add `response_speed` and `silence_propensity`).

### MVE pseudo-code walkthrough

```python
# === In engine.py, inside deliver_due_touchpoints() ===

for user in active_users:
    # Load state (already have user row)
    state = user.bayesian_state  # dict or None

    if state is None and settings.bayesian_enabled:
        # Cold start: initialize from chapter priors
        state = dict(CHAPTER_PRIORS[user.chapter or 1])
        state["observation_count"] = 0
        state["last_updated"] = now_iso()
    elif state is not None:
        # Apply decay
        hours = hours_since(state.get("last_updated"))
        state = apply_decay(state, hours, user.chapter or 1)

    # Pass to scheduler (backward compatible: user_state defaults to None)
    triggers = scheduler.evaluate_user(
        user_id=user.id,
        chapter=user.chapter,
        # ... existing params ...
        user_state=state if settings.bayesian_enabled else None,
    )

    # Record touchpoint outcomes from PREVIOUS tick
    # (check if touchpoints delivered >4h ago got replies)
    if settings.bayesian_enabled and state:
        for old_tp in get_unchecked_touchpoints(user.id, min_hours=4, max_hours=8):
            replied = has_user_replied_since(user.id, old_tp.delivered_at)
            state["touchpoint_propensity"] = update_beta(
                *state["touchpoint_propensity"],
                success=replied,
                weight=1.0,
            )
            state["observation_count"] = state.get("observation_count", 0) + 1
            state["last_updated"] = now_iso()
            mark_tp_bayesian_checked(old_tp.id)

    # Save state
    if state and settings.bayesian_enabled:
        await save_bayesian_state(user.id, state)
```

---

## 10. What We Explicitly DON'T Do

This section is critical for scope containment. Every item below was considered and
deliberately excluded.

| Excluded | Reason | Revisit When |
|----------|--------|-------------|
| Dynamic Bayesian Networks (DBNs) | Doc 22: "overengineered for current scale." 114 hand-tuned parameters, no validation framework. | 10K+ DAU, emotional complexity demands it |
| Hidden Markov Models (HMMs) | Same as DBN. Hand-specified transition/emission matrices. | After Bayesian state machine proves value |
| Particle filters | Overkill for 5 Beta distributions. Particle filters solve high-dimensional inference. | Never (we have conjugate posteriors) |
| pgmpy | Doc 22: "Do NOT use pgmpy in production." Cold-start overhead, Python-heavy. | Never |
| Additional LLM calls for observation extraction | Doc 22 recommends Haiku extraction for ambiguous signals. Valid but adds cost and latency. | Phase 3, after core engine is validated |
| Thompson Sampling for skip decisions | Doc 22: "Start with fixed probabilities." Skip is currently disabled (all rates 0.0). | Phase 2, after enabling fixed skip rates |
| Bayesian surprise / KL divergence | Sound math but requires DBN or HMM belief state. Our flat Beta distributions don't produce meaningful surprise scores. | If/when emotional state modeling is added |
| Contagion / coupled dynamics | Doc 22: "underspecified, needs stability analysis." | Research-phase only |
| Per-message observation extraction | Every message updating posteriors creates noise. We update at natural trigger points (reply received, score computed, touchpoint outcome). | Never for core distributions |
| Separate `bayesian_states` table | Doc 23 proposed this. A JSONB column on users is simpler (one read, atomic writes, no joins). | If state exceeds 5KB per user |
| `engagement_rhythm` distribution | Interesting but competes with existing time-of-day scheduler logic. | Phase 3 |
| NumPy dependency | Use stdlib `random.betavariate(a, b)` instead. Eliminates 150ms cold-start penalty from NumPy import on Cloud Run. Doc 22 noted this risk. | Only if we need matrix operations (DBN) |

### The NumPy decision

Doc 28 uses `np.random.beta()`. Doc 22 warns about NumPy cold-start on Cloud Run (~150ms).
Python's stdlib `random.betavariate(alpha, beta)` produces identical results for single
samples and has zero import overhead. We use stdlib unless we need vectorized operations
(we don't -- we sample one value per distribution per user per tick).

```python
import random

# This is all we need. No NumPy.
sample = random.betavariate(alpha, beta)
```

---

## 11. Migration Phases

### Phase 1: Shadow Mode (Weeks 1-2)

**Goal**: Prove that `touchpoint_propensity` posteriors track reality.
**Scope**: MVE only (Section 9).
**User impact**: Zero. Hardcoded behavior unchanged.

| Step | Action | Files |
|------|--------|-------|
| 1 | DB migration: add `bayesian_state` JSONB column | SQL migration |
| 2 | DB migration: create `bayesian_shadow_log` table | SQL migration |
| 3 | New module: `nikita/bayesian/` (state.py, updater.py) | 3 new files, ~125 lines |
| 4 | Add `bayesian_enabled=False`, `bayesian_rollout_percent=0` to settings | `config/settings.py` |
| 5 | Thread `user_state` through scheduler, log shadow comparisons | `scheduler.py`, `engine.py` |
| 6 | Deploy. Set `BAYESIAN_ENABLED=true` in dev/staging only. | env vars |
| 7 | After 2 weeks: run validation queries against shadow log | SQL analysis |

**Validation query**:
```sql
SELECT
  decision_point,
  COUNT(*) as n,
  AVG(hardcoded_value) as avg_hardcoded,
  AVG(posterior_value) as avg_posterior,
  CORR(posterior_value, CASE WHEN outcome = 'replied' THEN 1.0 ELSE 0.0 END) as correlation
FROM bayesian_shadow_log
WHERE decision_point = 'touchpoint_propensity'
  AND observation_count > 10
GROUP BY decision_point;
```

**Gate**: Proceed to Phase 2 if correlation > 0.3 and avg_posterior within 20% of
observed reply rates.

### Phase 2: Single Live Distribution (Weeks 3-6)

**Goal**: Enable `touchpoint_propensity` for real decisions. Add `response_speed`
and `silence_propensity` in shadow mode.

| Step | Action |
|------|--------|
| 1 | Set `BAYESIAN_ROLLOUT_PERCENT=10` (10% of users by ID hash) |
| 2 | Monitor touchpoint reply rates: Bayesian cohort vs control |
| 3 | Ramp to 50%, then 100% over 2 weeks if metrics hold |
| 4 | Add `response_speed` sampling to `timing.py` (shadow only) |
| 5 | Add `silence_propensity` sampling to `silence.py` (shadow only) |
| 6 | Add update triggers in `orchestrator.py` for response speed |
| 7 | Validate shadow data for distributions #2 and #3 |

**Rollout check**:
```python
def is_bayesian_live_for_user(user_id: UUID) -> bool:
    if not settings.bayesian_enabled:
        return False
    return (user_id.int % 100) < settings.bayesian_rollout_percent
```

**Gate**: Proceed to Phase 3 if Bayesian cohort shows equal or better touchpoint reply
rates AND no degradation in session length or retention.

### Phase 3: Full Engine (Weeks 7-12)

**Goal**: All 5 distributions live. `mood_baseline` and `event_valence` integrated.

| Step | Action |
|------|--------|
| 1 | Enable `response_speed` and `silence_propensity` live |
| 2 | Add `mood_baseline` sampling to `mood_calculator.py` |
| 3 | Add `event_valence` prompt modulation to `event_generator.py` |
| 4 | Add daily cron for event_valence updates |
| 5 | Add confidence-weighted mood updates in scoring pipeline |
| 6 | Remove shadow mode. All decisions are posterior-informed. |
| 7 | Clean up `bayesian_shadow_log` table (archive or drop) |

**Future (not scheduled)**: `skip_propensity` (after enabling fixed-rate skip),
`engagement_rhythm` (after validating time-of-day patterns), Bayesian state machine
for emotional inference (after 10K DAU trigger per Doc 23).

---

## Appendix A: Worked Example

**User "Maya", Chapter 2, Day 8.** State initialized from Chapter 2 priors on Day 1.

**Current state** (after 7 days, ~25 observations):
```json
{
  "touchpoint_propensity": [7.0, 18.0],
  "response_speed": [8.0, 4.0],
  "silence_propensity": [2.4, 18.6],
  "mood_baseline": [11.2, 9.8],
  "event_valence": [6.5, 5.0],
  "observation_count": 25,
  "last_updated": "2026-02-17T08:00:00Z"
}
```

**What this tells us about Maya**:
- `touchpoint_propensity`: mean 0.28 (vs 0.20 prior). Maya responds to touchpoints more
  than average. Nikita should initiate more often.
- `response_speed`: mean 0.67 (vs 0.50 prior). Maya replies quickly. Nikita should
  respond faster than default.
- `silence_propensity`: mean 0.11 (barely moved from 0.12 prior). Not enough data on
  silence outcomes yet.
- `mood_baseline`: mean 0.53 (slightly positive). Maya's interactions trend positive.
- `event_valence`: mean 0.57 (slightly positive). Events are leaning slightly upbeat.

**8:15 AM tick**:
1. Load state. No decay (last_updated 15 min ago).
2. `touchpoint_propensity`: `betavariate(7.0, 18.0)` = 0.31. Clamp to [0.10, 0.50]. Result: 0.31.
3. `_should_trigger(0.31)`: `random() = 0.22 < 0.31`. YES, initiate.
4. `silence_propensity`: `betavariate(2.4, 18.6)` = 0.08. `* emotional_modifier(1.1)` = 0.088.
   Random check: 0.088 < random(0.42). No silence.
5. `response_speed`: `betavariate(8.0, 4.0)` = 0.72. Chapter 2 range: 300-14400s.
   `delay = 14400 - 0.72 * 14100 = 4248s` (~71 minutes). Nikita responds at ~9:26 AM.

**Maya replies at 9:45 AM** (19 minutes after Nikita, 1140 seconds):
- `touchpoint_propensity`: replied within 4h -> `update_beta(7.0, 18.0, success=True)` -> (8.0, 18.0). Mean: 0.28 -> 0.31.
- `response_speed`: reply time 1140s < Nikita's delay 4248s -> fast -> `update_beta(8.0, 4.0, success=True, weight=0.5)` -> (8.5, 4.0). Mean: 0.67 -> 0.68.

**Scoring**: ScoreAnalyzer returns `delta=+1.5, confidence=0.7`.
- `mood_baseline`: positive delta -> `update_beta(11.2, 9.8, success=True, weight=0.7*0.3=0.21)` -> (11.41, 9.8). Mean: 0.53 -> 0.54.

After 30 days, Maya's Nikita is measurably more proactive and responsive than a user
who ignores half their touchpoints. No tuning required -- the posteriors adapt automatically.

---

## Appendix B: Complete File Change Inventory

### New files

| File | Lines | Purpose |
|------|-------|---------|
| `nikita/bayesian/__init__.py` | 5 | Package init |
| `nikita/bayesian/state.py` | 80 | CHAPTER_PRIORS, apply_decay, cold_start, on_chapter_advance |
| `nikita/bayesian/updater.py` | 60 | update_beta + per-trigger update methods |
| `tests/bayesian/test_state.py` | 60 | State model + decay tests |
| `tests/bayesian/test_updater.py` | 80 | Update logic + property tests |
| **Total** | **~285** | |

### Modified files

| File | Change | Lines |
|------|--------|-------|
| `nikita/touchpoints/scheduler.py` | `user_state` param on 3 methods, modify `_get_initiation_rate` | 15 |
| `nikita/touchpoints/engine.py` | Load/save bayesian_state, pass through pipeline, outcome tracking | 25 |
| `nikita/touchpoints/silence.py` | `user_state` param, modify base_rate source | 8 |
| `nikita/agents/text/timing.py` | `user_state` param, modify mean calculation | 12 |
| `nikita/life_simulation/event_generator.py` | Inject mood context into existing prompt | 10 |
| `nikita/life_simulation/mood_calculator.py` | `user_state` param, modify valence base | 8 |
| `nikita/pipeline/orchestrator.py` | Hooks for on_user_reply and on_scored_interaction | 15 |
| `nikita/db/models/user.py` | Add `bayesian_state` JSONB column | 1 |
| `nikita/db/repositories/user_repository.py` | Add get/save methods | 10 |
| `nikita/config/settings.py` | Add `bayesian_enabled`, `bayesian_rollout_percent` | 4 |
| **Total modified** | | **~108** |

### DB migrations

| Migration | SQL |
|-----------|-----|
| Add JSONB column | `ALTER TABLE users ADD COLUMN bayesian_state JSONB DEFAULT NULL;` |
| Add partial index | `CREATE INDEX idx_users_bayesian_active ON users ((bayesian_state IS NOT NULL)) WHERE bayesian_state IS NOT NULL;` |
| Add shadow log table | See Section 7 |

### Total impact

- ~285 lines new code (including tests)
- ~108 lines modified across 10 files
- 1 new JSONB column (nullable)
- 1 new logging table (shadow mode, temporary)
- 0 new cron jobs in Phase 1 (1 in Phase 2)
- 0 new LLM calls
- 0 new infrastructure dependencies
- 0 new Python package dependencies (uses stdlib `random.betavariate`)

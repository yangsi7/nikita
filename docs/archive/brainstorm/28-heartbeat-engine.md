# Doc 28 -- The Heartbeat Engine

## 1. Executive Summary

The Heartbeat Engine replaces Nikita's hardcoded `random.uniform()` and `random.random()` decisions with personalized, learning Beta distributions. Every 5 minutes, the existing pg_cron job fires `/api/v1/tasks/touchpoints`. Today it rolls static dice. After this change, it samples from per-user posteriors shaped by actual player behavior.

**Zero LLM calls.** No new infra. 10 floats of state per user in a JSONB column. Falls back to current behavior if anything fails. Thompson Sampling naturally produces the narrative arc: early chapters are unpredictable (high variance), later chapters are consistent (low variance) -- the math creates the character progression for free.

---

## 2. The 5 Beta Distributions

Each user gets 5 `Beta(alpha, beta)` distributions = 10 floats (80 bytes).

### 2.1 Touchpoint Propensity (tp)

**Controls**: Probability Nikita initiates contact in a time slot.
**Replaces**: `random.uniform(config.initiation_rate_min, config.initiation_rate_max)` at `scheduler.py:335`.

| Chapter | Current range | Prior alpha | Prior beta | Mean |
|---------|--------------|-------------|------------|------|
| 1       | 0.15-0.20    | 3           | 17         | 0.15 |
| 2       | 0.20-0.25    | 4           | 16         | 0.20 |
| 3-5     | 0.25-0.30    | 5           | 15         | 0.25 |

**Updates**: User replies within 2h -> `alpha += 1`. No reply after 4h -> `beta += 1`.

### 2.2 Response Timing (rt)

**Controls**: Where in the chapter's delay range Nikita's reply falls (0=fastest, 1=slowest).
**Replaces**: `mean = (min_sec + max_sec) / 2` at `timing.py:98`. Sampling: `delay = min_sec + sample * (max_sec - min_sec)`.

| Chapter | Range (sec)   | Prior alpha | Prior beta | Mean fraction |
|---------|--------------|-------------|------------|---------------|
| 1       | 600-28800    | 2           | 2          | 0.50          |
| 2       | 300-14400    | 2           | 2          | 0.50          |
| 3-4     | 300-7200/3600| 3           | 2          | 0.60          |
| 5       | 300-1800     | 4           | 2          | 0.67          |

**Updates**: User replies faster than Nikita's delay -> `beta += 0.5` (speed up). User replies slower -> `alpha += 0.5` (slow down). Higher alpha = higher fraction = longer delay.

### 2.3 Strategic Silence Rate (ss)

**Controls**: Probability of intentionally skipping a touchpoint for dramatic effect.
**Replaces**: `StrategicSilence.DEFAULT_RATES` at `silence.py:59-65`. Emotional modifier still multiplies the sampled rate.

| Chapter | Current rate | Prior alpha | Prior beta | Mean |
|---------|-------------|-------------|------------|------|
| 1       | 0.10        | 2           | 18         | 0.10 |
| 3       | 0.15        | 3           | 17         | 0.15 |
| 5       | 0.20        | 4           | 16         | 0.20 |

**Updates**: User re-engages within 12h after silence -> `alpha += 1` (silence worked). No reply for 24h -> `beta += 1` (backfired).

### 2.4 Mood Valence Baseline (mv)

**Controls**: Nikita's default emotional positivity between conversations.
**Replaces**: Hardcoded 0.5 neutral at `mood_calculator.py:27` and `engine.py:267-271`.

**Prior**: `Beta(10, 10)` all chapters. High pseudocount = slow drift. Uses the **currently ignored** `confidence` field from `ResponseAnalysis` at `scoring/models.py:79-84`.

**Updates**: After scoring with `confidence > 0.6`: positive avg delta -> `alpha += confidence * 0.3`. Negative -> `beta += confidence * 0.3`.

### 2.5 Event Valence Bias (ev)

**Controls**: Whether Nikita's daily life events skew positive or negative.
**Replaces**: Unbiased event generation in `event_generator.py:82-122`. Adds a bias line to the existing LLM prompt (zero extra LLM calls).

**Prior**: `Beta(5, 5)` all chapters. **Updates**: 3+ user replies/day -> `alpha += 0.5`. Zero replies -> `beta += 0.5`.

---

## 3. The Heartbeat Loop

### 3.1 Current Flow
```
pg_cron (5 min) -> /api/v1/tasks/touchpoints
  -> TouchpointEngine.deliver_due_touchpoints()     # engine.py:108
    -> scheduler.evaluate_user()                     # scheduler.py:56
      -> _get_initiation_rate() = random.uniform()   # REPLACE
      -> _should_trigger() = random.random() < rate  # REPLACE
    -> silence.apply_strategic_silence()             # silence.py:79
      -> base_rate from DEFAULT_RATES                # REPLACE
    -> generator.generate()                          # LLM call (KEEP)
    -> _send_telegram_message()                      # KEEP
```

### 3.2 New Flow
```
pg_cron (5 min) -> /api/v1/tasks/touchpoints
  -> for each active user:
    state = load bayesian_state JSONB (or cold_start)
    apply_decay(state, hours_since_update)

    TOUCHPOINT:  sample = Beta(tp.a, tp.b)  -> clamp [0.10, 0.50]
    SILENCE:     sample = Beta(ss.a, ss.b) * emotional_modifier -> clamp [0.05, 0.50]
    TIMING:      sample = Beta(rt.a, rt.b)  -> delay = min + sample * range
    MOOD:        sample = Beta(mv.a, mv.b)  -> default valence if no active state
    EVENT BIAS:  sample = Beta(ev.a, ev.b)  -> injected into event prompt

    (rest of pipeline unchanged)
    record observation for async posterior update
```

---

## 4. Decision Flow per User per Tick

```
LOAD bayesian_state (JSONB)
  NULL? -> cold_start(chapter)
  |
  APPLY DECAY (if hours_since_update > grace_period)
  |
  DEDUP CHECK (existing, unchanged)
  |
  TIME SLOT CHECK (existing, unchanged)
  |
  TOUCHPOINT: tp.sample() < 0.10 floor? -> SKIP
  |
  SILENCE: ss.sample() * emotional_mod > random() -> SILENCE
  |
  TIMING: rt.sample() -> delay_seconds
  |
  MOOD: no active state? mv.sample() -> valence baseline
  |
  GENERATE + DELIVER (existing)
  |
  RECORD observation
```

**Safety rails** -- every sample is clamped:

| Dist | Floor | Ceiling | Source |
|------|-------|---------|--------|
| tp   | 0.10  | 0.50    | models.py initiation_rate bounds |
| rt   | min_sec | max_sec | timing.py TIMING_RANGES |
| ss   | 0.05  | 0.50    | silence.py rates capped |
| mv   | 0.15  | 0.85    | prevent extreme mood lock-in |
| ev   | 0.20  | 0.80    | prevent all-bad/all-good days |

---

## 5. Update Rules

Updates happen **asynchronously** when outcomes are observed, not during the heartbeat tick.

| Observation | Trigger | Updates |
|-------------|---------|---------|
| User replied to touchpoint (<2h) | Message received in `orchestrator.py` | tp(+1), rt(+/-0.5) |
| Touchpoint ignored (>4h) | Checked in next heartbeat tick | tp(-1) |
| Re-engaged after silence (<12h) | Next touchpoint eval for user | ss(+1) |
| Went cold after silence (>24h) | Next touchpoint eval for user | ss(-1) |
| Scored interaction | After scoring stage in `orchestrator.py` | mv(+/-conf*0.3) |
| Daily engagement tally | Midnight cron job | ev(+/-0.5) |

```python
# Core update logic (nikita/bayesian/updater.py)
class BayesianUpdater:
    async def on_user_reply(self, state, reply_delay, touchpoint_delay):
        if reply_delay < 7200:
            state.tp.alpha += 1           # user wanted contact
        if touchpoint_delay and reply_delay < touchpoint_delay:
            state.rt.beta += 0.5          # user fast -> Nikita faster
        elif touchpoint_delay:
            state.rt.alpha += 0.5         # user slow -> Nikita slower

    async def on_touchpoint_ignored(self, state):
        state.tp.beta += 1               # user didn't want contact

    async def on_silence_outcome(self, state, re_engaged: bool):
        state.ss.update(success=re_engaged)

    async def on_scored_interaction(self, state, avg_delta, confidence):
        if confidence > 0.6:
            weight = confidence * 0.3
            state.mv.update(success=(avg_delta > 0), weight=weight)

    async def on_daily_engagement(self, state, reply_count):
        if reply_count >= 3:   state.ev.alpha += 0.5
        elif reply_count == 0: state.ev.beta += 0.5
```

---

## 6. Cold Start

When `bayesian_state IS NULL`, initialize from chapter priors that reproduce current hardcoded behavior:

```python
CHAPTER_PRIORS = {
    1: {"tp_a": 3, "tp_b": 17, "rt_a": 2, "rt_b": 2, "ss_a": 2, "ss_b": 18},
    2: {"tp_a": 4, "tp_b": 16, "rt_a": 2, "rt_b": 2, "ss_a": 2.4, "ss_b": 17.6},
    3: {"tp_a": 5, "tp_b": 15, "rt_a": 3, "rt_b": 2, "ss_a": 3, "ss_b": 17},
    4: {"tp_a": 5, "tp_b": 15, "rt_a": 3, "rt_b": 2, "ss_a": 3.6, "ss_b": 16.4},
    5: {"tp_a": 5, "tp_b": 15, "rt_a": 4, "rt_b": 2, "ss_a": 4, "ss_b": 16},
}
# mv: always Beta(10,10). ev: always Beta(5,5).
```

**Pseudocount strength**: tp/ss = 20 total (shifts after ~4 observations). rt = 4 total (shifts after ~2). mv = 20 (slow drift). ev = 10 (moderate).

**Chapter transitions**: Blend 70% current posterior + 30% new chapter prior. Don't discard learned behavior.

---

## 7. Decay Mechanism

Inactive users decay toward chapter priors. Uses existing `GRACE_PERIODS` from `constants.py:156-162`.

```python
def apply_decay(state, hours_since_update, chapter):
    grace = {1: 8, 2: 16, 3: 24, 4: 48, 5: 72}[chapter]
    if hours_since_update <= grace:
        return state  # no decay during grace period

    DECAY_PER_HOUR = 0.005  # 0.5%/hr = ~11%/day = ~55%/week
    excess = hours_since_update - grace
    factor = max(0.0, 1.0 - DECAY_PER_HOUR * excess)

    # Blend each dist toward its prior
    for name in ["tp", "ss", "rt"]:
        dist = getattr(state, name)
        prior_a, prior_b = CHAPTER_PRIORS[chapter][f"{name}_a"], ...
        dist.alpha = factor * dist.alpha + (1 - factor) * prior_a
        dist.beta  = factor * dist.beta  + (1 - factor) * prior_b

    # mv/ev decay toward neutral
    state.mv.alpha = factor * state.mv.alpha + (1 - factor) * 10.0
    state.mv.beta  = factor * state.mv.beta  + (1 - factor) * 10.0
    state.ev.alpha = factor * state.ev.alpha + (1 - factor) * 5.0
    state.ev.beta  = factor * state.ev.beta  + (1 - factor) * 5.0
    return state
```

| Hours Inactive (Ch3, 24h grace) | Factor | State |
|--------------------------------|--------|-------|
| 0-24h | 1.00 | Fully personalized |
| 48h   | 0.88 | 88% personal |
| 72h   | 0.76 | 76% personal |
| 1 week | 0.16 | Mostly prior |
| 2 weeks | 0.00 | Fully reset |

---

## 8. DB Schema

### Single JSONB column on existing users table:

```sql
ALTER TABLE users ADD COLUMN bayesian_state JSONB DEFAULT NULL;
CREATE INDEX idx_users_bayesian_not_null
  ON users ((bayesian_state IS NOT NULL)) WHERE bayesian_state IS NOT NULL;
```

```json
{
  "tp": {"alpha": 5.0, "beta": 16.0},
  "rt": {"alpha": 2.0, "beta": 2.5},
  "ss": {"alpha": 2.4, "beta": 17.6},
  "mv": {"alpha": 10.24, "beta": 10.0},
  "ev": {"alpha": 5.5, "beta": 5.0},
  "last_updated": "2026-02-17T10:30:00Z",
  "total_observations": 42
}
```

SQLAlchemy: add `bayesian_state = Column(JSON, nullable=True)` to `nikita/db/models/user.py`.
Repository: add `get_bayesian_state()` / `save_bayesian_state()` to `nikita/db/repositories/user_repository.py`.

---

## 9. pg_cron Configuration

**No new cron for the heartbeat** -- uses the existing 5-minute `/api/v1/tasks/touchpoints` job.

**One new daily cron** for event valence updates:
```sql
SELECT cron.schedule('bayesian-daily', '0 0 * * *',
  $$SELECT net.http_post(url := '.../api/v1/tasks/bayesian-daily')$$);
```

Touchpoint-ignored detection piggybacks on the existing 5-minute tick: query delivered touchpoints >4h old with no user reply, update posteriors, mark as processed.

---

## 10. Graceful Degradation

| Failure | Fallback |
|---------|----------|
| JSONB NULL/corrupted | Cold start from chapter priors |
| NumPy unavailable | `random.betavariate(a, b)` (stdlib) |
| Alpha/beta <= 0 | Clamp to 0.01 |
| Sample outside rails | Clamp to floor/ceiling |
| Entire module crashes | try/except -> original `random.uniform()` |
| DB write fails | Log error, continue (state lost but safe) |

Every integration point wraps Bayesian logic:
```python
def _get_initiation_rate(self, config, bayesian_state=None):
    try:
        if bayesian_state and "tp" in bayesian_state:
            sample = np.random.beta(bayesian_state["tp"]["alpha"],
                                     bayesian_state["tp"]["beta"])
            return max(0.10, min(0.50, sample))
    except Exception:
        pass
    return random.uniform(config.initiation_rate_min, config.initiation_rate_max)
```

**Shadow mode** (first 2 weeks): compute and log Bayesian decisions but use random decisions. Compare in analytics before switching.

---

## 11. Integration Points

### Files Modified

| File | Change |
|------|--------|
| `nikita/touchpoints/scheduler.py:335` | `_get_initiation_rate()` samples from Beta if state available |
| `nikita/touchpoints/scheduler.py:346` | `_should_trigger()` uses Bayesian sample |
| `nikita/touchpoints/engine.py:108-136` | Load bayesian_state, pass through pipeline |
| `nikita/touchpoints/engine.py:392-460` | `evaluate_and_schedule_for_user()` loads state |
| `nikita/touchpoints/silence.py:79-100` | `apply_strategic_silence()` uses Beta sample as base rate |
| `nikita/agents/text/timing.py:67-118` | `calculate_delay()` uses Beta sample for mean |
| `nikita/life_simulation/event_generator.py:124-233` | Inject event valence bias into prompt |
| `nikita/life_simulation/mood_calculator.py:71-77` | Accept valence baseline from Beta |
| `nikita/pipeline/orchestrator.py` | Hooks for `on_user_reply()` and `on_scored_interaction()` |
| `nikita/db/models/user.py` | Add `bayesian_state` JSONB column |
| `nikita/db/repositories/user_repository.py` | Add get/save methods (~10 lines) |
| `nikita/api/routes/tasks.py` | Add `/tasks/bayesian-daily` endpoint |

### New Files

| File | Purpose | ~Lines |
|------|---------|--------|
| `nikita/bayesian/__init__.py` | Package init | 5 |
| `nikita/bayesian/engine.py` | BayesianUserState, BetaParams, priors, decay | 150 |
| `nikita/bayesian/updater.py` | BayesianUpdater (all update methods) | 120 |
| `nikita/bayesian/sampler.py` | Sampling with safety rails + NumPy fallback | 60 |

### Migration Path

1. **Shadow mode (weeks 1-2)**: Deploy code, collect observations, log comparisons
2. **Gradual rollout (weeks 3-4)**: Enable for 10% of users by ID hash
3. **Full rollout (week 5+)**: Enable for all, remove shadow mode

---

## Appendix: Worked Example

**User "Alex", Chapter 2, Day 5.** Cold start: `tp=Beta(4,16) rt=Beta(2,2) ss=Beta(2.4,17.6)`.

**8:15 AM tick**: tp.sample()=0.23 (>0.10 floor, initiate). ss.sample()=0.09 (no silence). rt.sample()=0.61 -> delay=8901s (~2.5h). Nikita messages at ~10:45 AM.

**Alex replies at 11:30 AM** (2700s, faster than 8901s delay):
- tp: alpha 4->5 (user wanted contact, mean 0.20->0.24)
- rt: beta 2->2.5 (user fast, Nikita faster, mean 0.50->0.44)

**Scoring**: confidence=0.8, avg_delta=+2.5 -> mv: alpha 10->10.24 (slightly happier)

**End of day**: 4 replies -> ev: alpha 5->5.5 (more positive events tomorrow)

After 1 week, Alex's Nikita is measurably more proactive and responsive than a user who replies once daily. **Thompson Sampling produces this automatically** -- no tuning required.

**Why Thompson Sampling**: MAP is deterministic (no exploration). UCB over-explores. Thompson Sampling's variance naturally matches Nikita's character arc -- high variance in Chapter 1 (unpredictable), low variance in Chapter 5 (reliable). The math *is* the narrative.

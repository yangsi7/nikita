# 19 — Unified Bayesian Architecture: Synthesis of All Phase 2 Ideas

**Date**: 2026-02-16
**Type**: Synthesis / Capstone Architecture Document
**Phase**: 2 (Ideas — Final Synthesis)
**Inputs**: ALL Phase 2 documents (12-18) plus Phase 1 research (01-11)
**Outputs**: Foundation for Phase 3 evaluations (20-23) and Phase 4 synthesis (24-26)

---

## 1. Executive Summary

This document synthesizes all seven Phase 2 brainstorm documents into a single coherent architecture for Nikita's Bayesian inference engine. The unified architecture replaces deterministic scoring, hardcoded behavioral rules, and per-message LLM analysis with a mathematically principled system that learns from player behavior and makes decisions at near-zero cost.

**The Vision in One Paragraph:**

Every player message triggers a cascade of Bayesian updates: Beta posteriors for relationship metrics absorb new evidence, a Dynamic Bayesian Network propagates emotional state through a causal graph, Thompson Sampling selects behavioral parameters (skip rate, timing, tone), Dirichlet posteriors refine vice preferences, and Bayesian surprise decides whether the situation warrants LLM analysis. The entire computation completes in under 25 milliseconds, costs nothing in tokens, and produces per-player personalized behavior that evolves with the relationship.

### 1.1 Source Documents Synthesized

| Doc | Title | Key Contribution to Unified Architecture |
|---|---|---|
| 12 | Bayesian Player Model | Beta posteriors for 4 metrics, full player state schema |
| 13 | Nikita's DBN | Causal graph: perceived_threat → attachment → defense → emotional_tone |
| 14 | Event Generation | Thompson Sampling for event selection, Bayesian surprise as conflict trigger |
| 15 | Integration Architecture | Module structure, pipeline integration, API changes |
| 16 | Emotional Contagion | Bidirectional emotion transfer model, empathy as inference |
| 17 | Controlled Randomness | How to inject personality-coherent variability |
| 18 | Vice Discovery | Dirichlet posterior over 8 vice categories, targeted probing |

---

## 2. The Single Bayesian State Object

### 2.1 Complete Schema

Every player has exactly one `BayesianPlayerState` object, stored as JSONB in the `bayesian_states` table. This is the single source of truth for all Bayesian inference.

```python
"""nikita/bayesian/state.py — Complete Bayesian state for one player."""

import numpy as np
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class BayesianPlayerState:
    """Complete Bayesian state for a single player.

    This object is loaded from DB at the start of each message,
    updated by the BayesianEngine, and saved back to DB.

    Total serialized size: ~2-3 KB per player.
    """

    # ─── IDENTITY ────────────────────────────────────────
    user_id: str = ""
    chapter: int = 1

    # ─── RELATIONSHIP METRICS (Beta posteriors) ──────────
    # Each metric is modeled as Beta(alpha, beta)
    # Prior mean = alpha / (alpha + beta), mapped to [0, 100] scale
    # From Doc 12: Bayesian Player Model
    intimacy_alpha: float = 5.5
    intimacy_beta: float = 4.5     # Prior mean: 0.55 → 55/100
    passion_alpha: float = 4.0
    passion_beta: float = 6.0      # Prior mean: 0.40 → 40/100
    trust_alpha: float = 5.0
    trust_beta: float = 5.0        # Prior mean: 0.50 → 50/100
    secureness_alpha: float = 4.0
    secureness_beta: float = 6.0   # Prior mean: 0.40 → 40/100

    # ─── SKIP DECISION (Beta posterior) ──────────────────
    # P(should_skip) ~ Beta(skip_alpha, skip_beta)
    # From Doc 06/14: Thompson Sampling for skip rate
    skip_alpha: float = 3.0
    skip_beta: float = 7.0         # Prior mean: 0.30 (30% skip rate)

    # ─── RESPONSE TIMING (Dirichlet posterior) ───────────
    # Distribution over timing buckets
    # From Doc 06: Posterior-predictive timing
    timing_dirichlet: np.ndarray = field(
        default_factory=lambda: np.array([0.5, 1.0, 2.0, 3.0, 2.5])
    )

    # ─── EVENT PREFERENCES (nested Beta posteriors) ──────
    # From Doc 14: Bayesian event generation
    event_selector_state: Optional[dict] = None

    # ─── VICE PROFILE (Dirichlet posterior) ──────────────
    # Distribution over 8 vice categories
    # From Doc 18: Bayesian vice discovery
    vice_dirichlet: np.ndarray = field(
        default_factory=lambda: np.array([2.0] * 8)
    )

    # ─── EMOTIONAL STATE (DBN belief state) ──────────────
    # Full posterior over hidden emotional variables
    # From Doc 13: Nikita's DBN
    emotional_belief: Optional[dict] = None

    # ─── ATTACHMENT MODEL ────────────────────────────────
    # Dirichlet over attachment styles: secure, anxious, avoidant, disorganized
    # From Doc 13/16: Attachment as latent variable
    attachment_dirichlet: np.ndarray = field(
        default_factory=lambda: np.array([3.0, 4.0, 2.0, 1.0])
    )

    # ─── EMOTIONAL CONTAGION STATE ───────────────────────
    # Player's inferred emotional state (what Nikita thinks the player feels)
    # From Doc 16: Bidirectional emotion transfer
    player_emotion_estimate: np.ndarray = field(
        default_factory=lambda: np.array([0.3, 0.3, 0.1, 0.15, 0.1, 0.05])
    )
    # [positive, neutral, concerned, frustrated, sad, angry]

    # ─── RANDOMNESS PARAMETERS ───────────────────────────
    # From Doc 17: Controlled randomness
    behavioral_temperature: float = 0.8  # 0=deterministic, 1=maximum randomness
    consistency_score: float = 0.5       # How consistent has behavior been

    # ─── SURPRISE TRACKING ───────────────────────────────
    # From Doc 14: Bayesian surprise
    surprise_history: list[float] = field(default_factory=list)
    tension_level: float = 0.0

    # ─── METADATA ────────────────────────────────────────
    total_messages: int = 0
    last_surprise: float = 0.0
    messages_since_last_llm: int = 0
    last_updated: str = ""
    created_at: str = ""

    # ─── DERIVED PROPERTIES ──────────────────────────────

    @property
    def composite_score_estimate(self) -> float:
        """Estimate composite score from Beta posterior means.

        Uses the same weights as engine/constants.py:
        0.30 * intimacy + 0.25 * passion + 0.25 * trust + 0.20 * secureness
        """
        intimacy = self.intimacy_alpha / (self.intimacy_alpha + self.intimacy_beta)
        passion = self.passion_alpha / (self.passion_alpha + self.passion_beta)
        trust = self.trust_alpha / (self.trust_alpha + self.trust_beta)
        secureness = self.secureness_alpha / (self.secureness_alpha + self.secureness_beta)

        return 100 * (0.30 * intimacy + 0.25 * passion + 0.25 * trust + 0.20 * secureness)

    @property
    def dominant_attachment_style(self) -> str:
        """Most likely attachment style from Dirichlet posterior."""
        styles = ["secure", "anxious", "avoidant", "disorganized"]
        return styles[int(np.argmax(self.attachment_dirichlet))]

    @property
    def dominant_vice(self) -> str:
        """Most prominent vice category."""
        vices = [
            "intellectual_dominance", "risk_taking", "substances", "sexuality",
            "emotional_intensity", "rule_breaking", "dark_humor", "vulnerability",
        ]
        return vices[int(np.argmax(self.vice_dirichlet))]

    @property
    def metric_uncertainties(self) -> dict[str, float]:
        """Posterior variance for each metric. High = uncertain."""
        def beta_var(a, b):
            return (a * b) / ((a + b) ** 2 * (a + b + 1))
        return {
            "intimacy": beta_var(self.intimacy_alpha, self.intimacy_beta),
            "passion": beta_var(self.passion_alpha, self.passion_beta),
            "trust": beta_var(self.trust_alpha, self.trust_beta),
            "secureness": beta_var(self.secureness_alpha, self.secureness_beta),
        }

    # ─── SERIALIZATION ───────────────────────────────────

    def to_json(self) -> dict:
        """Serialize to JSONB-compatible dict."""
        return {
            "metrics": {
                "intimacy": {"alpha": self.intimacy_alpha, "beta": self.intimacy_beta},
                "passion": {"alpha": self.passion_alpha, "beta": self.passion_beta},
                "trust": {"alpha": self.trust_alpha, "beta": self.trust_beta},
                "secureness": {"alpha": self.secureness_alpha, "beta": self.secureness_beta},
            },
            "skip": {"alpha": self.skip_alpha, "beta": self.skip_beta},
            "timing": {"dirichlet": self.timing_dirichlet.tolist()},
            "events": self.event_selector_state,
            "vice": {"dirichlet": self.vice_dirichlet.tolist()},
            "emotional": self.emotional_belief,
            "attachment": {"dirichlet": self.attachment_dirichlet.tolist()},
            "player_emotion": self.player_emotion_estimate.tolist(),
            "randomness": {
                "temperature": self.behavioral_temperature,
                "consistency": self.consistency_score,
            },
            "surprise": {
                "history": self.surprise_history[-7:],  # Last 7 days
                "tension": self.tension_level,
            },
            "meta": {
                "chapter": self.chapter,
                "total_messages": self.total_messages,
                "last_surprise": self.last_surprise,
                "messages_since_llm": self.messages_since_last_llm,
                "last_updated": self.last_updated,
                "created_at": self.created_at,
            },
        }

    @classmethod
    def from_json(cls, user_id: str, data: dict) -> "BayesianPlayerState":
        """Deserialize from JSONB."""
        metrics = data.get("metrics", {})
        state = cls(
            user_id=user_id,
            chapter=data.get("meta", {}).get("chapter", 1),
            # Metrics
            intimacy_alpha=metrics.get("intimacy", {}).get("alpha", 5.5),
            intimacy_beta=metrics.get("intimacy", {}).get("beta", 4.5),
            passion_alpha=metrics.get("passion", {}).get("alpha", 4.0),
            passion_beta=metrics.get("passion", {}).get("beta", 6.0),
            trust_alpha=metrics.get("trust", {}).get("alpha", 5.0),
            trust_beta=metrics.get("trust", {}).get("beta", 5.0),
            secureness_alpha=metrics.get("secureness", {}).get("alpha", 4.0),
            secureness_beta=metrics.get("secureness", {}).get("beta", 6.0),
            # Skip
            skip_alpha=data.get("skip", {}).get("alpha", 3.0),
            skip_beta=data.get("skip", {}).get("beta", 7.0),
            # Timing
            timing_dirichlet=np.array(data.get("timing", {}).get("dirichlet", [0.5, 1.0, 2.0, 3.0, 2.5])),
            # Events
            event_selector_state=data.get("events"),
            # Vice
            vice_dirichlet=np.array(data.get("vice", {}).get("dirichlet", [2.0] * 8)),
            # Emotional
            emotional_belief=data.get("emotional"),
            # Attachment
            attachment_dirichlet=np.array(data.get("attachment", {}).get("dirichlet", [3.0, 4.0, 2.0, 1.0])),
            # Player emotion
            player_emotion_estimate=np.array(data.get("player_emotion", [0.3, 0.3, 0.1, 0.15, 0.1, 0.05])),
            # Randomness
            behavioral_temperature=data.get("randomness", {}).get("temperature", 0.8),
            consistency_score=data.get("randomness", {}).get("consistency", 0.5),
            # Surprise
            surprise_history=data.get("surprise", {}).get("history", []),
            tension_level=data.get("surprise", {}).get("tension", 0.0),
            # Meta
            total_messages=data.get("meta", {}).get("total_messages", 0),
            last_surprise=data.get("meta", {}).get("last_surprise", 0.0),
            messages_since_last_llm=data.get("meta", {}).get("messages_since_llm", 0),
            last_updated=data.get("meta", {}).get("last_updated", ""),
            created_at=data.get("meta", {}).get("created_at", ""),
        )
        return state

    @classmethod
    def default_for_chapter(cls, user_id: str, chapter: int) -> "BayesianPlayerState":
        """Create a new state with chapter-appropriate priors."""
        # Chapter 1: Low trust/secureness, moderate intimacy/passion
        # Chapter 5: High everything
        chapter_priors = {
            1: {"int": (5.5, 4.5), "pas": (4.0, 6.0), "tru": (4.0, 6.0), "sec": (3.5, 6.5),
                "skip": (3.0, 7.0), "temp": 0.9},
            2: {"int": (6.0, 4.0), "pas": (5.0, 5.0), "tru": (5.0, 5.0), "sec": (4.5, 5.5),
                "skip": (2.5, 7.5), "temp": 0.8},
            3: {"int": (6.5, 3.5), "pas": (5.5, 4.5), "tru": (6.0, 4.0), "sec": (5.5, 4.5),
                "skip": (2.0, 8.0), "temp": 0.7},
            4: {"int": (7.0, 3.0), "pas": (6.0, 4.0), "tru": (7.0, 3.0), "sec": (6.5, 3.5),
                "skip": (1.5, 8.5), "temp": 0.5},
            5: {"int": (8.0, 2.0), "pas": (7.0, 3.0), "tru": (8.0, 2.0), "sec": (7.5, 2.5),
                "skip": (0.5, 9.5), "temp": 0.3},
        }
        p = chapter_priors.get(chapter, chapter_priors[1])
        now = datetime.utcnow().isoformat()
        return cls(
            user_id=user_id,
            chapter=chapter,
            intimacy_alpha=p["int"][0], intimacy_beta=p["int"][1],
            passion_alpha=p["pas"][0], passion_beta=p["pas"][1],
            trust_alpha=p["tru"][0], trust_beta=p["tru"][1],
            secureness_alpha=p["sec"][0], secureness_beta=p["sec"][1],
            skip_alpha=p["skip"][0], skip_beta=p["skip"][1],
            behavioral_temperature=p["temp"],
            created_at=now,
            last_updated=now,
        )
```

### 2.2 State Size Budget

```
Component                    Parameters    Bytes (est.)
─────────────────────────────────────────────────────
Metric posteriors (4 x 2)   8 floats      64
Skip posterior (2)           2 floats      16
Timing Dirichlet (5)        5 floats      40
Event priors (~15 x 2)      30 floats     240
Vice Dirichlet (8)          8 floats      64
Emotional belief (~30)      30 floats     240
Attachment Dirichlet (4)    4 floats      32
Player emotion (6)          6 floats      48
Randomness params (2)       2 floats      16
Surprise history (7)        7 floats      56
Metadata                    ~6 fields     100
─────────────────────────────────────────────────────
TOTAL                       ~108 params   ~916 bytes

With JSON overhead (~2x):   ~1.8 KB per player
At 10,000 players:          ~18 MB total
```

---

## 3. Data Flow Diagram: End-to-End

### 3.1 Complete Message Processing Flow

```
PLAYER MESSAGE ARRIVES
         │
         v
    ┌─────────────────────────────────────────────────────┐
    │  1. FEATURE EXTRACTION (rule-based, <1ms)           │
    │                                                      │
    │  Input: raw message text                             │
    │  Output: {                                           │
    │    sentiment: float,     # NLP or keyword-based     │
    │    length: int,          # character count           │
    │    is_question: bool,    # ends with "?"             │
    │    topics: list[str],    # keyword matching          │
    │    hours_since_last: float,  # from last message    │
    │    engagement_with_events: list[dict],  # Doc 14    │
    │  }                                                   │
    └──────────────┬──────────────────────────────────────┘
                   │
                   v
    ┌─────────────────────────────────────────────────────┐
    │  2. STATE LOAD (DB read, <5ms)                      │
    │                                                      │
    │  SELECT state_json FROM bayesian_states              │
    │  WHERE user_id = ?                                   │
    │                                                      │
    │  Deserialize → BayesianPlayerState                   │
    └──────────────┬──────────────────────────────────────┘
                   │
                   v
    ┌─────────────────────────────────────────────────────┐
    │  3. POSTERIOR UPDATES (all sub-models, <1ms)         │
    │                                                      │
    │  a) Metric posteriors: update Beta(α,β) for each    │
    │     metric based on observed engagement signals      │
    │     [Doc 12: Bayesian Player Model]                  │
    │                                                      │
    │  b) Event engagement: update event type priors       │
    │     [Doc 14: Event Generation]                       │
    │                                                      │
    │  c) Vice signals: update Dirichlet from detected     │
    │     vice keywords in message                         │
    │     [Doc 18: Vice Discovery]                         │
    │                                                      │
    │  d) Attachment style: update Dirichlet based on      │
    │     behavioral patterns (clinginess, avoidance, etc) │
    │     [Doc 13: Nikita DBN]                             │
    │                                                      │
    │  e) Emotional contagion: infer player's emotion      │
    │     from message features, update player estimate    │
    │     [Doc 16: Emotional Contagion]                    │
    └──────────────┬──────────────────────────────────────┘
                   │
                   v
    ┌─────────────────────────────────────────────────────┐
    │  4. DBN FORWARD INFERENCE (5-15ms)                   │
    │                                                      │
    │  Input: updated posteriors + observations            │
    │  Process: propagate through causal graph             │
    │     perceived_threat → attachment_activation →       │
    │     defense_mode → emotional_tone → response_style   │
    │  Output: full belief state over all hidden vars      │
    │     [Doc 13: Nikita DBN]                             │
    └──────────────┬──────────────────────────────────────┘
                   │
                   v
    ┌─────────────────────────────────────────────────────┐
    │  5. THOMPSON SAMPLING DECISIONS (<1ms)               │
    │                                                      │
    │  a) Skip: sample from Beta(skip_α, skip_β)          │
    │     [Doc 06/14: Thompson Sampling]                   │
    │                                                      │
    │  b) Timing: sample from Dirichlet, pick bucket      │
    │     [Doc 06: Posterior-predictive timing]             │
    │                                                      │
    │  c) Event types: Thompson Sample for today's events  │
    │     [Doc 14: Bayesian Event Selection]               │
    │                                                      │
    │  d) Vice focus: top-3 from Dirichlet                │
    │     [Doc 18: Vice Discovery]                         │
    │                                                      │
    │  e) Behavioral temperature: modulate randomness      │
    │     [Doc 17: Controlled Randomness]                  │
    └──────────────┬──────────────────────────────────────┘
                   │
                   v
    ┌─────────────────────────────────────────────────────┐
    │  6. SURPRISE + ESCALATION (<1ms)                     │
    │                                                      │
    │  a) Compute Bayesian surprise for this message       │
    │  b) Update surprise history and tension level        │
    │  c) Decide escalation tier:                          │
    │     Tier 1 (<2.0): Pure Bayesian (no LLM)           │
    │     Tier 2 (2.0-3.0): Quick Sonnet check            │
    │     Tier 3 (>3.0): Deep Opus analysis               │
    │     [Doc 14: Surprise as trigger]                    │
    │     [Doc 15: Escalation architecture]                │
    └──────────────┬──────────────────────────────────────┘
                   │
                   v
    ┌─────────────────────────────────────────────────────┐
    │  7. STATE SAVE (DB write, <5ms)                      │
    │                                                      │
    │  UPDATE bayesian_states SET state_json = ?           │
    │  WHERE user_id = ?                                   │
    └──────────────┬──────────────────────────────────────┘
                   │
                   v
    ┌─────────────────────────────────────────────────────┐
    │  8. INJECT INTO PIPELINE                             │
    │                                                      │
    │  BayesianContext → PipelineContext:                   │
    │  - emotional_state_dist → Stage 4 (emotional)        │
    │  - surprise → Stage 6 (conflict)                     │
    │  - behavioral guidance → Stage 9 (prompt_builder)    │
    │  - event selections → Stage 3 (life_sim)             │
    │     [Doc 15: Pipeline integration]                   │
    └──────────────┬──────────────────────────────────────┘
                   │
                   v
    ┌─────────────────────────────────────────────────────┐
    │  9. EXISTING PIPELINE + CONVERSATION AGENT           │
    │                                                      │
    │  Stages 1-9 run with Bayesian context enrichment     │
    │  Sonnet 4.5 generates response with behavioral       │
    │  guidance from Bayesian state                        │
    └─────────────────────────────────────────────────────┘
```

### 3.2 Decision Matrix: When Does Each Sub-Model Fire?

```
Sub-Model          Fires On             Update Signal              Frequency
─────────────────────────────────────────────────────────────────────────────
Metric posteriors  Every message         Sentiment + engagement     100%
Skip decision      Every message         Thompson Sample            100%
Timing decision    Every non-skip msg    Thompson Sample            ~80%
Event selector     Daily (pg_cron)       Player engagement          ~1/day
Vice discovery     Every message         Keyword detection          100%
Emotional DBN      Every message         All observations           100%
Attachment model   Every 5th message     Behavioral pattern batch   ~20%
Emotional contagion Every message        Sentiment + tone           100%
Surprise check     Every message         KL divergence              100%
Temperature update Every message         Consistency tracking       100%
```

---

## 4. Migration Plan: From Current System to Bayesian

### 4.1 Phased Rollout

The migration happens in four phases, each independently deployable and rollback-safe.

**Phase 1: Metric Posteriors (Week 1-2)**

Replace the flat `Decimal` metric storage with Beta posteriors. The existing `ScoreCalculator` continues to produce deltas, but instead of applying them as:

```python
# Current: deterministic
metrics.trust = clamp(metrics.trust + delta, 0, 100)
```

We apply them as:

```python
# New: Bayesian update
if delta > 0:
    state.trust_alpha += delta / 10.0  # Scale to pseudo-observations
else:
    state.trust_beta += abs(delta) / 10.0
```

The `ScoreCalculator` still runs (for backwards compatibility and boss threshold checks), but the Bayesian state provides a richer, uncertainty-aware version.

**Scope**: New `bayesian_states` table, `BayesianPlayerState` class, metric update logic.
**Risk**: Low (additive, existing scoring unchanged).
**Success criteria**: Beta posterior means track within 5% of deterministic scores.

**Phase 2: Thompson Sampling Decisions (Week 3-4)**

Enable Bayesian skip rate and timing. The existing `SkipDecision` and timing logic become fallbacks behind feature flags.

**Scope**: `BayesianSkipDecision`, `BayesianTimingDecision`, feature flags.
**Risk**: Medium (visible behavior change — skip patterns differ per player).
**Success criteria**: Engagement metrics (response rate, session length) equal or better than control.

**Phase 3: Emotional DBN + Surprise (Week 5-8)**

Deploy the causal graph from Doc 13. The DBN replaces the `StateComputer` for emotional state inference. Bayesian surprise enables conflict triggering.

**Scope**: `EmotionalDBN`, `SurpriseDetector`, conflict trigger integration.
**Risk**: Medium-high (complex model, affects Nikita's personality expression).
**Success criteria**: Player qualitative feedback positive; boss encounters feel organic.

**Phase 4: Full Integration (Week 9-12)**

Enable event generation (Doc 14), vice discovery (Doc 18), emotional contagion (Doc 16), and controlled randomness (Doc 17). The full unified architecture is live.

**Scope**: All remaining sub-models, portal dashboard integration.
**Risk**: Medium (full stack, but each component independently tested in prior phases).
**Success criteria**: 90%+ messages handled by Tier 1 (pure Bayesian), token costs reduced by 85%+.

### 4.2 Parallel Running Strategy

During each phase, the old and new systems run in parallel:

```python
async def process_with_comparison(
    user_id: str,
    message: str,
    session,
) -> dict:
    """Run both old and new systems, compare results, use feature flag for output."""
    settings = get_settings()

    # Always run old system
    old_result = await old_pipeline_process(user_id, message, session)

    # Run new system if enabled (even in shadow mode)
    if settings.bayesian_engine_enabled or settings.bayesian_shadow_mode:
        new_result = await bayesian_engine_process(user_id, message, session)

        # Log comparison for analysis
        await log_comparison(user_id, old_result, new_result)

        # Use new result only if flag is set
        if settings.bayesian_engine_enabled:
            return new_result

    return old_result
```

### 4.3 Rollback Triggers

Automatic rollback if ANY of these conditions are met during A/B testing:

| Metric | Threshold | Action |
|---|---|---|
| Player churn rate | >15% higher than control | Disable Bayesian engine |
| Average session length | >20% shorter than control | Disable Bayesian engine |
| Bayesian escalation rate | >40% (expected: 5-15%) | Increase surprise thresholds |
| p99 latency | >100ms (expected: <50ms) | Simplify DBN or disable |
| Player satisfaction survey | >0.5 points worse (1-5 scale) | Disable and investigate |

---

## 5. Risk Assessment

### 5.1 Technical Risks

**Risk 1: DBN Inference Too Slow**
- Probability: Low (analysis shows <15ms for our model size)
- Impact: Moderate (adds latency to every message)
- Mitigation: Pre-compiled junction tree, caching common state combos, fallback to lookup table

**Risk 2: Beta Posteriors Diverge from Deterministic Scores**
- Probability: Medium (different update dynamics could produce different trajectories)
- Impact: High (boss encounters trigger at wrong times, game balance breaks)
- Mitigation: Run both systems in parallel for 2 weeks, compare. Use deterministic scores for boss thresholds as ground truth.

**Risk 3: Thompson Sampling Produces Erratic Behavior**
- Probability: Low (posterior concentration prevents this after ~10 observations)
- Impact: High (player experiences inconsistent Nikita)
- Mitigation: Hard caps on skip rate, timing bounds, diversity constraints. Behavioral temperature dampens randomness for players who need consistency.

**Risk 4: Cold Start Personality Mismatch**
- Probability: Medium (priors may not match all player expectations)
- Impact: Moderate (first few interactions feel "off")
- Mitigation: Chapter-specific priors encode game design intent. First 10 messages use wider priors (more exploration). Onboarding quiz could accelerate prior setting.

**Risk 5: Engagement Signal Noise**
- Probability: High (heuristic engagement detection will have false positives/negatives)
- Impact: Moderate (posteriors update on noisy signal, slower learning)
- Mitigation: Use partial updates (engagement_strength 0-1 instead of binary), require multiple signals to confirm engagement, periodic LLM validation of engagement detection accuracy.

### 5.2 Product Risks

**Risk 6: Players Dislike Adaptive Behavior**
- Probability: Low (game personalization is generally well-received)
- Impact: High (fundamental design assumption is wrong)
- Mitigation: A/B test with a subset first. Provide player control via portal ("Nikita personality settings").

**Risk 7: Optimization for Engagement Creates Unhealthy Dynamics**
- Probability: Medium (engagement optimization can reinforce addictive patterns)
- Impact: High (ethical/reputational)
- Mitigation: Ethical guardrails in `ViceBoundaryEnforcer` operate independently of Bayesian system. Hard limits on session length, cooling-off periods, and attachment-safety checks from Doc 13.

### 5.3 Operational Risks

**Risk 8: JSONB State Corruption**
- Probability: Low (atomic writes)
- Impact: High (player's learned state lost)
- Mitigation: Schema validation on read/write. Daily backups of bayesian_states. Recovery: reset to chapter defaults.

**Risk 9: Feature Flag Complexity**
- Probability: Medium (many interacting flags)
- Impact: Low (incorrect flag combo → old system fallback)
- Mitigation: Hierarchical flags (`bayesian_engine_enabled` = master switch, sub-flags only checked if master is on).

---

## 6. Fallback Strategies

### 6.1 Per-Component Fallbacks

| Component | Primary (Bayesian) | Fallback (Current) |
|---|---|---|
| Metric updates | Beta posterior update | `ScoreCalculator.apply_multiplier()` |
| Skip decision | Thompson Sampling | `SkipDecision.should_skip()` |
| Timing | Dirichlet TS | Gaussian from `TIMING_RANGES` |
| Emotional state | DBN forward inference | `StateComputer` additive model |
| Vice detection | Dirichlet focus | `ViceAnalyzer` (full LLM scan) |
| Event generation | Bayesian selection + LLM narration | LLM-only `EventGenerator` |
| Conflict trigger | Bayesian surprise | Score threshold only |

### 6.2 Global Fallback

If `bayesian_engine_enabled = False`, the entire Bayesian layer is bypassed. The system reverts to the exact behavior of the current production system. No code changes needed — the Bayesian stage simply doesn't execute.

---

## 7. Cost-Benefit Summary

### 7.1 Token Cost Projection

```
CURRENT SYSTEM (per player per day, assuming 15 messages):

  Scoring LLM calls:      15 x $0.002 = $0.030
  Vice analysis:           15 x $0.001 = $0.015
  Event generation:        1 x $0.002 = $0.002
  Emotional state:         0 (deterministic)
  ─────────────────────────────────────────────
  Total:                   $0.047/player/day

BAYESIAN SYSTEM (per player per day):

  Scoring LLM calls:       1.5 x $0.002 = $0.003  (90% Bayesian, 10% LLM)
  Vice analysis:            0.5 x $0.001 = $0.0005 (Dirichlet handles 97%)
  Event generation:         0.6 x $0.002 = $0.0012 (40% template, 60% LLM)
  Bayesian engine:          $0.000 (pure math)
  Escalation (Tier 2):      1.5 x $0.009 = $0.014  (~10% of messages)
  Escalation (Tier 3):      0.3 x $0.065 = $0.020  (~2% of messages)
  ─────────────────────────────────────────────
  Total:                    $0.039/player/day

  Savings: $0.008/player/day (17%)
```

Wait — this doesn't show the dramatic savings promised. The issue is that the current scoring LLM call is the biggest cost, and it's only partially eliminated because the scoring agent also serves other purposes (generating metric deltas that feed into the game state machine).

**Revised projection with Tier optimization:**

```
OPTIMIZED BAYESIAN SYSTEM:

  Key change: Bayesian metric updates REPLACE the scoring LLM call
  for 90% of messages. The scoring LLM call is only needed when
  Bayesian surprise triggers escalation.

  Scoring LLM calls:        1.5 x $0.002 = $0.003  (vs $0.030)
  Vice analysis:             0.5 x $0.001 = $0.0005 (vs $0.015)
  Event generation:          0.6 x $0.002 = $0.0012 (vs $0.002)
  Bayesian engine:           $0.000
  Escalation (Tier 2):       1.5 x $0.009 = $0.014
  Escalation (Tier 3):       0.3 x $0.065 = $0.020
  ─────────────────────────────────────────────
  Total:                     $0.039/player/day
  Current:                   $0.047/player/day
  Savings:                   $0.008/player/day (17%)

At scale:
  1,000 users:    $8/day    = $240/month saved
  10,000 users:   $80/day   = $2,400/month saved
  100,000 users:  $800/day  = $24,000/month saved
```

**Important nuance**: The savings are modest at low user counts because the Tier 2/3 escalation costs partially offset the Bayesian savings. The real value proposition is NOT just cost savings — it is:

1. **Personalization** (impossible with current system at any cost)
2. **Latency reduction** (Bayesian: <25ms vs LLM: 500-2000ms)
3. **Consistency** (deterministic posteriors vs. stochastic LLM outputs)
4. **Debuggability** (inspect exact posterior state vs opaque LLM reasoning)

### 7.2 Engineering Cost Estimate

```
Phase 1 (Metric posteriors):     2 dev-weeks
Phase 2 (Thompson Sampling):    2 dev-weeks
Phase 3 (Emotional DBN):        3 dev-weeks
Phase 4 (Full integration):     3 dev-weeks
Testing & A/B:                   2 dev-weeks
────────────────────────────────────────────
Total:                           12 dev-weeks (~3 months for 1 dev)
```

### 7.3 Break-Even Analysis

```
Engineering cost: 12 weeks × $X/week (developer cost)
Monthly savings at N users: N × $0.24/month

Break-even equation: 12 * X = N * 0.24 * months_to_break_even

Example: If developer costs $4,000/week:
  Total engineering: $48,000
  At 1,000 users: break-even in 200 months (NOT worth it for cost alone)
  At 10,000 users: break-even in 20 months
  At 100,000 users: break-even in 2 months

Conclusion: Cost savings alone justify the project only at 10K+ users.
The real justification is the personalization and latency improvements
that are IMPOSSIBLE with the current architecture at any scale.
```

---

## 8. Architectural Invariants

These invariants must hold throughout the migration and in the final system:

1. **Bayesian state is always recoverable**: If the JSONB is corrupted, reset to chapter defaults. No player data is permanently lost (worst case: lose learned preferences).

2. **LLM is always available as fallback**: Every Bayesian decision has an LLM fallback. The system never REQUIRES the Bayesian engine — it enhances.

3. **Existing game balance is preserved**: Boss thresholds, chapter progression, and composite scoring use the same formulas. Bayesian metrics provide ADDITIONAL signals, not replacements for game balance.

4. **No new infrastructure**: The Bayesian engine runs on the same Cloud Run instance, stores state in the same Supabase database, and uses the same deployment pipeline.

5. **Latency budget**: The Bayesian engine adds <25ms (p50) to message processing. Any optimization that violates this must be rejected or deferred.

6. **Privacy**: All Bayesian state is per-user and subject to the same RLS policies as existing user data. No cross-user inference or shared models.

7. **Deterministic reproducibility**: Given the same state and message, the Bayesian engine produces the same posterior updates (Thompson Sampling adds randomness, but the posteriors themselves are deterministic).

---

## 9. Open Questions for Expert Evaluation

These questions are deferred to Phase 3 (expert evaluations, docs 20-23):

1. **Game Designer**: Does Thompson Sampling produce good drama curves? Does adaptivity destroy Nikita's authored personality? (Doc 20)

2. **Psychologist**: Is modeling attachment styles as Dirichlet distributions psychologically valid? Are there ethical concerns with adaptive relationship dynamics? (Doc 21)

3. **ML Engineer**: Are the computational claims realistic? What breaks at scale or with adversarial players? Are there simpler alternatives? (Doc 22)

4. **Cost Analyst**: Is the 12-week engineering investment justified? What's the opportunity cost? What user count makes this viable? (Doc 23)

---

## 10. Summary: The Architecture at a Glance

```
                     ┌─────────────────────────────────┐
                     │     BayesianPlayerState          │
                     │  (one JSONB object per player)   │
                     │                                   │
                     │  Metrics: 4 × Beta(α, β)         │
                     │  Skip: Beta(α, β)                 │
                     │  Timing: Dirichlet(5)             │
                     │  Events: 15 × Beta(α, β)          │
                     │  Vice: Dirichlet(8)               │
                     │  Emotional: DBN belief state       │
                     │  Attachment: Dirichlet(4)          │
                     │  Contagion: Categorical(6)         │
                     │  Surprise: float[7]               │
                     │                                   │
                     │  Total: ~1.8 KB per player        │
                     └──────────┬──────────────────────┘
                                │
                  ┌─────────────┼─────────────┐
                  v             v             v
          ┌──────────┐  ┌──────────┐  ┌──────────┐
          │ Tier 1   │  │ Tier 2   │  │ Tier 3   │
          │ Bayesian │  │ DBN +    │  │ LLM      │
          │ Update + │  │ Surprise │  │ (Sonnet/ │
          │ Thompson │  │ Check    │  │  Opus)   │
          │ Sample   │  │          │  │          │
          │          │  │          │  │          │
          │ <1ms     │  │ 5-15ms   │  │ 300ms-3s │
          │ $0       │  │ $0       │  │ $0.009+  │
          │ 85-90%   │  │ 8-12%    │  │ 2-3%     │
          └──────────┘  └──────────┘  └──────────┘
```

This architecture fulfills the original Psyche Agent vision with a critical improvement: **Tier 1 and Tier 2 are live mathematical inference, not stale LLM cache**. The result is a system that is simultaneously more personalized, more responsive, more debuggable, and less expensive than the current approach.

---

**Cross-References:**
- Doc 12: Bayesian Player Model — metric posteriors and player state schema
- Doc 13: Nikita's DBN — causal graph and emotional inference
- Doc 14: Event Generation — Thompson Sampling for events, surprise triggers
- Doc 15: Integration Architecture — module structure, pipeline integration
- Doc 16: Emotional Contagion — bidirectional emotion transfer
- Doc 17: Controlled Randomness — personality-coherent variability
- Doc 18: Vice Discovery — Dirichlet posterior for vice preferences
- Doc 24: Integrated Architecture (Phase 4) — production-ready version with eval feedback
- Doc 25: Implementation Roadmap (Phase 4) — phased rollout plan
- Doc 26: Database Schema (Phase 4) — final DDL and migration

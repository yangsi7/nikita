# 24 — Integrated Bayesian Architecture: Final Design

**Series**: Bayesian Inference for AI Companions — Synthesis
**Date**: 2026-02-16
**Inputs**: Phase 2 ideas (12-19) + Phase 3 evaluations (20-23)
**Status**: FINAL — Incorporates all expert feedback

---

## 1. Design Philosophy

This architecture incorporates four critical feedback themes from Phase 3 evaluation:

1. **Narrative Accountability** (Doc 20): Every player-visible behavioral change must have a perceivable cause. The Bayesian engine is the brain; a narrative layer is the persona.
2. **Construct Honesty** (Doc 21): The system models behavioral engagement patterns, not clinical attachment styles. No clinical-level psychological claims.
3. **Simplicity First** (Doc 22): Bayesian state machine instead of full DBN. Custom NumPy over pgmpy. Start with fixed skip probabilities.
4. **Phased Investment** (Doc 23): Phase 1 delivers standalone value. Each subsequent phase has a decision gate.

---

## 2. System Architecture

### 2.1 High-Level Diagram

```
                    PLAYER MESSAGE
                         │
                         v
    ┌────────────────────────────────────────────┐
    │           BAYESIAN PRE-STAGE               │
    │  (inserted before existing 9-stage pipeline)│
    │                                             │
    │  ┌─────────────┐  ┌──────────────────────┐ │
    │  │ Feature      │  │ State Load           │ │
    │  │ Extractor    │  │ (bayesian_states)    │ │
    │  │ (rules +     │  │ JSONB → Python       │ │
    │  │  opt. Haiku) │  │ ~5ms                 │ │
    │  └──────┬───────┘  └──────────┬───────────┘ │
    │         │                     │              │
    │         v                     v              │
    │  ┌──────────────────────────────────────┐   │
    │  │       POSTERIOR UPDATES               │   │
    │  │                                       │   │
    │  │  Beta metrics ─── <1μs                │   │
    │  │  Dirichlet vices ─ <1μs               │   │
    │  │  Engagement pattern (HMM) ─ <10μs     │   │
    │  └──────────────┬───────────────────────┘   │
    │                 │                            │
    │                 v                            │
    │  ┌──────────────────────────────────────┐   │
    │  │    BAYESIAN STATE MACHINE             │   │
    │  │    (replaces full DBN — Doc 22 rec.)  │   │
    │  │                                       │   │
    │  │    6 emotional states                 │   │
    │  │    Bayesian transition probabilities   │   │
    │  │    ~50μs                               │   │
    │  └──────────────┬───────────────────────┘   │
    │                 │                            │
    │                 v                            │
    │  ┌──────────────────────────────────────┐   │
    │  │     SURPRISE + ESCALATION             │   │
    │  │     KL divergence check               │   │
    │  │     Tier 1/2/3 decision               │   │
    │  │     ~10μs                              │   │
    │  └──────────────┬───────────────────────┘   │
    │                 │                            │
    │                 v                            │
    │  ┌──────────────────────────────────────┐   │
    │  │     NARRATIVE FILTER (Doc 20 rec.)     │   │
    │  │     Ensure behavioral changes have     │   │
    │  │     perceivable causes                 │   │
    │  │     Signal-gradient enforcement         │   │
    │  └──────────────┬───────────────────────┘   │
    │                 │                            │
    │                 v                            │
    │  ┌──────────────────────────────────────┐   │
    │  │     STATE SAVE + CONTEXT BUILD        │   │
    │  │     BayesianContext → pipeline stages   │   │
    │  │     ~5ms (DB write)                    │   │
    │  └──────────────┬───────────────────────┘   │
    │                 │                            │
    └─────────────────┼────────────────────────────┘
                      │
                      v
    ┌────────────────────────────────────────────┐
    │       EXISTING 9-STAGE PIPELINE            │
    │                                             │
    │  Stage 1: Extraction (Haiku)               │
    │  Stage 2: Memory update (Supabase)         │
    │  Stage 3: Life sim (Bayesian event sel.)   │ ← enriched
    │  Stage 4: Emotional (from Bayesian state)  │ ← enriched
    │  Stage 5: Game state (Bayesian scores)     │ ← enriched
    │  Stage 6: Conflict (surprise-based)        │ ← enriched
    │  Stage 7: Touchpoint                       │
    │  Stage 8: Summary                          │
    │  Stage 9: Prompt builder + LLM response    │ ← behavioral guidance
    └────────────────────────────────────────────┘
```

### 2.2 Total Pre-Stage Latency Budget

```
Component                    Target     Worst Case
──────────────────────────────────────────────────
Feature extraction (rules)   1ms        3ms
State load (DB read)         5ms        10ms
Posterior updates             0.01ms     0.1ms
State machine inference      0.05ms     0.5ms
Surprise computation         0.01ms     0.1ms
Narrative filter             0.01ms     0.1ms
State save (DB write)        5ms        10ms
──────────────────────────────────────────────────
TOTAL                        ~11ms      ~24ms
```

---

## 3. Python Module Structure

### 3.1 Package Layout

```
nikita/bayesian/
├── __init__.py              # Public API: BayesianEngine
├── state.py                 # BayesianPlayerState dataclass + serialization
├── engine.py                # BayesianEngine: orchestrator
├── metrics.py               # Beta posterior update logic
├── emotional.py             # Bayesian state machine (6 states)
├── surprise.py              # KL divergence + escalation
├── narrative_filter.py      # Narrative Accountability Rule (Doc 20)
├── safety.py                # Secure Base Constraint + Emotional Safety (Doc 21)
├── features.py              # Observation extraction (rules + optional Haiku)
├── context.py               # BayesianContext → prompt guidance
└── config.py                # Feature flags + hyperparameters
```

**Estimated total**: ~1,200 lines (reduced from Doc 15's 1,990 estimate by replacing full DBN with state machine and deferring Thompson Sampling skip/timing to Phase 2).

### 3.2 Key Classes

```python
# nikita/bayesian/engine.py

from nikita.bayesian.state import BayesianPlayerState
from nikita.bayesian.metrics import MetricUpdater
from nikita.bayesian.emotional import BayesianStateMachine
from nikita.bayesian.surprise import SurpriseDetector
from nikita.bayesian.narrative_filter import NarrativeFilter
from nikita.bayesian.safety import SecureBaseConstraint, EmotionalSafetyGuard
from nikita.bayesian.features import FeatureExtractor
from nikita.bayesian.context import BayesianContext
from nikita.bayesian.config import BayesianConfig


class BayesianEngine:
    """Central coordinator for all Bayesian inference.

    Runs as a pre-stage before the existing 9-stage pipeline.
    Total latency budget: <25ms.
    """

    def __init__(self, config: BayesianConfig):
        self.config = config
        self.feature_extractor = FeatureExtractor()
        self.metric_updater = MetricUpdater()
        self.state_machine = BayesianStateMachine()
        self.surprise_detector = SurpriseDetector(
            tier2_threshold=config.surprise_tier2_threshold,
            tier3_threshold=config.surprise_tier3_threshold,
        )
        self.narrative_filter = NarrativeFilter()
        self.safety = SecureBaseConstraint()
        self.emotional_safety = EmotionalSafetyGuard()

    async def process(
        self,
        user_id: str,
        message: str,
        conversation_history: list[str],
        session,
    ) -> BayesianContext:
        """Full Bayesian pre-stage processing.

        Returns BayesianContext for injection into pipeline stages.
        """
        # 1. Extract features (~1ms)
        features = self.feature_extractor.extract(
            message=message,
            history=conversation_history,
            use_llm=self.config.use_llm_extraction,
        )

        # 2. Load state (~5ms)
        state = await self._load_state(user_id, session)

        # 3. Store pre-update snapshot (for surprise computation)
        pre_update_metrics = state.metric_snapshot()

        # 4. Update posteriors (<1ms)
        self.metric_updater.update(state, features)

        # 5. Emotional state machine (~0.05ms)
        emotional_result = self.state_machine.transition(
            state=state,
            features=features,
        )

        # 6. Surprise + escalation (~0.01ms)
        surprise = self.surprise_detector.compute(
            pre_metrics=pre_update_metrics,
            post_metrics=state.metric_snapshot(),
            direction="negative",  # Doc 20: directional surprise
        )
        escalation_tier = self.surprise_detector.escalation_tier(surprise)

        # 7. Safety checks (Doc 21)
        self.safety.constrain(state, features)
        self.emotional_safety.evaluate(state, features)

        # 8. Narrative filter (Doc 20)
        self.narrative_filter.enforce(
            state=state,
            features=features,
            emotional_result=emotional_result,
        )

        # 9. Save state (~5ms)
        await self._save_state(state, session)

        # 10. Build context for pipeline injection
        return BayesianContext(
            composite_score=state.composite_score_estimate,
            metric_means=state.metric_means,
            metric_uncertainties=state.metric_uncertainties,
            emotional_state=emotional_result.dominant_state,
            emotional_confidence=emotional_result.confidence,
            surprise_level=surprise,
            escalation_tier=escalation_tier,
            behavioral_guidance=emotional_result.to_prompt_guidance(),
            dominant_vice=state.dominant_vice,
            vice_confidence=state.vice_concentration,
        )
```

### 3.3 Bayesian State Machine (Doc 22 Recommendation)

```python
# nikita/bayesian/emotional.py

import numpy as np
from dataclasses import dataclass


@dataclass
class EmotionalTransitionResult:
    """Result of emotional state machine transition."""
    dominant_state: str
    state_probabilities: dict[str, float]
    confidence: float  # How certain we are about the state
    previous_state: str
    transition_cause: str  # Narrative accountability

    def to_prompt_guidance(self) -> str:
        """Convert to natural language for prompt injection."""
        guidance = f"Nikita is currently feeling {self.dominant_state}"
        if self.confidence < 0.5:
            guidance += " (though she's not entirely sure of her own feelings)"
        if self.transition_cause:
            guidance += f" because {self.transition_cause}"
        return guidance


class BayesianStateMachine:
    """Emotional state machine with Bayesian transition probabilities.

    Replaces the full DBN (Doc 13) with a simpler model that captures
    most of the benefit. Per Doc 22's recommendation.

    States: content, playful, anxious, guarded, confrontational, withdrawn
    (Renamed from Doc 21's behavioral response modes)
    """

    STATES = ["content", "playful", "anxious", "guarded", "confrontational", "withdrawn"]

    # Base transition matrix (row = from, col = to)
    # These are modulated by posterior state at runtime
    BASE_TRANSITIONS = np.array([
        #  cont  play  anx   guard conf  with
        [0.50, 0.25, 0.10, 0.10, 0.02, 0.03],  # from content
        [0.30, 0.40, 0.10, 0.10, 0.05, 0.05],  # from playful
        [0.15, 0.05, 0.35, 0.25, 0.10, 0.10],  # from anxious
        [0.10, 0.05, 0.15, 0.40, 0.20, 0.10],  # from guarded
        [0.05, 0.05, 0.15, 0.20, 0.40, 0.15],  # from confrontational
        [0.10, 0.05, 0.20, 0.15, 0.10, 0.40],  # from withdrawn
    ])

    # Situation-triggered modulation (Doc 21 Section 8.2)
    SITUATION_MODS = {
        "positive_message": {"content": 1.5, "playful": 1.3, "anxious": 0.7},
        "negative_message": {"anxious": 1.5, "guarded": 1.3, "content": 0.5},
        "repair_attempt": {"content": 1.8, "anxious": 0.6, "confrontational": 0.4},
        "absence": {"withdrawn": 1.5, "anxious": 1.3, "playful": 0.5},
        "vulnerability": {"content": 1.3, "playful": 0.8, "guarded": 0.6},
        "conflict_trigger": {"confrontational": 1.5, "guarded": 1.3, "content": 0.3},
    }

    def transition(
        self,
        state: "BayesianPlayerState",
        features: dict,
    ) -> EmotionalTransitionResult:
        """Compute next emotional state."""
        current_idx = self.STATES.index(state.emotional_state or "content")

        # Get base transition probabilities
        probs = self.BASE_TRANSITIONS[current_idx].copy()

        # Modulate by detected situation
        situation = features.get("detected_situation", "neutral")
        if situation in self.SITUATION_MODS:
            for state_name, mod in self.SITUATION_MODS[situation].items():
                idx = self.STATES.index(state_name)
                probs[idx] *= mod

        # Modulate by metric posteriors
        trust_mean = state.trust_alpha / (state.trust_alpha + state.trust_beta)
        stress = features.get("stress_level", 0.0)

        # High stress → more negative states
        for neg_state in ["anxious", "guarded", "confrontational", "withdrawn"]:
            probs[self.STATES.index(neg_state)] *= (1 + stress * 0.5)

        # Low trust → more guarded/withdrawn
        if trust_mean < 0.4:
            probs[self.STATES.index("guarded")] *= 1.3
            probs[self.STATES.index("withdrawn")] *= 1.2

        # Normalize
        probs = probs / probs.sum()

        # Minimum 3-message emotional transition (Doc 21 Section 9.3)
        if state.messages_in_current_emotion < 3:
            # Dampen transitions away from current state
            probs[current_idx] = max(probs[current_idx], 0.7)
            probs = probs / probs.sum()

        # Sample next state
        next_idx = np.random.choice(len(self.STATES), p=probs)
        next_state = self.STATES[next_idx]

        # Determine transition cause for narrative accountability
        cause = self._identify_cause(
            current=self.STATES[current_idx],
            next_state=next_state,
            features=features,
        )

        return EmotionalTransitionResult(
            dominant_state=next_state,
            state_probabilities=dict(zip(self.STATES, probs)),
            confidence=float(probs[next_idx]),
            previous_state=self.STATES[current_idx],
            transition_cause=cause,
        )

    def _identify_cause(self, current: str, next_state: str, features: dict) -> str:
        """Identify narrative cause for emotional transition."""
        if current == next_state:
            return ""  # No transition
        situation = features.get("detected_situation", "neutral")
        CAUSE_MAP = {
            "positive_message": "the player said something sweet",
            "negative_message": "the player's message stung",
            "repair_attempt": "the player is trying to make things right",
            "absence": "it's been a while since the player reached out",
            "vulnerability": "the player opened up emotionally",
            "conflict_trigger": "something the player said hit a nerve",
        }
        return CAUSE_MAP.get(situation, "something shifted in how she feels")
```

### 3.4 Safety Module (Doc 21 Recommendations)

```python
# nikita/bayesian/safety.py

import numpy as np


class SecureBaseConstraint:
    """Constrain optimization to promote secure engagement patterns.

    Per Doc 21: Nikita should model a secure attachment figure,
    not mirror the player's insecure patterns.
    """

    def constrain(self, state: "BayesianPlayerState", features: dict):
        """Apply secure base constraints."""
        pattern = self._detect_engagement_pattern(state, features)

        if pattern == "hyperactive":
            # Player showing anxious patterns — increase consistency
            state.behavioral_temperature = min(state.behavioral_temperature, 0.4)
            state.skip_consistency_floor = 0.85

        elif pattern == "withdrawn":
            # Player showing avoidant patterns — maintain warm availability
            state.warmth_floor = 0.6
            state.outreach_pressure = 0.0  # No "why aren't you talking?"

    def _detect_engagement_pattern(self, state, features) -> str:
        """Detect player's engagement pattern from behavioral signals."""
        msgs_per_day = features.get("messages_per_day_avg", 10)
        response_time_var = features.get("response_time_variance", 0.5)

        if msgs_per_day > 25 and response_time_var < 0.3:
            return "hyperactive"
        elif msgs_per_day < 3:
            return "withdrawn"
        return "normal"


class EmotionalSafetyGuard:
    """Prevent optimization from exploiting emotional vulnerability.

    Per Doc 21 Section 5.3-5.4.
    """

    CONSISTENCY_FLOOR = {
        "max_negative_ratio": 0.25,  # Gottman: 1 negative per 4 positive
        "min_transition_messages": 3,  # No back-to-back emotional reversals
        "max_simultaneous_variability": 2,  # Cap how many dims vary at once
    }

    def evaluate(self, state: "BayesianPlayerState", features: dict):
        """Apply emotional safety constraints."""
        # Check negative interaction ratio
        recent = state.recent_interaction_valences[-20:]  # Last 20 messages
        if recent:
            neg_ratio = sum(1 for v in recent if v < 0) / len(recent)
            if neg_ratio > self.CONSISTENCY_FLOOR["max_negative_ratio"]:
                state.force_positive_next = True
```

---

## 4. Configuration & Feature Flags

```python
# nikita/bayesian/config.py

from pydantic import BaseModel


class BayesianConfig(BaseModel):
    """Feature flags and hyperparameters for Bayesian system."""

    # Master switch
    bayesian_engine_enabled: bool = False
    bayesian_shadow_mode: bool = True  # Run both, compare, use old

    # Phase 1: Metric posteriors
    metric_posteriors_enabled: bool = True
    metric_shadow_compare: bool = True  # Log divergence from deterministic

    # Phase 2: Thompson Sampling (deferred)
    thompson_skip_enabled: bool = False
    thompson_timing_enabled: bool = False

    # Phase 3: Emotional state machine
    emotional_state_machine_enabled: bool = False

    # Phase 4: Full integration
    event_selection_enabled: bool = False
    vice_discovery_enabled: bool = False
    emotional_contagion_enabled: bool = False
    controlled_randomness_enabled: bool = False

    # Observation extraction
    use_llm_extraction: bool = False  # Use Haiku for ambiguous signals
    llm_extraction_sample_rate: float = 0.05  # 5% for quality monitoring

    # Hyperparameters
    surprise_tier2_threshold: float = 2.0  # nats
    surprise_tier3_threshold: float = 3.0  # nats
    cold_start_damping_messages: int = 10  # Half-weight for first N
    cold_start_damping_factor: float = 0.5
    decay_grace_hours: dict = {1: 8, 2: 16, 3: 24, 4: 48, 5: 72}
    narrative_filter_enabled: bool = True
    secure_base_enabled: bool = True

    # A/B testing
    ab_test_enabled: bool = False
    ab_test_bayesian_fraction: float = 0.5
```

---

## 5. API Endpoints

```python
# Added to nikita/api/main.py

@app.get("/api/v1/bayesian/state/{user_id}")
async def get_bayesian_state(user_id: str, session=Depends(get_session)):
    """Debug endpoint: view player's Bayesian state."""
    state = await load_bayesian_state(user_id, session)
    return {
        "user_id": user_id,
        "composite_score": state.composite_score_estimate,
        "metrics": state.metric_means,
        "uncertainties": state.metric_uncertainties,
        "emotional_state": state.emotional_state,
        "dominant_vice": state.dominant_vice,
        "tension": state.tension_level,
        "total_messages": state.total_messages,
    }

@app.get("/api/v1/bayesian/surprise-history/{user_id}")
async def get_surprise_history(user_id: str, session=Depends(get_session)):
    """Debug endpoint: view surprise history for conflict analysis."""
    state = await load_bayesian_state(user_id, session)
    return {
        "user_id": user_id,
        "surprise_history": state.surprise_history,
        "current_tension": state.tension_level,
        "last_surprise": state.last_surprise,
    }

@app.post("/api/v1/bayesian/reset/{user_id}")
async def reset_bayesian_state(user_id: str, session=Depends(get_session)):
    """Admin endpoint: reset player to chapter defaults."""
    state = BayesianPlayerState.default_for_chapter(user_id, chapter=1)
    await save_bayesian_state(state, session)
    return {"status": "reset", "user_id": user_id}
```

---

## 6. Deployment Architecture

```
Cloud Run (nikita-api)
├── Container Image
│   ├── Python 3.12 + FastAPI
│   ├── NumPy (for Bayesian inference) — already in dependencies
│   ├── nikita/bayesian/ package (~1,200 lines)
│   └── No pgmpy (Doc 22 rec.: custom NumPy only)
│
├── Environment Variables
│   ├── BAYESIAN_ENGINE_ENABLED=false  (Phase 1: shadow mode)
│   ├── BAYESIAN_SHADOW_MODE=true
│   └── BAYESIAN_LLM_EXTRACTION=false
│
├── Cold Start Impact
│   ├── NumPy: already loaded (no additional cost)
│   ├── Bayesian init: ~10ms (load config, init state machine)
│   └── Total additional cold start: ~10ms (negligible)
│
└── Scaling
    ├── No additional memory: ~1MB for matrices
    ├── No additional CPU: <1ms compute per message
    └── Scale-to-zero: fully compatible (no persistent state in memory)

Supabase
├── bayesian_states table (JSONB, RLS, GIN index)
├── pg_cron: daily event generation trigger (existing)
└── Analytics: aggregate Bayesian state queries
```

---

## 7. Monitoring & Observability

### 7.1 Key Metrics

```python
# Prometheus metrics (added to existing monitoring)

# Latency
bayesian_pipeline_duration_seconds  # Histogram, target p99 < 25ms

# Correctness
bayesian_deterministic_divergence   # Gauge, per metric, target < 5%

# Escalation
bayesian_escalation_total           # Counter, by tier

# Safety
bayesian_safety_interventions_total # Counter, by type (secure_base, emotional_guard)

# State health
bayesian_state_size_bytes           # Histogram, target p99 < 5KB
bayesian_posterior_concentration    # Gauge, per metric (alpha + beta)
```

### 7.2 Alerting Rules

| Metric | Threshold | Action |
|--------|-----------|--------|
| p99 latency > 50ms | Warning | Investigate DBN complexity |
| Deterministic divergence > 10% | Critical | Disable Bayesian scoring |
| Tier 3 escalation > 5% | Warning | Raise surprise thresholds |
| Safety interventions > 20% | Critical | Review safety constraints |
| State size > 10KB | Warning | Audit state schema |

---

## 8. Key Design Decisions (Evaluation-Informed)

| Decision | Phase 2 Proposal | Evaluation Feedback | Final Design |
|----------|-----------------|---------------------|-------------|
| Emotional model | Full DBN (12 vars) | Doc 22: overengineered | Bayesian state machine (6 states) |
| Defense mechanisms | 10 categorical | Doc 21: too granular | 5 behavioral response modes (mapped to states) |
| Skip/timing | Thompson Sampling | Doc 22: defer; Doc 23: Phase 2 | Fixed probabilities (Phase 1), TS (Phase 2) |
| Attachment naming | "attachment_style" | Doc 21: clinical overreach | "engagement_pattern" |
| Surprise direction | Bidirectional | Doc 20: symmetric surprise wrong | Negative directional only for bosses |
| Cold start | Full-weight updates | Doc 20: too volatile | Half-weight for first 10 messages |
| Surprise ratio | 70/20/10 | Doc 20: too aggressive | 85/12/3 |
| Observation model | Rules only | Doc 22: weakest link | Rules + optional Haiku (5% monitoring) |
| Personality traits | Beta distributions | Doc 21: traits should be fixed | Fixed traits, contextual expression |
| Contagion coupling | Fixed 0.3 | Doc 21: should be attachment-dependent | Varies by engagement pattern (0.05-0.45) |
| pgmpy | For prototyping | Doc 22: not for production | Custom NumPy only |
| Repair detection | Not addressed | Doc 20: critical for safety | Added to narrative_filter.py |
| Trauma bonding | Not addressed | Doc 21: ethical requirement | Consistency floor in safety.py |

---

## 9. What This Architecture Does NOT Include

Explicitly deferred or rejected:

1. **Portal Bayesian dashboard** (from Doc 16): Deferred to Phase 4+. The portal shows posterior means as abstract indicators, not raw Bayesian state.
2. **pgmpy dependency** (from Doc 07): Rejected. Custom NumPy is 50-100x faster with no cold start penalty.
3. **Player emotion modeling** (from Doc 16): Deferred. Emotional contagion is Phase 4, the most complex and risky component.
4. **Onboarding archetype quiz** (from Doc 12): Deferred. Let the Bayesian system infer archetypes from behavior rather than self-report.
5. **Population priors** (from Doc 12): Deferred. Requires >1K players. Use narrative priors initially.
6. **Change-point detection** (from Doc 22): Deferred. Use simple discounted posteriors first.

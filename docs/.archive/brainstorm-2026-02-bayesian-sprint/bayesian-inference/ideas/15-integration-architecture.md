# 15 — Integration Architecture: The Bayesian Engine as Tier 1/2 Background Process

**Date**: 2026-02-16
**Type**: Brainstorm / Technical Architecture Proposal
**Phase**: 2 (Ideas)
**Inputs**: Doc 01 (Bayesian Fundamentals), Doc 04 (HMM Emotional States), Doc 06 (Thompson Sampling), Doc 07 (Bayesian Networks), Doc 09 (Beta/Dirichlet Modeling), Doc 14 (Event Generation)
**Outputs**: Feeds into Doc 19 (Unified Architecture), Doc 24 (Integrated Architecture)

---

## 1. The Core Insight: Bayesian IS the Psyche Agent

### 1.1 Revisiting the Psyche Agent Proposal

The previous brainstorm cycle (Doc 15 of the original series) proposed a three-tier Psyche Agent:

```
Tier 1 (Cached):   Read pre-computed psyche state    | 0ms  | $0       | 85-90%
Tier 2 (Sonnet):   Quick emotional analysis           | 300ms| ~$0.009  | 8-12%
Tier 3 (Opus):     Deep psychological analysis         | 3s   | ~$0.065  | 2-3%
```

The Bayesian inference engine IS the mathematical realization of this architecture. It is not an addition to the Psyche Agent — it is its computational backbone:

- **Tier 1** = Read Beta/Dirichlet posteriors from DB, Thompson Sample decisions. Cost: $0, latency: <1ms.
- **Tier 2** = Run DBN forward inference when Bayesian surprise exceeds threshold. Cost: $0, latency: 5-15ms.
- **Tier 3** = Invoke LLM only when genuinely novel situations arise. Cost: ~$0.009-$0.065, latency: 300ms-3s.

The breakthrough: **Tier 1 and Tier 2 are entirely mathematical**. No tokens consumed. No API calls. Just NumPy operations on cached posterior parameters.

### 1.2 Why This Architecture

```
Previous proposal (Psyche Agent):
  Every message → Trigger detector → Choose tier → Execute

  Tier 1: Read cached LLM output (stale up to 24h)
  Tier 2: Real-time Sonnet call (~500 tokens)
  Tier 3: Real-time Opus call (~3000 tokens)

New proposal (Bayesian Engine):
  Every message → Bayesian update → Thompson Sample → Check surprise → Execute

  Tier 1: Pure math posterior update + Thompson Sample (<1ms, $0)
  Tier 2: Pure math DBN forward inference (5-15ms, $0)
  Tier 3: LLM call (only when Bayesian surprise triggers escalation)
```

The difference is fundamental: the Psyche Agent's Tier 1 was a *cached LLM output* — stale, generic, and requiring periodic LLM calls to refresh. The Bayesian Engine's Tier 1 is a *live posterior update* — always fresh, personalized, and computationally free.

---

## 2. Module Architecture

### 2.1 New Package: `nikita/bayesian/`

```
nikita/bayesian/
├── __init__.py           # Package exports
├── state.py              # BayesianPlayerState — unified state object
├── engine.py             # BayesianEngine — main inference coordinator
├── posteriors/
│   ├── __init__.py
│   ├── beta.py           # Beta distribution operations
│   ├── dirichlet.py      # Dirichlet distribution operations
│   └── nig.py            # Normal-Inverse-Gamma operations
├── models/
│   ├── __init__.py
│   ├── skip.py           # BayesianSkipDecision (replaces agents/text/skip.py)
│   ├── timing.py         # BayesianTimingDecision (replaces agents/text/timing.py)
│   ├── events.py         # BayesianEventSelector (wraps life_sim)
│   ├── vice.py           # BayesianViceDiscovery (wraps engine/vice)
│   └── emotional.py      # EmotionalDBN (wraps emotional_state)
├── surprise.py           # BayesianSurprise detection and escalation
├── serialization.py      # JSONB serialization/deserialization
└── pipeline_stage.py     # BayesianStage for the 9-stage pipeline
```

### 2.2 Module Dependency Graph

```
nikita/bayesian/engine.py
  ├── imports state.py (BayesianPlayerState)
  ├── imports posteriors/ (math operations)
  ├── imports models/ (skip, timing, events, vice, emotional)
  ├── imports surprise.py (escalation logic)
  └── imports serialization.py (DB read/write)

nikita/pipeline/stages/bayesian.py
  ├── imports bayesian/engine.py
  └── integrates with existing PipelineContext

nikita/agents/text/agent.py
  └── reads BayesianPlayerState for prompt injection
```

**Key boundary**: The `nikita/bayesian/` package has NO dependency on the LLM. It is pure math (NumPy + SciPy). The LLM dependency stays in the existing modules (`agents/text/`, `engine/scoring/`, `engine/vice/`). The Bayesian engine provides behavioral parameters; the LLM uses those parameters to generate responses.

### 2.3 The BayesianEngine Class

```python
"""nikita/bayesian/engine.py — Main Bayesian inference coordinator."""

import numpy as np
from datetime import datetime, timezone
from uuid import UUID
from typing import Optional

from nikita.bayesian.state import BayesianPlayerState
from nikita.bayesian.models.skip import BayesianSkipDecision
from nikita.bayesian.models.timing import BayesianTimingDecision
from nikita.bayesian.models.events import BayesianEventSelector
from nikita.bayesian.models.vice import BayesianViceDiscovery
from nikita.bayesian.models.emotional import EmotionalDBN
from nikita.bayesian.surprise import SurpriseDetector


class BayesianEngine:
    """Central coordinator for all Bayesian inference operations.

    This is the Tier 1/2 engine that replaces the Psyche Agent's
    cached-state and quick-check tiers. It processes every message
    at near-zero cost and decides whether to escalate to LLM (Tier 3).

    Lifecycle per message:
    1. Load state from DB (one JSONB read)
    2. Extract observations from message
    3. Update posteriors (all sub-models)
    4. Thompson Sample decisions (skip, timing, tone)
    5. Run DBN forward inference (emotional state)
    6. Compute surprise (escalation check)
    7. Save state to DB (one JSONB write)

    Total latency: 1-15ms depending on DBN complexity.
    Total cost: $0 (pure math).
    """

    def __init__(self, state: BayesianPlayerState):
        self.state = state
        self.skip = BayesianSkipDecision(
            chapter=state.chapter,
            alpha=state.skip_alpha,
            beta=state.skip_beta,
        )
        self.timing = BayesianTimingDecision(
            chapter=state.chapter,
            params=state.timing_dirichlet,
        )
        self.events = BayesianEventSelector.from_state(
            state.event_selector_state
        ) if state.event_selector_state else BayesianEventSelector()
        self.vice = BayesianViceDiscovery(
            params=state.vice_dirichlet
        )
        self.emotional = EmotionalDBN(
            belief_state=state.emotional_belief
        )
        self.surprise_detector = SurpriseDetector()

    def process_message(
        self,
        message_features: dict,
        previous_events: Optional[list[dict]] = None,
    ) -> dict:
        """Process a player message through all Bayesian sub-models.

        Args:
            message_features: Extracted features from the player message:
                - sentiment: float (-1 to 1)
                - length: int (character count)
                - is_question: bool
                - topics: list[str]
                - hours_since_last: float
            previous_events: Events from previous day (for engagement update)

        Returns:
            Dict of behavioral parameters for the conversation agent:
            {
                "skip": bool,
                "timing_seconds": float,
                "emotional_state": dict[str, float],
                "behavioral_mode": dict[str, float],
                "vice_focus": list[str],
                "surprise": float,
                "escalate_to_llm": bool,
                "escalation_tier": int (2 or 3),
                "escalation_reason": str | None,
            }
        """
        # 1. Update event posteriors from previous day's engagement
        if previous_events:
            for event in previous_events:
                self.events.update(
                    domain=event["domain"],
                    event_type=event["event_type"],
                    player_engaged=event.get("player_engaged", False),
                    engagement_strength=event.get("engagement_strength", 1.0),
                )

        # 2. Run DBN forward inference
        emotional_result = self.emotional.forward_step(
            observations={
                "sentiment": message_features["sentiment"],
                "investment": min(message_features["length"] / 200.0, 1.0),
                "is_question": message_features["is_question"],
                "hours_gap": message_features["hours_since_last"],
            }
        )

        # 3. Thompson Sample decisions
        should_skip = self.skip.should_skip()
        timing_seconds = self.timing.select_timing()
        vice_focus = self.vice.get_top_vices(n=3)

        # 4. Compute surprise
        surprise = self.surprise_detector.compute_message_surprise(
            state=self.state,
            message_features=message_features,
        )

        # 5. Escalation decision
        escalation = self._decide_escalation(
            surprise=surprise,
            emotional_entropy=emotional_result["entropy"],
            messages_since_llm=self.state.messages_since_last_llm,
        )

        # 6. Update state
        self.state.last_updated = datetime.now(timezone.utc).isoformat()
        self.state.total_messages += 1
        self.state.last_surprise = surprise
        self.state.emotional_belief = emotional_result["belief_state"]
        if not escalation["escalate"]:
            self.state.messages_since_last_llm += 1
        else:
            self.state.messages_since_last_llm = 0

        return {
            "skip": should_skip,
            "timing_seconds": timing_seconds,
            "emotional_state": emotional_result["emotional_dist"],
            "behavioral_mode": emotional_result["behavioral_dist"],
            "vice_focus": vice_focus,
            "surprise": surprise,
            "escalate_to_llm": escalation["escalate"],
            "escalation_tier": escalation["tier"],
            "escalation_reason": escalation.get("reason"),
        }

    def _decide_escalation(
        self,
        surprise: float,
        emotional_entropy: float,
        messages_since_llm: int,
    ) -> dict:
        """Decide whether to escalate from Bayesian to LLM processing.

        Escalation criteria (any one triggers):
        1. Very high surprise (> 3.0): Tier 3 (deep analysis)
        2. High surprise (> 2.0): Tier 2 (quick check)
        3. High emotional entropy (> 0.9): Tier 2
        4. Periodic check (every 10 messages): Tier 2
        5. Chapter transition: Tier 3
        """
        if surprise > 3.0:
            return {
                "escalate": True,
                "tier": 3,
                "reason": f"Very high surprise ({surprise:.2f}): "
                          "player behavior significantly deviates from model",
            }
        if surprise > 2.0:
            return {
                "escalate": True,
                "tier": 2,
                "reason": f"High surprise ({surprise:.2f}): "
                          "checking if model needs recalibration",
            }
        if emotional_entropy > 0.9:
            return {
                "escalate": True,
                "tier": 2,
                "reason": f"High emotional uncertainty (entropy={emotional_entropy:.2f}): "
                          "need LLM to disambiguate emotional state",
            }
        if messages_since_llm >= 10:
            return {
                "escalate": True,
                "tier": 2,
                "reason": "Periodic validation check (10 messages since last LLM)",
            }

        return {"escalate": False, "tier": 1}

    def get_serializable_state(self) -> dict:
        """Return the complete Bayesian state for DB persistence."""
        return {
            "skip": {"alpha": self.skip.alpha, "beta": self.skip.beta},
            "timing": {"dirichlet": self.timing.params.tolist()},
            "events": self.events.get_state(),
            "vice": {"dirichlet": self.vice.dirichlet_params.tolist()},
            "emotional": self.emotional.get_belief_state(),
            "meta": {
                "chapter": self.state.chapter,
                "total_messages": self.state.total_messages,
                "last_surprise": self.state.last_surprise,
                "messages_since_llm": self.state.messages_since_last_llm,
                "last_updated": self.state.last_updated,
            },
        }
```

---

## 3. How It Fits the 9-Stage Pipeline

### 3.1 Current Pipeline Stages

```
Stage 1: extraction        (CRITICAL) — LLM fact extraction
Stage 2: memory_update     (CRITICAL) — pgVector writes
Stage 3: life_sim          — simulated Nikita life events
Stage 4: emotional         — relationship dynamics
Stage 5: game_state        — chapter/boss progression
Stage 6: conflict          — argument/tension handling
Stage 7: touchpoint        — proactive message scheduling
Stage 8: summary           — daily conversation summaries
Stage 9: prompt_builder    — rebuild cached system prompt
```

### 3.2 Proposed Modification

The Bayesian engine runs as a **pre-stage** (Stage 0) before the existing pipeline, or as a modification to the message handling path before the pipeline is invoked. It does NOT replace any existing stage — it augments them.

```
NEW FLOW:

  Player message arrives
       │
       v
  ┌─────────────────────────────────────────┐
  │  BAYESIAN ENGINE (Stage 0)              │
  │  - Load state from bayesian_states      │  <1ms
  │  - Extract message features             │  <1ms
  │  - Update posteriors                    │  <1ms
  │  - Thompson Sample decisions            │  <1ms
  │  - DBN forward inference                │  5-15ms
  │  - Compute surprise                     │  <1ms
  │  - Save state to bayesian_states        │  <5ms
  │                                          │
  │  Output: {skip, timing, emotional_state, │
  │           behavioral_mode, surprise,      │
  │           escalate_to_llm}               │
  └──────────────┬──────────────────────────┘
                 │
                 v
  ┌─ skip=True? ─┐
  │ YES: Schedule │  Don't respond now. Set pg_cron timer
  │ delayed reply │  for timing_seconds from now.
  └───────────────┘
  │ NO: Continue
  v
  ┌─ escalate_to_llm? ─┐
  │ YES (Tier 2): Quick │  Sonnet analyzes message + Bayesian
  │ LLM emotional check │  state. May override Bayesian decisions.
  │                      │
  │ YES (Tier 3): Deep  │  Opus full analysis. Resets priors
  │ LLM analysis        │  if model is fundamentally wrong.
  └──────────────────────┘
  │ NO: Pure Bayesian path
  v
  ┌─────────────────────────────────────────┐
  │  EXISTING 9-STAGE PIPELINE              │
  │  (runs with Bayesian parameters injected │
  │   into PipelineContext)                   │
  │                                          │
  │  Stage 4 (emotional): Uses Bayesian      │
  │    emotional_state instead of hardcoded   │
  │                                          │
  │  Stage 6 (conflict): Uses Bayesian       │
  │    surprise as additional trigger         │
  │                                          │
  │  Stage 9 (prompt_builder): Injects       │
  │    behavioral_mode into system prompt     │
  └──────────────────────────────────────────┘
       │
       v
  ┌─────────────────────────────────────────┐
  │  CONVERSATION AGENT (Sonnet 4.5)        │
  │  System prompt now includes:             │
  │  - emotional_state distribution          │
  │  - behavioral_mode guidance              │
  │  - vice_focus areas                      │
  │  - skip/timing decisions already made    │
  └─────────────────────────────────────────┘
```

### 3.3 PipelineContext Modifications

```python
"""Additions to nikita/pipeline/models.py"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BayesianContext:
    """Bayesian engine output injected into PipelineContext.

    All fields are computed by the BayesianEngine before the
    pipeline starts. Pipeline stages can read (but not write)
    these values.
    """
    # Decision outputs
    skip_decision: bool = False
    timing_seconds: float = 0.0

    # State distributions
    emotional_state_dist: dict[str, float] = field(default_factory=dict)
    behavioral_mode_dist: dict[str, float] = field(default_factory=dict)

    # Surprise and escalation
    surprise_value: float = 0.0
    escalate_to_llm: bool = False
    escalation_tier: int = 1
    escalation_reason: Optional[str] = None

    # Vice focus (top 3 categories to probe)
    vice_focus: list[str] = field(default_factory=list)

    # Narrative state
    tension_level: float = 0.0
    pacing_recommendation: str = "neutral"

    # For prompt injection
    def to_prompt_guidance(self) -> str:
        """Generate behavioral guidance for the system prompt.

        ~100-150 tokens, injected into the conversation agent's
        system prompt to guide Nikita's personality expression.
        """
        dominant_emotion = max(
            self.emotional_state_dist,
            key=self.emotional_state_dist.get,
        ) if self.emotional_state_dist else "neutral"

        dominant_behavior = max(
            self.behavioral_mode_dist,
            key=self.behavioral_mode_dist.get,
        ) if self.behavioral_mode_dist else "balanced"

        tension_label = (
            "high tension" if self.tension_level > 0.6
            else "moderate tension" if self.tension_level > 0.3
            else "low tension"
        )

        return (
            f"[Nikita's current inner state: {dominant_emotion}. "
            f"Behavioral tendency: {dominant_behavior}. "
            f"Relationship tension: {tension_label}. "
            f"Areas of interest to the player: {', '.join(self.vice_focus[:2]) if self.vice_focus else 'general'}.]"
        )
```

### 3.4 Modified Stage Interactions

**Stage 3 (life_sim)**: Uses `BayesianEventSelector` from the Bayesian context instead of the current LLM-only `EventGenerator`. Falls back to LLM generation if the Bayesian event selector doesn't have enough history.

**Stage 4 (emotional)**: Currently uses `StateComputer` with hardcoded deltas. With the Bayesian engine, it reads `emotional_state_dist` from `BayesianContext` as the primary emotional state, using the existing `StateComputer` only as a fallback or validation.

**Stage 6 (conflict)**: Currently triggers conflicts based on score thresholds and keyword detection. The Bayesian engine adds `surprise_value` as an additional trigger pathway (see Doc 14, Section 3).

**Stage 9 (prompt_builder)**: Injects `BayesianContext.to_prompt_guidance()` into the system prompt, providing the conversation agent with Bayesian-derived behavioral direction.

---

## 4. Data Flow: End-to-End Message Processing

### 4.1 Complete Data Flow Diagram

```
PLAYER MESSAGE: "Hey, how was your day?"
       │
       ├──── Feature extraction (rule-based, <1ms)
       │     sentiment: 0.3 (mildly positive)
       │     length: 26 chars
       │     is_question: True
       │     topics: ["daily_check_in"]
       │     hours_since_last: 4.5
       │
       v
  BAYESIAN ENGINE
       │
       ├──── Load state: bayesian_states WHERE user_id = ? (<5ms)
       │     {skip_alpha: 4.2, skip_beta: 11.8, timing_dirichlet: [...], ...}
       │
       ├──── Update posteriors (<1ms total):
       │     - Skip: observe engagement (player messaged → response to previous skip)
       │     - Timing: player responded in 4.5h → update timing preference
       │     - Events: check engagement with yesterday's events
       │     - Vice: update from topic detection
       │
       ├──── DBN forward inference (5-15ms):
       │     Input: {sentiment: 0.3, investment: 0.13, question: True, gap: 4.5h}
       │     Previous state: {emotional: "guarded", behavioral: "aloof"}
       │     Output: {emotional: {warm: 0.35, guarded: 0.30, defensive: 0.20, ...},
       │              behavioral: {engaging: 0.40, aloof: 0.25, challenging: 0.20, ...}}
       │
       ├──── Thompson Sample decisions (<1ms):
       │     skip: False (sampled 0.12 from Beta(4.2, 11.8), below threshold)
       │     timing: 1200 seconds (~20 min, bucket 2 from Dirichlet)
       │     vice_focus: ["emotional_intensity", "intellectual_dominance", "dark_humor"]
       │
       ├──── Surprise computation (<1ms):
       │     surprise: 0.8 (low — question about day is expected)
       │     escalate: False (surprise < 2.0, entropy < 0.9)
       │
       ├──── Save state: UPDATE bayesian_states SET state_json = ? (<5ms)
       │
       └──── Output: BayesianContext {
                 skip: False,
                 timing_seconds: 1200,
                 emotional_state_dist: {warm: 0.35, guarded: 0.30, ...},
                 behavioral_mode_dist: {engaging: 0.40, aloof: 0.25, ...},
                 surprise: 0.8,
                 escalate: False,
                 vice_focus: ["emotional_intensity", ...],
                 tension_level: 0.25,
             }
       │
       v
  9-STAGE PIPELINE (enriched with BayesianContext)
       │
       ├──── Stage 1 (extraction): Extract facts as usual
       ├──── Stage 2 (memory): Write to pgVector as usual
       ├──── Stage 3 (life_sim): Use BayesianEventSelector for today's events
       ├──── Stage 4 (emotional): Use BayesianContext.emotional_state_dist
       ├──── Stage 5 (game_state): Chapter/boss as usual
       ├──── Stage 6 (conflict): Check Bayesian surprise + existing triggers
       ├──── Stage 7 (touchpoint): Schedule follow-up in 1200 seconds
       ├──── Stage 8 (summary): Summarize as usual
       └──── Stage 9 (prompt_builder): Inject behavioral guidance
       │
       v
  CONVERSATION AGENT (Sonnet 4.5)
       │
       ├──── System prompt includes:
       │     "[Nikita's current inner state: warm. Behavioral tendency:
       │      engaging. Relationship tension: low tension. Areas of
       │      interest: emotional_intensity, intellectual_dominance.]"
       │
       └──── Generates response with Bayesian-informed personality
```

### 4.2 Timing Budget

```
Total time budget for Bayesian Engine: <25ms target

Breakdown:
  DB read (bayesian_states):           5ms (p50), 15ms (p99)
  Feature extraction:                  <1ms
  Posterior updates (all sub-models):  <1ms
  DBN forward inference:               5-15ms
  Thompson Sampling:                   <1ms
  Surprise computation:                <1ms
  DB write (bayesian_states):          5ms (p50), 15ms (p99)

Total (p50): ~17ms
Total (p99): ~33ms

Compare with LLM latency: 500-2000ms
Bayesian Engine adds <2% overhead to the message processing path.
```

---

## 5. API Changes

### 5.1 New Endpoints for Bayesian State Inspection

```python
"""New endpoints in nikita/api/routes/ for Bayesian state debugging."""

from fastapi import APIRouter, Depends
from uuid import UUID

router = APIRouter(prefix="/bayesian", tags=["bayesian"])


@router.get("/state/{user_id}")
async def get_bayesian_state(
    user_id: UUID,
    session=Depends(get_session),
) -> dict:
    """Inspect a user's complete Bayesian state.

    Returns all posterior parameters, emotional distributions,
    and behavioral modes. Useful for debugging and the portal dashboard.
    """
    state = await load_bayesian_state(user_id, session)
    if not state:
        return {"status": "no_state", "user_id": str(user_id)}

    return {
        "user_id": str(user_id),
        "state": {
            "skip": {
                "alpha": state.skip_alpha,
                "beta": state.skip_beta,
                "mean": state.skip_alpha / (state.skip_alpha + state.skip_beta),
            },
            "timing": {
                "dirichlet_params": state.timing_dirichlet.tolist(),
                "expected_probs": (
                    state.timing_dirichlet / state.timing_dirichlet.sum()
                ).tolist(),
            },
            "emotional": state.emotional_belief,
            "vice_profile": state.vice_profile,
            "event_preferences": state.event_selector_state,
        },
        "meta": {
            "total_messages": state.total_messages,
            "last_surprise": state.last_surprise,
            "messages_since_llm": state.messages_since_last_llm,
            "last_updated": state.last_updated,
        },
    }


@router.get("/surprise-history/{user_id}")
async def get_surprise_history(
    user_id: UUID,
    days: int = 7,
    session=Depends(get_session),
) -> dict:
    """Get surprise value history for a user.

    Useful for understanding when and why conflicts were triggered.
    """
    history = await load_surprise_history(user_id, days, session)
    return {
        "user_id": str(user_id),
        "surprise_history": history,
        "current_tension": compute_tension_from_history(history),
    }


@router.post("/reset/{user_id}")
async def reset_bayesian_state(
    user_id: UUID,
    chapter: int,
    session=Depends(get_session),
) -> dict:
    """Reset a user's Bayesian state to chapter defaults.

    Admin-only endpoint for debugging. Resets all posteriors
    to their chapter-specific priors.
    """
    new_state = BayesianPlayerState.default_for_chapter(chapter)
    await save_bayesian_state(user_id, new_state, session)
    return {"status": "reset", "user_id": str(user_id), "chapter": chapter}
```

### 5.2 Portal Dashboard Integration

The portal (Next.js) can display Bayesian state to give players insight into how Nikita perceives them:

```
Portal Dashboard — "How Nikita Sees You"

  Emotional Connection:
    [████████░░] 78% warm  (Nikita feels comfortable with you)

  Behavioral Pattern:
    Most common: Engaging (40%)
    Sometimes: Aloof (25%), Challenging (20%)

  What Nikita Notices:
    ★ You love hearing about workplace drama
    ★ You always ask about her friends
    ★ You tend to ignore her personal reflections

  Relationship Tension: Low (0.25)
    ████░░░░░░ — Things are stable
```

This is generated from the Bayesian state without any LLM calls.

---

## 6. Module Boundaries: What's New, What's Modified

### 6.1 New Modules

| Module | Purpose | Lines (est.) |
|---|---|---|
| `nikita/bayesian/__init__.py` | Package exports | ~20 |
| `nikita/bayesian/state.py` | BayesianPlayerState dataclass | ~150 |
| `nikita/bayesian/engine.py` | BayesianEngine coordinator | ~300 |
| `nikita/bayesian/posteriors/beta.py` | Beta distribution ops | ~80 |
| `nikita/bayesian/posteriors/dirichlet.py` | Dirichlet ops | ~80 |
| `nikita/bayesian/posteriors/nig.py` | Normal-Inverse-Gamma ops | ~100 |
| `nikita/bayesian/models/skip.py` | BayesianSkipDecision | ~120 |
| `nikita/bayesian/models/timing.py` | BayesianTimingDecision | ~120 |
| `nikita/bayesian/models/events.py` | BayesianEventSelector | ~250 |
| `nikita/bayesian/models/vice.py` | BayesianViceDiscovery | ~120 |
| `nikita/bayesian/models/emotional.py` | EmotionalDBN | ~300 |
| `nikita/bayesian/surprise.py` | Surprise detection + escalation | ~150 |
| `nikita/bayesian/serialization.py` | JSONB serialization | ~100 |
| `nikita/bayesian/pipeline_stage.py` | Pipeline integration | ~100 |
| **Total new code** | | **~1,990 lines** |

### 6.2 Modified Modules

| Module | Change | Risk |
|---|---|---|
| `nikita/pipeline/models.py` | Add BayesianContext field | Low (additive) |
| `nikita/pipeline/orchestrator.py` | Add optional Stage 0 (Bayesian) | Low (backwards compatible) |
| `nikita/pipeline/stages/emotional.py` | Read from BayesianContext if available | Low (fallback to existing) |
| `nikita/pipeline/stages/conflict.py` | Add surprise trigger pathway | Low (additive trigger) |
| `nikita/pipeline/stages/prompt_builder.py` | Inject behavioral guidance | Low (additional prompt section) |
| `nikita/agents/text/skip.py` | Delegate to BayesianSkipDecision | Medium (behavior change) |
| `nikita/agents/text/timing.py` | Delegate to BayesianTimingDecision | Medium (behavior change) |
| `nikita/api/main.py` | Register /bayesian routes | Low (new routes only) |

### 6.3 Untouched Modules

These modules continue to work exactly as before:

- `nikita/engine/scoring/` — Score calculation is unchanged. The Bayesian engine provides ADDITIONAL signals but does not replace the scoring flow.
- `nikita/engine/chapters/` — Chapter progression based on composite score is unchanged.
- `nikita/engine/decay/` — Decay calculations are unchanged.
- `nikita/memory/` — pgVector memory is unchanged.
- `nikita/agents/text/agent.py` — The conversation agent is unchanged; it just receives richer context.
- `nikita/platforms/telegram/` — Platform layer is unchanged.

---

## 7. Database Changes

### 7.1 New Table: `bayesian_states`

```sql
CREATE TABLE bayesian_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) UNIQUE,
    state_json JSONB NOT NULL DEFAULT '{}',
    chapter INT NOT NULL DEFAULT 1,
    total_messages INT NOT NULL DEFAULT 0,
    last_surprise FLOAT NOT NULL DEFAULT 0.0,
    messages_since_llm INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_bayesian_states_user ON bayesian_states(user_id);

-- GIN index for JSONB queries (useful for analytics)
CREATE INDEX idx_bayesian_states_json ON bayesian_states
    USING GIN (state_json jsonb_path_ops);

-- Index for finding users that need periodic LLM checks
CREATE INDEX idx_bayesian_states_llm_check ON bayesian_states(messages_since_llm)
    WHERE messages_since_llm >= 10;
```

### 7.2 JSONB State Structure

```json
{
  "skip": {
    "alpha": 4.2,
    "beta": 11.8
  },
  "timing": {
    "dirichlet": [1.5, 3.0, 2.5, 1.0, 0.5]
  },
  "events": {
    "category_priors": {
      "work": {
        "career_milestone": {"alpha": 5.2, "beta": 3.1},
        "workplace_conflict": {"alpha": 8.1, "beta": 2.3},
        "new_project": {"alpha": 3.0, "beta": 4.2}
      },
      "social": {},
      "personal": {}
    },
    "domain_params": [4.5, 3.2, 2.8],
    "surprise_history": [1.2, 0.8, 2.1]
  },
  "vice": {
    "dirichlet": [3.2, 2.1, 1.5, 4.8, 6.1, 1.2, 3.5, 5.0]
  },
  "emotional": {
    "intimacy": [0.05, 0.15, 0.40, 0.30, 0.10],
    "passion": [0.10, 0.25, 0.35, 0.20, 0.10],
    "trust": [0.05, 0.20, 0.45, 0.20, 0.10],
    "secureness": [0.10, 0.30, 0.35, 0.20, 0.05],
    "emotional_state": [0.30, 0.15, 0.10, 0.25, 0.10, 0.05, 0.05],
    "behavioral_mode": [0.35, 0.20, 0.15, 0.15, 0.05, 0.10]
  }
}
```

**Size estimate**: ~1-2 KB per user. At 10,000 users: 10-20 MB total. Trivial for Supabase.

### 7.3 Migration Strategy

The `bayesian_states` table is additive — it does not modify any existing table. The migration is a simple CREATE TABLE, with RLS policies matching the existing `users` table pattern.

```sql
-- Row Level Security (matching existing patterns)
ALTER TABLE bayesian_states ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own bayesian state"
    ON bayesian_states FOR SELECT
    USING (auth.uid() = user_id);

-- Service role can do everything (for backend operations)
CREATE POLICY "Service role full access"
    ON bayesian_states FOR ALL
    USING (auth.role() = 'service_role');
```

---

## 8. Deployment on Cloud Run

### 8.1 Cold Start Considerations

Cloud Run scales to zero, so cold starts matter. The Bayesian engine's impact:

```
Current cold start: ~2-3 seconds (FastAPI + Pydantic AI + dependencies)

Additional for Bayesian engine:
  NumPy import: already imported (used by other modules)
  SciPy import: ~200ms (new dependency, needed for beta/dirichlet sampling)
  pgmpy import: ~500ms (if using pgmpy for DBN)
  Custom NumPy DBN: ~0ms (no additional import)

Recommendation: Use custom NumPy implementation for DBN inference
(not pgmpy) in production to avoid the 500ms cold start penalty.
pgmpy is valuable for prototyping but adds unnecessary import weight.
```

### 8.2 Memory Footprint

```
Per-request memory for Bayesian Engine:
  BayesianPlayerState: ~5 KB (all posteriors for one user)
  DBN inference workspace: ~10 KB (temporary arrays)
  Total: ~15 KB per request

Cloud Run instance memory: 256 MB (current setting)
Concurrent requests: up to ~10,000 users without memory pressure
No changes needed to Cloud Run configuration.
```

### 8.3 Stateless Architecture

The Bayesian engine is fully stateless per request:

1. Load state from Supabase (JSONB read)
2. Compute (pure functions on the loaded state)
3. Save state to Supabase (JSONB write)

This is perfectly compatible with Cloud Run's serverless model. No in-memory state survives between requests. The `bayesian_states` table IS the persistent state.

---

## 9. Monitoring and Observability

### 9.1 Key Metrics to Track

```python
# Prometheus/Cloud Monitoring metrics for the Bayesian engine

BAYESIAN_METRICS = {
    # Latency
    "bayesian_inference_duration_ms": Histogram(
        "Duration of Bayesian Engine per message",
        buckets=[1, 5, 10, 25, 50, 100],
    ),

    # Escalation rates
    "bayesian_escalation_rate": Counter(
        "How often Bayesian → LLM escalation occurs",
        labels=["tier", "reason"],
    ),

    # Surprise distribution
    "bayesian_surprise_value": Histogram(
        "Distribution of surprise values",
        buckets=[0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0],
    ),

    # Skip rate
    "bayesian_skip_rate": Counter(
        "Skip decisions made by Bayesian engine",
        labels=["chapter", "decision"],
    ),

    # LLM savings
    "bayesian_llm_calls_saved": Counter(
        "LLM calls avoided by Bayesian inference",
    ),
}
```

### 9.2 Alerting

```yaml
# Alert if escalation rate is too high (model may be broken)
- alert: BayesianEscalationRateHigh
  expr: rate(bayesian_escalation_rate[5m]) > 0.3
  for: 15m
  annotations:
    summary: >
      Bayesian engine escalating to LLM on >30% of messages.
      The model may be miscalibrated or player behavior has shifted
      significantly. Check surprise values and posterior parameters.

# Alert if Bayesian engine latency spikes
- alert: BayesianLatencyHigh
  expr: histogram_quantile(0.99, bayesian_inference_duration_ms) > 50
  for: 5m
  annotations:
    summary: >
      Bayesian engine p99 latency >50ms. DBN inference may be
      too complex. Consider reducing model size or caching.
```

---

## 10. Rollback Strategy

### 10.1 Feature Flag

```python
# In nikita/config/settings.py
class Settings(BaseSettings):
    # Bayesian engine feature flags
    bayesian_engine_enabled: bool = False
    bayesian_skip_enabled: bool = False
    bayesian_timing_enabled: bool = False
    bayesian_events_enabled: bool = False
    bayesian_emotional_enabled: bool = False

    # Escalation thresholds (tunable)
    bayesian_surprise_tier2: float = 2.0
    bayesian_surprise_tier3: float = 3.0
    bayesian_periodic_check: int = 10
```

### 10.2 Graceful Degradation

If `bayesian_engine_enabled = False`, all existing modules work exactly as before. The Bayesian engine is entirely additive — disabling it reverts to the current behavior with zero code changes.

If individual sub-models are disabled (e.g., `bayesian_skip_enabled = False`), the system falls back to the existing `SkipDecision` class from `agents/text/skip.py`.

```python
def get_skip_decision(chapter: int, user_id: str, session) -> bool:
    """Get skip decision with Bayesian fallback.

    If Bayesian engine is enabled, use Thompson Sampling.
    Otherwise, fall back to the existing SkipDecision class.
    """
    settings = get_settings()

    if settings.bayesian_skip_enabled:
        state = await load_bayesian_state(user_id, session)
        if state:
            skip = BayesianSkipDecision(chapter, state.skip_alpha, state.skip_beta)
            return skip.should_skip()

    # Fallback to existing system
    from nikita.agents.text.skip import SkipDecision
    return SkipDecision().should_skip(chapter)
```

---

## 11. Summary

### 11.1 Architecture Decisions

| Decision | Choice | Rationale |
|---|---|---|
| DBN library | Custom NumPy (not pgmpy) | Avoid 500ms cold start on Cloud Run |
| State storage | JSONB in Supabase | Consistent with existing patterns |
| Pipeline integration | Pre-stage (Stage 0) | Non-breaking, backwards compatible |
| Escalation trigger | Bayesian surprise | Principled, quantitative, tunable |
| Rollback | Per-feature flags | Gradual rollout, easy rollback |
| Deployment | Same Cloud Run instance | No new infrastructure |

### 11.2 What the Architecture Achieves

1. **Zero-token Tier 1/2**: 85-95% of messages processed without any LLM call for behavioral decisions
2. **Per-player personalization**: Each player gets unique skip rates, timing, event preferences, vice profiles
3. **Principled escalation**: LLM is called only when the Bayesian model detects genuine novelty or uncertainty
4. **Cost reduction**: Estimated 90%+ reduction in behavioral-decision LLM tokens
5. **Latency reduction**: Bayesian decisions in <25ms vs. 500-2000ms for LLM
6. **Debuggability**: Every posterior parameter is inspectable, plottable, explainable
7. **Backwards compatibility**: Feature flags allow per-component enable/disable with zero code changes

---

**Cross-References:**
- Doc 06: Thompson Sampling (the decision-making algorithm within Tier 1)
- Doc 07: Bayesian Networks (the DBN that powers Tier 2 emotional inference)
- Doc 09: Beta/Dirichlet Modeling (the posterior math)
- Doc 14: Event Generation (Phase A: Bayesian selection, Phase B: LLM narration)
- Doc 19: Unified Architecture (synthesis of all integration decisions)
- Doc 24: Integrated Architecture (final production-ready architecture with eval feedback)

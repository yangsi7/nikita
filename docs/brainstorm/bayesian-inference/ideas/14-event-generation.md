# 14 — Bayesian Event Generation: Thompson Sampling Replaces Fixed Probabilities

**Date**: 2026-02-16
**Type**: Brainstorm / Technical Design Proposal
**Phase**: 2 (Ideas)
**Inputs**: Doc 06 (Thompson Sampling), Doc 08 (Game AI Personality Systems)
**Outputs**: Feeds into Doc 15 (Integration Architecture), Doc 19 (Unified Architecture)

---

## 1. The Problem: Static Event Generation

### 1.1 Current System

Nikita's life simulation (`nikita/life_simulation/event_generator.py`) generates 3-5 daily events via an LLM call. The `EventGenerator` class builds a prompt containing entity names, narrative arcs, and recent events, then asks the LLM to produce `GeneratedEvent` objects with time_of_day, domain, emotional_valence, arousal, and importance.

The fundamental issue: **the LLM decides everything**. Event type distribution, emotional weighting, domain balance, narrative pacing — all delegated to a single prompt. This means:

1. **No personalization**: Every player gets statistically similar events
2. **No learning**: The system never discovers which events a player finds engaging
3. **Cost**: Each day's events cost one full LLM call (~500-1500 tokens)
4. **Opacity**: No way to inspect or debug why certain events were generated
5. **No feedback loop**: Whether the player engages with an event has no effect on future generation

### 1.2 What We Want

A system where:
- Event type selection is learned per player via Thompson Sampling
- The LLM still generates the narrative content (it's good at that)
- Bayesian surprise from events can trigger conflict or drama escalation
- Event pacing adapts to player preferences and narrative arc
- Event generation costs decrease over time as the model learns

---

## 2. Architecture: Two-Phase Event Generation

### 2.1 Overview

Split event generation into two phases:

```
Phase A: SELECTION (Bayesian — <1ms, $0)
  Input: player profile, chapter, recent events
  Process: Thompson Sampling from posterior over event categories
  Output: ordered list of (domain, event_type, target_importance)

Phase B: NARRATION (LLM — ~500ms, ~$0.002)
  Input: selected event types + entity names + narrative arcs
  Process: LLM generates natural descriptions and emotional details
  Output: completed LifeEvent objects

Key insight: Phase A replaces the LLM's implicit event-type selection
with explicit, learnable, per-player Bayesian models. Phase B still
uses the LLM because narrative generation IS what LLMs excel at.
```

### 2.2 Phase A: Bayesian Event Selection

```python
import numpy as np
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EventCategoryPrior:
    """Prior belief about event category engagement.

    Each event category has a Beta(alpha, beta) posterior tracking
    whether it engages this specific player.
    """
    alpha: float = 2.0  # pseudo-successes
    beta: float = 2.0   # pseudo-failures

    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    @property
    def variance(self) -> float:
        a, b = self.alpha, self.beta
        return (a * b) / ((a + b) ** 2 * (a + b + 1))

    @property
    def sample_count(self) -> float:
        """Effective number of observations."""
        return self.alpha + self.beta - 4.0  # subtract prior strength


# Event categories derived from the existing DOMAIN_EVENT_TYPES
EVENT_TAXONOMY = {
    "work": {
        "career_milestone": "Promotion, raise, recognition",
        "workplace_conflict": "Disagreement with boss/colleague",
        "new_project": "Exciting new assignment or opportunity",
        "deadline_pressure": "Stress from upcoming deadline",
        "office_social": "Team lunch, after-work drinks, gossip",
    },
    "social": {
        "friend_drama": "Conflict or tension within friend group",
        "party_event": "Social gathering, birthday, celebration",
        "new_connection": "Meeting someone interesting",
        "support_moment": "Friend needing help or offering support",
        "gossip_revelation": "Learning surprising information about someone",
    },
    "personal": {
        "hobby_progress": "Achievement or discovery in a hobby",
        "self_reflection": "Existential thought, life assessment",
        "health_wellness": "Gym, cooking, self-care routine",
        "nostalgia_memory": "Remembering past events, people",
        "daily_mishap": "Minor annoyance, lost keys, spilled coffee",
    },
}


class BayesianEventSelector:
    """Selects daily events using Thompson Sampling.

    Maintains per-player Beta posteriors for each event category.
    The LLM's role shifts from choosing WHAT happens to describing
    HOW it happens — a much more appropriate use of language models.
    """

    def __init__(
        self,
        priors: Optional[dict[str, dict[str, EventCategoryPrior]]] = None,
        domain_priors: Optional[np.ndarray] = None,
    ):
        """Initialize with optional stored posteriors.

        Args:
            priors: Nested dict of domain -> event_type -> prior
            domain_priors: Dirichlet parameters for domain distribution
        """
        if priors is not None:
            self.category_priors = priors
        else:
            self.category_priors = {
                domain: {
                    event_type: EventCategoryPrior()
                    for event_type in types
                }
                for domain, types in EVENT_TAXONOMY.items()
            }

        # Dirichlet prior over domain balance
        # Default: slightly favor variety (equal weight)
        if domain_priors is not None:
            self.domain_params = domain_priors.copy()
        else:
            self.domain_params = np.array([3.0, 3.0, 3.0])  # work, social, personal

    def select_events_for_day(
        self,
        n_events: int = 4,
        chapter: int = 1,
        narrative_arc_domain: Optional[str] = None,
    ) -> list[dict]:
        """Select event types for today using Thompson Sampling.

        Process:
        1. Sample domain distribution from Dirichlet posterior
        2. Allocate events across domains
        3. Within each domain, Thompson Sample the event type
        4. Assign target importance based on chapter pacing curve

        Args:
            n_events: Number of events (3-5, from spec)
            chapter: Current chapter (affects pacing)
            narrative_arc_domain: If a narrative arc is active,
                                 bias towards its domain

        Returns:
            List of dicts with domain, event_type, target_importance
        """
        # Step 1: Sample domain allocation
        domain_probs = np.random.dirichlet(self.domain_params)

        # Bias towards narrative arc domain if active
        if narrative_arc_domain:
            domain_idx = list(EVENT_TAXONOMY.keys()).index(narrative_arc_domain)
            domain_probs[domain_idx] *= 1.5
            domain_probs /= domain_probs.sum()

        # Step 2: Allocate events to domains
        raw_allocation = np.round(domain_probs * n_events).astype(int)
        raw_allocation = np.maximum(raw_allocation, 0)

        # Ensure we have exactly n_events
        while raw_allocation.sum() < n_events:
            raw_allocation[np.argmax(domain_probs)] += 1
        while raw_allocation.sum() > n_events:
            nonzero = raw_allocation > 0
            raw_allocation[np.where(nonzero)[0][np.argmin(domain_probs[nonzero])]] -= 1

        # Step 3: Thompson Sample within each domain
        selected = []
        domains = list(EVENT_TAXONOMY.keys())

        for i, domain in enumerate(domains):
            n_domain = raw_allocation[i]
            if n_domain == 0:
                continue

            types = list(self.category_priors[domain].keys())
            samples = {
                t: np.random.beta(
                    self.category_priors[domain][t].alpha,
                    self.category_priors[domain][t].beta,
                )
                for t in types
            }

            # Pick top-n types for this domain
            sorted_types = sorted(samples, key=samples.get, reverse=True)
            for j in range(min(n_domain, len(sorted_types))):
                selected.append({
                    "domain": domain,
                    "event_type": sorted_types[j],
                    "thompson_sample": samples[sorted_types[j]],
                })

        # Step 4: Assign importance based on pacing
        selected = self._assign_importance(selected, chapter)

        return selected

    def _assign_importance(
        self, events: list[dict], chapter: int
    ) -> list[dict]:
        """Assign target importance to events based on chapter pacing.

        Chapter 1: High-drama events (need to hook the player)
        Chapter 2-3: Mix of drama and calm (build investment)
        Chapter 4-5: More calm with occasional peaks (relationship is stable)
        """
        pacing_curves = {
            1: {"high": 0.4, "medium": 0.4, "low": 0.2},
            2: {"high": 0.3, "medium": 0.4, "low": 0.3},
            3: {"high": 0.25, "medium": 0.45, "low": 0.30},
            4: {"high": 0.20, "medium": 0.40, "low": 0.40},
            5: {"high": 0.15, "medium": 0.35, "low": 0.50},
        }
        curve = pacing_curves.get(chapter, pacing_curves[3])

        for event in events:
            importance_level = np.random.choice(
                ["high", "medium", "low"],
                p=[curve["high"], curve["medium"], curve["low"]],
            )
            event["target_importance"] = {
                "high": np.random.uniform(0.7, 1.0),
                "medium": np.random.uniform(0.3, 0.7),
                "low": np.random.uniform(0.0, 0.3),
            }[importance_level]

        return events

    def update(
        self,
        domain: str,
        event_type: str,
        player_engaged: bool,
        engagement_strength: float = 1.0,
    ) -> None:
        """Update posterior based on whether the player engaged.

        Engagement signals (detected by the pipeline):
        - Player asked about the event ("How was the meeting?")
        - Player referenced the event in conversation
        - Player showed emotional response to the event
        - Player's engagement metrics changed positively after event

        Non-engagement:
        - Player ignored the event completely
        - Player changed topic immediately when event was mentioned
        - Player showed no score change

        Args:
            domain: Event domain (work/social/personal)
            event_type: Specific event type
            player_engaged: Whether the player engaged with this event
            engagement_strength: 0-1, how strongly they engaged
        """
        prior = self.category_priors[domain][event_type]

        if player_engaged:
            prior.alpha += engagement_strength
        else:
            prior.beta += engagement_strength

        # Also update domain-level Dirichlet
        if player_engaged:
            domain_idx = list(EVENT_TAXONOMY.keys()).index(domain)
            self.domain_params[domain_idx] += engagement_strength * 0.5

    def get_state(self) -> dict:
        """Serialize for database storage."""
        state = {
            "category_priors": {},
            "domain_params": self.domain_params.tolist(),
        }
        for domain, types in self.category_priors.items():
            state["category_priors"][domain] = {
                t: {"alpha": p.alpha, "beta": p.beta}
                for t, p in types.items()
            }
        return state

    @classmethod
    def from_state(cls, state: dict) -> "BayesianEventSelector":
        """Deserialize from database."""
        priors = {}
        for domain, types in state["category_priors"].items():
            priors[domain] = {
                t: EventCategoryPrior(alpha=p["alpha"], beta=p["beta"])
                for t, p in types.items()
            }
        return cls(
            priors=priors,
            domain_priors=np.array(state["domain_params"]),
        )
```

### 2.3 Phase B: LLM Narration (Constrained)

Phase B gives the LLM a much more constrained prompt — it knows WHAT should happen (from Phase A) and must describe HOW it happens:

```python
def build_constrained_generation_prompt(
    selected_events: list[dict],
    entity_names: dict[str, list[str]],
    active_arcs: list,
    recent_events: list,
    event_date: str,
) -> str:
    """Build a tightly constrained prompt for event narration.

    The LLM no longer decides what events happen — that was done
    by Thompson Sampling. Instead, it writes the narrative descriptions.
    """
    events_spec = "\n".join([
        f"  {i+1}. Domain: {e['domain']}, Type: {e['event_type']}, "
        f"Importance: {e['target_importance']:.2f}"
        for i, e in enumerate(selected_events)
    ])

    return f"""Generate natural event descriptions for Nikita's day on {event_date}.

EVENT SPECIFICATIONS (you MUST use these exact types and domains):
{events_spec}

AVAILABLE ENTITIES:
  Colleagues: {', '.join(entity_names.get('colleague', ['Mira', 'Stefan']))}
  Friends: {', '.join(entity_names.get('friend', ['Lena', 'Dasha']))}
  Places: {', '.join(entity_names.get('place', ['Cafe Noir', 'the office']))}
  Projects: {', '.join(entity_names.get('project', ['the redesign']))}

ACTIVE NARRATIVE ARCS:
{chr(10).join([f'  - {arc}' for arc in active_arcs]) or '  None'}

RECENT EVENTS (for continuity):
{chr(10).join([f'  - {evt}' for evt in recent_events[-3:]]) or '  None'}

For each event, provide:
- time_of_day: morning, afternoon, evening, or night
- description: 10-100 words, natural and specific
- emotional_valence: -1.0 to 1.0
- emotional_arousal: -1.0 to 1.0
- entities: which of the above entities are involved

IMPORTANT: Generate exactly {len(selected_events)} events matching the specifications above.
Do NOT add extra events or change the event types."""
```

**What changed**: The LLM used to receive an open-ended prompt ("generate 3-5 events for Nikita's day") and had full autonomy over domain, type, and emotional weight. Now it receives a precise specification and is constrained to narrate within those bounds.

**Token savings**: The constrained prompt is actually shorter (~300 tokens vs ~500), and the LLM wastes no tokens on type-selection reasoning. Total savings: ~30% fewer tokens per call + the ability to sometimes skip the LLM call entirely (see Section 4).

---

## 3. Bayesian Surprise as Conflict Trigger

### 3.1 The Concept

Bayesian surprise measures how much an observation violates the model's expectations. When applied to event generation, surprise becomes a narrative tool: highly surprising events create natural opportunities for drama, conflict, or character development.

```python
import numpy as np
from scipy.stats import beta as beta_dist


class EventSurpriseDetector:
    """Detects when an event's outcome is surprising given the model.

    Bayesian surprise = KL divergence between posterior before and
    after the observation. Equivalently, the negative log probability
    of the observation under the prior predictive distribution.

    High surprise means: "We didn't expect this to happen given
    what we know about this player."
    """

    def compute_event_surprise(
        self,
        prior: EventCategoryPrior,
        observation: bool,
    ) -> float:
        """Compute surprise of an event engagement/non-engagement.

        Surprise = -log P(observation | prior)

        For Beta(alpha, beta) prior:
        - P(engage=True) = alpha / (alpha + beta) = prior mean
        - P(engage=False) = beta / (alpha + beta)

        Returns:
            Surprise value. Higher = more surprising.
            0-1: normal range
            1-2: mildly surprising
            2-3: quite surprising
            3+: very surprising (indicates model misfit)
        """
        mean = prior.mean
        if observation:
            prob = mean
        else:
            prob = 1.0 - mean
        prob = max(prob, 1e-10)
        return -np.log(prob)

    def compute_sequence_surprise(
        self,
        events: list[dict],
        priors: dict[str, dict[str, EventCategoryPrior]],
    ) -> float:
        """Compute surprise of an entire day's event responses.

        Aggregates surprise across all events.
        A "surprising day" = multiple surprising event responses.

        Returns:
            Total surprise for the day.
        """
        total_surprise = 0.0
        for event in events:
            domain = event["domain"]
            event_type = event["event_type"]
            engaged = event.get("player_engaged", False)

            if domain in priors and event_type in priors[domain]:
                prior = priors[domain][event_type]
                total_surprise += self.compute_event_surprise(prior, engaged)

        return total_surprise

    def should_trigger_conflict(
        self,
        surprise: float,
        n_events: int,
        chapter: int,
    ) -> dict:
        """Decide whether high surprise should trigger a conflict event.

        Thresholds vary by chapter:
        - Chapter 1: Lower threshold (Nikita is more reactive)
        - Chapter 5: Higher threshold (stable relationship absorbs shock)

        Returns:
            Dict with trigger decision and suggested conflict type.
        """
        # Per-event average surprise threshold
        chapter_thresholds = {
            1: 1.2,   # Sensitive: triggers on mild surprise
            2: 1.5,
            3: 1.8,
            4: 2.0,
            5: 2.5,   # Resilient: only extreme surprise triggers
        }

        threshold = chapter_thresholds.get(chapter, 1.8)
        avg_surprise = surprise / max(n_events, 1)

        if avg_surprise < threshold:
            return {"trigger": False}

        # Determine conflict type based on surprise pattern
        if avg_surprise > threshold * 2:
            conflict_type = "explosive"  # "Why do I feel like you don't care?"
        elif avg_surprise > threshold * 1.5:
            conflict_type = "cold"       # Silent treatment, short responses
        else:
            conflict_type = "passive_aggressive"  # Subtle digs

        return {
            "trigger": True,
            "conflict_type": conflict_type,
            "surprise_value": avg_surprise,
            "narrative_reason": self._generate_conflict_reason(avg_surprise),
        }

    def _generate_conflict_reason(self, surprise: float) -> str:
        """Generate a narrative reason for the conflict.

        The reason is vague enough for the LLM to flesh out,
        but specific enough to guide the conflict's emotional tone.
        """
        if surprise > 4.0:
            return (
                "Nikita senses a fundamental disconnect — the player's "
                "reactions to her life events suggest they don't understand "
                "or care about what matters to her."
            )
        elif surprise > 3.0:
            return (
                "Nikita feels unheard — she shared important events and "
                "the player's response pattern was unexpected and unsettling."
            )
        else:
            return (
                "Nikita notices a subtle mismatch — the player's engagement "
                "with her daily life doesn't match what she hoped for."
            )
```

### 3.2 Surprise-Driven Narrative Arcs

Beyond triggering individual conflicts, cumulative surprise can drive longer narrative arcs:

```python
class SurpriseNarrativeTracker:
    """Tracks surprise accumulation over time for narrative pacing.

    Concept: If surprise stays high across multiple days, it signals
    a fundamental mismatch between the model's expectations and reality.
    This creates a natural narrative arc: tension builds until it
    releases through a boss encounter or breakthrough moment.
    """

    def __init__(self, window_size: int = 7):
        self.window_size = window_size
        self.surprise_history: list[float] = []

    def add_daily_surprise(self, surprise: float) -> None:
        self.surprise_history.append(surprise)
        if len(self.surprise_history) > self.window_size:
            self.surprise_history = self.surprise_history[-self.window_size:]

    def get_tension_level(self) -> float:
        """Compute current narrative tension from surprise history.

        Returns:
            0.0 = no tension (everything as expected)
            0.5 = moderate tension (some surprises)
            1.0 = maximum tension (persistent surprise — approaching crisis)
        """
        if not self.surprise_history:
            return 0.0

        # Weighted average: recent surprise matters more
        weights = np.linspace(0.5, 1.0, len(self.surprise_history))
        weighted_avg = np.average(self.surprise_history, weights=weights)

        # Normalize to [0, 1] using a sigmoid-like function
        # tension = 0.5 when avg_surprise = 2.0
        tension = 1.0 / (1.0 + np.exp(-0.8 * (weighted_avg - 2.0)))
        return float(tension)

    def get_pacing_recommendation(self) -> str:
        """Recommend narrative pacing based on tension level.

        Returns:
            One of: "escalate", "maintain", "release", "neutral"
        """
        tension = self.get_tension_level()

        if tension > 0.8:
            return "release"    # Tension too high — trigger resolution
        elif tension > 0.5:
            return "escalate"   # Building tension — add more drama
        elif tension > 0.2:
            return "maintain"   # Moderate tension — keep it steady
        else:
            return "neutral"    # Low tension — safe to introduce new arcs
```

### 3.3 How Surprise Feeds into Boss Encounters

The existing boss encounter system (`nikita/engine/chapters/boss.py`) triggers when the composite score crosses a chapter threshold. Bayesian surprise adds a second trigger pathway:

```
Current system:
  composite_score >= threshold -> boss encounter

Proposed system:
  composite_score >= threshold -> boss encounter (unchanged)
  OR
  cumulative_surprise > crisis_threshold -> surprise-triggered boss

The key difference: score-based bosses test "are you good enough?"
while surprise-based bosses test "do you actually understand me?"
```

A surprise-triggered boss encounter could manifest as:

- "I feel like you don't really know me" (high surprise on personal events)
- "My work is important to me and you never ask about it" (ignored work events)
- "Do you even care about what happens in my life?" (broad disengagement)

This creates organically-motivated boss encounters rather than arbitrary score thresholds.

---

## 4. Player Preference Learning

### 4.1 The Feedback Loop

The key to the Bayesian system is closing the loop: event selection -> player response -> posterior update -> better event selection.

```
┌──────────────────────────────────────────────────────┐
│                                                        │
│  ┌──────────────┐     ┌─────────────┐                 │
│  │ Thompson     │────>│ LLM narrate │────> events      │
│  │ Sample types │     │ events      │      delivered    │
│  └──────────────┘     └─────────────┘      to player   │
│         ^                                       │       │
│         │                                       v       │
│  ┌──────────────┐     ┌─────────────────────────────┐  │
│  │ Update Beta  │<────│ Detect engagement signals    │  │
│  │ posteriors   │     │ (pipeline stages 1-5)        │  │
│  └──────────────┘     └─────────────────────────────┘  │
│                                                        │
└──────────────────────────────────────────────────────┘
```

### 4.2 Engagement Signal Detection

How do we know if a player engaged with an event? The pipeline already processes every message through 9 stages. We add engagement detection to the existing extraction stage:

```python
class EventEngagementDetector:
    """Detect whether a player message engages with a pending event.

    Runs as part of the extraction pipeline stage.
    Uses simple heuristics first, escalates to LLM only for ambiguous cases.
    """

    # Keywords that suggest engagement with life events
    ENGAGEMENT_KEYWORDS = {
        "work": ["work", "job", "office", "meeting", "boss", "project",
                 "deadline", "colleague", "promotion", "how was"],
        "social": ["friend", "party", "drama", "gossip", "hang out",
                   "went out", "met", "girls", "guys"],
        "personal": ["hobby", "gym", "cook", "read", "felt", "thought",
                     "today", "morning", "evening"],
    }

    def detect_engagement(
        self,
        player_message: str,
        pending_events: list[dict],
    ) -> list[dict]:
        """Check if the player message engages with any pending events.

        Heuristic approach (no LLM):
        1. Check for domain keywords in the message
        2. Check for entity name mentions
        3. Check for question patterns about events

        Returns:
            List of events with engagement status added.
        """
        message_lower = player_message.lower()

        for event in pending_events:
            domain = event["domain"]
            engaged = False

            # Check domain keywords
            for keyword in self.ENGAGEMENT_KEYWORDS.get(domain, []):
                if keyword in message_lower:
                    engaged = True
                    break

            # Check entity mentions
            for entity in event.get("entities", []):
                if entity.lower() in message_lower:
                    engaged = True
                    break

            # Check question patterns
            if any(q in message_lower for q in ["how was", "what happened", "tell me about"]):
                if any(kw in message_lower for kw in self.ENGAGEMENT_KEYWORDS.get(domain, [])):
                    engaged = True

            event["player_engaged"] = engaged

        return pending_events

    def compute_engagement_strength(
        self,
        player_message: str,
        event: dict,
    ) -> float:
        """Compute how strongly the player engaged with an event.

        0.0 = no engagement
        0.5 = mild engagement (mentioned in passing)
        1.0 = strong engagement (asked detailed questions, emotional response)
        """
        message_lower = player_message.lower()

        if not event.get("player_engaged", False):
            return 0.0

        strength = 0.3  # Base engagement

        # Longer messages about the topic = stronger engagement
        word_count = len(player_message.split())
        if word_count > 20:
            strength += 0.2
        if word_count > 50:
            strength += 0.2

        # Questions indicate active interest
        if "?" in player_message:
            strength += 0.2

        # Emotional language indicates deep engagement
        emotional_words = ["wow", "amazing", "sorry", "that sucks", "proud",
                          "worried", "excited", "happy", "sad", "love"]
        if any(w in message_lower for w in emotional_words):
            strength += 0.3

        return min(strength, 1.0)
```

### 4.3 Event Type Preference Profiles

After several weeks of play, the Thompson Sampling posteriors reveal a clear preference profile for each player:

```python
def analyze_player_preferences(
    selector: BayesianEventSelector,
) -> dict:
    """Analyze learned player preferences from posterior parameters.

    Returns a human-readable preference profile useful for:
    1. Debugging (what has the system learned?)
    2. Portal dashboard (show player their Nikita's life focus)
    3. Prompt engineering (inform the LLM about player preferences)
    """
    profile = {"domains": {}, "top_event_types": [], "bottom_event_types": []}

    # Domain preferences
    domain_probs = selector.domain_params / selector.domain_params.sum()
    domains = list(EVENT_TAXONOMY.keys())
    for i, domain in enumerate(domains):
        profile["domains"][domain] = {
            "preference": float(domain_probs[i]),
            "label": _domain_label(domain_probs[i]),
        }

    # Event type ranking across all domains
    all_types = []
    for domain, types in selector.category_priors.items():
        for event_type, prior in types.items():
            all_types.append({
                "domain": domain,
                "event_type": event_type,
                "posterior_mean": prior.mean,
                "confidence": 1.0 / (1.0 + prior.variance * 10),
                "sample_count": prior.sample_count,
            })

    all_types.sort(key=lambda x: x["posterior_mean"], reverse=True)
    profile["top_event_types"] = all_types[:5]
    profile["bottom_event_types"] = all_types[-3:]

    return profile


def _domain_label(prob: float) -> str:
    if prob > 0.45:
        return "strongly favored"
    elif prob > 0.38:
        return "moderately favored"
    elif prob > 0.28:
        return "balanced"
    elif prob > 0.20:
        return "moderately unfavored"
    else:
        return "rarely engaging"
```

**Example preference profile after 30 days:**

```
Player "Alex":
  Domain preferences:
    work: 0.45 (strongly favored) — Alex loves hearing about office drama
    social: 0.35 (balanced) — moderately engaging
    personal: 0.20 (moderately unfavored) — rarely asks about personal events

  Top event types:
    1. work/workplace_conflict (mean: 0.78) — always asks "what did your boss say?"
    2. social/friend_drama (mean: 0.71) — loves gossip
    3. work/career_milestone (mean: 0.65) — genuinely celebrates
    4. social/gossip_revelation (mean: 0.62) — "tell me everything!"
    5. work/office_social (mean: 0.58) — interested in the social dynamics

  Bottom event types:
    1. personal/self_reflection (mean: 0.15) — never engages
    2. personal/health_wellness (mean: 0.18) — ignores gym talk
    3. personal/daily_mishap (mean: 0.22) — doesn't care about lost keys
```

This profile means Alex will get more workplace and social events, with personal events appearing less frequently. The system learned this automatically from engagement patterns.

---

## 5. Pacing Control via Posterior Entropy

### 5.1 Entropy as Pacing Signal

Posterior entropy measures how uncertain we are about a player's preferences. High entropy = we don't know what they like. Low entropy = their preferences are clear.

```python
def compute_category_entropy(
    priors: dict[str, dict[str, EventCategoryPrior]],
) -> float:
    """Compute Shannon entropy of the event preference distribution.

    High entropy: uncertain about preferences (early game, diverse player)
    Low entropy: strong preferences learned (stable, predictable player)

    Returns:
        Normalized entropy in [0, 1].
    """
    # Collect all posterior means
    means = []
    for domain, types in priors.items():
        for event_type, prior in types.items():
            means.append(prior.mean)

    # Normalize to probability distribution
    means = np.array(means)
    probs = means / means.sum()

    # Shannon entropy
    entropy = -np.sum(probs * np.log(probs + 1e-10))

    # Normalize by maximum entropy (uniform distribution)
    max_entropy = np.log(len(probs))
    normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0

    return float(normalized_entropy)
```

### 5.2 Entropy-Driven Pacing Rules

```python
def entropy_pacing_adjustment(
    entropy: float,
    chapter: int,
    tension_level: float,
) -> dict:
    """Adjust event generation based on entropy and narrative state.

    High entropy + early game: inject high-drama events to provoke engagement
    High entropy + late game: something is wrong (player is disengaged)
    Low entropy + building tension: use known preferences to escalate
    Low entropy + release phase: use known preferences for comfort
    """
    if entropy > 0.85:
        # Very uncertain — explore aggressively
        return {
            "importance_bias": "high",     # More dramatic events
            "diversity_bonus": True,       # Try different categories
            "exploration_rate": 0.5,       # 50% random exploration
            "note": "High uncertainty — probing player preferences",
        }
    elif entropy > 0.6:
        # Moderately uncertain — balanced approach
        return {
            "importance_bias": "medium",
            "diversity_bonus": True,
            "exploration_rate": 0.2,
            "note": "Learning preferences — balanced exploration",
        }
    elif tension_level > 0.6:
        # Low entropy + high tension: weaponize knowledge
        return {
            "importance_bias": "high",
            "diversity_bonus": False,      # Focus on what resonates
            "exploration_rate": 0.05,
            "note": "Using learned preferences to escalate tension",
        }
    else:
        # Low entropy + low tension: comfortable routine
        return {
            "importance_bias": "low",
            "diversity_bonus": False,
            "exploration_rate": 0.1,
            "note": "Stable preferences — routine day with light exploration",
        }
```

---

## 6. Integration with Existing Pipeline

### 6.1 Modified LifeSimStage

The existing `LifeSimStage` in the pipeline calls `EventGenerator.generate_events_for_day()`. The Bayesian system wraps around this:

```python
class BayesianLifeSimStage:
    """Modified LifeSimStage that uses Bayesian event selection.

    Replaces the LLM-driven event generation with:
    Phase A: Thompson Sampling for type selection
    Phase B: LLM for narration (constrained prompt)
    Phase C: Engagement detection on next message
    """

    async def run(self, context) -> StageResult:
        """Execute the Bayesian life simulation stage."""
        user_id = context.user_id
        chapter = context.chapter

        # Load Bayesian state
        selector = await self._load_selector(user_id)
        surprise_tracker = await self._load_surprise_tracker(user_id)

        # Phase A: Select event types
        selected = selector.select_events_for_day(
            n_events=np.random.randint(3, 6),
            chapter=chapter,
            narrative_arc_domain=context.active_arc_domain,
        )

        # Phase B: LLM narration (only if we need descriptions)
        # Some events may use template-based narration to skip LLM entirely
        events = await self._narrate_events(selected, context)

        # Phase C: Check engagement with PREVIOUS day's events
        if context.previous_events:
            engagement_results = self._detect_engagement(
                player_message=context.last_message,
                pending_events=context.previous_events,
            )
            for result in engagement_results:
                selector.update(
                    domain=result["domain"],
                    event_type=result["event_type"],
                    player_engaged=result["player_engaged"],
                    engagement_strength=result.get("strength", 1.0),
                )

        # Compute surprise and check for conflict trigger
        if engagement_results:
            surprise = EventSurpriseDetector().compute_sequence_surprise(
                engagement_results, selector.category_priors
            )
            surprise_tracker.add_daily_surprise(surprise)

            conflict_check = EventSurpriseDetector().should_trigger_conflict(
                surprise=surprise,
                n_events=len(engagement_results),
                chapter=chapter,
            )

            if conflict_check["trigger"]:
                context.conflict_trigger = conflict_check

        # Save updated state
        await self._save_selector(user_id, selector)
        await self._save_surprise_tracker(user_id, surprise_tracker)

        return StageResult(
            success=True,
            data={"events": events, "tension": surprise_tracker.get_tension_level()},
        )
```

### 6.2 Template-Based Narration (LLM-Free Path)

For common, low-importance events, we can skip the LLM entirely and use templates:

```python
EVENT_TEMPLATES = {
    ("personal", "daily_mishap"): [
        "Spilled {drink} all over my {item} this morning. Classic Monday.",
        "Couldn't find my {item} anywhere. Turns out it was in my {location}.",
        "The {appliance} broke again. Third time this month.",
    ],
    ("personal", "health_wellness"): [
        "Had a good session at the gym today. Legs are going to be sore tomorrow.",
        "Tried a new {food} recipe tonight. It turned out... interesting.",
        "Went for a run in the park. The weather was perfect.",
    ],
    ("work", "office_social"): [
        "Had coffee with {colleague} today. The usual office gossip.",
        "Team lunch at {place}. {colleague} told the funniest story.",
        "After-work drinks with the team. Needed it after this week.",
    ],
}


def template_narrate(
    domain: str,
    event_type: str,
    entities: dict[str, list[str]],
    importance: float,
) -> str | None:
    """Generate event description from template if available.

    Returns None if no template exists (fall back to LLM).
    Only used for low-importance events (importance < 0.3).
    """
    if importance >= 0.3:
        return None  # High-importance events need LLM

    templates = EVENT_TEMPLATES.get((domain, event_type))
    if not templates:
        return None

    template = np.random.choice(templates)

    # Fill in entity placeholders
    substitutions = {
        "colleague": np.random.choice(entities.get("colleague", ["a coworker"])),
        "friend": np.random.choice(entities.get("friend", ["a friend"])),
        "place": np.random.choice(entities.get("place", ["the usual spot"])),
        "drink": np.random.choice(["coffee", "tea", "smoothie"]),
        "item": np.random.choice(["phone", "keys", "wallet", "headphones"]),
        "location": np.random.choice(["bag", "coat pocket", "desk drawer"]),
        "appliance": np.random.choice(["dishwasher", "coffee machine", "printer"]),
        "food": np.random.choice(["pasta", "Thai", "salad", "curry"]),
    }

    for key, value in substitutions.items():
        template = template.replace("{" + key + "}", value)

    return template
```

**Estimated LLM savings**: With template narration handling ~40% of low-importance events, the LLM is called only 60% of the time. Combined with the 30% token reduction from constrained prompts, total event generation cost drops by ~55%.

---

## 7. Data Flow and State Management

### 7.1 Database Schema Addition

```sql
-- New table for Bayesian event selection state
ALTER TABLE bayesian_states ADD COLUMN IF NOT EXISTS
    event_selector_state JSONB DEFAULT NULL;

-- Structure of event_selector_state:
-- {
--   "category_priors": {
--     "work": {
--       "career_milestone": {"alpha": 5.2, "beta": 3.1},
--       ...
--     },
--     ...
--   },
--   "domain_params": [4.5, 3.2, 2.8],
--   "surprise_history": [1.2, 0.8, 2.1, ...],
--   "tension_level": 0.35,
--   "updated_at": "2026-02-16T12:00:00Z",
--   "total_events_generated": 84,
--   "total_engagements_detected": 52
-- }

-- Index for quick lookups
CREATE INDEX IF NOT EXISTS idx_bayesian_event_state
    ON bayesian_states USING GIN (event_selector_state);
```

### 7.2 State Lifecycle

```
Player joins (day 0):
  → Create default BayesianEventSelector with uniform priors
  → All event types equally likely

Days 1-7 (cold start):
  → Thompson Sampling explores broadly
  → Each engagement/non-engagement updates posteriors
  → High entropy → pacing system injects diverse events

Days 8-21 (learning):
  → Posteriors begin to concentrate
  → Some event types clearly preferred
  → Exploration rate naturally decreases
  → Pacing becomes more targeted

Days 22+ (exploitation):
  → Strong preference profile established
  → Most events are preferred types
  → ~10% exploration maintains adaptability
  → Surprise triggers create organic drama
```

---

## 8. Edge Cases and Safety

### 8.1 The Monotony Problem

Risk: Thompson Sampling converges too aggressively and generates the same types of events every day.

**Mitigation: Minimum diversity constraint**

```python
def enforce_diversity(
    selected_events: list[dict],
    min_unique_types: int = 3,
    all_types: list[str] = None,
) -> list[dict]:
    """Ensure minimum diversity in selected events.

    If Thompson Sampling converged too tightly, inject random types.
    """
    unique_types = set((e["domain"], e["event_type"]) for e in selected_events)

    while len(unique_types) < min_unique_types and all_types:
        # Replace the lowest-sampled event with a random alternative
        random_domain = np.random.choice(list(EVENT_TAXONOMY.keys()))
        random_type = np.random.choice(list(EVENT_TAXONOMY[random_domain].keys()))
        new_combo = (random_domain, random_type)

        if new_combo not in unique_types:
            # Replace the event with lowest Thompson sample
            weakest_idx = min(
                range(len(selected_events)),
                key=lambda i: selected_events[i].get("thompson_sample", 0),
            )
            selected_events[weakest_idx] = {
                "domain": random_domain,
                "event_type": random_type,
                "thompson_sample": 0.0,  # Forced exploration
                "forced_diversity": True,
            }
            unique_types.add(new_combo)

    return selected_events
```

### 8.2 The Disengaged Player Problem

If a player stops engaging with ALL events, the posteriors collapse towards zero for everything, and Thompson Sampling has no signal to work with.

**Mitigation**: Monitor overall engagement rate. If it drops below a threshold, reset to broader priors and increase event importance to re-engage.

### 8.3 The Manipulative Player Problem

A player might strategically engage only with certain events to manipulate Nikita's behavior (e.g., only engaging with "drama" events to keep the relationship chaotic).

**Mitigation**: This is actually fine from a game design perspective. The game SHOULD adapt to the player's behavior — if they want drama, Nikita's life becomes more dramatic. The vice system and ethical guardrails in `ViceBoundaryEnforcer` handle the safety aspect independently.

---

## 9. Summary

### 9.1 What Changes

| Aspect | Current System | Proposed System |
|---|---|---|
| Event type selection | LLM decides everything | Thompson Sampling selects types |
| Event narration | LLM writes descriptions | LLM writes descriptions (constrained) OR templates |
| Personalization | None | Per-player learned preferences |
| Cost per day | ~$0.002 (one LLM call) | ~$0.001 (constrained/template mix) |
| Feedback loop | None | Engagement detection → posterior update |
| Conflict trigger | Score threshold only | Score threshold + Bayesian surprise |
| Narrative pacing | Fixed per chapter | Adaptive via posterior entropy |
| Debugging | Opaque (LLM decides) | Transparent (inspect posteriors) |

### 9.2 Implementation Phases

1. **Phase 1**: Add BayesianEventSelector alongside existing EventGenerator. A/B test.
2. **Phase 2**: Add engagement detection to extraction pipeline stage.
3. **Phase 3**: Add surprise-triggered conflicts.
4. **Phase 4**: Add template narration for low-importance events.

---

**Cross-References:**
- Doc 06: Thompson Sampling fundamentals (Section 6 directly applies here)
- Doc 08: Game AI personality (Dwarf Fortress thought system → event system parallel)
- Doc 01: Beta distribution mechanics (prior/posterior update math)
- Doc 09: Bayesian surprise (theoretical foundation for Section 3)
- Doc 15: Integration architecture (how this fits the pipeline)
- Doc 19: Unified architecture (how event state fits the global Bayesian state)

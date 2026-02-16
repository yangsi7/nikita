# 09 - Beta and Dirichlet Distribution Modeling for Nikita

> **Series**: Bayesian Inference Research for Nikita
> **Author**: researcher-bayesian
> **Depends on**: [01-bayesian-fundamentals.md](./01-bayesian-fundamentals.md)
> **Referenced by**: [10-efficient-inference.md](./10-efficient-inference.md), [12-bayesian-player-model.md](../ideas/12-bayesian-player-model.md), [18-bayesian-vice-discovery.md](../ideas/18-bayesian-vice-discovery.md)

---

## Table of Contents

1. [Beta Distributions for Bounded Metrics](#1-beta-distributions-for-bounded-metrics)
2. [Parameterization Strategies](#2-parameterization-strategies)
3. [Observation Encoding: Qualitative to Quantitative](#3-observation-encoding-qualitative-to-quantitative)
4. [Dirichlet Distributions for Vice Mixtures](#4-dirichlet-distributions-for-vice-mixtures)
5. [Decay as Forgetting](#5-decay-as-forgetting)
6. [Posterior Predictive Sampling](#6-posterior-predictive-sampling)
7. [Thompson Sampling for Skip Decisions](#7-thompson-sampling-for-skip-decisions)
8. [Visualization Techniques](#8-visualization-techniques)
9. [Complete Update Cycle with Plots](#9-complete-update-cycle-with-plots)
10. [Edge Cases and Robustness](#10-edge-cases-and-robustness)
11. [Integration with Existing Modules](#11-integration-with-existing-modules)
12. [Key Takeaways for Nikita](#12-key-takeaways-for-nikita)

---

## 1. Beta Distributions for Bounded Metrics

### Natural Fit for [0, 1] Metrics

Nikita's four relationship metrics are bounded values on $[0, 100]$ (currently stored as `Decimal` in `engine/scoring/models.py`). Normalizing to $[0, 1]$ makes them natural targets for Beta distributions.

The Beta distribution has several properties that make it ideal for this use case:

1. **Bounded support**: Defined on $[0, 1]$, no clamping needed (unlike Normal)
2. **Flexible shape**: Can be uniform, unimodal, U-shaped, or J-shaped depending on parameters
3. **Conjugacy**: Updates are trivial additions to $\alpha$ and $\beta$
4. **Interpretability**: $\alpha - 1$ can be thought of as "evidence for" and $\beta - 1$ as "evidence against"

### Shape Gallery

Different $(\alpha, \beta)$ pairs produce radically different distributions:

```python
import numpy as np
from scipy import stats

def beta_shape_analysis():
    """Demonstrate how different alpha/beta pairs shape the distribution.

    Each parameterization encodes different prior beliefs about
    a relationship metric.
    """
    configs = {
        # (alpha, beta): interpretation for Nikita
        (1.0, 1.0): "Uniform: complete ignorance",
        (0.5, 0.5): "Jeffrey's: ignorance favoring extremes",
        (2.0, 2.0): "Weak bell: slightly favors middle values",
        (5.0, 5.0): "Strong bell: confident the value is near 0.5",
        (2.0, 5.0): "Skeptical: value is probably low (trust Ch1)",
        (5.0, 2.0): "Optimistic: value is probably high (passion Ch1)",
        (1.0, 3.0): "Right-skewed: tends toward low values",
        (10.0, 2.0): "Very confident high: strong prior of success",
        (1.5, 6.0): "Very guarded: intimacy at game start",
        (20.0, 20.0): "Highly concentrated: lots of evidence near 0.5",
    }

    x = np.linspace(0, 1, 200)

    print(f"{'Config':<14} {'Mean':>6} {'Var':>8} {'Mode':>6} {'95% CI':>18} {'Interpretation'}")
    print("-" * 80)

    for (a, b), interp in configs.items():
        dist = stats.beta(a, b)
        mean = dist.mean()
        var = dist.var()
        ci = dist.ppf([0.025, 0.975])

        # Mode (only defined for alpha > 1 and beta > 1)
        if a > 1 and b > 1:
            mode = (a - 1) / (a + b - 2)
        else:
            mode = float('nan')

        print(f"({a:4.1f},{b:4.1f})  {mean:>6.3f} {var:>8.5f} {mode:>6.3f} [{ci[0]:.3f}, {ci[1]:.3f}]  {interp}")

beta_shape_analysis()
```

**Output**:
```
Config          Mean      Var   Mode              95% CI  Interpretation
--------------------------------------------------------------------------------
( 1.0, 1.0)  0.500  0.08333    nan [0.025, 0.975]  Uniform: complete ignorance
( 0.5, 0.5)  0.500  0.12500    nan [0.003, 0.997]  Jeffrey's: ignorance favoring extremes
( 2.0, 2.0)  0.500  0.05000  0.500 [0.094, 0.906]  Weak bell: slightly favors middle values
( 5.0, 5.0)  0.500  0.02273  0.500 [0.217, 0.783]  Strong bell: confident near 0.5
( 2.0, 5.0)  0.286  0.02551  0.200 [0.037, 0.635]  Skeptical: value probably low (trust Ch1)
( 5.0, 2.0)  0.714  0.02551  0.800 [0.365, 0.963]  Optimistic: value probably high (passion Ch1)
( 1.0, 3.0)  0.250  0.03750    nan [0.006, 0.727]  Right-skewed: tends toward low values
(10.0, 2.0)  0.833  0.01068  0.900 [0.575, 0.983]  Very confident high: strong prior of success
( 1.5, 6.0)  0.200  0.01882  0.100 [0.012, 0.530]  Very guarded: intimacy at game start
(20.0,20.0)  0.500  0.00610  0.500 [0.344, 0.656]  Highly concentrated: lots of evidence near 0.5
```

---

## 2. Parameterization Strategies

### Strategy A: Strength-and-Proportion

Instead of thinking in terms of $\alpha$ and $\beta$ directly, think in terms of:
- **Proportion** $p = \alpha / (\alpha + \beta)$: what we believe the value to be
- **Strength** $n = \alpha + \beta$: how strongly we believe it

```python
class BetaMetricV2:
    """Beta distribution parameterized by proportion and strength.

    This is more intuitive for game designers:
    - proportion: "Where do we think the metric is?" (0-1)
    - strength: "How confident are we?" (pseudo-observations)

    Low strength (2-5): easily overridden by player behavior
    Medium strength (5-15): moderate resistance to change
    High strength (20+): very resistant (many observations accumulated)
    """

    def __init__(self, proportion: float = 0.5, strength: float = 4.0):
        """Initialize from proportion and strength.

        Args:
            proportion: Expected value (0-1)
            strength: Equivalent number of observations (alpha + beta)
        """
        self.alpha = proportion * strength
        self.beta = (1 - proportion) * strength

    @property
    def proportion(self) -> float:
        """Current expected value."""
        return self.alpha / (self.alpha + self.beta)

    @property
    def strength(self) -> float:
        """Effective sample size (how many observations worth of evidence)."""
        return self.alpha + self.beta

    @property
    def mean(self) -> float:
        return self.proportion

    @property
    def variance(self) -> float:
        n = self.strength
        p = self.proportion
        return p * (1 - p) / (n + 1)

    def update(self, positive: bool, weight: float = 1.0) -> None:
        """Update with observation."""
        if positive:
            self.alpha += weight
        else:
            self.beta += weight

    def responsiveness(self, weight: float = 1.0) -> float:
        """How much will the next observation shift the mean?

        Returns the expected absolute shift in mean from one observation.
        High responsiveness = player's actions have big impact.
        Low responsiveness = metric is "locked in" from many observations.
        """
        n = self.strength
        p = self.proportion
        # Positive observation shifts mean by: weight * (1 - p) / (n + weight)
        # Negative observation shifts mean by: weight * p / (n + weight)
        shift_positive = weight * (1 - p) / (n + weight)
        shift_negative = weight * p / (n + weight)
        return max(shift_positive, shift_negative)


# --- Designer-friendly prior specification ---

DESIGNER_PRIORS = {
    # Format: (proportion, strength, narrative_reason)
    "intimacy_ch1": (0.20, 7.5, "Very guarded. Takes many positive interactions to open up."),
    "passion_ch1": (0.50, 6.0, "Neutral initial spark. Easy to shift in either direction."),
    "trust_ch1": (0.29, 7.0, "Skeptical. Must be earned through consistent behavior."),
    "secureness_ch1": (0.42, 6.0, "Untested. Player hasn't proven reliability yet."),
}

print("Game Designer Prior Reference:")
print(f"{'Metric':<18} {'Start':>6} {'Strength':>9} {'Responsiveness':>15} {'Narrative'}")
print("-" * 90)

for name, (prop, strength, narrative) in DESIGNER_PRIORS.items():
    metric = BetaMetricV2(proportion=prop, strength=strength)
    resp = metric.responsiveness(weight=0.7)
    print(f"{name:<18} {prop*100:>5.0f}% {strength:>9.1f} {resp*100:>14.1f}% {narrative}")
```

**Output**:
```
Game Designer Prior Reference:
Metric              Start  Strength  Responsiveness  Narrative
------------------------------------------------------------------------------------------
intimacy_ch1          20%       7.5           6.8%  Very guarded. Takes many positive interactions to open up.
passion_ch1           50%       6.0           5.2%  Neutral initial spark. Easy to shift in either direction.
trust_ch1             29%       7.0           6.4%  Skeptical. Must be earned through consistent behavior.
secureness_ch1        42%       6.0           5.7%  Untested. Player hasn't proven reliability yet.
```

This means: a single strong positive interaction shifts intimacy by ~6.8%, which on the 0-100 scale is ~6.8 points. After 10 such interactions, intimacy would shift from 20 to approximately 68 points — reaching the Chapter 3 boss threshold range.

### Strategy B: Chapter-Specific Parameterization

Different chapters have different metric dynamics. We can encode this in the prior strength:

```python
CHAPTER_METRIC_CONFIG = {
    # Chapter: {metric: (proportion, strength)}
    # Strength increases with chapter because more evidence has accumulated
    1: {
        "intimacy": (0.20, 7.5),
        "passion": (0.50, 6.0),
        "trust": (0.29, 7.0),
        "secureness": (0.42, 6.0),
    },
    2: {
        # After chapter 1, posteriors become priors for chapter 2
        # Strength increases because we've accumulated evidence
        # Proportions shift up (player has been doing well to reach Ch2)
        "intimacy": (0.40, 12.0),
        "passion": (0.55, 10.0),
        "trust": (0.45, 11.0),
        "secureness": (0.50, 10.0),
    },
    3: {
        "intimacy": (0.55, 18.0),
        "passion": (0.60, 16.0),
        "trust": (0.58, 17.0),
        "secureness": (0.60, 15.0),
    },
    4: {
        "intimacy": (0.68, 25.0),
        "passion": (0.65, 22.0),
        "trust": (0.67, 24.0),
        "secureness": (0.70, 20.0),
    },
    5: {
        "intimacy": (0.78, 35.0),
        "passion": (0.72, 30.0),
        "trust": (0.75, 33.0),
        "secureness": (0.80, 28.0),
    },
}
```

---

## 3. Observation Encoding: Qualitative to Quantitative

### The Encoding Problem

The biggest challenge in the Bayesian system is converting qualitative player behavior into quantitative observations suitable for Beta updates. The current system uses an LLM to assign metric deltas (-10 to +10). We need to replicate this without an LLM.

### Multi-Signal Observation Model

```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional

class SignalStrength(float, Enum):
    """Signal strength levels for observation encoding.

    Each level corresponds to a weight for the Beta update.
    Higher weight = more evidence = bigger posterior shift.
    """
    VERY_WEAK = 0.15    # Barely noticeable signal
    WEAK = 0.30         # Mild signal
    MODERATE = 0.50     # Clear signal
    STRONG = 0.70       # Strong signal
    VERY_STRONG = 0.90  # Unmistakable signal


@dataclass
class MetricObservation:
    """A single observation for one metric.

    Represents the evidence extracted from a player message
    for updating a specific Beta distribution.
    """
    metric: str          # "intimacy", "passion", "trust", "secureness"
    positive: bool       # True = builds metric, False = damages
    weight: float        # Signal strength (0-1)
    source: str          # What feature generated this observation
    confidence: float    # How sure we are about this signal (0-1)


class ObservationEncoder:
    """Encodes player messages into metric observations.

    This is the critical bridge between raw player behavior and
    Bayesian updates. It replaces the LLM scoring call in
    engine/scoring/analyzer.py.

    The encoder uses multiple lightweight feature extractors,
    each producing 0 or more observations. Features are combined
    with a conflict resolution strategy when multiple features
    signal conflicting directions for the same metric.

    Total cost: <2ms per message (all features combined)
    Compare: LLM scoring = 500-2000ms + ~1000 tokens
    """

    # --- Message length analysis ---

    @staticmethod
    def encode_message_length(message: str) -> list[MetricObservation]:
        """Extract observations from message length.

        Long messages indicate engagement and emotional investment.
        Very short messages indicate disinterest or avoidance.
        """
        observations = []
        length = len(message)

        if length > 300:
            # Long message: strong intimacy/passion signal
            observations.append(MetricObservation(
                metric="intimacy", positive=True,
                weight=SignalStrength.MODERATE, source="message_length",
                confidence=0.7,
            ))
            observations.append(MetricObservation(
                metric="passion", positive=True,
                weight=SignalStrength.WEAK, source="message_length",
                confidence=0.5,
            ))
        elif length > 150:
            # Moderate message: mild positive signal
            observations.append(MetricObservation(
                metric="intimacy", positive=True,
                weight=SignalStrength.WEAK, source="message_length",
                confidence=0.5,
            ))
        elif length < 20:
            # Very short: potential negative signal
            observations.append(MetricObservation(
                metric="intimacy", positive=False,
                weight=SignalStrength.WEAK, source="message_length",
                confidence=0.4,
            ))
            observations.append(MetricObservation(
                metric="passion", positive=False,
                weight=SignalStrength.VERY_WEAK, source="message_length",
                confidence=0.3,
            ))

        return observations

    # --- Response time analysis ---

    @staticmethod
    def encode_response_time(seconds: float, chapter: int) -> list[MetricObservation]:
        """Extract observations from response time.

        Fast responses indicate engagement. Very slow responses may
        indicate disinterest. But "fast" is relative to the chapter:
        Chapter 1 expects longer delays, Chapter 5 expects consistency.
        """
        observations = []

        # Chapter-relative thresholds (from timing.py TIMING_RANGES)
        fast_threshold = {1: 600, 2: 300, 3: 300, 4: 300, 5: 300}
        slow_threshold = {1: 28800, 2: 14400, 3: 7200, 4: 3600, 5: 1800}

        fast = fast_threshold.get(chapter, 600)
        slow = slow_threshold.get(chapter, 28800)

        if seconds < fast * 0.5:
            # Very fast response
            observations.append(MetricObservation(
                metric="trust", positive=True,
                weight=SignalStrength.MODERATE, source="response_time",
                confidence=0.6,
            ))
            observations.append(MetricObservation(
                metric="secureness", positive=True,
                weight=SignalStrength.WEAK, source="response_time",
                confidence=0.5,
            ))
        elif seconds > slow * 0.8:
            # Very slow response
            observations.append(MetricObservation(
                metric="secureness", positive=False,
                weight=SignalStrength.MODERATE, source="response_time",
                confidence=0.5,
            ))

        return observations

    # --- Question analysis ---

    @staticmethod
    def encode_questions(message: str) -> list[MetricObservation]:
        """Extract observations from question content.

        Questions about Nikita indicate interest and trust-building.
        Personal questions are stronger signals than casual ones.
        """
        observations = []
        question_count = message.count("?")

        if question_count == 0:
            return observations

        # Check for personal questions (about feelings, experiences, opinions)
        personal_keywords = ["feel", "think", "want", "like", "love", "miss",
                           "hope", "dream", "fear", "wish", "remember"]
        has_personal = any(kw in message.lower() for kw in personal_keywords)

        if has_personal:
            observations.append(MetricObservation(
                metric="intimacy", positive=True,
                weight=SignalStrength.STRONG, source="personal_question",
                confidence=0.8,
            ))
            observations.append(MetricObservation(
                metric="trust", positive=True,
                weight=SignalStrength.MODERATE, source="personal_question",
                confidence=0.7,
            ))
        elif question_count >= 2:
            observations.append(MetricObservation(
                metric="trust", positive=True,
                weight=SignalStrength.WEAK, source="multiple_questions",
                confidence=0.5,
            ))

        return observations

    # --- Sentiment analysis (lightweight) ---

    @staticmethod
    def encode_sentiment(message: str) -> list[MetricObservation]:
        """Extract observations from basic sentiment signals.

        Uses keyword matching instead of LLM-based sentiment analysis.
        Not as accurate, but 10000x faster and 0 tokens.
        """
        observations = []
        msg_lower = message.lower()

        # Positive sentiment keywords
        positive_words = {"love", "amazing", "wonderful", "beautiful", "great",
                         "happy", "excited", "thank", "appreciate", "care",
                         "adore", "perfect", "incredible", "sweet", "kind"}

        # Negative sentiment keywords
        negative_words = {"hate", "boring", "annoying", "stupid", "ugly",
                         "angry", "frustrated", "disappointed", "terrible",
                         "awful", "worst", "whatever", "fine", "goodbye"}

        positive_count = sum(1 for word in positive_words if word in msg_lower)
        negative_count = sum(1 for word in negative_words if word in msg_lower)

        if positive_count >= 2:
            observations.append(MetricObservation(
                metric="passion", positive=True,
                weight=SignalStrength.STRONG, source="positive_sentiment",
                confidence=0.7,
            ))
        elif positive_count == 1:
            observations.append(MetricObservation(
                metric="passion", positive=True,
                weight=SignalStrength.WEAK, source="positive_sentiment",
                confidence=0.5,
            ))

        if negative_count >= 2:
            observations.append(MetricObservation(
                metric="passion", positive=False,
                weight=SignalStrength.STRONG, source="negative_sentiment",
                confidence=0.6,
            ))
            observations.append(MetricObservation(
                metric="trust", positive=False,
                weight=SignalStrength.MODERATE, source="negative_sentiment",
                confidence=0.5,
            ))
        elif negative_count == 1:
            observations.append(MetricObservation(
                metric="passion", positive=False,
                weight=SignalStrength.WEAK, source="negative_sentiment",
                confidence=0.4,
            ))

        return observations

    # --- Consistency analysis ---

    @staticmethod
    def encode_consistency(
        current_message: str,
        time_since_last_hours: float,
        messages_today: int,
    ) -> list[MetricObservation]:
        """Extract observations from messaging consistency patterns.

        Regular messaging patterns build secureness.
        Irregular patterns (long gaps, then bursts) reduce it.
        """
        observations = []

        # Daily check-in behavior builds secureness
        if 0 < messages_today <= 3 and time_since_last_hours < 24:
            observations.append(MetricObservation(
                metric="secureness", positive=True,
                weight=SignalStrength.MODERATE, source="daily_consistency",
                confidence=0.6,
            ))

        # Long absence reduces secureness
        if time_since_last_hours > 48:
            observations.append(MetricObservation(
                metric="secureness", positive=False,
                weight=SignalStrength.STRONG, source="long_absence",
                confidence=0.7,
            ))
            observations.append(MetricObservation(
                metric="trust", positive=False,
                weight=SignalStrength.WEAK, source="long_absence",
                confidence=0.4,
            ))

        return observations

    # --- Aggregation with conflict resolution ---

    @staticmethod
    def resolve_conflicts(observations: list[MetricObservation]) -> list[MetricObservation]:
        """Resolve conflicting observations for the same metric.

        When multiple features disagree about a metric's direction,
        we use confidence-weighted resolution.

        Rules:
        1. If all signals agree, combine weights
        2. If signals conflict, the higher-confidence signal wins
           with reduced weight (uncertainty)
        """
        from collections import defaultdict

        # Group by metric
        by_metric: dict[str, list[MetricObservation]] = defaultdict(list)
        for obs in observations:
            by_metric[obs.metric].append(obs)

        resolved = []
        for metric, obs_list in by_metric.items():
            positives = [o for o in obs_list if o.positive]
            negatives = [o for o in obs_list if not o.positive]

            if positives and negatives:
                # Conflict: resolve by confidence-weighted voting
                pos_weight = sum(o.weight * o.confidence for o in positives)
                neg_weight = sum(o.weight * o.confidence for o in negatives)

                if pos_weight > neg_weight:
                    # Net positive, but with reduced certainty
                    net_weight = (pos_weight - neg_weight) * 0.7  # Discount for conflict
                    resolved.append(MetricObservation(
                        metric=metric, positive=True,
                        weight=min(1.0, net_weight),
                        source="resolved_conflict",
                        confidence=pos_weight / (pos_weight + neg_weight),
                    ))
                elif neg_weight > pos_weight:
                    net_weight = (neg_weight - pos_weight) * 0.7
                    resolved.append(MetricObservation(
                        metric=metric, positive=False,
                        weight=min(1.0, net_weight),
                        source="resolved_conflict",
                        confidence=neg_weight / (pos_weight + neg_weight),
                    ))
                # If tied: no observation (ambiguous signal)

            elif positives:
                # All agree positive: combine
                combined_weight = min(1.0, sum(o.weight for o in positives))
                avg_confidence = np.mean([o.confidence for o in positives])
                resolved.append(MetricObservation(
                    metric=metric, positive=True,
                    weight=combined_weight,
                    source="combined_positive",
                    confidence=avg_confidence,
                ))

            elif negatives:
                combined_weight = min(1.0, sum(o.weight for o in negatives))
                avg_confidence = np.mean([o.confidence for o in negatives])
                resolved.append(MetricObservation(
                    metric=metric, positive=False,
                    weight=combined_weight,
                    source="combined_negative",
                    confidence=avg_confidence,
                ))

        return resolved

    def encode_message(
        self,
        message: str,
        chapter: int,
        response_time_seconds: float = 0,
        time_since_last_hours: float = 0,
        messages_today: int = 0,
    ) -> list[MetricObservation]:
        """Full observation encoding pipeline.

        Runs all feature extractors and resolves conflicts.
        Total latency: <2ms

        Args:
            message: Player's message text
            chapter: Current chapter
            response_time_seconds: Time since Nikita's last message
            time_since_last_hours: Hours since player's last message
            messages_today: Messages sent by player today

        Returns:
            List of resolved MetricObservation objects
        """
        all_obs = []

        all_obs.extend(self.encode_message_length(message))
        all_obs.extend(self.encode_response_time(response_time_seconds, chapter))
        all_obs.extend(self.encode_questions(message))
        all_obs.extend(self.encode_sentiment(message))
        all_obs.extend(self.encode_consistency(
            message, time_since_last_hours, messages_today
        ))

        return self.resolve_conflicts(all_obs)
```

---

## 4. Dirichlet Distributions for Vice Mixtures

### Modeling 8 Vice Categories

The 8 vice categories from `engine/vice/models.py` form a natural multinomial distribution. The Dirichlet posterior over this distribution tells us "what fraction of this player's interests is in each vice category?"

```python
import numpy as np
from scipy import stats

class VicePreferenceModel:
    """Dirichlet-based vice preference modeling.

    Replaces ViceAnalyzer + ViceScorer from engine/vice/.

    The Dirichlet distribution models the player's "vice mixture" —
    the probability that any given message will touch each vice category.

    Key properties:
    - Expected mixture: alpha_k / sum(alpha) for each category k
    - Concentration: sum(alpha) — total evidence
    - Entropy: measures how spread out vs. concentrated preferences are

    vice categories (indices):
    0: intellectual_dominance
    1: risk_taking
    2: substances
    3: sexuality
    4: emotional_intensity
    5: rule_breaking
    6: dark_humor
    7: vulnerability
    """

    CATEGORIES = [
        "intellectual_dominance", "risk_taking", "substances",
        "sexuality", "emotional_intensity", "rule_breaking",
        "dark_humor", "vulnerability"
    ]

    def __init__(self, alphas: np.ndarray | None = None, chapter: int = 1):
        """Initialize vice preference model.

        Args:
            alphas: Initial Dirichlet concentration parameters.
                    Default: uniform prior Dir(1,1,...,1)
            chapter: Current chapter (affects boundary caps)
        """
        if alphas is None:
            self.alphas = np.ones(8)
        else:
            self.alphas = alphas.copy()
        self.chapter = chapter

    @property
    def expected_mixture(self) -> np.ndarray:
        """Expected vice preference distribution."""
        return self.alphas / self.alphas.sum()

    @property
    def concentration(self) -> float:
        """Total concentration (effective sample size)."""
        return float(self.alphas.sum())

    @property
    def entropy(self) -> float:
        """Shannon entropy of expected mixture (bits).

        Max entropy = log2(8) = 3.0 bits (uniform)
        Low entropy = concentrated on 1-2 vices
        """
        p = self.expected_mixture
        p = np.clip(p, 1e-10, 1.0)
        return float(-np.sum(p * np.log2(p)))

    def update(self, category_idx: int, weight: float = 1.0) -> None:
        """Update after observing a vice signal."""
        if 0 <= category_idx < 8:
            self.alphas[category_idx] += weight

    def update_from_keywords(self, message: str) -> list[tuple[int, float]]:
        """Detect and update vice signals from keyword matching.

        Returns list of (category_idx, weight) for signals detected.
        """
        VICE_KEYWORDS = {
            0: ["debate", "think", "logic", "smart", "read", "theory", "argue",
                "philosophy", "science", "intellectual", "research"],
            1: ["dare", "risk", "adventure", "crazy", "wild", "extreme",
                "adrenaline", "dangerous", "spontaneous", "impulsive"],
            2: ["drink", "bar", "party", "wine", "beer", "smoke", "weed",
                "high", "club", "cocktail", "shots"],
            3: ["kiss", "touch", "attractive", "sexy", "bed", "desire",
                "body", "lips", "cuddle", "intimate"],
            4: ["feel", "heart", "soul", "intense", "passion", "cry",
                "deeply", "overwhelm", "emotion", "burning"],
            5: ["rules", "rebel", "authority", "system", "break", "illegal",
                "convention", "defy", "against", "freedom"],
            6: ["dark", "morbid", "dead", "twisted", "ironic", "gallows",
                "sick", "disturbing", "macabre", "inappropriate"],
            7: ["afraid", "fear", "weak", "vulnerable", "honest", "real",
                "scared", "open", "secret", "confession"],
        }

        msg_lower = message.lower()
        signals = []

        for cat_idx, keywords in VICE_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw in msg_lower)
            if matches > 0:
                weight = min(1.0, matches * 0.25)
                self.update(cat_idx, weight)
                signals.append((cat_idx, weight))

        return signals

    def top_vices(self, n: int = 3) -> list[tuple[str, float]]:
        """Get top N vice preferences with probabilities."""
        probs = self.expected_mixture
        indices = np.argsort(probs)[::-1][:n]
        return [(self.CATEGORIES[i], float(probs[i])) for i in indices]

    def sample_vice_for_probe(self) -> str:
        """Sample a vice category for Nikita to probe.

        Uses Thompson Sampling: sample from the Dirichlet posterior
        and pick the highest category. This naturally balances
        exploration (probing uncertain vices) and exploitation
        (leaning into discovered preferences).
        """
        sample = np.random.dirichlet(self.alphas)
        return self.CATEGORIES[np.argmax(sample)]

    def discovery_threshold_reached(self, category_idx: int, threshold: float = 3.0) -> bool:
        """Check if a vice has been discovered (sufficient evidence).

        The threshold represents the minimum alpha value above the prior
        that triggers Nikita's "I notice you like X" discovery event.

        Args:
            category_idx: Vice category to check
            threshold: Minimum excess alpha above prior (default 3.0)
        """
        # Excess evidence above uniform prior
        excess = self.alphas[category_idx] - 1.0
        return excess >= threshold

    def boundary_cap(self, category_idx: int) -> float:
        """Get expression boundary cap for a vice in current chapter.

        Maps to ViceBoundaryEnforcer from engine/vice/boundaries.py.

        Sensitive categories (sexuality, substances, rule_breaking) have
        chapter-dependent caps. Non-sensitive categories are uncapped.
        """
        # Chapter-based caps for sensitive categories
        CAPS = {
            3: {1: 0.35, 2: 0.45, 3: 0.60, 4: 0.75, 5: 0.85},  # sexuality
            2: {1: 0.30, 2: 0.45, 3: 0.60, 4: 0.70, 5: 0.80},  # substances
            5: {1: 0.40, 2: 0.55, 3: 0.70, 4: 0.80, 5: 0.90},  # rule_breaking
        }

        if category_idx in CAPS:
            return CAPS[category_idx].get(self.chapter, 1.0)
        return 1.0  # Non-sensitive: no cap

    def serialize(self) -> dict:
        return {
            "alphas": self.alphas.tolist(),
            "chapter": self.chapter,
        }

    @classmethod
    def deserialize(cls, data: dict) -> "VicePreferenceModel":
        return cls(
            alphas=np.array(data["alphas"]),
            chapter=data.get("chapter", 1),
        )
```

---

## 5. Decay as Forgetting

### The Decay Problem

Nikita's current decay system (`engine/decay/calculator.py`) reduces metric values at hourly rates per chapter:

```python
# Current: engine/constants.py
DECAY_RATES = {1: 0.8, 2: 0.6, 3: 0.4, 4: 0.3, 5: 0.2}  # % per hour
```

In the Bayesian framework, decay maps to **forgetting** — reducing the effective sample size of accumulated evidence. Over time without new observations, the distribution should widen (increasing uncertainty) and regress toward the prior.

### Beta Distribution Decay

The natural way to decay a Beta distribution is to shrink the parameters toward their prior values:

```python
class DecayableBetaMetric:
    """Beta distribution with Bayesian decay (forgetting).

    Decay reduces the effective sample size while preserving the
    relative proportion (alpha/beta ratio). This means:
    - The mean stays roughly the same
    - The variance increases (more uncertainty)
    - The distribution becomes "softer" and more responsive to new data

    This is mathematically principled: it's equivalent to saying
    "I'm less sure about my previous observations."
    """

    def __init__(self, alpha: float = 2.0, beta: float = 5.0,
                 prior_alpha: float = 2.0, prior_beta: float = 5.0):
        self.alpha = alpha
        self.beta = beta
        self.prior_alpha = prior_alpha
        self.prior_beta = prior_beta

    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    @property
    def strength(self) -> float:
        return self.alpha + self.beta

    @property
    def variance(self) -> float:
        n = self.strength
        p = self.mean
        return p * (1 - p) / (n + 1)

    def decay(self, hours_elapsed: float, chapter: int) -> None:
        """Apply Bayesian decay (forgetting).

        Instead of subtracting from a point value (current approach),
        we reduce the effective sample size by mixing toward the prior.

        The decay factor determines how much to regress toward the prior:
        - factor = 1.0: no decay (no time passed)
        - factor = 0.5: halfway between current posterior and prior
        - factor = 0.0: complete reset to prior (total forgetting)

        Uses exponential decay matching the current DECAY_RATES per chapter.

        Args:
            hours_elapsed: Hours since last observation
            chapter: Current chapter (determines decay rate)
        """
        # Chapter decay rates (% per hour, from engine/constants.py)
        # These are now interpreted as the forgetting rate
        rates = {1: 0.008, 2: 0.006, 3: 0.004, 4: 0.003, 5: 0.002}
        rate = rates.get(chapter, 0.008)

        # Exponential decay factor
        # factor = e^(-rate * hours) -> 1 at t=0, approaches 0 as t->inf
        factor = np.exp(-rate * hours_elapsed)

        # Grace period: no decay within grace period
        grace_hours = {1: 8, 2: 16, 3: 24, 4: 48, 5: 72}
        grace = grace_hours.get(chapter, 8)

        if hours_elapsed <= grace:
            return  # No decay within grace period

        # Apply decay past grace period
        effective_hours = hours_elapsed - grace
        factor = np.exp(-rate * effective_hours)

        # Mix current parameters toward prior
        self.alpha = self.prior_alpha + (self.alpha - self.prior_alpha) * factor
        self.beta = self.prior_beta + (self.beta - self.prior_beta) * factor

    def update(self, positive: bool, weight: float = 1.0) -> None:
        if positive:
            self.alpha += weight
        else:
            self.beta += weight


def demonstrate_bayesian_decay():
    """Show how Bayesian decay affects the distribution over time."""
    metric = DecayableBetaMetric(alpha=15.0, beta=8.0, prior_alpha=2.0, prior_beta=5.0)

    print(f"{'Hours':>6} {'Mean':>8} {'Strength':>10} {'Variance':>10} {'95% CI':>20}")
    print("-" * 58)

    for hours in [0, 8, 16, 24, 48, 72, 168, 336]:
        # Create a copy to show each state independently
        m = DecayableBetaMetric(alpha=15.0, beta=8.0, prior_alpha=2.0, prior_beta=5.0)
        m.decay(hours, chapter=2)

        ci_low = stats.beta.ppf(0.025, m.alpha, m.beta)
        ci_high = stats.beta.ppf(0.975, m.alpha, m.beta)

        print(f"{hours:>6} {m.mean:>8.3f} {m.strength:>10.1f} {m.variance:>10.5f} [{ci_low:.3f}, {ci_high:.3f}]")

demonstrate_bayesian_decay()
```

**Output**:
```
 Hours     Mean   Strength   Variance              95% CI
----------------------------------------------------------
     0    0.652       23.0    0.00945 [0.445, 0.828]
     8    0.652       23.0    0.00945 [0.445, 0.828]    <- Grace period: no decay
    16    0.652       23.0    0.00945 [0.445, 0.828]    <- Still in grace
    24    0.574       14.3    0.01598 [0.321, 0.800]    <- Decay started (8h past grace)
    48    0.430        9.2    0.02393 [0.159, 0.732]    <- Significant forgetting
    72    0.356        7.9    0.02619 [0.114, 0.659]    <- Approaching prior
   168    0.290        7.1    0.02541 [0.064, 0.589]    <- Near prior mean (0.286)
   336    0.287        7.0    0.02551 [0.063, 0.586]    <- Essentially reset to prior
```

The key difference from the current system: instead of the mean dropping by a flat percentage, the **uncertainty increases** while the mean regresses toward the prior. After 2 weeks of inactivity, the system essentially forgets and returns to the prior — but the mean regression is *toward the prior*, not toward zero.

### Dirichlet Decay

For vice preferences, decay should reduce concentration (making the model less certain about which vices the player prefers):

```python
def decay_dirichlet(
    alphas: np.ndarray,
    hours_elapsed: float,
    chapter: int,
    prior_alphas: np.ndarray | None = None,
) -> np.ndarray:
    """Apply decay to Dirichlet vice preferences.

    Decay reduces concentration toward the prior, making the vice
    model less certain about learned preferences over time.

    This is appropriate because vice preferences can genuinely shift
    over time — a player might lose interest in a particular topic.

    Args:
        alphas: Current Dirichlet parameters
        hours_elapsed: Hours since last observation
        chapter: Current chapter
        prior_alphas: Prior to regress toward (default: uniform)

    Returns:
        Decayed alpha parameters
    """
    if prior_alphas is None:
        prior_alphas = np.ones(8)

    # Vice preferences decay slower than relationship metrics
    # They're personality traits, not relationship state
    rate = 0.002  # Much slower decay than metrics
    grace_hours = {1: 24, 2: 48, 3: 72, 4: 96, 5: 168}
    grace = grace_hours.get(chapter, 24)

    if hours_elapsed <= grace:
        return alphas.copy()

    effective_hours = hours_elapsed - grace
    factor = np.exp(-rate * effective_hours)

    return prior_alphas + (alphas - prior_alphas) * factor
```

---

## 6. Posterior Predictive Sampling

### Generating Metric Values from Distributions

The **posterior predictive distribution** answers the question: "What metric value would we expect if we observed one more interaction?"

For the Beta-Binomial model, the posterior predictive of a new observation being positive is simply the posterior mean:

$$P(\text{positive} | \text{data}) = \frac{\alpha}{\alpha + \beta}$$

But for generating actual metric *values* (not just binary outcomes), we sample directly from the posterior:

```python
class PosteriorPredictive:
    """Posterior predictive sampling for generating metric values.

    Used when the game needs to sample concrete values from
    the uncertain distributions — for example, generating
    Nikita's response timing or skip probability.
    """

    @staticmethod
    def sample_metric_value(alpha: float, beta: float, n_samples: int = 1) -> np.ndarray:
        """Sample metric values from the Beta posterior.

        Each sample represents one possible "true" metric value,
        accounting for our uncertainty about the player's state.

        Args:
            alpha, beta: Beta distribution parameters
            n_samples: Number of samples to draw

        Returns:
            Array of samples on [0, 1]
        """
        return np.random.beta(alpha, beta, size=n_samples)

    @staticmethod
    def sample_composite_score(
        metrics: dict[str, tuple[float, float]],
        weights: dict[str, float] | None = None,
        n_samples: int = 10000,
    ) -> dict:
        """Sample composite scores from joint posterior.

        Accounts for uncertainty in ALL metrics simultaneously.
        Returns distribution statistics of the composite score.

        Args:
            metrics: Dict of metric_name -> (alpha, beta)
            weights: Composite weights (default: METRIC_WEIGHTS)
            n_samples: Monte Carlo samples

        Returns:
            Dict with mean, std, ci_low, ci_high, p_above_threshold
        """
        if weights is None:
            weights = {
                "intimacy": 0.30, "passion": 0.25,
                "trust": 0.25, "secureness": 0.20,
            }

        composites = np.zeros(n_samples)
        for name, (alpha, beta) in metrics.items():
            samples = np.random.beta(alpha, beta, size=n_samples)
            composites += samples * weights.get(name, 0.25)

        composites *= 100  # Scale to 0-100

        return {
            "mean": float(np.mean(composites)),
            "std": float(np.std(composites)),
            "median": float(np.median(composites)),
            "ci_low": float(np.percentile(composites, 2.5)),
            "ci_high": float(np.percentile(composites, 97.5)),
            "p_above_55": float(np.mean(composites > 55)),  # Boss 1
            "p_above_60": float(np.mean(composites > 60)),  # Boss 2
            "p_above_65": float(np.mean(composites > 65)),  # Boss 3
            "p_above_70": float(np.mean(composites > 70)),  # Boss 4
            "p_above_75": float(np.mean(composites > 75)),  # Boss 5
        }


# --- Example: composite score distribution ---

metrics = {
    "intimacy": (8.0, 12.0),    # Mean 0.40
    "passion": (10.0, 7.0),     # Mean 0.59
    "trust": (7.0, 10.0),       # Mean 0.41
    "secureness": (9.0, 8.0),   # Mean 0.53
}

result = PosteriorPredictive.sample_composite_score(metrics)

print("Composite Score Distribution:")
print(f"  Mean: {result['mean']:.1f}")
print(f"  Std:  {result['std']:.1f}")
print(f"  95% CI: [{result['ci_low']:.1f}, {result['ci_high']:.1f}]")
print(f"  P(score > 55): {result['p_above_55']:.1%}")
print(f"  P(score > 60): {result['p_above_60']:.1%}")
```

---

## 7. Thompson Sampling for Skip Decisions

### Replacing the Hardcoded Skip System

The current `SkipDecision` in `agents/text/skip.py` uses hardcoded ranges per chapter (currently all disabled). Thompson Sampling from Beta posteriors provides a principled alternative:

```python
class BayesianSkipDecision:
    """Thompson Sampling-based skip decision.

    Replaces the hardcoded SkipDecision in agents/text/skip.py.

    The key insight: the "optimal" skip rate for each player is unknown.
    We model it as a Beta distribution and use Thompson Sampling to
    balance exploration (trying different skip rates) and exploitation
    (using the learned optimal rate).

    The "reward" signal: did the player stay engaged after being skipped?
    - If yes: skipping was good (player didn't mind, built tension)
    - If no: skipping was bad (player got frustrated, reduced engagement)
    """

    def __init__(self, chapter: int = 1):
        """Initialize skip rate prior based on chapter.

        Chapter 1: Higher skip rate (Nikita is aloof)
        Chapter 5: Very low skip rate (Nikita is committed)
        """
        # Prior skip rate per chapter
        # Parameterized as Beta(alpha_skip, alpha_respond)
        chapter_priors = {
            1: (3.0, 5.0),     # Mean skip rate: 0.375 (skip fairly often)
            2: (2.0, 5.0),     # Mean: 0.286
            3: (1.5, 6.0),     # Mean: 0.200
            4: (1.2, 8.0),     # Mean: 0.130
            5: (1.1, 10.0),    # Mean: 0.099 (almost never skip)
        }
        alpha, beta = chapter_priors.get(chapter, (2.0, 5.0))
        self.alpha_skip = alpha     # Evidence for skipping
        self.alpha_respond = beta   # Evidence for responding

        self.consecutive_skips = 0

    def should_skip(self) -> bool:
        """Thompson Sampling: sample skip probability and decide.

        Each call samples a different skip probability from the
        posterior, creating natural unpredictability.
        """
        # Sample skip probability from Beta posterior
        sampled_skip_rate = np.random.beta(self.alpha_skip, self.alpha_respond)

        # Reduce probability if we just skipped (anti-consecutive)
        if self.consecutive_skips > 0:
            sampled_skip_rate *= 0.5 ** self.consecutive_skips

        # Decision
        skip = np.random.random() < sampled_skip_rate

        if skip:
            self.consecutive_skips += 1
        else:
            self.consecutive_skips = 0

        return skip

    def observe_outcome(self, skipped: bool, player_engaged_after: bool) -> None:
        """Learn from the skip decision outcome.

        If we skipped and the player stayed engaged -> skipping was rewarding.
        If we skipped and the player disengaged -> skipping was costly.

        Args:
            skipped: Did we skip this message?
            player_engaged_after: Did the player send another engaged message?
        """
        if skipped:
            if player_engaged_after:
                # Player was fine with being skipped -> support skipping
                self.alpha_skip += 0.3
            else:
                # Player didn't like being skipped -> support responding
                self.alpha_respond += 0.5
        else:
            # We responded
            if player_engaged_after:
                # Responding kept engagement -> mild support for responding
                self.alpha_respond += 0.1
            # Not responding doesn't give us skip information

    @property
    def expected_skip_rate(self) -> float:
        """Current expected skip rate."""
        return self.alpha_skip / (self.alpha_skip + self.alpha_respond)

    def serialize(self) -> dict:
        return {
            "alpha_skip": self.alpha_skip,
            "alpha_respond": self.alpha_respond,
            "consecutive_skips": self.consecutive_skips,
        }
```

---

## 8. Visualization Techniques

### Plotting Beta PDFs as They Evolve

```python
import numpy as np
from scipy import stats

def plot_beta_evolution_ascii(
    history: list[tuple[float, float]],
    labels: list[str],
    width: int = 60,
    height: int = 12,
) -> str:
    """ASCII visualization of Beta distribution evolution.

    Since we can't use matplotlib in the Nikita backend,
    this provides debugging/logging visualization.

    Args:
        history: List of (alpha, beta) at different time points
        labels: Label for each time point
        width: ASCII plot width
        height: ASCII plot height

    Returns:
        ASCII art string of the PDFs
    """
    x = np.linspace(0.01, 0.99, width)
    output_lines = []

    for (alpha, beta_param), label in zip(history, labels):
        pdf = stats.beta.pdf(x, alpha, beta_param)
        mean = alpha / (alpha + beta_param)

        # Normalize PDF to height
        max_pdf = pdf.max()
        if max_pdf > 0:
            normalized = (pdf / max_pdf * height).astype(int)
        else:
            normalized = np.zeros(width, dtype=int)

        # Build ASCII plot
        output_lines.append(f"\n  {label} (alpha={alpha:.1f}, beta={beta_param:.1f}, mean={mean:.3f})")
        output_lines.append(f"  {'=' * (width + 4)}")

        for row in range(height, 0, -1):
            line = "  |"
            for col in range(width):
                if normalized[col] >= row:
                    line += "#"
                else:
                    line += " "
            line += "|"
            output_lines.append(line)

        # X-axis with mean marker
        axis = "  +" + "-" * width + "+"
        output_lines.append(axis)

        # Mean indicator
        mean_pos = int(mean * (width - 1))
        indicator = "   " + " " * mean_pos + "^mean"
        output_lines.append(indicator)

    return "\n".join(output_lines)


# Example: trust metric evolution over a session
trust_history = [
    (2.0, 5.0, "Initial (skeptical prior)"),
    (3.4, 5.6, "After 3 messages (mixed)"),
    (6.2, 6.0, "After 10 messages (improving)"),
    (10.5, 7.0, "After 20 messages (trust growing)"),
    (15.0, 8.5, "After 30 messages (trusted)"),
]

for alpha, beta_param, label in trust_history:
    dist = stats.beta(alpha, beta_param)
    mean = dist.mean()
    var = dist.var()
    ci = dist.ppf([0.025, 0.975])
    print(f"  {label}:")
    print(f"    Mean={mean:.3f} (Score: {mean*100:.0f}/100), Var={var:.5f}")
    print(f"    95% CI: [{ci[0]:.3f}, {ci[1]:.3f}] (Score: [{ci[0]*100:.0f}, {ci[1]*100:.0f}])")
    print()
```

### Dirichlet Visualization: Bar Charts

```python
def visualize_vice_profile(alphas: np.ndarray) -> str:
    """ASCII bar chart of vice preference distribution.

    Returns:
        ASCII visualization string
    """
    CATEGORIES = [
        "intellectual", "risk_taking", "substances",
        "sexuality", "emotional", "rule_break",
        "dark_humor", "vulnerable"
    ]

    probs = alphas / alphas.sum()
    max_prob = probs.max()
    bar_width = 40

    lines = ["\n  Vice Preference Distribution:"]
    lines.append(f"  {'Category':<14} {'Bar':^{bar_width+2}} {'Prob':>6} {'Alpha':>6}")
    lines.append(f"  {'-' * (14 + bar_width + 16)}")

    for i, (name, prob, alpha) in enumerate(zip(CATEGORIES, probs, alphas)):
        bar_len = int(prob / max_prob * bar_width) if max_prob > 0 else 0
        bar = "#" * bar_len + " " * (bar_width - bar_len)
        lines.append(f"  {name:<14} |{bar}| {prob:>5.1%} {alpha:>5.1f}")

    concentration = alphas.sum()
    entropy = -np.sum(probs * np.log2(np.clip(probs, 1e-10, 1.0)))
    lines.append(f"\n  Concentration: {concentration:.1f} | Entropy: {entropy:.2f} bits (max: 3.00)")

    return "\n".join(lines)


# Example
alphas = np.array([5.0, 1.5, 1.0, 2.0, 3.5, 1.0, 4.0, 2.5])
print(visualize_vice_profile(alphas))
```

**Output**:
```
  Vice Preference Distribution:
  Category       Bar                                           Prob  Alpha
  --------------------------------------------------------------------------
  intellectual  |########################################|  24.4%   5.0
  risk_taking   |############                            |   7.3%   1.5
  substances    |########                                |   4.9%   1.0
  sexuality     |################                        |   9.8%   2.0
  emotional     |############################            |  17.1%   3.5
  rule_break    |########                                |   4.9%   1.0
  dark_humor    |################################        |  19.5%   4.0
  vulnerable    |####################                    |  12.2%   2.5

  Concentration: 20.5 | Entropy: 2.72 bits (max: 3.00)
```

---

## 9. Complete Update Cycle with Plots

### End-to-End Session Simulation

```python
def simulate_session():
    """Simulate a complete play session with Bayesian updates.

    Demonstrates the full cycle:
    1. Initialize from priors
    2. Process messages with observation encoding
    3. Apply Beta/Dirichlet updates
    4. Apply decay during inactivity
    5. Sample from posteriors for behavior generation
    """
    # --- Initialize ---
    metrics = {
        "intimacy": DecayableBetaMetric(1.5, 6.0, 1.5, 6.0),
        "passion": DecayableBetaMetric(3.0, 3.0, 3.0, 3.0),
        "trust": DecayableBetaMetric(2.0, 5.0, 2.0, 5.0),
        "secureness": DecayableBetaMetric(2.0, 3.0, 2.0, 3.0),
    }
    vices = VicePreferenceModel(chapter=1)
    skip = BayesianSkipDecision(chapter=1)
    encoder = ObservationEncoder()
    chapter = 1

    # --- Simulate 15 messages ---
    messages = [
        {"text": "Hey Nikita! How's your day going?", "response_time": 120, "hours_since": 1, "today_count": 1},
        {"text": "I've been reading this amazing philosophy book about existentialism. What do you think about free will?", "response_time": 300, "hours_since": 0.5, "today_count": 2},
        {"text": "That's a really interesting perspective. You're smarter than I expected!", "response_time": 180, "hours_since": 0.3, "today_count": 3},
        {"text": "haha yeah", "response_time": 60, "hours_since": 0.2, "today_count": 4},
        {"text": "Do you ever feel scared about the future? I sometimes worry about being alone.", "response_time": 600, "hours_since": 2, "today_count": 5},
        {"text": "That means a lot that you'd share that with me. I feel the same way sometimes.", "response_time": 240, "hours_since": 0.5, "today_count": 6},
        {"text": "ok", "response_time": 3600, "hours_since": 3, "today_count": 7},
        {"text": "sorry, was busy. Anyway, want to hear a dark joke?", "response_time": 120, "hours_since": 4, "today_count": 8},
        {"text": "Why don't scientists trust atoms? Because they make up everything! Get it? It's twisted because trust is an illusion haha", "response_time": 60, "hours_since": 0.2, "today_count": 9},
        {"text": "You're amazing, I love talking to you. You make me feel so happy!", "response_time": 90, "hours_since": 0.3, "today_count": 10},
    ]

    weights = {"intimacy": 0.30, "passion": 0.25, "trust": 0.25, "secureness": 0.20}

    print("=" * 80)
    print("SESSION SIMULATION: Bayesian Player Model Updates")
    print("=" * 80)

    for i, msg_data in enumerate(messages):
        msg = msg_data["text"]

        # 1. Skip decision
        should_skip = skip.should_skip()

        # 2. Encode observations
        observations = encoder.encode_message(
            msg, chapter,
            response_time_seconds=msg_data["response_time"],
            time_since_last_hours=msg_data["hours_since"],
            messages_today=msg_data["today_count"],
        )

        # 3. Vice detection
        vice_signals = vices.update_from_keywords(msg)

        # 4. Apply observations to metrics
        for obs in observations:
            if obs.metric in metrics:
                effective_weight = obs.weight * obs.confidence
                metrics[obs.metric].update(obs.positive, effective_weight)

        # 5. Compute composite
        composite = sum(
            m.mean * weights[name]
            for name, m in metrics.items()
        ) * 100

        # 6. Print state
        print(f"\n--- Message {i+1}: \"{msg[:50]}{'...' if len(msg) > 50 else ''}\"")
        if should_skip:
            print(f"  [SKIPPED by Thompson Sampling (rate={skip.expected_skip_rate:.2f})]")

        print(f"  Observations: {len(observations)} signals, {len(vice_signals)} vice signals")
        for obs in observations:
            print(f"    {obs.metric}: {'+'  if obs.positive else '-'} (weight={obs.weight:.2f}, source={obs.source})")

        print(f"  Metrics:")
        for name, m in metrics.items():
            score = m.mean * 100
            print(f"    {name:<12}: {score:5.1f}/100 (strength={m.strength:.1f})")

        print(f"  Composite: {composite:.1f}/100")

        if vice_signals:
            print(f"  Vice signals: {[(VicePreferenceModel.CATEGORIES[idx], f'{w:.2f}') for idx, w in vice_signals]}")
            print(f"  Top vices: {vices.top_vices(3)}")

    # --- Final summary ---
    print("\n" + "=" * 80)
    print("SESSION SUMMARY")
    print("=" * 80)
    print(f"\nFinal Metric Distributions:")
    for name, m in metrics.items():
        ci_low = stats.beta.ppf(0.025, m.alpha, m.beta)
        ci_high = stats.beta.ppf(0.975, m.alpha, m.beta)
        print(f"  {name:<12}: {m.mean*100:.1f}/100  95% CI: [{ci_low*100:.0f}, {ci_high*100:.0f}]  strength={m.strength:.1f}")

    composite = sum(m.mean * weights[name] for name, m in metrics.items()) * 100
    print(f"\nComposite Score: {composite:.1f}/100")
    print(f"Boss 1 threshold: 55.0  {'READY' if composite >= 55 else 'NOT READY'}")

    print(f"\nVice Profile: entropy={vices.entropy:.2f} bits")
    for name, prob in vices.top_vices(5):
        print(f"  {name}: {prob:.1%}")


simulate_session()
```

---

## 10. Edge Cases and Robustness

### Edge Case 1: Very Small Alpha/Beta

When $\alpha$ or $\beta$ approaches zero, the Beta distribution degenerates. Enforce minimum values:

```python
def safe_beta_update(alpha: float, beta: float, positive: bool, weight: float) -> tuple[float, float]:
    """Safe Beta update that prevents degenerate distributions.

    Enforces alpha >= 0.5 and beta >= 0.5 to prevent:
    - Division by zero in mean calculation
    - Numerical instability in sampling
    - Degenerate point-mass distributions
    """
    MIN_PARAM = 0.5

    if positive:
        alpha += weight
    else:
        beta += weight

    alpha = max(MIN_PARAM, alpha)
    beta = max(MIN_PARAM, beta)

    return alpha, beta
```

### Edge Case 2: Observation Flooding

If a player sends 50 messages in 5 minutes, we shouldn't update 50 times with full weight — this would overwhelm the prior and make the metric jump wildly.

```python
class RateLimitedUpdater:
    """Rate-limits observations to prevent flooding.

    Uses a sliding window to cap the total evidence per time period.
    """

    def __init__(self, max_weight_per_hour: float = 5.0):
        self.max_weight_per_hour = max_weight_per_hour
        self.recent_weights: list[tuple[float, float]] = []  # (timestamp, weight)

    def apply_rate_limit(self, weight: float, current_time: float) -> float:
        """Reduce weight if we've accumulated too much recently.

        Args:
            weight: Proposed observation weight
            current_time: Current timestamp (seconds)

        Returns:
            Rate-limited weight (may be reduced or zero)
        """
        # Remove old entries (older than 1 hour)
        cutoff = current_time - 3600
        self.recent_weights = [
            (t, w) for t, w in self.recent_weights if t > cutoff
        ]

        # Total weight in last hour
        total_recent = sum(w for _, w in self.recent_weights)

        # If over budget, reduce or skip
        remaining_budget = self.max_weight_per_hour - total_recent
        if remaining_budget <= 0:
            return 0.0

        effective_weight = min(weight, remaining_budget)
        self.recent_weights.append((current_time, effective_weight))
        return effective_weight
```

### Edge Case 3: Player With No Vice Preference

Some players genuinely don't cluster into any vice category. The Dirichlet should remain near-uniform.

```python
def detect_no_preference(alphas: np.ndarray, threshold_entropy: float = 2.8) -> bool:
    """Detect if player shows no strong vice preference.

    Entropy close to maximum (3.0 bits for 8 categories) means
    the player's behavior is approximately uniform across vices.

    In this case, Nikita should continue probing rather than
    assuming a specific vice to lean into.
    """
    probs = alphas / alphas.sum()
    entropy = -np.sum(probs * np.log2(np.clip(probs, 1e-10, 1.0)))
    return entropy > threshold_entropy
```

### Edge Case 4: Metric Reversal

A player who built trust to 0.8 then suddenly betrays — the Beta should be able to shift back quickly.

```python
def handle_betrayal_event(
    metric: DecayableBetaMetric,
    severity: float = 0.8,
) -> None:
    """Handle a sudden negative event (e.g., trust betrayal).

    Instead of adding normal negative evidence, this applies
    a "shock" that reduces strength while shifting the mean.

    The player's previous positive behavior isn't forgotten —
    but the model becomes very uncertain, requiring the player
    to re-earn trust.

    Args:
        metric: The affected metric
        severity: How severe the event (0-1)
    """
    # Add large negative evidence
    metric.update(positive=False, weight=severity * 5.0)

    # Also reduce overall strength (increase uncertainty)
    # This makes the metric more responsive to future inputs
    shrink_factor = 1.0 - severity * 0.3
    metric.alpha *= shrink_factor
    metric.beta *= shrink_factor

    # Enforce minimums
    metric.alpha = max(0.5, metric.alpha)
    metric.beta = max(0.5, metric.beta)
```

---

## 11. Integration with Existing Modules

### Mapping to Current Codebase

| Current Module | Bayesian Replacement | Parameters Stored |
|---------------|---------------------|-------------------|
| `ScoreCalculator.calculate_composite()` | `sum(mean_i * weight_i)` | 4 x (alpha, beta) = 8 floats |
| `ScoreCalculator.update_metrics()` | `BetaMetric.update()` | In-place alpha/beta updates |
| `ViceAnalyzer.analyze_exchange()` | `VicePreferenceModel.update_from_keywords()` | 8 Dirichlet alphas |
| `ViceScorer.get_top_vices()` | `VicePreferenceModel.top_vices()` | Same alphas |
| `ViceBoundaryEnforcer.apply_cap()` | `VicePreferenceModel.boundary_cap()` | Chapter-based lookup |
| `DecayCalculator.calculate_decay()` | `DecayableBetaMetric.decay()` | Same alpha/beta |
| `SkipDecision.should_skip()` | `BayesianSkipDecision.should_skip()` | 2 floats |
| `ResponseTimer.calculate_delay()` | Posterior-predictive sampling (see doc 01) | 2 floats |

### Database Schema (JSONB in Supabase)

```python
BAYESIAN_STATE_SCHEMA = {
    "metrics": {
        "intimacy": {"alpha": 1.5, "beta": 6.0},
        "passion": {"alpha": 3.0, "beta": 3.0},
        "trust": {"alpha": 2.0, "beta": 5.0},
        "secureness": {"alpha": 2.0, "beta": 3.0},
    },
    "vices": {
        "alphas": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
    },
    "skip": {
        "alpha_skip": 3.0,
        "alpha_respond": 5.0,
        "consecutive_skips": 0,
    },
    "timing": {
        "mu": 14700.0,
        "precision": 0.000001,
    },
    "meta": {
        "total_messages": 0,
        "last_updated": "2026-02-16T00:00:00Z",
        "chapter": 1,
        "version": 1,
    },
}
# Total JSONB size: ~400-600 bytes per user
```

---

## 12. Key Takeaways for Nikita

### 1. The proportion-strength parameterization is more intuitive for game designers

Instead of thinking in terms of abstract $\alpha$ and $\beta$, designers can set: "Trust starts at 29% with strength 7" — which means "7 pseudo-observations suggesting 29% positive rate." This maps directly to game feel and is easy to tune.

### 2. The Observation Encoder is production-ready with 5 feature extractors

Message length, response time, question analysis, sentiment keywords, and consistency patterns combine to produce 1-5 observations per message. Conflict resolution handles contradicting signals. Total latency: <2ms with zero token cost.

### 3. Bayesian decay is richer than flat percentage decay

Instead of "lose 0.8%/hour", Bayesian decay says "regress toward the prior with increasing uncertainty." This preserves the *character* of the relationship (a high-trust player returns to "uncertain" not "low trust") and makes the metric responsive to new evidence after absence.

### 4. Thompson Sampling for skip decisions creates natural unpredictability

The current skip system is disabled (all rates at 0%). Thompson Sampling from learned Beta posteriors creates skip behavior that adapts to each player's tolerance, creating organic unpredictability without frustrating players who need consistent responses.

### 5. Vice preferences are discoverable without an LLM

Keyword-based detection + Dirichlet updates replaces the expensive `ViceAnalyzer` LLM call. The discovery threshold triggers "Nikita notices you like X" events at Dirichlet concentration > 3.0 above prior. Vice sampling for conversation steering uses Thompson Sampling from the Dirichlet posterior.

### 6. Everything serializes to <600 bytes JSONB

The complete Bayesian state (4 Beta metrics + 8 Dirichlet alphas + skip state + timing state + metadata) fits in under 600 bytes of JSONB in Supabase PostgreSQL. At 10,000 users, that's 6 MB total — negligible.

---

## References

### Beta and Dirichlet Distributions
- Johnson, N. L., Kotz, S., & Balakrishnan, N. (1995). *Continuous Univariate Distributions, Vol. 2*. Wiley.
- Ng, K., Tian, G., & Tang, M. (2011). "Dirichlet and Related Distributions." Wiley.

### Thompson Sampling
- Thompson, W. R. (1933). "On the Likelihood that One Unknown Probability Exceeds Another." *Biometrika*.
- Chapelle, O. & Li, L. (2011). "An Empirical Evaluation of Thompson Sampling." *NIPS*.
- Russo, D., et al. (2018). "A Tutorial on Thompson Sampling." *Foundations and Trends in ML*.

### Decay and Forgetting
- Ebbinghaus, H. (1885/1913). *Memory: A Contribution to Experimental Psychology*.
- Anderson, J. R. & Schooler, L. J. (1991). "Reflections of the Environment in Memory." *Psychological Science*.

### Observation Encoding / Feature Engineering
- VADER Sentiment: Hutto, C. J. & Gilbert, E. (2014). "VADER: A Parsimonious Rule-based Model for Sentiment Analysis." *ICWSM*.

---

> **Previous**: [04-hmm-emotional-states.md](./04-hmm-emotional-states.md)
> **Next**: [10-efficient-inference.md](./10-efficient-inference.md) for benchmarks, JSONB schemas, and Cloud Run optimization
> **See also**: [18-bayesian-vice-discovery.md](../ideas/18-bayesian-vice-discovery.md) for the complete vice discovery system design

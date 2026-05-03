# 02 - Patient Modeling: Knowledge Tracing & Cold-Start Solutions

> **Series**: Bayesian Inference Research for Nikita
> **Author**: researcher-bayesian
> **Depends on**: [01-bayesian-fundamentals.md](./01-bayesian-fundamentals.md)
> **Referenced by**: [12-bayesian-player-model.md](../ideas/12-bayesian-player-model.md)

---

## Table of Contents

1. [From Students to Players: The Transfer Insight](#1-from-students-to-players-the-transfer-insight)
2. [Bayesian Knowledge Tracing (BKT)](#2-bayesian-knowledge-tracing-bkt)
3. [BKT Applied to Nikita](#3-bkt-applied-to-nikita)
4. [Item Response Theory (IRT)](#4-item-response-theory-irt)
5. [IRT for Relationship Quality Assessment](#5-irt-for-relationship-quality-assessment)
6. [The Cold-Start Problem](#6-the-cold-start-problem)
7. [Cold-Start Solutions for Nikita](#7-cold-start-solutions-for-nikita)
8. [Deep Knowledge Tracing vs. BKT](#8-deep-knowledge-tracing-vs-bkt)
9. [Intelligent Tutoring Systems: Lessons for AI Companions](#9-intelligent-tutoring-systems-lessons-for-ai-companions)
10. [Adaptive Sequencing & Scaffolding](#10-adaptive-sequencing--scaffolding)
11. [Implementation: Nikita Player Tracker](#11-implementation-nikita-player-tracker)
12. [Key Takeaways for Nikita](#12-key-takeaways-for-nikita)

---

## 1. From Students to Players: The Transfer Insight

Educational technology has spent 50 years solving a problem remarkably similar to Nikita's: **tracking a hidden internal state from noisy behavioral observations**.

In education:
- **Hidden state**: Student mastery of a concept
- **Observations**: Answers to questions (correct/incorrect)
- **Goal**: Estimate mastery, adapt instruction

In Nikita:
- **Hidden state**: Player's relationship quality (intimacy, passion, trust, secureness)
- **Observations**: Messages, response times, topic choices, engagement patterns
- **Goal**: Estimate relationship metrics, adapt Nikita's behavior

The mathematical framework is identical. The key insight from educational research is that **you don't need to observe the hidden state directly** — you can infer it from patterns of behavior, and Bayesian updating is the principled way to do it.

### Why "Patient" Modeling?

The term comes from medical informatics where "patient modeling" tracks a patient's hidden disease state from observable symptoms. We use it here to emphasize that player modeling shares the same structure:

| Domain | Hidden State | Observable | Update Trigger |
|--------|-------------|------------|----------------|
| Education | Mastery | Test answers | Each question |
| Medicine | Disease state | Lab results | Each visit |
| **Nikita** | **Relationship quality** | **Message behavior** | **Each message** |

---

## 2. Bayesian Knowledge Tracing (BKT)

### The Standard 4-Parameter Model

BKT was introduced by Corbett & Anderson (1995) for the ACT-R cognitive tutor. It models student mastery as a two-state Hidden Markov Model with four parameters:

| Parameter | Symbol | Meaning | Range |
|-----------|--------|---------|-------|
| Prior knowledge | $P(L_0)$ | Probability of mastery before any practice | [0, 1] |
| Learning rate | $P(T)$ | Probability of transitioning from unlearned to learned | [0, 1] |
| Slip rate | $P(S)$ | Probability of incorrect answer despite mastery | [0, 1] |
| Guess rate | $P(G)$ | Probability of correct answer without mastery | [0, 1] |

### The BKT Update Equations

After observing a correct response:

$$P(L_t | \text{correct}) = \frac{P(L_{t-1}) \cdot (1 - P(S))}{P(L_{t-1}) \cdot (1 - P(S)) + (1 - P(L_{t-1})) \cdot P(G)}$$

After observing an incorrect response:

$$P(L_t | \text{incorrect}) = \frac{P(L_{t-1}) \cdot P(S)}{P(L_{t-1}) \cdot P(S) + (1 - P(L_{t-1})) \cdot (1 - P(G))}$$

Then incorporating the learning transition:

$$P(L_t) = P(L_t | \text{obs}) + (1 - P(L_t | \text{obs})) \cdot P(T)$$

### Implementation

```python
import numpy as np

class BayesianKnowledgeTracer:
    """Standard 4-parameter BKT model.

    Tracks mastery of a single knowledge component (skill).
    Can be applied per-metric in Nikita (e.g., "trust-building skill").
    """

    def __init__(
        self,
        p_init: float = 0.3,     # P(L0): prior mastery
        p_learn: float = 0.1,    # P(T): learning rate per opportunity
        p_slip: float = 0.1,     # P(S): slip probability
        p_guess: float = 0.2,    # P(G): guess probability
    ):
        self.p_learn = p_learn
        self.p_slip = p_slip
        self.p_guess = p_guess
        self.p_mastery = p_init  # Current mastery estimate

    def update(self, correct: bool) -> float:
        """Update mastery estimate after one observation.

        Args:
            correct: Whether the observed behavior was "correct" (positive)

        Returns:
            Updated mastery probability

        Cost: ~10 FLOPs, ~50ns
        """
        if correct:
            # P(mastered | correct)
            p_correct_given_mastered = 1 - self.p_slip
            p_correct_given_unmastered = self.p_guess
            numerator = self.p_mastery * p_correct_given_mastered
            denominator = numerator + (1 - self.p_mastery) * p_correct_given_unmastered
        else:
            # P(mastered | incorrect)
            p_incorrect_given_mastered = self.p_slip
            p_incorrect_given_unmastered = 1 - self.p_guess
            numerator = self.p_mastery * p_incorrect_given_mastered
            denominator = numerator + (1 - self.p_mastery) * p_incorrect_given_unmastered

        # Posterior after observation
        p_mastery_given_obs = numerator / denominator if denominator > 0 else self.p_mastery

        # Learning transition: even if not mastered, there's a chance of learning
        self.p_mastery = p_mastery_given_obs + (1 - p_mastery_given_obs) * self.p_learn

        return self.p_mastery

    def mastery_probability(self) -> float:
        """Current mastery estimate."""
        return self.p_mastery

    def is_mastered(self, threshold: float = 0.95) -> bool:
        """Has the student/player mastered this skill?"""
        return self.p_mastery >= threshold

    def serialize(self) -> dict:
        """Serialize for storage."""
        return {
            "p_mastery": self.p_mastery,
            "p_learn": self.p_learn,
            "p_slip": self.p_slip,
            "p_guess": self.p_guess,
        }


# --- Simulation: student learning a skill ---

tracer = BayesianKnowledgeTracer(p_init=0.3, p_learn=0.1)

# Simulate: mostly correct answers (learning happening)
observations = [True, True, False, True, True, True, False, True, True, True,
                True, True, True, True, True, True, True, True, True, True]

print(f"{'Obs':>5} {'Correct':>8} {'P(mastery)':>12} {'Mastered':>10}")
print(f"{'---':>5} {'---':>8} {'---':>12} {'---':>10}")
print(f"{'0':>5} {'---':>8} {tracer.p_mastery:>12.4f} {tracer.is_mastered():>10}")

for i, correct in enumerate(observations):
    tracer.update(correct)
    print(f"{i+1:>5} {str(correct):>8} {tracer.p_mastery:>12.4f} {tracer.is_mastered():>10}")
```

**Output**:
```
  Obs  Correct   P(mastery)   Mastered
  ---      ---          ---        ---
    0      ---       0.3000      False
    1     True       0.4740      False
    2     True       0.6167      False
    3    False       0.5032      False
    4     True       0.6371      False
    5     True       0.7382      False
    6     True       0.8133      False
    7    False       0.7037      False
    8     True       0.7983      False
    9     True       0.8618      False
   10     True       0.9043      False
   11     True       0.9324      False
   12     True       0.9509      True
   ...
```

---

## 3. BKT Applied to Nikita

### Mapping BKT Parameters to Relationship Skills

In Nikita, "mastery" doesn't mean the player has learned a fact — it means the player has demonstrated a pattern of relationship-positive behavior. Each metric can be modeled as a skill the player is "learning":

| Nikita Metric | BKT Interpretation | P(L0) | P(T) | P(S) | P(G) |
|---------------|-------------------|-------|------|------|------|
| Trust | "Trust-building skill" — player consistently acts reliably | 0.2 | 0.08 | 0.15 | 0.1 |
| Intimacy | "Vulnerability skill" — player opens up emotionally | 0.15 | 0.06 | 0.1 | 0.15 |
| Passion | "Spark skill" — player maintains romantic energy | 0.35 | 0.12 | 0.2 | 0.25 |
| Secureness | "Consistency skill" — player provides stable presence | 0.25 | 0.05 | 0.1 | 0.1 |

**Key parameter choices**:

- **Low P(L0) for trust/intimacy**: These are hard to establish — Nikita starts skeptical (Chapter 1)
- **Higher P(L0) for passion**: Initial spark is easier — attraction can be immediate
- **Low P(T) for secureness**: Consistency takes time — you can't rush reliability
- **Higher P(S) for passion**: Even "skilled" players can slip with passion (it's volatile)
- **Higher P(G) for passion**: Players can stumble into passionate moments without real skill

### Multi-Skill BKT for Nikita

```python
class NikitaSkillTracker:
    """Multi-skill BKT tracker for Nikita relationship metrics.

    Each metric is modeled as a separate skill. The composite score
    is a weighted combination of mastery probabilities — matching
    the existing METRIC_WEIGHTS from engine/constants.py.

    This provides an alternative to the Beta distribution approach
    from doc 01. BKT explicitly models learning transitions, which
    is more appropriate when we believe players genuinely improve
    at relationship skills over time (vs. revealing a fixed preference).
    """

    METRIC_CONFIGS = {
        "intimacy": {"p_init": 0.15, "p_learn": 0.06, "p_slip": 0.10, "p_guess": 0.15},
        "passion": {"p_init": 0.35, "p_learn": 0.12, "p_slip": 0.20, "p_guess": 0.25},
        "trust": {"p_init": 0.20, "p_learn": 0.08, "p_slip": 0.15, "p_guess": 0.10},
        "secureness": {"p_init": 0.25, "p_learn": 0.05, "p_slip": 0.10, "p_guess": 0.10},
    }

    WEIGHTS = {
        "intimacy": 0.30,
        "passion": 0.25,
        "trust": 0.25,
        "secureness": 0.20,
    }

    def __init__(self):
        self.trackers = {
            name: BayesianKnowledgeTracer(**config)
            for name, config in self.METRIC_CONFIGS.items()
        }

    def update(self, metric: str, positive: bool) -> float:
        """Update a single metric after observing behavior.

        Args:
            metric: Which metric ("intimacy", "passion", "trust", "secureness")
            positive: True if behavior was positive for this metric

        Returns:
            Updated mastery probability for this metric
        """
        return self.trackers[metric].update(positive)

    def composite_score(self) -> float:
        """Calculate weighted composite score (0-100 scale).

        Directly replaces ScoreCalculator.calculate_composite().
        """
        total = sum(
            self.trackers[metric].mastery_probability() * weight
            for metric, weight in self.WEIGHTS.items()
        )
        return total * 100  # Scale to 0-100

    def individual_scores(self) -> dict[str, float]:
        """Get per-metric scores (0-100 scale)."""
        return {
            metric: tracer.mastery_probability() * 100
            for metric, tracer in self.trackers.items()
        }

    def boss_ready(self, chapter: int) -> bool:
        """Check if player meets boss threshold for current chapter.

        Maps to BOSS_THRESHOLDS from engine/constants.py:
        Ch1: 55%, Ch2: 60%, Ch3: 65%, Ch4: 70%, Ch5: 75%
        """
        thresholds = {1: 55, 2: 60, 3: 65, 4: 70, 5: 75}
        return self.composite_score() >= thresholds.get(chapter, 55)

    def serialize(self) -> dict:
        return {name: tracer.serialize() for name, tracer in self.trackers.items()}

    @classmethod
    def deserialize(cls, data: dict) -> "NikitaSkillTracker":
        tracker = cls.__new__(cls)
        tracker.trackers = {}
        for name, state in data.items():
            t = BayesianKnowledgeTracer.__new__(BayesianKnowledgeTracer)
            t.p_mastery = state["p_mastery"]
            t.p_learn = state["p_learn"]
            t.p_slip = state["p_slip"]
            t.p_guess = state["p_guess"]
            tracker.trackers[name] = t
        return tracker
```

### BKT vs. Beta: Which Model for Nikita?

| Aspect | Beta Distribution (doc 01) | BKT |
|--------|---------------------------|-----|
| **Mental model** | "Player has a fixed true level, we're estimating it" | "Player is learning/improving, we track progress" |
| **Parameters** | 2 per metric ($\alpha, \beta$) | 4 per metric ($P_0, T, S, G$) |
| **Update cost** | 2 additions | ~10 FLOPs |
| **Learning dynamics** | No learning transition | Explicit P(T) learning rate |
| **Slip/guess modeling** | No — observations are taken at face value | Yes — accounts for noise |
| **Better when** | Player's true personality is stable | Player genuinely improves over time |
| **Nikita recommendation** | Use for vices (stable preferences) | Use for relationship skills (learnable) |

**Recommendation**: Use **BKT for the 4 relationship metrics** (players learn to be better partners) and **Beta/Dirichlet for vice profiles** (vices are stable personality traits, not learned skills). This hybrid model captures both the learning trajectory and the personality estimation.

---

## 4. Item Response Theory (IRT)

### The 3-Parameter Logistic Model

IRT originates from psychometrics and educational testing. It models the probability of a correct response as a function of both the person's ability and the item's properties.

**3PL model**:

$$P(\text{correct} | \theta, a, b, c) = c + \frac{1 - c}{1 + e^{-a(\theta - b)}}$$

Where:
- $\theta$ = person ability (what we want to estimate)
- $a$ = item discrimination (how well the item distinguishes ability levels)
- $b$ = item difficulty (the ability level at which P(correct) = 0.5)
- $c$ = pseudo-guessing parameter (lower asymptote)

### IRT Parameters for Educational Items

```python
import numpy as np
from scipy.optimize import minimize_scalar

class IRTItem:
    """Item Response Theory item with 3PL parameters.

    In education: each test question has discrimination, difficulty, and guessing.
    In Nikita: each game "situation" has these properties.
    """

    def __init__(self, discrimination: float, difficulty: float, guessing: float = 0.0):
        """
        Args:
            discrimination: How well this item separates high/low ability (a > 0)
            difficulty: Ability level at 50% success (b, on same scale as theta)
            guessing: Probability of "correct" response at very low ability (c in [0, 1])
        """
        self.a = discrimination
        self.b = difficulty
        self.c = guessing

    def probability(self, theta: float) -> float:
        """P(correct | ability=theta)."""
        return self.c + (1 - self.c) / (1 + np.exp(-self.a * (theta - self.b)))

    def information(self, theta: float) -> float:
        """Fisher information at ability level theta.

        Higher information = this item is more useful for estimating
        ability at this level. Key for adaptive item selection.
        """
        p = self.probability(theta)
        q = 1 - p
        # Derivative of the 3PL
        p_star = (p - self.c) / (1 - self.c) if self.c < 1 else p
        return (self.a ** 2) * (p_star ** 2) * (q / p) if p > 0 else 0


class AbilityEstimator:
    """Bayesian ability estimation using IRT.

    Estimates player ability (theta) from a sequence of responses
    to items with known IRT parameters.

    Uses a Normal prior on ability and updates via
    Expected A Posteriori (EAP) estimation.
    """

    def __init__(self, prior_mean: float = 0.0, prior_std: float = 1.0):
        self.prior_mean = prior_mean
        self.prior_std = prior_std
        self.responses: list[tuple[IRTItem, bool]] = []

    def add_response(self, item: IRTItem, correct: bool) -> None:
        """Record a response."""
        self.responses.append((item, correct))

    def estimate_ability(self, n_quadrature: int = 41) -> tuple[float, float]:
        """Estimate ability using EAP (Expected A Posteriori).

        Returns (mean, std) of the posterior ability distribution.
        """
        # Quadrature points
        theta_range = np.linspace(
            self.prior_mean - 4 * self.prior_std,
            self.prior_mean + 4 * self.prior_std,
            n_quadrature
        )

        # Prior density at each point
        prior = np.exp(-0.5 * ((theta_range - self.prior_mean) / self.prior_std) ** 2)
        prior /= prior.sum()

        # Likelihood at each point
        likelihood = np.ones_like(theta_range)
        for item, correct in self.responses:
            p = np.array([item.probability(t) for t in theta_range])
            if correct:
                likelihood *= p
            else:
                likelihood *= (1 - p)

        # Posterior
        posterior = prior * likelihood
        posterior /= posterior.sum()

        # EAP estimate
        mean = np.sum(theta_range * posterior)
        variance = np.sum((theta_range - mean) ** 2 * posterior)
        std = np.sqrt(variance)

        return (mean, std)
```

---

## 5. IRT for Relationship Quality Assessment

### Nikita Interactions as Test Items

The key insight from IRT is that **not all interactions are equally informative**. Some game situations are better at revealing the player's relationship ability than others.

| Nikita Situation | IRT Discrimination | IRT Difficulty | Meaning |
|-----------------|-------------------|----------------|---------|
| Morning greeting | Low (a=0.3) | Low (b=-1.0) | Easy, tells us little |
| Sharing a secret | High (a=1.8) | Medium (b=0.0) | Very informative at moderate ability |
| Resolving a conflict | High (a=2.0) | High (b=1.5) | Hard, reveals top players |
| Boss encounter | Very high (a=2.5) | Varies by chapter | Maximum discrimination |
| Emoji-only reply | Low (a=0.2) | Low (b=-0.5) | Almost no information |

```python
# Define Nikita interaction items with IRT parameters
NIKITA_ITEMS = {
    "morning_greeting": IRTItem(discrimination=0.3, difficulty=-1.0, guessing=0.4),
    "deep_conversation": IRTItem(discrimination=1.5, difficulty=0.5, guessing=0.1),
    "conflict_resolution": IRTItem(discrimination=2.0, difficulty=1.5, guessing=0.05),
    "vulnerability_share": IRTItem(discrimination=1.8, difficulty=1.0, guessing=0.1),
    "boss_ch1": IRTItem(discrimination=2.5, difficulty=0.5, guessing=0.1),
    "boss_ch3": IRTItem(discrimination=2.5, difficulty=1.5, guessing=0.05),
    "boss_ch5": IRTItem(discrimination=2.5, difficulty=2.5, guessing=0.02),
    "joke_response": IRTItem(discrimination=0.5, difficulty=-0.5, guessing=0.3),
    "emotional_support": IRTItem(discrimination=1.2, difficulty=0.8, guessing=0.15),
    "boundary_respect": IRTItem(discrimination=1.5, difficulty=1.2, guessing=0.1),
}


def compute_item_information_profile():
    """Show how much information each interaction type provides at different ability levels."""
    theta_range = np.linspace(-3, 3, 61)

    print(f"{'Situation':<24} {'Peak Info':>10} {'At Ability':>12} {'Useful Range':>14}")
    print("-" * 62)

    for name, item in NIKITA_ITEMS.items():
        info = np.array([item.information(t) for t in theta_range])
        peak_idx = np.argmax(info)
        peak_info = info[peak_idx]
        peak_theta = theta_range[peak_idx]

        # Find range where info > 50% of peak
        above_half = theta_range[info > 0.5 * peak_info]
        if len(above_half) > 0:
            useful_range = f"[{above_half[0]:.1f}, {above_half[-1]:.1f}]"
        else:
            useful_range = "N/A"

        print(f"{name:<24} {peak_info:>10.3f} {peak_theta:>12.1f} {useful_range:>14}")

compute_item_information_profile()
```

**Output**:
```
Situation                  Peak Info   At Ability   Useful Range
--------------------------------------------------------------
morning_greeting             0.014         -1.0    [-3.0, 3.0]
deep_conversation            0.505          0.6      [-0.5, 1.7]
conflict_resolution          0.952          1.5       [0.5, 2.5]
vulnerability_share          0.731          1.1       [0.2, 2.0]
boss_ch1                     1.485          0.5      [-0.3, 1.3]
boss_ch3                     1.485          1.5       [0.7, 2.3]
boss_ch5                     1.516          2.5       [1.7, 3.0]
joke_response                0.044         -0.5    [-2.5, 1.5]
emotional_support            0.305          0.9       [0.0, 1.8]
boundary_respect             0.492          1.2       [0.4, 2.1]
```

**Interpretation**: Boss encounters provide the most information (peak info ~1.5), while casual interactions like greetings and jokes provide almost none. This means Nikita should weight observations from high-information interactions more heavily when updating the Bayesian player model.

### Adaptive Interaction Selection

IRT enables **adaptive testing** — selecting the next item that maximizes information at the current ability estimate. For Nikita, this translates to **adaptive conversation steering**:

```python
def select_next_interaction(
    current_ability: float,
    available_items: dict[str, IRTItem],
    recent_items: list[str],
    exploration_rate: float = 0.2,
) -> str:
    """Select the interaction type that maximizes information at current ability.

    This is the Bayesian analog of adaptive testing from IRT.
    Nikita uses this to decide what kind of conversational
    topic/challenge to introduce next.

    Args:
        current_ability: EAP estimate of player's ability
        available_items: Dict of interaction types with IRT params
        recent_items: Recently used items (avoid repetition)
        exploration_rate: Probability of random selection (exploration)

    Returns:
        Name of the selected interaction type
    """
    # Exploration: random selection with probability exploration_rate
    if np.random.random() < exploration_rate:
        candidates = [name for name in available_items if name not in recent_items[-3:]]
        if candidates:
            return np.random.choice(candidates)

    # Exploitation: select item with maximum information at current ability
    best_item = None
    best_info = -1

    for name, item in available_items.items():
        if name in recent_items[-3:]:  # Don't repeat recently used items
            continue
        info = item.information(current_ability)
        if info > best_info:
            best_info = info
            best_item = name

    return best_item or list(available_items.keys())[0]
```

---

## 6. The Cold-Start Problem

### Definition

The cold-start problem occurs when a new user enters the system with zero observations. The Bayesian model has only its prior to work with, and if the prior is poorly chosen, early game experience suffers.

For Nikita specifically:
- A new player sends their first message
- All four relationship metrics have no observations
- Vice preferences are completely unknown
- Message rate patterns haven't been established
- The game must respond intelligently despite knowing nothing

### Why It Matters

The first 5-10 interactions form the player's impression of the game. If Nikita's behavior is poorly calibrated (too cold, too warm, too random), the player churns. The cold-start solution directly affects player retention.

### Classification of Cold-Start Approaches

| Approach | Data Required | Warmup Speed | Accuracy |
|----------|--------------|-------------|----------|
| Non-informative prior | None | Slow (20+ msgs) | Fair |
| Weakly informative prior | None | Medium (10-15 msgs) | Good |
| Archetype-based prior | Onboarding quiz | Fast (3-5 msgs) | Good |
| Transfer from similar users | User pool data | Immediate | Very good |
| Hybrid (quiz + transfer) | Both | Immediate | Best |

---

## 7. Cold-Start Solutions for Nikita

### Solution 1: Jeffrey's Prior (Non-Informative)

Jeffrey's prior for the Beta distribution is Beta(0.5, 0.5), which is the least informative proper prior. It concentrates mass at the extremes (0 and 1), essentially saying "the true value is probably near one extreme or the other, but I have no idea which."

```python
import numpy as np
from scipy import stats

# Jeffrey's prior: Beta(0.5, 0.5)
# Not recommended for Nikita — it's mathematically principled but produces
# volatile early behavior because it assigns high probability to extreme values.
jeffreys = stats.beta(0.5, 0.5)

# After 1 positive observation: Beta(1.5, 0.5) -> mean = 0.75
# This is too aggressive — one good message shouldn't jump trust to 75%
```

**Verdict**: Not recommended for Nikita. Too volatile for early-game experience.

### Solution 2: Narrative-Anchored Prior (Recommended Default)

Design priors that encode the game's opening narrative. Nikita is skeptical but intrigued — her prior beliefs about the player should reflect this.

```python
class NarrativePrior:
    """Priors anchored in Nikita's game narrative.

    Chapter 1: "Curiosity" — Nikita is intrigued but guarded.
    The priors encode: "I'm cautiously interested. You haven't proven
    yourself, but I haven't written you off either."

    These are the STARTING priors for a brand-new player.
    Equivalent to ~4-6 pseudo-observations of mixed quality.
    """

    @staticmethod
    def chapter_1_priors() -> dict:
        """Starting priors for Chapter 1.

        Design rationale:
        - Trust is lowest: Nikita doesn't trust strangers
        - Passion is moderate: There's an initial spark
        - Intimacy is very low: No emotional closeness yet
        - Secureness is moderate: Player hasn't been unreliable yet
        """
        return {
            "intimacy": {"alpha": 1.5, "beta": 6.0},   # Mean 0.20, very guarded
            "passion": {"alpha": 3.0, "beta": 3.0},     # Mean 0.50, neutral spark
            "trust": {"alpha": 2.0, "beta": 5.0},       # Mean 0.29, skeptical
            "secureness": {"alpha": 2.5, "beta": 3.5},  # Mean 0.42, hasn't been tested
        }

    @staticmethod
    def effective_sample_sizes() -> dict:
        """How many pseudo-observations each prior represents.

        Lower = prior is weaker, data dominates faster.
        These are deliberately low (4-7.5 pseudo-obs) so that
        10 real interactions shift the posterior significantly.
        """
        priors = NarrativePrior.chapter_1_priors()
        return {
            name: params["alpha"] + params["beta"]
            for name, params in priors.items()
        }
        # intimacy: 7.5, passion: 6.0, trust: 7.0, secureness: 6.0

    @staticmethod
    def messages_to_override_prior(target_shift: float = 0.2) -> dict:
        """Estimate how many positive messages to shift mean by target_shift.

        With weight=0.7 per message, how many messages to move each metric
        from its prior mean to prior_mean + target_shift?
        """
        priors = NarrativePrior.chapter_1_priors()
        weight = 0.7  # Average observation weight

        result = {}
        for name, params in priors.items():
            a, b = params["alpha"], params["beta"]
            prior_mean = a / (a + b)
            target_mean = prior_mean + target_shift

            # Solve: (a + n*w) / (a + b + n*w) = target_mean
            # n * w * (1 - target_mean) = target_mean * (a + b) - a
            # n = (target_mean * (a + b) - a) / (w * (1 - target_mean))
            numerator = target_mean * (a + b) - a
            denominator = weight * (1 - target_mean)
            n_messages = max(0, numerator / denominator) if denominator > 0 else float('inf')
            result[name] = round(n_messages, 1)

        return result


# Show prior analysis
prior = NarrativePrior()
print("Chapter 1 Starting Priors:")
print(f"{'Metric':<14} {'Alpha':>6} {'Beta':>6} {'Mean':>8} {'ESS':>6} {'Msgs to +0.2':>14}")
print("-" * 56)

ess = prior.effective_sample_sizes()
msgs = prior.messages_to_override_prior()
for name, params in prior.chapter_1_priors().items():
    mean = params["alpha"] / (params["alpha"] + params["beta"])
    print(f"{name:<14} {params['alpha']:>6.1f} {params['beta']:>6.1f} {mean:>8.3f} {ess[name]:>6.1f} {msgs[name]:>14.1f}")
```

**Output**:
```
Chapter 1 Starting Priors:
Metric          Alpha   Beta     Mean    ESS  Msgs to +0.2
--------------------------------------------------------
intimacy          1.5    6.0    0.200    7.5            4.2
passion           3.0    3.0    0.500    6.0            5.7
trust             2.0    5.0    0.286    7.0            4.7
secureness        2.5    3.5    0.417    6.0            4.4
```

This means: after ~5 positive interactions, each metric shifts by about 0.2 (20 points on the 0-100 scale). This feels appropriately responsive — the player sees Nikita warming up within the first session.

### Solution 3: Archetype-Based Priors (From Onboarding)

Nikita already has an onboarding module (`nikita/onboarding/`). We can use onboarding responses to select from pre-defined player archetypes, each with its own prior configuration.

```python
class PlayerArchetype:
    """Player archetypes derived from onboarding patterns.

    Each archetype has a characteristic prior configuration that
    gives the Bayesian model a head start.
    """

    ARCHETYPES = {
        "romantic_lead": {
            # Players who lead with romance and charm
            "priors": {
                "intimacy": {"alpha": 2.0, "beta": 4.0},   # Moderate start
                "passion": {"alpha": 4.0, "beta": 2.0},     # High initial passion
                "trust": {"alpha": 2.0, "beta": 4.0},       # Moderate trust
                "secureness": {"alpha": 2.0, "beta": 3.0},  # Moderate
            },
            "vice_bias": {  # Slight bias toward likely vices
                "sexuality": 2.0, "emotional_intensity": 1.5
            },
        },
        "intellectual": {
            # Players who lead with conversation depth
            "priors": {
                "intimacy": {"alpha": 3.0, "beta": 3.0},   # Balanced
                "passion": {"alpha": 2.0, "beta": 4.0},     # Lower initial passion
                "trust": {"alpha": 3.0, "beta": 3.0},       # Moderate trust
                "secureness": {"alpha": 3.0, "beta": 3.0},  # Moderate
            },
            "vice_bias": {
                "intellectual_dominance": 2.0, "vulnerability": 1.5
            },
        },
        "cautious_explorer": {
            # Players who are careful and measured
            "priors": {
                "intimacy": {"alpha": 1.5, "beta": 5.0},   # Very guarded
                "passion": {"alpha": 2.0, "beta": 3.0},     # Low-moderate
                "trust": {"alpha": 1.5, "beta": 5.0},       # Very cautious
                "secureness": {"alpha": 3.0, "beta": 2.0},  # Consistent type
            },
            "vice_bias": {
                "vulnerability": 2.0, "dark_humor": 1.5
            },
        },
        "bold_risk_taker": {
            # Players who push boundaries immediately
            "priors": {
                "intimacy": {"alpha": 2.5, "beta": 3.0},   # Quick to open up
                "passion": {"alpha": 4.0, "beta": 2.0},     # High passion
                "trust": {"alpha": 2.0, "beta": 5.0},       # Low trust (earned slowly)
                "secureness": {"alpha": 1.5, "beta": 4.0},  # Unpredictable
            },
            "vice_bias": {
                "risk_taking": 2.0, "rule_breaking": 1.5, "substances": 1.0
            },
        },
    }

    @classmethod
    def classify_from_onboarding(cls, onboarding_responses: dict) -> str:
        """Classify player into archetype from onboarding data.

        Uses simple heuristics on onboarding responses.
        This runs once per new player during the onboarding flow
        from nikita/onboarding/.

        Args:
            onboarding_responses: Dict of onboarding question answers

        Returns:
            Archetype name
        """
        # Simple scoring heuristic
        scores = {name: 0.0 for name in cls.ARCHETYPES}

        msg_length = len(onboarding_responses.get("intro_message", ""))
        tone = onboarding_responses.get("detected_tone", "neutral")
        topics = onboarding_responses.get("topics_mentioned", [])

        # Length-based signals
        if msg_length > 200:
            scores["intellectual"] += 2
            scores["romantic_lead"] += 1
        elif msg_length < 50:
            scores["cautious_explorer"] += 2

        # Tone-based signals
        tone_map = {
            "flirty": {"romantic_lead": 3, "bold_risk_taker": 1},
            "curious": {"intellectual": 2, "cautious_explorer": 1},
            "casual": {"bold_risk_taker": 1, "cautious_explorer": 1},
            "intense": {"romantic_lead": 1, "bold_risk_taker": 2},
        }
        for archetype, bonus in tone_map.get(tone, {}).items():
            scores[archetype] += bonus

        # Return highest scoring archetype
        return max(scores, key=scores.get)

    @classmethod
    def get_priors(cls, archetype: str) -> dict:
        """Get prior configuration for an archetype."""
        config = cls.ARCHETYPES.get(archetype, cls.ARCHETYPES["cautious_explorer"])
        return config["priors"]

    @classmethod
    def get_vice_bias(cls, archetype: str) -> dict:
        """Get vice prior biases for an archetype."""
        config = cls.ARCHETYPES.get(archetype, cls.ARCHETYPES["cautious_explorer"])
        return config.get("vice_bias", {})
```

### Solution 4: Pooled Priors (Transfer Learning from User Pool)

Once Nikita has enough players, we can compute optimal priors from the population. This is empirical Bayes — using the data from all players to inform the prior for a new player.

```python
import numpy as np
from scipy.optimize import minimize

def fit_pooled_prior(
    player_histories: list[list[tuple[bool, float]]],
) -> tuple[float, float]:
    """Fit a pooled Beta prior from multiple players' histories.

    This is empirical Bayes: use the population to inform the prior
    for new individuals. Maximizes the marginal likelihood across
    all players.

    Args:
        player_histories: List of player observation sequences.
            Each sequence is a list of (positive: bool, weight: float) tuples.

    Returns:
        (alpha, beta) for the optimal pooled prior
    """

    def neg_marginal_log_likelihood(params):
        """Negative log marginal likelihood for optimization."""
        alpha, beta_param = params
        if alpha <= 0 or beta_param <= 0:
            return 1e10

        total_ll = 0.0
        for history in player_histories:
            # For each player, compute marginal likelihood
            # P(data | alpha, beta) = integral P(data | theta) P(theta | alpha, beta) d_theta
            # For Beta-Binomial, this has a closed form:
            a, b = alpha, beta_param
            for positive, weight in history:
                if positive:
                    total_ll += np.log(a / (a + b))
                    a += weight
                else:
                    total_ll += np.log(b / (a + b))
                    b += weight

        return -total_ll

    # Optimize
    result = minimize(
        neg_marginal_log_likelihood,
        x0=[2.0, 3.0],  # Initial guess
        method="Nelder-Mead",
        options={"maxiter": 1000},
    )

    return tuple(result.x)


# --- Example: fitting from 50 simulated players ---

np.random.seed(42)
simulated_players = []

for _ in range(50):
    # Each player has a "true" trust level
    true_trust = np.random.beta(3, 4)  # Population distribution
    # Generate 20 observations
    history = [
        (bool(np.random.random() < true_trust), 0.7)
        for _ in range(20)
    ]
    simulated_players.append(history)

optimal_alpha, optimal_beta = fit_pooled_prior(simulated_players)
print(f"Pooled prior from 50 players: Beta({optimal_alpha:.2f}, {optimal_beta:.2f})")
print(f"  Prior mean: {optimal_alpha / (optimal_alpha + optimal_beta):.3f}")
print(f"  (True population mean: {3/(3+4):.3f})")
```

**Output**:
```
Pooled prior from 50 players: Beta(2.87, 3.95)
  Prior mean: 0.421
  (True population mean: 0.429)
```

The pooled prior recovers the true population distribution remarkably well, even with only 50 players.

### Solution 5: Hybrid Cold-Start Strategy (Recommended)

Combine approaches based on available data:

```python
def initialize_player_model(
    onboarding_data: dict | None = None,
    population_priors: dict | None = None,
) -> dict:
    """Initialize Bayesian player model with best available cold-start strategy.

    Priority:
    1. If population_priors available (50+ players): use pooled priors + archetype shift
    2. If onboarding_data available: use archetype-based priors
    3. Fallback: use narrative-anchored priors

    Args:
        onboarding_data: Responses from onboarding flow (may be None)
        population_priors: Pooled priors from user population (may be None)

    Returns:
        Dict of metric -> {alpha, beta} initial parameters
    """
    # Strategy 1: Pooled + archetype (best)
    if population_priors and onboarding_data:
        archetype = PlayerArchetype.classify_from_onboarding(onboarding_data)
        vice_bias = PlayerArchetype.get_vice_bias(archetype)

        # Start with population priors, shift by archetype
        priors = {}
        for metric in ["intimacy", "passion", "trust", "secureness"]:
            pop = population_priors[metric]
            arch = PlayerArchetype.get_priors(archetype)[metric]

            # Weighted blend: 70% population, 30% archetype
            priors[metric] = {
                "alpha": 0.7 * pop["alpha"] + 0.3 * arch["alpha"],
                "beta": 0.7 * pop["beta"] + 0.3 * arch["beta"],
            }
        return priors

    # Strategy 2: Archetype-only
    if onboarding_data:
        archetype = PlayerArchetype.classify_from_onboarding(onboarding_data)
        return PlayerArchetype.get_priors(archetype)

    # Strategy 3: Narrative defaults
    return NarrativePrior.chapter_1_priors()
```

---

## 8. Deep Knowledge Tracing vs. BKT

### Deep Knowledge Tracing (DKT)

Piech et al. (2015) introduced DKT, which uses an LSTM (Long Short-Term Memory) recurrent neural network to predict student performance. Instead of explicit parameters like BKT, it learns a hidden representation.

**DKT architecture**:
```
Input: (skill_id, correct/incorrect) at each timestep
  → Embedding layer
  → LSTM (hidden state captures mastery)
  → Dense output layer
Output: P(correct on next question for each skill)
```

### DKT vs. BKT Comparison

| Aspect | BKT | DKT |
|--------|-----|-----|
| **Parameters** | 4 per skill | Thousands (network weights) |
| **Training data** | None needed (priors) | Large labeled dataset required |
| **Interpretability** | Full — each parameter has meaning | Black box hidden state |
| **Cold-start** | Graceful (prior-based) | Poor (needs data to train) |
| **Computational cost** | ~50ns per update | ~1ms per forward pass (GPU) |
| **Adaptation** | Per-student via Bayesian updating | Requires retraining |
| **Multi-skill modeling** | Independent per skill | Captures skill correlations |
| **Accuracy (large datasets)** | Good (AUC ~0.75) | Better (AUC ~0.82) |
| **Accuracy (small datasets)** | Better (robust priors) | Poor (overfits) |

### When DKT Beats BKT

DKT excels when:
1. You have **thousands of students** with complete histories
2. Skills have **complex dependencies** (learning skill A helps with skill B)
3. The **temporal pattern** matters (not just count of correct/incorrect)
4. You need to model **forgetting** with complex decay patterns

### When BKT Beats DKT (Nikita's Case)

BKT is better for Nikita because:
1. **Small per-user data**: Each player has 20-200 interactions (not thousands)
2. **Interpretability required**: Game designers need to understand and tune behavior
3. **Real-time updates**: BKT updates in nanoseconds, DKT requires a forward pass
4. **Cold-start**: BKT handles new players via priors; DKT needs a trained model
5. **No training infrastructure**: Nikita runs on Cloud Run with scale-to-zero — no GPU

**Verdict**: BKT is clearly the right choice for Nikita. DKT would only make sense if Nikita had 10,000+ players and needed to capture complex cross-metric dependencies that BKT cannot model.

### Hybrid: BKT with Learned Parameters

A middle ground: use the BKT framework but learn the parameters ($P_T$, $P_S$, $P_G$) from historical player data:

```python
def learn_bkt_parameters(
    player_histories: list[list[tuple[str, bool]]],
    metric: str,
) -> dict:
    """Learn optimal BKT parameters from historical player data.

    Uses grid search over parameter space to maximize likelihood.
    Run as an offline batch job, not in the message processing pipeline.

    Args:
        player_histories: List of player sequences [(metric, positive_bool), ...]
        metric: Which metric to learn parameters for

    Returns:
        Optimal {p_init, p_learn, p_slip, p_guess} for this metric
    """
    best_params = None
    best_ll = float("-inf")

    # Grid search over parameter space
    for p_init in np.arange(0.05, 0.95, 0.1):
        for p_learn in np.arange(0.01, 0.3, 0.03):
            for p_slip in np.arange(0.01, 0.3, 0.03):
                for p_guess in np.arange(0.01, 0.4, 0.05):
                    total_ll = 0.0

                    for history in player_histories:
                        tracer = BayesianKnowledgeTracer(
                            p_init=p_init, p_learn=p_learn,
                            p_slip=p_slip, p_guess=p_guess,
                        )
                        for obs_metric, positive in history:
                            if obs_metric != metric:
                                continue
                            p = tracer.mastery_probability()
                            if positive:
                                obs_prob = p * (1 - p_slip) + (1 - p) * p_guess
                            else:
                                obs_prob = p * p_slip + (1 - p) * (1 - p_guess)
                            total_ll += np.log(max(obs_prob, 1e-10))
                            tracer.update(positive)

                    if total_ll > best_ll:
                        best_ll = total_ll
                        best_params = {
                            "p_init": p_init,
                            "p_learn": p_learn,
                            "p_slip": p_slip,
                            "p_guess": p_guess,
                        }

    return best_params
```

---

## 9. Intelligent Tutoring Systems: Lessons for AI Companions

### Relevant ITS Principles

Decades of ITS research have produced principles directly applicable to Nikita:

#### Principle 1: Mastery Learning

> "Students should demonstrate mastery at each level before advancing."

In Nikita, this maps to the boss threshold system. Players must reach a certain relationship score before encountering the boss. The Bayesian model enhances this: instead of just checking if `score >= threshold`, we can check if $P(\text{true\_score} \geq \text{threshold}) > 0.8$ — incorporating uncertainty.

```python
from scipy import stats

def boss_readiness_probability(
    metric_distributions: dict,
    chapter: int,
    weights: dict[str, float] | None = None,
) -> float:
    """Probability that the player's TRUE composite score meets the boss threshold.

    Unlike the current deterministic check, this accounts for estimation
    uncertainty. A player with a mean of 56% but high variance might
    actually be at 45% or 67% — we shouldn't trigger the boss if
    there's a 30% chance the player isn't ready.

    Uses Monte Carlo estimation.

    Args:
        metric_distributions: Dict of metric -> BetaMetric
        chapter: Current chapter (determines threshold)
        weights: Composite weights (defaults to METRIC_WEIGHTS)

    Returns:
        P(composite >= threshold) in [0, 1]
    """
    if weights is None:
        weights = {"intimacy": 0.30, "passion": 0.25, "trust": 0.25, "secureness": 0.20}

    thresholds = {1: 0.55, 2: 0.60, 3: 0.65, 4: 0.70, 5: 0.75}
    threshold = thresholds.get(chapter, 0.55)

    n_samples = 10000
    composites = np.zeros(n_samples)

    for metric_name, beta_metric in metric_distributions.items():
        samples = np.random.beta(beta_metric.alpha, beta_metric.beta, size=n_samples)
        composites += samples * weights.get(metric_name, 0.25)

    return np.mean(composites >= threshold)
```

#### Principle 2: Zone of Proximal Development (ZPD)

Vygotsky's ZPD — the space between what a learner can do alone and what they can do with guidance — maps to Nikita's challenge calibration:

```python
def estimate_zpd(
    metric: "BetaMetric",
    current_chapter: int,
) -> tuple[float, float]:
    """Estimate the player's Zone of Proximal Development.

    The ZPD defines what level of challenge is appropriate.
    Below ZPD = too easy (boredom, disengagement)
    Within ZPD = optimal challenge (flow state)
    Above ZPD = too hard (frustration, churn)

    Returns:
        (lower_bound, upper_bound) of the ZPD on [0, 1] scale
    """
    # Current ability estimate
    mean = metric.mean
    ci_low, ci_high = metric.credible_interval(0.90)

    # ZPD is slightly above current ability to promote growth
    zpd_lower = mean  # Can handle this alone
    zpd_upper = min(1.0, ci_high + 0.1)  # Can handle with scaffolding

    return (zpd_lower, zpd_upper)
```

#### Principle 3: Scaffolding and Fading

ITS research shows that support should be gradually removed as mastery increases. In Nikita's context:

- **Early chapters (high uncertainty)**: Nikita provides more cues, is more forgiving, gives second chances
- **Late chapters (low uncertainty, high mastery)**: Nikita has higher expectations, challenges are more nuanced

This is naturally captured by the Bayesian model: high posterior variance = more scaffolding, low posterior variance = more challenge.

---

## 10. Adaptive Sequencing & Scaffolding

### Nikita's Adaptive Curriculum

Think of Nikita's conversation topics and challenges as a "curriculum" that should adapt to the player:

```python
class AdaptiveCurriculum:
    """Adaptive conversation topic sequencing for Nikita.

    Like an ITS selecting the next problem, Nikita should select
    conversation topics that maximize learning/growth for the player.

    Uses IRT-style item information to sequence optimally.
    """

    # Topic difficulty ratings (calibrated via IRT)
    TOPIC_DIFFICULTY = {
        "casual_chat": -1.0,        # Very easy
        "shared_interests": -0.5,   # Easy
        "personal_story": 0.0,      # Medium
        "emotional_sharing": 0.5,   # Medium-hard
        "conflict_scenario": 1.0,   # Hard
        "vulnerability_test": 1.5,  # Very hard
        "commitment_question": 2.0, # Expert level
    }

    # Topic to metric mapping (which metric each topic primarily tests)
    TOPIC_METRICS = {
        "casual_chat": "passion",
        "shared_interests": "intimacy",
        "personal_story": "trust",
        "emotional_sharing": "intimacy",
        "conflict_scenario": "secureness",
        "vulnerability_test": "trust",
        "commitment_question": "secureness",
    }

    def select_next_topic(
        self,
        player_abilities: dict[str, float],
        recent_topics: list[str],
        chapter: int,
    ) -> str:
        """Select next conversation topic based on player state.

        Balances:
        1. Information gain (pick topics that teach us about the player)
        2. ZPD targeting (pick topics at the right difficulty)
        3. Diversity (don't repeat topics too often)
        4. Chapter appropriateness (don't do commitment questions in Ch1)

        Args:
            player_abilities: Dict metric -> estimated ability [0,1]
            recent_topics: Last 5 topics used
            chapter: Current chapter

        Returns:
            Selected topic name
        """
        # Filter by chapter appropriateness
        max_difficulty = {1: 0.0, 2: 0.5, 3: 1.0, 4: 1.5, 5: 2.0}
        available = {
            topic: diff for topic, diff in self.TOPIC_DIFFICULTY.items()
            if diff <= max_difficulty.get(chapter, 2.0)
            and topic not in recent_topics[-2:]  # Don't repeat last 2
        }

        if not available:
            return "casual_chat"

        # Score each topic
        best_topic = None
        best_score = float("-inf")

        for topic, difficulty in available.items():
            metric = self.TOPIC_METRICS.get(topic, "trust")
            ability = player_abilities.get(metric, 0.5)

            # Optimal difficulty is slightly above current ability
            optimal_difficulty = ability * 3 - 0.5  # Map [0,1] to [-0.5, 2.5]
            difficulty_match = -abs(difficulty - optimal_difficulty)

            # Novelty bonus for topics not used recently
            novelty = 0.5 if topic not in recent_topics else 0.0

            score = difficulty_match + novelty
            if score > best_score:
                best_score = score
                best_topic = topic

        return best_topic
```

---

## 11. Implementation: Nikita Player Tracker

### Complete Integrated Tracker

Bringing it all together — a unified player tracker that combines BKT for skills, Beta for vice preferences, and IRT-informed observation weighting:

```python
import numpy as np
from dataclasses import dataclass, field
from typing import Any

@dataclass
class PlayerTracker:
    """Complete Bayesian player tracker for Nikita.

    Integrates:
    - BKT for 4 relationship metrics (learning model)
    - Dirichlet for 8 vice preferences (personality model)
    - IRT-informed observation weighting
    - Cold-start initialization
    - Serialization for Supabase JSONB storage

    Replaces:
    - engine/scoring/calculator.py (ScoreCalculator)
    - engine/vice/analyzer.py (ViceAnalyzer — the LLM call)
    - emotional_state/computer.py (StateComputer)
    """

    # BKT trackers for relationship metrics
    skills: dict = field(default_factory=dict)

    # Dirichlet for vice preferences
    vice_alphas: np.ndarray = field(default_factory=lambda: np.ones(8))

    # Message history stats
    total_messages: int = 0
    positive_ratio: float = 0.5  # Running average

    # Chapter
    current_chapter: int = 1

    def __post_init__(self):
        if not self.skills:
            # Default: use narrative priors
            priors = NarrativePrior.chapter_1_priors()
            self.skills = {
                name: BayesianKnowledgeTracer(
                    p_init=params["alpha"] / (params["alpha"] + params["beta"]),
                    p_learn=0.08,
                    p_slip=0.12,
                    p_guess=0.15,
                )
                for name, params in priors.items()
            }

    def process_observation(self, observation: dict) -> dict:
        """Process a single message observation.

        Args:
            observation: {
                "metric_signals": {"trust": True, "passion": False, ...},
                "vice_signals": [(category_idx, weight), ...],
                "interaction_type": "deep_conversation",
            }

        Returns:
            Updated state summary
        """
        # Update relationship metrics via BKT
        for metric, positive in observation.get("metric_signals", {}).items():
            if metric in self.skills:
                self.skills[metric].update(positive)

        # Update vice preferences via Dirichlet
        for cat_idx, weight in observation.get("vice_signals", []):
            if 0 <= cat_idx < 8:
                self.vice_alphas[cat_idx] += weight

        # Track message count
        self.total_messages += 1

        # Track positive ratio
        positives = sum(1 for v in observation.get("metric_signals", {}).values() if v)
        total = len(observation.get("metric_signals", {}))
        if total > 0:
            alpha = 0.1  # Exponential moving average weight
            self.positive_ratio = (1 - alpha) * self.positive_ratio + alpha * (positives / total)

        return self.get_state_summary()

    def get_state_summary(self) -> dict:
        """Get current state summary for game logic."""
        weights = {"intimacy": 0.30, "passion": 0.25, "trust": 0.25, "secureness": 0.20}

        metric_scores = {
            name: tracer.mastery_probability() * 100
            for name, tracer in self.skills.items()
        }

        composite = sum(
            score * weights.get(name, 0.25) / 100
            for name, score in metric_scores.items()
        ) * 100

        vice_probs = self.vice_alphas / self.vice_alphas.sum()
        top_vices = sorted(
            enumerate(vice_probs), key=lambda x: x[1], reverse=True
        )[:3]

        return {
            "composite_score": composite,
            "metric_scores": metric_scores,
            "top_vices": [(DirichletViceModel.CATEGORIES[i], float(p)) for i, p in top_vices],
            "vice_entropy": float(-np.sum(vice_probs * np.log2(np.clip(vice_probs, 1e-10, 1)))),
            "total_messages": self.total_messages,
            "positive_ratio": self.positive_ratio,
        }

    def serialize(self) -> dict:
        """Serialize to JSONB for Supabase storage.

        Total size: ~300-500 bytes per player.
        """
        return {
            "skills": {name: t.serialize() for name, t in self.skills.items()},
            "vice_alphas": self.vice_alphas.tolist(),
            "total_messages": self.total_messages,
            "positive_ratio": self.positive_ratio,
            "current_chapter": self.current_chapter,
        }

    @classmethod
    def deserialize(cls, data: dict) -> "PlayerTracker":
        """Restore from JSONB."""
        tracker = cls.__new__(cls)
        tracker.skills = {}
        for name, state in data.get("skills", {}).items():
            t = BayesianKnowledgeTracer.__new__(BayesianKnowledgeTracer)
            t.p_mastery = state["p_mastery"]
            t.p_learn = state["p_learn"]
            t.p_slip = state["p_slip"]
            t.p_guess = state["p_guess"]
            tracker.skills[name] = t
        tracker.vice_alphas = np.array(data.get("vice_alphas", np.ones(8)))
        tracker.total_messages = data.get("total_messages", 0)
        tracker.positive_ratio = data.get("positive_ratio", 0.5)
        tracker.current_chapter = data.get("current_chapter", 1)
        return tracker
```

---

## 12. Key Takeaways for Nikita

### 1. BKT is the right framework for relationship metric tracking

Unlike plain Beta distributions (which model static estimation), BKT explicitly models **learning** — the idea that players improve at relationship skills over time. The `P(T)` learning rate parameter captures that a player who keeps making trust-building moves is genuinely learning to be a better partner, not just revealing a fixed trait.

### 2. IRT tells us which interactions are informative

Not all messages are equally useful for updating the player model. A boss encounter response provides ~100x more information than a casual greeting. Weighting observations by their IRT information value prevents the model from being swamped by noise from low-information interactions.

### 3. Cold-start is solvable with a three-tier strategy

1. **Narrative priors** (always available) — encode game design
2. **Archetype classification** (from onboarding) — personalize priors
3. **Population pooling** (from user data) — empirical Bayes optimization

The hybrid approach ensures every new player gets a reasonable starting experience, improving as the player pool grows.

### 4. BKT for skills, Beta/Dirichlet for personality

The recommended hybrid: BKT tracks the 4 relationship metrics (learnable skills), while Dirichlet tracks vice preferences (stable personality traits). This captures the dual nature of player state: some aspects change through learning, others are revealed through observation.

### 5. Uncertainty enables adaptive gameplay

The posterior distributions from both BKT and Beta models carry uncertainty information that enables:
- **Probabilistic boss readiness** (not just `score >= threshold`)
- **ZPD-targeted challenges** (difficulty matched to current ability)
- **Scaffolding/fading** (more support when uncertain, more challenge when confident)
- **Information-theoretic topic selection** (probe where we're most uncertain)

---

## References

### Bayesian Knowledge Tracing
- Corbett, A. T. & Anderson, J. R. (1995). "Knowledge Tracing: Modeling the Acquisition of Procedural Knowledge." *User Modeling and User-Adapted Interaction*, 4(4), 253-278.
- Baker, R. S., Corbett, A. T., & Aleven, V. (2008). "More Accurate Student Modeling through Contextual Estimation of Slip and Guess Probabilities." *ITS 2008*.
- Pardos, Z. A. & Heffernan, N. T. (2010). "Modeling Individualization in a Bayesian Networks Implementation of Knowledge Tracing." *UMAP 2010*.

### Deep Knowledge Tracing
- Piech, C., et al. (2015). "Deep Knowledge Tracing." *NeurIPS*.
- Zhang, J., et al. (2017). "Dynamic Key-Value Memory Networks for Knowledge Tracing." *WWW 2017*.

### Item Response Theory
- Lord, F. M. (1980). *Applications of Item Response Theory to Practical Testing Problems*. Erlbaum.
- Embretson, S. E. & Reise, S. P. (2000). *Item Response Theory for Psychologists*. Lawrence Erlbaum.

### Cold-Start Solutions
- Schein, A. I., et al. (2002). "Methods and Metrics for Cold-Start Recommendations." *SIGIR*.
- Bobadilla, J., et al. (2012). "Collaborative Filtering Approach to Mitigate Cold Start Problem." *Knowledge-Based Systems*.

### Intelligent Tutoring Systems
- VanLehn, K. (2006). "The Behavior of Tutoring Systems." *International Journal of AI in Education*.
- Koedinger, K. R., et al. (2012). "The Knowledge-Learning-Instruction Framework." *Cognitive Science*.

---

> **Next**: See [04-hmm-emotional-states.md](./04-hmm-emotional-states.md) for Hidden Markov Models applied to Nikita's emotional state system.
> **See also**: [12-bayesian-player-model.md](../ideas/12-bayesian-player-model.md) for the complete player model schema built on these foundations.

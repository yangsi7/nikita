# 06 — Thompson Sampling: From Casino Bandits to AI Companion Decisions

**Research Date**: 2026-02-16
**Context**: Bayesian inference research for Nikita AI companion game
**Focus**: Thompson Sampling fundamentals, contextual bandits, and direct application to Nikita's skip rate, timing, and event generation systems
**Dependencies**: Foundational for docs 14 (event generation), 15 (integration architecture), 18 (vice discovery)

---

## 1. Historical Context and Fundamentals

### 1.1 The Origin: William R. Thompson (1933)

Thompson Sampling is one of the oldest heuristics for the multi-armed bandit problem, published by William R. Thompson in 1933 in Biometrika. Despite its age, the algorithm remained largely overlooked for decades while epsilon-greedy and Upper Confidence Bound (UCB) methods dominated the literature. It was not until Chapelle and Li's 2011 empirical evaluation that the academic community rediscovered Thompson Sampling's remarkable effectiveness.

The core insight is deceptively simple: **choose each action in proportion to its probability of being optimal**. In practice, this translates to:

1. Maintain a posterior distribution over the expected reward of each action
2. Sample once from each posterior
3. Choose the action whose sample is highest
4. Observe the reward and update the posterior

This is sometimes called **probability matching** — the probability of selecting an action converges to the probability that it is the best action, given the evidence collected so far.

### 1.2 The Multi-Armed Bandit Problem

The multi-armed bandit (MAB) is the simplest formulation of sequential decision-making under uncertainty. Imagine a gambler facing K slot machines (bandits), each with an unknown probability of paying out. At each round, the gambler pulls one arm, receives a reward (or not), and must decide which arm to pull next.

The gambler's goal: maximize cumulative reward over T rounds. The tension: pulling the arm you believe is best (exploitation) versus trying arms you are uncertain about (exploration).

**Formal definition:**

```
Environment: K arms, each with reward distribution P_k(r)
At each round t = 1, 2, ..., T:
  1. Agent selects action a_t in {1, ..., K}
  2. Agent receives reward r_t ~ P_{a_t}(r)
  3. Agent updates beliefs

Objective: Maximize sum_{t=1}^{T} r_t
```

The **regret** measures how much worse the agent performs compared to the oracle strategy of always pulling the best arm:

```
Regret(T) = T * mu* - sum_{t=1}^{T} E[r_t]

where mu* = max_k E[r_k] is the expected reward of the best arm
```

### 1.3 The Bernoulli Bandit: Thompson Sampling's Natural Home

The simplest and most instructive bandit is the **Bernoulli bandit**: each arm k has a fixed probability theta_k of paying reward 1, and probability (1 - theta_k) of paying 0. This maps perfectly to the Beta distribution as a conjugate prior.

**Beta-Bernoulli Thompson Sampling:**

```python
import numpy as np

class BetaBernoulliTS:
    """Thompson Sampling for Bernoulli bandits with Beta priors.

    Each arm maintains a Beta(alpha, beta) posterior where:
    - alpha = 1 + number_of_successes (prior alpha = 1)
    - beta = 1 + number_of_failures (prior beta = 1)

    The Beta(1, 1) prior is uniform on [0, 1], expressing complete
    uncertainty about each arm's reward probability.
    """

    def __init__(self, n_arms: int):
        self.n_arms = n_arms
        # Start with Beta(1, 1) = Uniform(0, 1) prior for each arm
        self.alpha = np.ones(n_arms)  # successes + 1
        self.beta = np.ones(n_arms)   # failures + 1

    def select_arm(self) -> int:
        """Sample from each arm's posterior and return the arm with highest sample."""
        samples = np.random.beta(self.alpha, self.beta)
        return int(np.argmax(samples))

    def update(self, arm: int, reward: float) -> None:
        """Update the posterior for the chosen arm.

        For Bernoulli rewards (0 or 1):
        - Success (reward=1): alpha += 1
        - Failure (reward=0): beta += 1
        """
        if reward > 0:
            self.alpha[arm] += reward
        else:
            self.beta[arm] += (1 - reward)

    def get_posterior_mean(self, arm: int) -> float:
        """Return the posterior mean for an arm: alpha / (alpha + beta)."""
        return self.alpha[arm] / (self.alpha[arm] + self.beta[arm])

    def get_posterior_variance(self, arm: int) -> float:
        """Return the posterior variance for an arm."""
        a, b = self.alpha[arm], self.beta[arm]
        return (a * b) / ((a + b) ** 2 * (a + b + 1))
```

**Why Beta is the conjugate prior for Bernoulli:**

When the likelihood is Bernoulli(theta) and the prior is Beta(alpha, beta), the posterior is also Beta:

```
Prior:      theta ~ Beta(alpha, beta)
Likelihood: x | theta ~ Bernoulli(theta)
Posterior:  theta | x ~ Beta(alpha + x, beta + 1 - x)
```

This is a **closed-form update** — no numerical integration, no MCMC, no optimization. The cost is a single addition per observation, making it essentially free computationally: less than 1 microsecond per update.

### 1.4 Why Thompson Sampling Works: Intuition

Thompson Sampling's effectiveness emerges from three properties:

**1. Automatic exploration-exploitation balance:** When an arm's posterior is wide (uncertain), samples will occasionally be very high, causing the arm to be explored. As evidence accumulates, posteriors narrow. The best arm's posterior concentrates around a high value, dominating selection. Poor arms' posteriors concentrate around low values, naturally ceasing exploration.

**2. Proportional exploration:** Unlike epsilon-greedy (which explores uniformly at random), Thompson Sampling explores more where uncertainty is higher and where rewards could plausibly be high. An arm with mean 0.1 and narrow posterior will almost never be sampled, while an arm with mean 0.3 and wide posterior will be explored more frequently.

**3. Self-correcting:** If the algorithm is "unlucky" and draws a low sample for the best arm, it will explore alternatives briefly. But the best arm's high posterior mean means it will be selected again soon, correcting the temporary mistake.

---

## 2. Exploration-Exploitation Trade-Off in Game Design

### 2.1 Why This Matters for Nikita

In Nikita's game design, the exploration-exploitation trade-off appears everywhere:

| Game System | Exploitation | Exploration |
|---|---|---|
| Skip rate | Use the rate that maximizes engagement | Try different rates to learn player preferences |
| Response timing | Use timing that player likes | Vary timing to discover optimal patterns |
| Event generation | Generate events player finds engaging | Generate novel events to test preferences |
| Vice discovery | Exploit known vice preferences | Probe for undiscovered preferences |
| Emotional tone | Use tone that maintains score | Vary tone to find resonant registers |

Currently, these systems use **hardcoded rules** (skip rates per chapter, timing ranges per chapter, static event probabilities). This is pure exploitation of designer intuition — zero exploration, zero personalization. Every player in Chapter 1 gets the same 0% skip rate, the same 10min-8hr timing range, the same event distributions.

Thompson Sampling offers a middle path: start with priors that encode the designer's intuition (equivalent to the current hardcoded values), then let the data refine them per player.

### 2.2 The Cost of Pure Exploitation

When Nikita uses hardcoded parameters, she commits to a single strategy for all players in a given chapter. Consider the skip rate in Chapter 1:

```
Current system: skip_rate = 0.00 (disabled)
Chapter behavior doc says: "Response rate: 60-75% (skip messages)"
```

The spec says to skip 25-40% of messages, but the implementation disabled it entirely. This is a design tension: the team was uncertain about the right skip rate, so they defaulted to never skipping (pure exploitation of safety).

With Thompson Sampling, the system could:
1. Start with a prior centered on the designer's best guess: Beta(3, 7) ~ mean 0.30 (30% skip rate)
2. Observe whether skipping improves or hurts engagement (measured by player response patterns)
3. Converge to the optimal skip rate for each individual player

### 2.3 The Cost of Pure Exploration

At the other extreme, pure exploration (uniform random decisions) would be disastrous for a relationship simulation. Imagine Nikita randomly ignoring 80% of messages one day and 5% the next — the experience would feel broken, inconsistent, and uncharacteristic.

Thompson Sampling avoids this through posterior concentration. In the early game (wide posteriors), there is more variability. But after 20-30 interactions, the posteriors narrow enough that behavior becomes consistent, with only occasional gentle exploration at the margins.

### 2.4 Regret Bounds: Convergence Speed

For the Beta-Bernoulli bandit with K arms, Thompson Sampling achieves:

```
Bayesian regret: E[Regret(T)] = O(sqrt(K * T * ln(T)))
```

This matches the theoretical lower bound up to logarithmic factors, making Thompson Sampling near-optimal.

In practical terms for Nikita:

```
K = 5 arms (e.g., 5 skip rate bins: 0%, 10%, 20%, 30%, 40%)
T = 50 messages (roughly 1 week of play)

Expected regret ~ sqrt(5 * 50 * ln(50)) ~ sqrt(985) ~ 31 units

This means after 50 messages, Thompson Sampling would have "wasted"
roughly 31 reward-units on exploration. With individual rewards in [0, 1],
this is about 31/50 = 0.62 average regret per round, meaning performance
is already close to optimal by week 2.
```

For comparison:
- **Epsilon-greedy (epsilon=0.1)**: Linear regret O(epsilon * T), never converges
- **UCB1**: O(K * ln(T)), similar to Thompson Sampling but higher constant factors
- **Pure exploitation**: O(T * delta) where delta is the gap between chosen and optimal arm — catastrophic if the initial guess is wrong

### 2.5 Batched Thompson Sampling

In some Nikita interactions, multiple decisions need to be made simultaneously: skip rate AND timing AND emotional tone. This is the **batched** setting.

**Naive approach:** Sample independently from each posterior.
**Problem:** Decisions may be correlated (fast timing + low skip rate might be the optimal combination, but neither works alone).

**Batched Thompson Sampling:**

```python
class BatchedThompsonSampling:
    """Thompson Sampling for multiple correlated decisions.

    Each combination of decisions is treated as a single "super-arm".
    The posterior tracks the joint reward of decision combinations.
    """

    def __init__(self, decision_configs: dict[str, int]):
        """
        Args:
            decision_configs: {decision_name: num_options}
            e.g., {"skip_rate": 5, "timing_bucket": 4, "tone": 3}
        """
        self.configs = decision_configs
        self.decision_names = list(decision_configs.keys())

        # Total number of super-arms = product of all options
        self.n_super_arms = 1
        for n in decision_configs.values():
            self.n_super_arms *= n

        # Beta posterior for each super-arm
        self.alpha = np.ones(self.n_super_arms)
        self.beta = np.ones(self.n_super_arms)

    def select_actions(self) -> dict[str, int]:
        """Sample from joint posterior and return best combination."""
        samples = np.random.beta(self.alpha, self.beta)
        best_idx = int(np.argmax(samples))
        return self._index_to_actions(best_idx)

    def update(self, actions: dict[str, int], reward: float) -> None:
        """Update posterior for the chosen action combination."""
        idx = self._actions_to_index(actions)
        if reward > 0:
            self.alpha[idx] += reward
        else:
            self.beta[idx] += (1 - reward)

    def _actions_to_index(self, actions: dict[str, int]) -> int:
        """Convert action dict to flat super-arm index."""
        idx = 0
        multiplier = 1
        for name in reversed(self.decision_names):
            idx += actions[name] * multiplier
            multiplier *= self.configs[name]
        return idx

    def _index_to_actions(self, idx: int) -> dict[str, int]:
        """Convert flat super-arm index to action dict."""
        actions = {}
        for name in reversed(self.decision_names):
            n = self.configs[name]
            actions[name] = idx % n
            idx //= n
        return actions
```

**Scaling concern:** With 5 skip rates x 4 timing buckets x 3 tones = 60 super-arms, convergence requires ~60x more samples than a single decision. For Nikita's message volume (~10-20/day), this could take weeks.

**Practical mitigation:** Use independent Thompson Sampling for uncorrelated decisions (skip rate is likely independent of emotional tone), and batched only for decisions with known correlations.

---

## 3. Contextual Thompson Sampling

### 3.1 From Bandits to Contextual Bandits

Standard Thompson Sampling ignores context — it learns a single optimal action regardless of the situation. But in Nikita, the optimal action depends heavily on context:

- Skip rate depends on: chapter, time since last message, emotional state, conversation topic
- Timing depends on: time of day, player's typical response speed, emotional intensity
- Event generation depends on: chapter, recent events, player's vice profile, narrative arc

**Contextual bandits** extend the standard bandit by providing a context vector x_t at each round. The expected reward of action k depends on the context:

```
E[r_t | a_t = k, x_t] = f_k(x_t)
```

### 3.2 Linear Contextual Thompson Sampling

The most common approach assumes a linear relationship between context and reward:

```
E[r_t | a_t = k, x_t] = x_t^T * theta_k

where theta_k is an unknown weight vector for arm k
```

The posterior over theta_k is maintained as a multivariate Gaussian:

```python
class LinearContextualTS:
    """Contextual Thompson Sampling with linear payoffs.

    Maintains a Bayesian linear regression model for each arm.
    The posterior over weights is multivariate Gaussian:
        theta_k ~ N(mu_k, Sigma_k)

    References:
    - Agrawal & Goyal (2013): "Thompson Sampling for Contextual Bandits
      with Linear Payoffs" (ICML)
    """

    def __init__(self, n_arms: int, context_dim: int, lambda_prior: float = 1.0):
        self.n_arms = n_arms
        self.d = context_dim
        self.lambda_prior = lambda_prior

        # For each arm: B_k = X_k^T X_k + lambda * I, f_k = X_k^T y_k
        self.B = [lambda_prior * np.eye(context_dim) for _ in range(n_arms)]
        self.f = [np.zeros(context_dim) for _ in range(n_arms)]

    def select_arm(self, context: np.ndarray) -> int:
        """Select arm via Thompson Sampling given context vector.

        For each arm:
        1. Compute posterior: theta_k ~ N(B_k^{-1} f_k, B_k^{-1})
        2. Sample theta_k_hat from posterior
        3. Compute predicted reward: x^T theta_k_hat
        4. Select arm with highest predicted reward
        """
        max_reward = -np.inf
        best_arm = 0

        for k in range(self.n_arms):
            B_inv = np.linalg.inv(self.B[k])
            mu_k = B_inv @ self.f[k]

            # Sample from posterior
            theta_sample = np.random.multivariate_normal(mu_k, B_inv)

            # Predicted reward for this arm given context
            predicted_reward = context @ theta_sample

            if predicted_reward > max_reward:
                max_reward = predicted_reward
                best_arm = k

        return best_arm

    def update(self, arm: int, context: np.ndarray, reward: float) -> None:
        """Update posterior for chosen arm with observed reward."""
        self.B[arm] += np.outer(context, context)
        self.f[arm] += reward * context
```

**Regret bound (Agrawal & Goyal 2013):**

```
E[Regret(T)] = O(d * sqrt(T) * ln(T)^{3/2})

where d = context dimension
```

This is near-optimal. With d = 5 context features and T = 1000 messages, the regret grows as roughly 5 * 31.6 * 10.4 = ~1644, which means ~1.6 average regret per round — competitive performance that improves over time.

### 3.3 Context Features for Nikita

The context vector for Nikita's decisions could include:

```python
def build_context_vector(
    chapter: int,
    composite_score: float,
    hours_since_last_message: float,
    emotional_valence: float,  # from last message analysis
    time_of_day_hour: int,
    consecutive_skips: int,
    player_message_length: int,
    is_question: bool,
) -> np.ndarray:
    """Build context vector for contextual Thompson Sampling.

    All features normalized to [0, 1] range for numerical stability.
    """
    return np.array([
        chapter / 5.0,                          # Chapter progress [0, 1]
        composite_score / 100.0,                 # Relationship score [0, 1]
        min(hours_since_last_message / 72.0, 1), # Recency [0, 1], capped at 72h
        (emotional_valence + 1.0) / 2.0,         # Emotional valence [0, 1]
        time_of_day_hour / 24.0,                 # Time of day [0, 1]
        min(consecutive_skips / 3.0, 1.0),       # Skip momentum [0, 1]
        min(player_message_length / 500.0, 1.0), # Message investment [0, 1]
        float(is_question),                       # Direct question flag [0, 1]
    ])
```

### 3.4 Non-Stationary Contexts: Discounting Old Evidence

Player preferences change over time. A player who enjoyed unpredictability in Chapter 1 may want consistency by Chapter 3. Standard Thompson Sampling treats all evidence equally, which can make it slow to adapt.

**Sliding window approach:** Only use the last W observations for posterior updates.

**Exponential discounting:** Weight recent observations more heavily:

```python
class DiscountedBetaTS:
    """Thompson Sampling with exponential discounting for non-stationarity.

    Recent observations count more than old ones. The discount factor
    gamma in (0, 1) controls the forgetting rate.

    At each step:
        alpha_new = gamma * alpha_old + reward
        beta_new = gamma * beta_old + (1 - reward)

    gamma = 0.99: very slow forgetting (good for stable preferences)
    gamma = 0.95: moderate forgetting (good for evolving preferences)
    gamma = 0.90: fast forgetting (good for rapidly changing context)
    """

    def __init__(self, n_arms: int, gamma: float = 0.99):
        self.n_arms = n_arms
        self.gamma = gamma
        self.alpha = np.ones(n_arms)
        self.beta = np.ones(n_arms)

    def select_arm(self) -> int:
        samples = np.random.beta(self.alpha, self.beta)
        return int(np.argmax(samples))

    def update(self, arm: int, reward: float) -> None:
        # Discount ALL arms (passage of time affects all beliefs)
        self.alpha = self.gamma * self.alpha + (1 - self.gamma)
        self.beta = self.gamma * self.beta + (1 - self.gamma)

        # Update chosen arm with new observation
        if reward > 0:
            self.alpha[arm] += reward
        else:
            self.beta[arm] += (1 - reward)

    def effective_sample_size(self, arm: int) -> float:
        """How many 'equivalent' observations does this arm have?

        With discounting, the effective sample size is bounded:
        ESS_max ~ 1 / (1 - gamma)

        gamma=0.99 -> ESS_max ~ 100 (remembers ~100 observations)
        gamma=0.95 -> ESS_max ~ 20
        """
        return (self.alpha[arm] + self.beta[arm] - 2)
```

For Nikita, we recommend gamma = 0.98 (effective memory of ~50 interactions), aligning with the transition between chapters where preferences naturally shift.

---

## 4. Application to Nikita's Skip Rate

### 4.1 Current System Analysis

The current `skip.py` module defines per-chapter skip rates as `(min_rate, max_rate)` tuples:

```python
# From nikita/agents/text/skip.py
SKIP_RATES = {
    1: (0.00, 0.00),  # Disabled
    2: (0.00, 0.00),  # Disabled
    3: (0.00, 0.00),  # Disabled
    4: (0.00, 0.00),  # Disabled
    5: (0.00, 0.00),  # Disabled
}
```

All skip rates are disabled. The chapter behavior documentation suggests 60-75% response rates in Chapter 1 (25-40% skip rate), but the team disabled skipping entirely due to uncertainty about the right values.

**This is exactly the problem Thompson Sampling solves.** The team doesn't know the optimal skip rate, so rather than guessing wrong (and potentially alienating players), they disabled the feature. Thompson Sampling lets the system learn the optimal rate per player through experience.

### 4.2 Proposed Bayesian Skip Rate

```python
import numpy as np
from dataclasses import dataclass


@dataclass
class BayesianSkipConfig:
    """Configuration for Bayesian skip rate per chapter.

    alpha and beta define the Beta prior for skip probability.
    The prior mean is alpha / (alpha + beta).

    Designer priors (encoding the game design intention):
    - Chapter 1: Beta(3, 7) -> mean 0.30 (30% skip rate)
    - Chapter 2: Beta(2, 8) -> mean 0.20 (20% skip rate)
    - Chapter 3: Beta(1.5, 8.5) -> mean 0.15
    - Chapter 4: Beta(1, 9) -> mean 0.10
    - Chapter 5: Beta(0.5, 9.5) -> mean 0.05
    """
    alpha_prior: float
    beta_prior: float
    max_skip_rate: float  # Hard cap to prevent degenerate behavior

    @property
    def prior_mean(self) -> float:
        return self.alpha_prior / (self.alpha_prior + self.beta_prior)


CHAPTER_SKIP_PRIORS = {
    1: BayesianSkipConfig(alpha_prior=3.0, beta_prior=7.0, max_skip_rate=0.50),
    2: BayesianSkipConfig(alpha_prior=2.0, beta_prior=8.0, max_skip_rate=0.35),
    3: BayesianSkipConfig(alpha_prior=1.5, beta_prior=8.5, max_skip_rate=0.25),
    4: BayesianSkipConfig(alpha_prior=1.0, beta_prior=9.0, max_skip_rate=0.15),
    5: BayesianSkipConfig(alpha_prior=0.5, beta_prior=9.5, max_skip_rate=0.08),
}


class BayesianSkipDecision:
    """Skip decision using Thompson Sampling with Beta posteriors.

    Replaces the hardcoded SkipDecision class from skip.py.

    The reward signal for skip/no-skip decisions:
    - If we skipped and the player re-engaged (sent another message): reward = 1
    - If we skipped and the player went silent for 24h+: reward = 0
    - If we didn't skip and player responded positively: reward = 1
    - If we didn't skip and player disengaged: reward = 0

    This naturally learns: should Nikita be more aloof or more responsive
    for THIS specific player?
    """

    def __init__(self, chapter: int, alpha: float = None, beta: float = None):
        config = CHAPTER_SKIP_PRIORS.get(chapter, CHAPTER_SKIP_PRIORS[1])
        self.alpha = alpha if alpha is not None else config.alpha_prior
        self.beta = beta if beta is not None else config.beta_prior
        self.max_skip_rate = config.max_skip_rate
        self.last_was_skipped = False

    def should_skip(self) -> bool:
        """Thompson Sample from the skip probability posterior.

        Draw theta ~ Beta(alpha, beta), then skip with probability theta.
        Apply hard cap and consecutive-skip reduction.
        """
        # Sample skip probability from posterior
        skip_prob = np.random.beta(self.alpha, self.beta)

        # Apply hard cap
        skip_prob = min(skip_prob, self.max_skip_rate)

        # Reduce probability of consecutive skips (same as current system)
        if self.last_was_skipped:
            skip_prob *= 0.5

        # Make the binary decision
        should_skip = np.random.random() < skip_prob
        self.last_was_skipped = should_skip
        return should_skip

    def update(self, skipped: bool, player_reengaged: bool) -> None:
        """Update posterior based on observed outcome.

        Args:
            skipped: Whether we skipped the last message
            player_reengaged: Whether the player sent another message
                              (within a reasonable timeframe)
        """
        if skipped:
            # We chose to skip — did it maintain engagement?
            if player_reengaged:
                self.alpha += 1  # Skipping was good (built anticipation)
            else:
                self.beta += 1   # Skipping was bad (player left)
        else:
            # We chose to respond — did it maintain engagement?
            if player_reengaged:
                self.beta += 1   # Not skipping was good (player liked response)
            else:
                self.alpha += 1  # Not skipping was bad (maybe too available?)

    def get_state(self) -> dict:
        """Return serializable state for database storage."""
        return {
            "alpha": self.alpha,
            "beta": self.beta,
            "posterior_mean": self.alpha / (self.alpha + self.beta),
            "posterior_variance": self.get_posterior_variance(),
        }

    def get_posterior_variance(self) -> float:
        a, b = self.alpha, self.beta
        return (a * b) / ((a + b) ** 2 * (a + b + 1))
```

### 4.3 How the Skip Rate Evolves Per Player

Consider two players in Chapter 1:

**Player A (prefers chase dynamics):**
- Sends message, Nikita skips → Player A sends another excited message (reward = 1 for skipping)
- After 30 interactions: alpha = 18, beta = 15 → posterior mean = 0.55
- Nikita learns: this player responds well to being kept waiting
- Skip rate settles around 40-50% (capped at max_skip_rate = 0.50)

**Player B (prefers consistent attention):**
- Sends message, Nikita skips → Player B goes silent for 2 days (reward = 0 for skipping)
- After 30 interactions: alpha = 5, beta = 28 → posterior mean = 0.15
- Nikita learns: this player needs reliability
- Skip rate settles around 10-15%

Both players started with the same prior Beta(3, 7), but their different response patterns led to completely different optimal strategies. This is impossible with hardcoded chapter-based rates.

---

## 5. Application to Response Timing

### 5.1 Current System Analysis

The current `timing.py` uses hardcoded ranges:

```python
# From nikita/agents/text/timing.py
TIMING_RANGES = {
    1: (600, 28800),     # 10min - 8h
    2: (300, 14400),     # 5min - 4h
    3: (300, 7200),      # 5min - 2h
    4: (300, 3600),      # 5min - 1h
    5: (300, 1800),      # 5min - 30min
}
```

The timing is sampled using a Gaussian distribution centered around the midpoint of the range, with random jitter. Every player in the same chapter gets the same distribution.

### 5.2 Posterior-Predictive Timing

Instead of hardcoded ranges, we can use Thompson Sampling to learn the optimal timing for each player. The approach discretizes timing into buckets and maintains a Dirichlet posterior over bucket preferences:

```python
from scipy import stats


class BayesianTimingDecision:
    """Response timing using Thompson Sampling with Dirichlet posteriors.

    Timing is discretized into buckets. A Dirichlet posterior tracks
    which bucket produces the best engagement for this player.

    Buckets for Chapter 1:
    0: immediate (5-10 min)   — "too eager"
    1: short (10-30 min)      — "interested"
    2: medium (30min - 2h)    — "has a life"
    3: long (2h - 6h)         — "busy"
    4: very long (6h - 12h)   — "playing hard to get"

    The Dirichlet prior encodes designer intuition about chapter behavior.
    """

    # Timing buckets: (min_seconds, max_seconds) per bucket
    TIMING_BUCKETS = [
        (300, 600),       # 5-10 min
        (600, 1800),      # 10-30 min
        (1800, 7200),     # 30min - 2h
        (7200, 21600),    # 2h - 6h
        (21600, 43200),   # 6h - 12h
    ]

    # Dirichlet priors per chapter (higher = preferred bucket)
    # Sum represents confidence; uniform = [1,1,1,1,1]
    CHAPTER_PRIORS = {
        1: np.array([0.5, 1.0, 2.0, 3.0, 2.5]),  # Prefer long delays
        2: np.array([1.0, 2.0, 3.0, 2.0, 1.0]),   # Prefer medium delays
        3: np.array([1.5, 3.0, 3.0, 1.5, 0.5]),   # Prefer short-medium
        4: np.array([2.0, 3.0, 2.0, 1.0, 0.5]),   # Prefer short
        5: np.array([3.0, 3.0, 1.0, 0.5, 0.5]),   # Prefer immediate-short
    }

    def __init__(self, chapter: int, dirichlet_params: np.ndarray = None):
        if dirichlet_params is not None:
            self.params = dirichlet_params.copy()
        else:
            self.params = self.CHAPTER_PRIORS.get(
                chapter, self.CHAPTER_PRIORS[1]
            ).copy()

    def select_timing(self) -> float:
        """Thompson Sample a timing bucket and return seconds within it.

        1. Sample probability vector from Dirichlet posterior
        2. Select bucket with highest sampled probability
        3. Uniformly sample a time within that bucket
        """
        # Sample from Dirichlet posterior
        probs = np.random.dirichlet(self.params)

        # Select best bucket
        bucket_idx = int(np.argmax(probs))

        # Sample uniformly within bucket
        min_sec, max_sec = self.TIMING_BUCKETS[bucket_idx]
        delay_seconds = np.random.uniform(min_sec, max_sec)

        return delay_seconds

    def update(self, bucket_used: int, engagement_reward: float) -> None:
        """Update Dirichlet posterior based on engagement outcome.

        Args:
            bucket_used: Which timing bucket was selected
            engagement_reward: 0-1 score based on player's response
        """
        # Only update the bucket that was used
        # Scale the update by reward (partial updates for partial rewards)
        self.params[bucket_used] += engagement_reward

    def get_state(self) -> dict:
        """Serializable state for database storage."""
        return {
            "dirichlet_params": self.params.tolist(),
            "expected_probs": (self.params / self.params.sum()).tolist(),
            "effective_observations": float(self.params.sum()),
        }
```

### 5.3 From Posterior-Predictive to Continuous Timing

For more natural timing (not bucketed), we can use a posterior-predictive approach with a Normal-Inverse-Gamma conjugate:

```python
class ContinuousTimingTS:
    """Continuous timing using Normal-Inverse-Gamma posterior.

    Instead of buckets, models the optimal delay as a continuous variable.
    The posterior over (mean_delay, variance_delay) is Normal-Inverse-Gamma.

    Posterior-predictive: sample a mean and variance from the posterior,
    then sample a delay from N(mean, variance).

    The reward signal comes from engagement: did the player respond
    positively after this delay?
    """

    def __init__(
        self,
        mu_0: float,      # Prior mean delay (seconds)
        kappa_0: float,    # Prior precision on mean
        alpha_0: float,    # Prior shape for variance
        beta_0: float,     # Prior scale for variance
    ):
        self.mu = mu_0
        self.kappa = kappa_0
        self.alpha = alpha_0
        self.beta = beta_0
        self.n_observations = 0

    def sample_delay(self) -> float:
        """Sample a delay from the posterior-predictive distribution.

        1. Sample variance: sigma^2 ~ InverseGamma(alpha, beta)
        2. Sample mean: mu ~ Normal(mu_0, sigma^2 / kappa)
        3. Sample delay: delay ~ Normal(mu, sigma^2)
        4. Clip to reasonable bounds
        """
        # Sample variance from Inverse-Gamma
        sigma_sq = 1.0 / np.random.gamma(self.alpha, 1.0 / self.beta)

        # Sample mean from conditional Normal
        mu_sample = np.random.normal(self.mu, np.sqrt(sigma_sq / self.kappa))

        # Sample delay from predictive
        delay = np.random.normal(mu_sample, np.sqrt(sigma_sq))

        # Clip to [5 min, 24h] and ensure positive
        return float(np.clip(delay, 300, 86400))

    def update(self, observed_delay: float, engagement_reward: float) -> None:
        """Bayesian update with observed (delay, reward) pair.

        We only update when engagement_reward > threshold, effectively
        learning the delay distribution that produces engagement.
        """
        if engagement_reward < 0.3:
            return  # Don't learn from clearly bad outcomes

        # Standard Normal-Inverse-Gamma Bayesian update
        self.n_observations += 1
        n = self.n_observations
        kappa_n = self.kappa + 1
        mu_n = (self.kappa * self.mu + observed_delay) / kappa_n
        alpha_n = self.alpha + 0.5
        beta_n = (
            self.beta
            + 0.5 * self.kappa * (observed_delay - self.mu) ** 2 / kappa_n
        )

        self.mu = mu_n
        self.kappa = kappa_n
        self.alpha = alpha_n
        self.beta = beta_n
```

---

## 6. Application to Event Generation

### 6.1 Current System: LLM-Generated Events

The current `event_generator.py` uses an LLM (Pydantic AI) to generate 3-5 daily life events for Nikita, distributed across work, social, and personal domains. Each event has emotional valence, arousal, and importance scores.

The problem: the LLM generates events based on a static prompt, with no feedback about which types of events the player finds engaging. The event distribution is the same for every player.

### 6.2 Thompson Sampling for Event Type Selection

Instead of letting the LLM freely choose event types, Thompson Sampling can learn which event categories each player responds to best:

```python
class BayesianEventSelector:
    """Selects event types using Thompson Sampling.

    Maintains a Beta posterior for each event category's engagement rate.
    The LLM still generates the event content, but the TYPE of event
    is chosen by Thompson Sampling based on learned preferences.

    Event categories from the life_simulation models:
    - work: career, meetings, deadlines, achievements
    - social: friends, parties, drama, gossip
    - personal: hobbies, self-care, existential thoughts, daily routine

    Within each category, event types (from DOMAIN_EVENT_TYPES):
    - work: promotion, conflict_with_boss, new_project, deadline_stress
    - social: friend_drama, party_invite, gossip, new_friend
    - personal: hobby_milestone, existential_crisis, self_care, nostalgia
    """

    def __init__(self, event_types: list[str], prior_alpha: float = 2.0, prior_beta: float = 2.0):
        """Initialize with symmetric priors for all event types.

        Beta(2, 2) is a slightly informative prior centered at 0.5,
        representing "we don't know if this event type is engaging."
        """
        self.event_types = event_types
        self.alpha = {et: prior_alpha for et in event_types}
        self.beta = {et: prior_beta for et in event_types}

    def select_events(self, n_events: int = 4) -> list[str]:
        """Select n event types for today using Thompson Sampling.

        Samples from each posterior, ranks, and picks the top n.
        This ensures diversity (different types each day) while
        favoring types the player enjoys.
        """
        # Sample engagement rate from each event type's posterior
        samples = {
            et: np.random.beta(self.alpha[et], self.beta[et])
            for et in self.event_types
        }

        # Sort by sampled engagement rate, pick top n
        sorted_types = sorted(samples, key=samples.get, reverse=True)
        return sorted_types[:n_events]

    def update(self, event_type: str, player_engaged: bool) -> None:
        """Update posterior based on whether player engaged with this event.

        Engagement signals:
        - Player asked about it ("How was your meeting?") -> engaged = True
        - Player showed emotional response -> engaged = True
        - Player ignored it completely -> engaged = False
        - Player changed topic immediately -> engaged = False
        """
        if player_engaged:
            self.alpha[event_type] += 1
        else:
            self.beta[event_type] += 1

    def get_top_preferences(self, n: int = 3) -> list[tuple[str, float]]:
        """Return the top n event types by posterior mean."""
        means = {
            et: self.alpha[et] / (self.alpha[et] + self.beta[et])
            for et in self.event_types
        }
        sorted_types = sorted(means.items(), key=lambda x: x[1], reverse=True)
        return sorted_types[:n]
```

### 6.3 Hierarchical Event Selection

For richer event generation, we can use a two-level hierarchy: first select the domain, then select the event type within that domain:

```python
class HierarchicalEventSelector:
    """Two-level Thompson Sampling for event generation.

    Level 1: Select domain (work / social / personal)
    Level 2: Select event type within domain

    This respects the constraint that events should be distributed
    across domains (a day with only work events feels unrealistic).
    """

    def __init__(self, domain_types: dict[str, list[str]]):
        """
        Args:
            domain_types: {"work": ["promotion", "deadline", ...],
                          "social": ["friend_drama", "party", ...],
                          "personal": ["hobby", "self_care", ...]}
        """
        # Level 1: Dirichlet over domains
        self.domain_names = list(domain_types.keys())
        self.domain_params = np.ones(len(self.domain_names)) * 3.0  # Symmetric

        # Level 2: Beta per event type within each domain
        self.type_alpha = {}
        self.type_beta = {}
        for domain, types in domain_types.items():
            for t in types:
                self.type_alpha[t] = 2.0
                self.type_beta[t] = 2.0

        self.domain_types = domain_types

    def select_daily_events(self, n_events: int = 4) -> list[tuple[str, str]]:
        """Select n (domain, event_type) pairs for today.

        1. Sample domain distribution from Dirichlet
        2. Allocate events across domains proportionally
        3. Within each domain, use Thompson Sampling to pick types
        """
        # Sample domain distribution
        domain_probs = np.random.dirichlet(self.domain_params)

        # Allocate events to domains (at least 1 per domain if n >= 3)
        allocations = np.round(domain_probs * n_events).astype(int)
        allocations = np.maximum(allocations, 1)  # Minimum 1 per domain
        while allocations.sum() > n_events:
            allocations[np.argmax(allocations)] -= 1
        while allocations.sum() < n_events:
            allocations[np.argmin(allocations)] += 1

        # For each domain, Thompson Sample event types
        events = []
        for i, domain in enumerate(self.domain_names):
            n_domain_events = allocations[i]
            types = self.domain_types[domain]

            # Sample from each type's posterior
            type_samples = {
                t: np.random.beta(self.type_alpha[t], self.type_beta[t])
                for t in types
            }

            # Pick top types for this domain
            sorted_types = sorted(type_samples, key=type_samples.get, reverse=True)
            for j in range(min(n_domain_events, len(sorted_types))):
                events.append((domain, sorted_types[j]))

        return events[:n_events]
```

---

## 7. Comparison with Alternative Algorithms

### 7.1 Epsilon-Greedy

**Algorithm:** With probability epsilon, choose a random arm. Otherwise, choose the arm with highest empirical mean.

```python
class EpsilonGreedy:
    def __init__(self, n_arms: int, epsilon: float = 0.1):
        self.n_arms = n_arms
        self.epsilon = epsilon
        self.counts = np.zeros(n_arms)
        self.rewards = np.zeros(n_arms)

    def select_arm(self) -> int:
        if np.random.random() < self.epsilon:
            return np.random.randint(self.n_arms)
        means = np.where(self.counts > 0, self.rewards / self.counts, 0.5)
        return int(np.argmax(means))

    def update(self, arm: int, reward: float) -> None:
        self.counts[arm] += 1
        self.rewards[arm] += reward
```

**Comparison with Thompson Sampling:**

| Criterion | Epsilon-Greedy | Thompson Sampling |
|---|---|---|
| Hyperparameters | epsilon (requires tuning) | None (prior is natural) |
| Regret bound | O(epsilon * T) (linear!) | O(sqrt(K * T * ln(T))) |
| Exploration targeting | Uniform random | Proportional to uncertainty |
| Converges to optimal? | No (keeps exploring at rate epsilon) | Yes (posterior concentrates) |
| Adaptability | Requires decaying epsilon schedule | Naturally adapts |
| Implementation complexity | Trivial | Trivial (for Beta-Bernoulli) |
| For Nikita | Bad: random exploration feels erratic | Good: smooth, personalized |

### 7.2 Upper Confidence Bound (UCB)

**Algorithm:** Choose the arm that maximizes: empirical mean + sqrt(2 * ln(t) / n_k), where t is the total round count and n_k is how many times arm k has been played.

```python
class UCB1:
    def __init__(self, n_arms: int):
        self.n_arms = n_arms
        self.counts = np.zeros(n_arms)
        self.rewards = np.zeros(n_arms)
        self.total_rounds = 0

    def select_arm(self) -> int:
        self.total_rounds += 1
        # Play each arm at least once
        for k in range(self.n_arms):
            if self.counts[k] == 0:
                return k
        means = self.rewards / self.counts
        ucb_values = means + np.sqrt(2 * np.log(self.total_rounds) / self.counts)
        return int(np.argmax(ucb_values))

    def update(self, arm: int, reward: float) -> None:
        self.counts[arm] += 1
        self.rewards[arm] += reward
```

**Comparison with Thompson Sampling:**

| Criterion | UCB1 | Thompson Sampling |
|---|---|---|
| Exploration strategy | Optimistic (upper bound) | Probabilistic (posterior sampling) |
| Regret bound | O(K * ln(T)) | O(sqrt(K * T * ln(T))) |
| Behavior | Deterministic (always picks same arm given same history) | Stochastic (natural randomness) |
| Batched decisions | Difficult to extend | Natural extension |
| Contextual extension | LinUCB (well-studied) | Linear TS (well-studied) |
| For Nikita | Decent but deterministic → predictable patterns | Better: stochastic → natural unpredictability |

**Key advantage of Thompson Sampling for Nikita:** Its inherent randomness creates natural behavioral variability. A deterministic policy (UCB) would always make the same decision given the same state, which could feel robotic. Thompson Sampling's stochasticity means Nikita might skip one day but respond the next, even in identical situations — more human-like.

### 7.3 Pure Exploitation (Current System)

**Algorithm:** Use the designer's best guess forever. No learning.

| Criterion | Pure Exploitation | Thompson Sampling |
|---|---|---|
| Initial performance | Depends entirely on designer's guess | Same initial performance (prior = guess) |
| Long-term performance | Never improves | Converges to optimal |
| Personalization | None | Per-player adaptation |
| Engineering cost | Zero (already implemented) | Moderate (new module) |
| Risk | High if guess is wrong | Low (self-correcting) |
| For Nikita | Current system — acceptable but not adaptive | Goal system — adaptive and personalized |

---

## 8. Advanced Topics

### 8.1 Thompson Sampling with Gaussian Rewards

For metrics that are continuous (not binary), the Beta-Bernoulli model doesn't apply. For example, the composite relationship score change after a message is a continuous value in [-10, +10].

With Gaussian rewards and a Normal-Inverse-Gamma prior:

```python
class GaussianThompsonSampling:
    """Thompson Sampling for Gaussian-distributed rewards.

    Uses Normal-Inverse-Gamma conjugate prior:
    - mu | sigma^2 ~ Normal(mu_0, sigma^2 / kappa_0)
    - sigma^2 ~ InverseGamma(alpha_0, beta_0)

    Useful for learning optimal actions when the reward is continuous
    (e.g., relationship score change after a message).
    """

    def __init__(
        self,
        n_arms: int,
        mu_0: float = 0.0,
        kappa_0: float = 1.0,
        alpha_0: float = 2.0,
        beta_0: float = 1.0,
    ):
        self.n_arms = n_arms
        # Per-arm posterior parameters
        self.mu = np.full(n_arms, mu_0)
        self.kappa = np.full(n_arms, kappa_0)
        self.alpha = np.full(n_arms, alpha_0)
        self.beta = np.full(n_arms, beta_0)

    def select_arm(self) -> int:
        """Sample from each arm's posterior and select the best."""
        samples = np.zeros(self.n_arms)
        for k in range(self.n_arms):
            # Sample variance
            sigma_sq = 1.0 / np.random.gamma(self.alpha[k], 1.0 / self.beta[k])
            # Sample mean
            samples[k] = np.random.normal(
                self.mu[k], np.sqrt(sigma_sq / self.kappa[k])
            )
        return int(np.argmax(samples))

    def update(self, arm: int, reward: float) -> None:
        """Update Normal-Inverse-Gamma posterior with observed reward."""
        k = arm
        kappa_new = self.kappa[k] + 1
        mu_new = (self.kappa[k] * self.mu[k] + reward) / kappa_new
        alpha_new = self.alpha[k] + 0.5
        beta_new = self.beta[k] + 0.5 * self.kappa[k] * (reward - self.mu[k]) ** 2 / kappa_new

        self.mu[k] = mu_new
        self.kappa[k] = kappa_new
        self.alpha[k] = alpha_new
        self.beta[k] = beta_new
```

### 8.2 Thompson Sampling for Vice Discovery

The vice system (8 categories) is a natural fit for Thompson Sampling. Currently, the `ViceAnalyzer` uses an LLM to detect vice signals in every message. With Thompson Sampling, the system can learn which vices to probe for, reducing unnecessary LLM calls:

```python
class BayesianViceDiscovery:
    """Learn player's vice preferences using Thompson Sampling.

    Instead of analyzing every message for all 8 vice categories,
    focus analysis on categories most likely to be relevant.

    Vice categories:
    - intellectual_dominance, risk_taking, substances, sexuality,
    - emotional_intensity, rule_breaking, dark_humor, vulnerability
    """

    VICE_CATEGORIES = [
        "intellectual_dominance", "risk_taking", "substances", "sexuality",
        "emotional_intensity", "rule_breaking", "dark_humor", "vulnerability",
    ]

    def __init__(self):
        # Dirichlet prior over vice preference distribution
        # Start uniform: equal probability for all vices
        self.dirichlet_params = np.ones(len(self.VICE_CATEGORIES)) * 2.0

    def get_top_vices(self, n: int = 3) -> list[str]:
        """Thompson Sample the most likely vice categories to probe.

        Returns the top-n vices by sampled probability.
        Used to focus LLM analysis on promising categories.
        """
        probs = np.random.dirichlet(self.dirichlet_params)
        top_indices = np.argsort(probs)[-n:][::-1]
        return [self.VICE_CATEGORIES[i] for i in top_indices]

    def update(self, detected_vice: str, signal_strength: float) -> None:
        """Update Dirichlet posterior when a vice signal is detected.

        Args:
            detected_vice: The vice category that was detected
            signal_strength: How strong the signal was (0-1)
        """
        idx = self.VICE_CATEGORIES.index(detected_vice)
        self.dirichlet_params[idx] += signal_strength

    def get_profile(self) -> dict[str, float]:
        """Return normalized vice preference profile."""
        total = self.dirichlet_params.sum()
        return {
            vice: float(self.dirichlet_params[i] / total)
            for i, vice in enumerate(self.VICE_CATEGORIES)
        }
```

### 8.3 Bayesian Surprise as a Trigger

Thompson Sampling naturally produces a measure of surprise: the probability that an observed outcome is unlikely under the current posterior. This can trigger special game events:

```python
def compute_bayesian_surprise(
    alpha: float,
    beta: float,
    observed_outcome: bool,
) -> float:
    """Compute how surprising an outcome is given the posterior.

    Surprise = -log P(outcome | posterior)
    High surprise = the observation contradicts our beliefs

    This is the pointwise KL divergence, also called "surprisal" or
    "self-information."
    """
    posterior_mean = alpha / (alpha + beta)

    if observed_outcome:
        prob = posterior_mean
    else:
        prob = 1 - posterior_mean

    # Avoid log(0)
    prob = max(prob, 1e-10)

    surprise = -np.log(prob)
    return surprise


def should_trigger_conflict(
    surprise: float,
    surprise_threshold: float = 2.0,  # ~e^-2 = 0.135 probability
) -> bool:
    """Trigger a conflict event when behavior is highly surprising.

    If a player who is usually reliable suddenly goes silent for days,
    the surprise value will be high, triggering Nikita to initiate
    a conflict about feeling neglected.

    surprise > 2.0 corresponds to P(observation) < 13.5%
    surprise > 3.0 corresponds to P(observation) < 5%
    """
    return surprise > surprise_threshold
```

### 8.4 Computational Cost Analysis

One of the core motivations for the Bayesian approach is cost. Here is a precise comparison:

```
Beta distribution update:
  - 2 additions (alpha += 1, beta += 1)
  - Time: ~100 nanoseconds
  - Memory: 16 bytes per arm (two float64 values)
  - Cost: $0

Dirichlet update:
  - 1 addition per category
  - Time: ~100 nanoseconds
  - Memory: 8 bytes per category
  - Cost: $0

Thompson Sample (Beta):
  - 1 random number generation per arm
  - Time: ~1 microsecond for 10 arms
  - Memory: 0 (in-place)
  - Cost: $0

LLM call (current system):
  - API call to Claude Sonnet 4.5
  - Input: ~500 tokens, Output: ~200 tokens
  - Time: 500-2000ms
  - Memory: transient
  - Cost: ~$0.002 per call ($3/1M input + $15/1M output)

Per player per day (assuming 15 messages):
  Current (all LLM):     15 calls * $0.002 = $0.030/day
  Bayesian (90% saved):  1.5 calls * $0.002 = $0.003/day
  Savings:               $0.027/day per player

At 1000 users: $27/day = $810/month savings
At 10000 users: $270/day = $8,100/month savings
```

---

## 9. Implementation Patterns in NumPy

### 9.1 Vectorized Thompson Sampling for Multiple Players

In a production system, we update many players' posteriors simultaneously:

```python
class VectorizedBetaTS:
    """Vectorized Thompson Sampling for batch updates across players.

    Instead of one object per player, maintains arrays of parameters
    for efficient batch operations.
    """

    def __init__(self, n_players: int, n_arms: int, prior_alpha: float = 1.0, prior_beta: float = 1.0):
        self.n_players = n_players
        self.n_arms = n_arms
        # Shape: (n_players, n_arms)
        self.alpha = np.full((n_players, n_arms), prior_alpha)
        self.beta = np.full((n_players, n_arms), prior_beta)

    def select_arms(self) -> np.ndarray:
        """Thompson Sample for all players simultaneously.

        Returns: array of shape (n_players,) with selected arm indices.
        """
        # Sample from Beta posterior for all players and arms at once
        samples = np.random.beta(self.alpha, self.beta)  # (n_players, n_arms)
        return np.argmax(samples, axis=1)                  # (n_players,)

    def batch_update(
        self,
        player_indices: np.ndarray,
        arm_indices: np.ndarray,
        rewards: np.ndarray,
    ) -> None:
        """Update posteriors for a batch of (player, arm, reward) observations."""
        # Fancy indexing for vectorized update
        successes = rewards > 0
        failures = ~successes

        self.alpha[player_indices[successes], arm_indices[successes]] += rewards[successes]
        self.beta[player_indices[failures], arm_indices[failures]] += (1 - rewards[failures])
```

### 9.2 Serialization for Database Storage

Thompson Sampling state needs to persist in Supabase:

```python
import json
from datetime import datetime


def serialize_ts_state(
    player_id: str,
    system: str,  # "skip", "timing", "events", "vice"
    alpha: np.ndarray | float,
    beta: np.ndarray | float,
    metadata: dict = None,
) -> dict:
    """Serialize Thompson Sampling state for JSONB storage in Supabase.

    Target table: bayesian_states
    Column: state_json (JSONB)

    The state is minimal: just the posterior parameters.
    Everything else (posterior mean, variance, etc.) is derived.
    """
    state = {
        "system": system,
        "version": 1,
        "updated_at": datetime.utcnow().isoformat(),
        "params": {
            "alpha": alpha.tolist() if isinstance(alpha, np.ndarray) else alpha,
            "beta": beta.tolist() if isinstance(beta, np.ndarray) else beta,
        },
    }
    if metadata:
        state["metadata"] = metadata
    return state


def deserialize_ts_state(state_json: dict) -> tuple:
    """Deserialize Thompson Sampling state from JSONB.

    Returns (alpha, beta) as numpy arrays or floats.
    """
    params = state_json["params"]
    alpha = np.array(params["alpha"]) if isinstance(params["alpha"], list) else params["alpha"]
    beta = np.array(params["beta"]) if isinstance(params["beta"], list) else params["beta"]
    return alpha, beta
```

### 9.3 Complete Example: Skip Rate in the Pipeline

Putting it all together — how Thompson Sampling integrates into the existing 9-stage pipeline:

```python
async def bayesian_skip_decision(
    user_id: str,
    chapter: int,
    db_session,
) -> tuple[bool, dict]:
    """Make a Bayesian skip decision within the message pipeline.

    This replaces SkipDecision.should_skip() in the pipeline.

    Returns:
        (should_skip: bool, updated_state: dict)
    """
    # 1. Load posterior from database
    row = await db_session.execute(
        "SELECT state_json FROM bayesian_states "
        "WHERE user_id = :uid AND system = 'skip'",
        {"uid": user_id}
    )
    existing_state = row.scalar_one_or_none()

    if existing_state:
        alpha, beta = deserialize_ts_state(existing_state)
        skip_decision = BayesianSkipDecision(chapter, alpha=alpha, beta=beta)
    else:
        skip_decision = BayesianSkipDecision(chapter)

    # 2. Make the decision via Thompson Sampling
    should_skip = skip_decision.should_skip()

    # 3. Return decision and state (state saved after observing outcome)
    return should_skip, skip_decision.get_state()
```

---

## 10. Theoretical Guarantees and Practical Bounds

### 10.1 Regret Bounds for Beta-Bernoulli Thompson Sampling

**Theorem (Agrawal & Goyal, 2012):** For a K-armed Bernoulli bandit, Thompson Sampling with Beta(1,1) priors achieves:

```
E[Regret(T)] <= (1 + epsilon) * sum_{k: mu_k < mu*} [
    (mu* - mu_k) * ln(T) / KL(mu_k, mu*)
] + C(epsilon, K)
```

where KL(p, q) = p * ln(p/q) + (1-p) * ln((1-p)/(1-q)) is the KL divergence between Bernoulli(p) and Bernoulli(q).

This matches the Lai-Robbins lower bound, making Thompson Sampling **asymptotically optimal**.

### 10.2 Finite-Time Bounds

For practical purposes, the finite-time regret bound is more relevant:

```
E[Regret(T)] <= O(sqrt(K * T * ln(K)))
```

For Nikita's skip rate system with K = 5 options and T = 100 messages (first month):

```
Regret <= C * sqrt(5 * 100 * ln(5)) ~ C * sqrt(804) ~ 28.4 * C

With C ~ 1 (typical for well-tuned priors):
Expected regret ~ 28.4 units over 100 rounds
Average per-round regret ~ 0.284 (out of max 1.0)
```

This means Thompson Sampling is performing within 28.4% of optimal after just 100 interactions. For a game that spans months, this convergence is more than adequate.

### 10.3 Prior Sensitivity

**How much does the prior matter?**

For Beta-Bernoulli Thompson Sampling, the prior's impact diminishes as:

```
Prior influence ~ alpha_0 + beta_0 (prior strength)
Data influence ~ n (number of observations)

Prior dominates when: n < alpha_0 + beta_0
Data dominates when: n >> alpha_0 + beta_0
```

With our recommended priors (alpha + beta = 10 for Chapter 1), the prior dominates for roughly the first 10 interactions, then data takes over. This is by design: the first 10 messages should feel consistent with the game design, then personalization kicks in.

**Robustness to misspecified priors:** Even if the prior is significantly wrong, Thompson Sampling self-corrects within O(prior_strength) additional observations. With prior strength 10, a badly wrong prior adds at most ~10 rounds of extra regret — less than a day of play.

### 10.4 When Thompson Sampling Fails

Thompson Sampling is not a silver bullet. Known failure modes:

**1. Delayed feedback:** If the reward signal comes hours after the action (e.g., "did the player come back after being skipped?"), the posterior updates are delayed and may be noisy.

**Mitigation for Nikita:** Use a reasonable timeout (e.g., 24h) and treat no-response as negative signal. Accept slightly delayed learning.

**2. Non-stationary rewards:** If the optimal action changes over time (player preferences evolve), standard Thompson Sampling adapts slowly because old evidence weighs equally with new evidence.

**Mitigation for Nikita:** Use discounted Thompson Sampling (Section 3.4) with gamma = 0.98.

**3. Partial observability:** We only observe the reward for the chosen action, never the counterfactual ("what would have happened if we hadn't skipped?").

**Mitigation for Nikita:** This is inherent to the bandit setting and cannot be eliminated. Thompson Sampling handles it optimally by construction.

**4. Reward signal quality:** If the engagement reward is noisy or poorly defined, Thompson Sampling will converge to the action that maximizes the noisy reward, which may not align with the true design objective.

**Mitigation for Nikita:** Carefully design the reward signal. Use composite metrics (not just "did they respond" but also "response speed," "response length," "emotional positivity") to create a more robust signal.

---

## 11. Thompson Sampling vs. the Psyche Agent Tier System

### 11.1 Mapping to the Three-Tier Architecture

The Psyche Agent proposal (doc 15 of the previous brainstorm cycle) defined a three-tier system:

```
Tier 1: Cached psyche state (90% of messages)  - 0ms,  $0
Tier 2: Quick Sonnet analysis (8%)              - 300ms, ~500 tokens
Tier 3: Deep Opus analysis (2%)                 - 3s,    ~3000 tokens
```

Thompson Sampling maps directly onto **Tier 1**: it is the mathematical engine that produces decisions from cached state, at zero latency and zero cost. The posterior parameters (alpha, beta values) ARE the cached psyche state.

```
Tier 1 (Bayesian):
  - Read posterior from DB
  - Thompson Sample an action
  - Apply action (skip/respond, timing, event selection)
  - Time: <1ms, Cost: $0

Tier 2 (Quick inference):
  - Only triggered when Bayesian surprise is high (Section 8.3)
  - Uses LLM to re-evaluate the situation
  - Updates posterior with LLM-derived signal

Tier 3 (Deep analysis):
  - Only triggered for genuine novelty (new topics, emotional crises)
  - Full Opus analysis of relationship dynamics
  - May reset or significantly update priors
```

### 11.2 When to Escalate from Thompson Sampling to LLM

The escalation decision itself can be Bayesian:

```python
def should_escalate_to_llm(
    surprise: float,
    posterior_entropy: float,
    messages_since_last_llm: int,
) -> str:
    """Decide whether to escalate from Bayesian to LLM processing.

    Returns: "tier1" (Bayesian only), "tier2" (quick LLM), or "tier3" (deep LLM)
    """
    # High surprise = unexpected player behavior
    if surprise > 3.0:  # P(observation) < 5%
        return "tier3"  # Deep analysis needed

    if surprise > 2.0:  # P(observation) < 13.5%
        return "tier2"  # Quick check

    # High entropy = uncertainty is too high to trust Bayesian alone
    if posterior_entropy > 0.9:  # Near-maximum entropy
        return "tier2"

    # Periodic LLM check (every ~10 messages) to validate Bayesian model
    if messages_since_last_llm > 10:
        return "tier2"

    return "tier1"
```

---

## 12. Summary and Key Takeaways

### 12.1 Core Algorithms for Nikita

| System | Thompson Sampling Variant | Prior | Arms/Categories |
|---|---|---|---|
| Skip rate | Beta-Bernoulli TS | Per-chapter Beta(a, b) | 2 (skip/respond) |
| Response timing | Dirichlet TS (bucketed) | Per-chapter Dirichlet | 5 timing buckets |
| Event generation | Hierarchical Dirichlet + Beta TS | Symmetric priors | 3 domains x 4 types |
| Vice discovery | Dirichlet TS | Uniform Dirichlet(2, ..., 2) | 8 vice categories |
| Emotional tone | Linear contextual TS | N(0, I) prior on weights | Context-dependent |

### 12.2 What Thompson Sampling Gives Nikita

1. **Personalization without tokens**: Each player gets a unique behavioral profile, learned from their interaction history, at zero LLM cost
2. **Graceful cold start**: Designer priors provide sensible behavior from the first message; data refines from there
3. **Natural unpredictability**: Stochastic sampling creates human-like behavioral variance
4. **Self-correcting**: Bad decisions automatically trigger more exploration, which discovers better strategies
5. **Computationally trivial**: Microsecond updates, bytes of storage per player

### 12.3 What Thompson Sampling Cannot Do

1. **Understand language**: It learns from aggregate engagement signals, not from understanding what the player said. LLM calls are still needed for language comprehension
2. **Handle novelty**: Genuinely new situations (player discusses a topic never seen before) have no Thompson Sampling analog — escalation to LLM is required
3. **Replace emotional modeling**: Thompson Sampling optimizes decisions but doesn't model internal emotional states. The DBN (doc 07) handles that
4. **Guarantee safety**: Thompson Sampling optimizes engagement, which could potentially optimize for psychologically unhealthy patterns. Ethical guardrails must operate independently

### 12.4 Key References

1. Thompson, W.R. (1933). "On the Likelihood that One Unknown Probability Exceeds Another in View of the Evidence of Two Samples." Biometrika.
2. Chapelle, O. and Li, L. (2011). "An Empirical Evaluation of Thompson Sampling." NeurIPS.
3. Agrawal, S. and Goyal, N. (2012). "Analysis of Thompson Sampling for the Multi-Armed Bandit Problem." COLT.
4. Agrawal, S. and Goyal, N. (2013). "Thompson Sampling for Contextual Bandits with Linear Payoffs." ICML.
5. Russo, D. et al. (2018). "A Tutorial on Thompson Sampling." Foundations and Trends in Machine Learning.
6. Kaufmann, E. et al. (2012). "On Bayesian Upper Confidence Bounds for Bandit Problems." AISTATS.

---

**Cross-References:**
- Doc 01: Beta Distribution Fundamentals (prior/posterior mechanics)
- Doc 02: Conjugate Priors (why Beta-Bernoulli is computationally free)
- Doc 07: Bayesian Networks (for the state model Thompson Sampling acts upon)
- Doc 08: Behavioral Psychology (reward signal design)
- Doc 14: Event Generation ideas (direct application of Section 6)
- Doc 15: Integration Architecture (how TS fits the pipeline)
- Doc 18: Vice Discovery (direct application of Section 8.2)

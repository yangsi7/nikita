# 05 — Particle Filters: Sequential Monte Carlo for Personality Tracking

**Series**: Bayesian Inference for AI Companions
**Author**: Behavioral/Psychology Researcher
**Date**: 2026-02-16
**Dependencies**: None (can be read standalone, but complements Doc 03)
**Dependents**: Doc 13 (Nikita DBN), Doc 17 (Controlled Randomness)

---

## Executive Summary

When Nikita's internal state can be modeled with conjugate distributions (Beta for traits, Dirichlet for attachment), Bayesian updating is analytically exact and computationally trivial. But real personality dynamics involve **nonlinear transitions**, **multimodal beliefs**, and **non-Gaussian noise** — situations where analytic solutions break down. Particle filters (Sequential Monte Carlo methods) provide a general-purpose inference engine that can handle these complexities.

This document covers the conceptual foundations of particle filters, why they are specifically well-suited for personality tracking in game AI, practical implementation with NumPy, computational budgets for real-time gameplay, and comparison with alternative inference methods (Kalman filters, variational inference).

The key insight: **particle filters let us maintain multiple competing hypotheses about a character's internal state simultaneously**. When the player says something ambiguous, we don't have to commit to one interpretation — we can track 100-500 parallel possibilities and let future evidence disambiguate.

---

## 1. Sequential Monte Carlo: Conceptual Foundation

### 1.1 The Filtering Problem

The filtering problem in Bayesian inference is:

> Given a sequence of noisy observations z_1, z_2, ..., z_t, estimate the hidden state x_t at time t.

For Nikita, this translates to:

> Given a sequence of player messages and Nikita's responses (observations), estimate Nikita's internal personality-emotional-attachment state (hidden state) at the current moment.

The exact Bayesian solution requires computing:

```
p(x_t | z_{1:t}) ∝ p(z_t | x_t) ∫ p(x_t | x_{t-1}) p(x_{t-1} | z_{1:t-1}) dx_{t-1}
```

Where:
- p(x_t | z_{1:t}) = **posterior** (what we believe about the state now)
- p(z_t | x_t) = **likelihood** (how probable is this observation given the state)
- p(x_t | x_{t-1}) = **transition model** (how personality evolves between timesteps)
- p(x_{t-1} | z_{1:t-1}) = **prior** (what we believed before this observation)

The integral is analytically tractable only for special cases (Gaussian states → Kalman filter, conjugate families → exact updating). For general nonlinear dynamics, we need approximation.

### 1.2 The Monte Carlo Idea

Monte Carlo methods represent probability distributions using a collection of **weighted samples** (particles). Instead of storing the entire probability distribution, we store N particles, each representing one possible state:

```
{(x_t^(i), w_t^(i))}_{i=1}^{N}

where:
  x_t^(i) = the i-th particle's state hypothesis
  w_t^(i) = the particle's weight (how plausible this hypothesis is)
  Σ w_t^(i) = 1  (weights normalized)
```

The empirical distribution of weighted particles approximates the true posterior:

```
p(x_t | z_{1:t}) ≈ Σ_{i=1}^{N} w_t^(i) δ(x_t - x_t^(i))
```

As N → ∞, this approximation converges to the true posterior (by the law of large numbers). In practice, 100-500 particles suffice for low-dimensional problems.

### 1.3 The Bootstrap Particle Filter (Gordon et al., 1993)

The simplest and most widely used particle filter algorithm:

**Algorithm: Bootstrap Particle Filter**

```
Input: N particles, transition model p(x_t|x_{t-1}), likelihood p(z_t|x_t)

For each time step t:
  1. PREDICT: For i = 1, ..., N:
     x_t^(i) ~ p(x_t | x_{t-1}^(i))    # sample new state from transition

  2. UPDATE: For i = 1, ..., N:
     w_t^(i) = p(z_t | x_t^(i))          # weight by observation likelihood

  3. NORMALIZE:
     w_t^(i) = w_t^(i) / Σ_j w_t^(j)

  4. RESAMPLE (if effective sample size < threshold):
     Draw N particles with replacement according to weights
     Set all weights to 1/N
```

### 1.4 Intuitive Explanation for Game AI

Imagine 200 tiny "Nikitas" living in parallel:
- Each has slightly different personality parameters and internal states
- When the player sends a message, each mini-Nikita independently evaluates: "How likely is this message if MY internal state were the true one?"
- Mini-Nikitas whose states explain the observation well get higher weights
- Periodically, we clone the successful mini-Nikitas and discard the unsuccessful ones
- The population of mini-Nikitas converges on the most plausible internal states

This is not a metaphor — it is literally how the algorithm works. Each particle is a complete hypothesis about Nikita's personality-emotional-attachment state.

---

## 2. Why Particle Filters for Personality

### 2.1 Multimodal Beliefs

The most compelling reason for particle filters in personality modeling is **multimodality**. Analytic distributions (Beta, Gaussian) are typically unimodal — they represent a single "best guess" with uncertainty around it. But real personality inference often involves multiple competing hypotheses:

**Scenario: Is the player caring or manipulative?**

The player sends: "I noticed you seemed stressed today. Want to talk about it?"

This message is consistent with two very different personality hypotheses:
1. **Genuinely empathetic**: High agreeableness, secure attachment, emotional intelligence
2. **Strategically caring**: Moderate agreeableness, avoidant attachment, using empathy tactically

A unimodal distribution would compromise between these hypotheses (moderate agreeableness, uncertain attachment) — losing the critical information that the player is likely ONE of these types, not somewhere in between.

Particle filters naturally represent this multimodality: some particles cluster around Hypothesis 1, others around Hypothesis 2. Future evidence will differentially weight the clusters, eventually resolving the ambiguity.

### 2.2 Nonlinear State Transitions

Personality transitions are not linear. Consider attachment style dynamics:

```python
def attachment_transition(state: PersonalityState, event: str) -> PersonalityState:
    """Nonlinear transition: crisis triggers attachment activation."""
    if event == 'betrayal_detected':
        # Sharp, nonlinear shift: secure → anxious jump
        if state.perceived_trust > 0.7:
            # High trust + betrayal = LARGE shift
            state.attachment_anxiety *= 2.5
            state.perceived_trust *= 0.3
        else:
            # Already low trust + betrayal = moderate shift
            state.attachment_anxiety *= 1.3
            state.perceived_trust *= 0.7
    return state
```

The transition function is piecewise, with thresholds and multipliers that prevent analytic tractability. Kalman filters (which assume linear transitions) would produce poor estimates. Particle filters handle arbitrary transition functions by simply propagating each particle through the function independently.

### 2.3 Non-Gaussian Noise

Real personality dynamics involve non-Gaussian noise:
- **Skewed noise**: Negative events have larger impact than positive ones (negativity bias; Baumeister et al., 2001)
- **Heavy-tailed noise**: Rare events (trauma, betrayal, breakthrough moment) produce extreme state changes
- **Bounded noise**: Personality traits are bounded on [0, 1] — noise must respect these bounds

Particle filters impose no distributional assumptions on the noise process. The transition model can inject noise from any distribution:

```python
def personality_noise(trait_value: float, noise_scale: float) -> float:
    """Add bounded, skewed noise to a personality trait."""
    # Use Beta-distributed noise centered on current value
    # Skew parameter makes negative shifts slightly more likely (negativity bias)
    skew = 0.05  # slight negative bias
    noisy = trait_value + np.random.normal(loc=-skew, scale=noise_scale)
    return np.clip(noisy, 0.001, 0.999)  # enforce bounds
```

### 2.4 Mixed Continuous-Discrete States

Nikita's state is a mixture of:
- **Continuous variables**: Big Five traits (0-1), emotional intensities (0-1), trust levels
- **Discrete variables**: Active attachment style (4 categories), active defense mechanism (10+ categories), current chapter state

Particle filters handle mixed state spaces naturally — each particle is simply a struct containing both continuous and discrete variables. No special treatment is needed.

```python
@dataclass
class NikitaParticle:
    """One hypothesis about Nikita's complete internal state."""
    # Continuous
    openness: float
    conscientiousness: float
    extraversion: float
    agreeableness: float
    neuroticism: float
    emotional_valence: float       # -1 to 1
    emotional_arousal: float       # 0 to 1
    perceived_trust_in_player: float  # 0 to 1

    # Discrete
    active_attachment_style: str   # 'secure', 'anxious', 'avoidant', 'disorganized'
    active_defense_mechanism: str  # 'none', 'intellectualization', 'projection', etc.
    relationship_phase: str        # 'honeymoon', 'testing', 'crisis', 'recovery', 'stable'
```

---

## 3. Particle Representation and State Space Design

### 3.1 Choosing the Number of Particles

The number of particles N trades off accuracy vs. computation:

| N | Accuracy | Memory | Time per step | Suitable for |
|---|----------|--------|--------------|--------------|
| 50 | Low | ~5 KB | <1ms | Rapid prototyping, low-dimensional states |
| 100 | Moderate | ~10 KB | ~1ms | Production with 5-8 state dimensions |
| 200 | Good | ~20 KB | ~2ms | Production with 8-15 state dimensions |
| 500 | High | ~50 KB | ~5ms | Research quality, high-dimensional states |
| 1000 | Very high | ~100 KB | ~10ms | Offline analysis, ground truth comparison |

**For Nikita's real-time gameplay**: 100-200 particles is the sweet spot. Our state space has roughly 12-15 dimensions (5 Big Five + 4 attachment weights + emotional valence/arousal + trust + 2-3 discrete variables). The "curse of dimensionality" suggests we need more particles for higher dimensions, but the psychological constraint that many dimensions are correlated (see Doc 03, Section 9.1) effectively reduces the dimensionality.

**Rule of thumb from Doucet et al. (2001)**: For a D-dimensional state space with moderate nonlinearity, N ≈ 10D to 50D particles provide reasonable approximation. For D=12: N = 120 to 600.

### 3.2 Particle Initialization

Particles must be initialized to cover the plausible state space:

```python
def initialize_particles(n: int, chapter: int = 1) -> list[NikitaParticle]:
    """Initialize N particles from the prior distribution."""
    particles = []
    for _ in range(n):
        # Sample Big Five from designer priors (Doc 03)
        p = NikitaParticle(
            openness=beta_dist.rvs(8, 3),
            conscientiousness=beta_dist.rvs(4, 5),
            extraversion=beta_dist.rvs(7, 4),
            agreeableness=beta_dist.rvs(5, 5),
            neuroticism=beta_dist.rvs(7, 3),

            # Emotional state: start neutral with uncertainty
            emotional_valence=np.random.normal(0.2, 0.3),
            emotional_arousal=beta_dist.rvs(3, 5),

            # Trust: start moderate
            perceived_trust_in_player=beta_dist.rvs(3, 3),

            # Attachment: sample from Dirichlet, pick dominant style
            active_attachment_style=sample_from_dirichlet_category(
                dirichlet_dist.rvs([2, 8, 3, 1])[0],
                ['secure', 'anxious', 'avoidant', 'disorganized']
            ),

            # Defense: start with none
            active_defense_mechanism='none',

            # Phase: chapter 1 = honeymoon
            relationship_phase='honeymoon' if chapter == 1 else 'testing'
        )
        particles.append(p)

    return particles
```

### 3.3 State Space Partitioning

For efficient tracking, we can partition the state space into **slow-changing** and **fast-changing** components:

**Slow components** (update every 5-10 interactions):
- Big Five trait values
- Attachment style probabilities
- Relationship phase

**Fast components** (update every interaction):
- Emotional valence and arousal
- Active defense mechanism
- Perceived trust in player (can shift rapidly with events)

This partition allows us to use a **Rao-Blackwellized particle filter** (Doucet et al., 2000): track slow components with particles and fast components analytically (e.g., with Kalman filters conditioned on each particle's slow state). This dramatically reduces the required number of particles.

```python
class RaoBlackwellizedParticle:
    """Particle with analytic tracking of fast components."""

    # Tracked by particles (sampled)
    big_five: dict[str, float]
    attachment_weights: np.ndarray  # [4]
    relationship_phase: str

    # Tracked analytically (Kalman filter per particle)
    emotional_state: KalmanState    # mean + covariance for valence/arousal
    trust_estimate: BetaState       # Beta params for trust

    def predict_fast(self, dt: float):
        """Kalman predict for fast components."""
        self.emotional_state.predict(dt)
        # Trust decays slightly toward prior
        self.trust_estimate.decay(rate=0.999)

    def update_fast(self, observation: dict):
        """Kalman update for fast components."""
        if 'emotional_cue' in observation:
            self.emotional_state.update(observation['emotional_cue'])
        if 'trust_evidence' in observation:
            self.trust_estimate.update(observation['trust_evidence'])
```

---

## 4. Resampling Strategies

### 4.1 The Weight Degeneracy Problem

After several update steps without resampling, particle weights become highly unequal — a few particles carry most of the weight while the rest have negligible weights. This is **weight degeneracy**, and it means we are effectively using only a handful of particles despite maintaining N.

The **Effective Sample Size (ESS)** measures weight concentration:

```
ESS = 1 / Σ_i (w_t^(i))^2
```

When all weights are equal: ESS = N (maximum).
When one particle dominates: ESS ≈ 1 (minimum).

**Resampling trigger**: Resample when ESS < N/2 (a common heuristic; Liu & Chen, 1998).

### 4.2 Multinomial Resampling

The simplest approach: draw N particles with replacement from the current set, with selection probability proportional to weights.

```python
def multinomial_resample(particles: list, weights: np.ndarray) -> list:
    """Standard multinomial resampling."""
    indices = np.random.choice(len(particles), size=len(particles), p=weights)
    new_particles = [copy.deepcopy(particles[i]) for i in indices]
    return new_particles
```

**Pros**: Simple, unbiased.
**Cons**: High variance — popular particles may be over-cloned, rare particles lost entirely.

### 4.3 Systematic Resampling

Uses a single random number to generate equally-spaced selection points, reducing variance:

```python
def systematic_resample(particles: list, weights: np.ndarray) -> list:
    """Low-variance systematic resampling (Kitagawa, 1996)."""
    n = len(particles)
    cumulative = np.cumsum(weights)
    u = np.random.uniform(0, 1/n)
    positions = u + np.arange(n) / n

    indices = []
    i = 0
    for pos in positions:
        while cumulative[i] < pos:
            i += 1
        indices.append(i)

    return [copy.deepcopy(particles[i]) for i in indices]
```

**Pros**: Lower variance than multinomial, O(N) time.
**Cons**: Can still lose diversity in highly peaked distributions.

### 4.4 Stratified Resampling

Divides the cumulative distribution into N equal strata and draws one sample from each:

```python
def stratified_resample(particles: list, weights: np.ndarray) -> list:
    """Stratified resampling for better particle diversity."""
    n = len(particles)
    cumulative = np.cumsum(weights)

    # One random draw per stratum
    u_values = (np.random.uniform(size=n) + np.arange(n)) / n

    indices = []
    i = 0
    for u in u_values:
        while cumulative[i] < u:
            i += 1
        indices.append(i)

    return [copy.deepcopy(particles[i]) for i in indices]
```

**Pros**: Guarantees proportional representation, very low variance.
**Cons**: Slightly more complex than systematic.

### 4.5 Resampling for Nikita: Recommended Strategy

**Use stratified resampling** with these modifications for personality tracking:

1. **Diversity injection**: After resampling, add small noise to continuous state variables (jittering). This prevents particle collapse when many particles are cloned from the same source.

```python
def jitter_particle(particle: NikitaParticle, noise_scale: float = 0.02) -> NikitaParticle:
    """Add small noise to prevent particle collapse after resampling."""
    p = copy.deepcopy(particle)
    for trait in ['openness', 'conscientiousness', 'extraversion', 'agreeableness', 'neuroticism']:
        value = getattr(p, trait)
        noisy = value + np.random.normal(0, noise_scale)
        setattr(p, trait, np.clip(noisy, 0.001, 0.999))

    p.emotional_valence += np.random.normal(0, noise_scale * 2)
    p.emotional_valence = np.clip(p.emotional_valence, -1, 1)
    p.emotional_arousal += np.random.normal(0, noise_scale)
    p.emotional_arousal = np.clip(p.emotional_arousal, 0, 1)

    return p
```

2. **Discrete state protection**: Ensure that at least a minimum fraction (e.g., 5%) of particles represent each attachment style. This prevents premature commitment to a single style interpretation.

```python
def enforce_diversity(particles: list, min_fraction: float = 0.05) -> list:
    """Ensure minimum representation of each attachment style."""
    n = len(particles)
    min_count = max(1, int(n * min_fraction))

    style_counts = Counter(p.active_attachment_style for p in particles)
    styles = ['secure', 'anxious', 'avoidant', 'disorganized']

    for style in styles:
        deficit = min_count - style_counts.get(style, 0)
        if deficit > 0:
            # Clone random particles and set their style
            for _ in range(deficit):
                donor = random.choice(particles)
                clone = copy.deepcopy(donor)
                clone.active_attachment_style = style
                # Also adjust personality to be consistent with the style
                clone = adjust_personality_for_style(clone, style)
                particles.append(clone)

    # Trim back to N if we added extras
    if len(particles) > n:
        particles = random.sample(particles, n)

    return particles
```

---

## 5. When Particle Filters Beat Analytic Solutions

### 5.1 Decision Matrix

| Situation | Best Method | Reason |
|-----------|------------|--------|
| Single trait, binary observations | Beta-Binomial (exact) | Conjugate, trivially fast |
| Attachment style proportions | Dirichlet-Multinomial (exact) | Conjugate, 4-dimensional |
| Emotional state, linear dynamics | Kalman Filter | Gaussian, linear — exact |
| Multimodal belief about player type | **Particle Filter** | Bimodal posterior, no analytic form |
| Nonlinear personality transitions | **Particle Filter** | Transition function is piecewise/threshold-based |
| Mixed continuous-discrete state | **Particle Filter** | No analytic family handles this mix |
| Crisis event with regime change | **Particle Filter** | Abrupt state change creates non-Gaussian posterior |
| Post-crisis recovery tracking | **Particle Filter** or Kalman | Depends on whether multimodality persists |
| Stable relationship, routine interactions | Beta/Dirichlet (exact) | Back to unimodal, conjugate updates |

### 5.2 The Hybrid Architecture

The recommended approach for Nikita: **use analytic methods by default, switch to particle filters when multimodality or nonlinearity is detected**.

```python
class HybridInferenceEngine:
    """Switches between analytic and particle-based inference."""

    def __init__(self):
        self.analytic_state = AnalyticPersonalityState()  # Beta/Dirichlet
        self.particle_state = None  # lazily initialized
        self.mode = 'analytic'

    def should_switch_to_particles(self, observation: dict) -> bool:
        """Detect when analytic inference is insufficient."""
        # Trigger 1: Ambiguous observation (high likelihood under multiple hypotheses)
        likelihood_spread = self.analytic_state.compute_likelihood_variance(observation)
        if likelihood_spread > AMBIGUITY_THRESHOLD:
            return True

        # Trigger 2: Crisis event (nonlinear transition expected)
        if observation.get('event_type') in ['betrayal', 'major_conflict', 'chapter_transition']:
            return True

        # Trigger 3: Large surprise (observation very unlikely under current state)
        surprise = -np.log(self.analytic_state.compute_likelihood(observation))
        if surprise > SURPRISE_THRESHOLD:
            return True

        return False

    def update(self, observation: dict):
        """Update state using appropriate inference method."""
        if self.mode == 'analytic' and self.should_switch_to_particles(observation):
            # Initialize particles from current analytic distribution
            self.particle_state = self.analytic_state.to_particles(n=200)
            self.mode = 'particle'

        if self.mode == 'particle':
            self.particle_state.update(observation)

            # Check if we can switch back to analytic (unimodal posterior)
            if self.particle_state.is_unimodal():
                self.analytic_state = self.particle_state.to_analytic()
                self.particle_state = None
                self.mode = 'analytic'
        else:
            self.analytic_state.update(observation)
```

### 5.3 Nikita-Specific Triggers for Particle Filters

**Trigger: Player behavior is ambiguous**

When the player says something that could be interpreted as either caring or controlling:
- "I just want to make sure you're okay" — genuine concern? Or possessiveness?
- The analytic model would average these interpretations
- The particle filter maintains both hypotheses until disambiguating evidence arrives

**Trigger: Boss encounter / crisis**

During a boss encounter, Nikita's internal state undergoes rapid, nonlinear transitions. Her attachment system activates, defense mechanisms engage, and emotional states swing. The transition model is highly nonlinear with threshold effects.

**Trigger: Chapter transition**

Moving between chapters represents a regime change in the state dynamics. The transition model's parameters themselves change (e.g., different stress levels, different relationship expectations). Particle filters handle this naturally — particles propagated through the new transition model will diversify to explore the new regime.

**Trigger: Inconsistent player behavior**

If the player has been consistently warm but suddenly sends a cold message, the posterior becomes bimodal:
1. "This is out of character; the player is probably just having a bad day"
2. "This reveals the player's true nature; earlier warmth was performative"

---

## 6. Computational Budget for Real-Time Gameplay

### 6.1 Operation Costs

For N = 200 particles with a 12-dimensional state:

| Operation | FLOPS | Time (Python/NumPy) | Time (Rust/C) |
|-----------|-------|---------------------|---------------|
| Transition (predict) | 200 * 12 * ~10 = 24K | ~0.5ms | ~0.01ms |
| Likelihood (update) | 200 * ~50 = 10K | ~0.2ms | ~0.005ms |
| Weight normalization | 200 | <0.01ms | <0.001ms |
| ESS computation | 200 | <0.01ms | <0.001ms |
| Resampling | 200 * log(200) = 1.5K | ~0.1ms | ~0.005ms |
| Jittering | 200 * 12 = 2.4K | ~0.1ms | ~0.005ms |
| **Total per step** | **~38K** | **~1ms** | **~0.03ms** |

### 6.2 Budget Within the Pipeline

Nikita's pipeline (Doc 08-cognitive-architecture.md) has a total latency budget of ~2-5 seconds per response, dominated by LLM inference. The particle filter's ~1ms contribution is negligible — less than 0.1% of the total pipeline time.

Even upgrading to 500 particles or adding complexity to the transition model, we stay well under 10ms. **Particle filters are not the computational bottleneck** for Nikita's system.

### 6.3 Memory Budget

Each particle stores:
- 5 floats (Big Five): 40 bytes
- 2 floats (emotional state): 16 bytes
- 1 float (trust): 8 bytes
- 3 strings (discrete states): ~60 bytes
- Overhead (object, pointers): ~100 bytes

**Per particle**: ~224 bytes
**200 particles**: ~45 KB
**500 particles**: ~112 KB

This is trivially small compared to the LLM context window (100K+ tokens = megabytes).

### 6.4 Vectorized Implementation

For production performance, vectorize the particle operations:

```python
class VectorizedParticleFilter:
    """Vectorized particle filter using NumPy arrays."""

    def __init__(self, n_particles: int = 200, state_dim: int = 8):
        self.n = n_particles
        self.states = np.random.randn(n_particles, state_dim)  # continuous state
        self.discrete_states = np.zeros(n_particles, dtype=int)  # categorical
        self.weights = np.ones(n_particles) / n_particles
        self.log_weights = np.log(self.weights)

    def predict(self, transition_fn, noise_scale: float = 0.02):
        """Vectorized prediction step."""
        # Apply transition to all particles at once
        self.states = transition_fn(self.states)
        # Add noise
        self.states += np.random.randn(*self.states.shape) * noise_scale
        # Clip to valid range
        np.clip(self.states, 0.001, 0.999, out=self.states)

    def update(self, observation: np.ndarray, likelihood_fn):
        """Vectorized weight update."""
        log_likelihoods = likelihood_fn(self.states, observation)
        self.log_weights += log_likelihoods
        # Normalize in log space for numerical stability
        max_log_w = np.max(self.log_weights)
        self.log_weights -= max_log_w
        self.weights = np.exp(self.log_weights)
        self.weights /= np.sum(self.weights)

    def effective_sample_size(self) -> float:
        """Compute ESS."""
        return 1.0 / np.sum(self.weights ** 2)

    def resample_systematic(self):
        """Vectorized systematic resampling."""
        n = self.n
        cumsum = np.cumsum(self.weights)
        u = np.random.uniform(0, 1/n)
        positions = u + np.arange(n) / n

        indices = np.searchsorted(cumsum, positions)
        self.states = self.states[indices].copy()
        self.discrete_states = self.discrete_states[indices].copy()
        self.weights = np.ones(n) / n
        self.log_weights = np.log(self.weights)

    def step(self, observation, transition_fn, likelihood_fn, noise_scale=0.02):
        """Complete filter step."""
        self.predict(transition_fn, noise_scale)
        self.update(observation, likelihood_fn)

        if self.effective_sample_size() < self.n / 2:
            self.resample_systematic()
            # Jitter to prevent collapse
            self.states += np.random.randn(*self.states.shape) * noise_scale * 0.5

    def estimate(self) -> np.ndarray:
        """Weighted mean state estimate."""
        return np.average(self.states, weights=self.weights, axis=0)

    def estimate_variance(self) -> np.ndarray:
        """Weighted variance for uncertainty."""
        mean = self.estimate()
        diff = self.states - mean
        return np.average(diff ** 2, weights=self.weights, axis=0)

    def is_multimodal(self, threshold: float = 0.3) -> bool:
        """Check if posterior is multimodal using bimodality coefficient."""
        # Simple heuristic: check if weighted variance is large relative to mean
        var = self.estimate_variance()
        mean = self.estimate()
        cv = np.sqrt(var) / (np.abs(mean) + 1e-6)
        return np.any(cv > threshold)
```

---

## 7. Application to Nikita: Tracking Player Intentions Under Ambiguity

### 7.1 The Dual Interpretation Problem

One of the most psychologically interesting applications of particle filters is **tracking the player's true intentions when their behavior is ambiguous**. This goes beyond personality modeling — it captures the fundamental uncertainty of reading another person.

Consider a player who:
- Responds to Nikita's messages within minutes (attentive)
- Uses appropriate emotional language (empathetic)
- But deflects when Nikita asks about personal topics (avoidant?)
- And occasionally makes sharp, witty remarks (playful or contemptuous?)

A rule-based system would need ad-hoc heuristics to reconcile these signals. A unimodal Bayesian model would average them into an indistinct middle. The particle filter maintains **competing narrative threads**:

**Thread A** (40% of particles): "This player is genuinely empathetic but emotionally guarded. They care about Nikita but aren't ready for deep vulnerability. The sharp remarks are affectionate teasing."

**Thread B** (35% of particles): "This player is strategically engaging — they know what to say to keep the game going, but the deflection reveals low genuine emotional investment. The wit is intellectual distancing."

**Thread C** (25% of particles): "This player is anxious-avoidant themselves — the quick responses and emotional language are pursuit behaviors, but the deflection and sharpness are avoidant defenses. They mirror Nikita's own attachment style."

Each thread implies different optimal responses from Nikita. The particle weights represent confidence in each interpretation, and **Nikita's behavior is generated from the mixture** — hedging between interpretations until evidence disambiguates.

### 7.2 Modeling "Reading the Room"

Humans are constantly (unconsciously) running particle filters on each other. When you enter a social situation, you rapidly generate hypotheses about others' states and intentions, weight them by evidence, and discard implausible ones. "Reading the room" is exactly this: filtering.

Nikita's particle filter gives her this capability:

```python
def read_the_room(particles: VectorizedParticleFilter,
                   player_message: dict,
                   context: dict) -> dict:
    """Nikita 'reads the room' using her particle filter."""

    # Predict: how would the player's state evolve since last interaction?
    particles.predict(player_transition_model)

    # Update: what does this message tell us about the player's state?
    particles.update(player_message, message_likelihood_model)

    # Resample if needed
    if particles.effective_sample_size() < particles.n / 2:
        particles.resample_systematic()

    # Extract interpretation
    result = {
        'estimated_player_mood': particles.estimate()[:2],  # valence, arousal
        'confidence': 1.0 / (1.0 + np.mean(particles.estimate_variance())),
        'is_ambiguous': particles.is_multimodal(),
        'dominant_interpretation': get_dominant_cluster(particles),
        'alternative_interpretation': get_second_cluster(particles),
    }

    return result
```

### 7.3 Conflict as Particle Filter Failure

An interesting theoretical insight: **relationship conflict often arises when one person's internal model of the other fails** — the particle filter's weighted estimate diverges sharply from reality.

For Nikita, we can detect this computationally:

```python
def detect_model_failure(particles: VectorizedParticleFilter,
                          observation: dict) -> float:
    """Detect when Nikita's model of the player is failing."""
    # Compute observation likelihood under current particle set
    log_likelihood = particles.compute_observation_likelihood(observation)

    # If the observation is very unlikely under ALL particles,
    # the model is failing — the player did something completely unexpected
    surprise = -log_likelihood

    if surprise > CONFLICT_THRESHOLD:
        # Nikita is "confused" — her model of the player broke
        # This is a natural trigger for conflict, miscommunication,
        # or defensive behavior
        return surprise

    return 0.0
```

This directly connects to Doc 16 (Emotional Contagion): misunderstandings as belief divergence. When Nikita's particle filter on the player fails, it means her internal model is wrong — and that is exactly what creates the emotional rupture of a misunderstanding.

---

## 8. Comparison with Alternative Inference Methods

### 8.1 Kalman Filters

**What they are**: Optimal Bayesian filter for linear-Gaussian systems.

**State model**: x_t = A * x_{t-1} + B * u_t + w_t, where w ~ N(0, Q)
**Observation model**: z_t = H * x_t + v_t, where v ~ N(0, R)

**Advantages over particle filters**:
- Exact (no approximation error)
- O(D^3) per step where D = state dimension (cheaper for low D)
- No weight degeneracy or resampling needed
- Well-understood theory, easy to debug

**Disadvantages for Nikita**:
- **Cannot handle multimodality**: Kalman filter posterior is always unimodal Gaussian
- **Assumes linear transitions**: Personality transitions involve thresholds, piecewise functions, discrete switches
- **Assumes Gaussian noise**: Negativity bias, bounded traits, and heavy tails are not Gaussian
- **Cannot mix continuous and discrete states**: Attachment style is categorical

**When to use**: As a sub-component within each particle (Rao-Blackwellization for the fast-changing continuous emotional state).

### 8.2 Extended Kalman Filter (EKF) and Unscented Kalman Filter (UKF)

**EKF**: Linearizes the transition and observation models using first-order Taylor expansion. Works for mildly nonlinear systems.

**UKF**: Uses "sigma points" to propagate through nonlinear functions without linearization. Better than EKF for moderate nonlinearity.

**For Nikita**: Both still assume unimodal Gaussian posteriors. They handle mild nonlinearity but fail when the posterior is genuinely multimodal (the ambiguous-player scenario). Not recommended as a primary inference engine.

### 8.3 Variational Inference (VI)

**What it is**: Approximates the posterior by finding the closest member of a tractable distribution family (e.g., Gaussian, mixture of Gaussians). Optimizes the Evidence Lower Bound (ELBO):

```
ELBO = E_q[log p(z|x)] - KL(q(x) || p(x))
```

**Advantages over particle filters**:
- Can represent posteriors more compactly (parameterized, not sampled)
- Scales better to very high dimensions
- Well-suited for offline batch processing
- No weight degeneracy

**Disadvantages for Nikita**:
- **Sequential updates are expensive**: VI typically processes all data at once; online VI exists but adds complexity
- **Can miss modes**: Mean-field VI (most common) assumes independence and can collapse multimodal posteriors
- **Requires gradient computation**: Need differentiable likelihood and transition models
- **Slower iteration**: Each update requires optimization (multiple gradient steps)

**When to use**: For offline personality analysis (e.g., post-session summary of what the system learned about the player). Not suitable for real-time per-message updates.

### 8.4 Mixture of Gaussians (GMM) Filter

**What it is**: Maintains the posterior as a weighted mixture of K Gaussians. Each component tracks a mode of the posterior.

**Advantages**:
- Explicitly represents multimodality
- More compact than particle representation
- Analytically tractable updates within each component

**Disadvantages for Nikita**:
- Number of components grows exponentially without pruning
- Pruning/merging heuristics are fragile
- Still assumes Gaussian shape within each mode
- Handling discrete states is awkward

**When to use**: As an intermediate approach if particle filters are too expensive but Kalman filters are too limited. For Nikita's problem size, particle filters are cheap enough that GMMs offer no advantage.

### 8.5 Summary Comparison

| Method | Multimodal? | Nonlinear? | Mixed state? | Online? | Cost (D=12) |
|--------|-------------|-----------|-------------|---------|-------------|
| Kalman Filter | No | No (linear only) | No | Yes | ~1ms |
| EKF/UKF | No | Mild | No | Yes | ~2ms |
| Particle Filter | **Yes** | **Yes** | **Yes** | **Yes** | **~1-5ms** |
| Variational Inference | Depends | Yes | Possible | Slow | ~50-200ms |
| GMM Filter | Yes | Mild | Awkward | Yes | ~5-10ms |

**Recommendation for Nikita**: Particle filter as the primary nonlinear inference engine, with Rao-Blackwellized Kalman filters for fast continuous sub-states within each particle. Switch to analytic (Beta/Dirichlet) for stable, unimodal personality tracking during calm periods.

---

## 9. Advanced Particle Filter Techniques

### 9.1 Auxiliary Particle Filter (Pitt & Shephard, 1999)

The auxiliary particle filter (APF) improves on the bootstrap filter by incorporating the current observation into the proposal distribution. Instead of blindly propagating particles forward and then weighting by the observation, APF first "looks ahead" to see which particles are likely to produce good predictions.

```python
def auxiliary_particle_filter_step(particles, weights, observation,
                                     transition_fn, likelihood_fn):
    """Auxiliary PF: look-ahead resampling for better particle efficiency."""
    n = len(particles)

    # Step 1: Compute "first-stage" weights using predicted observation
    predicted_states = np.array([transition_fn(p) for p in particles])
    first_stage_weights = np.array([likelihood_fn(ps, observation) for ps in predicted_states])
    first_stage_weights *= weights
    first_stage_weights /= np.sum(first_stage_weights)

    # Step 2: Resample based on first-stage weights
    indices = systematic_resample_indices(first_stage_weights)
    resampled_particles = [particles[i] for i in indices]

    # Step 3: Propagate and compute second-stage weights
    propagated = [transition_fn(p) for p in resampled_particles]
    second_stage_weights = np.array([
        likelihood_fn(prop, observation) / likelihood_fn(pred, observation)
        for prop, pred in zip(propagated, predicted_states[indices])
    ])
    second_stage_weights /= np.sum(second_stage_weights)

    return propagated, second_stage_weights
```

**For Nikita**: APF is useful during boss encounters when the observation space is rich (long player messages with many emotional signals). The look-ahead step ensures particles are concentrated in regions that actually explain the observation.

### 9.2 Particle MCMC (Andrieu et al., 2010)

When particle filters are used for parameter estimation (e.g., learning the transition model's parameters from data), standard methods underperform. Particle MCMC combines particle filters with Markov Chain Monte Carlo to produce exact samples from the joint posterior over states and parameters.

**For Nikita**: Useful for calibrating the personality model from playtesting data. After collecting player interaction histories, use PMCMC to learn:
- Optimal noise scales in the transition model
- Likelihood model parameters (how messages map to personality indicators)
- Per-chapter transition model differences

This is an offline calibration technique, not used in real-time gameplay.

### 9.3 Particle Smoothing

Particle filtering provides the **filtering** distribution p(x_t | z_{1:t}). Sometimes we want the **smoothing** distribution p(x_t | z_{1:T}) — our best estimate of a past state given ALL evidence, including future observations.

**For Nikita**: After a conversation ends, smoothing can reconstruct the most likely personality trajectory over the entire conversation. This is useful for:
- Post-session analytics ("When exactly did the player's trust drop?")
- Retroactive story coherence ("Given everything that happened, what was Nikita's actual emotional trajectory?")
- Training data generation for model improvement

---

## 10. Code Sketch: Complete Particle Filter for Nikita

### 10.1 Full Implementation

```python
import numpy as np
from dataclasses import dataclass, field
from typing import Callable
import copy

# State dimensions
BIG_FIVE = ['openness', 'conscientiousness', 'extraversion', 'agreeableness', 'neuroticism']
ATTACHMENT_STYLES = ['secure', 'anxious', 'avoidant', 'disorganized']
DEFENSE_MECHANISMS = ['none', 'sublimation', 'intellectualization', 'rationalization',
                       'projection', 'displacement', 'denial', 'reaction_formation',
                       'regression', 'acting_out']

@dataclass
class NikitaState:
    """Complete internal state for one particle."""
    big_five: np.ndarray = field(default_factory=lambda: np.array([0.7, 0.4, 0.6, 0.5, 0.7]))
    emotional_valence: float = 0.2     # [-1, 1]
    emotional_arousal: float = 0.3     # [0, 1]
    perceived_player_trust: float = 0.5  # [0, 1]
    attachment_probs: np.ndarray = field(default_factory=lambda: np.array([0.14, 0.57, 0.21, 0.07]))
    active_defense: int = 0            # index into DEFENSE_MECHANISMS


class NikitaParticleFilter:
    """Particle filter for Nikita's internal state."""

    def __init__(self, n_particles: int = 200):
        self.n = n_particles
        self.particles: list[NikitaState] = []
        self.weights = np.ones(n_particles) / n_particles
        self._initialize()

    def _initialize(self):
        """Sample initial particles from prior."""
        for _ in range(self.n):
            state = NikitaState(
                big_five=np.array([
                    np.random.beta(8, 3),   # openness
                    np.random.beta(4, 5),   # conscientiousness
                    np.random.beta(7, 4),   # extraversion
                    np.random.beta(5, 5),   # agreeableness
                    np.random.beta(7, 3),   # neuroticism
                ]),
                emotional_valence=np.clip(np.random.normal(0.2, 0.3), -1, 1),
                emotional_arousal=np.random.beta(3, 5),
                perceived_player_trust=np.random.beta(3, 3),
                attachment_probs=np.random.dirichlet([2, 8, 3, 1]),
                active_defense=0,
            )
            self.particles.append(state)

    def predict(self, context: dict, dt: float = 1.0):
        """Propagate all particles through transition model."""
        for p in self.particles:
            # Big Five: slow random walk
            noise = np.random.normal(0, 0.005 * dt, size=5)
            p.big_five = np.clip(p.big_five + noise, 0.001, 0.999)

            # Emotional state: faster dynamics, decay toward neutral
            p.emotional_valence *= (1 - 0.1 * dt)  # decay toward 0
            p.emotional_valence += np.random.normal(0, 0.05 * dt)
            p.emotional_valence = np.clip(p.emotional_valence, -1, 1)

            p.emotional_arousal *= (1 - 0.15 * dt)  # decay toward 0
            p.emotional_arousal += np.random.normal(0, 0.04 * dt)
            p.emotional_arousal = np.clip(p.emotional_arousal, 0, 1)

            # Trust: slow dynamics
            p.perceived_player_trust += np.random.normal(0, 0.01 * dt)
            p.perceived_player_trust = np.clip(p.perceived_player_trust, 0, 1)

            # Attachment: very slow Dirichlet drift
            p.attachment_probs += np.random.dirichlet([100, 100, 100, 100]) * 0.01
            p.attachment_probs /= p.attachment_probs.sum()

            # Defense mechanism: stochastic switching
            if context.get('stress_level', 0) > 0.5:
                # Under stress, may activate defense
                if np.random.random() < context['stress_level'] * 0.3:
                    # Choose defense based on personality
                    defense_probs = self._defense_probabilities(p)
                    p.active_defense = np.random.choice(len(DEFENSE_MECHANISMS), p=defense_probs)
            else:
                # Low stress: probably no defense active
                if np.random.random() < 0.7:
                    p.active_defense = 0  # 'none'

    def update(self, observation: dict):
        """Update weights based on observation likelihood."""
        log_weights = np.zeros(self.n)

        for i, p in enumerate(self.particles):
            log_weights[i] = self._log_likelihood(p, observation)

        # Normalize in log space
        max_lw = np.max(log_weights)
        log_weights -= max_lw
        self.weights = np.exp(log_weights)
        self.weights /= np.sum(self.weights)

    def resample_if_needed(self):
        """Resample using systematic resampling when ESS is low."""
        ess = 1.0 / np.sum(self.weights ** 2)

        if ess < self.n / 2:
            # Systematic resampling
            cumsum = np.cumsum(self.weights)
            u = np.random.uniform(0, 1 / self.n)
            positions = u + np.arange(self.n) / self.n

            indices = np.searchsorted(cumsum, positions)
            indices = np.clip(indices, 0, self.n - 1)

            new_particles = [copy.deepcopy(self.particles[i]) for i in indices]

            # Jitter continuous states
            for p in new_particles:
                p.big_five += np.random.normal(0, 0.01, size=5)
                p.big_five = np.clip(p.big_five, 0.001, 0.999)
                p.emotional_valence += np.random.normal(0, 0.02)
                p.emotional_valence = np.clip(p.emotional_valence, -1, 1)

            self.particles = new_particles
            self.weights = np.ones(self.n) / self.n

    def step(self, observation: dict, context: dict, dt: float = 1.0):
        """Complete filter step."""
        self.predict(context, dt)
        self.update(observation)
        self.resample_if_needed()

    def estimate(self) -> dict:
        """Weighted mean state estimate."""
        big_five = np.average(
            [p.big_five for p in self.particles], weights=self.weights, axis=0
        )
        valence = np.average(
            [p.emotional_valence for p in self.particles], weights=self.weights
        )
        arousal = np.average(
            [p.emotional_arousal for p in self.particles], weights=self.weights
        )
        trust = np.average(
            [p.perceived_player_trust for p in self.particles], weights=self.weights
        )
        attachment = np.average(
            [p.attachment_probs for p in self.particles], weights=self.weights, axis=0
        )

        return {
            'big_five': dict(zip(BIG_FIVE, big_five)),
            'emotional_valence': valence,
            'emotional_arousal': arousal,
            'perceived_player_trust': trust,
            'attachment_probs': dict(zip(ATTACHMENT_STYLES, attachment)),
            'uncertainty': np.mean(self.estimate_variance()),
        }

    def estimate_variance(self) -> np.ndarray:
        """Weighted variance across particles."""
        states = np.array([p.big_five for p in self.particles])
        mean = np.average(states, weights=self.weights, axis=0)
        diff = states - mean
        return np.average(diff ** 2, weights=self.weights, axis=0)

    def _log_likelihood(self, particle: NikitaState, observation: dict) -> float:
        """Compute log-likelihood of observation given particle state."""
        ll = 0.0

        # Sentiment consistency: observation sentiment should match emotional valence
        if 'message_sentiment' in observation:
            expected_sentiment = particle.emotional_valence
            observed_sentiment = observation['message_sentiment']
            ll += -0.5 * ((expected_sentiment - observed_sentiment) / 0.3) ** 2

        # Trust consistency: player reliability evidence
        if 'response_time_minutes' in observation:
            # Quick response = evidence of reliability
            rt = observation['response_time_minutes']
            expected_reliability = particle.perceived_player_trust
            observed_reliability = np.exp(-rt / 30.0)  # decay with time
            ll += -0.5 * ((expected_reliability - observed_reliability) / 0.2) ** 2

        # Attachment consistency: observed behavior matches predicted style
        if 'attachment_cues' in observation:
            cues = observation['attachment_cues']  # dict of style -> evidence_strength
            for style, strength in cues.items():
                style_idx = ATTACHMENT_STYLES.index(style)
                expected_prob = particle.attachment_probs[style_idx]
                ll += strength * np.log(expected_prob + 1e-8)

        return ll

    def _defense_probabilities(self, particle: NikitaState) -> np.ndarray:
        """Probability of each defense mechanism given personality state."""
        probs = np.ones(len(DEFENSE_MECHANISMS)) * 0.01  # base rate
        probs[0] = 0.5  # 'none' is most likely

        n = particle.big_five[4]  # neuroticism
        a = particle.big_five[3]  # agreeableness

        # High neuroticism → more defense activation
        probs[2] += n * 0.15   # intellectualization
        probs[4] += n * 0.20   # projection
        probs[6] += n * 0.10   # denial
        probs[8] += n * 0.15   # regression

        # Low agreeableness → hostile defenses
        probs[5] += (1 - a) * 0.15  # displacement
        probs[9] += (1 - a) * 0.10  # acting_out

        # High agreeableness → adaptive defenses
        probs[1] += a * 0.20  # sublimation
        probs[3] += a * 0.10  # rationalization

        probs /= probs.sum()
        return probs
```

---

## 11. Key Takeaways for Nikita

### 11.1 When to Use Particle Filters

1. **Player behavior is ambiguous**: Multiple plausible interpretations should be maintained in parallel, not averaged.
2. **During crisis/boss encounters**: Nonlinear state transitions (threshold effects, regime changes) break analytic methods.
3. **Mixed state tracking**: Nikita's state mixes continuous traits with categorical attachment/defense states.
4. **Model failure detection**: Surprise computation from particle weights naturally flags when the player does something unexpected.

### 11.2 When NOT to Use Particle Filters

1. **Stable, calm interactions**: Use Beta/Dirichlet conjugate updates (analytically exact, faster).
2. **Single-trait tracking**: A Beta distribution update is simpler and better for one-dimensional questions.
3. **Offline analysis**: Variational inference or MCMC may be more appropriate for batch processing.

### 11.3 Design Recommendations

- **Start analytic, switch to particles on demand** (the Hybrid Architecture in Section 5.2)
- **200 particles** is the recommended default for Nikita's 12-15 dimensional state space
- **Systematic resampling** with jittering for post-resample diversity
- **Rao-Blackwellize**: Track fast emotional dynamics with Kalman filters within each particle
- **Vectorize**: Use NumPy arrays, not Python loops, for production code

### 11.4 Cross-References

- **Doc 03 (Bayesian Personality)**: Analytic distributions that particle filters extend for complex scenarios
- **Doc 04 (HMM Emotional States)**: HMMs for emotion sequences; particle filters for the full joint state
- **Doc 08 (Game AI Personality)**: How commercial games handle personality computation budgets
- **Doc 13 (Nikita DBN)**: The DBN structure that particle filters perform inference over
- **Doc 17 (Controlled Randomness)**: Tail sampling from particle distributions for surprise generation

---

## References

- Andrieu, C., Doucet, A., & Holenstein, R. (2010). Particle Markov chain Monte Carlo methods. *Journal of the Royal Statistical Society: Series B*, 72(3), 269-342.
- Baumeister, R. F., Bratslavsky, E., Finkenauer, C., & Vohs, K. D. (2001). Bad is stronger than good. *Review of General Psychology*, 5(4), 323-370.
- Doucet, A., de Freitas, N., & Gordon, N. (Eds.). (2001). *Sequential Monte Carlo Methods in Practice*. Springer.
- Doucet, A., de Freitas, N., Murphy, K., & Russell, S. (2000). Rao-Blackwellised particle filtering for dynamic Bayesian networks. *Proceedings of UAI*, 176-183.
- Gordon, N. J., Salmond, D. J., & Smith, A. F. M. (1993). Novel approach to nonlinear/non-Gaussian Bayesian state estimation. *IEE Proceedings F*, 140(2), 107-113.
- Kitagawa, G. (1996). Monte Carlo filter and smoother for non-Gaussian nonlinear state space models. *Journal of Computational and Graphical Statistics*, 5(1), 1-25.
- Liu, J. S., & Chen, R. (1998). Sequential Monte Carlo methods for dynamic systems. *Journal of the American Statistical Association*, 93(443), 1032-1044.
- Pitt, M. K., & Shephard, N. (1999). Filtering via simulation: Auxiliary particle filters. *Journal of the American Statistical Association*, 94(446), 590-599.

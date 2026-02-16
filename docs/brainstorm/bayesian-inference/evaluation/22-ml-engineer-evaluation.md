# 22 — ML Engineer Evaluation: Are the Computational Claims Realistic?

**Series**: Bayesian Inference for AI Companions — Expert Evaluations
**Persona**: Senior ML Engineer (10 years in production ML systems, specializing in probabilistic models, Bayesian inference, and real-time ML serving)
**Date**: 2026-02-16
**Evaluates**: Phase 2 documents (12-19), with focus on computational claims, scalability, and simpler alternatives

---

## Executive Summary

I have audited the Phase 2 proposals for mathematical correctness, computational feasibility, scalability, and engineering complexity. My assessment: the core Bayesian primitives (Beta-Bernoulli updates, Dirichlet updates, Thompson Sampling) are sound and their performance claims are accurate. The DBN proposal is computationally feasible but overengineered for the current scale. Several simpler alternatives would achieve 80% of the benefit at 20% of the complexity.

**Key finding**: The proposals conflate "Bayesian inference" (a mathematical framework) with "machine learning" (a data-driven optimization approach). Most of what is proposed is not ML — it is applied probability with hand-specified priors and update rules. This is not a criticism; applied probability is often the right choice. But calling it "Bayesian ML" creates expectations of data-driven learning that the system does not deliver.

**Overall Score: 7.0/10** — Mathematically sound, computationally feasible, but overengineered. Simpler approaches would work.

---

## 1. Computational Claims Audit

### 1.1 Beta-Bernoulli Update: <1 microsecond

**Claim (Docs 06, 12)**: Beta posterior updates complete in under 1 microsecond.

**Verdict**: Correct. A Beta-Bernoulli update is two floating-point additions:
```python
alpha += weight  # if positive
beta += weight   # if negative
```

On modern hardware (Apple M-series, Cloud Run n2-standard), this is ~1-5 nanoseconds — three orders of magnitude faster than the claimed 1 microsecond. The claim is conservative.

**Caveat**: The claim of "<1 microsecond per update" is accurate for the update itself, but the full pipeline includes feature extraction, observation mapping, and serialization. The realistic end-to-end time for all four metric updates is ~10-50 microseconds, which is still negligible.

### 1.2 Thompson Sampling: <1 millisecond

**Claim (Docs 06, 14, 19)**: Thompson Sampling decisions complete in under 1 millisecond.

**Verdict**: Correct. `numpy.random.beta(alpha, beta)` takes ~500 nanoseconds. Drawing one sample for skip rate, one for timing (or a Dirichlet sample for timing buckets), and performing the argmax comparison is well under 1 millisecond.

**Caveat**: The claim applies to NumPy's implementation. If using scipy.stats (which has object creation overhead), the first call in a cold process can take ~1-5 milliseconds due to module initialization. On Cloud Run with scale-to-zero, this cold-start overhead matters.

**Recommendation**: Use `numpy.random` directly, not `scipy.stats` distributions.

### 1.3 DBN Inference: 5-15 milliseconds

**Claim (Docs 07, 13, 19)**: Full DBN forward inference completes in 5-15 milliseconds.

**Verdict**: Plausible but requires validation. The claim depends critically on three factors:

**Factor 1: Number of nodes.** Doc 13's full node inventory has approximately 10-12 latent variables. For a DBN with this many variables, exact inference (variable elimination) has complexity O(n * k^w) where n is the number of variables, k is the maximum number of states per variable, and w is the treewidth of the graph. Doc 07 estimates treewidth at ~3 for the proposed graph.

With 12 variables, max 10 states (defense_mode), and treewidth 3, the computation is approximately:
```
12 * 10^3 = 12,000 operations
```

At ~1 nanosecond per floating-point operation, this is ~12 microseconds — well under the claimed 5ms. The 5-15ms claim includes Python overhead, memory allocation, and any matrix operations.

**Factor 2: Implementation.** The proposals mention both pgmpy and custom NumPy implementations.

- **pgmpy**: Variable elimination in pgmpy has significant Python overhead. For the proposed graph size, pgmpy inference takes approximately 20-80ms on first call (factor computation, evidence propagation) and 5-20ms on subsequent calls (with cached junction tree). This matches the 5-15ms claim for warm calls but exceeds it for cold calls.

- **Custom NumPy**: A hand-coded forward pass through the causal chain (6 sequential matrix multiplications, each <10x10) completes in approximately 50-200 microseconds. This is 50-100x faster than the claim.

**My recommendation**: Do NOT use pgmpy in production. Write the forward pass as six sequential NumPy matrix multiplications. The code is approximately 50 lines and runs in microseconds.

```python
def dbn_forward_pass(
    observations: dict,
    transition_matrices: dict,   # Pre-computed, loaded at startup
    current_belief: dict,
) -> dict:
    """Custom DBN forward pass. ~50-200 microseconds."""

    # Step 1: Threat perception
    threat = np.array(observations["sentiment_features"])
    threat_belief = transition_matrices["threat"] @ threat
    threat_belief /= threat_belief.sum()

    # Step 2: Attachment activation
    attach_input = np.concatenate([threat_belief, current_belief["attachment"]])
    attach_belief = transition_matrices["attachment"] @ attach_input
    attach_belief /= attach_belief.sum()

    # Step 3: Defense mode
    defense_input = np.concatenate([attach_belief, current_belief["personality"]])
    defense_belief = transition_matrices["defense"] @ defense_input
    defense_belief /= defense_belief.sum()

    # Step 4: Emotional tone (continuous: mixture of Gaussians)
    # Weighted sum of emotion centroids by defense mode probabilities
    emotion = transition_matrices["emotion_centroids"].T @ defense_belief
    stress_mod = current_belief["stress"] * transition_matrices["stress_weight"]
    emotion += stress_mod

    # Step 5: Response style
    style_input = np.concatenate([emotion, defense_belief[:5]])  # truncated
    style_belief = transition_matrices["style"] @ style_input
    style_belief = np.exp(style_belief)  # softmax
    style_belief /= style_belief.sum()

    return {
        "threat": threat_belief,
        "attachment": attach_belief,
        "defense": defense_belief,
        "emotion": emotion,
        "response_style": style_belief,
    }
```

**Factor 3: Cloud Run cold start.** On Cloud Run with scale-to-zero, the first request after a cold start must load NumPy (~150ms), initialize arrays (~10ms), and compile any JIT-optimized code. The DBN inference will be ~200ms on cold start. After warmup, it will be sub-millisecond.

This is fine — the existing pipeline already has multi-second cold start times (LLM API calls, database connections). The Bayesian overhead is negligible compared to the existing cold start.

### 1.4 Full Pipeline: <25 milliseconds

**Claim (Doc 19)**: The complete Bayesian pipeline (feature extraction + state load + posterior updates + DBN inference + Thompson Sampling + surprise check + state save) completes in under 25 milliseconds.

**Verdict**: Achievable with custom NumPy, not achievable with pgmpy.

Breakdown:
```
Component                  Custom NumPy      pgmpy
─────────────────────────────────────────────────────
Feature extraction         1-2ms             1-2ms
State load (DB read)       3-8ms             3-8ms
Posterior updates           0.01ms            0.01ms
DBN inference              0.05-0.2ms        5-20ms
Thompson Sampling          0.01ms            0.01ms
Surprise computation       0.1ms             0.1ms
State save (DB write)      3-8ms             3-8ms
─────────────────────────────────────────────────────
TOTAL                      7-19ms            12-39ms
```

With custom NumPy, the pipeline easily fits in 25ms. The bottleneck is database I/O, not computation. With pgmpy, the pipeline occasionally exceeds 25ms under load.

---

## 2. Mathematical Correctness Audit

### 2.1 Beta-Bernoulli Conjugate Updates

**Doc 12's update rule**:
```python
if positive:
    alpha += weight
else:
    beta += weight
```

**Correctness**: For the standard Beta-Bernoulli conjugate model, the update is alpha += 1 (on success) and beta += 1 (on failure). Using fractional weights (0.0-1.0) is an extension that models "partial observations" or "soft evidence." This is mathematically valid — it corresponds to observing a fractional number of trials, which is equivalent to power-likelihood or tempered posteriors.

**Concern**: The weight values (0.3 for a short message, 0.7 for a personal question, etc.) are hand-tuned, not learned from data. These weights are the most critical parameters in the system, and there is no validation framework to assess whether they are correct.

**Recommendation**: Log all observations and weights for the first 3 months. After accumulating data, use maximum marginal likelihood to optimize the weights:

```python
def optimize_observation_weights(
    observation_log: list[dict],  # {event_type, metric, weight, ground_truth_outcome}
) -> dict:
    """Fit observation weights using maximum marginal likelihood.

    After 3 months of shadow mode, use accumulated data to
    calibrate the hand-tuned weights.
    """
    from scipy.optimize import minimize

    def neg_log_marginal_likelihood(weights):
        total_nll = 0
        for obs in observation_log:
            # Compute predicted posterior mean given the weight
            alpha, beta = obs["prior_alpha"], obs["prior_beta"]
            if obs["is_positive"]:
                alpha += weights[obs["event_type_idx"]]
            else:
                beta += weights[obs["event_type_idx"]]
            predicted_mean = alpha / (alpha + beta)

            # Compare to actual outcome
            outcome = obs["ground_truth_outcome"]  # Did player engage more?
            nll = -outcome * np.log(predicted_mean + 1e-10) - (1 - outcome) * np.log(1 - predicted_mean + 1e-10)
            total_nll += nll
        return total_nll

    initial_weights = np.array([0.5] * len(EVENT_TYPES))
    result = minimize(neg_log_marginal_likelihood, initial_weights, bounds=[(0.01, 2.0)] * len(EVENT_TYPES))
    return dict(zip(EVENT_TYPES, result.x))
```

### 2.2 Dirichlet Updates for Vice Discovery

**Doc 12/18's update rule**:
```python
vice_alphas[category_idx] += weight
```

**Correctness**: This is the standard Dirichlet-Multinomial conjugate update. Observing vice category i increments alpha_i. The posterior Dirichlet concentration increases, narrowing the distribution around the observed category. Mathematically correct.

**Concern**: The initial alphas are all 1.0 (or 2.0 in Doc 19), which represents a uniform prior. This means the system has no initial preference — it treats all 8 vice categories as equally likely. This is fine for vice discovery (where we genuinely do not know the player's preference), but it means the first ~5 observations will have outsized influence on the posterior.

**Recommendation**: Use alpha = 2.0 (as Doc 19 does, not 1.0 as Doc 12 does) for a mildly informative prior. This requires ~4 observations to shift the mode from uniform, preventing single-message vice classification.

### 2.3 HMM Forward Algorithm

**Doc 12's mood update**:
```python
predicted = belief @ A       # Transition: P(mood_t | mood_t-1)
updated = predicted * B[:, observation_idx]  # Emission: P(obs | mood_t)
self.mood_belief = (updated / total).tolist()
```

**Correctness**: This is the standard HMM forward step (filtering). It computes P(mood_t | observation_1:t) using the predict-update cycle. Mathematically correct.

**Concern 1**: The observation model maps each message to a single observation index (out of 14 possible). This quantization loses information. A message could be "slightly warm" or "extremely warm" — both map to the same observation index. Consider using continuous emission models (Gaussian HMM) instead of discrete emissions.

**Concern 2**: The transition matrix A and emission matrix B are hand-specified, not learned. With 6 mood states and 14 observation types, the emission matrix has 84 parameters — all hand-tuned. The transition matrix has 30 free parameters (6x6 minus normalization). That is 114 hand-tuned parameters with no validation.

**Concern 3**: There is no observation for "no message received." In the HMM framework, absence of observation should update the belief state differently from any specific observation. During skip events or player absence, the forward step should apply only the transition (predict) without the emission update (update).

### 2.4 Bayesian Surprise via KL Divergence

**Doc 14's surprise computation**:
```
surprise = KL(posterior || prior)
```

**Correctness**: KL divergence from posterior to prior measures how much the observation changed the belief. This is a standard measure of Bayesian surprise (Itti & Baldi, 2009). Mathematically correct.

**Concern**: KL divergence is unbounded above. For Beta distributions, KL(Beta(a1,b1) || Beta(a2,b2)) can be very large when the distributions are far apart. The threshold values (2.0 for Tier 2, 3.0 for Tier 3) are in "nats" (natural log units). For Beta distributions with moderate parameters (alpha, beta in [2, 20]), a surprise of 2.0 nats corresponds to roughly halving or doubling the posterior mean — a very large shift. The thresholds seem reasonable.

**Implementation note**: Computing KL divergence between Beta distributions requires the digamma function (scipy.special.digamma). This is ~10x slower than basic arithmetic but still sub-microsecond.

```python
from scipy.special import betaln, digamma

def kl_beta(a1, b1, a2, b2):
    """KL divergence from Beta(a1,b1) to Beta(a2,b2)."""
    return (
        betaln(a2, b2) - betaln(a1, b1)
        + (a1 - a2) * digamma(a1)
        + (b1 - b2) * digamma(b1)
        + (a2 - a1 + b2 - b1) * digamma(a1 + b1)
    )
```

### 2.5 Discounted Thompson Sampling

**Doc 06's forgetting mechanism**:
```python
alpha = gamma * alpha + (1 - gamma) * prior_alpha + reward
beta = gamma * beta + (1 - gamma) * prior_beta + (1 - reward)
```

**Correctness**: This is the standard discounted posterior for non-stationary bandits (Raj & Kalyani, 2017). The discount factor gamma controls the effective window of observations. For gamma = 0.98, the effective window is approximately 1/(1-0.98) = 50 observations. Mathematically correct.

**Concern**: The discount is applied uniformly to all observations. An alternative is to use change-point detection (Adams & MacKay, 2007) to detect when player behavior shifts, then apply a hard reset of the posterior. This is more data-efficient: the discount continuously forgets even when behavior is stationary, wasting information.

**Recommendation for Nikita**: Use the simple discount for skip/timing (where preferences may drift gradually) and change-point detection for vice preferences (where a player discovering a new vice is a discrete shift, not a gradual drift).

---

## 3. Scalability Assessment

### 3.1 Memory: Will the JSONB State Fit?

**Doc 19's estimate**: ~1.8 KB per player, ~18 MB at 10,000 players.

**My assessment**: The estimate is accurate for the current schema. However, several proposed extensions could inflate this:

| Extension | Additional Size | Total at 10K |
|-----------|----------------|-------------|
| Base state | 1.8 KB | 18 MB |
| Surprise history (7 days) | 56 bytes | +0.6 MB |
| Event engagement history (15 categories x 7 days) | 840 bytes | +8.4 MB |
| Conversation-level emotional trajectory | 200 bytes/conv | +2 MB |
| Contagion state (Doc 16) | 120 bytes | +1.2 MB |
| Defense mode history | 80 bytes | +0.8 MB |
| **Total with all extensions** | **~3.1 KB** | **~31 MB** |

At 31 MB for 10K players, this is trivial for Supabase (PostgreSQL). Even at 100K players, 310 MB is well within reasonable limits.

**Concern**: JSONB parsing overhead. PostgreSQL must parse the entire JSONB document on each read, even if only one field is needed. At 3 KB, this is ~5 microseconds — negligible. But if the state grows to 10+ KB (through additional extensions), parsing overhead becomes measurable (~20 microseconds).

**Recommendation**: Monitor JSONB document size. If it exceeds 5 KB, consider breaking the state into multiple columns (metrics, emotional, behavioral) for partial reads.

### 3.2 Compute: Can Cloud Run Handle It?

**Current load**: Nikita processes ~15 messages per active player per day. With 1,000 daily active players, that is 15,000 messages/day, or ~0.17 requests/second average (with peaks of ~2-5 req/s during evening hours).

**Bayesian overhead per request**: ~10-20ms additional (compared to current LLM-dominated latency of 2-5 seconds).

**Assessment**: The Bayesian overhead is negligible. The current pipeline is bottlenecked by LLM API latency, not compute. Adding 20ms to a 3-second pipeline is a 0.7% increase. Even at 10x the current load (10,000 DAU), the Bayesian compute is trivially small.

**The real scalability question** is not compute but **database contention**. Each message requires a read-modify-write of the `bayesian_states` row. With 50 req/s (10K DAU peak), this creates potential for write contention if two messages from the same user arrive simultaneously.

**Mitigation**: Use `SELECT ... FOR UPDATE SKIP LOCKED` to prevent contention, or use optimistic locking with version counters:

```sql
UPDATE bayesian_states
SET state_json = $1, version = version + 1
WHERE user_id = $2 AND version = $3;
```

If the update affects 0 rows (version mismatch), reload and retry.

### 3.3 Latency: p99 Under Load

**Estimated p99 latency** for the Bayesian pipeline:

```
Percentile    Custom NumPy    pgmpy
──────────────────────────────────────
p50           8ms             15ms
p90           12ms            25ms
p95           15ms            35ms
p99           20ms            55ms
p99.9         30ms            80ms
```

The Custom NumPy path easily meets the <25ms target at p99. The pgmpy path exceeds it at p99. This further supports the recommendation to avoid pgmpy in production.

---

## 4. Simpler Alternatives

### 4.1 The Complexity Budget

Every proposal should be evaluated against the question: **could a simpler approach achieve most of the benefit?** The Phase 2 proposals introduce approximately 2,000 lines of new code (Doc 15's estimate) across 14 files. This is a significant maintenance burden for a system that currently has no Bayesian components.

Let me evaluate each proposed component against its simplest viable alternative.

### 4.2 Metric Updates: Bayesian vs. Exponential Moving Average

**Proposed**: Beta posterior updates with observation weights.
**Simpler alternative**: Exponential moving average (EMA) of metric scores.

```python
# Bayesian (proposed)
if positive:
    state.trust_alpha += weight

# EMA (simpler)
state.trust_ema = alpha * new_observation + (1 - alpha) * state.trust_ema
```

**Comparison**:
| Feature | Beta Posterior | EMA |
|---------|--------------|-----|
| Uncertainty quantification | Yes (variance from posterior) | No |
| Adaptive learning rate | Yes (concentrates with evidence) | No (fixed alpha) |
| Principled decay | Yes (regression toward prior) | Yes (exponential decay) |
| Cold start handling | Yes (wide prior) | Yes (but no uncertainty signal) |
| Implementation complexity | Low | Very low |
| Lines of code | ~50 | ~10 |

**Verdict**: The Beta posterior is worth the complexity. The uncertainty quantification (knowing when you are confident vs. uncertain about a metric) is the key differentiator. This directly enables the "mystery" feeling during early interactions and the escalation trigger (high surprise = uncertain → call LLM). The EMA cannot provide this.

**Recommendation**: Keep Beta posteriors for metrics. This is one of the few components where Bayesian treatment provides genuine value over a simpler alternative.

### 4.3 Skip Decision: Thompson Sampling vs. Tuned Probability

**Proposed**: Thompson Sampling from Beta posterior, adapting per-player.
**Simpler alternative**: Fixed skip probability per chapter, tuned via A/B testing.

```python
# Thompson Sampling (proposed)
sample = np.random.beta(state.skip_alpha, state.skip_beta)
should_skip = sample > 0.5

# Fixed probability (simpler)
SKIP_PROBS = {1: 0.30, 2: 0.25, 3: 0.20, 4: 0.15, 5: 0.05}
should_skip = np.random.random() < SKIP_PROBS[chapter]
```

**Comparison**:
| Feature | Thompson Sampling | Fixed Probability |
|---------|------------------|-------------------|
| Per-player adaptation | Yes | No |
| Exploration/exploitation | Automatic | None |
| Requires posterior state | Yes | No |
| Implementation complexity | Low | Trivial |
| Player experience | Personalized skip patterns | Same for all players |

**Verdict**: Thompson Sampling is marginally better but not necessary. The current system has all skip rates at 0.00 (skipping is disabled). The first step should be enabling any skip at all — and for that, fixed probabilities are sufficient. Thompson Sampling can be added later if per-player skip personalization proves valuable.

**Recommendation**: Start with fixed probabilities. Add Thompson Sampling in Phase 2 of the migration if player feedback indicates that one-size-fits-all skip rates are inadequate.

### 4.4 Event Selection: Thompson Sampling vs. Weighted Random

**Proposed**: Thompson Sampling over 15 event categories with per-player posteriors.
**Simpler alternative**: Weighted random selection with global weights tuned by the design team.

```python
# Thompson Sampling (proposed)
samples = [np.random.beta(a, b) for a, b in event_priors]
selected = np.argmax(samples)

# Weighted random (simpler)
GLOBAL_WEIGHTS = [0.15, 0.10, 0.08, ...]  # 15 categories, tuned by design team
selected = np.random.choice(15, p=GLOBAL_WEIGHTS)
```

**Verdict**: The weighted random is sufficient for launch. The benefit of per-player event adaptation requires many observations to converge (estimated 50-100 events per category, which is 750-1500 total events per player — roughly 6-12 months of daily play at 5 events/day). Until the posteriors concentrate, Thompson Sampling over 15 categories will behave essentially like a weighted random with extra noise.

**Recommendation**: Use weighted random for event selection. Reserve Thompson Sampling for the 2-3 most important event categories (e.g., "conflict events" vs. "positive events" vs. "neutral events") where personalization has the highest impact.

### 4.5 Emotional State: DBN vs. Rule-Based State Machine

**Proposed**: Full DBN with causal inference over 12 variables.
**Simpler alternative**: Rule-based state machine with 6 emotional states and transition rules.

```python
# DBN (proposed)
belief = dbn_forward_pass(observations, matrices, current_belief)
emotional_tone = belief["emotion"]

# State machine (simpler)
class EmotionalStateMachine:
    TRANSITIONS = {
        ("content", "negative_message"): "anxious",
        ("content", "positive_message"): "playful",
        ("anxious", "reassurance"): "content",
        ("anxious", "absence"): "withdrawn",
        ("defensive", "repair_attempt"): "anxious",
        # ... ~20 rules
    }
```

**Comparison**:
| Feature | DBN | State Machine |
|---------|-----|---------------|
| Causal reasoning | Yes | No |
| Uncertainty quantification | Yes (belief over states) | No (single state) |
| Smooth transitions | Yes (probability interpolation) | No (discrete jumps) |
| Transparency | Low (matrix parameters opaque) | High (rules readable) |
| Implementation complexity | High (~200 lines + matrices) | Low (~50 lines) |
| Calibration effort | High (84+ parameters) | Medium (~20 rules) |

**Verdict**: This is the hardest call. The DBN provides genuinely better emotional state modeling — the smooth transitions and uncertainty are psychologically valuable. But the engineering cost is high, and the 114 hand-tuned parameters create significant calibration debt.

**Recommendation**: Implement a **hybrid approach**. Use a state machine for the macro emotional state (6 states), but compute transition probabilities using Bayesian principles (the probability of transitioning from "content" to "anxious" depends on the posterior over trust and stress). This captures most of the DBN's benefit (uncertainty-aware transitions) with the state machine's simplicity (readable rules, easy debugging).

```python
class BayesianStateMachine:
    """State machine with Bayesian transition probabilities."""

    def transition(
        self,
        current_state: str,
        observations: dict,
        metric_posteriors: dict,
    ) -> str:
        """Compute next state using Bayesian transition probabilities."""
        # Base transition probabilities from state machine rules
        base_probs = self.BASE_TRANSITIONS[current_state]

        # Modulate by posterior uncertainty
        trust_mean = metric_posteriors["trust"]["alpha"] / (
            metric_posteriors["trust"]["alpha"] + metric_posteriors["trust"]["beta"]
        )
        stress = observations.get("stress_level", 0.0)

        # High stress increases probability of negative transitions
        for negative_state in ["anxious", "defensive", "withdrawn"]:
            base_probs[negative_state] *= (1 + stress)

        # Low trust increases probability of avoidant transitions
        for avoidant_state in ["withdrawn", "defensive"]:
            base_probs[avoidant_state] *= (2 - trust_mean)

        # Normalize
        total = sum(base_probs.values())
        probs = {s: p / total for s, p in base_probs.items()}

        # Sample (Thompson-style)
        states = list(probs.keys())
        weights = [probs[s] for s in states]
        return np.random.choice(states, p=weights)
```

### 4.6 Vice Discovery: Dirichlet vs. Counter-Based

**Proposed**: Dirichlet posterior over 8 categories with Thompson Sampling exploration.
**Simpler alternative**: Frequency counters with epsilon-greedy exploration.

```python
# Dirichlet (proposed)
vice_alphas[detected_category] += 0.5

# Counter-based (simpler)
vice_counts[detected_category] += 1
top_vices = sorted(vice_counts.items(), key=lambda x: x[1], reverse=True)[:3]
```

**Verdict**: The Dirichlet is marginally better (provides uncertainty, enables Thompson Sampling for vice probing), but the counter-based approach is sufficient for most use cases. The main advantage of the Dirichlet is that it handles the cold start elegantly (uniform prior means genuine uncertainty in early messages), while counters can be biased by a single early observation.

**Recommendation**: Keep the Dirichlet. It is trivial to implement (one line of update code) and provides genuine value for vice discovery exploration.

---

## 5. The Observation Encoding Problem

### 5.1 The Weakest Link

The entire Bayesian system depends on converting raw text messages into structured observations (positive/negative signals for each metric, vice category detection, mood observation indices). This conversion — the "observation model" — is the weakest link in the architecture.

Doc 12 proposes a keyword and heuristic-based approach: message length → intimacy signal, response time → trust signal, sentiment → passion signal. This is brittle. Consider:

| Message | Doc 12 Classification | Actual Intent |
|---------|----------------------|---------------|
| "ok" | short_message → negative intimacy | Could be busy, could be annoyed, could be satisfied |
| "Why did you say that?" | personal_question → positive trust | Could be curious, could be accusatory |
| "lol" | humor → positive passion | Could be genuine amusement, could be dismissive |
| "..." | short_message → negative intimacy | Could be thoughtful pause, could be disappointment |
| "I love you" | compliment → positive passion | Could be genuine, could be sarcastic, could be testing |

The observation model has no access to conversational context, tone, or pragmatic intent. It uses superficial features to make inferences that require deep understanding. This is the same problem that plagued rule-based NLP systems before the deep learning era.

### 5.2 The LLM Extraction Alternative

The ironic solution: use the LLM (which the Bayesian system is designed to replace) to produce the observations.

```python
async def extract_observations_via_llm(
    message: str,
    conversation_history: list[str],
    model: str = "claude-haiku-4-5-20251001",
) -> dict:
    """Use a small, fast LLM to extract structured observations.

    Cost: ~$0.0002 per message (Haiku 4.5, ~200 input tokens)
    Latency: ~200ms
    """
    prompt = f"""Analyze this message in the context of an AI girlfriend simulation.
    Message: {message}
    Recent history: {conversation_history[-3:]}

    Output JSON:
    {{
        "intimacy_signal": "positive" | "negative" | "neutral",
        "intimacy_strength": 0.0-1.0,
        "trust_signal": ...,
        "passion_signal": ...,
        "secureness_signal": ...,
        "detected_vices": ["category_name", ...],
        "mood_observation": "content" | "playful" | "anxious" | ...,
        "is_repair_attempt": true | false
    }}"""
    ...
```

**The math**: If Haiku 4.5 costs $0.0002 per observation extraction and the player sends 15 messages/day, that is $0.003/day for dramatically better observation quality. Compare to the $0.039/day total Bayesian system cost from Doc 19 — the extraction cost is <8% of the total.

**Recommendation**: Use a hybrid approach:
1. **Rule-based extraction** for simple signals (response time, message length, explicit keywords) — free, instant
2. **LLM extraction** for ambiguous signals (sentiment, intent, vice detection) — cheap, accurate
3. **Skip LLM extraction** for messages where all rule-based signals agree (low ambiguity) — save 40-60% of extraction calls

### 5.3 Observation Quality Monitoring

Add a monitoring system that tracks observation quality:

```python
class ObservationQualityMonitor:
    """Track accuracy of rule-based observation extraction."""

    def __init__(self):
        self.comparisons = []

    async def compare(self, message: str, history: list[str]):
        """Compare rule-based vs LLM observations (sample 5% of messages)."""
        if np.random.random() > 0.05:
            return  # Skip 95% of messages

        rule_based = extract_observations_rules(message)
        llm_based = await extract_observations_via_llm(message, history)

        agreement = {
            metric: rule_based[f"{metric}_signal"] == llm_based[f"{metric}_signal"]
            for metric in ["intimacy", "trust", "passion", "secureness"]
        }

        self.comparisons.append({
            "message_length": len(message),
            "agreement": agreement,
            "agreement_rate": sum(agreement.values()) / len(agreement),
        })
```

If the agreement rate drops below 70%, the rule-based extraction is not good enough and should be supplemented with more LLM calls.

---

## 6. The Prior Selection Problem

### 6.1 Where Do the Numbers Come From?

Throughout the Phase 2 proposals, specific numerical values appear for priors, weights, thresholds, and hyperparameters. None of these are derived from data — they are all hand-selected based on narrative design intent. Examples:

| Parameter | Value | Source |
|-----------|-------|--------|
| Intimacy prior | Beta(1.5, 6.0) | "Nikita starts skeptical" (Doc 12) |
| Skip rate prior | Beta(3.0, 7.0) | "30% initial skip" (Doc 19) |
| Surprise threshold | 2.0 nats | "Seems reasonable" (Doc 14) |
| Decay rate Ch1 | 0.008/hour | "Fragile early relationship" (Doc 12) |
| Contagion coupling | 0.3 | "Moderate coupling" (Doc 16) |
| Observation weight for "compliment" | 0.6 | "Direct positive sentiment" (Doc 12) |

**The problem**: These values interact in non-obvious ways. The intimacy prior affects how fast intimacy grows, which affects when boss encounters trigger, which affects the game's pacing. Changing one parameter cascades through the system.

### 6.2 Recommendation: Sensitivity Analysis

Before deploying, run a sensitivity analysis on the top 10 most impactful parameters:

```python
def sensitivity_analysis(
    parameter_name: str,
    base_value: float,
    range_factor: float = 2.0,
    n_simulations: int = 1000,
):
    """Simulate player trajectories under parameter perturbations."""
    results = []
    for multiplier in np.linspace(1/range_factor, range_factor, 20):
        perturbed_value = base_value * multiplier
        for _ in range(n_simulations):
            trajectory = simulate_player_trajectory(
                parameter_overrides={parameter_name: perturbed_value},
                messages=200,
            )
            results.append({
                "multiplier": multiplier,
                "final_composite_score": trajectory.final_score,
                "messages_to_chapter_2": trajectory.chapter_2_time,
                "boss_encounter_count": trajectory.boss_count,
                "mean_surprise": np.mean(trajectory.surprise_history),
            })
    return pd.DataFrame(results)
```

Parameters to test: decay rates, observation weights, surprise thresholds, contagion coupling, cold-start priors, behavioral temperature.

---

## 7. Testing Strategy

### 7.1 The Validation Gap

The proposals describe sophisticated mathematical models but no testing strategy. For a system that controls a character's personality expression, testing is critical.

### 7.2 Recommended Test Hierarchy

**Level 1: Unit tests (mathematical correctness)**
```python
def test_beta_update_positive():
    """Positive observation increases alpha."""
    model = BayesianPlayerModel(user_id=uuid4())
    old_alpha = model.intimacy[0]
    model.update_metric("intimacy", positive=True, weight=0.7)
    assert model.intimacy[0] == old_alpha + 0.7

def test_posterior_mean_bounded():
    """Posterior mean always in [0, 1]."""
    model = BayesianPlayerModel(user_id=uuid4())
    for _ in range(1000):
        model.update_metric("trust", positive=True, weight=10.0)
    assert 0 <= model.metric_mean("trust") <= 1
```

**Level 2: Property-based tests (statistical invariants)**
```python
from hypothesis import given, strategies as st

@given(st.floats(0.1, 10), st.floats(0.1, 10), st.booleans(), st.floats(0.01, 2.0))
def test_update_moves_mean_correctly(alpha, beta, positive, weight):
    """Positive updates increase mean, negative updates decrease it."""
    old_mean = alpha / (alpha + beta)
    if positive:
        new_mean = (alpha + weight) / (alpha + weight + beta)
        assert new_mean >= old_mean
    else:
        new_mean = alpha / (alpha + beta + weight)
        assert new_mean <= old_mean
```

**Level 3: Trajectory simulation tests (behavioral validation)**
```python
def test_consistently_positive_player_reaches_chapter_2():
    """A player who sends 50 positive messages should reach Chapter 2."""
    model = BayesianPlayerModel(user_id=uuid4())
    for _ in range(50):
        model.update_metric("intimacy", positive=True, weight=0.5)
        model.update_metric("trust", positive=True, weight=0.5)
        model.update_metric("passion", positive=True, weight=0.3)
        model.update_metric("secureness", positive=True, weight=0.3)
    assert model.composite_score >= 55  # Chapter 2 threshold

def test_absent_player_decays_toward_prior():
    """A player who is absent for 48 hours should see metrics regress."""
    model = BayesianPlayerModel(user_id=uuid4())
    # Build up metrics
    for _ in range(30):
        model.update_metric("trust", positive=True, weight=0.7)
    high_trust = model.metric_mean("trust")

    # Apply 48-hour decay
    model.apply_decay(hours_elapsed=48)
    decayed_trust = model.metric_mean("trust")

    assert decayed_trust < high_trust
    assert decayed_trust > model.metric_mean("trust")  # Not fully reset
```

**Level 4: A/B testing framework (production validation)**

```python
class BayesianABTest:
    """Framework for comparing Bayesian vs. deterministic system in production."""

    METRICS = {
        "session_length": {"direction": "higher_is_better", "min_effect_size": 0.05},
        "messages_per_day": {"direction": "higher_is_better", "min_effect_size": 0.10},
        "day_7_retention": {"direction": "higher_is_better", "min_effect_size": 0.02},
        "boss_pass_rate": {"direction": "similar", "max_deviation": 0.05},
        "player_satisfaction": {"direction": "higher_is_better", "min_effect_size": 0.1},
    }
```

---

## 8. Specific Document Critiques

### Doc 12 — Bayesian Player Model
**Technical assessment**: 8/10. Clean implementation, correct math, reasonable serialization. The observation mapping is the weak point — hand-tuned weights with no validation. The decay model is well-designed. The `to_jsonb()` method with short keys is a nice touch for storage efficiency. Suggest adding `__post_init__` validation to ensure alpha, beta > 0.

### Doc 13 — Nikita DBN
**Technical assessment**: 6/10. The causal structure is correct for the intended application. But the 12-variable DBN with hand-specified CPTs is a maintenance nightmare. Every time the game design changes (new defense mechanism, new emotional state, new observation type), the CPTs must be manually recalibrated. The proposal does not address how to update 114+ parameters when game design evolves. A Bayesian state machine (Section 4.5) would be easier to maintain.

### Doc 14 — Event Generation
**Technical assessment**: 7/10. The two-phase architecture (Bayesian selection + LLM narration) is the right decomposition. Thompson Sampling for event categories is overkill for 15 categories (see Section 4.4). The surprise-based conflict triggering is computationally sound. The template-based narration for low-importance events is the most impactful cost-saving idea.

### Doc 15 — Integration Architecture
**Technical assessment**: 8/10. The module structure is clean. The pipeline integration (pre-stage) is architecturally sound. The feature flag hierarchy is well-designed. The API endpoints for debugging are valuable. Minor: the `BayesianContext.to_prompt_guidance()` method should be tested to ensure the text it generates actually improves LLM responses (and does not just add noise to the prompt).

### Doc 16 — Emotional Contagion
**Technical assessment**: 5/10. The belief divergence concept is sound. The coupled dynamical system is underspecified — the coupling constants, damping factors, and stability conditions are not analyzed. The system could exhibit oscillatory behavior or divergence under certain parameter combinations. Needs a stability analysis before deployment.

### Doc 17 — Controlled Randomness
**Technical assessment**: 6/10. The tail sampling mechanics are correct. The surprise budget is a clever abstraction. The coherence constraints are necessary but insufficient — they are reactive (applied after sampling) rather than proactive (shaping the sampling). The `ControlledTailSampler` could be simplified to a mixture model: sample from the base distribution 80% of the time, sample from a tail-biased distribution 20% of the time.

### Doc 19 — Unified Architecture
**Technical assessment**: 7.5/10. The synthesis is comprehensive. The data flow diagram is clear. The migration plan is realistic. The cost-benefit analysis is honest (17% savings is modest). The risk assessment is thorough. Missing: a testing strategy (see Section 7) and a plan for parameter calibration (see Section 6).

---

## 9. Summary: Top 5 Recommendations

1. **Use custom NumPy, not pgmpy** (Section 1.3): Hand-coded forward pass is 50-100x faster and has no cold-start penalty. pgmpy is great for prototyping but not for production serving.

2. **Replace full DBN with Bayesian state machine** (Section 4.5): Captures most of the benefit at a fraction of the complexity. Readable rules, easy debugging, no 114-parameter calibration nightmare.

3. **Add LLM-based observation extraction for ambiguous signals** (Section 5.2): The rule-based observation model is the system's weakest link. Use Haiku 4.5 for ambiguous signals at $0.003/day — a rounding error compared to the system's total cost.

4. **Start with fixed skip probabilities, add Thompson Sampling later** (Section 4.3): Skip rates are currently all 0.00. The first step is enabling any skip. Personalized Thompson Sampling is a Phase 2+ optimization.

5. **Build the testing infrastructure first** (Section 7): Unit tests, property tests, trajectory simulations, and A/B testing framework. The mathematical models are correct — the risk is in the parameter calibration and observation quality, which only testing can validate.

---

## 10. Final Verdict

The Phase 2 proposals describe a mathematically sound system that is computationally feasible and architecturally well-integrated. The core primitives (Beta posteriors, Dirichlet, Thompson Sampling) are the right choices for this application. The DBN is overengineered but replaceable with a simpler hybrid.

The proposals' main weakness is the gap between "mathematically correct" and "empirically validated." The system has ~150 hand-tuned parameters with no validation framework. It relies on heuristic observation extraction that has not been tested against ground truth. It proposes 2,000 lines of new code with no testing strategy.

**Ship the primitives, defer the complexity.** Start with Beta posteriors for metrics, Dirichlet for vices, and fixed probabilities for skip/timing. Deploy the Bayesian state machine instead of the full DBN. Add Thompson Sampling and emotional inference in later phases after the observation model is validated.

The goal of Phase 1 should be: **prove that Bayesian metric tracking produces scores that correlate well with the deterministic system** (Doc 19's success criterion: within 5%). Once that is established, the foundation is solid for everything else.

---

*"The best ML system is the one that is as simple as possible, but no simpler. Most of what is proposed here could be simpler."*

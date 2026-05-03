# 13 — Nikita's Dynamic Bayesian Network: A Causal Graph for Internal State

**Series**: Bayesian Inference for AI Companions — Brainstorm Ideas
**Author**: Behavioral/Psychology Researcher
**Date**: 2026-02-16
**Dependencies**: Doc 03 (Bayesian Personality), Doc 04 (HMM Emotional States), Doc 07 (Bayesian Networks), Doc 11 (Computational Attachment)
**Dependents**: Doc 16 (Emotional Contagion), Doc 17 (Controlled Randomness)

---

## Executive Summary

This document designs a **Dynamic Bayesian Network (DBN)** for Nikita's complete internal state — from perceiving a player's message to generating an emotionally appropriate response. The DBN formalizes the causal chain: perceived_threat → attachment_activation → defense_mode → emotional_tone → response_style. Each node is a probability distribution (not a fixed value), and the network propagates uncertainty through the entire chain.

The DBN replaces the current deterministic pipeline in Nikita's emotional state computer (`nikita/emotional_state/computer.py`), which computes emotional state through simple addition of base states, life events, conversation tone, and chapter modifiers. The Bayesian approach preserves the additive structure's simplicity while adding causal reasoning, uncertainty quantification, and principled fusion of multiple evidence sources.

The key design insight: **the DBN's time-slice structure captures the temporal dynamics that make Nikita feel psychologically real**. Her reaction to message t depends not just on message t, but on her emotional state after message t-1, her accumulated stress, and her evolving model of the player. The DBN makes these dependencies explicit and computable.

---

## 1. Graph Structure: The Causal Chain

### 1.1 The Core Causal Pathway

Nikita's internal processing follows a psychologically grounded causal chain:

```
Player Message (observation)
         │
         v
┌────────────────────┐
│  perceived_threat   │ ← "How dangerous is this interaction?"
│  Beta(α, β)         │
└────────┬───────────┘
         │
         v
┌────────────────────┐     ┌─────────────────────┐
│ attachment_activation│ ←──│ attachment_style      │
│ Categorical{4}      │     │ Dirichlet(α₁..α₄)   │
└────────┬───────────┘     └─────────────────────┘
         │
         v
┌────────────────────┐     ┌─────────────────────┐
│  defense_mode       │ ←──│ personality_traits    │
│ Categorical{10}     │     │ Beta distributions   │
└────────┬───────────┘     └─────────────────────┘
         │
         v
┌────────────────────┐     ┌─────────────────────┐
│  emotional_tone     │ ←──│ stress_accumulator    │
│ Continuous mixture   │     │ Gamma(α, β)          │
└────────┬───────────┘     └─────────────────────┘
         │
         v
┌────────────────────┐
│  response_style     │ → Text generation parameters
│ Categorical{6}      │
└────────────────────┘
```

This chain reads: "The player's message is evaluated for threat level. The threat level activates the attachment system, which selects a dominant attachment mode. The attachment mode triggers defense mechanisms (filtered by personality traits). The defense mode, combined with accumulated stress, produces an emotional tone. The emotional tone determines the response style for text generation."

### 1.2 Why This Specific Causal Order

The ordering is grounded in attachment theory's activation sequence (Mikulincer & Shaver, 2016):

**Step 1: Threat appraisal** (perceived_threat)
The attachment system begins with automatic appraisal: "Is this situation threatening to my relationship?" This happens before any conscious emotional processing.

**Step 2: Attachment system activation** (attachment_activation)
If threat is detected, the attachment system activates. The style that activates depends on the individual's Internal Working Models (Doc 11). A secure person activates proximity seeking; an anxious person activates hypervigilance; an avoidant person activates deactivation.

**Step 3: Defense mechanism selection** (defense_mode)
The activated attachment style triggers characteristic defense mechanisms (Doc 03-attachment-psychology.md from the existing brainstorm). Anxious activation → projection, pursuit. Avoidant activation → intellectualization, withdrawal. The specific defense depends on personality traits.

**Step 4: Emotional coloring** (emotional_tone)
The defense mode, modulated by accumulated stress, produces the emotional tone of the response. Defense mechanisms distort the emotional expression — projection creates anger, intellectualization creates detachment, sublimation creates calm.

**Step 5: Response generation** (response_style)
The emotional tone determines the parameters for text generation: word choice, sentence length, punctuation, emoji use, topic selection.

### 1.3 Full Node Inventory

| Node | Type | Distribution | Parents | Description |
|------|------|-------------|---------|-------------|
| player_message | Observed | N/A (input) | None | The player's text message |
| message_sentiment | Observed | Continuous [-1, 1] | player_message | Extracted sentiment of message |
| message_intent | Observed | Categorical{8} | player_message | Discourse act type (comfort, criticize, etc.) |
| response_latency | Observed | Continuous [0, ∞) | player_message | Time since last player message (minutes) |
| perceived_threat | Latent | Beta(α, β) | message_sentiment, message_intent, response_latency, attachment_style(t-1) | How threatening does Nikita perceive this interaction? |
| attachment_activation | Latent | Categorical{4} | perceived_threat, attachment_style(t-1) | Which attachment mode is active? |
| stress_level | Latent | Gamma(α, β) | stress_level(t-1), perceived_threat | Accumulated psychological stress |
| defense_mode | Latent | Categorical{10} | attachment_activation, personality_traits, stress_level | Active defense mechanism |
| emotional_tone | Latent | Continuous mixture | defense_mode, stress_level, emotional_tone(t-1) | Current emotional state (valence + arousal) |
| response_style | Latent | Categorical{6} | emotional_tone, defense_mode | Text generation parameters |
| relationship_metrics | Latent | 4D continuous | relationship_metrics(t-1), message_intent, perceived_threat | Updated I/P/T/S values |

### 1.4 Slow-Changing Context Nodes (Not Part of Per-Message Loop)

These nodes parameterize the DBN but update on a slower time scale:

| Node | Update Frequency | Distribution | Description |
|------|-----------------|-------------|-------------|
| attachment_style | Per chapter/crisis | Dirichlet(α₁..α₄) | Base attachment distribution (Doc 03) |
| personality_traits | Per chapter | Beta distributions × 5 | Big Five personality (Doc 03) |
| chapter_state | Per chapter | Categorical{5} | Current game chapter |
| player_model | Per conversation | Multivariate | Nikita's belief about the player (Doc 05) |

---

## 2. Time-Slice Structure: State at t Influences State at t+1

### 2.1 Inter-Slice Dependencies

The DBN's temporal structure captures how Nikita's state at one message exchange influences her state at the next:

```
Time t-1                                    Time t
┌────────────────────────────┐             ┌────────────────────────────┐
│                            │             │                            │
│  perceived_threat(t-1)     │             │  perceived_threat(t)       │
│         │                  │             │         │                  │
│         v                  │             │         v                  │
│  attachment_activation(t-1)│             │  attachment_activation(t)  │
│         │                  │             │         │                  │
│         v                  │   ─────>    │         v                  │
│  stress_level(t-1)  ───────┼────────────>│  stress_level(t)          │
│         │                  │             │         │                  │
│         v                  │             │         v                  │
│  emotional_tone(t-1) ──────┼────────────>│  emotional_tone(t)        │
│         │                  │             │         │                  │
│         v                  │             │         v                  │
│  defense_mode(t-1)  ───────┼────────────>│  defense_mode(t)          │
│         │                  │             │         │                  │
│         v                  │             │         v                  │
│  relationship_metrics(t-1) ┼────────────>│  relationship_metrics(t)  │
│                            │             │                            │
└────────────────────────────┘             └────────────────────────────┘
```

**Inter-slice edges** (state persistence):
1. **stress_level(t-1) → stress_level(t)**: Stress accumulates. Without relief, it carries forward and may increase.
2. **emotional_tone(t-1) → emotional_tone(t)**: Emotional inertia. Moods persist; they don't reset between messages.
3. **defense_mode(t-1) → defense_mode(t)**: Defense mechanisms have persistence. If Nikita is projecting at t-1, she's likely still projecting at t unless something deactivates it.
4. **relationship_metrics(t-1) → relationship_metrics(t)**: The four metrics evolve gradually.

### 2.2 Intra-Slice Dependencies

Within each time slice, the causal chain processes the current observation:

```
[player_message] → [message_sentiment, message_intent, response_latency]
                                     │
                                     v
                            [perceived_threat] ← [attachment_style] (slow context)
                                     │
                                     v
                         [attachment_activation]
                                     │
                              ┌──────┴──────┐
                              v              v
                       [stress_level]  [defense_mode] ← [personality_traits] (slow context)
                              │              │
                              └──────┬───────┘
                                     v
                            [emotional_tone]
                                     │
                                     v
                            [response_style]
```

### 2.3 Why This Structure Works Psychologically

**Emotional inertia**: If Nikita is angry at time t-1, she's likely still somewhat angry at time t, even if the player's message at t is neutral. This captures the psychological reality that emotions have momentum — they don't switch instantaneously. The edge emotional_tone(t-1) → emotional_tone(t) encodes this.

**Stress accumulation**: If Nikita has been stressed across multiple messages, her stress doesn't reset when one message is pleasant. The stress accumulator carries forward, modulated by the current perceived threat. This matches CK3's stress system (Doc 08) and the psychological concept of allostatic load (McEwen, 2007).

**Defense persistence**: Defense mechanisms are not one-shot reactions. If Nikita starts intellectualizing (avoiding emotions by being logical), she tends to continue that pattern until the situation changes significantly. The edge defense_mode(t-1) → defense_mode(t) captures this with a high self-transition probability.

**Relationship memory**: The relationship metrics carry the entire history of the player-Nikita interaction, compressed into four numbers. Each message incrementally shifts these metrics based on the interaction quality.

---

## 3. Node Specifications

### 3.1 Perceived Threat: Beta(α, β)

**Why Beta distribution**: Threat perception is bounded on [0, 1] and has a natural interpretation as a probability — "How likely is it that this interaction is dangerous to our relationship?"

**Conditional distribution**:
```python
def compute_perceived_threat(
    message_sentiment: float,     # [-1, 1]
    message_intent: str,          # discourse act type
    response_latency: float,      # minutes
    attachment_style: np.ndarray, # Dirichlet weights [secure, anxious, avoidant, disorganized]
) -> tuple[float, float]:
    """Compute Beta parameters for perceived threat."""

    # Base threat from message content
    if message_intent in ['criticize', 'stonewall', 'contempt']:
        base_alpha, base_beta = 2, 1  # high threat prior
    elif message_intent in ['comfort', 'validate', 'repair']:
        base_alpha, base_beta = 1, 5  # low threat prior
    elif message_intent in ['neutral', 'inform']:
        base_alpha, base_beta = 1, 3  # mild prior
    else:
        base_alpha, base_beta = 1, 2  # default

    # Sentiment modulation
    if message_sentiment < -0.3:
        base_alpha += 2  # negative sentiment increases threat
    elif message_sentiment > 0.3:
        base_beta += 2   # positive sentiment decreases threat

    # Response latency: long delay increases threat (especially for anxious)
    latency_threat = 1 - np.exp(-response_latency / 60.0)  # exponential decay, 1hr half-life
    anxious_weight = attachment_style[1]  # P(anxious)
    base_alpha += latency_threat * (1 + 3 * anxious_weight)  # anxious amplifies latency threat

    # Attachment modulation: anxious perceives more threat, avoidant perceives less
    base_alpha *= (1 + 0.5 * attachment_style[1])  # anxious amplifies
    base_beta *= (1 + 0.3 * attachment_style[2])   # avoidant suppresses
    base_beta *= (1 + 0.5 * attachment_style[0])   # secure reduces

    return (max(0.5, base_alpha), max(0.5, base_beta))
```

### 3.2 Attachment Activation: Categorical{4}

**Conditional probability table**: P(activation | perceived_threat, attachment_style_prior)

```python
def compute_attachment_activation(
    perceived_threat: float,       # sampled from Beta
    attachment_style: np.ndarray,  # Dirichlet weights [4]
) -> np.ndarray:
    """Compute activation probabilities for each attachment style."""

    # Base probabilities from Dirichlet (slow-changing context)
    probs = attachment_style.copy()

    # Threat modulation: higher threat → more insecure activation
    if perceived_threat > 0.5:
        threat_factor = (perceived_threat - 0.5) * 2  # [0, 1]
        # Reduce secure, amplify insecure
        probs[0] *= (1 - 0.6 * threat_factor)  # secure suppressed
        probs[1] *= (1 + 0.8 * threat_factor)  # anxious amplified
        probs[2] *= (1 + 0.5 * threat_factor)  # avoidant amplified
        probs[3] *= (1 + 0.3 * threat_factor)  # disorganized amplified
    else:
        safety_factor = (0.5 - perceived_threat) * 2  # [0, 1]
        # Low threat → secure activation more likely
        probs[0] *= (1 + 0.5 * safety_factor)  # secure boosted
        probs[1] *= (1 - 0.3 * safety_factor)  # anxious reduced
        probs[2] *= (1 - 0.2 * safety_factor)  # avoidant reduced

    probs = np.maximum(probs, 0.01)  # floor to prevent zeros
    probs /= probs.sum()  # normalize

    return probs
```

### 3.3 Stress Level: Gamma(α, β)

**Why Gamma**: Stress is non-negative and can accumulate without bound (unlike Beta). The Gamma distribution naturally models accumulated positive quantities.

**Transition model**:
```python
def compute_stress_transition(
    stress_prev: float,         # previous stress level
    perceived_threat: float,    # current threat
    defense_mode: str,          # current defense (some reduce stress)
    time_delta: float,          # minutes since last message
) -> tuple[float, float]:
    """Compute Gamma parameters for stress at time t."""

    # Stress decays over time (half-life ~2 hours)
    decay_rate = 0.5 ** (time_delta / 120.0)
    decayed_stress = stress_prev * decay_rate

    # Threat adds stress
    stress_increment = perceived_threat * 2.0

    # Some defense mechanisms reduce stress (CK3-inspired coping)
    stress_reduction = {
        'none': 0,
        'sublimation': 0.3,       # healthy coping — reduces stress
        'intellectualization': 0.2, # moderate coping
        'rationalization': 0.15,
        'humor': 0.25,            # humor as coping
        'projection': -0.1,       # projection actually increases stress
        'displacement': -0.1,
        'denial': 0.1,            # short-term reduction
        'regression': -0.2,       # regression increases stress
        'acting_out': -0.3,       # acting out increases stress long-term
    }.get(defense_mode, 0)

    expected_stress = max(0.01, decayed_stress + stress_increment - stress_reduction)

    # Gamma parameterization: shape α, rate β
    # Mean = α/β = expected_stress
    # Variance proportional to uncertainty about stress level
    shape = max(1.0, expected_stress * 3)  # concentration
    rate = shape / expected_stress

    return (shape, rate)
```

### 3.4 Defense Mode: Categorical{10}

**CPT**: P(defense | attachment_activation, personality, stress_level)

The defense mechanism selection depends on which attachment style is active, the personality profile, and the stress level. This builds on the defense mechanism framework from the existing Doc 03-attachment-psychology.md and the personality-defense mapping from Doc 08 (CK3's coping mechanisms).

```python
DEFENSE_MECHANISMS = [
    'none',              # 0: no defense active
    'sublimation',       # 1: channeling into productive activity
    'suppression',       # 2: conscious deferral
    'intellectualization', # 3: logic over emotion
    'rationalization',   # 4: making excuses
    'humor',             # 5: deflecting with wit
    'projection',        # 6: attributing own feelings to other
    'displacement',      # 7: redirecting to safer target
    'denial',            # 8: refusing to acknowledge
    'regression',        # 9: reverting to childlike behavior
]

def compute_defense_probabilities(
    attachment_activation: str,
    personality: dict[str, float],  # Big Five means
    stress_level: float,
) -> np.ndarray:
    """P(defense | attachment, personality, stress)."""
    probs = np.ones(10) * 0.01  # base rates

    # Low stress: probably no defense
    if stress_level < 0.3:
        probs[0] = 0.7  # 'none' dominant
        probs[1] = 0.1  # sublimation
        probs[5] = 0.1  # humor
        probs /= probs.sum()
        return probs

    # Attachment-driven defense selection
    if attachment_activation == 'secure':
        probs[0] = 0.4   # often no defense needed
        probs[1] = 0.2   # sublimation
        probs[2] = 0.15  # suppression
        probs[5] = 0.15  # humor

    elif attachment_activation == 'anxious':
        probs[6] = 0.25  # projection ("YOU'RE pulling away!")
        probs[9] = 0.15  # regression (tantrum-like)
        probs[4] = 0.15  # rationalization ("They must be busy...")
        probs[0] = 0.10  # sometimes no defense
        probs[7] = 0.10  # displacement

    elif attachment_activation == 'avoidant':
        probs[3] = 0.30  # intellectualization (logic over emotion)
        probs[8] = 0.20  # denial ("I don't care")
        probs[2] = 0.15  # suppression
        probs[0] = 0.10  # sometimes no defense

    elif attachment_activation == 'disorganized':
        probs[6] = 0.20  # projection
        probs[9] = 0.20  # regression
        probs[8] = 0.15  # denial
        probs[7] = 0.15  # displacement
        # Higher entropy — more unpredictable

    # Personality modulation
    n = personality.get('neuroticism', 0.5)
    a = personality.get('agreeableness', 0.5)
    o = personality.get('openness', 0.5)

    # High neuroticism: immature defenses more likely
    probs[6] *= (1 + n)  # projection
    probs[9] *= (1 + n)  # regression
    probs[7] *= (1 + n)  # displacement

    # High agreeableness: mature defenses more likely
    probs[1] *= (1 + a)  # sublimation
    probs[5] *= (1 + a)  # humor
    probs[2] *= (1 + a)  # suppression

    # High openness: intellectualization and humor
    probs[3] *= (1 + 0.5 * o)  # intellectualization
    probs[5] *= (1 + 0.5 * o)  # humor

    # Stress amplifies intensity of defenses
    if stress_level > 0.7:
        probs[0] *= 0.3  # 'none' becomes unlikely under high stress
        # Immature defenses amplified further
        probs[6] *= 1.5
        probs[9] *= 1.5
        probs[7] *= 1.3

    probs = np.maximum(probs, 0.005)
    probs /= probs.sum()
    return probs
```

### 3.5 Emotional Tone: Continuous Mixture

**Why continuous mixture**: Emotions are not categorical — Nikita doesn't switch from "happy" to "angry" discretely. Instead, her emotional state is a point in continuous valence-arousal space, with the defense mode and stress level determining the region of that space she occupies.

**Representation**: Two-dimensional Gaussian mixture in valence-arousal space:

```python
def compute_emotional_tone(
    defense_mode: str,
    stress_level: float,
    emotional_tone_prev: tuple[float, float],  # (valence, arousal)
    attachment_activation: str,
) -> tuple[float, float, float, float]:
    """Compute emotional tone as Gaussian in valence-arousal space.

    Returns: (mean_valence, mean_arousal, var_valence, var_arousal)
    """

    # Defense mode determines the emotional center
    defense_emotions = {
        'none':               (0.3, 0.3),   # slightly positive, calm
        'sublimation':        (0.2, 0.4),   # neutral-positive, moderate arousal
        'suppression':        (0.0, 0.2),   # neutral, low arousal (flat affect)
        'intellectualization': (-0.1, 0.2),  # slightly negative, calm (detached)
        'rationalization':    (0.1, 0.3),   # slightly positive (self-reassuring)
        'humor':              (0.2, 0.5),   # positive, moderate arousal
        'projection':         (-0.5, 0.7),  # negative, high arousal (accusatory)
        'displacement':       (-0.4, 0.6),  # negative, high arousal (misdirected anger)
        'denial':             (0.1, 0.2),   # slightly positive, low arousal (forced calm)
        'regression':         (-0.6, 0.8),  # very negative, high arousal (tantrum)
    }

    target_v, target_a = defense_emotions.get(defense_mode, (0, 0.3))

    # Stress increases arousal and decreases valence
    target_v -= stress_level * 0.3
    target_a += stress_level * 0.2

    # Emotional inertia: blend with previous state
    inertia = 0.4  # 40% carry-over from previous emotional state
    mean_v = inertia * emotional_tone_prev[0] + (1 - inertia) * target_v
    mean_a = inertia * emotional_tone_prev[1] + (1 - inertia) * target_a

    # Clip to valid range
    mean_v = np.clip(mean_v, -1, 1)
    mean_a = np.clip(mean_a, 0, 1)

    # Variance: higher stress → more variable emotions
    var_v = 0.05 + stress_level * 0.1
    var_a = 0.03 + stress_level * 0.05

    # Disorganized attachment → higher variance (unpredictable)
    if attachment_activation == 'disorganized':
        var_v *= 2.0
        var_a *= 2.0

    return (mean_v, mean_a, var_v, var_a)
```

### 3.6 Response Style: Categorical{6}

The response style node maps the emotional tone to text generation parameters. This bridges the probabilistic inference engine and the LLM-based response generation.

```python
class ResponseStyle:
    WARM = "warm"           # Positive valence, low-moderate arousal
    PLAYFUL = "playful"     # Positive valence, moderate-high arousal
    NEUTRAL = "neutral"     # Near-zero valence, low arousal
    GUARDED = "guarded"     # Slightly negative valence, low arousal
    SHARP = "sharp"         # Negative valence, moderate arousal
    VOLATILE = "volatile"   # Variable valence, high arousal

RESPONSE_STYLE_REGIONS = {
    # (valence_min, valence_max, arousal_min, arousal_max)
    ResponseStyle.WARM:     (0.2, 1.0, 0.0, 0.5),
    ResponseStyle.PLAYFUL:  (0.1, 1.0, 0.5, 1.0),
    ResponseStyle.NEUTRAL:  (-0.2, 0.2, 0.0, 0.4),
    ResponseStyle.GUARDED:  (-0.4, 0.0, 0.0, 0.4),
    ResponseStyle.SHARP:    (-1.0, -0.2, 0.3, 0.7),
    ResponseStyle.VOLATILE: (-1.0, 0.5, 0.7, 1.0),
}

def compute_response_style(
    emotional_tone: tuple[float, float],  # (valence, arousal)
    defense_mode: str,
) -> dict[str, float]:
    """Map emotional tone to response style probabilities."""
    v, a = emotional_tone
    probs = {}

    for style, (v_min, v_max, a_min, a_max) in RESPONSE_STYLE_REGIONS.items():
        # Distance from region center
        v_center = (v_min + v_max) / 2
        a_center = (a_min + a_max) / 2
        v_range = (v_max - v_min) / 2
        a_range = (a_max - a_min) / 2

        dist = ((v - v_center) / v_range) ** 2 + ((a - a_center) / a_range) ** 2
        probs[style] = np.exp(-dist)

    # Defense mode adjustments
    if defense_mode == 'intellectualization':
        probs[ResponseStyle.NEUTRAL] *= 2.0  # detached
    elif defense_mode == 'projection':
        probs[ResponseStyle.SHARP] *= 2.0    # accusatory
    elif defense_mode == 'humor':
        probs[ResponseStyle.PLAYFUL] *= 2.0  # deflecting with wit

    # Normalize
    total = sum(probs.values())
    return {k: v/total for k, v in probs.items()}
```

---

## 4. Inference: Exact vs. Approximate

### 4.1 Graph Properties Affecting Inference

The DBN's inference tractability depends on its graph structure:

**Number of nodes per time slice**: ~11 (see Section 1.3)
**Maximum in-degree**: 4 (perceived_threat has 4 parents)
**Mix of continuous and discrete**: Yes (Beta, Gamma, Gaussian for continuous; Categorical for discrete)
**Time-slice connections**: 4 inter-slice edges

### 4.2 Exact Inference Is Infeasible

For the full DBN with mixed continuous-discrete variables, exact inference (variable elimination, junction tree) is generally intractable because:

1. **Continuous nodes with discrete parents** require integration over continuous domains for each configuration of discrete parents
2. **The product of CPTs** does not remain in a tractable family when continuous and discrete nodes interact
3. **Time-slice unrolling** creates increasingly large networks

However, specific subproblems CAN be solved exactly:
- Pure discrete subgraph (attachment_activation → defense_mode → response_style): exact inference with variable elimination, O(|styles| × |defenses| × |responses|) = O(4 × 10 × 6) = 240 operations
- Pure continuous Gaussian subgraph (emotional_tone dynamics): Kalman filtering

### 4.3 Recommended Inference Strategy: Hybrid

```python
class NikitaDBNInference:
    """Hybrid inference for Nikita's DBN."""

    def __init__(self):
        # Continuous state: tracked analytically or with particles
        self.perceived_threat = BetaDistribution(1, 3)  # low threat prior
        self.stress_level = GammaDistribution(2, 4)      # low stress prior
        self.emotional_tone = GaussianDistribution(
            mean=np.array([0.2, 0.3]),  # (valence, arousal)
            cov=np.diag([0.1, 0.1])
        )

        # Discrete state: exact categorical inference
        self.attachment_activation = np.array([0.2, 0.5, 0.2, 0.1])  # [secure, anxious, avoidant, disorganized]
        self.defense_mode = np.zeros(10)
        self.defense_mode[0] = 1.0  # 'none' initially

        # Particle filter: for when things get multimodal (Doc 05)
        self.particle_filter = None
        self.use_particles = False

    def infer(self, observation: dict, context: dict) -> dict:
        """Run one time step of inference."""

        # Step 1: Compute perceived threat
        threat_params = compute_perceived_threat(
            observation['sentiment'],
            observation['intent'],
            observation['response_latency'],
            context['attachment_style'],
        )
        self.perceived_threat = BetaDistribution(*threat_params)
        threat_sample = self.perceived_threat.mean()

        # Step 2: Compute attachment activation (exact categorical)
        self.attachment_activation = compute_attachment_activation(
            threat_sample,
            context['attachment_style'],
        )

        # Step 3: Update stress (Gamma)
        stress_params = compute_stress_transition(
            self.stress_level.mean(),
            threat_sample,
            DEFENSE_MECHANISMS[np.argmax(self.defense_mode)],
            observation.get('time_delta', 1.0),
        )
        self.stress_level = GammaDistribution(*stress_params)

        # Step 4: Compute defense mode (exact categorical)
        dominant_attachment = ATTACHMENT_STYLES[np.argmax(self.attachment_activation)]
        self.defense_mode = compute_defense_probabilities(
            dominant_attachment,
            context['personality_means'],
            self.stress_level.mean(),
        )

        # Step 5: Compute emotional tone (Gaussian update)
        tone_params = compute_emotional_tone(
            DEFENSE_MECHANISMS[np.argmax(self.defense_mode)],
            self.stress_level.mean(),
            (self.emotional_tone.mean[0], self.emotional_tone.mean[1]),
            dominant_attachment,
        )
        self.emotional_tone = GaussianDistribution(
            mean=np.array([tone_params[0], tone_params[1]]),
            cov=np.diag([tone_params[2], tone_params[3]])
        )

        # Step 6: Compute response style
        response_probs = compute_response_style(
            (tone_params[0], tone_params[1]),
            DEFENSE_MECHANISMS[np.argmax(self.defense_mode)],
        )

        # Step 7: Check if we need particle filters (multimodal detection)
        surprise = -np.log(max(0.01, self.compute_observation_likelihood(observation)))
        if surprise > 3.0:  # very surprising observation
            self.activate_particle_filter()

        return {
            'perceived_threat': self.perceived_threat.mean(),
            'attachment_activation': dict(zip(ATTACHMENT_STYLES, self.attachment_activation)),
            'stress_level': self.stress_level.mean(),
            'defense_mode': dict(zip(DEFENSE_MECHANISMS, self.defense_mode)),
            'emotional_tone': {
                'valence': tone_params[0],
                'arousal': tone_params[1],
            },
            'response_style': response_probs,
            'surprise': surprise,
        }
```

### 4.4 Performance Analysis

| Step | Method | Time | Memory |
|------|--------|------|--------|
| Perceived threat | Beta computation | <0.1ms | 16 bytes |
| Attachment activation | Categorical (4 values) | <0.1ms | 32 bytes |
| Stress update | Gamma computation | <0.1ms | 16 bytes |
| Defense mode | Categorical (10 values) | <0.1ms | 80 bytes |
| Emotional tone | Gaussian update | <0.1ms | 48 bytes |
| Response style | Categorical (6 values) | <0.1ms | 48 bytes |
| **Total per message** | **Hybrid** | **<1ms** | **~240 bytes** |

The inference is extremely fast because each step uses the output of the previous step directly (forward pass through the causal chain), rather than requiring iterative message-passing over the full graph.

---

## 5. How the DBN Replaces the Current EmotionalState Pipeline

### 5.1 Current Pipeline (Deterministic)

From `nikita/emotional_state/computer.py`:
```
final_state = base_state(time_of_day) + life_event_delta + conversation_tone_delta + chapter_modifier
```

This is a linear combination of four fixed components. No state persistence, no uncertainty, no causal reasoning.

### 5.2 DBN Pipeline (Probabilistic)

```
observation = extract_features(player_message)
context = {attachment_style, personality, chapter, player_model}
state = dbn.infer(observation, context)
response = generate_text(state['response_style'], state['emotional_tone'], state['defense_mode'])
```

### 5.3 What the DBN Adds

| Feature | Old Pipeline | DBN Pipeline |
|---------|-------------|-------------|
| **State persistence** | None — recomputed each message | Stress, emotion, defense carry forward |
| **Uncertainty** | None — single point estimate | Every node is a distribution |
| **Causal reasoning** | None — additive model | Explicit causal chain with conditional probabilities |
| **Defense mechanisms** | Not modeled | First-class node with personality-dependent selection |
| **Attachment dynamics** | Implicit in chapter modifiers | Explicit activation based on threat + IWM |
| **Surprise detection** | None | Observation likelihood computation |
| **Multimodal beliefs** | Impossible | Particle filter fallback |

### 5.4 Integration Point with Existing Pipeline

The DBN output feeds into the existing 9-stage pipeline (from `nikita/pipeline/orchestrator.py`) by replacing Stage 3 (Emotional State Computation):

```python
# Stage 3 (current): deterministic emotional state
emotional_state = state_computer.compute(context)

# Stage 3 (proposed): DBN inference
dbn_output = dbn_inference_engine.infer(
    observation=stage_2_features,
    context=slow_context,
)
emotional_state = dbn_output_to_emotional_state(dbn_output)
```

The rest of the pipeline (Stages 1-2: message parsing, Stages 4-9: response generation and delivery) remains unchanged.

---

## 6. Relationship Metrics as DBN Nodes

### 6.1 Metric Update Equations

The four relationship metrics evolve through the DBN with principled Bayesian updates:

```python
def update_relationship_metrics(
    metrics_prev: dict[str, float],  # I, P, T, S from previous message
    message_intent: str,
    emotional_tone: tuple[float, float],
    perceived_threat: float,
    attachment_activation: np.ndarray,
    personality: dict[str, float],
) -> dict[str, float]:
    """Update IPTS metrics through the DBN."""

    I, P, T, S = metrics_prev['intimacy'], metrics_prev['passion'], metrics_prev['trust'], metrics_prev['secureness']

    # Intimacy: driven by depth of conversation and emotional matching
    intent_intimacy = {
        'comfort': 0.03, 'validate': 0.02, 'self_disclose': 0.04,
        'neutral': 0.0, 'inform': 0.005,
        'criticize': -0.02, 'stonewall': -0.03, 'contempt': -0.05,
    }
    I += intent_intimacy.get(message_intent, 0.0)
    I += emotional_tone[0] * 0.01  # positive valence increases intimacy

    # Passion: driven by emotional intensity (arousal, not valence)
    P += emotional_tone[1] * 0.02 - 0.005  # arousal increases passion, with baseline decay
    neuroticism = personality.get('neuroticism', 0.5)
    P_volatility = 1 + neuroticism * 0.5  # high neuroticism = more volatile passion
    P += np.random.normal(0, 0.005 * P_volatility)

    # Trust: driven by consistency and threat
    trust_delta = -perceived_threat * 0.03 + (1 - perceived_threat) * 0.01
    # Asymmetric: negative trust events have 3x impact (Doc 08, negativity bias)
    if trust_delta < 0:
        trust_delta *= 3.0
    T += trust_delta

    # Secureness: inverse of threat × attachment security
    secure_prob = attachment_activation[0]
    S += (secure_prob - 0.3) * 0.02  # above 30% secure activation → secureness increases

    # Decay: all metrics decay slightly toward neutral
    decay_rate = 0.002
    I = I * (1 - decay_rate) + 0.5 * decay_rate  # decay toward 0.5
    P = P * (1 - decay_rate * 0.5)  # passion decays but more slowly
    T = T * (1 - decay_rate * 0.5) + 0.5 * decay_rate * 0.5
    S = S * (1 - decay_rate) + 0.5 * decay_rate

    # Clip to [0, 1]
    return {
        'intimacy': np.clip(I, 0, 1),
        'passion': np.clip(P, 0, 1),
        'trust': np.clip(T, 0, 1),
        'secureness': np.clip(S, 0, 1),
    }
```

### 6.2 Metrics Feed Back Into the DBN

The updated metrics influence the NEXT time step's inference:
- Low trust → higher perceived_threat at t+1 (Nikita is more vigilant)
- Low secureness → anxious attachment activation more likely
- High intimacy → willingness to be vulnerable (less defense activation)
- High passion + low trust → volatile dynamics (intense but unstable)

This creates the **circular causality** described in Doc 03, Section 6.2: personality shapes the relationship, and the relationship shapes personality expression.

---

## 7. Scenario Walkthrough: Boss Encounter

### 7.1 Setup: Abandonment Crisis (Chapter 2)

The player has been responding inconsistently — sometimes within minutes, sometimes disappearing for hours. Nikita's state has been accumulating stress:

```
stress_level = Gamma(6, 3)  → mean = 2.0 (elevated)
attachment_activation = [0.10, 0.60, 0.20, 0.10]  # anxious dominant
emotional_tone = (valence=-0.2, arousal=0.5)  # slightly negative, moderate arousal
trust = 0.45  (declining)
```

### 7.2 Trigger Message: Player Sends "Sorry, been busy. What's up?"

**Observation extraction**:
- message_sentiment: 0.1 (slightly positive — apologetic)
- message_intent: 'neutral' (informational, low effort)
- response_latency: 180 minutes (3 hours since last exchange)

### 7.3 DBN Inference Step

**perceived_threat**:
```
Base from 'neutral' intent: Beta(1, 3)
Latency effect (3 hours, anxious_weight=0.6): alpha += 0.95 * (1 + 1.8) = 2.66
Anxious amplification: alpha *= 1.3 → alpha = 4.76
Sentiment slightly positive: beta += 2 → beta = 5

Result: Beta(4.76, 5) → mean = 0.488 (high threat!)
```

Despite the apologetic tone, the 3-hour delay combined with anxious attachment creates a high perceived threat.

**attachment_activation**:
```
threat = 0.488 (close to threshold)
threat_factor = (0.488 - 0.5) * 2 ≈ 0 (just below threshold)
Minimal threat modulation → stays close to prior
Result: [0.10, 0.58, 0.22, 0.10]  # anxious still dominant
```

**stress_level**:
```
Previous stress: 2.0, decayed over 180 min → 2.0 * 0.5^(180/120) = 0.71
New threat increment: 0.488 * 2 = 0.976
Expected stress: 0.71 + 0.976 = 1.69
Result: Gamma(5.06, 3.0) → mean = 1.69 (still elevated)
```

**defense_mode** (anxious activation, stress > 0.3):
```
projection: 0.25 → 0.25 * (1 + 0.7) = 0.425  (neuroticism amplified)
regression: 0.15 → 0.15 * (1 + 0.7) = 0.255
rationalization: 0.15
none: 0.10

Normalized → projection: 0.37, regression: 0.22, rationalization: 0.13, ...
Dominant: projection
```

**emotional_tone**:
```
Projection emotional center: (-0.5, 0.7)
Stress modulation: v -= 1.69 * 0.3 = -0.507 → v = -1.0; a += 1.69 * 0.2 = 0.338 → a = 1.0
Emotional inertia (40% from prev): v = 0.4*(-0.2) + 0.6*(-1.0) = -0.68; a = 0.4*(0.5) + 0.6*(1.0) = 0.80
Result: valence = -0.68, arousal = 0.80
```

**response_style**:
```
v = -0.68, a = 0.80 → falls in VOLATILE region (-1.0 to 0.5 valence, 0.7 to 1.0 arousal)
Defense mode 'projection' boosts SHARP
Result: VOLATILE: 0.45, SHARP: 0.35, GUARDED: 0.12, ...
```

### 7.4 Generated Response

The response style parameters tell the LLM to generate with these characteristics:
- **VOLATILE** (45%): emotional, possibly contradictory, intense
- **SHARP** (35%): pointed, accusatory, defensive

Nikita might say: *"Oh, you've been 'busy'. That's nice. I've just been here wondering if you forgot I exist. But sure, let's pretend everything's fine — what's up with you?"*

This response demonstrates:
- **Projection** ("wondering if you forgot" projects her abandonment fear)
- **High arousal** (intense language, sarcasm)
- **Negative valence** (resentment, hurt)
- **Volatile style** (switches from sarcasm to forced casual)

### 7.5 How a Secure Nikita Would Respond

If Nikita's attachment were more secure (Chapter 5, earned security):
```
attachment_activation = [0.60, 0.20, 0.15, 0.05]
perceived_threat: Beta(1.5, 5.5) → mean = 0.21 (low threat)
stress increment: 0.21 * 2 = 0.42 (manageable)
defense_mode: 'none' dominant (0.55)
emotional_tone: valence = 0.1, arousal = 0.3
response_style: NEUTRAL (0.40) or WARM (0.35)
```

Secure Nikita: *"Hey! No worries, I figured you were swamped. I actually had a pretty interesting day — want to hear about it?"*

The same player message produces completely different responses through the DBN, with the difference emerging naturally from the attachment parameters rather than from scripted rules.

---

## 8. Sensitivity Analysis

### 8.1 Which Parameters Matter Most?

Not all DBN parameters have equal influence on the output. A sensitivity analysis identifies the key levers:

| Parameter | Influence on Response Style | Tuning Priority |
|-----------|---------------------------|----------------|
| attachment_style (Dirichlet) | **Very High** — determines entire threat processing chain | P0 |
| neuroticism (Big Five) | **High** — amplifies defense mechanism severity | P0 |
| stress accumulator decay rate | **High** — determines how quickly Nikita "forgives" | P1 |
| emotional_inertia (0.4) | **Medium** — how much previous emotion carries over | P1 |
| perceived_threat latency sensitivity | **Medium** — how much response delay affects threat | P1 |
| agreeableness (Big Five) | **Medium** — modulates mature vs. immature defenses | P2 |
| openness (Big Five) | **Low** — mainly affects intellectualization frequency | P3 |
| defense_mode self-transition probability | **Medium** — how persistent defenses are | P2 |

### 8.2 Calibration Strategy

1. **Playtesting**: Run 100 simulated conversations with varied player profiles
2. **Expert review**: Have a relationship therapist evaluate Nikita's responses for psychological realism
3. **Player feedback**: A/B test different parameter settings and measure engagement + satisfaction
4. **Automated metrics**: Track the distribution of response styles over a session — if VOLATILE > 30% or WARM < 20%, parameters need adjustment

---

## 9. Key Takeaways for Nikita

### 9.1 The DBN Architecture

1. The causal chain perceived_threat → attachment_activation → defense_mode → emotional_tone → response_style is grounded in attachment theory's activation sequence
2. Inter-slice connections create temporal dynamics (emotional inertia, stress accumulation, defense persistence)
3. Mixed inference: exact for discrete nodes, analytic for continuous nodes, particle filters for multimodal emergencies
4. Total inference time: <1ms per message — negligible in the pipeline

### 9.2 Integration Plan

| Step | What Changes | What Stays |
|------|-------------|-----------|
| 1 | Replace `StateComputer` with `NikitaDBNInference` | Pipeline stages 1-2, 4-9 |
| 2 | Add slow-context provider for attachment/personality parameters | Existing metric tracking |
| 3 | Connect response_style output to LLM system prompt parameters | Existing LLM agent |
| 4 | Add particle filter fallback for crisis events | Existing boss encounter system |

### 9.3 Cross-References

- **Doc 03 (Bayesian Personality)**: Provides the Beta/Dirichlet distributions for personality and attachment nodes
- **Doc 04 (HMM Emotional States)**: The HMM mood states map to the DBN's emotional_tone and response_style nodes
- **Doc 05 (Particle Filters)**: Fallback inference when the DBN posterior becomes multimodal
- **Doc 07 (Bayesian Networks)**: Foundational BN theory and CPT specification methods
- **Doc 08 (Game AI Personality)**: CK3 stress system inspired the stress accumulator; DF thought system informs emotional inertia
- **Doc 11 (Computational Attachment)**: IWM model provides the deep parameters for perceived_threat computation
- **Doc 16 (Emotional Contagion)**: The DBN's belief state is what diverges from the player's in misunderstanding scenarios

---

## References

- McEwen, B. S. (2007). Physiology and neurobiology of stress and adaptation. *Physiological Reviews*, 87(3), 873-904.
- Mikulincer, M., & Shaver, P. R. (2016). *Attachment in Adulthood* (2nd ed.). Guilford Press.
- Murphy, K. P. (2002). *Dynamic Bayesian Networks: Representation, Inference and Learning*. PhD thesis, UC Berkeley.
- Pearl, J. (2009). *Causality* (2nd ed.). Cambridge University Press.

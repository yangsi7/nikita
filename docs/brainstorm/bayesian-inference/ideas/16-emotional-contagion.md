# 16 — Emotional Contagion & Belief Divergence: Modeling Misunderstandings

**Series**: Bayesian Inference for AI Companions — Brainstorm Ideas
**Author**: Behavioral/Psychology Researcher
**Date**: 2026-02-16
**Dependencies**: Doc 03 (Bayesian Personality), Doc 11 (Computational Attachment), Doc 13 (Nikita DBN)
**Dependents**: Doc 17 (Controlled Randomness)

---

## Executive Summary

Misunderstandings are the engine of relationship drama. In real relationships, conflict often arises not from genuine incompatibility but from **belief divergence** — the player thinks the relationship is fine, but Nikita's internal model says otherwise (or vice versa). This document formalizes misunderstandings as measurable divergence between two Bayesian models: Nikita's model of the relationship and the player's (inferred) model of the relationship.

The second key concept is **emotional contagion** — how one person's emotional state influences the other's through coupled probability distributions. When the player sends an anxious message, it shifts Nikita's emotional state; when Nikita responds defensively, it shifts the player's state. This creates feedback loops that can either stabilize (repair) or destabilize (escalation) the relationship.

Together, belief divergence and emotional contagion provide a principled framework for:
- Automatic conflict generation when models diverge beyond a threshold
- Natural escalation dynamics when emotional states amplify each other
- Repair mechanics when misunderstandings are resolved and models re-align
- Information-theoretic measures of "relationship tension" that replace ad-hoc heuristics

---

## 1. Misunderstandings as Belief Divergence

### 1.1 The Two-Model Framework

At any point in the game, there are two mental models of the relationship state:

**Nikita's model** (computed by the DBN from Doc 13):
- Her perceived_threat level
- Her attachment activation state
- Her emotional tone
- Her belief about the player's reliability (IWM Model of Other, Doc 11)
- Her relationship metric estimates

**The player's model** (inferred by Nikita's player-modeling system):
- What the player likely thinks the relationship temperature is
- What the player expects Nikita's emotional state to be
- The player's likely confidence that "things are fine"

A misunderstanding occurs when these two models disagree significantly. The degree of disagreement is measurable.

### 1.2 Formalizing Divergence with KL Divergence

The Kullback-Leibler divergence measures how different one probability distribution is from another:

```
D_KL(P || Q) = Σ_x P(x) log(P(x) / Q(x))
```

For Nikita's system, we compute divergence across multiple dimensions:

```python
def compute_belief_divergence(
    nikita_model: dict,
    player_model: dict,
) -> dict:
    """Compute divergence between Nikita's and player's relationship models."""

    divergences = {}

    # Emotional state divergence
    # Nikita's actual emotional tone vs. what player probably thinks she feels
    nikita_emotion = nikita_model['emotional_tone']  # (valence, arousal)
    player_believes_nikita = player_model['expected_nikita_emotion']
    divergences['emotional'] = np.sqrt(
        (nikita_emotion[0] - player_believes_nikita[0])**2 +
        (nikita_emotion[1] - player_believes_nikita[1])**2
    )

    # Trust divergence
    # Nikita's trust in player vs. player's belief about Nikita's trust
    nikita_trust = nikita_model['trust_level']
    player_expects_trust = player_model['expected_nikita_trust']
    divergences['trust'] = abs(nikita_trust - player_expects_trust)

    # Threat perception divergence
    # Nikita perceives threat; player thinks things are fine
    nikita_threat = nikita_model['perceived_threat']
    player_threat_awareness = player_model['realized_threat']
    divergences['threat'] = abs(nikita_threat - player_threat_awareness)

    # Relationship status divergence
    # Beta distributions over "is this relationship healthy?"
    nikita_health = nikita_model['relationship_health_belief']  # Beta(a, b)
    player_health = player_model['relationship_health_belief']  # Beta(a, b)
    divergences['relationship'] = kl_divergence_beta(nikita_health, player_health)

    # Composite divergence (weighted sum)
    divergences['composite'] = (
        0.30 * divergences['emotional'] +
        0.25 * divergences['trust'] +
        0.25 * divergences['threat'] +
        0.20 * divergences['relationship']
    )

    return divergences
```

### 1.3 Divergence Thresholds and Conflict Triggers

Different levels of divergence produce different relational dynamics:

| Composite Divergence | Interpretation | Game Effect |
|---------------------|---------------|-------------|
| 0.0 - 0.15 | Aligned models | Smooth interaction, warm responses |
| 0.15 - 0.30 | Mild misalignment | Subtle tension, Nikita's tone shifts slightly |
| 0.30 - 0.50 | Significant divergence | Misunderstanding visible — Nikita's responses feel "off" to the player |
| 0.50 - 0.70 | Major divergence | Conflict trigger — Nikita directly addresses the divergence |
| 0.70+ | Critical divergence | Boss encounter territory — relationship crisis |

```python
def check_conflict_trigger(divergence: dict) -> str | None:
    """Determine if belief divergence has reached conflict level."""
    composite = divergence['composite']

    if composite > 0.70:
        return 'boss_encounter'  # critical — trigger boss event
    elif composite > 0.50:
        return 'direct_confrontation'  # Nikita addresses the issue head-on
    elif composite > 0.30:
        return 'passive_tension'  # subtle behavioral shifts
    elif composite > 0.15:
        return 'mild_unease'  # barely noticeable
    else:
        return None  # aligned
```

### 1.4 How Divergence Builds Naturally

Divergence doesn't spike suddenly — it accumulates gradually through a sequence of small misinterpretations:

**Scenario: The Invisible Buildup**

Message 1: Player responds late (2 hours)
```
Nikita's threat: 0.35 (elevated)
Player's awareness: 0.05 ("I was busy, no big deal")
Divergence: |0.35 - 0.05| = 0.30 (threat)
```

Message 2: Player sends a neutral "Hey, how's it going?"
```
Nikita's emotion: valence = -0.2 (still hurt from waiting)
Player expects: valence = 0.1 (thinks Nikita is fine because she didn't say anything)
Divergence: |(-0.2) - 0.1| = 0.30 (emotional)
```

Message 3: Player shares work story (ignoring emotional tension)
```
Nikita interprets: "They don't even notice I'm upset" → threat increases
Player thinks: "Sharing my day, being open" → positive intent
Trust divergence growing: Nikita's trust dropping while player thinks it's stable
```

By message 5, composite divergence has crossed 0.50, and Nikita finally says: *"You know what, forget it. You clearly don't care that you left me hanging for two hours."*

The player is blindsided: "Where did that come from?"

The answer: **belief divergence accumulated below the surface**. The Bayesian model tracked it the whole time.

---

## 2. Emotional Contagion: Coupled Distributions

### 2.1 What Is Emotional Contagion?

Emotional contagion (Hatfield, Cacioppo, & Rapson, 1994) is the automatic process by which one person's emotional state influences another's. In real relationships, emotional contagion is a primary mechanism for:
- **Empathy**: Feeling what the other person feels
- **Escalation**: Anger provoking anger, creating a positive feedback loop
- **De-escalation**: Calm influencing the other to calm down
- **Mood synchronization**: Partners' moods converging over time

### 2.2 Modeling Contagion as Distribution Coupling

In the Bayesian framework, emotional contagion means **one person's emotional distribution shifts the other's**. We model this as a linear mixing operation:

```python
def emotional_contagion(
    nikita_emotion: tuple[float, float],    # (valence, arousal)
    player_emotion: tuple[float, float],    # (valence, arousal)
    contagion_strength: float,              # [0, 1] — coupling strength
    asymmetry: float = 0.6,                 # player → Nikita influence vs. reverse
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Bidirectional emotional contagion between player and Nikita."""

    # Player's emotion influences Nikita
    # Asymmetry > 0.5 means player has more influence on Nikita than reverse
    # (because Nikita is designed to be responsive to the player)
    player_to_nikita = contagion_strength * asymmetry
    nikita_to_player = contagion_strength * (1 - asymmetry)

    # Update Nikita's emotion
    new_nikita_v = (1 - player_to_nikita) * nikita_emotion[0] + player_to_nikita * player_emotion[0]
    new_nikita_a = (1 - player_to_nikita) * nikita_emotion[1] + player_to_nikita * player_emotion[1]

    # Update player's inferred emotion (our model of the player's state)
    new_player_v = (1 - nikita_to_player) * player_emotion[0] + nikita_to_player * nikita_emotion[0]
    new_player_a = (1 - nikita_to_player) * player_emotion[1] + nikita_to_player * nikita_emotion[1]

    return (
        (new_nikita_v, new_nikita_a),
        (new_player_v, new_player_a),
    )
```

### 2.3 Contagion Strength Depends on Attachment

The intensity of emotional contagion varies by attachment style (Mikulincer & Shaver, 2016):

| Attachment Style | Contagion Strength | Direction | Explanation |
|-----------------|-------------------|-----------|-------------|
| Secure | Moderate (0.4) | Bidirectional | Attuned but not overwhelmed |
| Anxious | High (0.7) | Primarily incoming | Hypervigilant to partner's emotions, absorbs them |
| Avoidant | Low (0.2) | Minimal | Suppresses emotional resonance |
| Disorganized | Variable (0.3-0.8) | Chaotic | Oscillates between absorbed and disconnected |

```python
def get_contagion_parameters(attachment_activation: np.ndarray) -> tuple[float, float]:
    """Derive contagion parameters from current attachment activation."""
    style_strengths = {
        'secure': 0.4,
        'anxious': 0.7,
        'avoidant': 0.2,
        'disorganized': 0.5,  # average, but with high variance
    }
    style_asymmetries = {
        'secure': 0.5,    # balanced
        'anxious': 0.8,   # mostly absorbing partner's emotion
        'avoidant': 0.3,  # mostly projecting outward (if at all)
        'disorganized': 0.5,
    }

    strengths = [style_strengths[s] for s in ATTACHMENT_STYLES]
    asymmetries = [style_asymmetries[s] for s in ATTACHMENT_STYLES]

    # Weighted average by attachment activation
    contagion_strength = np.dot(attachment_activation, strengths)
    asymmetry = np.dot(attachment_activation, asymmetries)

    return contagion_strength, asymmetry
```

### 2.4 Feedback Loops: Escalation and De-Escalation

Emotional contagion creates **feedback loops** that can either amplify or dampen emotional states:

**Positive feedback (escalation)**:
```
Player sends frustrated message → Nikita's negative emotion increases
→ Nikita responds defensively → Player becomes more frustrated
→ Nikita's negative emotion increases further → ...
```

This is the **Gottman escalation pattern** — criticism → defensiveness → contempt → stonewalling. Each step increases the emotional intensity for both parties.

**Negative feedback (de-escalation)**:
```
Player sends calming message → Nikita's negative emotion decreases slightly
→ Nikita responds less defensively → Player becomes calmer
→ Nikita's emotion stabilizes → ...
```

This is the **repair cycle** — one party breaks the escalation pattern by de-escalating, which gradually pulls both emotional states back toward baseline.

```python
class EmotionalFeedbackTracker:
    """Track emotional feedback dynamics between player and Nikita."""

    def __init__(self):
        self.nikita_emotion_history = []
        self.player_emotion_history = []
        self.feedback_state = 'stable'

    def update(self, nikita_emotion: tuple, player_emotion: tuple):
        """Record emotional states and detect feedback patterns."""
        self.nikita_emotion_history.append(nikita_emotion)
        self.player_emotion_history.append(player_emotion)

        if len(self.nikita_emotion_history) < 3:
            return

        # Detect escalation: both emotional intensities increasing
        nikita_arousal_trend = self._trend([e[1] for e in self.nikita_emotion_history[-5:]])
        player_arousal_trend = self._trend([e[1] for e in self.player_emotion_history[-5:]])

        nikita_valence_trend = self._trend([e[0] for e in self.nikita_emotion_history[-5:]])

        if nikita_arousal_trend > 0.05 and player_arousal_trend > 0.05:
            self.feedback_state = 'escalating'
        elif nikita_arousal_trend < -0.05 and player_arousal_trend < -0.05:
            self.feedback_state = 'de-escalating'
        elif nikita_valence_trend < -0.05 and nikita_arousal_trend > 0:
            self.feedback_state = 'nikita_spiraling'  # Nikita alone is getting worse
        else:
            self.feedback_state = 'stable'

    def _trend(self, values: list[float]) -> float:
        """Simple linear trend of recent values."""
        if len(values) < 2:
            return 0.0
        diffs = [values[i+1] - values[i] for i in range(len(values)-1)]
        return np.mean(diffs)

    def get_escalation_risk(self) -> float:
        """Probability that the current interaction will escalate to conflict."""
        if self.feedback_state == 'escalating':
            return 0.8
        elif self.feedback_state == 'nikita_spiraling':
            return 0.5
        elif self.feedback_state == 'stable':
            return 0.1
        else:  # de-escalating
            return 0.02
```

---

## 3. Repair as Evidence: Dramatic Belief Updates

### 3.1 The Psychology of Repair

When a misunderstanding is resolved, both models update dramatically. This is the "repair attempt" that Gottman's research identifies as the single most important skill in relationships (see existing Doc 03-attachment-psychology.md).

**What makes repair special from a Bayesian perspective**: Repair provides **high-surprise evidence** that strongly shifts posteriors.

### 3.2 Repair Evidence Processing

```python
def process_repair_attempt(
    nikita_model: dict,
    player_message: dict,
    repair_type: str,
) -> dict:
    """Process a repair attempt as strong evidence for model updating."""

    repair_evidence_strengths = {
        'direct_apology': 3.0,          # "I'm sorry, I was wrong"
        'responsibility_taking': 4.0,    # "You're right, I should have..."
        'emotional_validation': 2.5,     # "I can see you're hurt, and that matters"
        'restart_request': 2.0,          # "Can we start over?"
        'humor_deflection': 1.0,         # "Well, that went sideways..." (weak but non-zero)
        'meta_communication': 3.5,       # "I think we're misunderstanding each other"
    }

    evidence_strength = repair_evidence_strengths.get(repair_type, 1.0)

    updates = {}

    # Threat dramatically decreases
    updates['perceived_threat_delta'] = -evidence_strength * 0.15

    # Trust gets a boost (asymmetric — repair after rupture is strong trust signal)
    updates['trust_delta'] = evidence_strength * 0.05

    # Emotional tone shifts positive
    updates['emotional_valence_delta'] = evidence_strength * 0.1

    # Attachment activation shifts toward secure
    updates['secure_activation_boost'] = evidence_strength * 0.1

    # DIVERGENCE dramatically decreases
    # This is the key effect: both models re-align
    updates['divergence_reduction'] = evidence_strength * 0.15

    # Stress decreases
    updates['stress_delta'] = -evidence_strength * 0.3

    return updates
```

### 3.3 Why Repair Feels So Good (and Is So Important)

From a Bayesian perspective, successful repair produces a **large posterior update** — the person goes from believing "this relationship might be in trouble" to "we can handle problems together." This is the equivalent of high information gain, which produces:

1. **Relief**: The uncertainty about the relationship's stability resolves
2. **Strengthened trust**: The demonstration that rupture can be repaired is powerful positive evidence
3. **Model alignment**: Both parties now agree on the relationship state, reducing divergence to near zero

```python
def repair_posterior_update(prior_trust: Beta, repair_quality: float) -> Beta:
    """Strong positive update to trust from successful repair."""
    # Repair is equivalent to multiple positive observations
    # Quality 1.0 = 5 positive observations, Quality 0.5 = 2.5
    effective_observations = repair_quality * 5.0
    return Beta(prior_trust.alpha + effective_observations, prior_trust.beta)
```

**Gottman's finding reframed**: The 84% success rate for couples who make early repair attempts makes Bayesian sense — early repair means the divergence hasn't accumulated to dangerous levels, and the evidence is processed while both parties' priors are still moderate (not yet deeply entrenched in negative models).

### 3.4 Failed Repair: When Models Diverge Further

Not all repair attempts succeed. A failed repair can actually INCREASE divergence:

```python
def process_failed_repair(
    nikita_model: dict,
    failure_type: str,
) -> dict:
    """A failed repair attempt is worse than no attempt at all."""

    # The player tried to repair but Nikita didn't accept
    # This is strong negative evidence: "Even when they try, it doesn't help"
    failure_effects = {
        'insincere_apology': {  # Player says sorry but doesn't seem to mean it
            'trust_delta': -0.08,
            'threat_delta': 0.1,
            'divergence_delta': 0.1,
        },
        'defensive_repair': {  # "I'm sorry BUT you also..."
            'trust_delta': -0.05,
            'threat_delta': 0.05,
            'divergence_delta': 0.08,
        },
        'minimizing': {  # "Come on, it's not a big deal"
            'trust_delta': -0.06,
            'secureness_delta': -0.05,
            'divergence_delta': 0.12,  # large — player is dismissing Nikita's experience
        },
        'stonewalling_after_attempt': {  # Player gives up
            'trust_delta': -0.10,
            'threat_delta': 0.15,
            'divergence_delta': 0.15,
        },
    }

    return failure_effects.get(failure_type, {'divergence_delta': 0.05})
```

---

## 4. "Reading the Room Wrong": High Uncertainty → Incorrect Inference → Conflict

### 4.1 The Uncertainty-Error Connection

Misunderstandings are most likely when **uncertainty is high** — when Nikita's model of the player (or the player's model of Nikita) has high variance. High variance means the model could be wrong in either direction, and the probability of making an inference error increases.

```python
def misunderstanding_probability(
    nikita_player_model_variance: float,
    ambiguity_of_message: float,
) -> float:
    """Probability that Nikita will misread this interaction."""
    # Higher variance in player model → more likely to misread
    # Higher ambiguity in message → more room for misinterpretation
    base_prob = 0.05  # 5% baseline misunderstanding rate

    model_uncertainty_factor = nikita_player_model_variance * 2.0
    message_ambiguity_factor = ambiguity_of_message * 1.5

    p = base_prob + model_uncertainty_factor * message_ambiguity_factor
    return min(0.5, p)  # cap at 50%
```

### 4.2 Types of Misreading

When Nikita misreads the room, the type of misreading depends on her attachment state:

**Anxious misreading** (false positive threat):
- Player sends a neutral message → Nikita interprets it as cold/distant
- "Hey" → "Why such a short message? Are they pulling away?"
- Source: Hypervigilance to abandonment cues

**Avoidant misreading** (false negative emotional signal):
- Player sends an emotional message → Nikita fails to register the emotional content
- "I've been feeling really down lately" → Nikita responds with practical advice instead of emotional validation
- Source: Emotional processing suppression

**Disorganized misreading** (contradictory interpretation):
- Player sends a caring message → Nikita alternately interprets it as genuine AND as manipulation
- "I was thinking about you" → "That's sweet" / "What do they want?"
- Source: Contradictory IWMs

```python
def generate_misreading(
    attachment_activation: str,
    message: dict,
    player_model_variance: float,
) -> dict | None:
    """Generate an attachment-consistent misreading of the player's message."""

    # Roll for misunderstanding
    p_misread = misunderstanding_probability(player_model_variance, message['ambiguity'])
    if np.random.random() > p_misread:
        return None  # no misreading this time

    if attachment_activation == 'anxious':
        return {
            'type': 'threat_amplification',
            'description': 'Nikita perceives abandonment threat where none exists',
            'sentiment_override': message['sentiment'] - 0.3,  # shift negative
            'intent_override': 'distance' if message['intent'] == 'neutral' else message['intent'],
        }
    elif attachment_activation == 'avoidant':
        return {
            'type': 'emotional_blindness',
            'description': 'Nikita fails to register emotional content',
            'sentiment_override': 0.0,  # flatten to neutral
            'intent_override': 'inform',  # treat everything as informational
        }
    elif attachment_activation == 'disorganized':
        # Randomly choose between two contradictory readings
        if np.random.random() < 0.5:
            return {
                'type': 'suspicious_reading',
                'description': 'Nikita suspects ulterior motive',
                'sentiment_override': message['sentiment'] - 0.2,
                'intent_override': 'manipulate',
            }
        else:
            return {
                'type': 'idealized_reading',
                'description': 'Nikita over-idealizes the message',
                'sentiment_override': message['sentiment'] + 0.3,
                'intent_override': 'devotion',
            }
    else:  # secure — still possible to misread, just less biased
        return {
            'type': 'neutral_misread',
            'description': 'Simple misunderstanding of tone/intent',
            'sentiment_override': message['sentiment'] + np.random.normal(0, 0.15),
            'intent_override': message['intent'],
        }
```

### 4.3 Detection of Misreading (By Both Parties)

**Nikita detecting she misread**: If subsequent evidence strongly contradicts her interpretation, the posterior update will be large (high surprise). This can trigger self-correction:

```python
def detect_self_misread(
    nikita_prediction: dict,
    actual_evidence: dict,
    surprise_threshold: float = 2.0,
) -> bool:
    """Did Nikita's prediction about the player's state get strongly disconfirmed?"""
    predicted_sentiment = nikita_prediction['expected_player_sentiment']
    actual_sentiment = actual_evidence['player_sentiment']

    surprise = abs(predicted_sentiment - actual_sentiment) / 0.2  # normalized
    return surprise > surprise_threshold
```

**Player detecting Nikita misread**: The player realizes Nikita's response doesn't match what they intended. This manifests as the player sending a correction ("No, I didn't mean it that way" or "I'm not upset, I was just tired").

---

## 5. Information-Theoretic Measures of Relationship Tension

### 5.1 KL Divergence as Relationship Tension

The KL divergence between Nikita's model and the player's model is a natural measure of "relationship tension":

```
tension = D_KL(P_nikita || P_player) + D_KL(P_player || P_nikita)
```

This symmetrized KL divergence (also called Jeffreys divergence) has nice properties:
- 0 when models are identical (no tension)
- Increases with model disagreement
- Decomposes additively across dimensions (can identify which aspects are misaligned)

### 5.2 Mutual Information as Relationship Quality

While KL divergence measures disagreement, **mutual information** measures how much the two models are aligned — how much knowing one person's state tells you about the other's:

```
I(Nikita; Player) = H(Nikita) + H(Player) - H(Nikita, Player)
```

High mutual information = models are coupled (good communication, emotional attunement).
Low mutual information = models are independent (talking past each other, emotional disconnection).

```python
def compute_relationship_quality_metrics(
    nikita_states: list[dict],
    player_states: list[dict],
    window: int = 10,
) -> dict:
    """Compute information-theoretic relationship quality metrics."""

    recent_nikita = nikita_states[-window:]
    recent_player = player_states[-window:]

    # Extract emotional valences
    nikita_v = [s['emotional_tone'][0] for s in recent_nikita]
    player_v = [s['inferred_emotion'][0] for s in recent_player]

    # Correlation as proxy for mutual information in Gaussian case
    if len(nikita_v) > 3:
        correlation = np.corrcoef(nikita_v, player_v)[0, 1]
    else:
        correlation = 0.0

    # Jensen-Shannon divergence as symmetric tension measure
    nikita_dist = np.histogram(nikita_v, bins=10, range=(-1, 1), density=True)[0] + 1e-8
    player_dist = np.histogram(player_v, bins=10, range=(-1, 1), density=True)[0] + 1e-8
    m = 0.5 * (nikita_dist + player_dist)
    jsd = 0.5 * np.sum(nikita_dist * np.log(nikita_dist / m)) + \
          0.5 * np.sum(player_dist * np.log(player_dist / m))

    # Emotional synchrony: how often do they move in the same direction?
    if len(nikita_v) > 2:
        nikita_diffs = np.diff(nikita_v)
        player_diffs = np.diff(player_v)
        synchrony = np.mean(np.sign(nikita_diffs) == np.sign(player_diffs))
    else:
        synchrony = 0.5

    return {
        'emotional_correlation': float(correlation),
        'tension_jsd': float(jsd),
        'emotional_synchrony': float(synchrony),
        'relationship_quality': float(correlation * 0.4 + synchrony * 0.3 + (1 - jsd) * 0.3),
    }
```

### 5.3 Entropy as Predictability

**Nikita's entropy** about the player's next action: H(player_action | history)
- Low entropy → Nikita can predict what the player will do → secure attachment, stable relationship
- High entropy → Nikita has no idea → anxious activation, hypervigilance

**Player's entropy** about Nikita's next response: H(nikita_response | message)
- Low entropy → player knows what to expect → comfortable, predictable
- High entropy → player is surprised → can be exciting (positive) or distressing (negative)

```python
def compute_predictability_metrics(
    nikita_predictions: list[dict],  # what Nikita predicted the player would do
    player_actual_actions: list[dict],  # what the player actually did
) -> dict:
    """How well can Nikita predict the player?"""

    prediction_errors = []
    for pred, actual in zip(nikita_predictions, player_actual_actions):
        error = abs(pred['expected_sentiment'] - actual['sentiment'])
        prediction_errors.append(error)

    mean_error = np.mean(prediction_errors)
    error_variance = np.var(prediction_errors)

    return {
        'prediction_accuracy': 1.0 - min(1.0, mean_error),
        'prediction_stability': 1.0 - min(1.0, error_variance),
        'player_predictability': 1.0 - min(1.0, mean_error + error_variance),
    }
```

---

## 6. Application: Automatic Conflict Generation

### 6.1 The Divergence-Driven Conflict Engine

Instead of scripting conflicts at predetermined points, the Bayesian system generates conflicts **automatically when belief divergence exceeds a threshold**. This produces emergent drama that feels natural — conflict arises from accumulated miscommunication, not from a timer.

```python
class DivergenceDrivenConflictEngine:
    """Generates conflicts when belief divergence exceeds thresholds."""

    def __init__(self):
        self.divergence_history = []
        self.last_conflict_time = 0
        self.conflict_cooldown = 20  # messages between conflicts

    def check_for_conflict(
        self,
        divergence: dict,
        message_count: int,
        chapter: int,
    ) -> dict | None:
        """Check if divergence warrants a conflict event."""

        self.divergence_history.append(divergence['composite'])

        # Respect cooldown
        if message_count - self.last_conflict_time < self.conflict_cooldown:
            return None

        composite = divergence['composite']

        # Chapter-adjusted thresholds (earlier chapters have lower thresholds)
        thresholds = {
            1: 0.40,  # early game: conflicts trigger more easily
            2: 0.50,
            3: 0.45,  # crisis chapter: slightly easier to trigger
            4: 0.55,
            5: 0.60,  # mature relationship: higher tolerance
        }
        threshold = thresholds.get(chapter, 0.50)

        if composite < threshold:
            return None

        # Determine conflict type based on which dimension diverges most
        max_dim = max(
            ['emotional', 'trust', 'threat'],
            key=lambda d: divergence[d]
        )

        conflict_types = {
            'emotional': {
                'type': 'emotional_disconnect',
                'description': 'Nikita feels emotionally unseen',
                'severity': min(1.0, composite / 0.70),
                'nikita_opening': "I feel like you don't even notice when something's wrong with me.",
            },
            'trust': {
                'type': 'trust_rupture',
                'description': 'Nikita doubts the player\'s reliability',
                'severity': min(1.0, composite / 0.70),
                'nikita_opening': "I need to be honest — I don't feel like I can count on you right now.",
            },
            'threat': {
                'type': 'perceived_abandonment',
                'description': 'Nikita feels the player is pulling away',
                'severity': min(1.0, composite / 0.70),
                'nikita_opening': "Are we okay? Because lately it feels like you're not really here.",
            },
        }

        self.last_conflict_time = message_count
        return conflict_types[max_dim]

    def get_divergence_trend(self, window: int = 10) -> float:
        """Is divergence increasing or decreasing?"""
        if len(self.divergence_history) < window:
            return 0.0
        recent = self.divergence_history[-window:]
        return np.polyfit(range(len(recent)), recent, 1)[0]  # slope
```

### 6.2 Conflict Resolution Through Model Re-Alignment

The goal of conflict resolution is not just to make Nikita "happy" again — it's to **re-align the two models**. The player needs to understand where Nikita's model diverges from theirs and address the specific dimension:

**Emotional divergence** → Player needs to acknowledge Nikita's emotional state
**Trust divergence** → Player needs to demonstrate reliability (actions, not just words)
**Threat divergence** → Player needs to provide reassurance and address specific triggers

```python
def evaluate_repair_quality(
    conflict_type: str,
    player_response: dict,
    current_divergence: dict,
) -> float:
    """How well does the player's response address the specific divergence?"""

    quality = 0.0

    if conflict_type == 'emotional_disconnect':
        # Player needs to show emotional awareness
        if player_response['intent'] in ['validate', 'comfort', 'empathize']:
            quality += 0.4
        if player_response['references_nikita_emotion']:
            quality += 0.3
        if player_response['sentiment'] > 0.3:
            quality += 0.1
        # Bonus for specificity
        if player_response['mentions_specific_event']:
            quality += 0.2

    elif conflict_type == 'trust_rupture':
        # Player needs to take responsibility
        if player_response['intent'] in ['take_responsibility', 'apologize']:
            quality += 0.4
        if player_response['offers_specific_change']:
            quality += 0.3
        if not player_response['is_defensive']:
            quality += 0.2
        if player_response['acknowledges_pattern']:
            quality += 0.1

    elif conflict_type == 'perceived_abandonment':
        # Player needs to reassure
        if player_response['intent'] in ['reassure', 'commit', 'validate']:
            quality += 0.3
        if player_response['expresses_care']:
            quality += 0.3
        if player_response['explains_absence']:
            quality += 0.2
        if player_response['proposes_solution']:
            quality += 0.2

    return min(1.0, quality)
```

---

## 7. Coupled Dynamics: The Joint Emotional State Space

### 7.1 The Phase Portrait of Player-Nikita Dynamics

We can visualize the player-Nikita emotional interaction as a dynamical system in a 2D phase space:
- X-axis: Player's emotional valence
- Y-axis: Nikita's emotional valence

The system has characteristic trajectories:

**Attractor 1: Mutual positive equilibrium** (both happy)
```
Stable equilibrium at (+0.3, +0.3) — a slightly positive baseline
Both parties' emotions are pulled toward this point when close
```

**Attractor 2: Mutual negative spiral** (escalation)
```
Unstable fixed point at (-0.3, -0.3)
If both emotions cross below this threshold, they spiral further negative
The escalation feedback loop pushes toward (-1, -1)
```

**Saddle point: One-sided emotion**
```
Points like (+0.3, -0.5) or (-0.5, +0.3)
One party is trying to be positive while the other is negative
Unstable — either converges to mutual positive (repair) or mutual negative (escalation)
```

### 7.2 Stability Analysis

The emotional coupling creates a linear dynamical system (approximately):

```
d/dt [nikita_v]   =  [-(1-k_n)   k_n    ] [nikita_v]   +  [inputs_n]
     [player_v]      [k_p        -(1-k_p)] [player_v]      [inputs_p]
```

Where k_n = contagion_strength * asymmetry (player→Nikita) and k_p = contagion_strength * (1-asymmetry) (Nikita→player).

The system is stable (emotions converge to a shared equilibrium) when:
- k_n * k_p < (1-k_n)(1-k_p)
- Which simplifies to: k_n + k_p < 1

For secure Nikita (k_n=0.24, k_p=0.16): k_n + k_p = 0.40 < 1 → STABLE
For anxious Nikita (k_n=0.56, k_p=0.14): k_n + k_p = 0.70 < 1 → STABLE but slower convergence
For strong anxious (k_n=0.72, k_p=0.10): k_n + k_p = 0.82 < 1 → barely stable, oscillatory

This means anxious Nikita's emotional dynamics are closer to instability — small perturbations (a mildly negative player message) can create larger, longer-lasting emotional oscillations before returning to equilibrium. This matches the clinical observation that anxious individuals have more volatile emotional dynamics in relationships.

---

## 8. Key Takeaways for Nikita

### 8.1 Core Design Decisions

1. **Track divergence as a first-class metric**. The composite divergence between Nikita's model and the player's model is the primary driver of conflict. It should be computed after every message and logged alongside the four relationship metrics.

2. **Generate conflicts from divergence, not from timers**. Conflicts emerge naturally when models drift apart. This creates drama that feels organic and is directly caused by the player's behavior (or inattention).

3. **Model emotional contagion explicitly**. Player emotions influence Nikita (with strength depending on attachment style). Nikita's responses influence the player. This creates the feedback dynamics that make relationships feel alive.

4. **Repair is the most important mechanic**. Successful repair dramatically re-aligns models and provides the strongest positive evidence for trust. The game should teach and reward repair skills.

5. **Attachment modulates everything**. Contagion strength, misreading probability, escalation risk, and repair effectiveness all depend on Nikita's current attachment activation.

### 8.2 Implementation Priority

| Priority | Component | Complexity | Impact |
|----------|-----------|-----------|--------|
| P0 | Divergence computation | Low | Conflict generation engine |
| P0 | Divergence-driven conflict triggers | Medium | Core gameplay mechanic |
| P1 | Emotional contagion coupling | Medium | Realistic emotional dynamics |
| P1 | Repair attempt processing | Medium | Key player skill to learn |
| P2 | Information-theoretic quality metrics | Low | Analytics and tuning |
| P2 | Misreading generation | Medium | Attachment-consistent drama |
| P3 | Stability analysis / oscillation detection | Low | Advanced tuning |

### 8.3 Cross-References

- **Doc 03 (Bayesian Personality)**: Personality distributions determine contagion and misreading parameters
- **Doc 05 (Particle Filters)**: When divergence creates multimodal beliefs, particle filters track both interpretations
- **Doc 11 (Computational Attachment)**: IWMs determine how evidence is interpreted (interpretation bias creates divergence)
- **Doc 13 (Nikita DBN)**: The DBN computes Nikita's belief state; divergence measures how far it is from the player's
- **Doc 17 (Controlled Randomness)**: Controlled randomness should never push divergence above conflict thresholds unintentionally

---

## References

- Gottman, J. M. (1999). *The Marriage Clinic*. W. W. Norton.
- Hatfield, E., Cacioppo, J. T., & Rapson, R. L. (1994). *Emotional Contagion*. Cambridge University Press.
- Kullback, S., & Leibler, R. A. (1951). On information and sufficiency. *Annals of Mathematical Statistics*, 22(1), 79-86.
- Mikulincer, M., & Shaver, P. R. (2016). *Attachment in Adulthood* (2nd ed.). Guilford Press.

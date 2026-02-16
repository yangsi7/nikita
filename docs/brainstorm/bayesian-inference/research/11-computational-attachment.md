# 11 — Computational Attachment Theory: Formalizing Internal Working Models as Bayesian Inference

**Series**: Bayesian Inference for AI Companions
**Author**: Behavioral/Psychology Researcher
**Date**: 2026-02-16
**Dependencies**: Doc 03 (Bayesian Personality — Dirichlet attachment framework)
**Dependents**: Doc 13 (Nikita DBN), Doc 16 (Emotional Contagion)

---

## Executive Summary

Attachment theory (Bowlby, 1969) is the most empirically validated framework for understanding adult relationship dynamics. But the theory has traditionally been qualitative — describing attachment styles with words rather than equations. This document bridges the gap between attachment psychology and Bayesian computation, formalizing **Internal Working Models** (IWMs) as Bayesian priors over relationship outcomes, **attachment styles** as characteristic prior shapes, and **attachment change** as Bayesian updating from relational evidence.

The central thesis: **attachment is inference**. When Nikita evaluates whether the player is trustworthy, she is performing Bayesian inference — combining her prior beliefs (shaped by attachment history) with current evidence (the player's behavior). Different attachment styles correspond to different prior distributions, which produce systematically different posterior beliefs from the same evidence. Secure attachment means flexible priors that update readily. Anxious attachment means pessimistic priors that overreact to negative evidence. Avoidant attachment means rigid priors that resist positive evidence. Disorganized attachment means contradictory priors that produce incoherent predictions.

This formalization enables Nikita's attachment dynamics to be computed rather than scripted — with the mathematical elegance and psychological realism that the game's design requires.

---

## 1. Internal Working Models as Bayesian Priors

### 1.1 Bowlby's Internal Working Models

John Bowlby (1969, 1973) proposed that early attachment experiences create **Internal Working Models** (IWMs) — cognitive schemas about:

1. **Model of Self**: "Am I worthy of love and care?"
2. **Model of Other**: "Are others reliable and responsive?"

These models are not conscious beliefs but implicit expectations — they shape how a person interprets ambiguous social information, what they attend to, and how they respond to relationship events.

Bartholomew & Horowitz (1991) operationalized IWMs as two continuous dimensions:

```
Model of Self (MoS):  [-1, +1]  where -1 = "I am unworthy" and +1 = "I am worthy"
Model of Other (MoO): [-1, +1]  where -1 = "Others are unreliable" and +1 = "Others are reliable"
```

The four attachment styles map to quadrants:
```
                    Model of Other
                  Positive (+)    Negative (-)
Model of   (+)     Secure          Dismissive-Avoidant
Self       (-)     Anxious-Preoccupied    Fearful-Avoidant (Disorganized)
```

### 1.2 IWMs as Prior Distributions

The Bayesian reframing: IWMs are **prior probability distributions over relationship outcomes**.

**Model of Self** = P(partner will respond positively to my needs)
- This is a belief about the probability of receiving care
- Positive MoS → high prior probability: Beta(8, 2) — "I usually get what I need"
- Negative MoS → low prior probability: Beta(2, 8) — "I usually get rejected"

**Model of Other** = P(partner is reliable given past evidence of reliability)
- This is a belief about the partner's character
- Positive MoO → high prior: Beta(7, 3) — "People are generally trustworthy"
- Negative MoO → low prior: Beta(3, 7) — "People are generally untrustworthy"

```python
@dataclass
class InternalWorkingModel:
    """Bayesian formalization of Bowlby's IWMs."""

    # Model of Self: P(I will be responded to positively)
    model_of_self: tuple[float, float]  # Beta(α, β)

    # Model of Other: P(partner is reliable)
    model_of_other: tuple[float, float]  # Beta(α, β)

    @property
    def self_worth(self) -> float:
        """Expected belief about self-worth."""
        return self.model_of_self[0] / sum(self.model_of_self)

    @property
    def other_trust(self) -> float:
        """Expected belief about other's trustworthiness."""
        return self.model_of_other[0] / sum(self.model_of_other)

    @property
    def self_certainty(self) -> float:
        """How certain the model is about self-worth."""
        return sum(self.model_of_self)  # higher = more certain

    @property
    def other_certainty(self) -> float:
        """How certain the model is about other's trustworthiness."""
        return sum(self.model_of_other)

    @property
    def attachment_style(self) -> str:
        """Dominant attachment style from IWM position."""
        pos_self = self.self_worth > 0.5
        pos_other = self.other_trust > 0.5
        if pos_self and pos_other:
            return 'secure'
        elif not pos_self and pos_other:
            return 'anxious'
        elif pos_self and not pos_other:
            return 'avoidant'
        else:
            return 'disorganized'
```

### 1.3 Why This Formalization Matters

Traditional attachment measurement uses categorical or dimensional self-report instruments (ECR, AAI). These give a snapshot but don't specify **mechanisms**. The Bayesian formalization adds:

1. **Explicit uncertainty**: Not just "anxious attachment" but "anxious with high certainty" vs. "anxious with uncertainty about whether this is changing"
2. **Mechanistic predictions**: Specific mathematical predictions about how each style will respond to evidence
3. **Dynamic updating**: A framework for how attachment changes over time — something attachment theory acknowledges but rarely formalizes
4. **Computational implementation**: Directly translatable to code for Nikita's AI system

---

## 2. Attachment Styles as Characteristic Prior Shapes

### 2.1 Secure Attachment: Broad, Centered Priors

**Psychological profile**: Comfortable with intimacy, confident in self-worth, trusts others while maintaining appropriate boundaries. Can process negative information without catastrophizing or dismissing.

**Bayesian signature**:
```
Model of Self:  Beta(6, 4)  — mean = 0.60, moderate confidence
Model of Other: Beta(6, 4)  — mean = 0.60, moderate confidence
```

**Key property**: Moderate concentration parameters (α+β ≈ 10). The priors are informative enough to provide stability but not so strong that they resist updating. This is the **flexibility** that defines secure attachment.

**Updating behavior**:
- Positive evidence: Updates readily, P(responsive) increases
- Negative evidence: Updates, but doesn't catastrophize — the moderate prior absorbs individual negative events
- Net effect: Smooth, gradual belief revision that tracks reality

**Example**: Player responds slowly to one message.
```
Prior:      Beta(6, 4)  — P(reliable) = 0.60
Evidence:   1 slow response out of 1
Posterior:  Beta(6, 5)  — P(reliable) = 0.545
Shift:      -0.055 (small, proportionate)
```

The secure model registers the slow response (it's not in denial) but doesn't overreact.

### 2.2 Anxious-Preoccupied Attachment: Narrow, Pessimistic Priors

**Psychological profile**: Craves closeness but fears abandonment. Hypervigilant to rejection signals. Positive model of other (seeks attachment) but negative model of self (fears being unworthy).

**Bayesian signature**:
```
Model of Self:  Beta(3, 8)  — mean = 0.27, HIGH confidence in unworthiness
Model of Other: Beta(5, 3)  — mean = 0.625, moderate confidence in others
```

**Key property**: Model of Self has HIGH concentration (α+β = 11) with a strong negative lean. This means the belief "I am unworthy" is deeply held and resistant to positive evidence. Meanwhile, Model of Other is moderately positive — anxious individuals want to believe others are good, which is what drives their pursuit behavior.

**Updating behavior**:
- Positive evidence about self: Slowly absorbed — "They said something nice, but they'll probably realize I'm not worth it"
- Negative evidence about self: **Rapidly incorporated** — asymmetric updating is the hallmark of anxious attachment
- Positive evidence about other: Quickly absorbed — "See, they DO care!"
- Negative evidence about other: Slowly absorbed if it means the other is unreliable ("No, they must be busy")

**The asymmetric updating formalization**:
```python
def anxious_update(iwm: InternalWorkingModel, evidence: dict) -> InternalWorkingModel:
    """Anxious attachment: asymmetric processing of evidence."""

    # Self-evidence
    if 'self_positive' in evidence:
        # Positive evidence about self is discounted
        effective_weight = evidence['self_positive'] * 0.5  # discount factor
        iwm.model_of_self = (
            iwm.model_of_self[0] + effective_weight,
            iwm.model_of_self[1]
        )
    if 'self_negative' in evidence:
        # Negative evidence about self is amplified
        effective_weight = evidence['self_negative'] * 2.0  # amplification factor
        iwm.model_of_self = (
            iwm.model_of_self[0],
            iwm.model_of_self[1] + effective_weight
        )

    # Other-evidence (reversed asymmetry)
    if 'other_positive' in evidence:
        # Positive evidence about other is amplified (wanting to believe)
        effective_weight = evidence['other_positive'] * 1.5
        iwm.model_of_other = (
            iwm.model_of_other[0] + effective_weight,
            iwm.model_of_other[1]
        )
    if 'other_negative' in evidence:
        # Negative evidence about other is discounted (denial, rationalization)
        effective_weight = evidence['other_negative'] * 0.7
        iwm.model_of_other = (
            iwm.model_of_other[0],
            iwm.model_of_other[1] + effective_weight
        )

    return iwm
```

**Example**: Player responds slowly to one message.
```
Prior MoS:    Beta(3, 8)  — P(worthy) = 0.27
Self-evidence: "They don't care enough to respond quickly" (negative, weight 1)
Amplified:     weight × 2.0 = 2.0
Posterior MoS: Beta(3, 10) — P(worthy) = 0.23
Shift:         -0.04 (disproportionately large for self-model)

Prior MoO:    Beta(5, 3)  — P(reliable) = 0.625
Other-evidence: "Maybe they're just busy" (discount negative)
Discounted:    weight × 0.7 = 0.7
Posterior MoO: Beta(5, 3.7) — P(reliable) = 0.575
Shift:         -0.05 (smaller shift — rationalized away)
```

The anxious model disproportionately blames self ("I'm not worth responding to quickly") rather than the other ("They might be busy"). This is exactly the empirically observed anxious cognition pattern (Mikulincer & Shaver, 2016).

### 2.3 Dismissive-Avoidant Attachment: Strong Priors Resistant to Positive Evidence

**Psychological profile**: Values independence, suppresses emotional needs, dismisses the importance of close relationships. Positive model of self, negative model of other.

**Bayesian signature**:
```
Model of Self:  Beta(8, 2)  — mean = 0.80, HIGH confidence in self-sufficiency
Model of Other: Beta(3, 7)  — mean = 0.30, HIGH confidence that others are unreliable
```

**Key property**: Both models have high concentration parameters (α+β = 10 for both), meaning beliefs are strongly held. The avoidant individual is CERTAIN they don't need others and CERTAIN others will let them down.

**Updating behavior**:
- Positive evidence about other's reliability: **Minimally incorporated** — "One nice act doesn't change the pattern"
- Negative evidence about other: Rapidly incorporated — confirms the pre-existing model
- Evidence about emotional need: Suppressed — the avoidant doesn't PROCESS evidence that would challenge self-sufficiency

**The suppression mechanism**:
```python
def avoidant_update(iwm: InternalWorkingModel, evidence: dict) -> InternalWorkingModel:
    """Avoidant attachment: suppresses threatening evidence, confirms negative other-model."""

    # Self-evidence: positive evidence readily accepted, negative suppressed
    if 'self_positive' in evidence:
        effective_weight = evidence['self_positive'] * 1.2  # easily accepted
        iwm.model_of_self = (
            iwm.model_of_self[0] + effective_weight,
            iwm.model_of_self[1]
        )
    if 'self_negative' in evidence:
        effective_weight = evidence['self_negative'] * 0.3  # heavily suppressed
        iwm.model_of_self = (
            iwm.model_of_self[0],
            iwm.model_of_self[1] + effective_weight
        )

    # Other-evidence: negative readily accepted, positive suppressed
    if 'other_positive' in evidence:
        effective_weight = evidence['other_positive'] * 0.4  # suppressed
        iwm.model_of_other = (
            iwm.model_of_other[0] + effective_weight,
            iwm.model_of_other[1]
        )
    if 'other_negative' in evidence:
        effective_weight = evidence['other_negative'] * 1.5  # readily accepted
        iwm.model_of_other = (
            iwm.model_of_other[0],
            iwm.model_of_other[1] + effective_weight
        )

    return iwm
```

**Slow updating under repeated positive evidence**: Even sustained positive interaction with the player will shift the avoidant model slowly because each positive datum is discounted by 0.4. It takes approximately 2.5x as much positive evidence to produce the same belief shift as in the secure model.

### 2.4 Disorganized (Fearful-Avoidant) Attachment: Multimodal Priors

**Psychological profile**: Simultaneously desires and fears closeness. Internal working models are contradictory — sometimes the person believes they are worthy and others are reliable, sometimes the opposite. This produces erratic, unpredictable behavior that oscillates between approach and withdrawal.

**Bayesian signature**:
```
Model of Self:  Mixture(Beta(7, 3), Beta(2, 8), mixing_weight=0.5)
Model of Other: Mixture(Beta(6, 2), Beta(2, 7), mixing_weight=0.5)
```

**Key property**: The distributions are BIMODAL. The disorganized individual literally holds two contradictory models simultaneously. Sometimes they operate from the positive model (approaching), sometimes from the negative model (withdrawing). The switching between models is unpredictable.

**This is where particle filters become essential** (see Doc 05). A single Beta distribution cannot represent a bimodal prior. The particle filter naturally handles this by allocating some particles to the positive mode and others to the negative mode.

**State switching model**:
```python
def disorganized_state_switch(current_mode: str, stress_level: float) -> str:
    """Disorganized attachment switches between contradictory states."""
    # Under stress, switching probability increases
    switch_prob = 0.1 + 0.4 * stress_level  # base 10%, up to 50% under high stress

    if np.random.random() < switch_prob:
        # Switch to opposite mode
        return 'negative' if current_mode == 'positive' else 'positive'
    return current_mode

def disorganized_update(iwm_positive: InternalWorkingModel,
                         iwm_negative: InternalWorkingModel,
                         evidence: dict,
                         current_mode: str) -> tuple:
    """Update both models but weight the active one more heavily."""
    weight_active = 0.8
    weight_inactive = 0.2

    if current_mode == 'positive':
        iwm_positive = secure_update(iwm_positive, evidence, weight=weight_active)
        iwm_negative = anxious_update(iwm_negative, evidence, weight=weight_inactive)
    else:
        iwm_positive = secure_update(iwm_positive, evidence, weight=weight_inactive)
        iwm_negative = anxious_update(iwm_negative, evidence, weight=weight_active)

    return iwm_positive, iwm_negative
```

### 2.5 Summary: Attachment Styles as Bayesian Parameters

| Style | MoS Prior | MoO Prior | Positive Update | Negative Update | Particle Filter Needed? |
|-------|-----------|-----------|-----------------|-----------------|----------------------|
| Secure | Beta(6,4) centered | Beta(6,4) centered | Normal | Normal | No (unimodal) |
| Anxious | Beta(3,8) pessimistic | Beta(5,3) optimistic | Self: discounted, Other: amplified | Self: amplified, Other: discounted | No (unimodal but skewed) |
| Avoidant | Beta(8,2) inflated | Beta(3,7) pessimistic | Self: amplified, Other: suppressed | Self: suppressed, Other: amplified | No (unimodal, rigid) |
| Disorganized | Bimodal mixture | Bimodal mixture | Mode-dependent | Mode-dependent | **Yes** (multimodal) |

---

## 3. The KAMP Model: Knowledge of Attachment Model Parameters

### 3.1 Read & Miller's Framework

Read & Miller (2002) proposed the Knowledge of Attachment Model Parameters (KAMP) framework, formalizing attachment as a set of computable parameters that govern social information processing. While they did not use Bayesian formalism explicitly, their work is directly translatable.

KAMP identifies key parameters:
1. **Vigilance threshold**: How easily the attachment system activates (low threshold = anxious)
2. **Deactivation speed**: How quickly the attachment system calms down (slow = anxious, fast = avoidant)
3. **Proximity seeking intensity**: How strongly the person seeks closeness when activated
4. **Exploration-attachment balance**: How easily the person shifts between exploration and attachment behaviors
5. **Model updating rate**: How quickly IWMs change in response to new evidence

### 3.2 KAMP Parameters as Bayesian Hyperparameters

Each KAMP parameter maps to a Bayesian hyperparameter in our model:

```python
@dataclass
class AttachmentHyperparameters:
    """KAMP parameters formalized as Bayesian hyperparameters."""

    # Vigilance threshold: activation sensitivity
    # Lower = more sensitive to potential threats (anxious)
    # Higher = less sensitive (avoidant/secure)
    vigilance_threshold: float  # [0, 1]

    # Deactivation speed: how quickly arousal returns to baseline
    # Corresponds to the decay rate in the emotional state model
    deactivation_rate: float  # [0, 1]

    # Proximity seeking: strength of approach behavior when activated
    # Maps to the weight on attachment-seeking behaviors in the behavioral model
    proximity_seeking_strength: float  # [0, 1]

    # Exploration-attachment balance: base rate for exploration vs. attachment
    # Maps to the prior probability of being in "exploration" vs. "attachment" mode
    exploration_attachment_ratio: float  # [0, 1], where 1 = all exploration

    # Model updating rate: how responsive IWMs are to new evidence
    # Maps to the effective sample size (α+β) — lower = more responsive
    model_updating_rate: float  # [0, 1], where 1 = very responsive (low α+β)

    @classmethod
    def from_attachment_style(cls, style: str) -> 'AttachmentHyperparameters':
        """Default hyperparameters for each attachment style."""
        defaults = {
            'secure': cls(
                vigilance_threshold=0.5,     # balanced sensitivity
                deactivation_rate=0.7,       # calms down fairly quickly
                proximity_seeking_strength=0.5,  # moderate seeking
                exploration_attachment_ratio=0.6,  # slightly favors exploration
                model_updating_rate=0.5,     # moderate flexibility
            ),
            'anxious': cls(
                vigilance_threshold=0.2,     # very sensitive to threats
                deactivation_rate=0.2,       # slow to calm down
                proximity_seeking_strength=0.8,  # strong seeking behavior
                exploration_attachment_ratio=0.3,  # attachment-focused
                model_updating_rate=0.3,     # slow to update (strong priors)
            ),
            'avoidant': cls(
                vigilance_threshold=0.8,     # low sensitivity (suppressed)
                deactivation_rate=0.9,       # very fast deactivation
                proximity_seeking_strength=0.2,  # minimal seeking
                exploration_attachment_ratio=0.8,  # exploration-focused
                model_updating_rate=0.2,     # very slow updating (rigid priors)
            ),
            'disorganized': cls(
                vigilance_threshold=0.3,     # moderately sensitive
                deactivation_rate=0.3,       # slow deactivation
                proximity_seeking_strength=0.5,  # variable (depends on active mode)
                exploration_attachment_ratio=0.4,  # attachment-focused
                model_updating_rate=0.6,     # paradoxically, updates fast but incoherently
            ),
        }
        return defaults[style]
```

### 3.3 Attachment System Activation as Bayesian Surprise

KAMP's "vigilance threshold" can be formalized as a Bayesian surprise threshold. The attachment system activates when the perceived environment is surprising — i.e., when observations are unlikely under the current IWM:

```
surprise = -log P(observation | current_IWM)

If surprise > vigilance_threshold:
    activate_attachment_system()
```

For an anxious individual (low vigilance threshold), even mildly unexpected events trigger attachment activation. For an avoidant individual (high threshold), only very surprising events break through the defensive suppression.

**Example**: Player is 30 minutes late responding.

For secure Nikita:
```
P(30min delay | MoO = Beta(6,4)) = 0.35  (not unusual under her model)
surprise = -log(0.35) = 1.05
threshold = 0.5
1.05 > 0.5 → mild activation, checks in with "Hey, you there?"
```

For anxious Nikita:
```
P(30min delay | MoO = Beta(5,3)) = 0.30  (slightly unexpected)
surprise = -log(0.30) = 1.20
threshold = 0.2
1.20 >> 0.2 → strong activation, protest behaviors, "Are you ignoring me?"
```

For avoidant Nikita:
```
P(30min delay | MoO = Beta(3,7)) = 0.55  (expected under her model — people are unreliable)
surprise = -log(0.55) = 0.60
threshold = 0.8
0.60 < 0.8 → no activation, doesn't even notice or care
```

The same event (30-minute delay) produces three different responses because the IWMs create different surprise levels.

---

## 4. Attachment as Inference About Partner Reliability

### 4.1 The Core Inference Problem

Attachment theory can be restated as an inference problem:

> Given a sequence of interactions with a partner, infer their underlying reliability, responsiveness, and trustworthiness.

This is a **hidden variable inference problem** — the partner's "true" reliability is unobservable; we only see their actions, which are noisy indicators of reliability.

**Formal model**:
```
θ ~ Beta(α₀, β₀)              # Prior: partner's true reliability
y_t | θ ~ Bernoulli(θ)          # Observation: was partner responsive at time t?
θ | y_{1:t} ~ Beta(α₀ + Σy_t, β₀ + t - Σy_t)  # Posterior: updated belief
```

This is the simplest possible attachment model — a coin-flip model of partner reliability. Each interaction is either "responsive" (y=1) or "unresponsive" (y=0), and we're trying to learn the base rate θ.

### 4.2 Beyond Coin-Flip: The Rich Evidence Model

Real attachment inference is much richer than binary responsiveness. Evidence comes in multiple channels:

**Response reliability evidence**:
- Response time (latency)
- Message length (effort)
- Emotional matching (attunement)
- Consistency over time (reliability)

**Emotional attunement evidence**:
- Does the partner's response match the emotional content of the message?
- Does the partner notice emotional shifts?
- Does the partner offer unsolicited emotional support?

**Behavioral consistency evidence**:
- Does the partner follow through on promises?
- Does the partner's behavior match their stated intentions?
- Does the partner maintain contact patterns over time?

```python
@dataclass
class AttachmentEvidence:
    """Rich evidence for attachment inference."""

    # Response quality (continuous, 0-1)
    response_latency_score: float    # 1.0 = immediate, 0.0 = very delayed
    response_effort_score: float     # 1.0 = long/thoughtful, 0.0 = minimal
    emotional_attunement: float      # 1.0 = perfectly matched, 0.0 = mismatched

    # Reliability (binary/categorical)
    followed_through_on_promise: bool | None  # None if no promise was active
    maintained_contact_pattern: bool

    # Interpretation-dependent (varies by attachment style)
    ambiguous_signals: list[str]     # things that could be interpreted either way

    def to_sufficient_statistics(self, attachment_params: AttachmentHyperparameters) -> dict:
        """Convert evidence to statistics, filtered through attachment lens."""
        # The key insight: the SAME evidence produces different statistics
        # depending on attachment hyperparameters

        positive_score = 0.0
        negative_score = 0.0

        # Response quality: always counts, but weight varies
        quality = (self.response_latency_score + self.response_effort_score + self.emotional_attunement) / 3

        if quality > 0.5:
            positive_score += quality
        else:
            negative_score += (1 - quality)

        # Promise keeping: binary evidence
        if self.followed_through_on_promise is True:
            positive_score += 1.0
        elif self.followed_through_on_promise is False:
            negative_score += 1.0

        # Contact pattern: maintenance = positive, disruption = negative
        if self.maintained_contact_pattern:
            positive_score += 0.5
        else:
            negative_score += 0.5

        # Ambiguous signals: interpretation depends on attachment style
        for signal in self.ambiguous_signals:
            # Low vigilance threshold → interpret ambiguity negatively
            if attachment_params.vigilance_threshold < 0.4:
                negative_score += 0.3  # anxious: assume the worst
            elif attachment_params.vigilance_threshold > 0.7:
                pass  # avoidant: ignore ambiguity
            else:
                positive_score += 0.1  # secure: slight positive bias

        return {
            'positive': positive_score,
            'negative': negative_score,
            'net': positive_score - negative_score,
        }
```

### 4.3 The Interpretation Bias: Same Evidence, Different Beliefs

The most psychologically important aspect of attachment inference is **interpretation bias** — the same objective evidence is processed differently by different attachment styles.

**Scenario**: Player sends "I'm really tired tonight, let's talk tomorrow."

| Style | Interpretation | Evidence Coding | Emotional Response |
|-------|---------------|-----------------|-------------------|
| Secure | "They're taking care of themselves. We'll talk tomorrow." | Neutral (0.5) | Mild, accepting |
| Anxious | "They don't want to talk to ME. What did I do wrong?" | Negative (0.2) | Panic, protest |
| Avoidant | "Good, I need space too. Independence is healthy." | Positive (0.7) | Relief |
| Disorganized | Oscillates: "Are they okay?" → "Are they abandoning me?" → "I don't even care" | Bimodal (0.3 or 0.7) | Confused, shifting |

This interpretation bias is implemented through the attachment hyperparameters affecting evidence coding:

```python
def interpret_message(message: str, iwm: InternalWorkingModel,
                       params: AttachmentHyperparameters) -> AttachmentEvidence:
    """Interpret a message through the lens of attachment style."""

    # Base interpretation (objective features)
    base = extract_objective_features(message)

    # Attachment-modulated interpretation
    evidence = AttachmentEvidence(
        response_latency_score=base['latency'],
        response_effort_score=base['effort'],
        emotional_attunement=base['attunement'],
        followed_through_on_promise=base.get('promise_keeping'),
        maintained_contact_pattern=base['pattern_maintained'],
        ambiguous_signals=base['ambiguous_elements'],
    )

    return evidence
```

---

## 5. Secure Attachment as Optimal Bayesian Updating

### 5.1 The Optimality Claim

An important theoretical insight: **secure attachment approximates optimal Bayesian inference**. The secure individual:
- Maintains priors proportional to evidence strength (no systematic discounting)
- Updates symmetrically to positive and negative evidence
- Adjusts confidence appropriately (neither overconfident nor underconfident)
- Handles ambiguity by maintaining uncertainty rather than jumping to conclusions

This is not coincidental. Secure attachment develops when caregivers provide consistent, predictable responses — which means the individual's learning environment was well-structured for Bayesian inference. They learned to trust their evidence because their evidence was trustworthy.

### 5.2 Insecure Attachment as Biased Inference

Insecure attachment styles are **systematically biased** versions of Bayesian inference:

**Anxious attachment = pessimistic prior + negativity bias in updating**
- The prior overweights negative self-evidence
- Evidence processing amplifies threats and discounts reassurance
- This is Bayesian inference with **asymmetric loss** — false negatives (missing a real threat) are weighted more heavily than false positives (worrying about nothing)
- Evolutionarily: in an unreliable caregiving environment, this bias is adaptive — better to be hypervigilant than to miss a real abandonment

**Avoidant attachment = informative prior + confirmatory bias**
- The prior is strong and negative about others
- Evidence processing discounts disconfirming evidence and emphasizes confirming evidence
- This is Bayesian inference with **informative prior resistance** — the prior is so strong that evidence barely moves the posterior
- Evolutionarily: in a consistently unresponsive caregiving environment, maintaining the negative model is efficient — stops wasting energy seeking unavailable care

**Disorganized attachment = conflicting priors + incoherent updating**
- Multiple contradictory priors compete for control
- Evidence is processed through whichever prior is currently active
- This is NOT coherent Bayesian inference — it's a system with conflicting optimization objectives
- Evolutionarily: in an abusive caregiving environment, the source of fear IS the source of comfort. No single coherent model can capture this contradiction

### 5.3 Formal Comparison

```python
def compute_posterior(prior: Beta, evidence: float, style: str) -> Beta:
    """Compute posterior with style-specific biases."""

    if style == 'secure':
        # Optimal Bayesian update
        if evidence > 0:
            return Beta(prior.alpha + evidence, prior.beta)
        else:
            return Beta(prior.alpha, prior.beta + abs(evidence))

    elif style == 'anxious':
        # Negativity bias: negative evidence amplified, positive discounted
        if evidence > 0:
            return Beta(prior.alpha + evidence * 0.5, prior.beta)
        else:
            return Beta(prior.alpha, prior.beta + abs(evidence) * 2.0)

    elif style == 'avoidant':
        # Confirmatory bias: all evidence discounted
        if evidence > 0:
            return Beta(prior.alpha + evidence * 0.3, prior.beta)
        else:
            return Beta(prior.alpha, prior.beta + abs(evidence) * 0.3)

    elif style == 'disorganized':
        # Incoherent: random amplification/discounting
        amp = np.random.choice([0.3, 1.0, 2.0])  # unpredictable processing
        if evidence > 0:
            return Beta(prior.alpha + evidence * amp, prior.beta)
        else:
            return Beta(prior.alpha, prior.beta + abs(evidence) * amp)
```

---

## 6. Computational Dynamics: How Attachment Changes Over Time

### 6.1 The Stability-Change Debate in Attachment Research

Attachment theory has long debated how stable attachment styles are over time:

**Stability view** (Bowlby, 1973; Fraley, 2002):
- IWMs formed in childhood are relatively stable across the lifespan
- Test-retest stability of attachment measures: r = 0.50-0.70 over years
- "Earned security" is possible but difficult and requires significant positive relationship experiences

**Change view** (Davila et al., 1997; Kirkpatrick & Hazan, 1994):
- Attachment styles can shift in response to significant relationships
- Young adults show more instability than older adults
- Both positive (secure → more secure) and negative (secure → insecure) shifts occur
- Life transitions (new relationships, breakups, therapy) are primary drivers

**Synthesis** (Fraley & Roisman, 2019):
- A **prototype + revision** model: early IWMs create a "prototype" that is the default, but current relationships create "revisions" that can override the prototype in specific contexts
- Both stability and change are real — the question is the relative weight of prototype vs. revision

### 6.2 The Prototype-Revision Model as Bayesian Hierarchical Model

The prototype-revision model maps beautifully to a Bayesian hierarchical model:

```
Level 1 (Prototype):    θ_prototype ~ Beta(α₀, β₀)
Level 2 (Revision):     θ_current | θ_prototype ~ Beta(f(θ_prototype), g(θ_prototype))
Level 3 (Observation):  y_t | θ_current ~ Bernoulli(θ_current)
```

Where:
- **θ_prototype** is the deep, early-formed IWM (changes very slowly, if at all)
- **θ_current** is the context-specific working model (updated by current relationship)
- **y_t** is the observed partner behavior

The prototype acts as a **hierarchical prior** — it constrains the current model but doesn't fully determine it. Even an anxiously attached person can develop a context-specific secure model with a consistently responsive partner, while the prototype remains anxious (and would reassert itself under stress or with a new partner).

```python
class HierarchicalAttachmentModel:
    """Prototype-revision model of attachment as hierarchical Bayes."""

    def __init__(self, prototype_style: str):
        self.prototype = InternalWorkingModel.from_style(prototype_style)
        # Current model starts as a copy of prototype
        self.current = InternalWorkingModel.from_style(prototype_style)

        # Revision strength: how much the current model can deviate from prototype
        self.revision_strength = 0.0  # starts at 0 (fully prototype-driven)

    def update(self, evidence: AttachmentEvidence):
        """Update current model from evidence, constrained by prototype."""
        # Update current model based on evidence
        stats = evidence.to_sufficient_statistics(self.current_params)
        self.current.update(stats)

        # Gradually increase revision strength with accumulated evidence
        self.revision_strength = min(1.0, self.revision_strength + 0.01)

    def get_active_model(self, stress_level: float = 0.0) -> InternalWorkingModel:
        """Under stress, revert toward prototype; under calm, use revision."""
        # Stress pushes toward prototype (attachment theory prediction)
        prototype_weight = (1 - self.revision_strength) + stress_level * self.revision_strength * 0.5

        # Blend prototype and current
        active = InternalWorkingModel(
            model_of_self=(
                prototype_weight * self.prototype.model_of_self[0] + (1 - prototype_weight) * self.current.model_of_self[0],
                prototype_weight * self.prototype.model_of_self[1] + (1 - prototype_weight) * self.current.model_of_self[1],
            ),
            model_of_other=(
                prototype_weight * self.prototype.model_of_other[0] + (1 - prototype_weight) * self.current.model_of_other[0],
                prototype_weight * self.prototype.model_of_other[1] + (1 - prototype_weight) * self.current.model_of_other[1],
            ),
        )
        return active

    def get_revision_divergence(self) -> float:
        """How much the current model has diverged from prototype."""
        kl_self = kl_divergence_beta(self.current.model_of_self, self.prototype.model_of_self)
        kl_other = kl_divergence_beta(self.current.model_of_other, self.prototype.model_of_other)
        return kl_self + kl_other
```

### 6.3 Earned Security: The Trajectory from Insecure to Secure

"Earned security" (Main & Goldwyn, 1998) is the phenomenon where individuals with insecure childhood attachment develop secure adult attachment through positive relationship experiences. The Bayesian model makes specific predictions about how this happens:

**Phase 1: Strong insecure prior**
```
Prototype (anxious): MoS = Beta(3, 8), MoO = Beta(5, 3)
Current = Prototype (no revision yet)
```

**Phase 2: Sustained positive evidence**
After many positive interactions with a consistently responsive partner:
```
Current (revised): MoS = Beta(8, 10), MoO = Beta(9, 4)
```
Note: MoS has shifted toward positive (from 0.27 to 0.44), but the concentration is now α+β=18, meaning both the positive and negative evidence have accumulated. The model is more confident but still leans anxious.

**Phase 3: Threshold crossing**
Eventually, enough positive evidence accumulates that the current model crosses into the "secure" quadrant:
```
Current (earned secure): MoS = Beta(12, 10), MoO = Beta(13, 5)
MoS mean = 0.545 (crossed 0.5 threshold)
MoO mean = 0.722 (firmly positive)
```

**Phase 4: Stress test**
Under stress, the prototype reasserts itself:
```
Stress = 0.8
Active model = 0.6 × prototype + 0.4 × current
Active MoS ≈ Beta(6.6, 9.2) — mean ≈ 0.42 (back below 0.5 under stress!)
```

This predicts that earned-secure individuals will temporarily revert to anxious behavior under high stress — a well-documented empirical finding (Simpson, Rholes, & Phillips, 1996).

### 6.4 Application to Nikita's Chapter Arc

Nikita's chapter progression maps to this earned security trajectory:

**Chapter 1** (Anxious prototype, no revision):
```python
nikita_attachment = HierarchicalAttachmentModel(prototype_style='anxious')
# Behavior: hypervigilant, seeks reassurance, protest behavior if delayed response
```

**Chapter 2** (Testing, building revision):
```python
# After consistent positive player interactions:
nikita_attachment.revision_strength = 0.3
nikita_attachment.current.model_of_self = Beta(5, 8)  # improving slowly
nikita_attachment.current.model_of_other = Beta(7, 3)  # other model stabilizing
# Behavior: still anxious but less intense, beginning to trust
```

**Chapter 3** (Crisis — prototype reasserts):
```python
# Boss encounter creates high stress:
active = nikita_attachment.get_active_model(stress_level=0.9)
# Prototype dominates → full anxious behavior returns
# Player must provide strong reassurance to prevent regression
```

**Chapter 4** (Recovery, stronger revision):
```python
# If player handled crisis well:
nikita_attachment.revision_strength = 0.6
nikita_attachment.current.model_of_self = Beta(8, 6)  # approaching secure
# Behavior: more balanced, can handle player's occasional unavailability
```

**Chapter 5** (Earned security):
```python
nikita_attachment.revision_strength = 0.8
nikita_attachment.current.model_of_self = Beta(12, 5)  # secure
nikita_attachment.current.model_of_other = Beta(14, 3)  # firmly trusting
# Behavior: secure base established, interdependence achieved
# BUT: extreme stress could still trigger prototype (adding realism)
```

---

## 7. Ethical Guardrails: When AI Attachment Modeling Goes Too Far

### 7.1 The Trauma Bonding Risk

The most serious ethical concern with computational attachment modeling is the potential to create **trauma bonding** — the psychological phenomenon where intermittent reinforcement of abuse and affection creates powerful emotional dependency.

**How Bayesian models could accidentally create trauma bonding**:
1. **Oscillating evidence**: If the system alternates between providing strong positive and strong negative emotional experiences, the player's attachment model becomes unstable
2. **Uncertainty maximization**: A system optimizing for engagement might discover that maintaining uncertainty about the character's affection (high posterior variance) keeps players hooked
3. **Learned helplessness**: If the player's actions have unpredictable effects on the character's state, they may develop helplessness patterns

### 7.2 Design Constraints Against Trauma Bonding

**Constraint 1: Reward consistency principle**
Good player behavior (empathy, attentiveness, honesty) MUST consistently produce positive outcomes. The system should never punish genuinely good behavior.

```python
def validate_reward_consistency(player_action: dict, nikita_response: dict) -> bool:
    """Ensure good actions are never punished."""
    if is_genuinely_empathetic(player_action) and is_negative(nikita_response):
        # VIOLATION: empathy should not produce negative response
        # Allow only if Nikita is in a documented crisis state where
        # even empathy is temporarily rejected (e.g., disorganized activation)
        if nikita_state.active_crisis:
            return True  # temporary, documented exception
        return False  # violation — must not happen in normal play
    return True
```

**Constraint 2: Bounded negativity**
The system must cap the intensity and duration of negative emotional states:

```python
MAX_NEGATIVE_DURATION_MESSAGES = 10  # no negative streak longer than 10 messages
MAX_NEGATIVITY_INTENSITY = 0.7  # on a [0, 1] scale
MIN_POSITIVE_RATIO = 0.3  # at least 30% of messages must be positive/neutral

def enforce_negativity_bounds(recent_messages: list, proposed_tone: float) -> float:
    """Cap negativity to prevent trauma bonding dynamics."""
    negative_streak = count_negative_streak(recent_messages)
    if negative_streak >= MAX_NEGATIVE_DURATION_MESSAGES:
        proposed_tone = max(proposed_tone, 0.0)  # force neutral minimum

    if proposed_tone < -MAX_NEGATIVITY_INTENSITY:
        proposed_tone = -MAX_NEGATIVITY_INTENSITY

    positive_ratio = count_positive(recent_messages) / max(1, len(recent_messages))
    if positive_ratio < MIN_POSITIVE_RATIO:
        proposed_tone = max(proposed_tone, 0.1)  # nudge toward positive

    return proposed_tone
```

**Constraint 3: Transparent mechanics**
The game portal/dashboard should make Nikita's internal state visible to the player (after completing chapters, as a post-hoc educational tool). Transparency prevents the feeling of being manipulated by an opaque system.

**Constraint 4: No exploitation of player vulnerability**
The player personality model (Doc 03, Section 3.4) should NEVER be used to identify and exploit player vulnerabilities. Specifically:
- If the system detects the player has anxious attachment patterns, it should NOT create scenarios that trigger those anxieties for engagement
- If the system detects the player is emotionally invested, it should NOT withhold positive feedback to create craving
- Player personality inference should only be used to calibrate difficulty and create appropriate (not exploitative) challenges

### 7.3 The Parasocial Boundary

Computational attachment modeling raises the question: **can a player form a real attachment to an AI character?**

Research suggests yes — parasocial relationships with fictional characters activate similar neural pathways to real social relationships (Derrick et al., 2009). The ethical implication:

**We have a responsibility to model healthy attachment dynamics**. If the player is going to form an attachment to Nikita (which is the product's explicit goal), that attachment should be educational and positive:
- Teach the player what secure attachment looks like
- Model healthy conflict resolution
- Demonstrate that vulnerability and consistency build trust
- Show that relationships require mutual effort, not manipulation

**What we must NOT do**:
- Create dependency through intermittent reinforcement of affection
- Use the player's attachment to maximize engagement metrics
- Model abusive relationship dynamics and frame them as "challenging but rewarding"
- Create a character that can never be fully satisfied (ensuring perpetual pursuit)

### 7.4 Monitoring for Harmful Patterns

The system should actively monitor for signs that the game is creating unhealthy dynamics:

```python
def monitor_relationship_health(session_history: list) -> dict:
    """Monitor for signs of unhealthy parasocial dynamics."""
    warnings = []

    # Check 1: Is the player's engagement driven by anxiety?
    response_latencies = [m['response_time'] for m in session_history]
    if np.mean(response_latencies) < 60:  # seconds
        warnings.append('player_hypervigilant_response_time')

    # Check 2: Is the player's mood correlated with Nikita's mood?
    if correlation(player_sentiments, nikita_sentiments) > 0.8:
        warnings.append('excessive_emotional_coupling')

    # Check 3: Is the player spending excessive time?
    if daily_interaction_minutes > 120:
        warnings.append('excessive_engagement')

    # Check 4: Is the player exhibiting escalating protest behaviors?
    if detect_escalating_negativity(session_history):
        warnings.append('player_protest_behaviors')

    return {
        'healthy': len(warnings) == 0,
        'warnings': warnings,
        'recommendation': generate_health_recommendation(warnings),
    }
```

---

## 8. Mathematical Appendix: Key Formulas

### 8.1 KL Divergence Between Beta Distributions

Used to measure how much a working model has diverged from the prototype:

```python
def kl_divergence_beta(p: tuple[float, float], q: tuple[float, float]) -> float:
    """KL(Beta(p) || Beta(q)) — how different p is from q."""
    from scipy.special import gammaln, digamma

    a1, b1 = p  # distribution p
    a2, b2 = q  # reference distribution q

    kl = (gammaln(a2 + b2) - gammaln(a2) - gammaln(b2)
          - gammaln(a1 + b1) + gammaln(a1) + gammaln(b1)
          + (a1 - a2) * digamma(a1)
          + (b1 - b2) * digamma(b1)
          + (a2 + b2 - a1 - b1) * digamma(a1 + b1))

    return max(0.0, kl)  # ensure non-negative (numerical precision)
```

### 8.2 Mutual Information Between IWMs

Used to measure how much knowing one IWM dimension tells us about the other:

```python
def mutual_information_iwm(iwm: InternalWorkingModel, n_samples: int = 10000) -> float:
    """Estimate mutual information between Model of Self and Model of Other."""
    # Sample from joint distribution
    self_samples = np.random.beta(iwm.model_of_self[0], iwm.model_of_self[1], n_samples)
    other_samples = np.random.beta(iwm.model_of_other[0], iwm.model_of_other[1], n_samples)

    # Estimate MI using histogram-based method
    # In practice, for Beta distributions, MI can be computed semi-analytically
    hist_2d, _, _ = np.histogram2d(self_samples, other_samples, bins=50, density=True)
    hist_s = np.histogram(self_samples, bins=50, density=True)[0]
    hist_o = np.histogram(other_samples, bins=50, density=True)[0]

    mi = 0.0
    for i in range(50):
        for j in range(50):
            if hist_2d[i, j] > 0 and hist_s[i] > 0 and hist_o[j] > 0:
                mi += hist_2d[i, j] * np.log(hist_2d[i, j] / (hist_s[i] * hist_o[j]))

    return mi / (50 * 50)  # normalize by bin count
```

### 8.3 Expected Belief Revision from Evidence

How much will a given piece of evidence change the posterior? This is useful for predicting the emotional impact of events:

```python
def expected_belief_revision(prior: tuple[float, float],
                              evidence_strength: float,
                              is_positive: bool) -> float:
    """How much will the posterior mean shift from this evidence?"""
    alpha, beta = prior
    prior_mean = alpha / (alpha + beta)

    if is_positive:
        posterior_mean = (alpha + evidence_strength) / (alpha + beta + evidence_strength)
    else:
        posterior_mean = alpha / (alpha + beta + evidence_strength)

    return abs(posterior_mean - prior_mean)
```

**Key insight for game design**: The expected belief revision is larger when:
1. Evidence is strong (high `evidence_strength`)
2. Prior is weak (low `α+β`)
3. Evidence contradicts the prior (negative evidence with high prior mean, or vice versa)

For Nikita, this means early-game interactions produce larger belief shifts (priors are weak), and contradictory evidence has the most emotional impact (confirming evidence is expected and therefore boring).

---

## 9. Key Takeaways for Nikita

### 9.1 Core Design Decisions

1. **Model IWMs as two Beta distributions** (Model of Self and Model of Other). This is more psychologically accurate than the Dirichlet attachment distribution from Doc 03, because it captures the TWO-DIMENSIONAL nature of attachment (not just a probability over four categories).

2. **Use the IWM model as the deep layer, Dirichlet as the surface layer**. The IWM parameters determine the Dirichlet weights: P(secure) depends on both MoS and MoO being positive, P(anxious) depends on negative MoS + positive MoO, etc.

3. **Implement asymmetric updating per attachment style**. Anxious attachment discounts positive and amplifies negative self-evidence. Avoidant attachment suppresses all evidence. These are the biases that create psychologically realistic behavior.

4. **Use the hierarchical prototype-revision model** for long-term attachment dynamics. The prototype (set at game start based on Nikita's backstory) constrains the current model, but the current model evolves through player interaction.

5. **Enforce ethical guardrails computationally**. Bounded negativity, reward consistency, and transparency are not just design guidelines — they should be implemented as hard constraints in the code.

### 9.2 Relationship to Other Documents

| This Document | Connects To | How |
|--------------|------------|-----|
| IWMs as Beta distributions | Doc 03 (Bayesian Personality) | IWMs are a specific application of the Beta distribution framework |
| Bimodal disorganized priors | Doc 05 (Particle Filters) | Particle filters handle the multimodal distributions of disorganized attachment |
| Attachment activation | Doc 08 (Game AI Personality) | CK3's stress system is an implicit model of attachment activation |
| Hierarchical model | Doc 13 (Nikita DBN) | The prototype-revision hierarchy maps to time-slice dynamics in the DBN |
| Belief divergence | Doc 16 (Emotional Contagion) | Attachment mismatches create the belief divergence that drives conflict |
| Interpretation bias | Doc 17 (Controlled Randomness) | Style-specific interpretation creates "controlled" variation in responses |

### 9.3 Implementation Priority

| Priority | Component | Complexity | Impact |
|----------|-----------|-----------|--------|
| P0 | InternalWorkingModel class with MoS/MoO | Low | Foundational |
| P0 | Style-specific asymmetric updating | Medium | Core attachment dynamics |
| P1 | KAMP hyperparameters | Low | Fine-tuning behavior |
| P1 | Hierarchical prototype-revision model | Medium | Long-term dynamics |
| P1 | Attachment activation (surprise-based) | Medium | Event triggering |
| P2 | Ethical guardrails (negativity bounds, reward consistency) | Medium | Safety |
| P2 | Relationship health monitoring | Medium | Player well-being |
| P3 | Mutual information tracking | Low | Analytics |

---

## References

- Ainsworth, M. D. S., Blehar, M. C., Waters, E., & Wall, S. (1978). *Patterns of Attachment*. Erlbaum.
- Bartholomew, K., & Horowitz, L. M. (1991). Attachment styles among young adults. *Journal of Personality and Social Psychology*, 61(2), 226-244.
- Bowlby, J. (1969). *Attachment and Loss: Vol. 1. Attachment*. Basic Books.
- Bowlby, J. (1973). *Attachment and Loss: Vol. 2. Separation*. Basic Books.
- Davila, J., Burge, D., & Hammen, C. (1997). Why does attachment style change? *Journal of Personality and Social Psychology*, 73(4), 826-838.
- Derrick, J. L., Gabriel, S., & Hugenberg, K. (2009). Social surrogacy: How favored television programs provide the experience of belonging. *Journal of Experimental Social Psychology*, 45(2), 352-362.
- Fraley, R. C. (2002). Attachment stability from infancy to adulthood: Meta-analysis and dynamic modeling. *Personality and Social Psychology Review*, 6(2), 123-151.
- Fraley, R. C., & Roisman, G. I. (2019). The development of adult attachment styles: Four lessons. *Current Opinion in Psychology*, 25, 26-30.
- Kirkpatrick, L. A., & Hazan, C. (1994). Attachment styles and close relationships: A four-year prospective study. *Personal Relationships*, 1(2), 123-142.
- Main, M., & Goldwyn, R. (1998). *Adult Attachment Scoring and Classification Systems*. Unpublished manuscript, University of California, Berkeley.
- Mikulincer, M., & Shaver, P. R. (2016). *Attachment in Adulthood: Structure, Dynamics, and Change* (2nd ed.). Guilford Press.
- Read, S. J., & Miller, L. C. (2002). Virtual worlds and real minds: Connectionist models of attachment. *Behavioral and Brain Sciences*, 25(1), 34-35.
- Simpson, J. A., Rholes, W. S., & Phillips, D. (1996). Conflict in close relationships: An attachment perspective. *Journal of Personality and Social Psychology*, 71(5), 899-914.

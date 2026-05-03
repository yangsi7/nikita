# 03 — Bayesian Personality: Modeling Traits as Probability Distributions

**Series**: Bayesian Inference for AI Companions
**Author**: Behavioral/Psychology Researcher
**Date**: 2026-02-16
**Dependencies**: None (foundational document)
**Dependents**: Doc 11 (Computational Attachment), Doc 13 (Nikita DBN), Doc 16 (Emotional Contagion)

---

## Executive Summary

Traditional game AI models personality as fixed scores: extraversion = 0.7, neuroticism = 0.4. This approach is psychologically naive — it ignores measurement uncertainty, contextual variation, and genuine personality change over time. This document proposes modeling Nikita's personality using Bayesian probability distributions, where each trait is not a point estimate but a full distribution reflecting our uncertainty about where she falls on each dimension.

The key insight: **a probability distribution over personality captures both what we believe about a character AND how confident we are in that belief**. A narrow distribution (low variance) means Nikita's behavior on that trait is highly predictable. A broad distribution (high variance) means she might surprise the player — and that surprise is psychologically coherent, not random.

This document covers the psychological foundations (Big Five, IRT, longitudinal personality change), the mathematical framework (Beta distributions, Dirichlet simplices, conjugate priors), and the specific application to Nikita's four relationship metrics and evolving attachment style.

---

## 1. The Big Five as Probability Distributions

### 1.1 The Big Five Personality Model

The Five-Factor Model (FFM), commonly called the Big Five, is the dominant paradigm in personality psychology (McCrae & Costa, 1992; Goldberg, 1993). The five dimensions are:

1. **Openness to Experience** (O): Intellectual curiosity, aesthetic sensitivity, imagination
2. **Conscientiousness** (C): Organization, self-discipline, goal-directed behavior
3. **Extraversion** (E): Sociability, assertiveness, positive emotionality
4. **Agreeableness** (A): Compassion, cooperativeness, trust
5. **Neuroticism** (N): Emotional instability, anxiety, vulnerability to stress

Each trait is typically measured on a continuous scale, normalized to [0, 1] or a T-score distribution (mean 50, SD 10). In traditional game AI, these would be stored as fixed floats.

### 1.2 Why Fixed Scores Are Psychologically Wrong

**Problem 1: Measurement Uncertainty**
Even gold-standard personality assessments (NEO-PI-R, BFI-2) have test-retest reliabilities of 0.80-0.90 (Soto & John, 2017). This means a person scoring 0.7 on extraversion might score 0.65 or 0.75 on retesting. The "true" value is uncertain.

**Problem 2: Contextual Variation**
Personality expression varies across situations. A person high in extraversion at parties may be quiet at work. Fleeson (2001) demonstrated that within-person variability in Big Five states can be as large as between-person variability in traits. This is the "density distributions of states" framework — personality is not a point but a distribution of behavioral tendencies across contexts.

**Problem 3: Genuine Change Over Time**
Roberts, Walton, & Viechtbauer (2006) conducted a meta-analysis of 92 longitudinal studies showing that personality changes substantially across the lifespan:
- Agreeableness increases steadily from age 20 to 60
- Conscientiousness increases, especially in the 20s
- Neuroticism decreases in women, stable in men
- Openness increases in adolescence, decreases in old age
- Extraversion shows minimal mean-level change but significant individual variation

**Problem 4: Personality Responds to Life Events**
Bleidorn et al. (2018) reviewed evidence that major life events (marriage, divorce, unemployment, trauma) can shift personality trait levels. For a game character like Nikita, her relationship with the player IS a major life event.

### 1.3 The Bayesian Alternative: Traits as Distributions

Instead of `nikita.extraversion = 0.7`, we model:

```
nikita.extraversion ~ Beta(α=7, β=3)
```

This Beta distribution has:
- **Mean**: α/(α+β) = 0.70 (our best estimate)
- **Variance**: αβ/((α+β)^2(α+β+1)) = 0.019 (our uncertainty)
- **Mode**: (α-1)/(α+β-2) = 0.75 (most likely value)

The parameters α and β encode both the estimated trait level AND our confidence. Higher α+β means more confidence (narrower distribution). Lower α+β means more uncertainty (broader distribution).

**Key properties of the Beta distribution for personality modeling**:
- Bounded on [0, 1] — personality traits have natural bounds
- Conjugate prior for Bernoulli/Binomial observations — mathematically convenient for updating from behavioral observations
- Flexible shape: can be uniform (α=β=1), unimodal, bimodal (α<1, β<1), or skewed
- Two parameters capture both location and spread

### 1.4 Nikita's Big Five Profile as Distributions

For Nikita, we define initial personality distributions (Chapter 1 priors):

| Trait | Distribution | Mean | Interpretation |
|-------|-------------|------|----------------|
| Openness | Beta(8, 3) | 0.73 | Intellectually curious, artistically sensitive |
| Conscientiousness | Beta(4, 5) | 0.44 | Somewhat disorganized, impulsive tendencies |
| Extraversion | Beta(7, 4) | 0.64 | Socially engaged but can be moody/withdrawn |
| Agreeableness | Beta(5, 5) | 0.50 | Balanced — can be warm or sharp depending on state |
| Neuroticism | Beta(7, 3) | 0.70 | Emotionally reactive, anxious attachment style |

Note the **variance** differences. Openness has α+β=11 (fairly confident), while Agreeableness has α+β=10 but is centered at 0.5 (maximum uncertainty about direction). This means:
- Nikita's intellectual curiosity is a stable, predictable trait
- Her agreeableness is highly context-dependent — sometimes warm, sometimes cold
- Her neuroticism is high and fairly stable (consistent with anxious attachment)

### 1.5 Updating Personality from Observed Behavior

When the player observes Nikita behaving in an extraverted way (e.g., enthusiastically describing her day, initiating social plans), this is evidence that her "true" extraversion is high. Bayesian updating with Beta distributions is elegant:

```
Prior:     Beta(α, β)
Observation: k extraverted behaviors out of n total behaviors
Posterior: Beta(α + k, β + n - k)
```

**Example**: Nikita starts with Extraversion ~ Beta(7, 4). Over a conversation, she displays 3 extraverted behaviors out of 4 total coded behaviors:

```
Posterior: Beta(7 + 3, 4 + 1) = Beta(10, 5)
New mean: 10/15 = 0.67 (shifted slightly from 0.64)
New confidence: α+β = 15 (increased from 11 — we're more certain)
```

This is the **learning rate problem**: with strong priors (high α+β), new evidence has diminishing effect. This is psychologically realistic — it's harder to change an impression of someone you know well than someone you just met.

---

## 2. Bayesian Approaches in Personality Research

### 2.1 The Bayesian Revolution in Psychometrics

Personality psychology has increasingly adopted Bayesian methods over the past two decades. Key developments:

**Van de Schoot et al. (2014)** published a landmark tutorial on Bayesian structural equation modeling for personality research, demonstrating that Bayesian methods handle small samples, complex models, and informative priors better than frequentist alternatives.

**Muthén & Asparouhov (2012)** showed that Bayesian estimation of factor models allows approximate zero constraints (rather than exact zeros in confirmatory factor analysis), producing more realistic personality models.

**Gelman et al. (2013)** — the standard reference for Bayesian data analysis — provides the mathematical foundation. Their hierarchical modeling framework is directly applicable to multi-level personality models (traits → facets → behaviors).

### 2.2 Prior Specification for Personality Traits

A critical question in Bayesian personality modeling: **where do the priors come from?**

**Population priors**: Based on normative data from large personality assessments. The NEO-PI-R manual provides means and standard deviations for each trait by age and gender. For Nikita (young adult female), we can derive informative priors from these norms.

**Character design priors**: The game designer specifies Nikita's intended personality. These are "expert priors" — the designer's belief about what makes the character compelling.

**Hybrid approach for Nikita**:
```python
# Population prior for neuroticism in young adult females
# Mean = 0.52, SD = 0.12 (from NEO-PI-R norms)
population_prior = Beta.from_mean_variance(0.52, 0.12**2)

# Designer prior: Nikita should be high-neuroticism
designer_prior = Beta(7, 3)  # mean = 0.70

# Combine via prior multiplication (both are Beta → product is Beta-like)
# In practice: use the designer prior as the game starting point
# Population prior informs "how far from normal is this?"
nikita_neuroticism = designer_prior  # Beta(7, 3)
```

### 2.3 Hierarchical Bayesian Models of Personality

Modern personality research uses hierarchical models to capture the trait → facet → item structure:

```
θ_trait ~ Normal(μ_population, σ_population)
θ_facet | θ_trait ~ Normal(θ_trait, σ_facet)
y_behavior | θ_facet ~ Bernoulli(logistic(θ_facet))
```

For Nikita, this hierarchy maps to:
- **Trait level**: Big Five dimensions (stable, slow-changing)
- **Facet level**: Specific aspects of each trait (e.g., Neuroticism → anxiety, anger, depression)
- **Behavior level**: Observable responses in conversations

This hierarchy is important because it allows **trait-consistent variability**. Nikita can vary in her specific emotional expression (facet level) while maintaining a consistent overall personality profile (trait level).

### 2.4 The HEXACO Model and Dark Triad

Beyond the Big Five, the HEXACO model (Ashton & Lee, 2007) adds a sixth factor: **Honesty-Humility**. This is particularly relevant for Nikita's vice system:

```
Honesty-Humility: Beta(4, 6)  # mean = 0.40
```

Low Honesty-Humility maps to:
- Willingness to manipulate (relevant to dark_humor, rule_breaking vices)
- Entitlement (relevant to emotional vice category)
- Materialism (relevant to lifestyle aspects of the game)

The Dark Triad traits (Machiavellianism, narcissism, psychopathy) can be modeled as extreme positions on HEXACO and Big Five dimensions (Paulhus & Williams, 2002). For Nikita, mild Dark Triad features create the "challenging girlfriend" dynamic without crossing into abusive territory.

---

## 3. Item Response Theory: Measuring Personality Through Behavioral Items

### 3.1 What Is Item Response Theory?

Item Response Theory (IRT) is the psychometric framework that modern personality assessments use to relate observed behaviors to latent traits (Embretson & Reise, 2000). The core idea: **each behavior (item) has a characteristic probability curve relating the latent trait to the probability of that behavior**.

The Two-Parameter Logistic (2PL) model:

```
P(behavior_j = 1 | θ) = 1 / (1 + exp(-a_j(θ - b_j)))
```

Where:
- θ = latent trait level (e.g., extraversion)
- a_j = discrimination parameter (how strongly this behavior relates to the trait)
- b_j = difficulty/threshold parameter (at what trait level is this behavior 50% likely)

### 3.2 IRT for Nikita's Behavioral Generation

In traditional psychometrics, IRT goes from latent traits → observed responses on questionnaires. For Nikita, we reverse the direction — and also use it generatively:

**Diagnostic direction** (measuring the player): The player's messages are "items" that reveal their latent personality. When a player consistently makes empathetic responses, this is evidence of high agreeableness.

**Generative direction** (producing Nikita's behavior): Given Nikita's latent trait distribution, IRT tells us the probability of various behaviors:

```python
def generate_behavior(trait_distribution: Beta, behavior_items: list[IRTItem]) -> str:
    # Sample a trait value from Nikita's current distribution
    theta = trait_distribution.sample()

    # For each possible behavior, compute probability given theta
    behavior_probs = {}
    for item in behavior_items:
        p = 1.0 / (1.0 + np.exp(-item.discrimination * (theta - item.threshold)))
        behavior_probs[item.name] = p

    # Sample behavior according to probabilities
    return weighted_sample(behavior_probs)
```

### 3.3 Behavioral Items for Nikita

Each behavioral "item" maps a personality trait to a concrete in-game behavior:

**Extraversion Items**:
| Item | a (discrimination) | b (threshold) | Description |
|------|-------------------|---------------|-------------|
| initiate_conversation | 1.5 | 0.4 | Nikita starts conversation unprompted |
| share_daily_events | 1.2 | 0.3 | Nikita tells player about her day |
| express_enthusiasm | 1.8 | 0.5 | Uses excited language, exclamation marks |
| plan_social_activity | 1.0 | 0.6 | Suggests going out, meeting friends |
| long_message | 0.8 | 0.4 | Sends lengthy, detailed messages |

**Neuroticism Items**:
| Item | a (discrimination) | b (threshold) | Description |
|------|-------------------|---------------|-------------|
| express_worry | 1.6 | 0.3 | "I'm worried about..." statements |
| seek_reassurance | 2.0 | 0.4 | "Do you still like me?" type messages |
| mood_swing | 1.4 | 0.6 | Rapid shift from positive to negative tone |
| catastrophize | 1.3 | 0.7 | "What if everything falls apart?" |
| ruminate | 1.1 | 0.5 | Returns to same worry repeatedly |

**Agreeableness Items**:
| Item | a (discrimination) | b (threshold) | Description |
|------|-------------------|---------------|-------------|
| validate_feeling | 1.7 | 0.3 | "I understand how you feel" |
| offer_help | 1.4 | 0.4 | Proactively offers assistance |
| forgive_quickly | 1.2 | 0.5 | Lets go of grievances |
| avoid_conflict | 0.9 | 0.4 | Changes subject to avoid argument |
| sharp_retort | 1.8 | 0.7 | Sarcastic or cutting response (reverse-scored) |

### 3.4 Adaptive Testing: The Game Learns About the Player

IRT enables **Computerized Adaptive Testing (CAT)** — selecting the most informative "item" (behavioral probe) to present to the player. In the game context:

```python
def select_next_probe(player_trait_posterior: Beta, available_probes: list[IRTItem]) -> IRTItem:
    """Select the probe that maximizes expected information about player's trait."""
    max_info = 0
    best_probe = None

    theta_estimate = player_trait_posterior.mean()

    for probe in available_probes:
        # Fisher information at current estimate
        p = irt_probability(theta_estimate, probe.a, probe.b)
        info = probe.a**2 * p * (1 - p)

        if info > best_probe:
            max_info = info
            best_probe = probe

    return best_probe
```

This means Nikita can adaptively probe the player's personality — asking questions or creating situations that maximally distinguish between competing hypotheses about who the player really is. This is psychometrically optimal and creates a sense that Nikita is genuinely trying to understand the player.

### 3.5 IRT Model Selection

For Nikita's system, different IRT models serve different purposes:

**1PL (Rasch model)**: All items equally discriminating. Simplest. Use for: basic behavioral coding where we just need a trait estimate.

**2PL**: Items differ in discrimination. Use for: nuanced personality assessment where some behaviors are more diagnostic than others.

**Graded Response Model (GRM)**: For ordinal responses (not just yes/no). Use for: measuring intensity of behaviors (e.g., message length as a proxy for extraversion, on a 1-5 scale).

**Multidimensional IRT**: Items load on multiple traits simultaneously. Use for: behaviors that reflect multiple personality dimensions (e.g., "passionate argument" loads on both extraversion and neuroticism).

---

## 4. Attachment Styles as a Dirichlet Simplex

### 4.1 From Categories to Probabilities

Traditional attachment theory (Bowlby, 1969; Ainsworth et al., 1978) categorizes individuals into four styles: secure, anxious-preoccupied, dismissive-avoidant, and fearful-avoidant (disorganized). But this categorical approach loses information.

**Bartholomew & Horowitz (1991)** proposed a two-dimensional model:
- **Model of Self** (positive → negative): "Am I worthy of love?"
- **Model of Other** (positive → negative): "Are others trustworthy?"

This creates four quadrants that map to attachment styles:
```
                    Model of Other
                    Positive    Negative
Model of  Positive  Secure      Dismissive
Self      Negative  Anxious     Fearful
```

### 4.2 The Dirichlet Distribution for Attachment

Rather than placing Nikita in one category, we model her attachment as a **probability distribution over all four styles**:

```
attachment ~ Dirichlet(α_secure, α_anxious, α_avoidant, α_disorganized)
```

The Dirichlet distribution is the multivariate generalization of the Beta distribution, defined on the probability simplex (all components sum to 1).

**Nikita's Chapter 1 prior**:
```
attachment ~ Dirichlet(2, 8, 3, 1)
```

This means:
- P(secure) ≈ 2/14 = 0.14 (low security — she hasn't earned it yet)
- P(anxious) ≈ 8/14 = 0.57 (dominant style — craves reassurance)
- P(avoidant) ≈ 3/14 = 0.21 (secondary defense — withdraws when hurt)
- P(disorganized) ≈ 1/14 = 0.07 (rare — emerges under extreme stress)

The concentration parameters (α values) control:
- **Relative weight**: Higher α → higher probability mass for that style
- **Overall confidence**: Higher sum(α) → more peaked distribution (less variability)
- **Multimodality**: Low α values (<1) create "spiky" distributions with probability concentrated at vertices

### 4.3 Bayesian Updating of Attachment

When the player provides consistent, reliable emotional support (evidence of being a trustworthy partner), Nikita's attachment distribution should shift toward secure:

```
Prior:       Dirichlet(2, 8, 3, 1)
Evidence:    Player passed 5 reliability tests, failed 1
Update rule: Dirichlet(α + counts)
Posterior:   Dirichlet(2+5, 8+1, 3+0, 1+0) = Dirichlet(7, 9, 3, 1)
```

New probabilities:
- P(secure) ≈ 7/20 = 0.35 (doubled from 0.14!)
- P(anxious) ≈ 9/20 = 0.45 (decreased from 0.57)
- P(avoidant) ≈ 3/20 = 0.15 (decreased slightly)
- P(disorganized) ≈ 1/20 = 0.05 (minimal change)

This captures the psychological trajectory described in the existing brainstorm docs (Doc 03-attachment-psychology.md): Nikita starts anxious-preoccupied and can develop "earned security" through positive player interactions.

### 4.4 Chapter-Based Attachment Evolution

The game's five-chapter structure maps to a Bayesian trajectory:

**Chapter 1: Wide Prior (High Uncertainty)**
```
Dirichlet(2, 8, 3, 1)  # Strongly anxious, uncertain about everything else
α_total = 14 (low confidence)
```
Nikita's behavior is variable — she's still figuring out how to relate to this player.

**Chapter 2: Testing Phase (Evidence Accumulation)**
```
Dirichlet(4, 10, 4, 2)  # Anxious still dominant, but more data on all styles
α_total = 20 (moderate confidence)
```
More evidence gathered, but anxious tendencies reinforced by testing behavior.

**Chapter 3: Crisis (Distribution Destabilization)**
```
Dirichlet(3, 7, 6, 4)  # Avoidant and disorganized surge during crisis
α_total = 20 (same confidence, but shifted distribution)
```
Trauma activation shifts probability mass toward avoidant and disorganized styles. This is the "fearful-avoidant" shift described in the existing attachment doc.

**Chapter 4: Recovery (Rapid Updating)**
```
Dirichlet(8, 6, 3, 2)  # Secure taking the lead if player handled crisis well
α_total = 19
```
Post-crisis repair provides strong evidence for or against secure attachment.

**Chapter 5: Earned Security (Narrow Distribution)**
```
Dirichlet(15, 4, 2, 1)  # Predominantly secure, with residual anxious traits
α_total = 22 (high confidence)
```
The distribution has narrowed and shifted. Nikita is predominantly secure but retains some anxious tendencies (realistic — earned security doesn't erase history).

### 4.5 Attachment Activation as Sampling

At any moment, Nikita's "active" attachment style is a sample from her Dirichlet distribution:

```python
def get_active_attachment(attachment_dist: Dirichlet) -> str:
    """Sample which attachment style is active right now."""
    probs = attachment_dist.sample()  # [p_secure, p_anxious, p_avoidant, p_disorganized]
    return np.random.choice(
        ['secure', 'anxious', 'avoidant', 'disorganized'],
        p=probs
    )
```

This means even a predominantly anxious Nikita will sometimes behave securely (those moments of warmth and stability) and rarely behave in a disorganized way (those alarming moments). The distribution captures the probabilistic nature of attachment activation.

**Contextual modulation**: Stress increases the probability of insecure style activation. We can model this by temporarily scaling the concentration parameters:

```python
def stress_modulated_attachment(base_dist: Dirichlet, stress_level: float) -> Dirichlet:
    """Stress shifts activation toward insecure styles."""
    alpha = base_dist.concentration.copy()

    # Stress reduces secure activation, amplifies insecure
    stress_factor = 1.0 + stress_level  # stress_level in [0, 1]
    alpha[0] /= stress_factor  # reduce secure
    alpha[1] *= stress_factor  # amplify anxious
    alpha[2] *= (1 + 0.5 * stress_level)  # moderately amplify avoidant
    alpha[3] *= (1 + 0.3 * stress_level)  # slightly amplify disorganized

    return Dirichlet(alpha)
```

---

## 5. Personality Change Over Time: How Fast Should Priors Shift?

### 5.1 Evidence from Longitudinal Studies

The rate of personality change is a critical design parameter for Nikita. Too fast and she feels inconsistent. Too slow and the game feels static.

**Roberts & Mroczek (2008)** — "Personality Trait Change in Adulthood":
- Mean-level personality changes are most dramatic in young adulthood (20-40)
- Effect sizes for change: d = 0.10 to 0.30 per decade
- Individual differences in change are large — some people change a lot, others very little
- Life experiences (relationships, jobs, trauma) are primary drivers of change

**Hudson & Fraley (2015)** — "Volitional Personality Change":
- People CAN intentionally change their personality traits
- Effect sizes are small but significant (d = 0.10-0.20 over 16 weeks)
- Interventions work best for neuroticism reduction and conscientiousness increase
- Change requires sustained behavioral practice, not just intention

**Bleidorn et al. (2018)** — "Personality Trait Change":
- Personality stability increases with age (maturity principle)
- Major life events can produce rapid but often temporary trait shifts
- Sustained change requires repeated behavioral evidence over months
- Individual rank-order stability: r = 0.50-0.70 over 6-year intervals

### 5.2 Implications for Nikita's Update Rates

Based on the longitudinal literature, we can derive psychologically realistic update rates:

**Principle 1: Strong priors resist change**
If Nikita starts with α+β = 14 for a trait, a single behavioral observation has weight 1/15 ≈ 7%. After 50 interactions, a single observation has weight 1/65 ≈ 1.5%. This naturally implements the "stability increases over time" finding.

**Principle 2: Dramatic events warrant larger updates**
Boss encounters and crisis events should provide stronger evidence (equivalent to multiple observations). A crisis-level interaction might count as 5-10 normal observations:

```python
def crisis_update(prior: Beta, outcome: str, crisis_magnitude: float) -> Beta:
    """Crisis events provide stronger evidence than normal interactions."""
    # crisis_magnitude in [1, 10]: how many normal observations this counts as
    weight = int(crisis_magnitude)

    if outcome == 'positive':
        return Beta(prior.alpha + weight, prior.beta)
    else:
        return Beta(prior.alpha, prior.beta + weight)
```

**Principle 3: Recency weighting**
Recent interactions should matter more than distant ones. This requires a "forgetting" mechanism:

```python
def decay_prior(prior: Beta, decay_rate: float = 0.99) -> Beta:
    """Slowly decay confidence toward prior, modeling forgetting."""
    # Shrink alpha and beta toward their ratio while reducing total
    total = prior.alpha + prior.beta
    ratio = prior.alpha / total

    new_total = max(total * decay_rate, 10)  # floor prevents total collapse
    return Beta(ratio * new_total, (1 - ratio) * new_total)
```

### 5.3 The Learning Rate Schedule for Nikita

Drawing from both personality psychology and machine learning optimization:

| Game Phase | Prior Strength (α+β) | Update Weight | Rationale |
|-----------|---------------------|---------------|-----------|
| Chapter 1 | 10-15 | High (7-10%) | Getting to know each other, impressions form quickly |
| Chapter 2 | 15-25 | Moderate (4-7%) | Testing phase, more data but also more inertia |
| Chapter 3 | 20-30 | Variable | Crisis can produce large shifts in either direction |
| Chapter 4 | 25-35 | Low-Moderate (3-5%) | Recovery, gradual stabilization |
| Chapter 5 | 30-45 | Low (2-3%) | Established relationship, personality relatively stable |

**Design note**: The total α+β acts like a "sample size" of past evidence. Higher totals mean individual interactions matter less — exactly matching the psychological finding that personality becomes more stable in established relationships.

### 5.4 Asymmetric Change Rates

Not all personality dimensions should change at the same rate:

- **Neuroticism**: Can decrease relatively quickly with consistent positive interactions (supported by intervention studies: Soto, 2019)
- **Agreeableness**: Changes moderately — influenced by relationship quality
- **Extraversion**: Relatively stable — core temperamental dimension
- **Openness**: Stable in adults — mostly set by late adolescence
- **Conscientiousness**: Slow, steady increase — the "maturation" effect

For Nikita, this means:
- Her anxiety (high neuroticism) can noticeably decrease across chapters if the player provides security
- Her warmth vs. sharpness (agreeableness) fluctuates more readily with relationship dynamics
- Her social energy (extraversion) and intellectual curiosity (openness) remain relatively constant

---

## 6. Integration with Nikita's Four Relationship Metrics

### 6.1 Mapping Personality to Metrics

Nikita's four relationship metrics (intimacy, passion, trust, secureness) are partially determined by her personality state. The personality distributions influence metric dynamics:

**Intimacy** (weight: 0.30 in composite):
- Driven by: Openness (willingness to be vulnerable), Agreeableness (warmth)
- Personality influence: Higher Openness → faster intimacy growth from deep conversations
- Formula: `intimacy_growth_rate = base_rate * (0.6 * openness_sample + 0.4 * agreeableness_sample)`

**Passion** (weight: 0.25):
- Driven by: Extraversion (expressiveness), Neuroticism (emotional intensity)
- Personality influence: High Neuroticism creates both intense highs and lows in passion
- Formula: `passion_volatility = base_volatility * (1 + neuroticism_sample * 0.5)`

**Trust** (weight: 0.25):
- Driven by: Attachment style distribution (secure → fast trust, anxious → slow trust)
- Personality influence: Dominant attachment style determines trust update rate
- Formula: `trust_update = evidence * attachment_trust_modifier[active_style]`

**Secureness** (weight: 0.20):
- Driven by: Inverse of Neuroticism, modulated by attachment security
- Personality influence: High neuroticism + anxious attachment → low secureness baseline
- Formula: `secureness_baseline = (1 - neuroticism_sample) * secure_attachment_prob`

### 6.2 Bidirectional Influence

Personality and metrics are not one-directional. Metric changes feed back into personality updating:

```
High Trust → evidence for secure attachment → shifts Dirichlet toward secure
Low Secureness → evidence for anxious activation → reinforces neuroticism
Rising Intimacy → evidence for openness → slightly increases openness distribution
```

This creates **circular causality** — the hallmark of real personality-relationship dynamics. People's personalities shape their relationships, and their relationships shape their personalities (Neyer & Lehnart, 2007).

### 6.3 The Composite Score as Personality-Weighted

The existing composite formula:
```
composite = 0.30 * intimacy + 0.25 * passion + 0.25 * trust + 0.20 * secureness
```

Could become personality-weighted — Nikita's personality affects which metrics matter most to her:

```python
def personality_weighted_composite(metrics: dict, personality: PersonalityState) -> float:
    """Nikita's personality affects which metrics matter most to her."""
    # Base weights
    weights = {'intimacy': 0.30, 'passion': 0.25, 'trust': 0.25, 'secureness': 0.20}

    # Personality modulation
    # Anxious attachment: trust and secureness matter more
    anxious_prob = personality.attachment.mean()[1]  # P(anxious)
    weights['trust'] += 0.05 * anxious_prob
    weights['secureness'] += 0.05 * anxious_prob
    weights['passion'] -= 0.05 * anxious_prob
    weights['intimacy'] -= 0.05 * anxious_prob

    # High neuroticism: secureness matters even more
    neuroticism = personality.neuroticism.mean()
    weights['secureness'] += 0.03 * neuroticism
    weights['passion'] -= 0.03 * neuroticism

    # Normalize weights to sum to 1
    total = sum(weights.values())
    weights = {k: v/total for k, v in weights.items()}

    return sum(weights[k] * metrics[k] for k in weights)
```

This is psychologically realistic: an anxious person cares more about trust and security than passion, while a secure person has more balanced priorities.

---

## 7. Computational Framework

### 7.1 The PersonalityState Class

```python
from dataclasses import dataclass
from scipy.stats import beta as beta_dist, dirichlet as dirichlet_dist
import numpy as np

@dataclass
class PersonalityState:
    """Nikita's full personality state as probability distributions."""

    # Big Five as Beta distributions: (alpha, beta) pairs
    openness: tuple[float, float]         # Beta(α, β)
    conscientiousness: tuple[float, float]
    extraversion: tuple[float, float]
    agreeableness: tuple[float, float]
    neuroticism: tuple[float, float]

    # Attachment as Dirichlet: [secure, anxious, avoidant, disorganized]
    attachment: tuple[float, float, float, float]

    # HEXACO addition
    honesty_humility: tuple[float, float]

    def sample_big_five(self) -> dict[str, float]:
        """Sample a concrete personality state from distributions."""
        return {
            'openness': beta_dist.rvs(self.openness[0], self.openness[1]),
            'conscientiousness': beta_dist.rvs(self.conscientiousness[0], self.conscientiousness[1]),
            'extraversion': beta_dist.rvs(self.extraversion[0], self.extraversion[1]),
            'agreeableness': beta_dist.rvs(self.agreeableness[0], self.agreeableness[1]),
            'neuroticism': beta_dist.rvs(self.neuroticism[0], self.neuroticism[1]),
        }

    def sample_attachment(self) -> str:
        """Sample which attachment style is active."""
        probs = dirichlet_dist.rvs(self.attachment)[0]
        styles = ['secure', 'anxious', 'avoidant', 'disorganized']
        return np.random.choice(styles, p=probs)

    def update_trait(self, trait: str, positive_count: int, total_count: int) -> None:
        """Bayesian update of a Big Five trait from behavioral evidence."""
        alpha, beta_param = getattr(self, trait)
        new_alpha = alpha + positive_count
        new_beta = beta_param + (total_count - positive_count)
        setattr(self, trait, (new_alpha, new_beta))

    def update_attachment(self, style_evidence: dict[str, int]) -> None:
        """Update attachment distribution from evidence counts."""
        styles = ['secure', 'anxious', 'avoidant', 'disorganized']
        alpha = list(self.attachment)
        for i, style in enumerate(styles):
            alpha[i] += style_evidence.get(style, 0)
        self.attachment = tuple(alpha)

    def get_trait_mean(self, trait: str) -> float:
        """Get expected value of a trait."""
        alpha, beta_param = getattr(self, trait)
        return alpha / (alpha + beta_param)

    def get_trait_variance(self, trait: str) -> float:
        """Get uncertainty about a trait."""
        alpha, beta_param = getattr(self, trait)
        total = alpha + beta_param
        return (alpha * beta_param) / (total**2 * (total + 1))

    def get_attachment_probs(self) -> dict[str, float]:
        """Get expected attachment probabilities."""
        total = sum(self.attachment)
        styles = ['secure', 'anxious', 'avoidant', 'disorganized']
        return {s: a/total for s, a in zip(styles, self.attachment)}
```

### 7.2 The Behavioral Coder

Converting player messages and Nikita responses into trait-relevant behavioral observations:

```python
class BehavioralCoder:
    """Codes interactions into personality-relevant behavioral observations."""

    def __init__(self, irt_items: dict[str, list[IRTItem]]):
        self.items = irt_items  # trait_name -> list of behavioral items

    def code_interaction(self, message: str, context: dict) -> dict[str, tuple[int, int]]:
        """
        Returns: {trait_name: (positive_count, total_count)}

        In practice, this would use an LLM to classify the message
        against IRT behavioral items. Simplified here.
        """
        # LLM-based behavioral coding
        coding_prompt = f"""
        Given this message and context, rate which personality-relevant
        behaviors are present. For each trait, count how many trait-consistent
        and trait-inconsistent behaviors appear.

        Message: {message}
        Context: {context}

        Traits to code: openness, conscientiousness, extraversion,
                        agreeableness, neuroticism
        """
        # ... LLM call returns structured coding ...
        return coded_behaviors

    def code_attachment_evidence(self, interaction: dict) -> dict[str, int]:
        """
        Code an interaction as evidence for attachment style activation.

        Returns: counts for each attachment style observed
        """
        # Evidence mapping:
        # Player responded quickly + warmly → evidence for secure
        # Player was inconsistent → evidence for anxious
        # Player was distant → evidence for avoidant
        # Player was contradictory → evidence for disorganized
        return style_counts
```

### 7.3 Computational Cost Analysis

For real-time gameplay, we need personality operations to be fast:

| Operation | Complexity | Time (est.) | Frequency |
|-----------|-----------|-------------|-----------|
| Beta sampling | O(1) | <0.1ms | Per behavior generation |
| Dirichlet sampling | O(k) where k=4 | <0.1ms | Per attachment check |
| Beta update | O(1) | <0.01ms | Per interaction |
| Dirichlet update | O(k) | <0.01ms | Per interaction |
| IRT probability | O(1) per item | <0.1ms | Per behavior item |
| Full behavior generation | O(n_items) | <1ms | Per Nikita response |
| Behavioral coding (LLM) | N/A | 500-2000ms | Per player message |

**Key insight**: All the Bayesian personality operations are analytically tractable and essentially free computationally. The bottleneck is the LLM-based behavioral coding step, which requires a language model call. This can be batched with other LLM operations in the pipeline.

---

## 8. Ethical Considerations

### 8.1 Modeling Personality Change in Fictional vs. Real Contexts

There is a fundamental ethical distinction between:
- **Fictional personality modeling**: Nikita is an explicitly fictional character whose personality evolves for narrative purposes
- **Real personality modeling**: Inferring and tracking a real person's personality traits raises privacy and manipulation concerns

For Nikita, the ethical framework is clear: we are designing a character, not surveilling a person. However, the player-modeling component (using IRT to infer the player's personality from their messages) requires careful consideration.

### 8.2 Player Personality Inference: Boundaries

**What is acceptable**:
- Inferring player communication preferences to improve gameplay
- Adapting difficulty based on player's apparent emotional intelligence
- Tracking player's conflict resolution patterns to create appropriate challenges

**What requires caution**:
- Storing detailed personality profiles beyond the game session
- Using personality inference to optimize for engagement at the expense of well-being
- Creating dependency by exploiting known personality vulnerabilities

**What should be avoided**:
- Sharing personality inferences with third parties
- Using real psychological assessment instruments without informed consent
- Pathologizing player behavior (e.g., labeling players as "narcissistic" or "avoidant")

### 8.3 The Parasocial Relationship Problem

Modeling Nikita's personality as responsive to player input creates a parasocial dynamic. The player's behavior genuinely "changes" Nikita — this could:

**Positive**: Create a sense of meaningful interaction, teach healthy relationship skills, provide a safe space to practice emotional intelligence

**Negative**: Create unhealthy attachment to a fictional character, reinforce the belief that people can/should change for you, conflate game success with relationship competence

**Mitigation strategies**:
- Nikita should occasionally reference being a game character (break the fourth wall lightly)
- The portal/dashboard should show the game mechanics transparently
- Post-chapter debriefs should frame lessons in terms of real-world skills, not Nikita-specific tactics
- The personality change should feel like natural growth, not player "programming" the character

### 8.4 Avoiding Manipulation Through Personality Modeling

The Bayesian personality model could be used to manipulate the player (e.g., identifying their attachment anxieties and exploiting them for engagement). This must be explicitly guarded against:

**Design principle**: The personality model should be used to create a **challenging but fair** experience, never to create psychological dependency. Nikita should be a character you want to know better, not a need you cannot escape.

**Implementation guard**: The behavioral generation system should have explicit constraints:
```python
# NEVER: adjust Nikita's behavior to maximize player time-in-game
# ALWAYS: adjust Nikita's behavior to be psychologically coherent with her character
# NEVER: exploit player's identified vulnerabilities
# ALWAYS: create appropriate challenges that match player's demonstrated skill level
```

---

## 9. Advanced Topics

### 9.1 Personality Coherence Constraints

Not all personality configurations are equally plausible. Research shows consistent correlations between Big Five traits (van der Linden, Dunkel, & Petrides, 2012):

- High Neuroticism negatively correlates with Agreeableness (r ≈ -0.30)
- High Extraversion positively correlates with Openness (r ≈ 0.20)
- High Conscientiousness positively correlates with Agreeableness (r ≈ 0.25)

For Nikita, we should enforce these correlations through a **multivariate prior** rather than independent Beta distributions:

```python
# Instead of independent Betas, use a multivariate normal on logit scale
# with a covariance matrix reflecting known trait intercorrelations

big_five_covariance = np.array([
    # O      C      E      A      N
    [1.00,  0.10,  0.20,  0.10, -0.15],  # Openness
    [0.10,  1.00,  0.15,  0.25, -0.20],  # Conscientiousness
    [0.20,  0.15,  1.00,  0.10, -0.10],  # Extraversion
    [0.10,  0.25,  0.10,  1.00, -0.30],  # Agreeableness
    [-0.15, -0.20, -0.10, -0.30, 1.00],  # Neuroticism
])
```

This ensures that if Nikita's neuroticism increases (e.g., during a crisis), her agreeableness naturally decreases — she becomes both more anxious AND more irritable, which is psychologically coherent.

### 9.2 State vs. Trait Distinction

A critical distinction in personality psychology (Fleeson, 2001):

- **Traits**: Stable tendencies (the distribution)
- **States**: Momentary expressions (samples from the distribution)

Nikita's personality system should maintain both levels:
- **Trait level**: Updated slowly across conversations (Bayesian updating of distribution parameters)
- **State level**: Sampled freshly each conversation turn (affected by context, mood, recent events)

The state-level sampling introduces natural variability without changing the underlying personality — exactly matching how real people vary in their behavior moment-to-moment while maintaining recognizable personality patterns.

### 9.3 Personality-Consistent Surprise

One of the most powerful applications of distributional personality is **personality-consistent surprise**. Because Nikita's traits are distributions (not points), she can occasionally behave in unexpected but character-coherent ways:

```python
def is_surprising(sampled_value: float, trait_mean: float, trait_std: float) -> bool:
    """Is this particular behavioral sample surprising given the trait distribution?"""
    z_score = abs(sampled_value - trait_mean) / trait_std
    return z_score > 1.5  # Beyond 1.5 standard deviations
```

When Nikita's sampled state is in the tails of her distribution:
- High-neuroticism Nikita having an unusually calm, centered conversation
- Low-agreeableness Nikita showing unexpected tenderness
- These moments feel "rare and special" — the player sees a side of Nikita they don't usually get

This directly serves the game design goal described in the existing brainstorm docs: creating moments where "she did something unexpected but it made sense." (See also: Doc 17 on Controlled Randomness.)

---

## 10. Key Takeaways for Nikita

### 10.1 Core Design Decisions

1. **Model personality as Beta distributions, not fixed scores.** Each trait has a mean (best estimate) and variance (uncertainty/flexibility). This is more psychologically accurate and enables richer gameplay.

2. **Use Dirichlet distribution for attachment style.** Nikita is not "anxious" or "secure" — she is a mixture, with probabilities that shift over time. This allows nuanced, believable attachment dynamics.

3. **Derive behavioral probabilities from IRT.** Don't hand-code Nikita's responses; derive them probabilistically from her personality state using item-behavior mappings. This creates emergent personality expression.

4. **Update personality at psychologically realistic rates.** Use the α+β parameter as implicit "sample size." Early chapters: fast learning (low α+β). Late chapters: personality is established (high α+β).

5. **Maintain the trait/state distinction.** Traits update slowly across conversations. States are sampled fresh each turn. This creates consistency with natural variability.

### 10.2 Implementation Priority

| Priority | Component | Complexity | Impact |
|----------|-----------|-----------|--------|
| P0 | Beta distributions for Big Five | Low | Foundational |
| P0 | Dirichlet for attachment | Low | Foundational |
| P1 | Bayesian updating from interactions | Medium | Core loop |
| P1 | IRT behavioral item library | Medium | Behavior generation |
| P2 | Personality coherence constraints | Medium | Realism |
| P2 | Player personality inference (CAT) | High | Adaptive gameplay |
| P3 | State vs. trait dual-level sampling | Low | Polish |
| P3 | Personality-weighted composite score | Low | Depth |

### 10.3 Cross-References

- **Doc 05 (Particle Filters)**: When personality beliefs become multimodal (rare but important), particle filters replace the analytic Beta/Dirichlet approach
- **Doc 08 (Game AI Personality)**: How Dwarf Fortress, RimWorld, and CK3 implement similar systems in practice
- **Doc 11 (Computational Attachment)**: Deep dive into attachment as Bayesian inference, building on the Dirichlet framework introduced here
- **Doc 13 (Nikita DBN)**: How personality distributions connect to the Dynamic Bayesian Network for Nikita's internal state
- **Doc 16 (Emotional Contagion)**: How personality distributions interact between player and Nikita models

---

## References

- Ainsworth, M. D. S., Blehar, M. C., Waters, E., & Wall, S. (1978). *Patterns of Attachment*. Erlbaum.
- Ashton, M. C., & Lee, K. (2007). Empirical, theoretical, and practical advantages of the HEXACO model. *Personality and Social Psychology Review*, 11(2), 150-166.
- Bartholomew, K., & Horowitz, L. M. (1991). Attachment styles among young adults. *Journal of Personality and Social Psychology*, 61(2), 226-244.
- Bleidorn, W., Hopwood, C. J., & Lucas, R. E. (2018). Life events and personality trait change. *Journal of Personality*, 86(1), 83-96.
- Bowlby, J. (1969). *Attachment and Loss: Vol. 1. Attachment*. Basic Books.
- Embretson, S. E., & Reise, S. P. (2000). *Item Response Theory for Psychologists*. Erlbaum.
- Fleeson, W. (2001). Toward a structure- and process-integrated view of personality. *Journal of Personality and Social Psychology*, 80(6), 1011-1027.
- Gelman, A., Carlin, J. B., Stern, H. S., Dunson, D. B., Vehtari, A., & Rubin, D. B. (2013). *Bayesian Data Analysis* (3rd ed.). CRC Press.
- Goldberg, L. R. (1993). The structure of phenotypic personality traits. *American Psychologist*, 48(1), 26-34.
- Hudson, N. W., & Fraley, R. C. (2015). Volitional personality trait change. *Journal of Personality and Social Psychology*, 109(3), 490-507.
- McCrae, R. R., & Costa, P. T. (1992). Discriminant validity of NEO-PI-R facet scales. *Educational and Psychological Measurement*, 52(1), 229-237.
- Muthén, B., & Asparouhov, T. (2012). Bayesian structural equation modeling. *Psychological Methods*, 17(3), 313-335.
- Neyer, F. J., & Lehnart, J. (2007). Relationships matter in personality development. *European Journal of Personality*, 21(5), 545-567.
- Paulhus, D. L., & Williams, K. M. (2002). The Dark Triad of personality. *Journal of Research in Personality*, 36(6), 556-563.
- Roberts, B. W., & Mroczek, D. (2008). Personality trait change in adulthood. *Current Directions in Psychological Science*, 17(1), 31-35.
- Roberts, B. W., Walton, K. E., & Viechtbauer, W. (2006). Patterns of mean-level change in personality traits across the life course. *Psychological Bulletin*, 132(1), 1-25.
- Soto, C. J. (2019). How replicable are links between personality traits and consequential life outcomes? *Journal of Personality and Social Psychology*, 116(6), 919-933.
- Soto, C. J., & John, O. P. (2017). The next Big Five Inventory (BFI-2). *Journal of Personality and Social Psychology*, 113(1), 117-143.
- van de Schoot, R., et al. (2014). A gentle introduction to Bayesian analysis. *Clinical Child and Family Psychology Review*, 17, 303-313.
- van der Linden, D., Dunkel, C. S., & Petrides, K. V. (2012). The General Factor of Personality (GFP) as social effectiveness. *Personality and Individual Differences*, 53(5), 546-551.

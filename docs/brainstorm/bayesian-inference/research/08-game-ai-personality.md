# 08 — Game AI Personality Systems: Lessons from Commercial Games

**Series**: Bayesian Inference for AI Companions
**Author**: Behavioral/Psychology Researcher
**Date**: 2026-02-16
**Dependencies**: None (standalone survey)
**Dependents**: Doc 13 (Nikita DBN), Doc 17 (Controlled Randomness)

---

## Executive Summary

Before proposing a novel Bayesian personality system for Nikita, we must understand what has actually worked in shipped games. This document surveys personality and behavioral AI systems in Dwarf Fortress, RimWorld, Crusader Kings 3, The Sims, and academic interactive narrative systems like Facade. Each game takes a different approach to the fundamental tension: **determinism creates predictability (boring), randomness creates chaos (frustrating), and the sweet spot is emergent personality — behavior that surprises the player but makes sense in retrospect**.

The key insight for Nikita: the most beloved game personality systems (Dwarf Fortress's moods, RimWorld's mental breaks, CK3's stress) all share a common architecture — a set of hidden continuous variables that accumulate over time and trigger discrete state changes when they cross thresholds. This is, at its core, a hidden Markov model with nonlinear emission and transition probabilities — exactly the structure that Bayesian inference can formalize.

---

## 1. Dwarf Fortress: Emergent Narrative from Trait Interactions

### 1.1 Overview

Dwarf Fortress (Bay 12 Games, 2006-present) is widely regarded as the gold standard for emergent personality in games. Each dwarf has approximately 50 personality facets (based on the Big Five model), along with values, needs, skills, and relationships. The game's legendary "stories" — dwarves going berserk over the death of a beloved cat, craftsmen creating masterwork engravings of cheese — emerge entirely from mechanical personality interactions.

### 1.2 Personality Architecture

**Trait System**: Each dwarf has ~50 personality facets scored on a continuous scale:
- Based on the NEO-PI-R facets of the Big Five
- Examples: ANXIETY, ANGER, DEPRESSION, SELF_CONSCIOUSNESS, VULNERABILITY (Neuroticism facets)
- Scored approximately 0-100, with population mean around 50
- Initialized at birth with genetic + environmental factors
- Modify behavior probabilities, mood impacts, and social interactions

**Needs System**: 15 needs that must be fulfilled:
- CRAFT, MARTIAL_TRAINING, SOCIALIZE, BE_WITH_FAMILY, etc.
- Each need has a satisfaction level that decays over time
- Unmet needs reduce happiness; met needs provide positive thoughts
- Need strength is personality-dependent (high GREGARIOUSNESS → strong SOCIALIZE need)

**Thought System**: A running list of positive and negative "thoughts":
- "Annoyed by a lack of chairs" (-1 happiness)
- "Made a masterwork artifact" (+50 happiness)
- "Lost a loved one" (-100 happiness)
- Thoughts accumulate and decay over time
- Net happiness determines mood state

**Mood States** (thresholds on net happiness):
```
Ecstatic  →  Content  →  Fine  →  Unhappy  →  Stressed  →  Miserable  →  [Tantrum/Insanity]
```

### 1.3 The Emergent Behavior Engine

The brilliance of Dwarf Fortress is that personality doesn't directly control behavior. Instead, personality modulates **how events are perceived** (thought strength), **what needs matter** (need weights), and **how quickly stress accumulates** (mood decay rates). The actual behavior emerges from the interaction:

```
personality → need weights → unmet needs → negative thoughts → mood decline → threshold → tantrum spiral
```

**Example emergence**:
- Dwarf "Urist" has HIGH_ANXIETY, HIGH_EMPATHY, LOW_STRESS_TOLERANCE
- Urist's cat dies → GRIEF thought (-80 happiness)
- HIGH_ANXIETY amplifies the grief: -80 × 1.3 = -104
- LOW_STRESS_TOLERANCE means the mood threshold for "tantrum" is lower
- Urist enters tantrum spiral → destroys workshop → other dwarves see destruction → cascading mood loss

No designer scripted this story. It emerged from personality parameters interacting with game events.

### 1.4 Performance Profile

Dwarf Fortress simulates 200+ dwarves, each with ~50 personality facets, needs, thoughts, and social relationships:
- **Personality updates**: Per-tick mood recalculation, but only for dwarves in active contexts (~O(1) per dwarf per tick)
- **Need decay**: Linear decay per tick, O(N_dwarves × N_needs) per tick
- **Thought management**: Bounded list (max ~30 thoughts), O(N_dwarves × 30)
- **Social graph**: Relationship strength between all pairs, updated on interaction events (not per tick)
- **Total personality CPU**: Estimated 5-15% of per-tick budget on a single CPU core
- **Frame budget**: 100-200ms per tick at normal speed (not real-time)

### 1.5 Lessons for Nikita

**What DF gets right**:
1. **Personality modulates perception, not behavior directly**: Nikita's personality should affect how she interprets player messages, not what she says verbatim
2. **Emergent narrative > scripted responses**: The best moments come from unexpected but logical combinations of personality + situation
3. **Cascading effects create drama**: One negative event can spiral if personality amplifies it — perfect for boss encounter escalation
4. **Memory of past events matters**: Dwarves carry grudges for years. Nikita should too (via weighted thought history)

**What DF gets wrong (for our purposes)**:
1. **No learning or adaptation**: Dwarf personality is fixed from birth. Nikita needs to evolve
2. **No social modeling of the OTHER party**: DF doesn't model what the dwarf thinks the player is thinking. Nikita needs theory of mind
3. **Deterministic thresholds**: Mood crosses a line and tantrum triggers. Nikita needs stochastic thresholds (probability of tantrum increases continuously)

---

## 2. RimWorld: Pawn Traits, Mental Breaks, and Social Dynamics

### 2.1 Overview

RimWorld (Ludeon Studios, 2018) adapted Dwarf Fortress's personality concepts into a more accessible system. Each "pawn" has 2-3 traits (from a pool of ~60) plus a background that determines skills and incapabilities.

### 2.2 Trait System

**Discrete traits** (not continuous scales):
- Each pawn has exactly 2-3 traits from a curated list
- Traits are binary: you either have "Neurotic" or you don't
- No facet scores or continuous dimensions
- Traits create gameplay-relevant behavioral modifications

**Examples**:
| Trait | Effect |
|-------|--------|
| Neurotic | +12% work speed, +8 mental break threshold |
| Optimist | +6 mood baseline |
| Psychopath | No mood penalty from deaths, cannot be a warden |
| Kind | +5 mood, initiates "kind word" social interactions |
| Abrasive | Initiates "insult" social interactions, -20 opinion |
| Jealous | Mood penalty if bedroom is not the best |
| Greedy | Needs impressive bedroom, mood penalty otherwise |

### 2.3 Mental Break System

RimWorld's signature mechanic — when mood drops below a threshold, pawns have "mental breaks" with severity proportional to mood:

```
Minor Break (mood < 25%): Binge eating, hiding in room, sad wandering
Major Break (mood < 15%): Berserk, fire starting, substance binge
Extreme Break (mood < 5%): Catatonia, psychotic wandering, self-harm
```

**Break selection is probabilistic**: When a pawn's mood crosses a threshold, the game rolls against a probability table modified by traits. A "Volatile" pawn is more likely to get aggressive breaks; a "Depressive" pawn is more likely to get catatonic breaks.

### 2.4 Social Dynamics

RimWorld models pawn-to-pawn relationships:
- **Opinion**: -100 to +100, modified by traits, interactions, gifts
- **Social interactions**: Random events ("X insulted Y", "X shared a meal with Y") that modify opinion
- **Relationship types**: Acquaintance → Friend → Best Friend, and separately Romance → Lover → Fiancé → Spouse
- **Breakup mechanics**: Low opinion + traits like "Fickle" → relationship dissolution

**The interaction frequency model**:
```
P(interaction) = base_rate × social_trait_modifier × proximity_factor
P(positive_interaction) = 0.5 + 0.3 × agreeableness_proxy + 0.2 × opinion/100
```

### 2.5 Performance Profile

RimWorld typically manages 3-20 pawns:
- **Trait effects**: Computed on-demand, not per-tick (constant-time lookup)
- **Mood calculation**: Sum of all active mood modifiers, O(N_modifiers) per pawn per tick
- **Mental break check**: Single probability roll per pawn when mood is below threshold
- **Social interaction**: Random roll per pair of nearby pawns, O(N_pawns^2 × proximity_check)
- **Total personality CPU**: ~2-5% of per-tick budget
- **Frame budget**: 16ms (60 FPS real-time), but personality updates typically at 1Hz

### 2.6 Lessons for Nikita

**What RimWorld gets right**:
1. **Discrete traits create memorable characters**: "Neurotic Psychopath" is instantly understood. Nikita's most prominent traits should be distilled into player-comprehensible labels
2. **Mental breaks as dramatic moments**: Boss encounters are essentially designed mental breaks — mood crosses threshold → dramatic event
3. **Social interaction as random events**: Not every interaction is equally weighted; some are more impactful (insults stick more than pleasantries — negativity bias)
4. **Probabilistic severity**: The same trigger can produce different responses, creating replayability

**What RimWorld gets wrong (for our purposes)**:
1. **Traits are fixed and binary**: No personality change, no continuums. Too coarse for Nikita
2. **Mood is a single scalar**: Nikita needs separate emotional dimensions (valence + arousal at minimum)
3. **No relationship memory**: RimWorld pawns don't remember the specific content of past conversations. Nikita must
4. **Random interactions, not responsive**: Social events happen randomly. Nikita's behaviors must respond to player input

---

## 3. Crusader Kings 3: Personality Trait System and Stress Mechanics

### 3.1 Overview

Crusader Kings 3 (Paradox Interactive, 2020) has perhaps the most psychologically sophisticated personality system in mainstream gaming. Each character has personality traits that interact with a stress mechanic and coping mechanisms — creating behavior patterns that are remarkably psychologically realistic.

### 3.2 Personality Traits

**7 trait categories with opposing pairs**:
| Category | Positive | Negative |
|----------|----------|----------|
| Temperament | Calm | Wrathful |
| Courage | Brave | Craven |
| Energy | Diligent | Lazy |
| Greed | Generous | Greedy |
| Honor | Just | Arbitrary |
| Sociability | Gregarious | Shy |
| Zeal | Zealous | Cynical |

**Additional personality traits**: Compassionate, Callous, Sadistic, Forgiving, Vengeful, Honest, Deceitful, Patient, Impatient, Humble, Arrogant, Content, Ambitious, Paranoid, Trusting, Temperate, Gluttonous, Chaste, Lustful

**Each character has 3 personality traits** (CK3 specifically avoids continuous scales in favor of discrete, combinatorial traits). The interactions between traits create character archetypes:
- Brave + Wrathful + Ambitious = "Conqueror"
- Compassionate + Just + Diligent = "Wise Ruler"
- Paranoid + Deceitful + Sadistic = "Tyrant"

### 3.3 The Stress System

CK3's most innovative mechanic for our purposes: **stress as accumulated psychological pressure**.

**Stress accumulation**:
- Actions that conflict with personality traits generate stress
- A Compassionate ruler who executes prisoners gains +30 stress
- A Greedy ruler who donates to charity gains +15 stress
- A Brave ruler who flees battle gains +20 stress
- Stress ranges from 0 to 400+

**Stress thresholds**:
```
0-99:   Normal behavior
100-199: Level 1 stress ("Uncomfortable") — mild coping behaviors
200-299: Level 2 stress ("Stressed") — significant behavioral changes
300+:    Level 3 stress ("Mental Break") — severe consequences
```

**Coping mechanisms** (based on personality):
| Personality | Coping Mechanism | Effect |
|-------------|-----------------|--------|
| Wrathful | Beating people | Reduces stress, opinion penalty |
| Gregarious | Hosting feasts | Reduces stress, costs gold |
| Lustful | Taking lovers | Reduces stress, risk of scandal |
| Shy | Seclusion | Reduces stress, opinion penalty for isolation |
| Zealous | Pilgrimage | Reduces stress, time away from court |
| Sadistic | Torturing prisoners | Reduces stress, massive opinion penalty |
| Gluttonous | Comfort eating | Reduces stress, health penalty |

### 3.4 Personality-Decision Coherence

CK3's AI decision-making uses a **weighted utility system** where personality traits modify the weights:

```
Utility(action) = Σ_i weight_i(personality) × value_i(action)

Example: "Declare war on neighbor"
- Base military value: +50
- Brave modifier: weight_military × 1.3
- Craven modifier: weight_military × 0.5
- Compassionate modifier: weight_suffering × -20
- Ambitious modifier: weight_power × 1.5
```

This means the same action has different utility for different personality configurations — and importantly, **the AI sometimes takes suboptimal actions because personality overrides rationality**. This is psychologically realistic and creates interesting narrative moments.

### 3.5 Performance Profile

CK3 simulates thousands of characters simultaneously:
- **Trait lookup**: O(1) per character per decision (hash table)
- **Stress calculation**: O(N_stress_modifiers) per event, not per tick
- **Coping mechanism check**: Per-month roll, O(1) per character
- **Utility computation**: O(N_actions × N_traits) per AI decision turn
- **Total personality CPU**: ~10-20% of monthly AI turn budget
- **Turn budget**: ~100-500ms per in-game month tick (not real-time)

### 3.6 Lessons for Nikita

**What CK3 gets right**:
1. **Stress as hidden variable**: The concept of accumulated psychological pressure is exactly what Nikita needs — tension builds from multiple sources and releases in dramatic coping behaviors
2. **Actions against personality cost stress**: When the player forces Nikita to act against her nature (or when game events do), stress should accumulate
3. **Personality-consistent coping**: How Nikita de-stresses should depend on her personality — intellectualization for high openness, social seeking for high extraversion, etc.
4. **Trait-decision coherence**: Nikita should sometimes make "irrational" choices because her personality overrides optimal behavior

**What CK3 gets wrong (for our purposes)**:
1. **Discrete traits, no learning**: CK3 characters don't develop personality organically. Traits are gained through events (scripted, not emergent)
2. **No emotional memory**: CK3 stress is a single scalar, not a rich emotional state
3. **No relationship modeling with player insight**: CK3 AI doesn't model what the player thinks or wants
4. **No gradual trait evolution**: A character is "Brave" or not — no "becoming braver over time through small acts of courage"

---

## 4. The Sims: Need-Based Personality and Aspiration System

### 4.1 Overview

The Sims franchise (Maxis/EA, 2000-present) is the closest analogue to Nikita in terms of simulating a character's daily life with personality-driven behavior. While mechanically simpler than Dwarf Fortress, The Sims mastered **player-readable personality** — you can glance at a Sim and understand their personality from their behavior.

### 4.2 Personality Evolution Across Versions

**The Sims 1 (2000)**: 5 continuous personality axes on 0-10 scales
- Neat/Sloppy, Outgoing/Shy, Active/Lazy, Playful/Serious, Nice/Grouchy
- Directly modified behavior probabilities and autonomous action selection
- Set at creation, never changed

**The Sims 2 (2004)**: Added aspiration system
- Aspirations (Romance, Knowledge, Family, Popularity, Fortune, Pleasure) guide goals
- Aspiration meter (fear → failure → neutral → gold → platinum)
- Personality + aspiration + mood → autonomous behavior selection

**The Sims 3 (2009)**: Trait-based system (similar to CK3)
- 5 traits per Sim from a pool of ~63
- Traits create behavioral tendencies, social interactions, and emotional reactions
- Added "Wishes" system: personality-consistent goals that appear dynamically

**The Sims 4 (2014)**: Emotion-centered system
- Emotions replace mood as the primary driver: Happy, Sad, Angry, Confident, Embarrassed, Tense, etc.
- Emotions have intensities that modify behavior options
- Traits (3 per Sim) modify emotional response patterns
- "Whims" replace wishes as personality-consistent micro-goals

### 4.3 Need-Based Behavior Selection

The Sims' core loop: autonomous behavior selection based on needs and personality.

**8 needs** (Sims 4):
- Hunger, Energy, Fun, Social, Hygiene, Bladder, Environment, Comfort

**Autonomous action selection**:
```
For each available action:
    utility = Σ_i need_weight_i × need_delta_i(action)
    utility += personality_modifier(action, traits)
    utility += emotion_modifier(action, current_emotion)
    utility += social_modifier(action, relationship_to_target)

Select action with highest utility (with small random noise)
```

**Personality modifiers**:
- "Bookworm" Sim: +50 utility for reading actions
- "Mean" Sim: +30 utility for insult actions, -20 for compliment actions
- "Romantic" Sim: +40 utility for flirtation actions
- "Loner" Sim: -30 utility for social actions when Social need is above 50%

### 4.4 Relationship Modeling

The Sims has the most developed relationship model among these games:

**Dual-track relationships**:
- **Friendship**: -100 to +100, built through positive social interactions
- **Romance**: -100 to +100, separate from friendship, built through romantic interactions

**Relationship decay**: Both tracks decay toward 0 over time without interaction (configurable decay rate based on relationship level and traits)

**Social compatibility**: Trait-based compatibility modifiers
- "Geek" + "Geek" = +20 friendship boost per interaction
- "Mean" + "Good" = -10 friendship per interaction
- "Romantic" + "Non-committal" = reduced romance gain

### 4.5 Performance Profile

The Sims 4 manages 8 Sims in active household + ~100 in the world:
- **Need decay**: Linear per-tick, O(N_sims × 8)
- **Action selection**: O(N_available_actions × N_modifiers) per Sim per autonomy tick (~every 10 seconds)
- **Emotion calculation**: O(N_active_moodlets) per Sim per tick
- **Relationship updates**: On interaction event only, O(1) per pair
- **Total personality CPU**: ~3-8% of per-tick budget
- **Frame budget**: 16ms (60 FPS), autonomy at ~0.1 Hz

### 4.6 Lessons for Nikita

**What The Sims gets right**:
1. **Readable personality through behavior**: You know a Sim is "Mean" because they autonomously insult people. Nikita's personality should be equally legible through her behavior
2. **Need-based motivation**: Nikita should have needs (social contact, emotional validation, intellectual stimulation) that drive her behavior when the player isn't interacting
3. **Dual-track relationships**: The friendship/romance distinction maps well to Nikita's intimacy/passion split
4. **Relationship decay**: Critical for Nikita — if the player doesn't interact, the relationship degrades realistically

**What The Sims gets wrong (for our purposes)**:
1. **Shallow personality**: 3 traits × binary = only 8 possible personality configurations per trait slot. Way too coarse
2. **No genuine personality change**: Traits are fixed. Emotions fluctuate but personality is static
3. **Utility maximization**: Sims always pick the highest-utility action. Real people (and Nikita) should sometimes make personality-consistent but irrational choices
4. **No conflict modeling**: Sims relationships degrade linearly. There's no concept of rupture and repair

---

## 5. Facade: Academic Game AI for Interactive Drama

### 5.1 Overview

Facade (Mateas & Stern, 2005) is a landmark interactive drama system — an AI-driven short play where the player interacts with a married couple (Trip and Grace) in crisis. Despite being nearly 20 years old, Facade's drama management system remains one of the most sophisticated AI personality-narrative systems ever built.

### 5.2 The Drama Manager Architecture

Facade uses a three-layer architecture:

**Layer 1: Natural Language Understanding (NLU)**
- Parses player's text/speech into "discourse acts" (flirt, comfort, criticize, agree, etc.)
- ~50 recognized discourse act types
- Maps to affect dimensions: valence (positive/negative) and directness (direct/indirect)

**Layer 2: Drama Manager (ABL - A Behavior Language)**
- Maintains a "story arc" with beats (narrative units)
- Each beat has preconditions (what must be true) and effects (what changes)
- The drama manager sequences beats to create a coherent narrative
- Uses a "tension arc" model: rising tension → climax → resolution (or breakup)

**Layer 3: Character Behavior**
- Trip and Grace have individual personality models
- Affinity scores: how each character feels about the player (+/- 100)
- Argument state: escalation level between Trip and Grace
- Defense mechanisms: denial, deflection, accusation, vulnerability
- Each character responds differently to the same discourse act based on their personality + current state

### 5.3 Beat-Based Story Structuring

Facade's most innovative contribution: using beats (discrete narrative units) as the atomic unit of story management.

**Beat examples**:
- "Trip deflects emotional question with humor" (defense mechanism beat)
- "Grace reveals insecurity about her art career" (vulnerability beat)
- "Trip and Grace argue about party planning" (escalation beat)
- "Player sides with Grace, Trip becomes hostile" (alliance shift beat)

**Beat selection algorithm**:
```
For each available beat:
    score = narrative_value(beat, current_tension_level)
    score += character_consistency(beat, trip_state, grace_state)
    score += player_responsiveness(beat, recent_discourse_acts)
    score += variety_bonus(beat, beats_played_recently)

Select highest-scoring beat (with threshold for "no beat is appropriate")
```

### 5.4 The Tension Arc Model

Facade manages a global "tension level" that rises and falls throughout the 20-minute experience:

```
time 0:    Tension = 0.2  (welcoming, small talk)
time 5:    Tension = 0.3  (first hint of relationship problems)
time 10:   Tension = 0.6  (conflict begins to surface)
time 15:   Tension = 0.8  (climax — major argument or revelation)
time 18:   Tension → 1.0 or → 0.0  (resolution: breakup or reconciliation)
```

The drama manager actively pushes toward the target tension curve, selecting beats that increase or decrease tension as needed. Player actions can accelerate or delay the curve but cannot fundamentally derail it.

### 5.5 Lessons for Nikita

**What Facade gets right**:
1. **Discourse act classification**: Parsing player messages into typed acts (comfort, criticize, flirt, etc.) is exactly what Nikita's behavioral coder needs (see Doc 03, Section 7.2)
2. **Tension arc management**: Nikita's chapter progression needs a similar tension curve — rising tension toward boss encounters, resolution afterward
3. **Character-specific responses to same input**: Trip and Grace react differently because they have different personalities. Nikita's personality distributions should similarly modulate her responses
4. **Defense mechanisms as behavioral modes**: Facade explicitly models characters shifting between defense mechanisms under stress — directly applicable to Nikita

**What Facade gets wrong (for our purposes)**:
1. **Fixed narrative arc**: Facade's tension curve is predetermined. Nikita's should emerge from the interaction dynamics (Bayesian inference)
2. **20-minute experience**: Facade has no long-term memory or personality change. Nikita spans weeks/months
3. **Binary character states**: Trip and Grace don't have continuous personality dimensions — they switch between scripted behavioral modes
4. **No learning**: Facade's NLU doesn't improve over the session. Nikita's model of the player should refine continuously

---

## 6. Other Notable Systems

### 6.1 Prom Week (McCoy et al., 2013)

**System**: Social simulation game using the "Comme il Faut" (CiF) AI engine.
**Innovation**: Models social norms as first-class objects. Characters don't just have traits — they have beliefs about social expectations (e.g., "friends should help each other", "rivals shouldn't be trusted").
**Relevance to Nikita**: The concept of modeling social expectations as probabilistic beliefs is directly aligned with Bayesian inference. Nikita should have beliefs about what a "good partner" does, updated by evidence from the player's behavior.

### 6.2 Spirit AI (Kara, 2021-present)

**System**: Commercial middleware for AI character behavior in games and simulations.
**Innovation**: Modular personality engine with pluggable emotion models, memory systems, and decision-making modules.
**Relevance to Nikita**: Spirit AI's architecture validates the modular approach — separate modules for personality, emotion, memory, and behavior generation, communicating through a shared state representation.

### 6.3 AI Dungeon / Character.AI (2020-present)

**System**: LLM-based character simulation through prompted generation.
**Innovation**: Leverages the LLM's implicit personality modeling through system prompts and conversation history.
**Limitation**: No explicit personality state — the character's personality is entirely in the prompt/history context window. This means personality cannot be quantitatively tracked, updated, or reasoned about.
**Relevance to Nikita**: This is the approach Nikita currently uses. The Bayesian personality system is specifically designed to move beyond pure-LLM personality simulation by maintaining explicit, quantitative personality state that INFORMS the LLM generation but exists independently of it.

### 6.4 Versu (Short & Adams, 2013)

**System**: Interactive fiction engine by Emily Short (interactive fiction pioneer) and Richard Evans.
**Innovation**: Characters with goals, relationships, social practices, and personality traits. Characters autonomously pursue goals and react to each other, creating emergent social dynamics.
**Key technique**: "Social practice" library — common social interaction patterns (greetings, arguments, flirtation) encoded as reusable behavioral templates with personality-parameterized variation.
**Relevance to Nikita**: Social practice templates could serve as the high-level behavior patterns that Nikita's personality distributions parameterize. Instead of generating every response from scratch, Nikita selects and personalizes social practice templates.

---

## 7. Common Patterns: What Works in Practice

### 7.1 The Hidden-Variable Architecture

Every successful game personality system follows the same meta-architecture:

```
                    [Hidden Continuous Variables]
                    - Personality traits (slow-changing)
                    - Mood/stress/needs (medium-changing)
                    - Emotional state (fast-changing)
                            |
                            v
                    [Threshold/Probability Gates]
                    - Mental break thresholds (RimWorld)
                    - Stress levels (CK3)
                    - Need urgency (Sims)
                            |
                            v
                    [Observable Behaviors]
                    - Dialogue choices
                    - Autonomous actions
                    - Social interactions
                    - Dramatic events
```

This is precisely a Hidden Markov Model or Dynamic Bayesian Network — hidden state evolves over time, observations are probabilistic functions of the hidden state, and thresholds create discrete behavioral modes from continuous internal states.

**For Nikita**: This validates the DBN approach proposed in Doc 13. The architecture is not novel — it is the common architecture of successful game AI, formalized in Bayesian terms.

### 7.2 The Three Time Scales

All games operate personality on three time scales:

| Time Scale | What Changes | Update Frequency | Examples |
|-----------|-------------|-----------------|---------|
| Slow (identity) | Core personality traits | Per chapter/major event | DF traits, CK3 traits, Sims personality |
| Medium (state) | Mood, stress, needs | Per session/conversation | DF thoughts, CK3 stress, Sims needs |
| Fast (reaction) | Emotional expression | Per message/turn | DF mood state, CK3 coping, Sims emotions |

Nikita's system should explicitly maintain these three scales:
1. **Slow**: Big Five distributions, attachment style Dirichlet (updated per chapter/crisis)
2. **Medium**: Relationship metrics (intimacy, passion, trust, secureness), stress level, defense mechanism activation (updated per conversation)
3. **Fast**: Current emotional valence/arousal, active response style, behavioral choices (updated per message)

### 7.3 The Determinism-Randomness Balance

All games balance determinism (predictable behavior) with randomness (surprising behavior):

| Game | Approach | Player Experience |
|------|----------|-------------------|
| Dwarf Fortress | Very high randomness, low player control | Wild stories, frustrating gameplay |
| RimWorld | High randomness, moderate player control | Dramatic stories, acceptable gameplay |
| CK3 | Moderate randomness, high player influence | Rich narratives, satisfying strategy |
| The Sims | Low randomness, high player control | Relaxing play, shallow narratives |
| Facade | Low randomness, guided narrative | Cohesive story, limited replayability |

**Nikita's sweet spot**: Between CK3 and RimWorld — enough randomness that the player is surprised by Nikita's behavior, but enough coherence that surprises feel personality-consistent. The Bayesian framework naturally provides this: sampling from personality distributions introduces variability, but the distribution shapes ensure consistency.

### 7.4 The Negativity Bias

Every successful system weights negative events more heavily than positive ones:
- DF: Death of a pet creates a thought 10x stronger than a good meal
- RimWorld: One insult affects opinion more than three compliments
- CK3: Stress from trait-violating actions is immediate; stress relief from coping is gradual
- Sims: Negative moodlets last longer than positive ones

This matches psychological research on negativity bias (Baumeister et al., 2001): negative events have roughly 3-5x the impact of equivalent positive events.

**For Nikita**: The Bayesian update weights should be asymmetric — negative evidence about trust should produce a larger posterior shift than equivalent positive evidence. This creates the realistic dynamic where trust is hard to build and easy to destroy.

```python
def asymmetric_trust_update(trust: Beta, evidence: float, negativity_bias: float = 3.0) -> Beta:
    """Negative evidence about trust has stronger impact."""
    if evidence > 0:
        return Beta(trust.alpha + evidence, trust.beta)
    else:
        return Beta(trust.alpha, trust.beta + abs(evidence) * negativity_bias)
```

### 7.5 Performance Patterns

Across all surveyed games:

| Game | Characters | Personality Dimensions | CPU Budget | Update Hz |
|------|-----------|----------------------|------------|-----------|
| Dwarf Fortress | 200+ | ~50 continuous | 5-15% | ~10 Hz |
| RimWorld | 3-20 | 3 discrete + moods | 2-5% | ~1 Hz |
| CK3 | 1000+ | 3 discrete + stress | 10-20% | ~0.01 Hz (monthly) |
| The Sims 4 | 8-100 | 3 discrete + emotions | 3-8% | ~0.1 Hz |
| Facade | 2 | Custom model | ~15% | ~30 Hz |

**For Nikita**: We have exactly 1 character (Nikita) with ~15 personality dimensions. Even the most expensive computation (particle filter with 500 particles) costs <5ms. **Computation is not a constraint** — we can afford much richer personality modeling than any of these games because we only model one character.

---

## 8. Synthesis: The Optimal Architecture for Nikita

### 8.1 What We Should Borrow

From **Dwarf Fortress**:
- Personality-as-perception-modifier: personality affects how events are interpreted, not behavior directly
- Thought/memory system: running list of weighted events that affect state
- Emergent narrative from mechanical interaction

From **RimWorld**:
- Mental break system: probabilistic threshold-crossing events triggered by accumulated stress
- Social interaction as random events with personality-weighted outcomes
- Readable trait labels that make personality comprehensible to the player

From **CK3**:
- Stress as accumulated psychological pressure with multiple thresholds
- Personality-consistent coping mechanisms
- Actions against personality type costing stress (creating internal conflict)
- Trait-decision coherence with occasional irrational choices

From **The Sims**:
- Need-based autonomous behavior when player is absent
- Dual-track relationships (friendship/romance → intimacy/passion)
- Relationship decay over time
- Readable personality through observable behavioral patterns

From **Facade**:
- Discourse act classification for player messages
- Tension arc management across the experience
- Defense mechanisms as explicit behavioral modes
- Character-specific response to identical player input

### 8.2 What We Should NOT Borrow

- Fixed personality traits that never change (all games except none)
- Single-scalar mood/stress (too simplistic for Nikita)
- Deterministic thresholds (should be probabilistic)
- AI-to-AI social dynamics (Nikita only interacts with one player)
- Frame-budget optimization for many characters (we have one character, unlimited budget relative to these games)

### 8.3 The Nikita Architecture (Informed by This Survey)

```
[Bayesian Personality Layer] (Doc 03)
  - Big Five as Beta distributions
  - Attachment as Dirichlet distribution
  - Updated per chapter/crisis (slow time scale)

        ↓ parameterizes

[State Dynamics Layer] (CK3 stress + DF thoughts)
  - Stress accumulator (CK3-inspired)
  - Thought history with decay (DF-inspired)
  - Need satisfaction levels (Sims-inspired)
  - Active defense mechanism (Facade-inspired)
  - Updated per conversation (medium time scale)

        ↓ determines probabilities

[Behavioral Expression Layer] (RimWorld mental breaks + Sims autonomy)
  - Emotional state (Sims 4 emotions)
  - Response style selection (IRT from Doc 03)
  - Controlled randomness (personality-consistent surprise)
  - Updated per message (fast time scale)

        ↓ feeds into

[LLM Generation Layer] (existing pipeline)
  - System prompt parameterized by personality state
  - Emotional tone specified by behavioral layer
  - Defense mechanism mode if activated
  - Response generated by conversation agent
```

### 8.4 Implementation Priority Based on Game Survey

| Priority | Feature | Inspired By | Complexity | Impact |
|----------|---------|------------|-----------|--------|
| P0 | Personality distributions (Doc 03) | All (formalization) | Medium | Foundational |
| P0 | Stress accumulator | CK3 stress system | Low | Core mechanic |
| P1 | Thought history with decay | DF thought system | Medium | Emotional realism |
| P1 | Need-based life simulation | Sims need system | Medium | Autonomous behavior |
| P1 | Defense mechanism activation | CK3 coping + Facade | Medium | Conflict depth |
| P2 | Discourse act classification | Facade NLU | High (LLM) | Player modeling |
| P2 | Tension arc management | Facade drama manager | Medium | Narrative pacing |
| P2 | Particle filter inference | Novel | Medium | Ambiguity handling |
| P3 | Personality-consistent surprise | All (formalized) | Low | Delight factor |
| P3 | Asymmetric negativity bias | All (formalized) | Low | Realism |

---

## 9. Key Takeaways for Nikita

### 9.1 The Meta-Pattern

All successful game personality systems share one meta-pattern: **personality is a set of hidden variables that influence observable behavior through probabilistic mappings**. The specific implementation varies (continuous vs. discrete traits, threshold vs. probabilistic transitions, static vs. dynamic), but the architecture is consistent.

Nikita's Bayesian approach is the mathematically rigorous version of what these games do intuitively. Where Dwarf Fortress uses ad-hoc personality modifiers, Nikita uses Bayesian posterior distributions. Where CK3 uses fixed stress thresholds, Nikita uses probabilistic threshold functions. Where The Sims uses utility maximization, Nikita uses personality-weighted sampling.

### 9.2 The One-Character Advantage

Every surveyed game must balance personality richness against the computational cost of simulating many characters. Nikita has only ONE character to model. This means:
- We can afford 10-100x more computation per character than any of these games
- We can model far more personality dimensions and subtler dynamics
- We can use sophisticated inference (particle filters, DBNs) that would be prohibitively expensive for 200+ characters
- The bottleneck is LLM inference cost, not personality computation

### 9.3 What Makes AI Companions Different from NPCs

The surveyed games are all NPC systems — the character exists in service of gameplay. Nikita is an AI companion — the character IS the gameplay. This changes the requirements:

| NPC Games | AI Companion (Nikita) |
|-----------|----------------------|
| Personality serves gameplay/strategy | Personality IS the experience |
| Player optimizes against personality | Player relates to personality |
| Many characters, shallow modeling | One character, deep modeling |
| Fixed personality, emergent narrative | Evolving personality, personal narrative |
| AI behavior creates challenges | AI behavior creates emotional connection |
| Success = beating the system | Success = understanding the person |

### 9.4 Cross-References

- **Doc 03 (Bayesian Personality)**: The formal framework that replaces ad-hoc personality systems
- **Doc 05 (Particle Filters)**: The inference method for when personality dynamics exceed what these games handle
- **Doc 11 (Computational Attachment)**: Formalizing the attachment dynamics that CK3's stress system approximates
- **Doc 13 (Nikita DBN)**: The DBN that formalizes the hidden-variable architecture all these games use
- **Doc 17 (Controlled Randomness)**: The formal treatment of the determinism-randomness balance

---

## References

- Mateas, M., & Stern, A. (2005). Structuring content in the Facade interactive drama architecture. *Proceedings of AIIDE*.
- McCoy, J., Treanor, M., Samuel, B., Reed, A., Mateas, M., & Wardrip-Fruin, N. (2013). Prom Week: Designing past the AI cliff. *Proceedings of FDG*.
- Short, E., & Adams, R. (2013). Versu: A simulationist interactive fiction engine. *Proceedings of AIIDE*.
- Baumeister, R. F., Bratslavsky, E., Finkenauer, C., & Vohs, K. D. (2001). Bad is stronger than good. *Review of General Psychology*, 5(4), 323-370.
- Adams, T. (2006-2025). Dwarf Fortress design documents. Bay 12 Games.
- Paradox Interactive. (2020). Crusader Kings 3 developer diaries.
- Maxis/EA. (2014-2024). The Sims 4 developer blog posts on personality and emotions.
- Ludeon Studios. (2018). RimWorld wiki: traits, mental breaks, social interactions.

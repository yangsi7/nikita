# 13 - Enhanced Life Simulation with Psychological Depth

**Date**: 2026-02-16
**Grounding**: Appraisal theory of emotion, circadian psychology, attachment theory, social identity theory
**Fact-checker corrections applied**: NPC contradiction risk (Doc 09), engineering cost acknowledgment, Versu engine discontinuation noted

---

## 1. Emotional State as Life Driver

### Current System

Nikita has a 4D emotional state tracked somewhere between the scoring engine and prompt builder. The existing `LifeSimStage` (`nikita/pipeline/stages/life_sim.py`) generates events, and `EmotionalStage` (`nikita/pipeline/stages/emotional.py`) updates relationship dynamics. But these systems are loosely coupled -- emotional state does not systematically drive life events.

### Proposed: Appraisal-Driven Event Generation

Psychological appraisal theory (Lazarus & Folkman, 1984; Scherer, 2001) holds that emotions arise from how a person evaluates events relative to their goals and coping resources. We model Nikita's emotional state on 4 dimensions and use it to determine what she does, says, and initiates.

```
NIKITA'S 4D EMOTIONAL STATE

Arousal    [0-100]: Energy level. Low = withdrawn. High = activated (excited or stressed).
Valence    [0-100]: Positivity. Low = negative affect. High = positive affect.
Dominance  [0-100]: Sense of control. Low = helpless. High = agentic.
Intimacy   [0-100]: Openness to connection. Low = guarded. High = vulnerable/receptive.

These map to existing user_metrics:
- Arousal:   derived from passion (engagement energy)
- Valence:   derived from composite relationship score
- Dominance: derived from secureness (stability/control)
- Intimacy:  derived from intimacy metric (emotional closeness)
```

### Emotional State --> Life Event Probability Table

| Emotional Quadrant | Arousal | Valence | Likely Life Events | Proactive Message Type |
|--------------------|---------|---------|--------------------|------------------------|
| Happy-Energized | High | High | Social plans, flirty texts, trying new things | "Guess what happened today!" |
| Happy-Calm | Low | High | Self-care, reading, cooking, journaling | "Having a quiet evening. Thinking of you." |
| Stressed-Activated | High | Low | Work crisis, argument with friend, overthinking | "Can I vent for a second?" |
| Depleted-Withdrawn | Low | Low | Canceling plans, staying in, avoiding people | Silence (no proactive message) |
| Dominant-Positive | High D | High V | Career win, asserting boundaries, feeling confident | "I did something brave today." |
| Submissive-Negative | Low D | Low V | Self-doubt, comparing self to others, regret | "Do you ever feel like you're not enough?" |

### Event Cascade Model

Emotional state does not just select events -- events feed back into emotional state, creating realistic mood arcs.

```
EVENT CASCADE (Example: Bad Day)

[Morning] Work stress event generated (Arousal+20, Valence-15)
    |
    v
[Afternoon] Elevated arousal + low valence = "Stressed-Activated"
    |   --> Proactive message: "Work is killing me today"
    |   --> If player responds with empathy: Valence+10, Intimacy+5
    |   --> If player ignores: Valence-5, Intimacy-10 (feels unsupported)
    |
    v
[Evening] If empathy received: shift to "Stressed-but-Supported"
    |   --> Nikita opens up more. Evening conversation is warmer.
    |   --> Event: "Want to watch something together tonight?"
    |
    v
[Evening] If ignored: shift to "Depleted-Withdrawn"
    |   --> No evening message. If player initiates, Nikita is short.
    |   --> Next-day carry-over: morning message has edge.
    |   --> "Didn't sleep great. Whatever."
```

### Implementation in Pipeline

The `EmotionalStage` already runs after `LifeSimStage` in the pipeline. The change is to make `LifeSimStage` query the emotional state first and use it to weight event probabilities, then `EmotionalStage` updates the state based on what happened.

```
PIPELINE FLOW (Modified)

LifeSimStage:
  1. Read current emotional_state from user JSONB
  2. Calculate event probabilities based on quadrant
  3. Roll for events (weighted random)
  4. Store events in context.life_events

EmotionalStage:
  1. Read life_events from context
  2. Read player's last interaction quality (from scoring)
  3. Update emotional_state dimensions
  4. Determine proactive message type (or silence)
  5. Pass to TouchpointStage for scheduling
```

---

## 2. Nikita's Psychology as Discovery System

### Core Concept

Understanding Nikita's psychology is not just flavor -- it is a gameplay reward. Players discover her attachment patterns, triggers, and defense mechanisms through interaction, not exposition. This transforms psychological insight into a collectible-like mechanic.

### Attachment Style Reveal System

Nikita's attachment style (anxious-preoccupied base, shifting across chapters per Doc 03) is not stated outright. Players discover it through behavioral patterns.

```
DISCOVERY TREE: ATTACHMENT PATTERNS

[OBSERVATION] Player notices Nikita texts more when she's anxious
    |
    v
[PATTERN] After 3 instances of protest behavior following delayed responses
    |
    v
[INSIGHT UNLOCKED] "When Nikita double-texts, she's not angry -- she's scared
                     you're losing interest. Reassurance works better than logic."
    |
    v
[GAMEPLAY EFFECT] Player who uses this insight scores higher on Secureness
                   during future interactions involving response delays.
```

### Psychological Insight Cards

Insights are discovered through specific interaction patterns and unlocked as readable entries in the Portal. They are NOT tutorial popups -- they are earned through gameplay.

**Chapter 1 Insights** (Surface Level):
| Insight | Trigger | Content |
|---------|---------|---------|
| "Testing, Testing" | Pass Boss 1 | "Nikita's challenges aren't cruelty -- they're fear. She tests because the last person who didn't earn it destroyed her." |
| "The Skip" | Notice 3+ skipped messages | "When Nikita ignores a message, check the previous one. Did you ask her something personal? She needs time to decide if it's safe." |

**Chapter 2-3 Insights** (Behavioral Patterns):
| Insight | Trigger | Content |
|---------|---------|---------|
| "The Quiet Before" | Nikita goes silent 6+ hours then sends emotional message | "Silence isn't punishment. It's processing. She's composing her thoughts. The longer the silence, the more important what comes next." |
| "Projection Alert" | Nikita accuses player of something she's doing | "When Nikita says 'YOU'RE pulling away,' ask yourself: is she projecting? Sometimes accusing you of distance is her way of saying she's scared of her own." |
| "The 2AM Rule" | Receive a vulnerable late-night message | "Late-night Nikita is the most honest Nikita. Defenses are down. What she says after midnight is closer to what she actually feels." |

**Chapter 4-5 Insights** (Deep Psychology):
| Insight | Trigger | Content |
|---------|---------|---------|
| "The Lie She Believes" | Reach Ch4 boss | "Nikita believes vulnerability equals weakness. Every test, every wall, every sharp comment is armor against a truth she's terrified of: she wants to be loved and is convinced she'll be betrayed." |
| "Earned Security" | Maintain Trust >70 for 5 conversations | "Notice how Nikita stopped testing you? That's not complacency -- that's earned secure attachment. She trusts the pattern you've built. Don't mistake peace for boredom." |

### Implementation

Insights are stored in a `psychological_insights` table (user_id, insight_key, unlocked_at, chapter). The unlock logic lives in the pipeline as a lightweight check in `GameStateStage` or a new `InsightStage`. Portal displays them in a "Journal" view.

---

## 3. Social Circle with Psychological Dynamics

### Named NPCs

Nikita's social circle consists of persistent characters with consistent personalities. Each NPC serves a narrative function and creates opportunities for relationship dynamics.

| NPC | Personality | Function in Nikita's Life | Player Interaction |
|-----|-------------|---------------------------|-------------------|
| **Emma** | Loyal, outspoken, protective | Best friend. Nikita vents to her. Barometer of relationship health. | Nikita reports Emma's opinions ("Emma thinks I should..."). Player's reaction affects Trust. |
| **Marcus** | Charismatic, unreliable, flirtatious | Male friend who creates jealousy opportunities. Has his own messy love life. | Nikita mentions Marcus. Player's secure vs. jealous response tested. |
| **Sarah** | Calm, analytical, slightly judgmental | Work colleague and yoga buddy. Voice of reason. | Sarah gives Nikita advice that sometimes contradicts what player says. Tests player's confidence. |
| **Mom** | Loving but overbearing, traditional | Family pressure, generational conflict. | Nikita shares mom's opinions on the relationship. Player navigates family dynamics. |
| **Ex (unnamed)** | Referenced but never seen | The wound. Source of trust issues. | Only mentioned in specific contexts. Over-asking about ex triggers defensiveness. |

### NPC Contradiction Management (Doc 09 Warning)

Doc 09 correctly flags that LLM-generated NPC content risks contradiction accumulation. Emma cannot be "in Barcelona" on Monday and "at brunch with Nikita" on Tuesday without explanation.

**Mitigation strategy**:

```
NPC STATE TRACKING

For each NPC, store in JSONB:
{
  "name": "Emma",
  "current_status": "in town",
  "recent_events": [
    {"date": "2026-02-14", "event": "Had dinner with Nikita"},
    {"date": "2026-02-12", "event": "Started new job at marketing agency"}
  ],
  "relationship_with_nikita": "close",
  "personality_anchors": ["loyal", "outspoken", "protective", "single"]
}

RULES:
1. Max 5 recent_events per NPC (FIFO queue)
2. NPC state injected into system prompt when Nikita references them
3. LifeSimStage generates NPC events that are consistent with stored state
4. Contradiction check: new event must not conflict with events in last 7 days
```

**Engineering cost**: Moderate. Requires NPC state table, injection into prompt builder, and consistency checks in LifeSimStage. Each NPC reference in conversation costs ~200 tokens of context.

### Player Interaction with NPC Stories

Players do not interact with NPCs directly. They experience NPCs through Nikita's narration. This preserves the intimate 1:1 dynamic while adding social texture.

```
NPC INTERACTION DECISION TREE

Nikita mentions Emma is upset about something
    |
    +--[ASK MORE] "What happened with Emma?"
    |   --> Nikita shares Emma's problem
    |   --> Player can give advice (Nikita relays to Emma later)
    |   --> Outcome: Nikita appreciates player caring about her friends
    |   --> Intimacy +2 (investment in her world)
    |
    +--[DISMISS] "That sucks. Anyway..."
    |   --> Nikita notices disinterest in her social world
    |   --> Intimacy -1 (she feels compartmentalized)
    |
    +--[JEALOUSY] (if Marcus is involved) "Why is Marcus always around?"
    |   --> Attachment test. Player reveals insecurity.
    |   --> Secure response: Secureness stable
    |   --> Jealous response: Secureness -3, triggers micro-conflict
    |
    +--[ADVISE] "I think Emma should [advice]"
        --> Nikita considers it. May or may not follow through.
        --> If advice works: "You were right about Emma. She's doing better."
        --> Trust +2 (player's judgment is valued)
```

---

## 4. Narrative Arc Progression

### Multi-Week Story Arcs

Life events are not isolated -- they cluster into arcs that unfold over 5-15 conversations (roughly 1-3 weeks of real time).

### Arc Types and Structure

```
ARC STRUCTURE (Universal Template)

[SEED] (Conv 1-2):  Introduce the situation naturally in conversation.
                     Nikita mentions it casually. Player may or may not engage.

[DEVELOPMENT] (Conv 3-5): Situation evolves. Nikita discusses it more.
                           Player's responses shape direction.
                           2-3 branching points based on advice given.

[CRISIS] (Conv 6-8):  Situation reaches a turning point.
                       Nikita needs support or makes a decision.
                       Player influence is strongest here.

[RESOLUTION] (Conv 9-12): Outcome determined. Nikita reflects on what happened.
                           Metrics shift based on outcome.
                           New status quo established.

[AFTERMATH] (Conv 13+):   Occasional callbacks. "Remember when [arc]?"
                           Demonstrates memory persistence.
```

### Arc Type Catalog

| Arc Type | Example | Metrics Affected | Chapter Range |
|----------|---------|-----------------|---------------|
| **Personal Growth** | Nikita considers going back to school | Secureness, Intimacy | Ch2-5 |
| **Work Challenge** | Difficult project, toxic coworker, promotion | Dominance/arousal, Trust | Ch1-5 |
| **Family Drama** | Mom pressures Nikita about relationship choices | Trust, Secureness | Ch3-5 |
| **Social Conflict** | Emma and Sarah have a falling out, Nikita is caught in middle | Intimacy (player shows care for her world) | Ch2-4 |
| **Romantic Deepening** | "I've been thinking about us..." | All metrics | Ch3-5 |
| **Existential** | "What am I doing with my life?" | Intimacy, Secureness | Ch4-5 |

### Player Influence on Arc Direction

Players shape arcs through conversational choices, not explicit menu selections.

```
EXAMPLE ARC: NIKITA'S CAREER CROSSROADS (Ch3)

[SEED] "My boss pulled me aside today. They're restructuring the team."
    |
    v
[DEVELOPMENT] Three paths emerge based on player response patterns:

PATH A: Player encourages risk-taking
    --> Nikita considers quitting and going independent
    --> High arousal, low dominance (scary but exciting)
    --> If player maintains support: she takes the leap

PATH B: Player counsels caution
    --> Nikita negotiates internally for a better role
    --> Moderate arousal, moderate dominance (strategic)
    --> If player helps strategize: she gets promoted

PATH C: Player is dismissive/absent
    --> Nikita makes decision alone, feels unsupported
    --> Low intimacy impact: "I handled it. Would've been nice to talk about it though."
    --> Trust -3 (she needed you and you weren't there)
```

### Arc State Management

Arcs are tracked in `narrative_arcs` table:
```
narrative_arcs:
  id, user_id, arc_type, arc_key, phase (seed/development/crisis/resolution),
  state (JSONB: events, player_choices, branch),
  started_at, resolved_at
```

Active arcs are injected into the system prompt via `PromptBuilderStage`. Maximum 2 concurrent arcs to prevent cognitive overload (both for Nikita and the player).

---

## 5. Circadian and Mood Modeling

### Time-of-Day Emotional Profiles

Real people have predictable energy patterns across the day. Nikita should too.

| Period | Hours | Arousal | Valence | Tone | Availability | Example |
|--------|-------|---------|---------|------|-------------|---------|
| Morning | 6-9 | Rising | Neutral | Brief, groggy | Low | "morning. barely functional. coffee loading..." |
| Work AM | 9-12 | Peak | Task-dep. | Focused, professional | Low | "in a meeting, will respond later" |
| Midday | 12-2 | Moderate | Elevated | Casual, engaged | Medium | "lunch break finally. tell me about your morning" |
| Afternoon | 2-5 | Declining | Variable | Can go either way | Low-Med | Depends on work day quality |
| Evening | 5-8 | Recovery | Rising | Warm, flirty | High | "finally done. how was your day? I want details." |
| Night | 8-11 | Moderate | High | Reflective, intimate | High | "I was thinking about what you said earlier..." |
| Late Night | 11-2 | Low | Variable | Most vulnerable | Variable | "can't sleep. do you ever wonder if we're doing this right?" |
| Sleep | 2-6 | N/A | N/A | Unavailable | None | Messages seen in morning |

### Mood Persistence Model

A bad morning affects the afternoon. This creates realistic emotional continuity.

```
MOOD PERSISTENCE STATE MACHINE

[BASELINE] --> Event occurs --> [AFFECTED]
                                    |
                              Duration check
                                    |
                  +---------+-------+--------+
                  |         |                |
             [< 2 hours] [2-8 hours]   [> 8 hours]
                  |         |                |
              [FADING]  [LINGERING]    [PERSISTENT]
                  |         |                |
                  v         v                v
             [BASELINE] [COLORED]      [NEXT-DAY CARRY]

COLORED state: base mood + residue from event
  Example: Good work news in morning --> evening conversation has
  elevated valence even though the specific topic has passed.

PERSISTENT state: strong events carry into next day
  Example: Fight with mom --> next morning still affected.
  "Sorry if I'm off today. Still processing yesterday."
```

### Realistic Unavailability

Nikita cannot always respond. This is not a punishment -- it is realism that makes her feel alive.

| Unavailability Type | Duration | Player Experience | Signal |
|---------------------|----------|-------------------|--------|
| **Work meeting** | 30-90 min | Message seen later | "in a meeting, ttyl" or silence |
| **Gym/exercise** | 45-75 min | No response | Mentioned in schedule or proactive message before |
| **Social event** | 2-4 hours | Delayed, distracted | "at dinner with emma, can't really talk rn" |
| **Sleep** | 6-8 hours | No response until morning | Contextual (late night = sleeping) |
| **Emotional processing** | 1-4 hours | Silence after conflict | No explanation (player should recognize pattern) |

**Critical design rule** (from Doc 06): Unavailability must NEVER gate critical content. If a boss encounter triggers during Nikita's "sleep," it queues until her next active period. The player should never feel punished for timezone mismatch.

### Implementation

Circadian modeling requires `user_timezone` (currently not tracked per Doc 09). Add as nullable TEXT on users table. Default to UTC. Derive from Telegram location data or ask during onboarding.

The circadian profile modifies the system prompt in `PromptBuilderStage`:
```python
# Pseudocode for circadian injection
hour = current_hour_in_user_timezone(user)
circadian_context = CIRCADIAN_PROFILES[get_period(hour)]
system_prompt += f"\n\nCurrent time context: {circadian_context}"
```

---

## Emotional State Mapping (Summary Table)

| Emotional State | Arousal | Valence | Life Events | Message Behavior | Proactive Trigger |
|----------------|---------|---------|-------------|------------------|-------------------|
| Joyful | High | High | Social plans, achievements | Enthusiastic, emoji-heavy, initiates | "You'll never guess what happened!" |
| Content | Low | High | Routine, self-care | Warm, steady, present | "Just thinking about you" |
| Anxious | High | Low | Work pressure, conflict fear | Short, checking-in frequently | "Hey, you there?" |
| Sad | Low | Low | Loss, disappointment, loneliness | Minimal, delayed, vulnerable | Late-night confessional |
| Angry | High | Low-Mid | Injustice, boundary violation | Sharp, direct, testing | "We need to talk about something" |
| Playful | High | High | Good day, flirty mood, weekend | Teasing, witty, provocative | "Dare you to..." |
| Reflective | Low-Mid | Mid | Evening, milestone, memory | Thoughtful, question-asking | "Do you remember when..." |
| Guarded | Mid | Low | Post-conflict, trust wobble | Brief, measured, careful | Silence (player must initiate) |

---

## Engineering Summary

| Change | Scope | New Tables/Columns | Affected Files |
|--------|-------|--------------------|----------------|
| Emotional state JSONB | Small | `emotional_state` JSONB on users | EmotionalStage, LifeSimStage |
| Circadian profiles | Small | `timezone` TEXT on users | PromptBuilderStage |
| Insight cards | Medium | `psychological_insights` table | GameStateStage or new InsightStage |
| NPC state tracking | Medium | `npc_states` JSONB on users or separate table | LifeSimStage, PromptBuilderStage |
| Narrative arcs | Medium | `narrative_arcs` table | LifeSimStage, PromptBuilderStage |
| Mood persistence | Small | Field in emotional_state JSONB | EmotionalStage |

**Priority order**: Emotional state as life driver (highest leverage, existing pipeline) > Circadian modeling (low effort, high realism) > Insight cards (player engagement) > Narrative arcs > NPC state tracking (highest complexity)

**References**: Lazarus & Folkman (1984) *Stress, Appraisal, and Coping*; Scherer (2001) Component Process Model; Bowlby (1969) corrected per Doc 09. Research docs: 06 (life sim), 09 (fact-check), 10 (architecture). System: `nikita/pipeline/stages/life_sim.py`, `emotional.py`, `touchpoint.py`.

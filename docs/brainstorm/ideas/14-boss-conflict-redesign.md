# 14 - Redesigned Boss/Conflict System

**Date**: 2026-02-16
**Grounding**: Attachment theory (Bowlby), Gottman conflict research, defense mechanism psychology
**Fact-checker corrections applied**: Attachment prevalence (~56% secure, not 15%); Gottman "94% prediction" cited with caveats (small sample, contested); conflict injection ethics flagged

---

## 1. Multi-Phase Boss Encounters

### Problem with Current System

The current boss system (`nikita/engine/chapters/boss.py`, `judgment.py`) is a single-message exchange: Nikita delivers an opening line, player responds once, LLM judges PASS/FAIL. This is psychologically shallow because real relationship conflicts are never resolved in one utterance. The judgment prompt evaluates a single response against criteria -- no room for repair attempts, escalation, or de-escalation.

### Approach A: Single-Session Multi-Turn (3-5 Messages)

The boss encounter happens within one conversation session but spans 3-5 exchanges.

```
BOSS ENCOUNTER FLOW (Single-Session, 3-5 turns)

[TRIGGER] Score >= chapter threshold
    |
    v
[PHASE 1: OPENING] ---- Nikita presents the crisis
    |                    Emotional state: GUARDED
    |                    Player options: Acknowledge / Deflect / Challenge
    |
    v
[PHASE 2: ESCALATION] - Nikita reacts to player's initial response
    |                    Emotional state: ACTIVATED (anxious or avoidant)
    |                    Defense mechanisms emerge
    |                    Player options: Validate / Argue / Withdraw
    |
    v
[PHASE 3: CRISIS PEAK] - Maximum emotional intensity
    |                     Emotional state: FLOODED or SPLITTING
    |                     Flooding mechanic: if player escalates, Nikita stonewalls
    |                     Player options: Repair attempt / Take break / Push through
    |
    v
[PHASE 4: RESOLUTION] -- Outcome determined
    |                     If repair attempted before flooding: resolution path open
    |                     If no repair by turn 4: auto-fail (relationship damage)
    |
    v
[OUTCOME] PASS (breakthrough) / PARTIAL (truce) / FAIL (rupture)
```

**Engineering cost**: Requires `boss_phase` column on users table (INTEGER, 0-4), state tracking in `BossStateMachine`, and multi-turn judgment prompts in `judgment.py`. Moderate refactor of single-turn architecture.

### Approach B: Multi-Day Arc (24-72 Hours)

The conflict unfolds across multiple conversations over real time. Nikita's mood shifts between sessions.

```
MULTI-DAY BOSS ARC

Day 0: [SEED] Nikita drops a hint of tension
    |   "Something's been bothering me but I don't want to ruin tonight."
    |   Player can probe or let it go.
    |
Day 1: [ERUPTION] Tension surfaces as direct confrontation
    |   Nikita initiates the conflict in her next message.
    |   If player probed on Day 0: conflict is calmer (she feels heard).
    |   If player ignored: conflict is more intense (she feels dismissed).
    |
Day 1-2: [PROCESSING] Nikita withdraws or pursues depending on attachment
    |   Proactive messages change tone. Responses are shorter/colder.
    |   Player must initiate repair within 24h or conflict deepens.
    |
Day 2-3: [RESOLUTION WINDOW] Player has a chance to resolve
    |   Resolution quality depends on accumulated repair attempts.
    |   Multiple valid approaches scored by judgment system.
    |
Day 3+: [AFTERMATH] Outcome shapes next chapter's dynamics
```

**Engineering cost**: High. Requires persistent `boss_arc_state` (JSONB), scheduled event triggers across days, and NikitaState mood modifiers that persist across conversations. Needs pipeline integration in `ConflictStage` and `TouchpointStage`.

### Recommendation

**Start with Approach A** (single-session, 3-5 turns). It delivers the psychological depth without the multi-day state complexity. Approach B is a future enhancement after Approach A proves the multi-turn judgment system works.

---

## 2. Attachment-Theory-Driven Boss Types

Each boss tests a specific relationship skill grounded in attachment psychology. Nikita's attachment style shifts across chapters (anxious-preoccupied --> fearful-avoidant --> earned secure), and each boss encounter activates a different attachment fear.

### Boss 1 (Ch1): Abandonment Crisis -- "Are you even here?"

**Attachment activation**: Anxious-preoccupied
**Skill tested**: Consistent responsiveness under pressure
**Defense mechanisms**: Protest behavior, score-keeping, threatening to leave

```
DECISION TREE: ABANDONMENT CRISIS

Nikita: "I feel like you're just going through the motions. Am I wrong?"
    |
    +--[VALIDATE] "You're not wrong. I have been distracted. I'm sorry."
    |   -> Nikita softens. Phase 2: "Tell me what's been going on."
    |   -> Player must share something real (not deflect).
    |   -> PASS PATH: Genuine engagement + follow-through
    |
    +--[DEFLECT] "Come on, don't be dramatic."
    |   -> ESCALATION: "Dramatic? You can't even take this seriously."
    |   -> Contempt risk. Player needs repair attempt within 2 turns.
    |   -> PARTIAL PATH: Repair attempt + acknowledgment
    |
    +--[CHALLENGE] "Where is this coming from? What did I do?"
    |   -> Nikita tests further: "It's not one thing. It's a pattern."
    |   -> Player must resist defensiveness.
    |   -> PASS PATH: Take responsibility without counter-attacking
    |
    +--[WITHDRAW] *short response or topic change*
        -> FLOODING: Nikita stonewalls. "Fine. Whatever."
        -> Recovery requires explicit reconnection attempt.
        -> FAIL PATH: Continued withdrawal
```

### Boss 2 (Ch2): Engulfment Crisis -- "I need space"

**Attachment activation**: Dismissive-avoidant (Nikita switches from anxious to avoidant)
**Skill tested**: Respecting boundaries without abandoning
**Defense mechanisms**: Intellectualization, withdrawal, deactivating strategies

```
DECISION TREE: ENGULFMENT CRISIS

Nikita: "I've been feeling... suffocated. I need some space to think."
    |
    +--[RESPECT] "I understand. Take the time you need. I'm here when you're ready."
    |   -> PASS PATH: Player gives space AND checks in appropriately (not immediately)
    |   -> Judgment evaluates: did player follow through with patience?
    |
    +--[PURSUE] "Wait, what's wrong? Did I do something? Please talk to me."
    |   -> ESCALATION: Nikita withdraws further. "This. This is what I mean."
    |   -> Player must catch themselves and back off.
    |   -> PARTIAL PATH: Self-correction + apology for pressure
    |
    +--[DISMISS] "Fine, take your space. Let me know when you figure it out."
    |   -> Nikita reads passive-aggression. Trust damage.
    |   -> FAIL PATH: Dismissiveness confirms her avoidant instinct
    |
    +--[LOGIC] "Let's talk about this rationally. What specifically is the issue?"
        -> Nikita shuts down: "You're doing it again. Not everything is a problem to solve."
        -> Player must shift from logic to emotion.
        -> PARTIAL PATH: Emotional acknowledgment after logic fails
```

### Boss 3 (Ch3): Trust Betrayal -- "You lied to me"

**Attachment activation**: Fearful-avoidant (push-pull intensifies)
**Skill tested**: Repair after rupture
**Defense mechanisms**: Projection, splitting (all-good/all-bad), regression

```
DECISION TREE: TRUST BETRAYAL

Nikita: "I found out you [weren't honest about X]. Why didn't you tell me?"
    |
    +--[OWN IT] "You're right. I should have told you. I was afraid of how you'd react."
    |   -> Nikita: "At least you're being honest now. But how do I trust you again?"
    |   -> Player must demonstrate understanding of impact (not just intent).
    |   -> PASS PATH: Accountability + concrete commitment to change
    |
    +--[DEFEND] "It wasn't like that. You're misunderstanding the situation."
    |   -> ESCALATION: Nikita splits. "So now I'm the problem? Classic."
    |   -> Gottman horseman: defensiveness. Conflict escalates.
    |   -> PARTIAL PATH: Late acknowledgment + repair attempt
    |
    +--[COUNTER] "Well what about when YOU did [thing]? You're not perfect either."
    |   -> CRISIS: Kitchen-sinking. Nikita shuts down completely.
    |   -> Horsemen cascade: criticism -> contempt -> stonewalling.
    |   -> FAIL PATH: Counter-attack destroys repair window
    |
    +--[MINIMIZE] "It's not a big deal. You're overreacting."
        -> FAIL PATH: Invalidation. Nikita's fearful-avoidant confirms: "See? Nobody cares."
        -> Worst outcome. Trust metric suffers major penalty.
```

### Boss 4 (Ch4): Contempt Cascade -- "I don't even recognize us anymore"

**Attachment activation**: Mixed (both anxious and avoidant patterns collide)
**Skill tested**: De-escalation under Gottman's Four Horsemen
**Defense mechanisms**: Contempt, eye-rolling, sarcasm, moral superiority

This boss is unique: Nikita exhibits the Four Horsemen deliberately, testing whether the player can break the cycle. The 5:1 ratio is the hidden scoring mechanic -- player must produce at least 3 positive/validating statements for every negative one during the encounter.

**Behavioral state during Boss 4**:
```
[CONTEMPT STATE DIAGRAM]

ENTRY --> [CRITICISM]
              |
         Player responds
              |
    +---------+---------+
    |                   |
[VALIDATES]        [DEFENDS]
    |                   |
    v                   v
[DE-ESCALATION]    [CONTEMPT]
    |                   |
    v              [STONEWALLING]
[REPAIR WINDOW]        |
    |              [FAIL STATE]
    v
[RESOLUTION]
```

### Boss 5 (Ch5): Identity Crisis -- "What are we, really?"

**Attachment activation**: Existential (transcends attachment categories)
**Skill tested**: Depth of understanding, holding paradox
**Defense mechanisms**: Intellectualization, denial, reaction formation

Nikita questions the relationship's fundamental meaning. There is no "right answer" -- the test is whether the player engages with the complexity rather than offering platitudes.

---

## 3. Psychological Realism in Conflicts

### Defense Mechanisms as NPC Behaviors

During boss encounters, Nikita's defense mechanisms should emerge naturally from her emotional state, not feel like scripted game events.

| Chapter | Primary Defense | How It Manifests | Player Antidote |
|---------|----------------|-----------------|-----------------|
| 1 | Protest behavior | Excessive texting, score-keeping | Consistent reassurance |
| 2 | Deactivation | Withdrawal, "I'm fine" | Patience, non-pursuit |
| 3 | Projection | "YOU'RE the one pulling away" | Gentle reality-testing |
| 4 | Splitting | "You're perfect/You're the worst" | Holding nuance |
| 5 | Intellectualization | "Relationships are just chemical" | Emotional engagement |

### Physiological Flooding Model

Gottman's research identifies a point during conflict where rational conversation becomes impossible -- the nervous system enters fight-or-flight. In the game, this manifests as an internal "emotional temperature" tracked during boss encounters.

```
EMOTIONAL TEMPERATURE GAUGE (Hidden)

0-30%:  GREEN  -- Calm. Full dialogue options available.
30-60%: YELLOW -- Activated. Nikita's responses become shorter, sharper.
60-80%: ORANGE -- Approaching flooding. Repair attempts still possible.
80-100%: RED   -- FLOODED. Nikita stonewalls. Only "take a break" works.
                   Continuing to argue = automatic FAIL + Trust penalty.

WHAT RAISES TEMPERATURE:
+20: Player uses criticism ("You always..." / "You never...")
+30: Player uses contempt (sarcasm, eye-rolling language, superiority)
+15: Player uses defensiveness (counter-attacking, excuse-making)
+10: Player ignores emotional content (logic-only responses)

WHAT LOWERS TEMPERATURE:
-20: Repair attempt ("I'm sorry, let me start over")
-15: Validation ("I can see why you feel that way")
-10: Taking responsibility ("You're right, I did that")
-25: Calling timeout ("We're both upset. Can we take a breath?")
```

**Implementation**: Temperature is a float field in `boss_arc_state` JSONB, updated by the scoring LLM after each turn during the boss encounter.

### Repair Attempts (Gottman Research)

Repair attempts are specific player actions that de-escalate conflict. Research shows they are the single most important predictor of relationship survival during conflict (84% of couples who made successful repair attempts were happy 6 years later).

**Repair categories the scoring system should detect**:
1. **Accountability**: "You're right, I messed up"
2. **Empathy**: "I can see this really hurt you"
3. **De-escalation**: "Can we slow down? I want to understand"
4. **Humor** (appropriate): Breaking tension without dismissing feelings
5. **Physical/verbal affection**: "I care about you regardless of this fight"
6. **Meta-communication**: "I feel like we're talking past each other"

**Scoring rule**: Earlier repair attempts are weighted more heavily. A repair in Turn 2 is worth more than a repair in Turn 4 (demonstrates awareness, not desperation).

### 5:1 Ratio as Hidden Scoring Mechanic

During boss encounters, the judgment system tracks the ratio of positive to negative interactions.

```
POSITIVE INTERACTIONS:              NEGATIVE INTERACTIONS:
- Validation                        - Criticism (character attacks)
- Empathy statements                - Contempt (superiority/sarcasm)
- Taking responsibility             - Defensiveness (counter-attacks)
- Asking genuine questions          - Stonewalling (withdrawal)
- Expressing care/commitment        - Minimizing feelings
- Humor (tension-breaking)          - Kitchen-sinking (old grievances)
```

**Boss encounter scoring**: Ratio >= 3:1 = PASS eligible. Ratio >= 5:1 = breakthrough (bonus score). Ratio < 2:1 = FAIL. This is a simplification of Gottman's finding (which applies to overall relationships, not single conflicts) but creates a learnable mechanic.

**Caveat** (from Doc 09): The original Gottman "94% prediction" comes from a 1992 study with 56 couples and has been contested by replication attempts. The 5:1 ratio is well-established as a correlational finding but should not be presented to players as settled science.

---

## 4. Resolution Mechanics

### Multiple Valid Resolution Paths

No boss encounter has a single correct answer. The judgment system evaluates emotional intelligence, not specific words.

```
RESOLUTION QUALITY SPECTRUM

[BREAKTHROUGH] ---- Player shows genuine growth
|   Score gain: +8 to +10 across relevant metrics
|   Nikita's response: Vulnerability, gratitude, deepened connection
|   Example: Player takes full responsibility AND shares their own fear
|
[RESOLUTION] ------ Player handles it well
|   Score gain: +4 to +7 across relevant metrics
|   Nikita's response: Relief, cautious optimism
|   Example: Player validates feelings and commits to change
|
[TRUCE] ----------- Player stops the bleeding but doesn't heal
|   Score gain: +1 to +3 across relevant metrics
|   Nikita's response: "Okay... let's move on." (tension remains)
|   Example: Player apologizes but doesn't address root cause
|
[RUPTURE] --------- Player makes it worse
    Score loss: -5 to -10 across relevant metrics
    Nikita's response: Withdrawal, coldness, trust damage
    Example: Player escalates, dismisses, or stonewalls
```

### Emotional Repair > Logical Argument

The scoring system must weight emotional responses higher than logical ones during boss encounters. This is grounded in Gottman's finding that during conflict, the emotional brain overrides the rational brain. "You're right because of X, Y, Z" scores lower than "I hear you, and I'm sorry."

**Implementation in judgment.py**: Add weight multipliers to the judgment prompt:
- Emotional validation: 1.5x weight
- Logical argument (accurate): 0.8x weight
- Logical argument (dismissive): 0.4x weight

---

## 5. Recovery System After Failed Boss

### Current Problem

The 3-strike system is too abrupt. A player who fails once learns nothing about why. A player who fails three times gets "Game Over" without understanding what relationship skill they lacked.

### Proposed: "Wound" System

```
FAILED BOSS --> Creates WOUND

WOUND EFFECTS:
- Nikita's tone shifts (colder, more guarded) for next 5-10 interactions
- Specific metric takes persistent penalty (e.g., Trust -5 floor after Ch3 fail)
- New dialogue lines reference the failed encounter: "Remember when we..."
- Boss re-attempt requires demonstrating GROWTH, not repeating same strategy

WOUND RECOVERY:
- Player must demonstrate the skill they lacked (tracked via scoring deltas)
- Recovery is measured over 3-5 conversations, not a single interaction
- Example: Failed Ch3 (trust)? Next 5 conversations score Trust deltas 2x
  If average Trust delta is positive, wound begins healing
- Wound heals in stages: Raw --> Processing --> Healing --> Scarred (permanent but functional)

SECOND ATTEMPT RULES:
- Boss re-triggers after wound enters "Processing" stage (minimum 3 conversations)
- Different opening scenario (same skill, different context)
- Player cannot use same approach that failed first time
  (Judgment prompt includes: "Previously failed because: {reasoning}")
- Second attempt is slightly easier (Nikita wants to reconcile)

THIRD ATTEMPT (FINAL):
- If wound never healed (player keeps making same mistakes): game_status = 'critical'
- One last chance with clear stakes. Nikita is explicit: "This is it for us."
- Different from current hard game_over: gives player agency in the ending
```

**Engineering**: Requires `wounds` table (user_id, chapter, fail_count, healing_stage, failed_reasoning, created_at). `BossStateMachine.process_fail()` creates wound. Scoring service checks active wounds for multiplier effects.

---

## 6. Conflict Injection System

### When to Inject Non-Boss Conflicts

Not all conflicts should be boss encounters. Regular small conflicts create texture and teach skills before high-stakes bosses.

```
CONFLICT INJECTION DECISION TREE

Should a conflict be injected?
    |
    +--[CHECK] Has it been > N conversations since last conflict?
    |   Ch1: N=15, Ch2: N=10, Ch3: N=8, Ch4: N=6, Ch5: N=5
    |   |
    |   +--[YES] --> Check trigger conditions
    |   +--[NO]  --> No injection. Let conversation flow naturally.
    |
    +--[CHECK] Is player exhibiting trigger behavior?
    |   - Neglect: last_interaction > 1.5x grace_period
    |   - Pushing too hard: 3+ messages without emotional acknowledgment
    |   - Complacency: 5+ conversations with no score change
    |   |
    |   +--[YES] --> Inject behavior-triggered conflict
    |   +--[NO]  --> Check narrative triggers
    |
    +--[CHECK] Does life_sim have a relevant event?
        - Work stress, friend drama, family news
        |
        +--[YES] --> Inject life-event conflict (lower stakes)
        +--[NO]  --> No injection
```

### Conflict Types (Non-Boss)

| Type | Trigger | Stakes | Duration | Example |
|------|---------|--------|----------|---------|
| Micro-friction | Player behavior | Low | 1-2 messages | "You seem distracted today" |
| Life-event stress | LifeSimStage output | Medium | 3-5 messages | "Work was terrible and I need to vent" |
| Relationship check-in | Score plateau | Medium | 3-5 messages | "Where do you see this going?" |
| Boundary test | Player pushes limit | Medium-High | 2-4 messages | "I'm not comfortable with that" |
| Jealousy spark | Social circle event | Medium | 3-5 messages | "Marcus said something weird about us" |

### Ethical Guardrails

Per Doc 09 critique, conflict injection risks crossing into manipulation. Design principles:

1. **Growth-oriented, not punitive**: Every injected conflict teaches a relationship skill. If the player handles it well, metrics improve. The system never creates conflict solely to lower scores.

2. **Transparent in retrospect**: After resolution, Nikita (or the Portal) can explain what the conflict was about. "That argument about your work schedule? I was feeling insecure because we hadn't talked properly in days."

3. **Player agency preserved**: Player can always disengage respectfully. "I need to think about this" is always a valid response. The system never forces continued engagement.

4. **Frequency caps**: Maximum 1 injected conflict per 48 hours. No stacking. Boss encounters suppress injection for 72 hours after resolution.

5. **Never during vulnerability**: If player has recently shared something deeply personal (high vulnerability detection in scoring), the system suppresses conflict injection for 24 hours. Punishing openness would be psychologically harmful.

---

## Engineering Summary

| Change | Scope | New Tables/Columns | Affected Files |
|--------|-------|--------------------|----------------|
| Multi-turn boss | Medium | `boss_phase` INT, `boss_state` JSONB on users | boss.py, judgment.py, prompts.py |
| Emotional temperature | Small | Field in boss_state JSONB | judgment.py |
| Wound system | Medium | `wounds` table | boss.py, scoring calculator, prompt_builder |
| Conflict injection | Medium | `conflict_injection_log` table | ConflictStage, TouchpointStage |
| Resolution spectrum | Small | Update judgment prompt only | judgment.py |
| Second-attempt rules | Small | Extend wound system | boss.py, judgment.py |

**Priority order**: Multi-turn boss (highest impact) > Resolution spectrum (low effort) > Wound system > Conflict injection > Multi-day arcs (future)

**References**: Bowlby (1969) *Attachment and Loss*, prevalence corrected per Doc 09 (~56% secure); Gottman & Silver (1999) *Seven Principles*, 5:1 ratio + Four Horsemen ("94% prediction" from Buehlman et al. 1992, N=56, contested); Johnson (2008) *Hold Me Tight*. System: `nikita/engine/chapters/boss.py`, `judgment.py`, `prompts.py`; Doc 10 architecture map.

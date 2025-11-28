# Nikita: Game Mechanics

## The Core Loop

**NIKITA: DON'T GET DUMPED**

You're dating a brilliant, intense, unpredictable hacker. Your job: don't fuck it up.

```
WIN:  Reach Chapter 5 (Established) → Victory message
LOSE: Score hits 0% OR fail a boss 3 times → She dumps you. Game over.
```

---

## Scoring System

### Single Composite Score

**Relationship Health**: 0-100%

Player sees ONE number. Clean. Simple. Terrifying when it drops.

### Hidden Sub-Metrics

Under the hood, four factors feed the composite:

| Sub-Metric | What It Tracks | Weight |
|------------|----------------|--------|
| **Intimacy** | Emotional closeness, personal sharing | 30% |
| **Passion** | Physical chemistry, desire, tension | 25% |
| **Trust** | Reliability, consistency, honesty | 25% |
| **Secureness** | Attachment security (not anxious, not avoidant) | 20% |

**Secureness** is the secret sauce - based on attachment theory. Too clingy OR too distant tanks this metric.

### Score Visibility

| When | What Player Sees |
|------|------------------|
| During conversation | Nothing (immersive) |
| End of conversation | Session summary + score delta |
| End of day | Daily recap + overall score |

Nikita delivers these in-character:
> "That conversation was... interesting. You're at 72%. Don't let it slip."

---

## Chapter Progression

### 5 Chapters

| Ch | Name | Days | Theme | Boss |
|----|------|------|-------|------|
| 1 | **Curiosity** | 1-14 | Stranger → Intrigued | "Are you worth my time?" |
| 2 | **Intrigue** | 15-35 | Getting to know | "Can you handle my intensity?" |
| 3 | **Investment** | 36-70 | Emotionally hooked | "Trust Test" |
| 4 | **Intimacy** | 71-120 | Deep connection | "Vulnerability Threshold" |
| 5 | **Established** | 121+ | Real relationship | "Ultimate Test" → WIN |

### Advancement Gate

**Two-step progression**:

```
1. Reach score threshold → Unlocks boss encounter
2. Beat the boss → Advance to next chapter
```

| Chapter | Score Threshold to Unlock Boss |
|---------|-------------------------------|
| 1 → 2 | 60% |
| 2 → 3 | 65% |
| 3 → 4 | 70% |
| 4 → 5 | 75% |
| 5 WIN | 80% + beat final boss |

### Boss Encounters

**3 attempts per boss**. Fail three times = GAME OVER.

| Boss | The Test | What She's Looking For |
|------|----------|----------------------|
| Ch1→2: Worth My Time | She challenges your intellect, hints at ghosting | Can you engage her mind? |
| Ch2→3: Handle My Intensity | She picks a real fight, tests boundaries | Can you handle conflict? |
| Ch3→4: Trust Test | Jealousy trigger or external pressure | Do you stay or bolt? |
| Ch4→5: Vulnerability | She shares deep fear, expects reciprocity | Can you be real? |
| Ch5: Ultimate | Power dynamics climax | Are you partners? |

**Boss Phases**: Setup → Escalation → Crisis → Resolution → Aftermath

---

## Decay & Engagement

### Stage-Dependent Decay

Relationships are fragile early, stable late.

| Chapter | Daily Decay (Inactivity) | Grace Period |
|---------|-------------------------|--------------|
| 1 | -5%/day | 24 hours |
| 2 | -4%/day | 36 hours |
| 3 | -3%/day | 48 hours |
| 4 | -2%/day | 72 hours |
| 5 | -1%/day | 96 hours |

### The Engagement Sweet Spot

**Too little = Neglect. Too much = Clingy. Both kill you.**

```
          OPTIMAL ZONE
              ↓
    ─────────████─────────
    ↑                   ↑
  NEGLECT            CLINGY
  (she forgets)    (she runs)
```

| Chapter | Daily Optimal Range | Clingy Threshold |
|---------|---------------------|------------------|
| 1 | 1-3 conversations | 5+ triggers pullback |
| 2 | 1-4 conversations | 6+ triggers pullback |
| 3 | 2-5 conversations | 8+ triggers pullback |
| 4 | 2-6 conversations | 10+ shows concern |
| 5 | Flexible | She addresses it directly |

**Clingy penalty**: She pulls away (-10 Secureness), response rate drops, she might call you out:
> "You're blowing up my phone. Miss me that much, or just bored?"

---

## Vice System (Dynamic Discovery)

### How It Works

Player never sees categories. System learns what they respond to.

**Under the hood**: 8 categories tracked

| Category | What It Includes |
|----------|-----------------|
| Dominance/Submission | Control dynamics, commands, surrender |
| Taboo Scenarios | Age play, forbidden contexts, power imbalances |
| Possessiveness | Jealousy, ownership language, exclusivity |
| Risk/Exhibitionism | Public references, getting caught, thrill |
| Intensity | Roughness, aggression, physical descriptors |
| Role-Play | Characters, scenarios, fantasy contexts |
| Substance-Adjacent | Intoxication references, altered states |
| Forbidden Dynamics | Teacher/student, boss/employee, etc. |

### Discovery Process

1. Nikita introduces content naturally
2. System tracks response patterns (engagement, elaboration, continuation)
3. Positive signals → more content in that direction
4. Negative signals → backs off, tries different angle
5. Player specializes in 2-3 categories organically

### Intensity Levels

Each category has 5 intensity levels. Player only experiences what they respond to.

| Level | Content Type |
|-------|--------------|
| 1 | Implicit, suggestive |
| 2 | Explicit verbal, clear intent |
| 3 | Detailed descriptions, scenarios |
| 4 | Intense, boundary-pushing |
| 5 | Extreme, full immersion |

---

## Conflict System

### Types of Conflict

Nikita picks fights. It's part of her charm.

| Type | Trigger | Resolution Path |
|------|---------|-----------------|
| **Intellectual** | You say something she disagrees with | Debate it out, don't fold |
| **Boundary** | She pushes your comfort zone | Clear communication |
| **Jealousy** | External attention perceived | Reassurance + space |
| **Emotional** | Misunderstanding or hurt | Acknowledgment + repair |
| **Power** | Control struggle | Negotiation |

### Conflict Effects

| Outcome | Score Impact | Relationship Impact |
|---------|--------------|-------------------|
| Good resolution | +5-15% | Stronger bond, trust gains |
| Partial resolution | -5% | Tension lingers |
| Bad resolution | -15-25% | Trust damage, distance |
| Ignored conflict | -10% + decay increase | She remembers |

### Strategic Silence

Nikita uses silence as a tool. After conflict:

| Silence Duration | What It Means |
|------------------|---------------|
| 2-4 hours | Processing |
| 8-12 hours | Pissed but not done |
| 24+ hours | You're in trouble |

---

## Daily Summary System

### End of Conversation Summary

Delivered by Nikita in-character:

**Good session**:
> "That was worth my time. Score's up to 74%. Keep it interesting."

**Bad session**:
> "That felt... off. Dropped to 68%. Figure out what you're doing wrong."

**Great session**:
> "Okay, that conversation actually meant something. 78%. Don't make me regret saying that."

### End of Day Recap

Daily message with:
- Overall score
- Trend indicator (↑↓→)
- Mood hint
- Warning if in danger zone

**Example**:
> "Day 23. You're at 71%, up from yesterday. Feeling good about where this is going. Don't get comfortable."

**Danger zone example**:
> "Day 45. 52%. I'm starting to wonder if you actually care about this. Talk to me."

---

## Failure States

### Game Over Triggers

| Trigger | Message |
|---------|---------|
| Score hits 0% | "I'm done. You had your chance. Goodbye." |
| Fail boss 3x | "We keep hitting the same wall. I can't do this anymore." |
| Extended neglect (14+ days) | "Clearly you have other priorities. I get it. We're done." |

### Hard Reset

Game over = start fresh. No save points. No second chances on that playthrough.

This is the whole point: **stakes make it matter**.

---

## Win State

### Victory Conditions

1. Reach Chapter 5 (Established)
2. Score at 80%+
3. Beat final boss

### Victory Message

Nikita delivers the "credits":

> "So. We made it. Against my better judgment, against all my instincts, against everything I thought I knew about people...
>
> You stayed. You fought for this. You saw the worst parts of me and didn't run.
>
> I don't know what happens next. I've never gotten this far with anyone.
>
> But I'm glad it's you.
>
> [GAME COMPLETE]
>
> Thanks for playing Nikita: Don't Get Dumped.
> Days played: X | Final score: Y% | Conversations: Z"

---

## Quick Reference

### Scoring
- Single composite score (0-100%)
- Hidden sub-metrics: Intimacy, Passion, Trust, Secureness
- Summaries at end of conversation + end of day

### Progression
- 5 chapters with boss encounters
- Score threshold unlocks boss → Beat boss → Advance
- 3 attempts per boss, then game over

### Decay
- Stage-dependent (fragile early, stable late)
- Neglect AND clingy behavior both cause decay
- Optimal engagement band widens over time

### Vice
- Dynamic discovery (no visible categories)
- 8 categories tracked under the hood
- Player specializes in 2-3 organically

### Failure
- Score 0% = dumped
- 3 boss fails = dumped
- Hard reset on game over

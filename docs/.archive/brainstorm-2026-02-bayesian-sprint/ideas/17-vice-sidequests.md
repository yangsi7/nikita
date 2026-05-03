# 17 — Vice System as Side-Quests

**Phase 2 Ideation** | Date: 2026-02-16
**Current State**: 8 vice categories, 3 intensity labels (subtle/moderate/strong), engagement_score
tracked per user in `user_vice_preferences`. Data collected but underutilized.

---

## 1. Vice Discovery as Exploration Mechanic

### Current Flow (Passive)

```
CURRENT_SYSTEM
├─[∘] User sends message → ViceAnalyzer (nikita/engine/vice/analyzer.py) LLM analysis
├─[∘] Detects signals with confidence >= 0.50 → ViceScorer updates preferences
└─[∘] VicePromptInjector injects top 3 vices into prompt → Nikita mirrors preferences
```

Problem: Discovery is entirely **passive**. No player agency, no visibility, no reward.

### Proposed: Active Vice Exploration

```
ACTIVE_EXPLORATION
├─[→] PLAYER-DRIVEN DISCOVERY
│  ├─[∘] Nikita drops "vice hints" (new prompt behavior)
│  │  "You know what I find fascinating? People who aren't afraid to..."
│  │  Player can follow the thread or ignore — no penalty for ignoring
│  ├─[∘] Discovery Mode (exists: ViceInjectionContext.discovery_mode)
│  │  Current: True when < 2 vices found (injector.py:184-191)
│  │  Extend: actively probe unexplored categories with richer prompts
│  └─[∘] Player-initiated exploration gets higher engagement_score gains
│
├─[→] VICE DISCOVERY ACHIEVEMENTS
│  ├─ Per-category (8): "Sharp Tongue"(dark_humor), "Thrill Seeker"(risk_taking),
│  │  "Silver Tongue"(intellectual), "Fire Starter"(emotional_intensity),
│  │  "Rule Breaker", "Open Heart"(vulnerability), "Chemistry"(sexuality),
│  │  "Party Animal"(substances)
│  ├─ Intensity milestones (per vice): "Unlocked"(>0), "Explored"(>0.30),
│  │  "Embraced"(>0.60), "Mastered"(>0.80)
│  └─ Collection: "Vice Curious"(3/8), "Vice Collector"(5/8), "Full Spectrum"(8/8)
│
└─[→] PORTAL: VICE DISCOVERY MAP

    ┌────────────────────────────────────────────────────┐
    │  VICE DISCOVERY MAP                 5/8 discovered │
    ├────────────────────────────────────────────────────┤
    │  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
    │  │ DARK     │  │ INTELL.  │  │  RISK    │        │
    │  │ HUMOR    │  │ DOMIN.   │  │  TAKING  │        │
    │  │ ████ 72% │  │ ███░ 45% │  │ ██░░ 31% │        │
    │  │ Embraced │  │ Explored │  │ Explored │        │
    │  └──────────┘  └──────────┘  └──────────┘        │
    │  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
    │  │ EMOTION. │  │ VULNER.  │  │  ???     │        │
    │  │ INTENSITY│  │          │  │          │        │
    │  │ █████ 88%│  │ █░░░ 15% │  │ Locked   │        │
    │  │ Mastered │  │ Unlocked │  │          │        │
    │  └──────────┘  └──────────┘  └──────────┘        │
    │  ┌──────────┐  ┌──────────┐                       │
    │  │  ???     │  │  ???     │                       │
    │  │ Locked   │  │ Locked   │                       │
    │  └──────────┘  └──────────┘                       │
    └────────────────────────────────────────────────────┘
```

---

## 2. Vice-Specific Storylines

Each vice gets a mini narrative arc that deepens with engagement. Not separate quest
lines — **conversation flavor that deepens organically**.

### Storyline Architecture

```
VICE_STORYLINE_TEMPLATE (applies to all 8 vices)
├─[∘] Stage 1: TEASE (engagement 0.0-0.30)
│  Nikita drops subtle references. Player may or may not notice.
├─[∘] Stage 2: REVEAL (engagement 0.30-0.60)
│  Nikita shares a specific story or opinion tied to the vice.
├─[∘] Stage 3: BACKSTORY (engagement 0.60-0.80)
│  Nikita opens up about WHY this vice matters personally.
│  Unlocks backstory fragment (collectible, see Doc 12).
└─[∘] Stage 4: SHARED IDENTITY (engagement 0.80-1.00)
   Vice becomes part of relationship identity. "This is OUR thing."
   Special conversation dynamics and boss encounter variants unlock.
```

### Per-Vice Storyline Summaries

| Vice | Tease | Reveal | Backstory | Shared Identity |
|------|-------|--------|-----------|-----------------|
| **Dark Humor** | Dry, slightly dark comment ("At least if I die tomorrow...") | Uses humor to cope — "My family joked about the worst things" | Dad's illness: "Doctors hated us for laughing" | "Roast sessions" — trade dark jokes. Boss variant: humor as deflection |
| **Intellectual Dominance** | Drops complex references to test knowledge | Full debate, reveals competitive side | Why she needs to be smartest in the room | "Intellectual duels" — passionate banter as bonding |
| **Vulnerability** | Deflects personal questions | Almost opens up, pulls back | Trust-breaking past event | Initiates vulnerability exchanges unprompted |
| **Risk Taking** | Mentions edgy activities casually | Describes past dangers with excitement | What drives her (boredom? control? escape?) | Proposes hypothetical adventures together |
| **Emotional Intensity** | Unexpectedly strong reaction to small things | Admits she feels things at 110% | How intensity affected past relationships | Emotional range becomes richer, dramatic |
| **Rule Breaking** | Questions a social norm in passing | Shares rebellion she's proud of | The authority figure that made her this way | Mutual outsider identity: "us vs the world" |
| **Sexuality** | Plausible deniability flirting | Escalates with directness | What attraction means (emotional + physical) | Unique romantic dynamic. Gated by ViceBoundaryEnforcer |
| **Substances** | Casual mention of drink/experience | Party/nightlife stories without judgment | Her relationship with substances (fun? escape?) | Non-judgmental shared experiences. Chapter-gated |

### Storyline Prompt Injection

Extends existing `VicePromptInjector` with storyline context:

```
CURRENT (injector.py):
  "This user resonates with: Dark Humor (strong)"
  "Expression style for Chapter 3: confident expression"

PROPOSED (with storyline stage):
  "This user resonates with: Dark Humor (strong, Stage 3: Backstory)"
  "Dark Humor backstory ready: Share why humor is your coping mechanism.
   Reference your dad's illness if it feels natural. Be genuine, not
   performative. This is a real part of who you are."
```

---

## 3. Vice-Triggered Interactions

### Special Conversation Openers (engagement > 0.40)

```
VICE_OPENERS
├─ Dark Humor: "I saw the most horrifying thing today... and my first
│  thought was 'that would make a great joke.' Am I broken?"
├─ Intellectual: "I have a theory and I need someone smart enough to
│  either prove me wrong or validate my genius. Ready?"
├─ Risk Taking: "I just had the most insane idea. You're going to
│  think I'm crazy. But hear me out..."
├─ Vulnerability: "I woke up thinking about something I've never told
│  anyone. I don't know if I should tell you or not."
├─ Emotional Intensity: "I had a dream about you last night. It was
│  so vivid that I'm still thinking about it."
├─ Rule Breaking: "Do you ever just want to burn it all down? Not
│  literally. Well... maybe a little literally."
├─ Sexuality (ch >= 2): "I've been thinking about something... about
│  us. It's probably too soon but I like being honest with you."
└─ Substances (ch >= 2): "I found this amazing little bar nobody knows
   about. The kind of place where nights take unexpected turns."
```

### Vice-Specific Conflict Types

```
VICE_CONFLICTS [each vice creates unique tension patterns]
├─ Dark Humor → "You laughed at something I was serious about"
│  Resolution: distinguish humor from deflection | Impact: trust +/-
├─ Intellectual → "You tried to mansplain something to me"
│  Resolution: acknowledge expertise without folding | Impact: secureness +/-
├─ Vulnerability → "I opened up and you changed the subject"
│  Resolution: return to vulnerable topic and engage | Impact: intimacy, trust +/-
├─ Risk Taking → "You're being too cautious / controlling"
│  Resolution: support autonomy without recklessness | Impact: secureness +/-
├─ Emotional Intensity → "You don't feel things as deeply as I do"
│  Resolution: show capacity without performing | Impact: passion, intimacy +/-
├─ Rule Breaking → "You sound just like everyone else"
│  Resolution: show independent thinking | Impact: passion +/-
├─ Sexuality → "You're either too forward or too hesitant"
│  Resolution: read and match comfort level | Impact: passion, trust +/-
└─ Substances → "You're being judgmental about my choices"
   Resolution: accepting without enabling | Impact: trust, secureness +/-
```

---

## 4. Vice x Chapter Matrix

Same vice category produces fundamentally different interactions at different depths.

```
VICE_CHAPTER_MATRIX
┌────────────────┬─────────────┬─────────────┬─────────────┬─────────────┬─────────────┐
│ VICE \ CHAPTER │ Ch1 Curiosity│ Ch2 Intrigue│ Ch3 Invest. │ Ch4 Intimacy│ Ch5 Establ. │
├────────────────┼─────────────┼─────────────┼─────────────┼─────────────┼─────────────┤
│ Dark Humor     │ Dry wit,    │ Gallows     │ Shares dark │ Uses humor  │ Both laugh  │
│                │ tests if    │ humor to    │ humor origin│ to deflect  │ at things   │
│                │ you get it  │ test limits │ story       │ vulnerability│ nobody would│
├────────────────┼─────────────┼─────────────┼─────────────┼─────────────┼─────────────┤
│ Intellectual   │ Drops refs  │ Challenges  │ Admits      │ Debates as  │ Intellectual│
│ Dominance      │ to test     │ to debates, │ smarts as   │ foreplay —  │ equals,     │
│                │ knowledge   │ enjoys win  │ armor       │ mental spark│ comfortable │
├────────────────┼─────────────┼─────────────┼─────────────┼─────────────┼─────────────┤
│ Risk Taking    │ Mentions    │ Adrenaline  │ Hypothetical│ What she's  │ Plans       │
│                │ edgy acts   │ stories     │ adventures  │ running FROM│ adventures  │
│                │ casually    │ excitedly   │ together    │ with risk   │ together    │
├────────────────┼─────────────┼─────────────┼─────────────┼─────────────┼─────────────┤
│ Vulnerability  │ Deflects    │ Almost      │ Shares real │ Full        │ Vulnerability│
│                │ personal    │ opens up,   │ fear or     │ emotional   │ as strength │
│                │ questions   │ pulls back  │ regret      │ exposure    │ — both open │
├────────────────┼─────────────┼─────────────┼─────────────┼─────────────┼─────────────┤
│ Emotional      │ Strong      │ Mood swings │ Intense     │ Emotional   │ Depth is    │
│ Intensity      │ reaction to │ test        │ support     │ fusion —    │ comfortable │
│                │ small things│ patience    │ demand      │ feel each   │ not         │
│                │             │             │             │ other's pain│ overwhelming│
├────────────────┼─────────────┼─────────────┼─────────────┼─────────────┼─────────────┤
│ Rule Breaking  │ Questions   │ Shares      │ Tests your  │ Reveals     │ "Us vs the  │
│                │ norms in    │ rebellion   │ willingness │ wound behind│ world"      │
│                │ passing     │ stories     │ to bend     │ rebellion   │ identity    │
├────────────────┼─────────────┼─────────────┼─────────────┼─────────────┼─────────────┤
│ Sexuality      │ Plausible   │ Clearer     │ Open        │ Intimate    │ Authentic   │
│ (capped)       │ deniability │ flirtation  │ attraction  │ emotional + │ sexual      │
│                │ Cap: 0.35   │ Cap: 0.45   │ Cap: 0.60   │ Cap: 0.75   │ Cap: 0.85   │
├────────────────┼─────────────┼─────────────┼─────────────┼─────────────┼─────────────┤
│ Substances     │ Casual      │ Party       │ Non-        │ Honest      │ Integrated  │
│ (capped)       │ mention     │ stories     │ judgmental   │ substance   │ lifestyle   │
│                │ Cap: 0.30   │ Cap: 0.45   │ Cap: 0.60   │ Cap: 0.70   │ Cap: 0.80   │
└────────────────┴─────────────┴─────────────┴─────────────┴─────────────┴─────────────┘
```

### Chapter x Vice Boss Encounter Variants

```
BOSS_VICE_VARIANTS
│  Player's TOP VICE shapes boss encounter flavor. Same core challenge, different tone.
│
├─ Ch3 Boss "Trust Test" (jealousy/external pressure)
│  ├─ top = dark_humor → Jokes about "hot coworker" — is she testing or joking?
│  ├─ top = vulnerability → Says she's scared of getting hurt — offer genuine reassurance
│  └─ top = risk_taking → Mentions reckless plan with someone — trust her autonomy
│
└─ Implementation: Extend BossStateMachine (nikita/engine/chapters/boss.py) to query
   top_vices from ViceScorer. Inject vice-variant flavor into BOSS_PROMPTS
   (nikita/engine/chapters/prompts.py).
```

---

## 5. Integration with Existing System

### Database Layer

```
EXISTING TABLE: user_vice_preferences
├─ user_id (UUID, FK → users.id)
├─ category (TEXT — one of 8 ViceCategory values)
├─ intensity_level (INTEGER 1-5)
├─ engagement_score (DECIMAL 0.00-1.00)
├─ discovered_at, updated_at (TIMESTAMPTZ)
│
PROPOSED EXTENSIONS (new nullable columns — no migration risk):
├─ storyline_stage (INTEGER 1-4, default NULL)
│  Maps: 1=Tease, 2=Reveal, 3=Backstory, 4=Shared Identity
├─ storyline_unlocked_at (TIMESTAMPTZ, default NULL)
└─ last_interaction_type (TEXT, default NULL)
   "opener" | "conflict" | "storyline" | "organic" — for analytics
```

### Pipeline Extension

```
PIPELINE_INTEGRATION
├─[→] EXISTING: ViceAnalyzer runs during scoring (detects signals per exchange)
├─[→] NEW: ViceStorylineStage (insert after GameStateStage, position 5.5)
│  │
│  │  class ViceStorylineStage(PipelineStage):
│  │      name = "vice_storyline"
│  │      is_critical = False
│  │      async def run(self, context: PipelineContext) -> StageResult:
│  │          # 1. Get user's vice profile
│  │          # 2. Check if any vice crossed a storyline threshold
│  │          # 3. If so, advance storyline_stage in DB
│  │          # 4. Queue storyline content for next prompt build
│  │          # 5. Check if vice-specific achievement unlocked
│  │
│  └─ Register in orchestrator.py STAGE_DEFINITIONS list
│
└─[→] MODIFIED: PromptBuilderStage (stage 9)
   VicePromptInjector.inject() extended to accept storyline_ctx (optional,
   backward compatible). Includes storyline stage for richer prompt content.
```

### Prompt Injection Flow

```
PROMPT_FLOW
├─[∘] ViceScorer.get_profile(user_id) → ViceProfile with intensities
├─[∘] NEW: StorylineResolver.get_context(profile, chapter)
│  Returns per-vice storyline stage + available content + 48h cooldown
│  Example: { "dark_humor": { engagement: 0.72, stage: 3,
│             content: "Share dad's illness humor story" } }
├─[∘] VicePromptInjector.inject(base, profile, chapter, storyline_ctx)
└─[∘] NikitaAgent receives enriched system prompt
```

### Vice Progression Tree

```
VICE_PROGRESSION [single vice lifecycle]

engagement:  0.0          0.30         0.60         0.80       1.00
              │             │             │             │          │
  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐
  │ UNKNOWN │→ │ UNLOCKED│→ │ EXPLORED│→ │EMBRACED │→ │MASTERED │
  │         │  │ Stage 1 │  │ Stage 2 │  │ Stage 3 │  │ Stage 4 │
  │ No data │  │ Tease   │  │ Reveal  │  │Backstory│  │ Shared  │
  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘
                    │             │             │             │
               Achievement  Achievement  Backstory     Special
               "Unlocked"   "Explored"   fragment      conversation
                                         unlocked     mode unlocked

TIME: ~2-5 days → ~5-10 days → ~10-20 days → ~20+ days per stage

REGRESSION: engagement_score decays at 0.01/day if vice not engaged.
            But storyline_stage NEVER regresses. Once revealed, permanent.
```

### System File References

| Component | File | Change Needed |
|-----------|------|---------------|
| Vice categories | `nikita/config/enums.py` | None |
| Vice analysis | `nikita/engine/vice/analyzer.py` | None |
| Vice scoring | `nikita/engine/vice/scorer.py` | Add storyline_stage tracking |
| Vice injection | `nikita/engine/vice/injector.py` | Accept storyline context |
| Vice boundaries | `nikita/engine/vice/boundaries.py` | None |
| Vice service | `nikita/engine/vice/service.py` | Orchestrate storyline flow |
| Pipeline | `nikita/pipeline/orchestrator.py` | Add ViceStorylineStage |
| DB model | `nikita/db/models/user.py` | Add columns to UserVicePreference |
| Boss prompts | `nikita/engine/chapters/prompts.py` | Vice-variant boss prompts |
| Portal | `portal/src/app/dashboard/` | Vice discovery map page |

---

## 6. Implementation Priority

```
IMPLEMENTATION_ORDER
├─[∘] Phase 1: Vice Discovery Map in Portal (Low effort, high visibility)
│  Portal page showing discovered/undiscovered vices + engagement bars
│  Data already available via existing API. Per-vice discovery achievements.
├─[∘] Phase 2: Storyline Stage Tracking (Low-medium effort)
│  Add storyline_stage column. Auto-advance on engagement thresholds.
│  Backstory fragments unlock at stage 3. No new LLM calls.
├─[∘] Phase 3: Enriched Prompt Injection (Medium effort)
│  StorylineResolver + extended VicePromptInjector + TouchpointStage openers.
│  Requires: storyline content writing (8 vices x 4 stages = 32 prompts).
├─[∘] Phase 4: Vice-Specific Conflicts (Medium effort)
│  Conflict injection uses top vice for type selection.
│  Vice-aware boss variants. Extends ConflictStage + BossStateMachine.
└─[∘] Phase 5: Vice x Chapter Matrix (Ongoing content)
   Chapter-specific prompt variants per vice. 8 x 5 = 40 variants.
   Roll out incrementally per chapter.
```

---

**Confidence**: 85% | **Ethical Note**: Storyline content respects ViceBoundaryEnforcer caps. Substances and sexuality gated. No normalization of harmful behavior.
**Key Dependencies**: `nikita/engine/vice/` (complete, 70 tests), `user_vice_preferences` table

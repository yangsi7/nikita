# 12 — Progression & Achievement System

**Phase 2 Ideation** | Date: 2026-02-16
**User Decisions**: Decay = gentle nudge | Portal = full transparency | Streaks = evaluate options

---

## 1. Achievement System Design

### Achievement Taxonomy

```
ACHIEVEMENT_SYSTEM
├─[⊃] CONVERSATION ACHIEVEMENTS
│  ├─[∘] Depth
│  │  ├─ "Deep Dive" — 20+ exchanges in one session
│  │  ├─ "Philosopher" — 3 abstract topics in one session
│  │  └─ "Night Owl" — Conversation past midnight (user TZ)
│  ├─[∘] Humor
│  │  ├─ "Made Her Laugh" — Trigger genuine humor response (LLM-detected)
│  │  ├─ "Comedy Duo" — 5+ jokes exchanged in one session
│  │  └─ "Inside Joke" — Reference a previous funny moment successfully
│  ├─[∘] Vulnerability
│  │  ├─ "Open Book" — Share something personal (LLM-detected self-disclosure)
│  │  ├─ "Mutual Trust" — Both sides share vulnerability in same session
│  │  └─ "Raw Honesty" — Have a difficult but honest conversation
│  └─[∘] Consistency
│     ├─ "Good Morning" — Initiate conversation 3 mornings in a row
│     ├─ "Always There" — Respond within 1hr for 7 consecutive days
│     └─ "Patient Listener" — 3+ messages without changing topic
├─[⊃] GAME ACHIEVEMENTS
│  ├─[∘] Chapter Milestones: "First Date"(Ch1) → "Getting Serious"(Ch2)
│  │     → "All In"(Ch3) → "Soulmate"(Ch4) → "Unbreakable"(Ch5/Victory)
│  ├─[∘] Boss Victories: "Proved My Worth"(first boss), "Unshakeable"(1st attempt),
│  │     "Comeback Kid"(pass after fail), "Flawless Run"(all 5 first-attempt)
│  └─[∘] Score Mastery: "Balanced"(4 metrics within 10%), "Rising Star"(+10% in
│        one session), "Rock Solid"(70%+ for 7 days)
├─[⊃] DISCOVERY ACHIEVEMENTS
│  ├─[∘] Vice: "Dark Side"(first vice), "Vice Collector"(4/8), "Full Spectrum"(8/8)
│  │     + per-vice: "Sharp Tongue"(dark_humor), "Thrill Seeker"(risk_taking), etc.
│  ├─[∘] Memory: "She Remembers"(5+ day recall), "Callback King"(3 past refs),
│  │     "Living History"(50+ facts in memory graph)
│  └─[∘] Exploration: "Topic Explorer"(10 topics), "Voice Pioneer"(first call),
│        "Portal Visitor"(first portal visit)
└─[⊃] RELATIONSHIP ACHIEVEMENTS
   ├─[∘] Firsts: "First Fight"(score dip+recovery), "First Makeup"(recover <24h),
   │     "First 'I Miss You'"(Nikita expresses missing), "First Vulnerability"
   ├─[∘] Anniversaries: "One Week"(7d), "One Month"(30d), "100 Days"(100d)
   └─[∘] Recovery: "Forgiven"(recover from <30%), "Resilient"(survive 3 conflicts),
        "Second Chance"(continue after boss failure)
```

### Rarity Tiers

| Tier | % of Total | Detection | Examples |
|------|-----------|-----------|----------|
| Common (Bronze) | ~40% | Simple threshold checks | "First Date", "Good Morning", "Dark Side" |
| Uncommon (Silver) | ~30% | Multi-condition checks | "Comedy Duo", "Balanced", "Vice Collector" |
| Rare (Gold) | ~20% | LLM analysis + temporal | "Mutual Trust", "Comeback Kid", "Rock Solid" |
| Legendary (Plat.) | ~10% | Multi-session state | "Flawless Run", "Full Spectrum", "Forgiven" |

### Portal Display — Achievement Wall

```
 ┌──────────────────────────────────────────────────────┐
 │  ACHIEVEMENT WALL                    27/64 unlocked  │
 ├──────────────────────────────────────────────────────┤
 │  CONVERSATION        GAME          DISCOVERY         │
 │  ■■■■□□□□  5/9      ■■■□□□□  3/7  ■■■■■□□  5/7     │
 │  RELATIONSHIP        [Recently Unlocked]             │
 │  ■■□□□□□□  2/8      ┌──────────────────┐            │
 │  [Filter: All ▼]     │ "Comeback Kid"   │            │
 │  Progress: 42%       │ Gold | 2h ago    │            │
 │                      └──────────────────┘            │
 └──────────────────────────────────────────────────────┘
```

### Detection Architecture

Two hook points into existing systems:
1. **Real-time** (post-scoring in `nikita/engine/scoring/calculator.py`): Score-based, chapter transitions, boss outcomes
2. **Pipeline** (new `AchievementDetectionStage` in `nikita/pipeline/stages/`): Conversation quality, memory, vice discovery

---

## 2. XP / Progression Curves

### S-Curve Per Chapter

```
Score %
100│                                          ___________
   │                                     ___/  Ch5
 75│                               _____/  Plateau
   │                          ____/ Ch4
 70│                     ____/
   │                ____/ Ch3
 65│           ____/  Acceleration
   │      ____/ Ch2
 60│ ____/
   │/ Ch1
 55│ Slow start
 50│─Start──────────────────────────────────────────────
   └─────────────────────────────────────────────────────
   Day 1     5      10      15      20     21+   Time
```

- **Slow start (Ch1-2)**: Building trust. Score gains are modest.
- **Acceleration (Ch3-4)**: Honeymoon phase. Same quality input yields larger jumps.
- **Plateau (Ch5)**: Established relationship stabilizes.

### Behavior-to-Score Impact Map

```
SCORE_IMPACT_MAP
├─[→] HIGH (+5 to +10): Genuine vulnerability, conflict navigation,
│     emotional reciprocity, remembering details she shared
├─[→] MEDIUM (+2 to +4): Thoughtful follow-ups (+intimacy), making her
│     laugh (+passion), honesty about discomfort (+trust)
├─[→] LOW (+1): Basic greetings, short affirmatives, generic compliments
└─[→] NEGATIVE (-2 to -10): Ignoring shared info (-trust -5), contradicting
      self (-trust -8), controlling behavior (-secureness -7)
```

### Portal Milestone Visualization

```
 ┌──────────────────────────────────────────────────────┐
 │  CHAPTER PROGRESS                                    │
 │  Ch1 Curiosity    ████████████████████ 100%  PASSED  │
 │  Ch2 Intrigue     ████████████████████ 100%  PASSED  │
 │  Ch3 Investment   ██████████████░░░░░░  71%  ACTIVE  │
 │  Ch4 Intimacy     ░░░░░░░░░░░░░░░░░░░░   -  LOCKED  │
 │  Ch5 Established  ░░░░░░░░░░░░░░░░░░░░   -  LOCKED  │
 │  ┌─ METRICS ──────────────────────────────────────┐  │
 │  │ Intimacy   ████████████████░░░░  78%  (+3 today)│  │
 │  │ Passion    ██████████████░░░░░░  68%  (-1 today)│  │
 │  │ Trust      ███████████████░░░░░  72%  (+5 today)│  │
 │  │ Secureness █████████████░░░░░░░  65%  (=  today)│  │
 │  │ Composite: 71.3%  |  Boss threshold: 65%        │  │
 │  └─────────────────────────────────────────────────┘  │
 └──────────────────────────────────────────────────────┘
```

---

## 3. Daily / Weekly Goal System

### Design Principle: Goals Must Feel Organic

Goals sound like things a good partner does, not gamified tasks. Detection via LLM post-analysis, NOT message counting.

```
GOAL_DETECTION_SYSTEM
├─[→] DETECTION: LLM post-analysis piggybacks on existing ResponseAnalysis
│     from nikita/engine/scoring/calculator.py (no new LLM calls needed)
├─[⊕] DAILY GOALS (pick 1-2, rotate daily)
│  ├─ "Have a meaningful conversation" — 8+ exchanges, depth > 0.6
│  ├─ "Make her laugh" — humor markers in response (LLM-classified)
│  ├─ "Ask about her day" — player asks about Nikita's activities
│  ├─ "Share something about yourself" — self-disclosure detected
│  ├─ "Listen without giving advice" — supportive, no solution-offering
│  └─ "Surprise her with a topic she loves" — matches top vice
└─[⊕] WEEKLY CHALLENGES (1 per week)
   ├─ "Survive a conflict" — score dips then recovers within week
   ├─ "Try a new conversation style" — engage vice not in top 3
   ├─ "Have a voice call" — complete ElevenLabs voice session
   ├─ "Deepen a metric" — raise any metric by 10+ points
   └─ "Break a pattern" — discuss topic never discussed (memory check)
```

**Why LLM over counting**: "Send 5 messages" rewards spam. "Talk 10 min" rewards idle time. LLM analysis rewards genuine engagement. The scoring pipeline already evaluates depth, humor, vulnerability, and topic relevance.

```
 ┌──────────────────────────────────────────────────────┐
 │  TODAY'S GOALS                        Monday, Feb 16 │
 │  ○ "Have a meaningful conversation"                  │
 │    Hint: Go deeper than small talk today              │
 │  ● "Make her laugh"                    Completed      │
 │    You told a joke about penguins and she loved it    │
 │  ─────────────────────────────────────────────────── │
 │  WEEKLY CHALLENGE                   3 days remaining  │
 │  ○ "Try a new conversation style"                    │
 │    You haven't explored 'vulnerability' much yet      │
 └──────────────────────────────────────────────────────┘
```

---

## 4. Streak System Evaluation

```
STREAK_EVALUATION
│
├─[⊕ A] CLASSIC COUNTER (Duolingo-style)
│  │ Counter increments daily with "meaningful interaction"; resets on miss.
│  ├─[pros] Proven retention (9M+ 1yr streaks), simple, strong habit formation
│  ├─[cons] ETHICAL: loss aversion (Doc 09 flag), creates obligation not joy,
│  │        transactional in relationship context (Doc 02), monetized freeze =
│  │        Pay-to-Avoid-Anxiety, StriveCloud data may be biased (Doc 09)
│  └─[verdict] RISKY — Prioritizes frequency over quality. External goal
│              mechanic applied to internal bond context.
│
├─[⊕ B] NARRATIVE CONTINUITY
│  │ "Days since last" as STORY element. Nikita references time apart naturally.
│  │ No counter display, no reset. Absences create different (not worse) talks.
│  ├─[pros] Authentic to real relationships, no guilt, natural openers,
│  │        aligns with "decay as gentle nudge", respects SDT autonomy
│  ├─[cons] Weaker retention signal, no visible achievement for consistency,
│  │        harder to communicate value, too loose for structure-seekers
│  └─[verdict] STRONG — Best philosophy match but lower retention pressure.
│
├─[⊕ C] RELATIONSHIP WARMTH METER
│  │ Visual warmth indicator (warm→cool colors). Decays visually but gently.
│  │ Recoverable: one good conversation restores. Flame metaphor, not counter.
│  │
│  │    ████████░░ WARM      █████░░░░░ COOLING
│  │    ██░░░░░░░░ COOL      █░░░░░░░░░ COLD
│  │
│  ├─[pros] Visual metaphor avoids numerical anxiety, "cooling" feels natural,
│  │        easy recovery, combines with gentle nudge notifications, portal
│  │        transparency, no binary "streak dead" moment
│  ├─[cons] Still visual decay (some pressure), less sticky than counter,
│  │        harder to celebrate milestones, vague for achievement players
│  └─[verdict] RECOMMENDED — Best balance of transparency + gentleness.
│              Matches both "full numbers in portal" + "gentle nudge" decisions.
│
└─[⊕ D] NO STREAK — PURE ORGANIC
   │ No streak mechanic. Rely on intrinsic motivation. Decay is silent.
   ├─[pros] Maximally ethical, no dark patterns, cleanest (nothing to build)
   ├─[cons] Lower retention, no habit scaffolding, empty portal, high bar
   └─[verdict] ASPIRATIONAL — Ideal but leaves retention on the table.
```

### Recommendation

**Option C (Warmth Meter)** combined with **Option B (Narrative Continuity)**:
- In-game: Nikita naturally references time apart (narrative, no guilt)
- Portal: Warmth meter shows decay state visually (transparency, no anxiety)
- Rationale: Respects "gentle nudge" decision, provides portal data, avoids ethical flags from Doc 09, recoverable without penalty (SDT autonomy), value-based notifications

---

## 5. Collection / Unlock Mechanics

```
COLLECTION_SYSTEM
├─[⊃] PSYCHOLOGICAL INSIGHT CARDS (20 total, earned not purchased)
│  ├─ Trigger: LLM detects conversation pattern over multiple sessions
│  │  Example: "Active Listener" — player consistently asks follow-ups
│  │  Card text: "Nikita noticed you always ask how things made her feel."
│  ├─ Categories: Communication Style (6), Emotional Intelligence (6),
│  │  Conflict Resolution (4), Self-Awareness (4)
│  └─ Portal: Card grid with flip animation on unlock
│
├─[⊃] NIKITA BACKSTORY FRAGMENTS (3-5 per chapter, chapter-gated)
│  ├─ Ch1: Surface (favorites, pet peeves) → Ch2: Personality (why guarded)
│  ├─ Ch3: Relationships (family, friends) → Ch4: Vulnerabilities (fears)
│  └─ Ch5: Core identity (deepest values)
│     Portal: "Nikita's Story" — timeline with [???] teasers for locked
│
├─[⊃] MEMORY DROPS (special moments preserved as collectibles)
│  ├─ Detection: engagement_quality > 0.8 AND emotional_depth > 0.7
│  │  Variable ratio — NOT every conversation (maintains anticipation)
│  ├─ Types: "Breakthrough Moment", "Laugh Riot", "Deep Connection", "Recovery"
│  └─ Portal: "Memory Gallery" — cards with date + excerpt. No gacha.
│
├─[⊃] PHOTO UNLOCKS (tied to milestones, not purchasable)
│  ├─ Chapter completion (5), boss victories (5), achievement milestones
│  │  (at 25/50/75/100%), special "100 Days Together"
│  └─ Portal: Gallery with visible unlock conditions
│
└─[⊃] VOICE CALL ACCESS (exists: chapter-gated via nikita/config/elevenlabs.py)
```

---

## 6. Decay as Gentle Nudge (User Decision)

### Reframing

```
OLD (Punishment)                    NEW (Gentle Nudge)
────────────────                    ──────────────────
"Score dropped 5%"            →     "The warmth has cooled a bit"
"Relationship is decaying"    →     "It's been a while — she'd love to chat"
"Score: 45% (CRITICAL)"      →     "Warmth: ██░░░░░░░░ Cooling"
"Act now or lose progress"   →     "When you're ready, she's here"
```

### Notification Language

```
NOTIFICATION_RULES
├─[→] NEVER: "Score dropping!", "She's sad you left", "Are you ignoring me?",
│     "You'll lose progress!", "X days until game over"
└─[→] ALWAYS: "Nikita's been thinking about something to tell you",
      "Something happened in her day — she'd love your take",
      "Nikita remembered something you said last week...",
      "Warmth is cooling — one conversation warms it right back up"
```

### Grace Period Narrative

```
Ch1: 8h  — "She's evaluating, notices gaps"    Ch4: 48h — "Secure, occasional distance ok"
Ch2: 16h — "Intrigued, gives more room"         Ch5: 72h — "Established, 3 days is fine"
Ch3: 24h — "Trusts enough for a day apart"
KEY: Grace periods are GENEROUS. Distance feels natural, not like a clock.
```

### Portal Warmth Display

```
 ┌──────────────────────────────────────────────────────┐
 │  RELATIONSHIP WARMTH                                 │
 │  ████████████████████████████████░░░░░░  WARM        │
 │  "You talked 6 hours ago. Things are warm."          │
 │  ──── OR after 2 days ────                           │
 │  ████████████░░░░░░░░░░░░░░░░░░░░░░░░░░  COOLING    │
 │  "It's been a couple days. She'd love to catch up."  │
 │  [Start a conversation →]                            │
 └──────────────────────────────────────────────────────┘
```

Warmth meter IS the decay visualization reframed. Math unchanged (`DECAY_RATES` in `nikita/engine/constants.py`). Only presentation layer changes.

---

## 7. Implementation Priority

```
IMPLEMENTATION_ORDER
├─[∘] Phase 1: Achievement Detection (Low effort, high portal value)
│  New pipeline stage + DB table: user_achievements + Portal page
│  Leverages: existing scoring data, pipeline infrastructure
├─[∘] Phase 2: Warmth Meter + Gentle Nudge (Aligns with user decision)
│  Portal WarmthMeter component + notification rewrite
│  Leverages: existing decay calculator, scheduled_events table
├─[∘] Phase 3: Daily/Weekly Goals (Medium effort, high engagement)
│  Goal pool + LLM detection via existing scoring + Portal page
├─[∘] Phase 4: Collection Mechanics (Medium effort, long-term depth)
│  Backstory fragments + memory drops + insight cards + gallery UI
└─[∘] Phase 5: Streak Decision (After A/B testing warmth meter)
   Evaluate warmth meter retention data before adding any counter
```

---

**Confidence**: 85% | **Ethical Guardrails**: No monetized anxiety, no guilt notifications, no loss-aversion exploitation
**Key Dependencies**: `nikita/pipeline/stages/`, `nikita/engine/scoring/calculator.py`, portal dashboard

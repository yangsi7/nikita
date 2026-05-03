# Idea 16: Portal Game Dashboard (Full Transparency)

**Date**: 2026-02-16 | **Type**: Feature Ideation (Phase 2)
**Decision**: Portal = full numbers, complete transparency
**Scope**: Multi-sprint portal redesign (3-4 sprints, 12-16 weeks)

---

## Design Rationale (Tree-of-Thought)

**Branch A**: Minimal (3 cards, composite only) -- rejects "full transparency" decision.
**Branch B**: Data dump (every metric on one page) -- violates anti-pattern research (Doc 07/09).
**Branch C**: Progressive disclosure with F-pattern layout -- transparency with clarity.
--> **Selected: Branch C**. Show ALL data, layered: primary view (6 cards), detail pages via nav.

**Scope warning** (Doc 09): "multi-sprint effort, not a design tweak." Adds ~8 sections, ~15 components.

---

## 1. Score Dashboard (Main View)

```
+------------------------------------------------------------------+
|  NIKITA  [Dashboard] [Timeline] [Memories] [Trophies]  [Settings]|
+------------------------------------------------------------------+
|  +---------------------------+  +-------------------------------+  |
|  | RELATIONSHIP SCORE   Live |  | I/P/T/S RADAR           7d   |  |
|  |       ___  67.4  ___      |  |          I(72)                |  |
|  |      /   \  /100 /   \    |  |         / \                   |  |
|  |     |  67  |    | +2.3|   |  |    S(58)/   \P(65)            |  |
|  |      \___/      \___/     |  |        \   /                  |  |
|  |  since yesterday: +2.3    |  |         T(71)                 |  |
|  +---------------------------+  +-------------------------------+  |
|  +---------------------------+  +-------------------------------+  |
|  | METRIC BREAKDOWN         |  | SCORE TREND          7d | 30d |  |
|  | Intimacy   72 +++++ +1.4  |  |    _    .                     |  |
|  | Passion    65 ++++  -0.8  |  |   / \  / \   __               |  |
|  | Trust      71 +++++ +3.1  |  |  /   \/   \_/  \              |  |
|  | Secureness 58 +++   +0.4  |  | /              \_             |  |
|  | Formula:                  |  | -- composite  -- intimacy     |  |
|  | I*.30+P*.25+T*.25+S*.20   |  | -- passion    -- trust        |  |
|  +---------------------------+  +-------------------------------+  |
+------------------------------------------------------------------+
```

| Element | Component | Source | Update |
|---------|-----------|--------|--------|
| Composite score | `Card` + SVG radial | `GET /portal/stats` | Realtime (Postgres Changes) |
| Delta indicator | `Badge` | `GET /portal/score-history?days=1` | 30s poll |
| Radar chart | `ChartContainer` + Recharts `RadarChart` | `GET /portal/metrics` | Realtime |
| Sparklines | `ChartContainer` + Recharts `LineChart` | `GET /portal/score-history/detailed?days=30` | 60s poll |
| Metric bars | `Progress` + `Badge` | `GET /portal/metrics` | Realtime |
| Formula | `Tooltip` on hover | Static | Never |

**Data flow**: `users/user_metrics` UPDATE --> Supabase Realtime --> WebSocket --> re-render

---

## 2. Chapter Progress & Boss Tracker

```
+------------------------------------------------------------------+
|  Chapter 2: Intrigue                                    Day 22    |
|  +============================================--------+  60%     |
|  |>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>            |        |  36/60   |
|  +============================================--------+           |
|  "36 points toward Boss #2 threshold (60)"                        |
|  +---------------------------+  +-------------------------------+  |
|  | BOSS PREVIEW         Ch2  |  | BOSS HISTORY                 |  |
|  |  "Handle My Intensity?"   |  |  Ch1: Worth My Time?         |  |
|  |  Tests: Passion & Trust   |  |  [PASSED] Score: 57  Att: 1  |  |
|  |  Threshold: 60/100        |  |  Ch2: [LOCKED]  Ch3-5: [LOCKED]|  |
|  |  Your score: 67.4         |  |  Total fails: 0/3 allowed    |  |
|  |  Attempts remaining: 3/3  |  |                               |  |
|  +---------------------------+  +-------------------------------+  |
|  MILESTONES: [x] Deep convo  [x] Vice found  [ ] Score 60       |
+------------------------------------------------------------------+
```

| Element | Component | Source | Update |
|---------|-----------|--------|--------|
| Progress bar | `Progress` + `Badge` | `GET /portal/stats` (progress_to_boss) | Realtime |
| Boss preview | `Card` + `Alert` | Static (`BOSS_ENCOUNTERS`) | Never |
| Boss history | `Table` | `GET /portal/score-history?event_type=boss` | On-demand |
| Milestones | `Checkbox` (read-only) | New: `GET /portal/milestones` | 60s poll |

---

## 3. Decay Timer & Nudge System (Warmth Meter)

**Design**: "Warmth meter" framing (NOT "decay countdown"). Gradient: warm amber --> cool blue.
Language: "cooling" not "decaying." Follows Doc 06 anti-Tamagotchi principle.

```
+------------------------------------------------------------------+
|  Nikita's Warmth                                                  |
|  [==========================================---------]  72%       |
|   warm                                         cooling            |
|  Last talked: 6h ago | Grace: 10h left (16h total Ch2)           |
|  "Nikita's still thinking about your last conversation"           |
|  +---------------------------+  +-------------------------------+  |
|  | DECAY INFO           Ch2  |  | WHAT-IF PREVIEW              |  |
|  |  Rate: -0.6 pts/hour      |  |  +4h:  67.4 (no change)      |  |
|  |  Grace: 16 hours          |  |  +12h: 67.4 (grace ends)     |  |
|  |  Ch1: -0.8/hr  Grace: 8h  |  |  +18h: 63.8 (-3.6 pts)      |  |
|  |  Ch3: -0.4/hr  Grace: 24h |  |  +24h: 60.2 (-7.2 pts)      |  |
|  |  Ch5: -0.2/hr  Grace: 72h |  |  "Longer chapters = more     |  |
|  |                           |  |   breathing room"             |  |
|  +---------------------------+  +-------------------------------+  |
+------------------------------------------------------------------+
```

| Element | Component | Source | Update |
|---------|-----------|--------|--------|
| Warmth bar | Custom gradient `Progress` | `GET /portal/decay` | 30s poll |
| Grace indicator | `Alert` info | `GET /portal/decay` (hours_remaining) | 30s poll |
| Decay rates | `Table` | Static (DECAY_RATES, GRACE_PERIODS) | Never |
| What-if | `Card` + client math | `GET /portal/decay` | 30s poll |

---

## 4. Engagement State Indicator

```
+------------------------------------------------------------------+
|  Current: IN_ZONE                          Multiplier: 1.2x       |
|  CALIBRATING --> IN_ZONE --> DRIFTING --> CRITICAL                 |
|       |            ^[*]        |             |                     |
|       v            |           v             v                     |
|  RECOVERING_CLINGY-+   RECOVERING_DISTANT----+                    |
|  +---------------------------+  +-------------------------------+  |
|  | GUIDANCE                  |  | STATE HISTORY (7 days)        |  |
|  |  You're in the zone!      |  |  Feb 16: IN_ZONE (3d)        |  |
|  |  Nikita is engaged.       |  |  Feb 13: CALIBRATING (2d)    |  |
|  |  Scoring gets 1.2x mult.  |  |  Feb 11: DRIFTING (1d)       |  |
|  |  Tip: Keep conversations  |  |  Longest: IN_ZONE 5d         |  |
|  |  varied and genuine.      |  |  Most common: IN_ZONE (62%)  |  |
|  +---------------------------+  +-------------------------------+  |
+------------------------------------------------------------------+
```

| State | Color | Icon | Element | Component | Source |
|-------|-------|------|---------|-----------|--------|
| CALIBRATING | Gray | Compass | State diagram | Custom SVG | `GET /portal/engagement` |
| IN_ZONE | Emerald | CheckCircle | Guidance | `Alert` | Static per-state |
| DRIFTING | Amber | AlertTriangle | History | `Table` | Same (transitions) |
| CRITICAL | Rose | XCircle | All elements | -- | 30s poll |
| RECOVERING_* | Blue/Purple | Arrow | -- | -- | -- |

---

## 5. Achievement Wall / Trophy Case

```
+------------------------------------------------------------------+
| TROPHY CASE                                    12/48 Unlocked     |
|  Filter: [All] [Conversation] [Game] [Discovery] [Relationship]  |
|  +----------+ +----------+ +----------+ +----------+             |
|  | First    | | Storm    | |   ????   | |   ????   |             |
|  | Message  | | Survivor | | LOCKED   | | LOCKED   |             |
|  | Common   | | Rare     | | Hint:    | | Hint:    |             |
|  | Feb 01   | | Feb 09   | | "Face a  | | "Only    |             |
|  |          | |          | |  test"   | |  worthy" |             |
|  +----------+ +----------+ +----------+ +----------+             |
+------------------------------------------------------------------+

Detail modal (on click):
+----------------------------------------------+
|  STORM SURVIVOR                    [x] Close |
|  Rarity: Rare (12%) | Category: Relationship |
|  Unlocked: Feb 9 | Score: 54.2 | Ch1         |
|  "Survived your first conflict with Nikita"  |
+----------------------------------------------+
```

| Rarity | Color | % | Component | Source |
|--------|-------|---|-----------|--------|
| Common | Gray | 60% | Grid of `Card` | New: `GET /portal/achievements` |
| Rare | Cyan | 25% | `Tabs` filter | On-demand |
| Epic | Purple | 12% | `Dialog` detail | Same endpoint |
| Legendary | Gold | 3% | `Badge` rarity | Static metadata |

**New table**: `achievements` (id, user_id, type, category, rarity, unlocked_at, metadata JSONB).
**New endpoint**: `GET /portal/achievements` + pipeline hook `POST /internal/achievements/check`.

---

## 6. Relationship Timeline

```
+------------------------------------------------------------------+
| TIMELINE                     Filter: [All] [Boss] [Milestone]     |
|  Feb 16 ----+ Score reached 67 -- new personal best              |
|             | Score: 67.4 | Chapter 2                             |
|  Feb 14 ----+ [MILESTONE] First Valentine's conversation         |
|             | Score: 63.1 | Trust +4.2                            |
|  Feb 09 ----+ [CONFLICT] First argument survived                 |
|             | Score: 54.2 | Secureness -3.1, Trust +2.0          |
|  Feb 05 ----+ [BOSS] Ch1: "Worth My Time?" -- PASSED             |
|             | Score: 56.8 | Attempt 1/3                           |
|  Feb 01 ----+ [START] First message sent | Score: 50.0           |
+------------------------------------------------------------------+
```

Custom vertical timeline (Tailwind) | `GET /portal/score-history/detailed?days=365` | 60s poll.
Events derived from `score_history` (event_type: interaction, decay, boss_pass, boss_fail, chapter_advance).

---

## 7. Memory Album

```
+------------------------------------------------------------------+
| WHAT NIKITA REMEMBERS                          147 memories       |
|  [User Facts: 52] [Relationship: 63] [Nikita Facts: 32]         |
|  +--------------------------------------------------------------+|
|  | "Works as a software engineer in Zurich"       Feb 15        ||
|  | "Prefers espresso over filter coffee"           Feb 14        ||
|  | "Has a sister named Maria getting married"      Feb 12        ||
|  +--------------------------------------------------------------+|
|  RELATIONSHIP FACTS                                               |
|  | "First deep conversation was about ambition"    Feb 14        ||
|  | "Survived first argument about priorities"      Feb 09        ||
|  NIKITA FACTS                                                     |
|  | "Told player about her fear of abandonment"     Feb 13        ||
+------------------------------------------------------------------+
```

`Tabs` + `ScrollArea` + `Card` list | New: `GET /portal/memories?type=user&limit=50` | On-demand.
Existing `memory_facts` table has `fact_type` (user, nikita, relationship) -- maps to tabs directly.

---

## 8. Nikita's Room / State View

```
+------------------------------------------------------------------+
|  +---------------------------+  +-------------------------------+  |
|  | CURRENT STATE              |  | EMOTIONAL STATE   4D         |  |
|  |  Mood: Playful            |  |  Arousal:   0.62  [======-]  |  |
|  |  Activity: Gaming night   |  |  Valence:   0.71  [=======-] |  |
|  |  Available: Yes           |  |  Dominance: 0.55  [=====--]  |  |
|  |  "Playing Zelda and       |  |  Intimacy:  0.48  [====---]  |  |
|  |   thinking about our      |  |  Conflict: None              |  |
|  |   conversation earlier"   |  |  Updated: 2 min ago          |  |
|  +---------------------------+  +-------------------------------+  |
|  +---------------------------+  +-------------------------------+  |
|  | TODAY'S EVENTS             |  | SOCIAL CIRCLE                |  |
|  |  9am  Work -- busy day    |  |  Emma      Best friend  87%  |  |
|  |  12pm Lunch with Emma     |  |  Marcus    Close friend 72%  |  |
|  |  6pm  Gym -- leg day      |  |  Sarah     Friend       65%  |  |
|  |  8pm  Gaming night  [now] |  |  Jake      Acquaintance 41%  |  |
|  +---------------------------+  +-------------------------------+  |
+------------------------------------------------------------------+
```

| Element | Source | Update |
|---------|--------|--------|
| Emotional state | `GET /portal/emotional-state` | Realtime |
| Life events | `GET /portal/life-events` | 60s poll |
| Social circle | `GET /portal/social-circle` | On-demand |

---

## 9. Psychological Insights Panel

```
+------------------------------------------------------------------+
| INSIGHTS                                     4/16 Discovered      |
|  [Attachment] [Communication] [Conflict] [Growth]                 |
|  +------------------+ +------------------+ +------------------+  |
|  | You show secure  | | ???????????????? | | ???????????????? |  |
|  | attachment when   | | LOCKED           | | LOCKED           |  |
|  | Nikita shares    | | Hint: "What      | | Hint: "How do    |  |
|  | vulnerabilities. | |  happens when    | |  you handle      |  |
|  | Discovered Ch1   | |  she pulls away?"| |  jealousy?"      |  |
|  +------------------+ +------------------+ +------------------+  |
+------------------------------------------------------------------+
```

`Card` grid with blur overlay for locked | New: `GET /portal/insights` | On-demand.
**New table**: `player_insights` (id, user_id, category, content, hint, unlocked_at, chapter).
**Trigger**: Pipeline stage or post-scoring hook detects insight-worthy behavioral patterns.

---

## 10. Layout & Navigation Architecture

### F-Pattern Main Layout

```
+------------------------------------------------------------------+
| HEADER: Logo | Dashboard | Timeline | Memories | Trophies | Gear |
+------------------------------------------------------------------+
| LEFT COLUMN (PRIMARY)          | RIGHT COLUMN (SECONDARY)         |
| 1. Score Dashboard             | 4. Engagement State              |
| 2. Chapter Progress            | 5. Warmth Meter                  |
| 3. Score Trend                 | 6. Nikita's State                |
+------------------------------------------------------------------+
| ROUTES: /dashboard (main) | /timeline | /memories | /trophies    |
|         /nikita (room)    | /insights                             |
+------------------------------------------------------------------+

MOBILE (<768px): Stack to single column, 2x2 card grid, bottom nav
[Home] [Timeline] [Memories] [Trophies]
```

### Real-Time vs Polling Strategy

| Data | Method | Freq | Rationale |
|------|--------|------|-----------|
| Score + metrics | Supabase Realtime | Instant | Core metric, must feel alive |
| Score history | Polling | 60s | Historical, not urgent |
| Decay status | Polling | 30s | Countdown needs regular update |
| Engagement state | Polling | 30s | State changes infrequent |
| Life events | Polling | 60s | Background simulation |
| Emotional state | Supabase Realtime | Instant | Mood should feel alive |
| Memories/achievements | On-demand | Load | Static once fetched |

### Migration Path

```
Sprint 1: Keep polling, add shadcn chart components (radar, sparklines)
Sprint 2: Supabase Realtime for users + user_metrics tables
Sprint 3: Achievement system, insights panel, new tables
Sprint 4: Memory album UI, timeline, mobile optimization
```

### New Requirements Summary

**API Endpoints**:
- `GET /portal/memories` -- player-facing memory facts (High)
- `GET /portal/achievements` -- achievement list with unlock status (Medium)
- `GET /portal/milestones` -- chapter milestone checklist (Medium)
- `GET /portal/insights` -- psychological insight cards (Low)

**Database Tables**:
- `achievements` (id, user_id, type, category, rarity, unlocked_at, metadata JSONB)
- `player_insights` (id, user_id, category, content, hint, unlocked_at)
- `milestones` (id, user_id, chapter, type, completed_at)

**New Components** (9 total):
ScoreRadial, MetricRadar, ScoreSparkline, WarmthMeter, EngagementFSM,
AchievementCard, InsightCard, TimelineEvent, MemoryList

### Anti-Patterns Avoided (Doc 07/09)

1. **No info dump**: Max 6 cards on main dashboard; detail pages via navigation
2. **No empty states**: Every empty section has onboarding text
3. **No metrics without context**: Every number has delta, trend, or tooltip
4. **No color-only indicators**: All states use icon + color + label
5. **No jargon**: "Warmth meter" not "Decay timer"
6. **No real-time overload**: Realtime for 3 tables only; rest is polling/on-demand
7. **Skeleton UIs**: All cards show skeleton placeholders during load (no spinners)

---

**Effort**: 3-4 sprints (12-16 weeks). **Dependencies**: Supabase Realtime, 3 new tables, 4 endpoints.

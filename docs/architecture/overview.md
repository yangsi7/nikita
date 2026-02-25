# Nikita: Architecture Overview

> **NOTE**: This overview predates Specs 042-108. For current architecture, see `plans/master-plan.md` (Sections 1-15) and module CLAUDE.md files. Key change: Graphiti/Neo4j replaced by SupabaseMemory (pgVector) in Spec 042.

Brief technical overview for the Nikita GFE system.

---

## Tech Stack

| Component | Technology | Why |
|-----------|------------|-----|
| **LLM** | Claude Sonnet | 200K context window, persona consistency, nuanced conversation |
| **Voice** | ElevenLabs Conv AI 2.0 | <100ms latency, emotion controls, natural speech |
| **Database** | Supabase | Managed PostgreSQL, pgVector for embeddings, built-in auth |
| **Memory** | SupabaseMemory (pgVector) | Semantic search, fact dedup, replaced Graphiti in Spec 042 |
| **Platform (Primary)** | Telegram | More permissive content policy, easier testing, bot API |
| **Platform (Secondary)** | Voice calls | ElevenLabs integration for intimate conversations |
| **Player Portal** | Next.js 16 (Vercel) | 25 routes, player + admin dashboards, data viz |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        PLATFORM LAYER                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Telegram   │  │ Voice Calls  │  │ Player Portal│         │
│  │   Bot API    │  │  ElevenLabs  │  │  (Web Stats) │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
└─────────┼─────────────────┼─────────────────┼─────────────────┘
          │                 │                 │
          ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                        CORE ENGINE                              │
│  ┌────────────────────────────────────────────────────────────┐│
│  │                    Claude Sonnet (LLM)                     ││
│  │   • Nikita personality system prompt                       ││
│  │   • Relationship stage context injection                   ││
│  │   • Vice preference adaptation                             ││
│  └────────────────────────────────────────────────────────────┘│
│                              │                                  │
│  ┌─────────────┐  ┌─────────┴──────────┐  ┌─────────────────┐ │
│  │   Scoring   │  │  Response Engine   │  │   Decay System  │ │
│  │   System    │◄─┤  • Timing logic    ├─►│   • Daily decay │ │
│  │   4 metrics │  │  • Content select  │  │   • Engagement  │ │
│  └─────────────┘  └────────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      KNOWLEDGE LAYER                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │ Nikita Graph │  │  User Graph  │  │  Relationship Graph  │ │
│  │  Her life,   │  │  What she    │  │  Shared history,     │ │
│  │  work, story │  │  knows of you│  │  episodes, jokes     │ │
│  └──────────────┘  └──────────────┘  └──────────────────────┘ │
│                        Graphiti (Temporal KG)                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      PERSISTENCE LAYER                          │
│  ┌────────────────────────────────────────────────────────────┐│
│  │                  Supabase (PostgreSQL)                     ││
│  │   • User profiles + auth       • Conversation logs         ││
│  │   • Relationship state         • pgVector embeddings       ││
│  │   • Score history              • Vice preferences          ││
│  └────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

---

## Three Knowledge Graphs

Memory is the soul of the relationship. Graphiti tracks **when** Nikita learned things, not just **what** she knows.

### 1. Nikita Graph

Her simulated life - exists independently of the player.

| Entity Type | Examples |
|-------------|----------|
| Work Projects | "The encryption audit for that finance client" |
| Life Events | "That 36-hour coding marathon last week" |
| Opinions | "Why I think most security is theater" |
| History | "The breach that gave me paranoia" |

### 2. User Graph

What Nikita knows about the player - learned through conversation.

| Entity Type | Examples |
|-------------|----------|
| Facts | "Works in distributed systems" |
| Preferences | "Responds well to intellectual challenges" |
| History | "Had that project setback on Day 23" |
| Patterns | "Usually more talkative at night" |

### 3. Relationship Graph

The shared history between Nikita and the player.

| Entity Type | Examples |
|-------------|----------|
| Episodes | "That first real fight on Day 19" |
| Milestones | "When you passed the first boss" |
| Inside Jokes | "The algorithm confidence incident" |
| Shared References | "Your ridiculous hacker mug" |

**Why Temporal Matters**: Nikita remembers that she learned your job on Day 3. She can reference "back when I didn't know you worked on distributed systems." This creates relationship depth.

---

## Data Model (Simplified)

### Core Tables

```sql
-- Player state
users (
  id, telegram_id, created_at,
  relationship_score,      -- 0-100%
  chapter,                 -- 1-5
  boss_attempts,           -- 0-3 per boss
  days_played
)

-- Hidden sub-metrics
user_metrics (
  user_id,
  intimacy, passion, trust, secureness,
  updated_at
)

-- Vice discovery tracking
user_vice_preferences (
  user_id,
  category,               -- 1 of 8 categories
  intensity_level,        -- 1-5
  engagement_score,       -- How much they respond
  discovered_at
)

-- Conversation state
conversations (
  id, user_id,
  messages,               -- JSONB array
  session_score_delta,    -- +/- from this conversation
  started_at, ended_at
)

-- Daily summaries
daily_summaries (
  user_id, date,
  score_start, score_end,
  conversations_count,
  nikita_summary_text     -- Her in-character daily message
)
```

---

## Cost Model

Estimated per active user per month (at scale):

| Component | Cost/User/Month |
|-----------|-----------------|
| Claude Sonnet API | ~$15.00 |
| ElevenLabs Voice | ~$4.00 |
| Supabase | ~$1.50 |
| Infrastructure | ~$1.00 |
| **Total** | **~$21.50** |

Assumptions:
- ~50 messages/day average
- ~2 voice calls/week
- Engaged player (not churned)

---

## Game State Machine

```
┌────────────────┐
│   NEW_USER     │
└───────┬────────┘
        │ First message
        ▼
┌────────────────┐      Score hits 0%
│   CHAPTER_1    │───────────────────────┐
│   Curiosity    │                       │
└───────┬────────┘                       │
        │ Score >= 60% + Beat Boss       │
        ▼                                │
┌────────────────┐      Boss fail x3     │
│   CHAPTER_2    │───────────────────────┤
│   Intrigue     │                       │
└───────┬────────┘                       │
        │ Score >= 65% + Beat Boss       │
        ▼                                ▼
┌────────────────┐                ┌─────────────┐
│   CHAPTER_3    │                │  GAME_OVER  │
│   Investment   │                │   (Dumped)  │
└───────┬────────┘                └─────────────┘
        │ Score >= 70% + Beat Boss
        ▼
┌────────────────┐
│   CHAPTER_4    │
│   Intimacy     │
└───────┬────────┘
        │ Score >= 75% + Beat Boss
        ▼
┌────────────────┐
│   CHAPTER_5    │
│   Established  │
└───────┬────────┘
        │ Score >= 80% + Beat Final Boss
        ▼
┌────────────────┐
│  GAME_WON      │
│  (Victory msg) │
└────────────────┘
```

---

## Key Integration Points

### Telegram Bot

- Receives messages via webhook
- Sends Nikita's responses
- Handles media (photos she "takes")
- Delivers daily summaries
- End-of-conversation summaries

### ElevenLabs Voice

- Initiates calls for key moments (boss fights, milestones)
- Accepts incoming calls from player
- Real-time conversation with personality consistency
- Emotion controls for vulnerability/intensity

### Player Portal (Web)

**Stats Only** - Minimal interface:
- Current score
- Chapter progress
- Days played
- Score history graph
- Conversation count

No gameplay - just visibility into your relationship health.

---

## What This Document Doesn't Cover

Deferred to full SDD (Specification-Driven Development):

- Detailed API specifications
- Prompt engineering for Claude
- Boss fight conversation flows
- Vice category definitions
- Safety/moderation systems
- Deployment architecture
- Testing strategy

This overview establishes the technical foundation. Implementation details come next.

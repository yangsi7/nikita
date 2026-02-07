# User Journey

```yaml
context_priority: high
audience: ai_agents
last_updated: 2026-02-03
related_docs:
  - PROJECT_OVERVIEW.md
  - ONBOARDING.md
  - GAME_ENGINE_MECHANICS.md
```

## Overview

This document maps the complete user journey through the Nikita game, from first contact to potential game over.

---

## High-Level Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           USER JOURNEY FLOW                                   │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   FIRST     │    │  ONBOARDING │    │    ACTIVE   │    │   CHAPTER   │  │
│  │  CONTACT    │───▶│    FLOW     │───▶│    PLAY     │───▶│ PROGRESSION │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └──────┬──────┘  │
│                                                                   │         │
│                                              ┌────────────────────┘         │
│                                              ▼                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                     │
│  │  GAME OVER  │◀───│ BOSS FIGHT  │◀───│   CHAPTER   │                     │
│  │  (Breakup)  │    │ (55-75%)    │    │  THRESHOLD  │                     │
│  └─────────────┘    └─────────────┘    └─────────────┘                     │
│         ▲                                                                   │
│         │                                                                   │
│  ┌─────────────┐                                                           │
│  │   DECAY     │  (Happens continuously when player is inactive)           │
│  │  TIMEOUT    │                                                           │
│  └─────────────┘                                                           │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: First Contact

### Entry Points

| Channel | Trigger | Handler |
|---------|---------|---------|
| Telegram | User sends `/start` | `nikita/platforms/telegram/commands.py:CommandHandler` |
| Voice | User calls phone number | `nikita/agents/voice/inbound.py:handle_inbound_call` |
| Portal | User visits web app | `portal/src/app/page.tsx` |

### Telegram Flow Detail

```
User sends /start to @Nikita_my_bot
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  CommandHandler.handle() @ commands.py:45-80                    │
│  - Validates webhook signature (SEC-01)                         │
│  - Checks if user exists in database                            │
│  - Routes to appropriate handler                                │
└─────────────────────────────────────────────────────────────────┘
         │
         ├──── User EXISTS with completed profile ────▶ MessageHandler
         │
         └──── User NEW or incomplete profile ────▶ OnboardingRouter
```

### Code References

| File | Line | Function |
|------|------|----------|
| `nikita/platforms/telegram/commands.py` | 45-80 | `CommandHandler.handle()` |
| `nikita/platforms/telegram/webhook.py` | 30-60 | Signature validation |
| `nikita/api/routes/telegram.py` | 20-50 | Webhook endpoint |

---

## Phase 2: Onboarding

### Two Onboarding Paths

```
                    ┌─────────────────┐
                    │  NEW USER       │
                    │  DETECTED       │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
              ▼                             ▼
     ┌─────────────────┐          ┌─────────────────┐
     │  VOICE PATH     │          │   TEXT PATH     │
     │  (Preferred)    │          │   (Fallback)    │
     └────────┬────────┘          └────────┬────────┘
              │                             │
              ▼                             ▼
     ┌─────────────────┐          ┌─────────────────┐
     │  Meta-Nikita    │          │  Text Questions │
     │  Voice Agent    │          │  via Telegram   │
     │  (Conversational)│         │  (Form-like)    │
     └────────┬────────┘          └────────┬────────┘
              │                             │
              ▼                             ▼
     ┌─────────────────┐          ┌─────────────────┐
     │  Profile stored │          │  Profile stored │
     │  via server tool│          │  via handler    │
     └────────┬────────┘          └────────┬────────┘
              │                             │
              └──────────────┬──────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  HANDOFF TO     │
                    │  NIKITA AGENT   │
                    └─────────────────┘
```

### Voice Onboarding (Meta-Nikita)

The voice onboarding uses a separate "Meta-Nikita" agent that:
1. Asks conversational questions about the user
2. Extracts profile data via LLM
3. Stores profile using `store_user_profile` server tool
4. Hands off to main Nikita agent

**Key Files:**
| File | Line | Purpose |
|------|------|---------|
| `nikita/onboarding/meta_nikita.py` | 1-150 | Meta-Nikita agent config |
| `nikita/onboarding/server_tools.py` | 30-80 | Profile storage tool |
| `nikita/onboarding/handoff.py` | 1-100 | Agent handoff logic |

### Text Onboarding

The text onboarding asks structured questions:
1. What's your name?
2. What do you do for work?
3. What are your hobbies?
4. What are you looking for in this relationship?

**Key Files:**
| File | Line | Purpose |
|------|------|---------|
| `nikita/platforms/telegram/registration_handler.py` | 1-200 | Text onboarding flow |
| `nikita/db/models/pending_registration.py` | 1-50 | Registration state |

### Profile Data Collected

| Field | Type | Source |
|-------|------|--------|
| `display_name` | string | Voice extraction or text input |
| `occupation` | string | Voice extraction or text input |
| `hobbies` | string[] | Voice extraction or text input |
| `relationship_goals` | string | Voice extraction or text input |
| `personality_notes` | string | LLM inference from conversation |
| `phone_number` | string | Telegram phone or voice caller ID |

---

## Phase 3: Active Play

### Conversation Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          ACTIVE PLAY LOOP                                     │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐                                                            │
│  │ User sends  │                                                            │
│  │  message    │                                                            │
│  └──────┬──────┘                                                            │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  MessageHandler.handle_message() @ message_handler.py:50-150        │   │
│  │  1. Rate limit check (20/min, 500/day)                              │   │
│  │  2. Profile gate check (onboarding_status)                          │   │
│  │  3. Game over check (chapter_number > 5)                            │   │
│  │  4. Create conversation record                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  ContextEngine.collect() @ engine.py:80-150                         │   │
│  │  - 8 collectors gather context (45s total timeout)                  │   │
│  │  - Returns ContextPackage with 115+ fields                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  PromptGenerator.generate() @ generator.py:100-200                  │   │
│  │  - Assembles system prompt from context                             │   │
│  │  - Validates coverage (80% min, 5 CORE sections)                    │   │
│  │  - Calls Claude Sonnet 4.5                                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  PostProcessor.process_conversation() @ post_processor.py:100-250   │   │
│  │  - 11 async stages (threads, thoughts, scoring, etc.)               │   │
│  │  - Updates Neo4j graphs                                             │   │
│  │  - Calculates score deltas                                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Score Update & Chapter Check                                        │   │
│  │  - Apply score delta to user metrics                                │   │
│  │  - Check if score crosses chapter threshold                         │   │
│  │  - Trigger boss fight if needed                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────┐                                                            │
│  │ Send Nikita │                                                            │
│  │  response   │                                                            │
│  └─────────────┘                                                            │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Scoring Mechanics

Every conversation affects 4 metrics:

| Metric | Weight | Positive Triggers | Negative Triggers |
|--------|--------|-------------------|-------------------|
| Intimacy | 30% | Personal sharing, vulnerability | Dismissive responses |
| Passion | 25% | Flirting, excitement, humor | Boring, disengaged |
| Trust | 25% | Honesty, reliability, support | Lies, inconsistency |
| Secureness | 20% | Reassurance, commitment | Jealousy triggers, avoidance |

**Key Files:**
| File | Line | Purpose |
|------|------|---------|
| `nikita/engine/scoring/calculator.py` | 30-100 | Score delta calculation |
| `nikita/engine/scoring/analyzer.py` | 1-80 | Response analysis |
| `nikita/engine/constants.py` | 20-50 | Metric weights |

### Engagement States

The engagement model tracks player behavior:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        ENGAGEMENT STATE MACHINE                               │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                         ┌─────────────────┐                                  │
│                         │   CALIBRATING   │ (First 5 conversations)          │
│                         └────────┬────────┘                                  │
│                                  │                                           │
│                                  ▼                                           │
│                         ┌─────────────────┐                                  │
│                         │    IN_ZONE      │ (Ideal engagement)               │
│                         └────────┬────────┘                                  │
│                    ┌─────────────┼─────────────┐                             │
│                    │             │             │                              │
│                    ▼             │             ▼                              │
│           ┌──────────────┐      │      ┌──────────────┐                      │
│           │   DRIFTING   │      │      │    CLINGY    │                      │
│           │ (Too passive)│      │      │ (Too active) │                      │
│           └──────┬───────┘      │      └──────┬───────┘                      │
│                  │              │              │                              │
│                  ▼              │              ▼                              │
│           ┌──────────────┐      │      ┌──────────────┐                      │
│           │   DISTANT    │      │      │  OUT_OF_ZONE │                      │
│           │(Very passive)│      │      │ (Any extreme)│                      │
│           └──────────────┘      │      └──────────────┘                      │
│                                 │                                            │
│                                 ▼                                            │
│                    Recovery paths back to IN_ZONE                            │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Key Files:**
| File | Line | Purpose |
|------|------|---------|
| `nikita/engine/engagement/state_machine.py` | 1-150 | State transitions |
| `nikita/engine/engagement/calculator.py` | 1-100 | State calculation |
| `nikita/db/models/user.py` | 100-150 | Engagement state storage |

---

## Phase 4: Chapter Progression

### Chapter Thresholds

| Chapter | Threshold | Unlock |
|---------|-----------|--------|
| 1 | 55% | Initial chapter |
| 2 | 60% | After Ch1 boss |
| 3 | 65% | After Ch2 boss |
| 4 | 70% | After Ch3 boss |
| 5 | 75% | After Ch4 boss |

### Boss Fight Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           BOSS FIGHT FLOW                                     │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Score crosses chapter threshold (e.g., 55% for Ch1)                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  BossEncounter.trigger() @ boss_encounter.py:50-100                 │   │
│  │  - Sets user.in_boss_fight = True                                   │   │
│  │  - Generates boss scenario (jealousy test, commitment test, etc.)   │   │
│  │  - Nikita presents the challenge                                    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Player responds to boss challenge                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  BossJudgment.evaluate() @ boss_judgment.py:30-100                  │   │
│  │  - LLM evaluates player response                                    │   │
│  │  - Returns PASS, PARTIAL, or FAIL                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         ├──── PASS ────▶ Advance to next chapter                            │
│         │                                                                    │
│         ├──── PARTIAL ──▶ Stay in chapter, retry available                  │
│         │                                                                    │
│         └──── FAIL ────▶ Score penalty, retry available                     │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Key Files:**
| File | Line | Purpose |
|------|------|---------|
| `nikita/engine/chapters/boss_encounter.py` | 1-150 | Boss trigger logic |
| `nikita/engine/chapters/boss_judgment.py` | 1-100 | Response evaluation |
| `nikita/engine/chapters/state_machine.py` | 1-150 | Chapter transitions |

---

## Phase 5: Decay System

### Decay Mechanics

When players are inactive, relationship decays:

| Chapter | Decay Rate | Grace Period |
|---------|------------|--------------|
| 1 | 0.8/hour | 8 hours |
| 2 | 0.6/hour | 16 hours |
| 3 | 0.4/hour | 24 hours |
| 4 | 0.3/hour | 48 hours |
| 5 | 0.2/hour | 72 hours |

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           DECAY SYSTEM                                        │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐                                                        │
│  │ pg_cron job     │  Runs every hour                                       │
│  │ POST /tasks/decay                                                        │
│  └────────┬────────┘                                                        │
│           │                                                                  │
│           ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  DecayProcessor.process_all() @ decay_processor.py:30-80            │   │
│  │  - Get all users with last_interaction > grace_period               │   │
│  │  - Calculate decay based on chapter                                 │   │
│  │  - Apply decay to relationship_score                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│           │                                                                  │
│           ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Check for game over condition                                       │   │
│  │  - If relationship_score <= 0 → GAME OVER                           │   │
│  │  - User.chapter_number = 6 (game over state)                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Key Files:**
| File | Line | Purpose |
|------|------|---------|
| `nikita/engine/decay/calculator.py` | 1-80 | Decay calculation |
| `nikita/engine/decay/processor.py` | 1-100 | Batch decay processing |
| `nikita/api/routes/tasks.py` | 100-150 | Decay endpoint |

---

## Phase 6: Game Over

### Game Over Conditions

1. **Decay to Zero** - Relationship score decays to 0%
2. **Failed Boss Fight** - Multiple boss failures (implementation varies)
3. **Manual Trigger** - Admin intervention (rare)

### Game Over Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           GAME OVER FLOW                                      │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Game over condition triggered                                       │   │
│  │  - User.chapter_number = 6                                          │   │
│  │  - User.game_over_at = now()                                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│           │                                                                  │
│           ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Nikita's Breakup Message                                           │   │
│  │  - Pre-canned response based on breakup reason                      │   │
│  │  - Emotional closure for player                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│           │                                                                  │
│           ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Future messages blocked                                             │   │
│  │  - MessageHandler.handle_message() checks game_over state           │   │
│  │  - Returns pre-canned "we broke up" message                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│           │                                                                  │
│           ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  (Future) Restart option?                                           │   │
│  │  - Reset game state                                                 │   │
│  │  - Keep memory graph?                                               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Key Files:**
| File | Line | Purpose |
|------|------|---------|
| `nikita/platforms/telegram/message_handler.py` | 80-100 | Game over check |
| `nikita/db/models/user.py` | 50-80 | Game over state |

---

## Voice vs Text Paths

### Key Differences

| Aspect | Text (Telegram) | Voice (ElevenLabs) |
|--------|-----------------|-------------------|
| Context Source | ContextEngine (8 collectors) | server_tools.py (direct queries) |
| Timeout | 45s total | 2s per tool call |
| Prompt Assembly | PromptGenerator | ElevenLabs agent config |
| Post-Processing | Full 11-stage pipeline | Limited (via webhook) |
| Memory Update | Via pipeline | Via `update_memory` tool |

### NEEDS RETHINKING

**Voice-Text Parity Gap**: Voice bypasses ContextEngine entirely, leading to different context quality. See [VOICE_IMPLEMENTATION.md](VOICE_IMPLEMENTATION.md) for details.

---

## Related Documentation

- **Onboarding Details**: [ONBOARDING.md](ONBOARDING.md)
- **Game Mechanics**: [GAME_ENGINE_MECHANICS.md](GAME_ENGINE_MECHANICS.md)
- **Context Assembly**: [CONTEXT_ENGINE.md](CONTEXT_ENGINE.md)
- **Voice Specifics**: [VOICE_IMPLEMENTATION.md](VOICE_IMPLEMENTATION.md)

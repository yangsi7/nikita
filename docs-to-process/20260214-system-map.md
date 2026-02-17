# System Maps — Nikita Repository

**Date**: 2026-02-14
**Source**: tot-mapper agent, verified against source code
**Notation**: `→` dependency, `⊕` parallel, `∘` sequential, `⇄` bidirectional, `∥` concurrent, `≫` transform, `⊗` GAP/ISSUE, `⊙` integration point

---

## 1. System Architecture Hierarchy

```
NIKITA SYSTEM
├── [BACKEND] nikita/ (Python — Cloud Run: us-central1)
│   ├── api/routes/ [FastAPI]
│   │   ├── telegram.py  → /api/v1/telegram/*
│   │   ├── voice.py     → /api/v1/voice/*
│   │   ├── tasks.py     → /api/v1/tasks/*
│   │   ├── portal.py    → /api/v1/portal/*
│   │   ├── admin.py     → /api/v1/admin/*
│   │   ├── admin_debug.py → /admin/debug/*
│   │   └── onboarding.py → /api/v1/onboarding/*
│   ├── agents/
│   │   ├── text/ [Pydantic AI + Claude Sonnet 4.5]
│   │   └── voice/ [ElevenLabs Conversational AI 2.0]
│   ├── pipeline/ [9-Stage Unified Post-Processing]
│   │   ├── orchestrator.py [sequential, savepoints]
│   │   └── stages/ [extraction, memory_update, life_sim, emotional,
│   │                 game_state, conflict, touchpoint, summary, prompt_builder]
│   ├── engine/ [Game Mechanics]
│   │   ├── scoring/, chapters/, decay/, engagement/, vice/
│   │   └── conflicts/ ⊗ BreakupManager NOT WIRED
│   ├── db/ [Supabase PostgreSQL + pgVector]
│   │   ├── models/ (22 models)
│   │   └── repositories/ (21 repos)
│   ├── memory/ [SupabaseMemory — pgVector]
│   ├── platforms/telegram/ [Bot integration]
│   ├── humanization/ [emotional, life_sim, text_patterns, touchpoints]
│   ├── context/ [session detection, validation]
│   └── config/ [Settings, YAML loaders]
│
├── [FRONTEND] portal/ (Next.js 16 — Vercel)
│   ├── dashboard/ [19 player-facing routes]
│   ├── admin/ [9 admin routes]
│   └── 31 shadcn/ui components
│
└── [EXTERNAL]
    ├── Supabase ⇄ db/ [PostgreSQL + pgVector + RLS + Auth]
    ├── ElevenLabs ⇄ agents/voice/ [Conversational AI 2.0]
    ├── Twilio → agents/voice/inbound.py [Phone]
    ├── Telegram Bot API ⇄ platforms/telegram/
    ├── Anthropic → agents/text/ [Claude Sonnet 4.5]
    ├── Cloud Run → api/ [serverless, scale to zero]
    ├── Vercel → portal/ [Next.js hosting]
    └── pg_cron → /tasks/* [8 scheduled jobs]
```

---

## 2. Data Flow: Text Message

```
[Telegram User]
  ∘ POST /telegram/webhook (HMAC sig check)
  ∘ CommandHandler.route() → /start | /help | /status | text
  ∘ [AUTH] user_repository.get_by_telegram_id()
  ∘ [ONBOARDING GATE] check onboarding_status
  ∘ [GAME STATUS GATE]
    ├── boss_fight → _handle_boss_response() [BRANCH A]
    ├── game_over/won → canned response [STOP]
    └── active → continue
  ∘ [RATE LIMIT] 20/min, 500/day
  ∘ [CONVERSATION] get_or_create + append_message
  ∘ [LLM] text_agent_handler.handle() → Claude Sonnet 4.5
  ∘ [SCORING] ScoringService → metric deltas → boss threshold check
  ∘ [ENGAGEMENT] state machine update → point_of_no_return check
  ∘ [TEXT PATTERNS] emoji, length, punctuation
  ∘ [DELIVERY] response_delivery.queue(delay)
  ∘ [POST-PROCESSING] pg_cron → pipeline 9 stages (async, 15min stale)

[BRANCH A: BOSS]
  ∘ BossJudgment.judge_boss_outcome() [LLM]
  ∘ BossStateMachine.process_outcome()
    ⊗ CRASHES: UserRepository() no session (BUG-BOSS-1)
```

---

## 3. Data Flow: Voice Call

```
[Phone/Portal]
  ∘ ElevenLabs signed URL or Twilio → inbound handler
  ∘ [DURING CALL] server tools: get_context, get_memory, score_turn, update_memory
  ∘ [CALL ENDS] webhook → create conversation(platform="voice")
  ∘ [SCORING] VoiceCallScorer → transcript analysis
  ∘ [PIPELINE] inline PipelineOrchestrator.process() (9 stages)
  ∘ [BACKUP] pg_cron process-conversations picks up missed voice convos

Voice vs Text gaps (by design):
  - No boss encounter trigger
  - No engagement state update
  - No rate limiting (availability-based instead)
```

---

## 4. Data Flow: Background Tasks (pg_cron)

```
pg_cron → POST /tasks/{job} (Bearer: TELEGRAM_WEBHOOK_SECRET)

├── [HOURLY] /tasks/decay → DecayProcessor → score -= decay_rate
│   Skips: boss_fight, game_over, won
│   Triggers: game_over if score <= 0
├── [1 MIN] /tasks/deliver → ScheduledEventRepository → Telegram send
├── [DAILY] /tasks/summary → LLM daily summaries per user
├── [HOURLY] /tasks/cleanup → expired pending registrations
├── [1 MIN] /tasks/process-conversations → stale session → pipeline
├── [5 MIN] /tasks/touchpoints → proactive message delivery
├── [10 MIN] /tasks/detect-stuck → mark stuck conversations as failed
└── [10 MIN] /tasks/recover-stuck → retry failed conversations
```

---

## 5. Game Lifecycle Tree

```
signup → onboarding → ACTIVE
  │
  ├── Chapters 1-5 (boss thresholds: 55, 60, 65, 70, 75)
  │   └── Boss encounter → ⊗ CRASHES (BUG-BOSS-1)
  │       └── ⊗ NO TIMEOUT — stuck forever
  │
  ├── Game-Over paths:
  │   ├── Score decay to 0 (pg_cron hourly) ✓ WORKS
  │   ├── Boss fail 3x → ⊗ CRASHES (BUG-BOSS-1)
  │   ├── Engagement (7d clingy/10d distant) → ⊗ SILENT FAIL (BACK-01)
  │   └── Conflict breakup → ⊗ NOT WIRED (dead code)
  │
  ├── Won (chapter 5 pass) → ⊗ CRASHES (BUG-BOSS-1)
  │
  └── Restart: /start → reset_game_state() ✓ WORKS
```

---

## 6. Database Entity Relationship Tree

```
User [users] ─── PRIMARY ENTITY (22 columns)
├── [1:1] UserMetrics (intimacy, passion, trust, secureness)
├── [1:1] EngagementState (6-state FSM)
├── [1:1] UserProfile (name, age, location)
├── [1:1] UserBackstory (LLM-generated)
├── [1:N] Conversation (text/voice, messages JSONB)
│   └── [1:N] MessageEmbedding (Vector 1536)
├── [1:N] ScoreHistory (conversation/decay/boss/manual)
├── [1:N] DailySummary (per-day LLM summary)
├── [1:N] ConversationThread (open/resolved)
├── [1:N] NikitaThought (per-conversation)
├── [1:N] EngagementHistory (state transitions)
├── [1:N] GeneratedPrompt (text/voice)
├── [1:N] UserVicePreference (8 categories)
├── [1:N] ScheduledEvent (pending deliveries)
├── [1:N] ScheduledTouchpoint (proactive msgs)
├── [1:N] UserSocialCircle (entity relationships)
├── [1:N] UserNarrativeArc (story arcs)
├── [1:N] MemoryFact (pgVector embeddings)
└── [1:N] ReadyPrompt (pre-built prompts)

Standalone: PendingRegistration, RateLimit, JobExecution, ErrorLog, AuditLog

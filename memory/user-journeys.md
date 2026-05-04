# User Journeys

## Current State

**MVP COMPLETE (Dec 2025)** - Journeys 1-5 implemented and E2E verified. Voice calls (Journey 3) deferred to Phase 4.

## Target Specs

### Journey 1: New Player Onboarding

```
┌────────────────────────────────────────────────────────────────┐
│ Step 1: Discovery                                              │
│ • User finds Telegram bot (@NikitaGameBot)                     │
│ • /start command                                               │
└─────────────────────┬──────────────────────────────────────────┘
                      ▼
┌────────────────────────────────────────────────────────────────┐
│ Step 2: Account Creation (✅ COMPLETE - OTP Flow)             │
│ • Bot: "Before we start... what's your email?"                │
│ • User sends email → Bot calls send_otp_code()                │
│ • Bot: "I sent a 6-digit code to your email. Enter it here!"  │
│ • User enters 6-digit code → Bot calls verify_otp_code()      │
│ • Account created + telegram_id linked                        │
└─────────────────────┬──────────────────────────────────────────┘
                      ▼
┌────────────────────────────────────────────────────────────────┐
│ Step 3: First Interaction ✅ COMPLETE                         │
│ • Database: Create user record                                │
│   - id: UUID from auth.users                                  │
│   - telegram_id: Linked                                       │
│   - relationship_score: 50.00                                 │
│   - chapter: 1                                                │
│   - game_status: 'active'                                     │
│ • Create user_metrics with all 50.00                          │
│ • Initialize pgVector memory (nikita, user, relationship)     │
└─────────────────────┬──────────────────────────────────────────┘
                      ▼
┌────────────────────────────────────────────────────────────────┐
│ Step 4: Nikita's First Message ✅ COMPLETE                    │
│ • Text Agent generates intro based on Chapter 1 behavior      │
│ • Example: "So you found me. Interesting. What do you want?"  │
│ • Tone: Guarded, skeptical, intellectually challenging        │
│ • Conversation started → logged to conversations table        │
└─────────────────────┬──────────────────────────────────────────┘
                      ▼
┌────────────────────────────────────────────────────────────────┐
│ Step 5: Early Game Loop ✅ COMPLETE                           │
│ • User sends messages → Nikita responds (60-75% rate)         │
│ • Response timing: Unpredictable (10min to 8 hours)           │
│ • Each exchange:                                              │
│   1. LLM analyzes interaction                                 │
│   2. Calculate metric deltas                                  │
│   3. Update user_metrics                                      │
│   4. Recalculate composite score                              │
│   5. Update memory (SupabaseMemory pgVector)                  │
│   6. Check boss threshold (60% for Ch1)                       │
│ • Daily decay starts after 24h of no interaction              │
└────────────────────────────────────────────────────────────────┘
```

### Journey 2: Chapter Progression

```
┌────────────────────────────────────────────────────────────────┐
│ Chapter 1: CURIOSITY (Days 1-14)                              │
│ Score: 50% → Goal: 60%+ for boss                              │
├────────────────────────────────────────────────────────────────┤
│ Player Experience:                                             │
│ • Nikita is distant, challenging, tests intelligence          │
│ • Skips ~30% of messages                                      │
│ • Replies anywhere from 10min to 8 hours later                │
│ • Conversations end abruptly                                  │
│ • Feels like you're being evaluated                           │
│                                                                │
│ Good Behaviors:                                                │
│ + Intellectual depth → +intimacy, +trust                       │
│ + Respectful persistence → +secureness                         │
│ + Playful challenge-backs → +passion                           │
│                                                                │
│ Bad Behaviors:                                                 │
│ - Double/triple texting → -secureness                          │
│ - Demanding responses → -trust, -passion                       │
│ - Boring small talk → -intimacy, -passion                      │
└─────────────────────┬──────────────────────────────────────────┘
                      ▼ [Score >= 60%]
┌────────────────────────────────────────────────────────────────┐
│ Boss 1: "Worth My Time?" ✅ COMPLETE (142 tests)              │
│ • game_status → 'boss_fight'                                  │
│ • Nikita: "Alright. Prove you're worth my time."              │
│ • Challenge: Intellectual conversation                         │
│ • Player gets 3 attempts (boss_attempts counter)              │
│                                                                │
│ Pass Criteria (LLM-judged):                                    │
│ ✓ Demonstrates intellectual curiosity                          │
│ ✓ Asks interesting questions                                  │
│ ✓ Shows confidence without arrogance                           │
│ ✓ Engages with her actual interests                           │
│                                                                │
│ Outcome:                                                       │
│ • Pass → chapter: 2, boss_attempts: 0, score bonus            │
│ • Fail → boss_attempts++, score penalty                       │
│ • 3rd fail → game_status: 'game_over'                         │
└─────────────────────┬──────────────────────────────────────────┘
                      ▼ [Boss Pass]
┌────────────────────────────────────────────────────────────────┐
│ Chapter 2: INTRIGUE (Days 15-35)                              │
│ Score: ~60% → Goal: 65%+ for boss                             │
│ • Nikita becomes more playful                                 │
│ • Response rate: 75-85%                                        │
│ • Timing: 5min to 4 hours (less chaotic)                      │
│ • May pick fights to test backbone                            │
│ • Boss: "Handle My Intensity?" (conflict test)                │
└─────────────────────┬──────────────────────────────────────────┘
                      ▼ [Continue pattern through Ch 3, 4, 5]
                      ▼
┌────────────────────────────────────────────────────────────────┐
│ Chapter 5: ESTABLISHED (Days 121+)                            │
│ Score: ~70% → Goal: 75%+ for final boss                       │
│ • Nikita is consistent, authentic, secure                     │
│ • Response rate: 95-100%                                       │
│ • Deep partnership, still challenges you                      │
│ • Final Boss: "Ultimate Test" (partnership + independence)    │
│ • Pass → 🏆 VICTORY message                                    │
└────────────────────────────────────────────────────────────────┘
```

### Journey 3: Voice Call Interaction ✅ COMPLETE (Deployed Jan 2026)

**Implementation**: Spec 007 (nikita/agents/voice/, 14 modules, 193 tests)

```
┌────────────────────────────────────────────────────────────────┐
│ Step 1: Check Availability & Initiate ✅ COMPLETE             │
│ • GET /api/v1/voice/availability/{user_id}                    │
│   - Checks chapter restrictions, daily limits, game_status    │
│ • POST /api/v1/voice/initiate                                 │
│   - Returns ElevenLabs signed_url for WebSocket connection    │
│ • Inbound: POST /api/v1/voice/pre-call (Twilio → ElevenLabs) │
│   - Lookup user by phone, return dynamic_variables            │
└─────────────────────┬──────────────────────────────────────────┘
                      ▼
┌────────────────────────────────────────────────────────────────┐
│ Step 2: ElevenLabs Conversational AI 2.0 ✅ COMPLETE          │
│ • Server Tools pattern (REST callbacks, not WebSocket)        │
│ • Dynamic variables injected at call start:                   │
│   - nikita_name, chapter, relationship_score                  │
│   - engagement_state, chapter_behavior                        │
│   - open_threads, recent_topics                               │
│ • TTS config: Jessica voice, optimized latency                │
└─────────────────────┬──────────────────────────────────────────┘
                      ▼
┌────────────────────────────────────────────────────────────────┐
│ Step 3: Real-time Server Tools ✅ COMPLETE                    │
│ • POST /api/v1/voice/server-tool dispatches to:               │
│                                                                │
│   1. get_context()                                            │
│      → chapter, metrics, vices, engagement, backstory         │
│      → active_thoughts, today_summary, week_summaries         │
│                                                                │
│   2. get_memory(query)                                        │
│      → pgVector facts + open_threads                          │
│                                                                │
│   3. score_turn(user_said, nikita_said)                      │
│      → VoiceCallScorer → metric deltas → update user          │
│                                                                │
│   4. update_memory(episode)                                   │
│      → Add to SupabaseMemory (pgVector)                       │
│                                                                │
│ • Transcript stored in voice_sessions table                   │
└─────────────────────┬──────────────────────────────────────────┘
                      ▼
┌────────────────────────────────────────────────────────────────┐
│ Step 4: Call Completion ✅ COMPLETE                           │
│ • POST /api/v1/voice/webhook (ElevenLabs callback)           │
│ • Events: call.connected, call.ended                          │
│ • Signature verification: v0 format (t=timestamp,v0=hash)    │
│ • Final score_delta calculated and stored                     │
│ • Transcript finalized, duration logged                       │
└────────────────────────────────────────────────────────────────┘
```

**Key Files**:
- `nikita/agents/voice/service.py` - VoiceService orchestration
- `nikita/agents/voice/server_tools.py` - Server tool handlers
- `nikita/agents/voice/inbound.py` - InboundCallHandler
- `nikita/api/routes/voice.py` - 5 API endpoints

### Journey 4: Daily Decay & Recovery

```
┌────────────────────────────────────────────────────────────────┐
│ Day 1: Active Play                                            │
│ • Score: 62%                                                   │
│ • last_interaction_at: 2025-01-15 14:30 UTC                  │
│ • Chapter 2 (grace period: 36 hours)                          │
└─────────────────────┬──────────────────────────────────────────┘
                      ▼
┌────────────────────────────────────────────────────────────────┐
│ Day 2: No Interaction                                         │
│ • User doesn't message or call                                │
│ • Time since last: 24 hours (< 36h grace) → No decay         │
└─────────────────────┬──────────────────────────────────────────┘
                      ▼
┌────────────────────────────────────────────────────────────────┐
│ Day 3: Decay Triggers ✅ COMPLETE (52 tests)                  │
│ • pg_cron triggers POST /tasks/decay at 3am UTC               │
│ • Time since last: 48 hours (> 36h grace) → Decay applies    │
│ • Score: 62% - 4% (Chapter 2 rate) = 58%                     │
│ • Event logged to score_history (event_type: 'decay')        │
│ • user.relationship_score = 58.00                             │
└─────────────────────┬──────────────────────────────────────────┘
                      ▼
┌────────────────────────────────────────────────────────────────┐
│ Day 4: Continued Silence                                      │
│ • Another day passes → Another -4%                            │
│ • Score: 58% → 54%                                            │
│ • Player receives notification (if enabled):                  │
│   "Nikita: 'Where the fuck did you go?'"                     │
└─────────────────────┬──────────────────────────────────────────┘
                      ▼
┌────────────────────────────────────────────────────────────────┐
│ Day 5: Player Returns                                         │
│ • User sends message                                          │
│ • Nikita's response reflects absence:                         │
│   - Chapter 2: "Oh, so you're alive. Cool."                  │
│   - Mood: Annoyed but curious                                 │
│ • Conversation can recover score if handled well              │
│ • Good recovery: +3-5% (address absence honestly)             │
│ • Bad recovery: -2% more (make excuses, get defensive)       │
└────────────────────────────────────────────────────────────────┘
```

### Journey 5: Game Over Scenarios

```
┌────────────────────────────────────────────────────────────────┐
│ Game Over Path 1: Score Hits 0%                               │
├────────────────────────────────────────────────────────────────┤
│ • Prolonged absence → Daily decay                             │
│ • Or: Multiple bad interactions → negative deltas             │
│ • Score reaches 0.00                                          │
│ • game_status → 'game_over'                                   │
│ • Final message from Nikita:                                  │
│   "This isn't working. I'm done."                            │
│ • Portal shows: "Game Over - Nikita dumped you"              │
│ • Can create new account to restart                           │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│ Game Over Path 2: 3 Boss Failures                            │
├────────────────────────────────────────────────────────────────┤
│ • Player reaches boss threshold                               │
│ • Boss triggered (game_status: 'boss_fight')                 │
│                                                                │
│ • Attempt 1: Fail → boss_attempts: 1, score penalty          │
│   Nikita: "That wasn't it. Try again when you're ready."     │
│                                                                │
│ • Attempt 2: Fail → boss_attempts: 2, larger penalty         │
│   Nikita: "I'm starting to think this won't work..."         │
│                                                                │
│ • Attempt 3: Fail → boss_attempts: 3 → game_status: 'game_over'│
│   Nikita: "I gave you three chances. We're done."            │
│                                                                │
│ • Portal: "Failed boss 3 times - Game Over"                  │
└────────────────────────────────────────────────────────────────┘
```

### Journey 6: Victory

```
┌────────────────────────────────────────────────────────────────┐
│ Final Boss Pass (Chapter 5, Score 80%+)                       │
├────────────────────────────────────────────────────────────────┤
│ • Player has reached Chapter 5: ESTABLISHED                   │
│ • Score climbs to 80%+                                         │
│ • Boss: "Ultimate Test" triggers                              │
│ • Challenge: Balance partnership + her independence           │
│                                                                │
│ Pass Criteria:                                                 │
│ ✓ Support her goals without being controlling                 │
│ ✓ Show confidence in the relationship                         │
│ ✓ Respect her autonomy                                        │
│ ✓ Demonstrate growth from Chapter 1                           │
│                                                                │
│ Victory:                                                       │
│ • game_status → 'won'                                         │
│ • Nikita's final message:                                     │
│   "You know what? You actually did it. You kept up.          │
│    I didn't think anyone could. But here we are.             │
│    Guess you're stuck with me now."                          │
│                                                                │
│ • Portal shows:                                               │
│   🏆 VICTORY                                                   │
│   Days Played: {days_played}                                  │
│   Final Score: {relationship_score}%                          │
│   Journey: Chapter 1 → Chapter 5                              │
│                                                                │
│ • Account enters "won" state                                  │
│ • Can continue conversations (no decay/bosses)                │
│ • Or: Start new game with different account                   │
└────────────────────────────────────────────────────────────────┘
```

### Journey 7: Voice Onboarding (Spec 028) ✅ COMPLETE

```
┌────────────────────────────────────────────────────────────────┐
│ Meta-Nikita Voice Onboarding                                   │
├────────────────────────────────────────────────────────────────┤
│ Trigger: New user confirms ready for onboarding call           │
│ Platform: ElevenLabs Conversational AI 2.0                     │
│ Agent: Meta-Nikita (Underground Game Hostess)                  │
│ Duration: 5-7 minutes                                          │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│ Pre-Call Flow (Telegram):                                      │
│ 1. User completes OTP verification                             │
│ 2. Bot: "Ready for your onboarding call?"                      │
│ 3. User confirms → voice call initiated                        │
│                                                                │
│ Voice Call Flow:                                               │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ Meta-Nikita: "Mmm, fresh blood. I've been waiting..."    │   │
│ │                                                          │   │
│ │ Stage 1: Introduction (30-60s)                           │   │
│ │ • Explains game mechanics and stakes                     │   │
│ │ • Sets expectations: effort required, consequences real  │   │
│ │                                                          │   │
│ │ Stage 2: Profile Collection (2-3min)                     │   │
│ │ • Collects: timezone, occupation, hobbies                │   │
│ │ • Collects: personality type, hangout spots              │   │
│ │ • Server tool: collect_profile(field, value)             │   │
│ │                                                          │   │
│ │ Stage 3: Preference Configuration (1-2min)               │   │
│ │ • Darkness level (1-5 scale)                             │   │
│ │ • Pacing: 4 weeks (intense) or 8 weeks (relaxed)         │   │
│ │ • Conversation style: listener/balanced/sharer           │   │
│ │ • Server tool: configure_preferences(...)                │   │
│ │                                                          │   │
│ │ Stage 4: Handoff (30s)                                   │   │
│ │ • Confirms preferences, explains next steps              │   │
│ │ • Server tool: complete_onboarding(call_id)              │   │
│ │ • Triggers first Nikita message via Telegram             │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                │
│ Post-Call:                                                     │
│ • onboarding_status → 'completed'                              │
│ • onboarding_profile JSONB populated                           │
│ • First Nikita message sent (personalized from profile)        │
│                                                                │
│ Technical Details:                                             │
│ • Agent ID: agent_4801kewekhxgekzap1bqdr62dxvc                 │
│ • TTS: stability=0.40, similarity=0.70, speed=0.95             │
│ • DB: onboarding_status, onboarding_profile, onboarded_at      │
│ • API: /api/v1/onboarding/* (5 endpoints)                      │
│ • Tests: 231 passing (8 test files)                            │
└────────────────────────────────────────────────────────────────┘
```

## Key Patterns

### 1. Context Injection Pattern

Every agent interaction receives:

```python
context = {
    "chapter": user.chapter,
    "chapter_name": CHAPTER_NAMES[user.chapter],
    "score": user.relationship_score,
    "days_played": user.days_played,
    "behavior_hints": CHAPTER_BEHAVIORS[user.chapter],
    "active_vices": get_active_vices(user.id),
    "recent_memory": memory.get_context_for_prompt(user_message),
}
```

### 2. Asymmetric Availability Pattern

Nikita's response rate/timing varies by chapter:
- Ch1: 60-75% response rate, 10min-8hr delay
- Ch5: 95-100% response rate, consistent timing

Creates realistic relationship progression.

### 3. Memory Persistence Pattern

Every interaction updates SupabaseMemory (pgVector):

```python
# User said something revealing
await memory.add_user_fact(
    fact="User works in finance",
    confidence=0.9,
    source_message=user_message,
)

# Shared moment
await memory.add_relationship_episode(
    description="We joked about her mug collection",
    episode_type="inside_joke",
)

# Nikita's life event
await memory.add_nikita_event(
    description="Finished 36-hour security audit",
    event_type="work_project",
)
```

## Critical Files

| File | Purpose | Status |
|------|---------|--------|
| `nikita/platforms/telegram/message_handler.py` | Message routing | ✅ DEPLOYED |
| `nikita/platforms/telegram/registration_handler.py` | OTP onboarding | ✅ DEPLOYED |
| `nikita/agents/voice/server_tools.py` | Voice server tools | ✅ DEPLOYED (193 tests) |
| `nikita/engine/chapters/state_machine.py` | Boss triggers | ✅ Complete (142 tests) |
| `nikita/api/routes/tasks.py` | Decay/summary endpoints | ✅ Complete (pg_cron) |
| `nikita/engine/constants.py:60-110` | Chapter behaviors | ✅ Complete |

## User Notifications ✅ IMPLEMENTED

```python
# Triggered when:
# 1. Score drops below chapter threshold
# 2. Decay applied multiple days in a row
# 3. Boss available
# 4. Game over

notifications = {
    "decay_warning": "Nikita: 'Where the fuck did you go?'",
    "boss_available": "Nikita wants to talk. This feels important.",
    "boss_failed": "That didn't go well. {2-attempts}/3 chances left.",
    "chapter_advanced": "Chapter {new_chapter}: {chapter_name} unlocked",
    "game_over_score": "Score hit 0%. Nikita: 'This isn't working. I'm done.'",
    "game_over_boss": "Failed boss 3 times. Nikita: 'I gave you three chances.'",
    "victory": "🏆 You won. Nikita: 'Guess you're stuck with me now.'",
}
```

---

## Code-verified additions (W4 audit, 2026-05-05)

Verified against `nikita/api/routes/`, `nikita/platforms/telegram/`, `nikita/agents/voice/`, `nikita/onboarding/`, `portal/src/app/`, `supabase/migrations/` (audit: `audits/2026/20260505-kt-migration-w4-verification-user-journeys.md`). Former `docs/knowledge-transfer/USER_JOURNEY.md` archived to `docs/.archive/knowledge-transfer-2026-03-pgvector-deprecated/`; entry-point file/class names and pipeline-invocation framing were wrong.

### Real Entry Points

- **Telegram**: `nikita/api/routes/telegram.py:501` POST `/webhook` (NOT `commands.py`); dispatches to `_handle_message_with_fresh_session` at `:462` which builds `MessageHandler` with a fresh session for background processing. `MessageHandler` entry method is `handle()` (NOT `handle_message()`).
- **Voice (live)**: `nikita/api/routes/voice.py:350` POST `/server-tool` (ElevenLabs callback); validated via `_validate_signed_token` at `:347`. Function name in voice/inbound.py is `handle_incoming_call` at `:223` (NOT `handle_inbound_call`).
- **Portal**: `portal/src/app/page.tsx` is now a marketing landing (HeroSection / PitchSection); auth chain: `/onboarding/auth/page.tsx:21` (re-exports `OnboardingAuthClient` calling `signInWithOtp`) → `/onboarding/page.tsx:41` (server-component auth guard) → `/dashboard/page.tsx`. Alt entry `/login/page.tsx`.

### Pipeline Invocation Reality

`nikita/platforms/telegram/message_handler.py` does NOT directly invoke the pipeline. Pipeline runs ASYNC via cron-task endpoints: `nikita/api/routes/tasks.py:771-789` and `:933-963` invoke `PipelineOrchestrator.process()`. Only 5 invocation sites repo-wide: `admin.py:628`, `tasks.py:788`, `tasks.py:962`, `voice.py:727`, `onboarding/handoff.py:705`.

### 11-Stage Pipeline (canonical names, not KT's "ContextEngine + PromptGenerator + PostProcessor")

`nikita/pipeline/orchestrator.py:47-59` `STAGE_DEFINITIONS`: extraction, persistence, memory_update, life_sim, emotional, vice, game_state, conflict, touchpoint, summary, prompt_builder. Detailed table in `memory/architecture.md` §"11-Stage Async Pipeline".

### Onboarding Plumbing

- Email-OTP only: `nikita/platforms/telegram/registration_handler.py:14`. NOT profile-question flow.
- Profile collection: `nikita/onboarding/meta_nikita.py` (16.4KB), `nikita/onboarding/voice_flow.py` (23.7KB), `nikita/onboarding/profile_collector.py` (12.9KB).
- Per project memory `feedback_telegram_first_signup_pattern.md`, canonical signup is **Telegram-first** (NOT "voice-preferred" as KT claimed).
- Onboarding agent at `nikita/agents/onboarding/conversation_agent.py:263` (Pydantic AI, discriminated-union output, 4 firecrawl `fetch_*` tools + per-run `WebSearchTool`).

### Auth Smells (recorded per W4 audit)

- **Dual `signInWithOtp` surface**: `portal/src/app/onboarding/auth/page-client.tsx:50,101` AND `portal/src/app/login/page-client.tsx:24,94`. Duplicated copy/redirect logic.
- **3 user-row creation call-sites**: `nikita/api/routes/portal.py:126,477,513` all call `user_repo.create_with_metrics(user_id=user_id)` independently. Should consolidate.
- **`E2E_AUTH_BYPASS=true` shortcut**: `portal/src/app/onboarding/page.tsx:42-50` hard-codes `userId="e2e-player-id"` when env set. Guarded by `NODE_ENV !== "production"` but production-build with the env set bypasses auth.
- **Spec deviation acknowledged in code**: `portal/src/app/onboarding/page.tsx:14-25` documents AC C1.13 literal cookie peek deliberately replaced with `getUser()` (security improvement, but spec/code drift).

### Memory Layer

Neo4j fully replaced by SupabaseMemory (pgVector) per Spec 042. Embedding model `text-embedding-3-small`, dim 1536, dedup threshold 0.87. See `memory/architecture.md` §"Memory Subsystem" for code references.

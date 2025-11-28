# User Journeys

## Current State

**No user-facing implementations yet** - all journeys defined conceptually in plan, awaiting Phases 2-5 implementation.

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
│ Step 2: Account Creation (TODO Phase 2)                       │
│ • Bot: "Before we start... link your account"                 │
│ • Send magic link: portal.nikita.game/auth?telegram_id=...    │
│ • User clicks → Supabase Auth OTP                             │
│ • Enter phone/email → Verify code → Account created           │
└─────────────────────┬──────────────────────────────────────────┘
                      ▼
┌────────────────────────────────────────────────────────────────┐
│ Step 3: First Interaction (TODO Phase 2)                      │
│ • Database: Create user record                                │
│   - id: UUID from auth.users                                  │
│   - telegram_id: Linked                                       │
│   - relationship_score: 50.00                                 │
│   - chapter: 1                                                │
│   - game_status: 'active'                                     │
│ • Create user_metrics with all 50.00                          │
│ • Initialize Graphiti graphs (nikita, user, relationship)     │
└─────────────────────┬──────────────────────────────────────────┘
                      ▼
┌────────────────────────────────────────────────────────────────┐
│ Step 4: Nikita's First Message (TODO Phase 2)                 │
│ • Text Agent generates intro based on Chapter 1 behavior      │
│ • Example: "So you found me. Interesting. What do you want?"  │
│ • Tone: Guarded, skeptical, intellectually challenging        │
│ • Conversation started → logged to conversations table        │
└─────────────────────┬──────────────────────────────────────────┘
                      ▼
┌────────────────────────────────────────────────────────────────┐
│ Step 5: Early Game Loop (TODO Phase 2-3)                      │
│ • User sends messages → Nikita responds (60-75% rate)         │
│ • Response timing: Unpredictable (10min to 8 hours)           │
│ • Each exchange:                                              │
│   1. LLM analyzes interaction                                 │
│   2. Calculate metric deltas                                  │
│   3. Update user_metrics                                      │
│   4. Recalculate composite score                              │
│   5. Update memory graphs (Graphiti)                          │
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
│ Boss 1: "Worth My Time?" (TODO Phase 3)                       │
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
│ Score: ~75% → Goal: 80%+ for final boss                       │
│ • Nikita is consistent, authentic, secure                     │
│ • Response rate: 95-100%                                       │
│ • Deep partnership, still challenges you                      │
│ • Final Boss: "Ultimate Test" (partnership + independence)    │
│ • Pass → 🏆 VICTORY message                                    │
└────────────────────────────────────────────────────────────────┘
```

### Journey 3: Voice Call Interaction

```
┌────────────────────────────────────────────────────────────────┐
│ Step 1: Initiate Call (TODO Phase 4)                          │
│ • User: Telegram bot command /call                            │
│ • Bot: "Calling Nikita..." + phone number or deep link        │
│ • Or: Direct dial to ElevenLabs number                        │
└─────────────────────┬──────────────────────────────────────────┘
                      ▼
┌────────────────────────────────────────────────────────────────┐
│ Step 2: ElevenLabs Agent Connection                           │
│ • WebSocket connection established                            │
│ • Agent ID selected based on:                                 │
│   - user.chapter → chapter-specific voice/mood                │
│   - game_status == 'boss_fight' → boss agent ID              │
│ • Example: Chapter 1 → guarded tone, sparse words            │
│           Chapter 5 → warm, playful, secure tone             │
└─────────────────────┬──────────────────────────────────────────┘
                      ▼
┌────────────────────────────────────────────────────────────────┐
│ Step 3: Real-time Conversation (TODO Phase 4)                 │
│ • User speaks → ElevenLabs transcribes                        │
│ • Agent calls server tools via callbacks:                     │
│                                                                │
│   1. get_context()                                            │
│      → Returns: chapter, score, vice_prefs, behavior_hints    │
│                                                                │
│   2. get_memory(query="recent conversations")                │
│      → Graphiti search → Returns: relevant facts              │
│                                                                │
│   3. Agent generates response (uses context + memory)         │
│                                                                │
│   4. score_turn(user_said, nikita_said)                      │
│      → Analyze interaction → Update metrics                   │
│                                                                │
│   5. update_memory(episode="User mentioned...")              │
│      → Add to Graphiti graphs                                 │
│                                                                │
│ • Voice response played to user (<100ms latency)              │
│ • Transcript logged to conversations table                    │
└─────────────────────┬──────────────────────────────────────────┘
                      ▼
┌────────────────────────────────────────────────────────────────┐
│ Step 4: Call End                                              │
│ • User hangs up or session timeout                            │
│ • Conversation marked ended_at                                │
│ • Final score_delta calculated and logged                     │
│ • Memory episodes finalized                                   │
└────────────────────────────────────────────────────────────────┘
```

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
│ Day 3: Decay Triggers (TODO Phase 3)                          │
│ • Celery task runs at midnight UTC                            │
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

Every interaction updates Graphiti:

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
| `nikita/platforms/telegram/handlers.py` | Message routing | ❌ TODO Phase 2 |
| `nikita/platforms/voice/callbacks.py` | Voice server tools | ❌ TODO Phase 4 |
| `nikita/engine/chapters/state_machine.py` | Boss triggers | ❌ TODO Phase 3 |
| `nikita/tasks/decay_task.py` | Daily decay | ❌ TODO Phase 3 |
| `nikita/engine/constants.py:60-110` | Chapter behaviors | ✅ Complete |

## User Notifications (TODO Phase 2-3)

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

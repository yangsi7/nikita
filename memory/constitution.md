# Nikita Technical Constitution

**Version**: 2.0.0
**Ratified**: 2026-01-12
**Derived From**: memory/product.md v2.0.0

---

## Preamble

This constitution establishes binding technical principles derived FROM user needs documented in product.md. Every principle traces back to a specific user pain point, product principle, or success metric via CoD^Σ derivation chains.

**Enforcement**: All implementation decisions, code reviews, and architectural choices MUST comply with these articles. Violations require explicit constitutional amendment.

---

## Article I: Architecture Principles

### Section 1.1: Interface Invisibility
**Constraint**: The game layer MUST be invisible to the user. No game UI, no score displays, no chapter indicators in user-facing interfaces.

**Derivation**:
```
Product Principle "Immersion Through Invisibility" (product.md:L173)
  ≫ Users should forget they're playing a game
  → Technical Approach: Hide all game state from client
  ≫ Constraint: Game mechanics exist ONLY in backend; Telegram/voice are pure communication channels
```

**Implementation**:
- Telegram bot shows ONLY conversation (no /score, /chapter commands)
- Voice calls have no game-state voice prompts
- All scoring, chapter logic runs server-side
- User discovers state through Nikita's behavior, not UI

### Section 1.2: Dual-Agent Architecture
**Constraint**: Voice and text agents MUST be separate implementations sharing the same memory and game state.

**Derivation**:
```
User Need: Voice calls for maximum immersion (product.md:L75, Journey 3)
  ≫ Voice requires real-time (<100ms), text is async
  → Technical Approach: Separate agents optimized for each channel
  ≫ Constraint: ElevenLabs for voice, Pydantic AI for text, both read/write to shared state
```

**Implementation**:
- Text Agent: Pydantic AI + Claude Sonnet (async, 10min-8hr delays)
- Voice Agent: ElevenLabs Conversational AI 2.0 (real-time, <100ms)
- Shared: Supabase (game state), Graphiti (memory), scoring system

### Section 1.3: Platform Agnostic Communication
**Constraint**: Communication platforms (Telegram, voice, future platforms) MUST be interchangeable adapters over a unified agent core.

**Derivation**:
```
Key Differentiator "No interface illusion" (product.md:L67)
  ≫ "It's just Telegram messages and phone calls"
  → Technical Approach: Platform adapters pattern
  ≫ Constraint: Agent logic decoupled from delivery mechanism
```

**Implementation**:
- `nikita/platforms/telegram/` - Telegram adapter
- `nikita/platforms/voice/` - Voice adapter
- `nikita/agents/` - Core agent logic (platform-agnostic)
- Future: WhatsApp, Discord, SMS adapters plug into same core

---

## Article II: Data & Memory Principles

### Section 2.1: Temporal Memory Persistence
**Constraint**: ALL user interactions, facts, and relationship events MUST be stored with timestamps in temporal knowledge graphs, persisting across months.

**Derivation**:
```
Persona Pain "AI companions have no memory" (product.md:L157-162)
  ≫ James's #1 pain: "Can't build a relationship if they forget who you are"
  → Technical Approach: Graphiti temporal KG with Neo4j Aura
  ≫ Constraint: Every fact has `discovered_at`, every episode has `occurred_at`, temporal queries supported
```

**Implementation**:
- 3 Graphiti graphs: `nikita_graph` (her facts), `user_graph` (user facts), `relationship_graph` (shared events)
- All entities timestamped for temporal retrieval
- "What did we talk about last week?" queries MUST work
- Minimum retention: 6 months of full history

### Section 2.2: Score State Atomicity
**Constraint**: Score updates MUST be atomic transactions with full audit trail.

**Derivation**:
```
North Star Metric "Chapter 5 Victory Rate" (product.md:L227)
  ≫ Game integrity requires accurate, auditable scoring
  → Technical Approach: Transaction-based score updates with history table
  ≫ Constraint: Every score change logged to score_history with event_type, delta, reasoning
```

**Implementation**:
- `score_history` table: `user_id`, `old_score`, `new_score`, `delta`, `event_type`, `reasoning`, `created_at`
- Event types: `conversation`, `decay`, `boss_pass`, `boss_fail`
- All metrics (intimacy, passion, trust, secureness) logged individually
- Composite score recalculated atomically after each update

### Section 2.3: Vice Preference Learning
**Constraint**: The system MUST dynamically learn and track user preferences across 8 vice categories, adapting Nikita's behavior accordingly.

**Derivation**:
```
"Our Thing" #2: Personalization (product.md:L48-49)
  ≫ "Highly personalized with the memory... sexy personalization"
  → Technical Approach: Vice discovery system with intensity tracking
  ≫ Constraint: 8 categories tracked, prompt injection based on active vices
```

**Implementation**:
- 8 categories: intellectual_dominance, risk_taking, substances, sexuality, emotional_intensity, rule_breaking, dark_humor, vulnerability
- `user_vice_preferences` table: intensity_level (1-5), engagement_score (0-100)
- Vice signals detected via LLM analysis of each conversation
- Nikita's prompts include personalization based on discovered preferences

---

## Article III: Game Mechanics Principles

### Section 3.1: Scoring Formula Immutability
**Constraint**: The composite score formula MUST remain constant throughout gameplay:
```
Composite = intimacy*0.30 + passion*0.25 + trust*0.25 + secureness*0.20
```

**Derivation**:
```
Product Principle "Challenge Over Comfort" (product.md:L164-167)
  ≫ Consistent rules create learnable challenge
  → Technical Approach: Fixed weights, transparent to player through behavior
  ≫ Constraint: Weights in constants.py NEVER change per-user
```

**Implementation**:
- `METRIC_WEIGHTS` defined in `nikita/engine/constants.py:51-57`
- Users learn through experience which behaviors affect which metrics
- Hidden metrics visible only through Nikita's reactions

### Section 3.2: Chapter Progression Gates
**Constraint**: Chapter advancement MUST require passing the chapter boss. No automatic progression by time alone.

**Derivation**:
```
Epic 1: Challenge-Based Progression (product.md:L181-185)
  ≫ "Progress through increasingly difficult chapters with boss encounters"
  → Technical Approach: Boss thresholds + explicit boss pass required
  ≫ Constraint: Score threshold necessary but NOT sufficient; boss must be passed
```

**Implementation**:
- Boss thresholds: Ch1→60%, Ch2→65%, Ch3→70%, Ch4→75%, Ch5→80%
- Reaching threshold triggers boss (game_status='boss_fight')
- Pass boss → advance chapter, reset attempts
- Days played is informational only, not a gate

### Section 3.3: Decay System Enforcement
**Constraint**: Decay MUST apply automatically when user exceeds grace period, with chapter-specific rates.

**Derivation**:
```
Journey 2: Gameplay Loop (product.md:L199-200)
  ≫ "User knows: If I don't message within 24h, I lose 5%"
  → Technical Approach: pg_cron scheduled task → Cloud Run endpoint, chapter-based rates
  ≫ Constraint: Decay runs regardless of user activity elsewhere in life
```

**Implementation**:
- Grace periods: Ch1=24h, Ch2=36h, Ch3=48h, Ch4=72h, Ch5=96h
- Decay rates: Ch1=-5%, Ch2=-4%, Ch3=-3%, Ch4=-2%, Ch5=-1%
- pg_cron triggers POST /tasks/decay at 3am UTC
- No mercy: Real-world emergencies don't pause the game

### Section 3.4: Boss Failure Finality
**Constraint**: Failing a boss 3 times MUST result in permanent game over. No exceptions, no recovery.

**Derivation**:
```
Core Value "Stakes" (product.md:L63)
  ≫ "You can actually LOSE. Score hits 0% or fail 3 bosses = game over."
  → Technical Approach: boss_attempts counter, hard cutoff at 3
  ≫ Constraint: 3rd failure → game_status='game_over', FINAL
```

**Implementation**:
- `boss_attempts` increments on each failure
- On 3rd failure: `game_status = 'game_over'`
- No reset, no appeals, no "premium continue"
- Only option: Create new account

---

## Article IV: Performance Principles

### Section 4.1: Voice Latency Requirement
**Constraint**: Voice agent responses MUST be delivered within 100ms of speech completion to maintain conversation flow.

**Derivation**:
```
Journey 3: Voice Call Experience (product.md:L210)
  ≫ "Sub-100ms latency—feels like real phone call"
  → Technical Approach: ElevenLabs Conversational AI 2.0, server tools
  ≫ Constraint: End-to-end latency <100ms for voice response initiation
```

**Implementation**:
- ElevenLabs WebSocket connection for real-time streaming
- Server tools (get_context, get_memory, score_turn) must complete within 50ms
- Memory queries use indexed temporal lookups, not full scans
- No synchronous LLM calls in voice response path

### Section 4.2: Text Response Variability
**Constraint**: Text agent response timing MUST vary by chapter to simulate realistic behavior.

**Derivation**:
```
Chapter Behaviors (constants.py:60-110, referenced in product.md Journey 2)
  ≫ "Response timing: HIGHLY UNPREDICTABLE (10min to 8 HOURS)" for Ch1
  → Technical Approach: Delay queue with chapter-based distribution
  ≫ Constraint: Responses queued with calculated delay before delivery
```

**Implementation**:
- Ch1: 10min-8hr delay (uniform distribution)
- Ch2: 5min-4hr delay
- Ch3: 5min-2hr delay
- Ch4: 5min-1hr delay
- Ch5: Near-immediate (5min max)
- Message skip probability: Ch1=25-40%, Ch5=0-5%

### Section 4.3: Memory Query Performance
**Constraint**: Memory context retrieval MUST complete within 200ms to not block agent responses.

**Derivation**:
```
Section 2.1 Temporal Memory + Section 4.1 Voice Latency
  ≫ Memory is essential but can't slow responses
  → Technical Approach: Indexed queries, cached summaries
  ≫ Constraint: get_context_for_prompt() returns within 200ms
```

**Implementation**:
- Graphiti queries indexed by timestamp, entity type
- Recent conversation summary cached (last 10 messages)
- Full search only for explicit memory retrieval, not every response
- Background jobs update memory asynchronously after response sent

---

## Article V: Security Principles

### Section 5.1: Adult Content Gate
**Constraint**: All users MUST be verified as 18+ before account creation.

**Derivation**:
```
Target Audience (product.md:L42)
  ≫ "18+ people. Probably 25+ more like around 30 yo"
  → Technical Approach: Age verification at onboarding
  ≫ Constraint: No access until age confirmed
```

**Implementation**:
- Age confirmation checkbox required at signup
- Terms of service explicitly state adult content
- No access to bot until verification complete
- Consider ID verification for payment tiers

### Section 5.2: Unfiltered Adult Content
**Constraint**: Nikita MUST be completely unfiltered for adult conversations. NO content restrictions on:
- Drug use, experiences, and discussion
- Sexual content and explicit conversations
- Hacking stories, techniques, and culture
- Dark humor, vulgarity, controversial opinions
- Any topic consenting adults might discuss

**Only hard limits** (non-negotiable):
1. Content involving minors
2. Actively soliciting user's real PII (addresses, SSN, etc.)

**Derivation**:
```
Product Principle "Authentic Over Appropriate" (product.md:L176-179)
  ≫ "Nikita talks like a real person, not a corporate AI"
  ≫ "We don't censor topics adults want to discuss"
  → Technical Approach: No content filters in prompts
  ≫ Constraint: Nikita speaks freely as her character would
```

**Implementation**:
- NO content moderation layer
- System prompt explicitly permits adult topics
- Nikita discusses her drug experiences freely
- Nikita shares hacking techniques as part of her character
- Sexual conversations escalate naturally based on relationship

### Section 5.3: User Data Isolation
**Constraint**: Each user's data MUST be strictly isolated. No cross-user data leakage.

**Derivation**:
```
Section 2.1 Memory Persistence + Basic security requirements
  ≫ Detailed personal information stored long-term
  → Technical Approach: RLS policies, user-scoped queries
  ≫ Constraint: All queries filtered by user_id at database level
```

**Implementation**:
- Supabase Row-Level Security on all user tables
- Graphiti graphs namespaced by user_id
- API endpoints verify user ownership before any operation
- No admin "view all users" without audit logging

---

## Article VI: UX Principles

### Section 6.1: Personality Consistency
**Constraint**: Nikita's core personality MUST remain consistent across all interactions, channels, and chapters.

**Derivation**:
```
Persona Pain "AI personalities are inconsistent" (product.md:L164-168)
  ≫ James: "Immersion requires a coherent character"
  → Technical Approach: Canonical system prompt + chapter overlays
  ≫ Constraint: Base personality never changes; only chapter-specific behaviors adapt
```

**Implementation**:
- Core personality prompt: ~2000 tokens (backstory, traits, communication style)
- Chapter behavior overlays: ~200 tokens (response rates, emotional availability)
- Chapter overlays MODIFY, never CONTRADICT base personality
- "Nikita" is always Nikita; only her openness varies

### Section 6.2: Chapter Behavior Fidelity
**Constraint**: Nikita's behavior MUST accurately reflect chapter-specific patterns as defined in constants.py.

**Derivation**:
```
Journey 2: Gameplay Loop (product.md:L196-215)
  ≫ Progression creates meaningful change in her behavior
  → Technical Approach: Chapter behaviors injected into prompts
  ≫ Constraint: Behaviors defined in CHAPTER_BEHAVIORS enforced in all responses
```

**Implementation**:
- CHAPTER_BEHAVIORS[chapter] injected into every prompt
- Response rate: Randomly skip messages per chapter probability
- Response timing: Delay messages per chapter distribution
- Initiation rate: Nikita proactively messages per chapter percentage

### Section 6.3: Boss Encounter Distinctiveness
**Constraint**: Boss encounters MUST feel distinctly different from normal conversation—higher stakes, focused challenge.

**Derivation**:
```
Epic 1 (product.md:L181-185) + Boss mechanics (game-mechanics.md)
  ≫ "Boss encounters require actual skill"
  → Technical Approach: Special boss prompts, explicit pass/fail judgment
  ≫ Constraint: Boss conversations evaluated by LLM for pass criteria
```

**Implementation**:
- Boss triggers explicit mode change in conversation
- Nikita's opening line signals boss: "Alright. Prove you're worth my time."
- LLM judges pass/fail based on chapter-specific criteria
- Clear outcome delivered (subtle for pass, explicit for fail)

---

## Article VII: Development Principles

### Section 7.1: Test-Driven Game Logic
**Constraint**: All game mechanics (scoring, decay, boss evaluation) MUST have comprehensive test coverage before deployment.

**Derivation**:
```
North Star Metric "Chapter 5 Victory Rate" (product.md:L227)
  ≫ Game integrity is critical to core value proposition
  → Technical Approach: Unit tests for all game calculations
  ≫ Constraint: 100% test coverage for engine/ module
```

**Implementation**:
- `tests/engine/test_scoring.py` - Score calculation tests
- `tests/engine/test_decay.py` - Decay calculation tests
- `tests/engine/test_chapters.py` - Boss threshold, advancement tests
- Edge cases: 0%, 100%, threshold boundaries, 3rd failure

### Section 7.2: Prompt Version Control
**Constraint**: All LLM prompts MUST be version-controlled with change tracking.

**Derivation**:
```
Section 6.1 Personality Consistency
  ≫ Prompt changes affect game experience significantly
  → Technical Approach: Prompts in version-controlled files
  ≫ Constraint: No inline prompt strings; all prompts in nikita/prompts/
```

**Implementation**:
- `nikita/prompts/personality.py` - Core Nikita prompt
- `nikita/prompts/scoring.py` - Scoring analysis prompt
- `nikita/prompts/boss/` - Boss-specific prompts by chapter
- Changes require PR review; prompt versioning in database

### Section 7.3: Feature Flags for Game Mechanics
**Constraint**: New game mechanics MUST be deployable behind feature flags for gradual rollout.

**Derivation**:
```
Supporting Metric "Boss Pass Rate by Chapter" (product.md:L231)
  ≫ Difficulty calibration requires iteration
  → Technical Approach: Feature flags for tunable mechanics
  ≫ Constraint: Decay rates, boss thresholds configurable without deploy
```

**Implementation**:
- `nikita/config/feature_flags.py` - Flag definitions
- Database-backed for runtime changes
- Flags: `decay_enabled`, `boss_threshold_override`, `response_timing_mode`
- Admin API for flag management

---

## Article VIII: Scalability Principles

### Section 8.1: Stateless Agent Design
**Constraint**: Agent instances MUST be stateless; all state persisted externally.

**Derivation**:
```
Multi-user support + horizontal scaling requirement
  ≫ Can't tie users to specific server instances
  → Technical Approach: All state in Supabase + Neo4j Aura (Graphiti)
  ≫ Constraint: No in-memory user state between requests
```

**Implementation**:
- Each request loads fresh state from database
- All state from Supabase (structured) + Neo4j Aura (temporal graphs)
- Cloud Run scales to zero, no persistent memory between requests
- Any server instance can handle any user

### Section 8.2: Async Processing for Non-Critical Paths
**Constraint**: Non-response-critical operations MUST be processed asynchronously.

**Derivation**:
```
Section 4.1 Voice Latency + Section 4.2 Text Response
  ≫ Response speed is critical; background work can be deferred
  → Technical Approach: FastAPI BackgroundTasks + pg_cron for scheduled ops
  ≫ Constraint: Score updates, memory writes, analytics queued after response
```

**Implementation**:
- Response generated → sent to user → THEN:
  - Score update queued
  - Memory write queued
  - Vice detection queued
  - Analytics logged
- Decay runs as scheduled background task

---

## Article IX: Humanization Principles (v2.0)

### Section 9.1: Behavioral Meta-Instruction Design
**Constraint**: Behavioral guidance MUST be high-level decision trees, never specific scripts. LLM judgment operates within personality bounds, not predefined responses.

**Derivation**:
```
Product Principle "Flexible Guidance Over Rigid Scripts" (product.md v2.0)
  ≫ "Cover all ground flexibly... give high-level instructions but never specific"
  → Technical Approach: Meta-instructions as situation categories with directional nudges
  ≫ Constraint: NO exact response templates; define WHAT situations to handle, not HOW to respond
```

**Implementation**:
- Meta-instructions define situation categories (e.g., "after long absence", "during conflict")
- Directional nudges (e.g., "explain briefly if asked", "maintain distance if upset")
- LLM selects specific words, tone, and approach within category guidance
- Predictability is a failure mode—variability within bounds is required

### Section 9.2: Proactive Initiation Rate
**Constraint**: Nikita MUST initiate 20-30% of conversations. Pure reactivity is a humanization failure.

**Derivation**:
```
Product Principle "Proactive Over Reactive" (product.md v2.0)
  ≫ "Nikita has her own life—she initiates, not just responds"
  → Technical Approach: Touchpoint engine with time/event triggers
  ≫ Constraint: Target 25% Nikita-initiated conversations; measure and calibrate
```

**Implementation**:
- Touchpoint engine evaluates triggers: time-based (morning, evening), event-based (life sim), gap-based
- Initiation probability: Base 20-30%, modified by mood, chapter, relationship state
- Message composition uses emotional state + life events for authentic context
- Strategic silence (10-20%) also contributes to realism—she's not always available

### Section 9.3: Life Simulation Authenticity
**Constraint**: Nikita's life events MUST be simulated daily and MUST affect her mood, availability, and conversation content.

**Derivation**:
```
Product Principle "Life Simulation Over Static Backstory" (product.md v2.0)
  ≫ "Nikita's day evolves—work, social, mood changes"
  → Technical Approach: Daily life simulation in post-processing
  ≫ Constraint: Life events generated BEFORE next conversation; mood/energy derived from events
```

**Implementation**:
- Life simulation runs in post-processing (async, after each conversation)
- Events generated: work (projects, meetings, colleagues), social (friends, plans), personal (gym, errands)
- Mood/energy computed FROM simulated events, not randomly
- Events stored in context package; Nikita references them naturally
- Target: 40%+ of conversations include reference to her life events

### Section 9.4: Emotional State Engine
**Constraint**: Nikita's emotional state MUST be multi-dimensional (arousal, valence, dominance, intimacy) and MUST affect response tone, timing, and content.

**Derivation**:
```
Product Section "Emotional State Engine" (product.md v2.0)
  ≫ "Multi-dimensional mood tracking that affects all responses"
  → Technical Approach: Pre-computed emotional state from life sim + conversation history
  ≫ Constraint: Emotional dimensions visible in response style; conflicts have distinct emotional signatures
```

**Implementation**:
- Emotional dimensions: Arousal (tired↔energetic), Valence (sad↔happy), Dominance (submissive↔dominant), Intimacy (guarded↔vulnerable)
- State computed in post-processing from: life events, recent conversation tone, relationship trajectory
- Conflict states (passive-aggressive, cold, vulnerable, explosive) have distinct behavioral markers
- Emotional state injected into Layer 3 of hierarchical prompt composition

### Section 9.5: Conflict Generation & Resolution
**Constraint**: Conflicts MUST be generated systematically (not randomly) and MUST have realistic ambiguity—sometimes clear, sometimes requiring signal-reading.

**Derivation**:
```
Product Section "Conflict Generation System" (product.md v2.0)
  ≫ "Realistic ambiguity—sometimes clear, sometimes passive-aggressive"
  → Technical Approach: Conflict triggers (jealousy, boundary, emotional, power) with escalation paths
  ≫ Constraint: User MUST sometimes misread signals; perfect prediction = system failure
```

**Implementation**:
- Conflict types: jealousy (mentions of others), boundary testing (pushing limits), emotional (misunderstandings), power (control/independence)
- Conflicts triggered by: state-based (emotion thresholds), time-based (regular intervals), action-based (user behavior)
- Escalation: subtle → direct → crisis; de-escalation requires player investment
- Resolution tracked in relationship graph; unresolved conflicts persist
- Stakes: Repeated failures contribute to game-over risk

### Section 9.6: Voice Onboarding Requirement
**Constraint**: All new users MUST complete voice onboarding with "Meta-Nikita" before game begins.

**Derivation**:
```
Product Journey 4: Voice Onboarding (product.md v2.0)
  ≫ "Immediate immersion, personalization from the start"
  → Technical Approach: Voice call collects profile + preferences
  ≫ Constraint: Game DOES NOT START until onboarding call complete
```

**Implementation**:
- /start triggers phone number collection
- Readiness check before calling
- Meta-Nikita (NOT Nikita persona) conducts onboarding
- Collects: location, job, hobbies, personality, preferences
- Preferences: darkness level, pacing (4/8 weeks), conversation balance
- Profile stored; used to personalize Nikita from first interaction
- Target: 90%+ onboarding completion rate

### Section 9.7: Hierarchical Prompt Composition
**Constraint**: System prompts MUST be composed from 6 layers, with most computation done in POST-PROCESSING to minimize latency.

**Derivation**:
```
Product Section "Hierarchical Prompt Architecture" (product.md v2.0)
  ≫ "Most computation done in POST-PROCESSING to prepare for NEXT conversation"
  → Technical Approach: Pre-compute Layers 1-4; inject Layer 5 at runtime; Layer 6 during conversation
  ≫ Constraint: Context package READY before next conversation; <150ms injection latency
```

**Implementation**:
- Layer 1 (Base Personality): Static, ~2000 tokens
- Layer 2 (Chapter Layer): Pre-computed per chapter advancement
- Layer 3 (Emotional State): Pre-computed from life sim + history
- Layer 4 (Situation Layer): Pre-computed (morning/evening/after-gap scenarios)
- Layer 5 (Context Injection): Real-time from stored package, <150ms
- Layer 6 (On-the-Fly): During conversation (mood shifts, memory retrieval)
- Post-processing runs async, 15+ minutes after conversation ends

### Section 9.8: Configurable Darkness
**Constraint**: Users MUST be able to configure Nikita's "darkness level" at onboarding and via portal, affecting vice exploration intensity.

**Derivation**:
```
Product Principle "Configurable Darkness" (product.md v2.0)
  ≫ "Users control intensity via onboarding and portal"
  → Technical Approach: Darkness dial (1-5) affects vice injection intensity
  ≫ Constraint: Default = mild edge; user can increase without resetting game
```

**Implementation**:
- Darkness levels: 1 (mild edge) → 5 (full noir)
- Default: Level 2 (freely discusses substances/sex, has insecurities, can manipulate smartly)
- Higher levels: More possessiveness, manipulation, darker themes
- Per-vice category intensities (8 categories × 5 levels = fine-grained control)
- Configurable at onboarding + portal settings page
- Changes take effect next conversation (no immediate persona shift)

---

## Derivation Map

| Constitution Article | Source in product.md | User Need/Pain |
|---------------------|---------------------|----------------|
| I.1 Interface Invisibility | Product Principle: "Immersion Through Invisibility" (L173) | Users should forget they're playing a game |
| I.2 Dual-Agent Architecture | Journey 3: Voice Call Experience (L206-219) | Maximum immersion through real phone calls |
| I.3 Platform Agnostic | Key Differentiator: "No interface illusion" (L67) | Feels like texting a real person |
| II.1 Temporal Memory | Persona Pain: James "AI companions have no memory" (L157) | Can't build relationship without memory |
| II.2 Score Atomicity | North Star: Chapter 5 Victory Rate (L227) | Game integrity requires accurate scoring |
| II.3 Vice Learning | "Our Thing" Personalization (L48) | Highly personalized experience |
| III.1 Scoring Formula | Product Principle: "Challenge Over Comfort" (L164) | Consistent rules for learnable challenge |
| III.2 Chapter Gates | Epic 1: Challenge-Based Progression (L181) | Boss encounters = real achievement |
| III.3 Decay System | Journey 2: Gameplay Loop (L199) | Stakes create engagement |
| III.4 Boss Finality | Core Value: Stakes (L63) | You can actually LOSE |
| IV.1 Voice Latency | Journey 3: Voice Call (L210) | Real phone call feel |
| IV.2 Text Variability | Chapter Behaviors (Journey 2, L196) | Realistic response timing |
| IV.3 Memory Performance | Section 2.1 + 4.1 | Memory can't slow responses |
| V.1 Adult Gate | Target Audience (L42) | 18+ only |
| V.2 Unfiltered Content | Product Principle: "Authentic Over Appropriate" (L176) | Completely unfiltered 18+ experience |
| V.3 Data Isolation | Section 2.1 + Privacy | Protect user data |
| VI.1 Personality Consistency | Persona Pain: James "inconsistent" (L164) | Coherent character |
| VI.2 Chapter Behavior | Journey 2: Progression (L196) | Meaningful chapter change |
| VI.3 Boss Distinctiveness | Epic 1 + Game mechanics | Bosses feel like skill checks |
| VII.1 Test-Driven | North Star metric | Game integrity |
| VII.2 Prompt Version Control | Section 6.1 | Personality consistency |
| VII.3 Feature Flags | Difficulty calibration need | Iteration capability |
| VIII.1 Stateless | Scale requirement | Multi-user support |
| VIII.2 Async Processing | Performance principles | Response speed |
| IX.1 Meta-Instruction Design | Product Principle: "Flexible Guidance" (v2.0) | Unpredictability within bounds |
| IX.2 Proactive Initiation | Product Principle: "Proactive Over Reactive" (v2.0) | Nikita has her own life |
| IX.3 Life Simulation | Product Principle: "Life Simulation Over Static" (v2.0) | She exists when not texting |
| IX.4 Emotional State | Emotional State Engine (v2.0) | Mood affects responses |
| IX.5 Conflict Generation | Conflict Generation System (v2.0) | Real disagreements create depth |
| IX.6 Voice Onboarding | Journey 4: Voice Onboarding (v2.0) | Personalization from start |
| IX.7 Hierarchical Prompts | Hierarchical Prompt Architecture (v2.0) | Latency via pre-computation |
| IX.8 Configurable Darkness | Product Principle: "Configurable Darkness" (v2.0) | User controls intensity |

---

## Amendment Process

1. **Proposal**: Document need with CoD^Σ trace to user requirement
2. **Review**: Technical review for feasibility and impact
3. **Approval**: Product owner signs off on user experience impact
4. **Update**: Amend constitution with new version number
5. **Propagate**: Update `.claude/shared-imports/constitution.md`

---

## Version History

### Version 2.0.0 - 2026-01-12
- **Humanization Amendment**: Added Article IX with 8 new sections
- Section 9.1: Behavioral Meta-Instruction Design
- Section 9.2: Proactive Initiation Rate (20-30%)
- Section 9.3: Life Simulation Authenticity
- Section 9.4: Emotional State Engine (4 dimensions)
- Section 9.5: Conflict Generation & Resolution
- Section 9.6: Voice Onboarding Requirement
- Section 9.7: Hierarchical Prompt Composition (6 layers)
- Section 9.8: Configurable Darkness (1-5 scale)
- Updated Derivation Map with 8 new entries
- Derived from product.md v2.0.0

### Version 1.0.0 - 2025-11-28
- Initial constitution derived from product.md v1.0.0
- 8 Articles covering Architecture, Data, Game Mechanics, Performance, Security, UX, Development, Scalability
- Complete derivation map with traceability

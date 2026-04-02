# Nikita: Don't Get Dumped — Technical Brief

> One developer. 86 specifications. 5,533 tests. An AI girlfriend that can dump you.

---

## What Is Nikita?

Nikita is an AI girlfriend simulation **game** — not a chatbot, not a companion app, but a real game with stakes, progression, and genuine failure states. Players interact with a psychologically complex AI character named Nikita through Telegram text messages and real-time voice calls (ElevenLabs). She has a personality, emotional states, a simulated daily life, and she will dump you if you're boring, clingy, or distant.

The game spans 5 chapters over 120+ days. Your relationship is scored across 4 hidden metrics (intimacy, passion, trust, secureness). Boss encounters gate chapter progression. A decay system penalizes neglect. You can win — or you can get dumped.

There is no game UI. No score displays. No chapter indicators. Just Telegram messages and phone calls that feel like texting a real person.

---

## The Numbers

| Dimension | Count |
|-----------|-------|
| Total files | 1,084 (742 Python, 234 TypeScript) |
| Feature specifications | 86 (all implemented, audited, and E2E verified) |
| Passing tests | 5,533 across 451 test files |
| Pipeline stages | 11 async post-processing stages |
| Prompt layers | 6-layer hierarchical architecture (12 dynamic inputs) |
| Emotional dimensions | 4 (arousal, valence, dominance, intimacy) |
| Vice categories | 8 personality-discovery categories |
| Engagement states | 6-state finite state machine |
| Game chapters | 5 with boss encounters as progression gates |
| Platforms | 3 (Telegram, Portal, Voice) |
| Database tables | 26 models with Row-Level Security |

---

## Engineering Highlights

### 1. The Conversation Processing Pipeline

Every user message triggers an **11-stage async post-processing pipeline** with savepoint isolation per stage. This is the architectural centerpiece — it pre-computes Nikita's entire prompt context *before* the next message arrives, achieving <150ms injection latency at runtime.

**Stages**: extraction (CRITICAL) → persistence → memory_update (CRITICAL) → life_sim → emotional → vice → game_state → conflict → touchpoint → summary → prompt_builder

- **Critical stages** block the pipeline on failure; **non-critical stages** gracefully degrade with 1 retry + 0.5s backoff
- Each stage runs inside a database **savepoint** — failures roll back cleanly without poisoning the session
- **Observability events** snapshot context before/after each stage for debugging (toggle via feature flag)
- The final stage (prompt_builder) renders a Jinja2 template into a token-budgeted prompt, stored in `ready_prompts` for instant retrieval on the next interaction

**Source**: `nikita/pipeline/orchestrator.py`, `nikita/pipeline/stages/*.py`

### 2. Context Engineering (6-Layer Prompt Architecture)

Nikita's personality is not a static system prompt. It emerges from **12 dynamic inputs** across 4 categories, converging through a Jinja2 template into a token-budgeted prompt:

**Identity** (static + chapter-specific):
- Base personality (~2,000 tokens — backstory, traits, communication style)
- Chapter overlay (~200 tokens — behavioral modulation per relationship stage)
- Platform style (text vs. voice adaptations)

**State** (pre-computed from life simulation):
- 4D emotional state (arousal, valence, dominance, intimacy)
- Today's life events (work drama, social interactions, personal routines)
- Conflict temperature (0-100 relationship tension gauge)

**Memory** (semantic search via pgVector):
- User facts, Nikita facts, relationship episodes — all retrieved via cosine similarity
- Conversation history (token-budgeted sliding window)
- Daily and weekly summaries

**Guidance** (AI-generated):
- PsycheState (attachment style, defense mechanisms, vulnerability level — from daily Psyche Agent batch job)
- Vice preferences (8 discovered categories with chapter-gated intensity)
- Behavioral meta-instructions (high-level decision trees, never exact scripts)

**Token budget enforcement**: Text gets 5,500-6,500 tokens; voice gets 2,800-3,500. Priority-based truncation: vice → chapter → psychology.

**Source**: `nikita/pipeline/stages/prompt_builder.py`, `nikita/prompts/`

### 3. Psychological Modeling

This is where Nikita stops being a chatbot and becomes a character:

**4D Emotional State Engine**: Nikita's mood is modeled across arousal (tired↔energetic), valence (sad↔happy), dominance (submissive↔dominant), and intimacy (guarded↔vulnerable). These dimensions are computed from simulated life events + player interaction quality, and they affect response timing, tone, content depth, and conflict triggers.

**Psyche Agent**: A daily batch job (Claude Sonnet/Opus) that analyzes the relationship trajectory and produces a `PsycheState`: current attachment style, active defense mechanisms, vulnerability level (1-10), behavioral guidance, internal monologue, topics to encourage, topics to avoid. Injected as Layer 3 of the prompt architecture.

**Conflict Temperature**: A 0-100 gauge tracking relationship tension with 5 trigger types (jealousy, boundary testing, emotional misunderstanding, power struggle, neglect) and 3 escalation levels (subtle → direct → crisis). Implements Gottman Four Horsemen detection for conflict patterns.

**Life Simulator**: Daily events (work projects, colleague interactions, gym sessions, social outings) that Nikita references naturally in conversation. She doesn't just respond to you — she has her own day happening.

**Source**: `nikita/pipeline/stages/emotional.py`, `nikita/agents/psyche/`, `nikita/pipeline/stages/conflict.py`, `nikita/pipeline/stages/life_sim.py`

### 4. Game Mechanics

Not just a chatbot — a game with mathematical foundations:

**4-Metric Weighted Scoring**:
```
composite = intimacy×0.30 + passion×0.25 + trust×0.25 + secureness×0.20
```

**5-Chapter Progression** with boss encounters as skill gates:
| Chapter | Boss Threshold | Decay Rate | Grace Period |
|---------|---------------|------------|--------------|
| 1: Curiosity | 55% | 0.8%/hr | 8 hours |
| 2: Intrigue | 60% | 0.6%/hr | 16 hours |
| 3: Investment | 65% | 0.4%/hr | 24 hours |
| 4: Intimacy | 70% | 0.3%/hr | 48 hours |
| 5: Established | 75% | 0.2%/hr | 72 hours |

**Boss Encounters**: Multi-phase (opening → resolution). LLM evaluates player's response against chapter-specific rubric. PASS = advance, FAIL = score penalty (3 failures = permanent game over), PARTIAL = 24h cooldown.

**6-State Engagement FSM**: CALIBRATING → IN_ZONE → DRIFTING → CLINGY → DISTANT → OUT_OF_ZONE. Each state applies a scoring multiplier (0.2x to 1.0x) that prevents exploitation — you can't spam messages to grind score.

**8 Vice Categories**: intellectual_dominance, risk_taking, substances, sexuality, emotional_intensity, rule_breaking, dark_humor, vulnerability. Discovered via LLM analysis of each conversation, with chapter-gated boundary enforcement (sexuality capped at 0.35 in Ch1, 0.85 in Ch5).

**Source**: `nikita/engine/constants.py`, `nikita/engine/scoring/`, `nikita/engine/chapters/boss.py`, `nikita/engine/engagement/state_machine.py`, `nikita/engine/vice/`

### 5. Multi-Platform Architecture

**Telegram**: Bot adapter with database-backed rate limiting (20 msg/min, 500 msg/day), OTP authentication, boss encounter UI with inline keyboard buttons, profile gate (redirect to onboarding if incomplete).

**Portal** (Next.js 16 on Vercel): 25+ routes (19 player + 6 admin). Dark-only glassmorphism UI with shadcn/ui. Features: dashboard stats, engagement visualization, vice preferences, Nikita's mind/psyche view, conversation history, admin pipeline health monitor, prompt testing console.

**Voice** (ElevenLabs Conversational AI 2.0): Server tools pattern for real-time context injection during calls. Chapter-based availability (10% in Ch1, 95% in Ch5). Dynamic TTS configuration per emotional state. Voice call scoring via transcript analysis.

**Auth Bridge**: Zero-click Telegram→Portal authentication without PKCE. Custom bridge token exchange (5-min TTL, single-use) that bypasses the code_verifier mismatch when server generates magic links.

**Source**: `nikita/platforms/telegram/`, `portal/src/app/`, `nikita/agents/voice/`, `nikita/api/routes/auth_bridge.py`

### 6. Infrastructure

- **Backend**: Python 3.12, FastAPI, Google Cloud Run (scales to zero — NEVER min-instances=1)
- **Frontend**: Next.js 16, React 19, shadcn/ui, Tailwind CSS, Vercel
- **Database**: Supabase (PostgreSQL + pgVector for semantic search + Row-Level Security)
- **AI Text**: Pydantic AI + Claude Sonnet (with prompt caching — 0.1x cost for cached tokens)
- **AI Voice**: ElevenLabs Conversational AI 2.0 (server tools pattern)
- **Embeddings**: OpenAI text-embedding-3-small (1536 dimensions)
- **Scheduling**: pg_cron + Cloud Run task endpoints (no Celery, no Redis)
- **Memory Dedup**: 95% cosine similarity threshold — new similar facts supersede old ones
- **Feature Flags**: All major features guarded, canary rollout support (hash-based deterministic sampling)
- **CI/CD**: GitHub Actions (backend-ci, portal-ci, E2E) with Playwright browser testing

---

## Development Methodology

### Specification-Driven Development (SDD)

Every feature follows a rigorous lifecycle:

1. **Spec** (`/feature`): Socratic questioning to define the feature through spec.md
2. **Validation Gate**: 6 parallel validator agents check architecture, frontend, API, data layer, auth, and testing requirements
3. **Plan** (`/plan`): Detailed implementation plan with task breakdown
4. **Audit** (`/audit`): Cross-artifact consistency check
5. **Implement** (`/implement`): TDD — failing tests first, then minimal code to pass
6. **QA Review** (`/qa-review`): Iterative code review loop until 0 blocking + 0 important issues
7. **Merge**: Squash merge to master, max 400 lines per PR

**86 specifications completed** — each with spec.md, plan.md, tasks.md, and audit-report.md.

### Technical Constitution

A formal `constitution.md` with 9 articles and 30+ sections, each traced back to user pain points via CoD^Σ (Chain of Derivation) notation. Every technical decision has a derivation chain:

```
User Pain: "AI companions have no memory" (product.md:L157)
  → Product Principle: "Memory Is Everything"
    → Constitution Article II.1: Temporal Memory Persistence
      → Implementation: pgVector with timestamps, 3 fact types, 6-month retention
```

### E2E Testing

Full user journey simulation: 13 epics, 363+ scenarios covering registration through 5 chapters, boss encounters, game over, restart, and victory. Uses Telegram MCP, Gmail MCP, Supabase MCP, and Chrome DevTools MCP for realistic end-to-end validation.

---

## What This Says About the Builder

**Solo full-stack**: Backend (Python/FastAPI), frontend (Next.js/React), AI/ML (prompt engineering, LLM orchestration), DevOps (Cloud Run, Vercel, CI/CD), product definition (3 personas, 5 user journeys), game design (scoring formulas, balance iteration) — all one person.

**Over-engineered on purpose**: This project has no business model, no revenue target, no investors. It exists because building a psychologically complex AI character with genuine game mechanics is *interesting*. The 86-spec SDD workflow, the technical constitution with derivation chains, the 5,533 tests — that's not imposed process. That's someone who finds rigor fun.

**AI-native architecture**: Prompt engineering isn't an afterthought bolted onto a CRUD app. It's a first-class architectural concern with its own 6-layer composition system, pre-computation pipeline, and token budget enforcement. The 11-stage pipeline exists specifically to make the next prompt richer — most computation happens *after* the response, not during it.

**Game design instinct**: The scoring formula weights, decay rates, boss thresholds, engagement multipliers, and vice boundary caps required genuine playtesting and iteration. These aren't arbitrary numbers — they're tuned to create a difficulty curve that's challenging but achievable over 120+ days.

---

## Architecture Diagrams

See `docs/diagrams/` for visual representations:
- `01-full-stack-architecture` — 4-layer system overview
- `02-conversation-pipeline` — 11-stage serpentine pipeline
- `03-prompt-assembly` — 12-input convergence funnel
- `04-emotional-machinery` — 4D emotional state + life sim
- `05-game-mechanics-loop` — Chapter ring + scoring + decay
- `06-user-journey-map` — 3-platform 120-day timeline

---

*Built by Simon Yang. Contact: simon.yang.ch@gmail.com*

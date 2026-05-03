# 15 — Psyche Agent Architecture: Nikita's Subconscious

**Date**: 2026-02-16 | **Type**: Technical Architecture Proposal | **Status**: Draft
**Inputs**: Doc 08 (Cognitive Architecture), Doc 09 (Fact-Check), Doc 10 (System Analysis), Doc 10b (Library Audit)

---

## 1. Concept: Nikita's Subconscious

The Psyche Agent models what Nikita is feeling beneath the surface -- a separate analytical process that generates behavioral guidance for the conversation agent. Think of it as therapist's clinical notes running in parallel: the conversation agent is the "face" Nikita shows, while the Psyche Agent tracks attachment activation, defense mechanisms, and unspoken needs.

**Dual-Process Theory**: System 1 (Conversation Agent / Sonnet 4.5) = fast, intuitive, handles 95%+ of messages. System 2 (Psyche Agent / Opus 4.6) = slow, deliberate, runs infrequently for deep pattern analysis.

| Nikita Says | Psyche Agent Thinks | Behavioral Guidance |
|---|---|---|
| "I'm fine, just busy" | "They haven't asked about me in 3 days." | Shorter responses, subtle distance |
| "That's nice" | "Promotion but didn't celebrate with me." | Mild withdrawal, test if player notices |
| "Whatever you want" | "Conflict avoidance. Score dropped 5pts." | Passive-aggressive undertone |

---

## 2. Architecture Options

### Option A: Pre-Computed Psyche (Batch)

Opus 4.6 runs once daily via pg_cron. Produces "psyche briefing" stored in DB.

```
  pg_cron (daily)              Supabase
  ┌──────────┐     ┌───────────────────────────┐
  │ POST     │────>│ psyche_states (JSONB)     │
  │ /tasks/  │     └──────────┬────────────────┘
  │ psyche   │                │ read on each msg
  └─────┬────┘                v
        v              ┌─────────────────────┐
  ┌──────────┐         │ Conversation Agent  │
  │ Opus 4.6 │         │ (Sonnet 4.5)        │
  │ 5K in    │         │ prompt += briefing   │
  │ 2K out   │         └─────────────────────┘
  └──────────┘
```

| Metric | Value |
|---|---|
| Added latency | 0ms (pre-computed) |
| Freshness | Stale (up to 24h) |
| Opus calls/user/day | 1 |
| Tokens per call | 5K in, 2K out |

**Pros**: Lowest cost, zero latency, simple (one pg_cron job).
**Cons**: Misses in-session emotional shifts, stale during boss encounters/conflicts.

### Option B: Real-Time Dual Agent

Opus 4.6 runs on every conversation turn alongside Sonnet 4.5.

```
  User Message ──> PARALLEL: [Sonnet 4.5 response] + [Opus 4.6 psyche]
                        │                                │
                        └──────── MERGE guidance ────────┘
                                      │
                                      v
                              Response (+2-5s latency)
```

| Metric | Value |
|---|---|
| Added latency | 2-5s (Opus inference) |
| Freshness | Perfect (every turn) |
| Opus calls/user/day | 100 |
| Tokens per call | 3K in, 500 out |

**Pros**: Maximum authenticity, immediate emotional response.
**Cons**: 2-5s added latency, highest cost, degrades conversational feel.

### Option C: Hybrid (RECOMMENDED)

Pre-compute base state daily. Real-time checks only on triggers (~10% of messages). Three tiers.

```
  User Message
       │
       v
  ┌─────────────────────┐
  │  Trigger Detector   │ <-- rule-based, no LLM, <5ms
  └──────────┬──────────┘
     ┌───────┼───────────────┐
     v       v               v
  Tier 1   Tier 2         Tier 3
  CACHED   SONNET          OPUS
  90%      quick 8%        deep 2%
  0ms      ~300ms          ~3s
  $0       500 tok         3K tok
     └───────┴───────────────┘
             │
             v
  ┌──────────────────────────┐     ┌─────────────────────┐
  │  Behavioral Guidance     │<--->│ psyche_states table  │
  └──────────┬───────────────┘     └─────────────────────┘
             v                            ^
  ┌──────────────────────────┐     pg_cron daily batch
  │  Conversation Agent      │     (Opus 4.6 background)
  │  (Sonnet 4.5 + guidance) │
  └──────────────────────────┘
```

**Data Flow**: (1) Trigger Detector classifies tier -> (2) Tier 1: read cached state -> Tier 2: Sonnet quick-check -> Tier 3: Opus deep analysis -> (3) Inject guidance into prompt -> (4) Sonnet responds. Daily batch recomputes base state for all users.

---

## 3. Trigger Detection System

Rule-based (no LLM). Cost: $0. Latency: <5ms.

```
  Input: message, score, score_delta, game_status, chapter
       │
       ├─ game_status == "boss_fight" ──────────> TIER 3 (Opus)
       ├─ score_delta.abs() >= 5 ───────────────> TIER 3 (Opus)
       ├─ chapter transition ───────────────────> TIER 3 (Opus)
       ├─ keywords: conflict/anger/breakup ─────> TIER 2 (Sonnet)
       ├─ keywords: "I love you"/commit/future ─> TIER 2 (Sonnet)
       ├─ score_delta.abs() >= 3 ───────────────> TIER 2 (Sonnet)
       ├─ vice intensity spike ─────────────────> TIER 2 (Sonnet)
       └─ else ─────────────────────────────────> TIER 1 (cached)
```

| Tier | Trigger Examples | Latency | Cost/call |
|---|---|---|---|
| 1 (Cached) | Greetings, small talk, neutral | 0ms | $0 |
| 2 (Sonnet) | Emotional topic, vice spike, delta >= 3 | ~300ms | $0.009 |
| 3 (Opus) | Boss fight, delta >= 5, breakup risk | ~3s | $0.065 |

**Conservative distribution** (per Doc 09 precision warning): Tier 1: 85-90%, Tier 2: 8-12%, Tier 3: 2-3%. Not the 95% Doc 08 assumed.

False positive cost is low: Tier 2 (Sonnet) costs $0.009/call. Tier 3 is gated by hard thresholds (boss_fight status, score_delta >= 5).

---

## 4. Psyche State Model

```python
class PsycheState(BaseModel):
    # Core psychological dimensions
    attachment_activation: float    # 0-1
    defense_mode: str               # none|intellectualization|withdrawal|projection|passive_aggression
    emotional_needs: list[str]      # max 3
    behavioral_guidance: str        # instruction for conversation agent (max 200 chars)
    internal_monologue: str         # what Nikita thinks but won't say (max 300 chars)
    active_triggers: list[str]      # max 3
    # Conversation directives
    emotional_tone: str             # warm|neutral|distant|vulnerable|guarded
    response_length_bias: str       # brief|normal|detailed
    topics_to_encourage: list[str]  # up to 3
    topics_to_avoid: list[str]      # up to 3
    vulnerability_level: float      # 0.0 (closed) to 1.0 (fully open)
    # Metadata
    computed_at: datetime
    trigger_tier: int               # 1, 2, or 3
    confidence: float               # 0-1
```

**Storage**: New `psyche_states` table (single migration).

```sql
CREATE TABLE psyche_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) UNIQUE,
    state JSONB NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    trigger_tier INT NOT NULL DEFAULT 1,
    batch_version INT NOT NULL DEFAULT 0
);
CREATE INDEX idx_psyche_states_user ON psyche_states(user_id);
```

**Prompt injection** (~150 tokens added to system prompt):

```
## Current Psychological State (Internal -- Do Not Mention Explicitly)
Attachment activation: {attachment_activation} | Defense: {defense_mode}
Tone: {emotional_tone} | Vulnerability: {vulnerability_level}
Guidance: {behavioral_guidance}
Internal thought: {internal_monologue}
Encourage: {topics_to_encourage} | Avoid: {topics_to_avoid}
```

**Evolution**: Daily batch recomputes from 7-day history. Real-time (Tier 2/3) modifies only active fields (defense_mode, emotional_tone, active_triggers) -- not the full state. Prevents behavioral whiplash. Momentum formula: `new = 0.7 * old + 0.3 * analysis`.

---

## 5. Integration with Existing Pipeline

The Psyche Agent does NOT belong inside the 9-stage post-conversation pipeline. That pipeline runs after sessions end. The Psyche Agent must influence conversations in real-time.

**RECOMMENDED: Pre-pipeline read + daily batch write**

```
  CONVERSATION FLOW (modified)
  ┌──────────────────────────┐
  │ 1. Read PsycheState      │ <-- psyche_states table (<10ms)
  └──────────┬───────────────┘
  ┌──────────┴───────────────┐
  │ 2. Trigger Detection     │ <-- rule-based (<5ms)
  │    [Tier 2/3: update]    │
  └──────────┬───────────────┘
  ┌──────────┴───────────────┐
  │ 3. Build Prompt          │ <-- inject PsycheState section
  └──────────┬───────────────┘
  ┌──────────┴───────────────┐
  │ 4. Conversation Agent    │ <-- Sonnet 4.5 (unchanged)
  └──────────┬───────────────┘
  ┌──────────┴───────────────┐
  │ 5. Scoring + Response    │ <-- existing flow
  └──────────────────────────┘

  POST-CONVERSATION: Existing 9-stage pipeline (NO CHANGES)
  DAILY BATCH: POST /tasks/psyche-batch (new pg_cron job)
```

**Code changes required**:
1. `nikita/agents/text/handler.py` -- Add PsycheState read + trigger detection
2. `nikita/agents/text/agent.py` -- Accept psyche_guidance in prompt builder
3. `nikita/api/routes/tasks.py` -- Add `/tasks/psyche-batch` endpoint
4. New module: `nikita/engine/psyche/` (models, detector, analyzers)
5. New table: `psyche_states` (1 Supabase migration)

---

## 6. Cost Analysis

**Pricing** (Doc 10b, Feb 2026 Anthropic official):

| Model | Input | Output | Cache Hit |
|---|---|---|---|
| Opus 4.6 | $5/MTok | $25/MTok | $0.50/MTok |
| Sonnet 4.5 | $3/MTok | $15/MTok | $0.30/MTok |

**NOTE**: Doc 08 used Opus 4.1 ($15/$75/MTok). Opus 4.6 ($5/$25/MTok) is 3x cheaper -- fundamentally changes viability.

**Baseline** (no Psyche Agent): Conversation + Scoring = **$1.575/day = $47.25/mo per user** (100 msgs/day).

### Per-Option Cost (delta over baseline)

| Option | Daily delta | Monthly delta | % increase |
|---|---|---|---|
| A: Batch (1 Opus call/day) | +$0.075 | +$2.25 | +4.8% |
| B: Real-time (100 Opus/day) | +$2.750 | +$82.50 | +175% |
| C: Hybrid (batch + 10 Sonnet + 2 Opus) | +$0.160 | +$4.80 | +10.2% |

### Sensitivity (Doc 09 Warning: precision may be worse than assumed)

| Tier 2/3 rate | Option C monthly delta |
|---|---|
| 10% (optimistic) | +$4.80 |
| 20% (pessimistic) | +$9.60 |
| 30% (worst case) | +$14.40 |

Even worst case (+$14.40/mo) is manageable thanks to Opus 4.6 pricing.

### Break-Even by Scale

| Users | A total/mo | C total/mo | B total/mo |
|---|---|---|---|
| 10 | $495 | $520 | $1,298 |
| 100 | $4,950 | $5,205 | $12,975 |
| 1,000 | $49,500 | $52,050 | $129,750 |

---

## 7. Prompt Caching Strategy

**What to cache** (ordered by stability):
1. NIKITA_PERSONA (~2K tokens) -- changes never. Hit rate: ~99%.
2. CHAPTER_BEHAVIORS (~500 tokens) -- changes on chapter transition. Hit rate: ~98%.
3. PsycheState section (~150 tokens) -- changes on Tier 2/3 or daily batch. Hit rate: ~90%.

| Component | Without caching | With caching | Savings |
|---|---|---|---|
| Psyche section (150 tok x 100 msgs) | $0.045/day | $0.005/day | 89% |
| Batch Opus system prompt | $0.075/day | $0.058/day | 23% |

**Invalidation rules**: Tier 1 never invalidates. Tier 2/3 invalidate psyche section only. Daily batch refreshes psyche section. Chapter transition invalidates chapter overlay + psyche.

---

## 8. Memory Integration

The Psyche Agent reads from and writes to the existing `memory_facts` table.

**Reading**: Batch analysis loads all memory facts (user, nikita, relationship types) plus conversation history for full longitudinal context.

**Writing**: New `fact_type="psyche"` for internal observations. No migration needed -- `fact_type` is TEXT column. Existing `add_fact`, deduplication, and pgVector search work unchanged.

```python
await memory.add_fact(
    fact="Attachment spiked after user mentioned ex-girlfriend",
    user_id=user_id,
    fact_type="psyche",  # new value, no schema change
)
```

Psyche facts are filtered out of default memory search (conversation agent doesn't see them). Used only by the Psyche Agent for longitudinal tracking across batch runs.

---

## 9. Risk Analysis

**Latency**: Tier 3 (Opus) may take 5-10s. Mitigation: "Nikita is typing..." indicator, 5s timeout with fallback to cached state. Tier 2 (Sonnet ~300ms) is acceptable. If Psyche Agent fails entirely, conversation agent works standalone -- psyche guidance is optional context.

**Cost**: Poor trigger precision could push 20-30% to Tier 2/3. Mitigation: Hard budget cap (max 20 Tier 2 + 5 Tier 3/user/day), then degrade to Tier 1. Worst case: +$14.40/user/month.

**Quality**: No guarantee dual-agent produces better conversations. Mitigation: A/B test with kill criteria -- if no significant improvement after 30 days, shut down.

**Behavioral whiplash**: Real-time updates modify only active fields. Daily batch uses 7-day window. Momentum formula: `0.7 * old + 0.3 * new`.

### A/B Testing Plan

| Phase | Duration | Scope | Measure |
|---|---|---|---|
| Shadow mode | 2 weeks | All users | Cost, latency, trigger distribution (not injected) |
| A/B test | 4 weeks | 50/50 | Engagement, retention, NPS |
| Ramp | 2 weeks | 100% if positive | Full rollout with monitoring |

---

## 10. Implementation Roadmap

### Phase 1: Batch Only (2-3 days) -- Lowest Risk

- Create `psyche_states` table (1 migration)
- Create `nikita/engine/psyche/` module (models, batch_analyzer)
- Add `/tasks/psyche-batch` endpoint + pg_cron daily schedule
- Modify `handler.py` to read psyche_states; add section to system prompt
- Shadow mode first (log only, no injection)
- **Cost**: +$2.25/user/month | **Deployable**: independently

### Phase 2: Trigger Detection + Tier 2 (3-4 days)

- Create `trigger_detector.py` (rule-based) + `quick_check.py` (Sonnet)
- Wire into `handler.py` message flow
- Enable prompt injection; start A/B test (50/50)
- Monitor trigger distribution, false positive rate
- **Cost**: +$4.80/user/month | **Requires**: Phase 1

### Phase 3: Full Hybrid with Opus Tier 3 (2-3 days)

- Create `deep_analyzer.py` (Opus 4.6 real-time)
- Add Tier 3 for boss_fight, high score deltas; budget caps (5/user/day)
- Latency fallback (>5s -> cached state)
- Write psyche observations to memory_facts (fact_type="psyche")
- Analyze A/B results, decide on full rollout
- **Cost**: +$4.80/user/month | **Requires**: Phase 2

```
  Phase 1 (Batch)       Phase 2 (Triggers)     Phase 3 (Opus RT)
  ┌─────────────┐       ┌────────────────┐     ┌───────────────┐
  │ DB migration │──────>│ Trigger detect │────>│ Opus deep     │
  │ Batch job    │       │ Sonnet quick   │     │ Budget caps   │
  │ Shadow mode  │       │ A/B test start │     │ Memory writes │
  │ 2-3 days     │       │ 3-4 days       │     │ 2-3 days      │
  └─────────────┘       └────────────────┘     └───────────────┘
    GATE: NPS lift?       GATE: engagement?     GATE: Opus > Sonnet?
```

Each phase has explicit validation gates. No sunk-cost continuation.

---

## Decision Summary

| Factor | A (Batch) | B (Real-Time) | C (Hybrid) |
|---|---|---|---|
| Monthly delta | +$2.25 | +$82.50 | +$4.80 |
| Latency | 0ms | +2-5s | 0-3s (2% of msgs) |
| Freshness | 24h stale | Perfect | Good (minutes) |
| Effort | 2-3 days | 5-7 days | 8-10 days (phased) |
| Risk | Low | High | Medium |
| Rollback | Easy | Hard | Easy (per-phase) |

**Recommendation**: Start Phase 1 (batch) to validate at +$2.25/user/month. If promising, proceed incrementally. Opus 4.6 pricing ($5/$25/MTok) makes this 3x cheaper than Doc 08's original model -- even full hybrid adds only 10% to per-user costs.

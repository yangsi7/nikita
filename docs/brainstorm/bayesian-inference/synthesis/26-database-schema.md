# 26 — Database Schema: Bayesian State Storage

**Series**: Bayesian Inference for AI Companions — Synthesis
**Date**: 2026-02-16
**Inputs**: Phase 2 ideas (12, 19) + Phase 3 evaluations (22, 23) + Architecture (Doc 24)
**Status**: FINAL

---

## 1. Schema Overview

The Bayesian system requires one new table (`bayesian_states`), one logging table (`bayesian_shadow_log`), and one A/B test table. No existing tables are modified — the Bayesian state exists alongside the current system.

```
EXISTING TABLES (unchanged):
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ user_metrics      │  │ user_vice_prefs  │  │ emotional_state  │
│ (Decimal scores)  │  │ (8 floats)       │  │ (4D + conflict)  │
│ deterministic     │  │ deterministic    │  │ deterministic    │
└──────────────────┘  └──────────────────┘  └──────────────────┘

NEW TABLE (additive):
┌──────────────────────────────────────────────────────────────┐
│                    bayesian_states                             │
│  user_id UUID PK → auth.users                                │
│  state_json JSONB — complete Bayesian state (~2-3 KB)         │
│  version INTEGER — optimistic locking                        │
│  created_at TIMESTAMPTZ                                      │
│  updated_at TIMESTAMPTZ                                      │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Table Definitions

### 2.1 `bayesian_states` — Core State Table

```sql
-- Migration: 001_create_bayesian_states.sql

CREATE TABLE IF NOT EXISTS public.bayesian_states (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    state_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- GIN index for analytics queries on JSONB fields
CREATE INDEX IF NOT EXISTS idx_bayesian_states_gin
    ON public.bayesian_states USING GIN (state_json);

-- B-tree index for finding active players
CREATE INDEX IF NOT EXISTS idx_bayesian_states_updated
    ON public.bayesian_states (updated_at DESC);

-- Partial index for recently active players (most queries)
CREATE INDEX IF NOT EXISTS idx_bayesian_states_active
    ON public.bayesian_states (user_id)
    WHERE updated_at > now() - INTERVAL '7 days';

-- Row Level Security
ALTER TABLE public.bayesian_states ENABLE ROW LEVEL SECURITY;

-- Players can only read/write their own state
CREATE POLICY "Users access own bayesian state"
    ON public.bayesian_states
    FOR ALL
    USING (auth.uid() = user_id);

-- Service role can access all states (for admin/analytics)
CREATE POLICY "Service role full access"
    ON public.bayesian_states
    FOR ALL
    TO service_role
    USING (true);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_bayesian_states_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    NEW.version = OLD.version + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER bayesian_states_update_timestamp
    BEFORE UPDATE ON public.bayesian_states
    FOR EACH ROW
    EXECUTE FUNCTION update_bayesian_states_timestamp();

COMMENT ON TABLE public.bayesian_states IS
    'Complete Bayesian inference state per player. Single JSONB document '
    'containing all posteriors, emotional state, and metadata. '
    'See docs/brainstorm/bayesian-inference/ for schema documentation.';
```

### 2.2 `bayesian_shadow_log` — Shadow Mode Comparison

```sql
-- Migration: 002_create_bayesian_shadow_log.sql

CREATE TABLE IF NOT EXISTS public.bayesian_shadow_log (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    message_id UUID,  -- correlation with message processing
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Deterministic scores (from existing system)
    det_intimacy DECIMAL(5,2),
    det_passion DECIMAL(5,2),
    det_trust DECIMAL(5,2),
    det_secureness DECIMAL(5,2),
    det_composite DECIMAL(5,2),

    -- Bayesian scores (from new system)
    bay_intimacy DECIMAL(5,2),
    bay_passion DECIMAL(5,2),
    bay_trust DECIMAL(5,2),
    bay_secureness DECIMAL(5,2),
    bay_composite DECIMAL(5,2),

    -- Divergence metrics
    intimacy_divergence DECIMAL(5,3),
    passion_divergence DECIMAL(5,3),
    trust_divergence DECIMAL(5,3),
    secureness_divergence DECIMAL(5,3),
    composite_divergence DECIMAL(5,3),

    -- Context
    chapter INTEGER,
    total_messages INTEGER,
    bayesian_latency_ms DECIMAL(6,2)
);

-- Index for time-series queries
CREATE INDEX IF NOT EXISTS idx_shadow_log_time
    ON public.bayesian_shadow_log (timestamp DESC);

-- Index for per-user analysis
CREATE INDEX IF NOT EXISTS idx_shadow_log_user
    ON public.bayesian_shadow_log (user_id, timestamp DESC);

-- Auto-partition by month (if volume warrants it)
-- For now, simple retention policy via pg_cron
-- DELETE FROM bayesian_shadow_log WHERE timestamp < now() - INTERVAL '90 days';

COMMENT ON TABLE public.bayesian_shadow_log IS
    'Comparison log between deterministic and Bayesian scoring systems. '
    'Used during shadow mode (Phase 1) to validate Bayesian accuracy. '
    'Retained for 90 days, then pruned by pg_cron.';
```

### 2.3 `bayesian_ab_assignments` — A/B Test Tracking

```sql
-- Migration: 003_create_bayesian_ab_assignments.sql

CREATE TABLE IF NOT EXISTS public.bayesian_ab_assignments (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    cohort VARCHAR(20) NOT NULL,  -- 'control', 'bayesian_phase2', 'bayesian_phase3', etc.
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    phase INTEGER NOT NULL DEFAULT 2
);

CREATE INDEX IF NOT EXISTS idx_ab_cohort
    ON public.bayesian_ab_assignments (cohort);

COMMENT ON TABLE public.bayesian_ab_assignments IS
    'A/B test cohort assignments for Bayesian system rollout. '
    'Stable assignment per user (hash-based, recorded here for audit).';
```

---

## 3. JSONB State Schema

### 3.1 Complete Schema Definition

The `state_json` column in `bayesian_states` contains this structure:

```jsonc
{
    // ── METRICS (Beta posteriors) ──────────────────────
    // Each metric: {alpha, beta} → mean = alpha/(alpha+beta)
    "metrics": {
        "intimacy": {"alpha": 5.5, "beta": 4.5},      // mean: 0.55
        "passion": {"alpha": 4.0, "beta": 6.0},        // mean: 0.40
        "trust": {"alpha": 5.0, "beta": 5.0},          // mean: 0.50
        "secureness": {"alpha": 4.0, "beta": 6.0}      // mean: 0.40
    },

    // ── SKIP DECISION (Beta posterior) ─────────────────
    // P(skip) ~ Beta(alpha, beta)
    // Phase 2+: used for Thompson Sampling
    // Phase 1: computed but not used for decisions
    "skip": {
        "alpha": 3.0,
        "beta": 7.0      // mean: 0.30 (30% skip rate)
    },

    // ── TIMING (Dirichlet posterior) ───────────────────
    // Distribution over 5 timing buckets
    // [instant, fast, moderate, slow, very_slow]
    "timing": {
        "dirichlet": [0.5, 1.0, 2.0, 3.0, 2.5]
    },

    // ── VICE PREFERENCES (Dirichlet posterior) ─────────
    // 8 categories: intellectual_dominance, risk_taking, substances,
    // sexuality, emotional_intensity, rule_breaking, dark_humor, vulnerability
    "vice": {
        "dirichlet": [2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0]
    },

    // ── EMOTIONAL STATE ────────────────────────────────
    // Bayesian state machine (Phase 3+)
    "emotional": {
        "current_state": "content",       // One of 6 states
        "state_probabilities": {           // Full belief over states
            "content": 0.45,
            "playful": 0.25,
            "anxious": 0.10,
            "guarded": 0.10,
            "confrontational": 0.05,
            "withdrawn": 0.05
        },
        "messages_in_state": 3,           // For minimum transition constraint
        "transition_cause": ""            // Narrative accountability
    },

    // ── STRESS (Dual-decay model, Doc 21) ──────────────
    "stress": {
        "acute": 0.0,       // Fast decay (half-life ~3 messages)
        "chronic": 0.0      // Slow decay (half-life ~23 messages)
    },

    // ── ENGAGEMENT PATTERN (renamed from "attachment", Doc 21) ──
    // Dirichlet over: responsive, hyperactive, withdrawn, inconsistent
    "engagement": {
        "dirichlet": [3.0, 1.0, 1.0, 1.0]
    },

    // ── SURPRISE TRACKING ──────────────────────────────
    "surprise": {
        "history": [0.3, 0.1, 0.5, 1.2, 0.2, 0.8, 0.4],  // Last 7 values
        "tension": 0.15,     // Accumulated tension (decays)
        "last_value": 0.4
    },

    // ── CONTAGION STATE (Phase 4) ──────────────────────
    // What Nikita thinks the player is feeling
    "player_emotion": {
        "estimate": [0.30, 0.30, 0.15, 0.10, 0.10, 0.05],
        // [positive, neutral, concerned, frustrated, sad, angry]
        "coupling": 0.15    // Current contagion coupling constant
    },

    // ── RANDOMNESS (Phase 4) ───────────────────────────
    "randomness": {
        "temperature": 0.8,     // 0=deterministic, 1=max randomness
        "consistency": 0.5      // Recent behavioral consistency score
    },

    // ── INTERACTION HISTORY (for safety checks) ────────
    "recent_valences": [0.5, 0.3, -0.2, 0.6, 0.4],  // Last 20 interaction valences

    // ── METADATA ───────────────────────────────────────
    "meta": {
        "chapter": 1,
        "total_messages": 47,
        "messages_in_chapter": 47,
        "messages_since_llm": 12,     // Messages since last Tier 2/3 escalation
        "last_updated": "2026-02-16T15:30:00Z",
        "created_at": "2026-02-10T09:00:00Z",
        "schema_version": 1
    }
}
```

### 3.2 Schema Size Budget

```
Section                      Fields    Bytes (JSON)
──────────────────────────────────────────────────────
metrics (4 x 2 floats)       8         ~200
skip (2 floats)              2         ~50
timing (5 floats)            5         ~80
vice (8 floats)              8         ~120
emotional (state + probs)    8         ~250
stress (2 floats)            2         ~50
engagement (4 floats)        4         ~80
surprise (7 + 2)             9         ~150
player_emotion (6 + 1)       7         ~130
randomness (2 floats)        2         ~50
recent_valences (20)         20        ~150
meta (7 fields)              7         ~200
──────────────────────────────────────────────────────
TOTAL                        ~82       ~1,510 bytes

With JSON key overhead:      ~2.0 KB per player
At 10,000 players:           ~20 MB
At 100,000 players:          ~200 MB
```

### 3.3 Schema Versioning

The `schema_version` field in metadata enables forward migration:

```python
# nikita/bayesian/state.py

CURRENT_SCHEMA_VERSION = 1

def migrate_state(data: dict) -> dict:
    """Migrate JSONB state to current schema version."""
    version = data.get("meta", {}).get("schema_version", 1)

    if version == 1:
        # Current version, no migration needed
        return data

    # Future migrations:
    # if version == 1:
    #     data = migrate_v1_to_v2(data)
    # if version == 2:
    #     data = migrate_v2_to_v3(data)

    return data
```

---

## 4. Migration from Current Tables

### 4.1 Migration Strategy

The Bayesian system does NOT migrate data from existing tables. Instead:

1. **Phase 1**: New players get a `bayesian_states` row with chapter-appropriate priors. Existing players get one on their next message.
2. **Existing data stays**: `user_metrics`, `user_vice_preferences`, and `emotional_state` tables remain active. The deterministic system continues to read/write them.
3. **Shadow mode**: Both systems run in parallel. The Bayesian system computes independently; the deterministic system handles all game logic.
4. **Cutover (Phase 4+)**: Once the Bayesian system is validated, the deterministic scoring calls can be disabled. The existing tables become read-only archives.

### 4.2 Initial State Creation

```python
async def ensure_bayesian_state(
    user_id: str,
    session,
) -> BayesianPlayerState:
    """Load or create Bayesian state for a player.

    Called on every message. Creates default state if none exists.
    """
    result = await session.execute(
        text("SELECT state_json FROM bayesian_states WHERE user_id = :uid"),
        {"uid": user_id},
    )
    row = result.fetchone()

    if row:
        data = migrate_state(row[0])
        return BayesianPlayerState.from_json(user_id, data)

    # New state — determine chapter from existing user data
    user_result = await session.execute(
        text("SELECT chapter FROM user_game_state WHERE user_id = :uid"),
        {"uid": user_id},
    )
    user_row = user_result.fetchone()
    chapter = user_row[0] if user_row else 1

    state = BayesianPlayerState.default_for_chapter(user_id, chapter)

    # Insert new row
    await session.execute(
        text("""
            INSERT INTO bayesian_states (user_id, state_json)
            VALUES (:uid, :state)
            ON CONFLICT (user_id) DO NOTHING
        """),
        {"uid": user_id, "state": state.to_json()},
    )
    await session.commit()

    return state
```

### 4.3 Optimistic Locking for Concurrent Updates

```python
async def save_bayesian_state(
    state: BayesianPlayerState,
    expected_version: int,
    session,
) -> bool:
    """Save state with optimistic locking.

    Returns True if save succeeded, False if version conflict.
    """
    result = await session.execute(
        text("""
            UPDATE bayesian_states
            SET state_json = :state
            WHERE user_id = :uid AND version = :ver
        """),
        {
            "uid": state.user_id,
            "state": state.to_json(),
            "ver": expected_version,
        },
    )
    await session.commit()

    if result.rowcount == 0:
        # Version conflict — another request updated the state
        # Reload and retry (caller's responsibility)
        return False
    return True
```

---

## 5. Query Patterns

### 5.1 Hot Path: Per-Message Load + Save

```sql
-- Load (called every message, ~5ms)
SELECT state_json, version
FROM bayesian_states
WHERE user_id = $1;

-- Save (called every message, ~5ms)
UPDATE bayesian_states
SET state_json = $1
WHERE user_id = $2 AND version = $3;
```

### 5.2 Analytics: Aggregate Queries

```sql
-- Average composite score across all active players
SELECT
    AVG(
        0.30 * (state_json->'metrics'->'intimacy'->>'alpha')::float /
        ((state_json->'metrics'->'intimacy'->>'alpha')::float +
         (state_json->'metrics'->'intimacy'->>'beta')::float)
        +
        0.25 * (state_json->'metrics'->'passion'->>'alpha')::float /
        ((state_json->'metrics'->'passion'->>'alpha')::float +
         (state_json->'metrics'->'passion'->>'beta')::float)
        +
        0.25 * (state_json->'metrics'->'trust'->>'alpha')::float /
        ((state_json->'metrics'->'trust'->>'alpha')::float +
         (state_json->'metrics'->'trust'->>'beta')::float)
        +
        0.20 * (state_json->'metrics'->'secureness'->>'alpha')::float /
        ((state_json->'metrics'->'secureness'->>'alpha')::float +
         (state_json->'metrics'->'secureness'->>'beta')::float)
    ) * 100 AS avg_composite
FROM bayesian_states
WHERE updated_at > now() - INTERVAL '7 days';

-- Distribution of emotional states
SELECT
    state_json->'emotional'->>'current_state' AS emotional_state,
    COUNT(*) AS player_count
FROM bayesian_states
WHERE updated_at > now() - INTERVAL '7 days'
GROUP BY 1
ORDER BY 2 DESC;

-- Players with high tension (potential boss encounters)
SELECT
    user_id,
    (state_json->'surprise'->>'tension')::float AS tension,
    state_json->'meta'->>'chapter' AS chapter
FROM bayesian_states
WHERE (state_json->'surprise'->>'tension')::float > 0.5
ORDER BY tension DESC;

-- Engagement pattern distribution
SELECT
    CASE
        WHEN (state_json->'engagement'->'dirichlet'->0)::float >
             GREATEST(
                 (state_json->'engagement'->'dirichlet'->1)::float,
                 (state_json->'engagement'->'dirichlet'->2)::float,
                 (state_json->'engagement'->'dirichlet'->3)::float
             )
        THEN 'responsive'
        WHEN (state_json->'engagement'->'dirichlet'->1)::float >
             GREATEST(
                 (state_json->'engagement'->'dirichlet'->0)::float,
                 (state_json->'engagement'->'dirichlet'->2)::float,
                 (state_json->'engagement'->'dirichlet'->3)::float
             )
        THEN 'hyperactive'
        WHEN (state_json->'engagement'->'dirichlet'->2)::float >
             GREATEST(
                 (state_json->'engagement'->'dirichlet'->0)::float,
                 (state_json->'engagement'->'dirichlet'->1)::float,
                 (state_json->'engagement'->'dirichlet'->3)::float
             )
        THEN 'withdrawn'
        ELSE 'inconsistent'
    END AS dominant_pattern,
    COUNT(*) AS player_count
FROM bayesian_states
WHERE updated_at > now() - INTERVAL '7 days'
GROUP BY 1;
```

### 5.3 Debugging: Single Player Deep Dive

```sql
-- Full state dump for a specific player
SELECT
    user_id,
    state_json,
    version,
    created_at,
    updated_at
FROM bayesian_states
WHERE user_id = 'player-uuid-here';

-- Shadow comparison history for a specific player
SELECT
    timestamp,
    det_composite,
    bay_composite,
    composite_divergence,
    bayesian_latency_ms
FROM bayesian_shadow_log
WHERE user_id = 'player-uuid-here'
ORDER BY timestamp DESC
LIMIT 50;
```

---

## 6. Data Retention & Maintenance

### 6.1 Retention Policies

```sql
-- pg_cron: Clean up shadow log (keep 90 days)
SELECT cron.schedule(
    'cleanup_shadow_log',
    '0 3 * * *',  -- Daily at 3 AM UTC
    $$DELETE FROM public.bayesian_shadow_log
      WHERE timestamp < now() - INTERVAL '90 days'$$
);

-- pg_cron: Clean up stale Bayesian states (inactive >6 months)
-- Note: does NOT delete — archives to cold storage
SELECT cron.schedule(
    'archive_stale_bayesian',
    '0 4 * * 0',  -- Weekly on Sunday at 4 AM UTC
    $$UPDATE public.bayesian_states
      SET state_json = state_json || '{"archived": true}'::jsonb
      WHERE updated_at < now() - INTERVAL '180 days'
        AND NOT (state_json ? 'archived')$$
);
```

### 6.2 Backup Strategy

The `bayesian_states` table is included in Supabase's standard daily backups. No additional backup infrastructure needed.

For disaster recovery: the state can be reconstructed from chapter defaults at the cost of losing learned posteriors. A player who returns after a state loss would effectively start over from chapter-appropriate priors — a graceful degradation.

---

## 7. Performance Considerations

### 7.1 JSONB vs. Separate Columns

**Decision**: JSONB (not separate columns).

**Rationale**:
1. **Schema flexibility**: JSONB allows adding new posterior types without migration
2. **Atomic reads/writes**: One column = one I/O operation
3. **Good enough performance**: At ~2 KB, JSONB parse overhead is ~5 microseconds
4. **Analytics via GIN index**: Complex queries work, just slower than columnar

**When to reconsider**: If JSONB grows beyond 5 KB, OR if analytics queries become a bottleneck, consider extracting hot-path fields (composite_score, emotional_state) to dedicated columns while keeping the full JSONB for the complete state.

### 7.2 Connection Pooling

The Bayesian pre-stage adds one read and one write per message. With Supabase's PgBouncer (transaction mode), this is 2 additional pool checkouts per message. At 1K DAU (15K messages/day = ~0.5 req/s average, ~5 req/s peak), this is well within PgBouncer's default limits.

### 7.3 Write Contention

Two messages from the same player arriving simultaneously could cause a write conflict (optimistic locking failure). The probability is low (players rarely send two messages in the same second), and the impact is minimal (the second message retries with the updated state).

Worst case: a retry adds ~10ms latency. The system should log retries and alert if the rate exceeds 1%.

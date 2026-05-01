# Data Layer Validation Report — ITERATION 2

**Spec:** specs/216-onboarding-redesign-cinematic/subspecs/216-D-data-layer-inference/spec.md
**Validator:** sdd-data-layer-validator
**Status:** PASS
**Timestamp:** 2026-04-29
**Iteration:** 2

## Summary
- CRITICAL: 0
- HIGH: 0
- MEDIUM: 0
- LOW: 1

## Iteration 1 Findings — Resolution Verification

| ID | Severity | Issue | Iter-2 Resolution | Status |
|----|----------|-------|-------------------|--------|
| HIGH-1 | HIGH | Backfill predicate `length(cache_key) < 64` would double-hash any pre-existing 60-63 char raw cache_keys, AND skip already-hashed values whose length happened to match. | AC D1.8 explicitly mandates regex predicate `cache_key !~ '^[a-f0-9]{64}$'`. Migration SQL skeleton (lines 84-87) uses the regex predicate with inline comment explaining rationale. Post-migration test (`tests/db/test_backstory_cache_hashed.py`) asserts ALL rows match `^[a-f0-9]{64}$`. | CLOSED |
| MED-1 | MEDIUM | Spec narrative said "JSONB embedding" but DB-level CHECK constraints require top-level columns. | AC D1.10 added: explicitly mandates top-level columns on `public.users` (NOT JSONB embedding); ORM extends `User` (not `UserProfile`). Migration SQL (lines 68-71) uses `ALTER TABLE public.users ADD COLUMN`. | CLOSED |
| MED-2 | MEDIUM | CHECK constraints would fail on idempotent re-run (no `ADD CONSTRAINT IF NOT EXISTS` in PostgreSQL). | AC D1.11 added: requires DO-block IF NOT EXISTS guards per canonical pattern in `20260414213313_add_profile_fields_and_backstory_cache.sql:28-41`. Note: migration SQL skeleton at lines 74-76 still shows bare `ADD CONSTRAINT` — AC mandates DO-block wrapper at implementation time. AC is the authoritative contract; skeleton inconsistency tracked as LOW finding below. | CLOSED |
| MED-3 | MEDIUM | `archetype_candidates` JSONB column missing for W4 walk G.6 verification. | AC D1.12 added: `archetype_candidates` JSONB column on `users` to persist the 3 LLM-picked candidate archetypes (separate from final `backstory_pick`). | CLOSED |
| MED-4 | MEDIUM | Migration number placeholder "NNN" unresolved. | Open Question Q1 explicitly defers resolution to PR-open time (next available number). Acceptable as documented open question. | DEFERRED (acceptable) |
| LOW-1 | LOW | brand_resonance_signal computation formula TBD. | Documented as Open Question Q4 with placeholder (cosine similarity). | DEFERRED (acceptable) |
| LOW-2 | LOW | Cohort chip seed list needs UX review. | Documented as Open Question Q3. | DEFERRED (acceptable) |

## Findings (Iteration 2)

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| LOW | Migration SQL Hygiene | Migration SQL skeleton (lines 73-76) shows bare `ALTER TABLE ... ADD CONSTRAINT` without DO-block IF NOT EXISTS wrapper, although AC D1.11 mandates the wrapper. Skeleton and AC are inconsistent; an implementer copying the skeleton verbatim could miss the DO-block requirement. | spec.md:73-76 vs AC D1.11 line 29 | Update migration SQL skeleton to demonstrate the DO-block pattern explicitly. Non-blocking (AC supersedes skeleton at implementation time). |

## Entity Inventory

| Entity | Attributes | PK | FK | RLS | Notes |
|--------|------------|----|----|-----|-------|
| public.users (extended) | + big5_vector JSONB DEFAULT '{}', + backstory_seed TEXT NULL (≤300), + brand_resonance_signal NUMERIC NULL (0-1), + archetype_candidates JSONB | id (auth.uid()) | — | YES (existing + policies updated per D1.4) | Top-level columns per D1.10 (NOT JSONB embedding) |
| public.backstory_cache (modified) | cache_key TEXT → sha256-hex via D1.8 backfill (regex predicate) | (existing) | user_id → users.id | YES (existing) | Closes #446 PII leak; idempotent regex backfill |

## Relationship Map

```
auth.users 1──1 public.users (id maps via auth.uid())
public.users 1──N public.backstory_cache (user_id FK)
```

## RLS Policy Checklist
- [x] RLS enabled on `public.users` (verified per D1.4)
- [x] SELECT/UPDATE/INSERT user-scoped via `(SELECT auth.uid()) = id`
- [x] UPDATE policy includes `WITH CHECK ((SELECT auth.uid()) = id)` per D1.4
- [x] Post-migration verification via `mcp__supabase__list_policies` mandated
- [x] backstory_cache policies (existing) unaffected by sha256 cache_key shape change

## Index Requirements

| Table | Column(s) | Type | Query Pattern |
|-------|-----------|------|---------------|
| backstory_cache | cache_key | (existing UNIQUE/INDEX) | sha256-hex lookup; no schema change needed |
| users | id | PK (existing) | auth.uid() lookup |
| users | big5_vector / archetype_candidates (JSONB) | not indexed | accessed by user_id PK lookup, not JSON path; no GIN/expression index warranted |

No new indexes required.

## DB Migration Checklist (per .claude/rules/testing.md)

- [x] `ALTER TABLE public.users ENABLE ROW LEVEL SECURITY` — already enabled (verified via D1.4)
- [x] `CREATE POLICY` coverage — D1.4 mandates SELECT/UPDATE/INSERT policies user-scoped via `(SELECT auth.uid()) = id`
- [x] UPDATE policy `WITH CHECK` clause — explicitly required by D1.4
- [x] Post-migration `mcp__supabase__list_policies` verification — mandated by D1.4
- [x] CHECK constraint idempotency — D1.11 mandates DO-block IF NOT EXISTS wrapper
- [x] Backfill idempotency — D1.8 mandates regex predicate (not length-based)

## Recommendations

1. **LOW (non-blocking):** Update migration SQL skeleton (spec.md:73-76) to demonstrate the DO-block IF NOT EXISTS wrapper that AC D1.11 mandates. Example per canonical pattern in `20260414213313_add_profile_fields_and_backstory_cache.sql:28-41`:

   ```sql
   DO $$ BEGIN
     IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'backstory_seed_length') THEN
       ALTER TABLE public.users ADD CONSTRAINT backstory_seed_length
         CHECK (backstory_seed IS NULL OR length(backstory_seed) <= 300);
     END IF;
   END $$;
   ```

   This prevents an implementer from copying the skeleton verbatim and missing the idempotency guard. AC supersedes skeleton at implementation time, so this is documentation hygiene only.

## Verdict

**PASS.** All iteration-1 CRITICAL/HIGH/MEDIUM findings are CLOSED or properly DEFERRED via documented open questions. The HIGH-1 backfill predicate finding is fully closed: AC D1.8 mandates regex predicate `cache_key !~ '^[a-f0-9]{64}$'` (idempotent + safe under all length conditions), the migration SQL skeleton implements it correctly, and the post-migration test asserts the invariant. One LOW finding (skeleton/AC inconsistency on DO-block wrapper) does not block planning. Spec 216-D is ready to proceed past GATE 2.

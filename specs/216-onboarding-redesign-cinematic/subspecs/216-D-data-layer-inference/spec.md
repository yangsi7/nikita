# Subspec 216-D — Data Layer + Inference

**Parent**: `specs/216-onboarding-redesign-cinematic/spec.md` FR-06, FR-09, NR-03, NR-05
**PR boundary**: 216-D (parallel with 216-B; depends only on 216-A merged)
**Estimated**: ~250 LOC (migration + Big5 judge + archetypes + cohort cache) + ~120 LOC tests
**Status**: Draft (GATE 1)

---

## Scope

Server-side personality + identity layer. Adds 3 columns to `users.onboarding_profile` JSONB embedding (`big5_vector`, `backstory_seed`, `brand_resonance_signal`) with RLS enabled and policies. Implements per-turn `claude-haiku-4-5` Big Five inference judge writing to `big5_vector`. Curated 12-archetype taxonomy in `archetypes.py` with meta-prompt picker + 3-persona generation. Hand-seeded `cohort_chips.py` with 6-8 (city, occupation) → chip-list cohorts. Hashes raw PII in `backstory_cache.cache_key` (closes #446).

Big Five framework is **HIDDEN** from UI per NR-05 (Replika 2025 / Pi.ai precedent). `big5_vector` and `brand_resonance_signal` NEVER appear in any UI response payload.

## Acceptance Criteria

| AC | Description | Severity |
|----|-------------|----------|
| **D1.1** | Migration `supabase/migrations/NNN_user_profile_inference.sql` adds `users.onboarding_profile.big5_vector` JSONB (5 floats `{O, C, E, A, N}` + `confidence: {O: 0.x, C: 0.x, ...}`). Default `'{}'::jsonb`. | CRIT |
| **D1.2** | Migration adds `users.onboarding_profile.backstory_seed` TEXT NULL (≤300 chars enforced via CHECK constraint). | HIGH |
| **D1.3** | Migration adds `users.onboarding_profile.brand_resonance_signal` NUMERIC NULL with CHECK (`val >= 0 AND val <= 1`). | HIGH |
| **D1.4** | RLS enabled on `users` (already on) AND policies updated: SELECT/UPDATE/INSERT user-scoped via `(SELECT auth.uid()) = id`. UPDATE policy includes `WITH CHECK ((SELECT auth.uid()) = id)`. Verified via `mcp__supabase__list_policies` post-migration. | CRIT |
| **D1.5** | Per-turn `claude-haiku-4-5` judge runs after each prose answer (saturday/geek/together/hobbies/same_weird_if/optional probes). Updates `big5_vector` via merge: dimension scores averaged, confidence updated per Bayesian update. Once any dim confidence ≥0.7, M4 short-circuits further probes on that axis. | HIGH |
| **D1.6** | `nikita/agents/onboarding/archetypes.py` exposes 12 curated labels: `the runner`, `the maker`, `the watcher`, `the climber`, `the seeker`, `the architect`, `the survivor`, `the rebel`, `the romantic`, `the wanderer`, `the host`, `the fugitive`. Meta-prompt `pick_three_archetypes(big5, city, occupation, hobbies, darkness) -> list[ArchetypeCard]` returns 3 picks from the 12-list ONLY. Validator rejects invented labels. | HIGH |
| **D1.7** | `nikita/agents/onboarding/cohort_chips.py` exposes 6-8 hand-seeded `(city, occupation)` cohorts: e.g., `(zurich, designer)`, `(london, finance)`, `(berlin, nurse)`, `(brooklyn, dev)`, `(sf, founder)`, `(stockholm, researcher)`. Each cohort returns ordered chip list of ~12 plausible options. Cache key = sha256 of `(lowercase_city, lowercase_occupation)`, NEVER raw values. | HIGH |
| **D1.8** | `cache_key` in `backstory_cache` table hashed via sha256 (closes #446 PII raw city in cache_key). Existing rows migrated to hashed format via `UPDATE backstory_cache SET cache_key = encode(sha256(cache_key::bytea), 'hex')` in migration. | HIGH |
| **D1.9** | Big5 inference NEVER surfaces in any UI response. `TurnOutput` schema does NOT contain `big5_vector` field. Endpoint response payload audited (test_api_response_no_big5.py). | CRIT |

## Critical Files

### NEW migration
- `supabase/migrations/NNN_user_profile_inference.sql` — schema migration with ALTER TABLE + ENABLE RLS + CREATE POLICY + UPDATE backstory_cache.cache_key. Test via `supabase db reset` locally + `mcp__supabase__list_policies` post-deploy.

### NEW Python modules
- `nikita/agents/onboarding/big5_judge.py` — `update_big5_vector(state: WizardSlots, deps: ConverseDeps) -> dict` Haiku-backed judge. Reads `state.slots_dict + recent_messages`, returns updated `big5_vector` JSONB. Per-dim confidence Bayesian merge.
- `nikita/agents/onboarding/archetypes.py` — `ARCHETYPES: list[Literal[...]]` (12 entries) + `ArchetypeCard(BaseModel)` + `pick_three_archetypes(...)` Opus meta-prompt + `generate_three_personas(picked_archetype, ...)` Opus prompt. Validator: every output label MUST be in `ARCHETYPES`.
- `nikita/agents/onboarding/cohort_chips.py` — `CohortCache` dict + `lookup_cohort(city: str, occupation: str) -> list[ChipOption] | None` with sha256 hash key.

### EXTENDED ORM
- `nikita/db/models/user.py` — extend `UserProfile` (or `OnboardingProfile` JSONB embedding) with `big5_vector`, `backstory_seed`, `brand_resonance_signal` typed fields.

### EXTENDED contracts
- `nikita/api/schemas/onboarding.py` — `BackstoryArchetypeResponse(BaseModel)` schema for the 3-card payload (label + 150-char prose only; NO archetype rationale prose, NO big5 vector).

## Tests to Write

| Test File | Focus | AC |
|-----------|-------|-----|
| `tests/db/migrations/test_NNN_user_profile_inference.py` | columns added, RLS enabled, policies queryable | D1.1, D1.2, D1.3, D1.4 |
| `tests/agents/onboarding/test_big5_judge.py` | mock Haiku golden vectors; Bayesian confidence merge; ≥0.7 short-circuit | D1.5 |
| `tests/agents/onboarding/test_archetypes.py` | 12-list validator rejects invented labels; meta-prompt deterministic with fixed Big5 | D1.6 |
| `tests/agents/onboarding/test_cohort_chips.py` | 6-8 cohorts return chip lists; sha256 hash key (no raw PII) | D1.7 |
| `tests/api/routes/test_no_big5_in_response.py` | call /onboarding/answer 12 turns; assert no response payload contains "big5", "vector", "OCEAN", "extraversion" | D1.9 |
| `tests/db/test_backstory_cache_hashed.py` | new rows have sha256 cache_key, no raw city | D1.8 |

## Migration SQL Skeleton

```sql
-- supabase/migrations/NNN_user_profile_inference.sql

BEGIN;

-- Add columns to users.onboarding_profile JSONB embedding
ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS big5_vector JSONB DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS backstory_seed TEXT,
  ADD COLUMN IF NOT EXISTS brand_resonance_signal NUMERIC;

-- Constraints
ALTER TABLE public.users
  ADD CONSTRAINT backstory_seed_length CHECK (backstory_seed IS NULL OR length(backstory_seed) <= 300),
  ADD CONSTRAINT brand_resonance_range CHECK (brand_resonance_signal IS NULL OR (brand_resonance_signal >= 0 AND brand_resonance_signal <= 1));

-- RLS already enabled on public.users; verify policies cover new columns
-- (column-level grants not used; row-level policies apply to all columns)

-- Hash existing backstory_cache.cache_key values (closes #446 PII leak)
UPDATE public.backstory_cache
SET cache_key = encode(sha256(cache_key::bytea), 'hex')
WHERE cache_key IS NOT NULL AND length(cache_key) < 64;  -- not already hashed

COMMIT;
```

Verify post-migration via:
```python
result = await mcp__supabase__list_policies(schema="public", table="users")
assert any(p["policyname"].startswith("user_") for p in result)
```

## Big Five Bayesian Merge

Per-turn confidence update follows weighted average:
```python
def merge_dim(prior: float, prior_conf: float, new_score: float, new_conf: float) -> tuple[float, float]:
    # Weighted average — higher confidence dominates
    total_weight = prior_conf + new_conf
    if total_weight == 0:
        return new_score, new_conf
    merged_score = (prior * prior_conf + new_score * new_conf) / total_weight
    merged_conf = min(0.95, prior_conf + new_conf * (1 - prior_conf))  # asymptotic to 0.95
    return merged_score, merged_conf
```

Confidence thresholds:
- 0.5 → "weak signal", continue probing
- 0.7 → "strong signal", M4 short-circuit further probes on that dim
- 0.95 → asymptotic ceiling

## Open Questions

- **Q1**: Migration number — next available in `supabase/migrations/` directory. Resolve at PR-open time.
- **Q2**: Archetype label vocabulary — 12-list is locked, but rationale prose generation uses dark-luxe Nikita voice; sample tones in 216-D PR.
- **Q3**: Cohort chip seed list — 6-8 (city, occupation) pairs hand-curated. Confirm with UX review during implementation.
- **Q4**: brand_resonance_signal computation — formula TBD (Big5 + hobbies + city → [0,1]). Default placeholder: cosine similarity between user vector and brand-archetype vector. Resolve in 216-D /clarify.

## References

- Master spec FR-06, FR-09, NR-03, NR-05
- W3 walk finding #446 (PII raw city in cache_key)
- BFI-2-XS reference: Soto & John 2017 — used as inference TARGET, never as survey
- BIG5-CHAT (ACL 2025): https://arxiv.org/abs/2410.16491 — LLM Big5 inference from prose
- Replika 2025 / Pi.ai precedent: hide-the-framework
- `.claude/rules/testing.md` — DB Migration Checklist

## Data Layer Validation Report

**Spec:** `specs/111-consecutive-crises/spec.md`
**Status:** PASS
**Timestamp:** 2026-03-11T00:00:00Z
**Validator:** sdd-data-layer-validator

### Summary
- CRITICAL: 0
- HIGH: 0
- MEDIUM: 2
- LOW: 2

### Findings

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| MEDIUM | Data Integrity | `users.conflict_details` column has no DEFAULT (is bare `jsonb`), while `nikita_emotional_states.conflict_details` defaults to `'{}'::jsonb`. `from_jsonb()` handles `None` gracefully (returns defaults), but inconsistent column defaults may cause confusion for raw SQL queries. | `baseline_schema.sql:61` vs `:382` | Document that `users.conflict_details` may be NULL and `from_jsonb(None)` returns defaults. Consider a future migration to add `DEFAULT '{}'::jsonb` to `users.conflict_details` for consistency. Not blocking — the Pydantic code handles both cases. |
| MEDIUM | Indexes | The GIN index on `nikita_emotional_states.conflict_details` indexes the full JSONB blob. After adding `consecutive_crises` to the JSONB, admin queries like `WHERE conflict_details->>'consecutive_crises' > '2'` will use this GIN index, but GIN containment queries (`@>`) are more efficient than key-path queries (`->>`) for JSONB. The spec acknowledges this tradeoff (Section 2, Devil's Advocate). | `baseline_schema.sql:683`, `spec.md:53` | No action needed now. If admin dashboard queries on `consecutive_crises` become frequent, consider a generated/expression index: `CREATE INDEX idx_consecutive_crises ON nikita_emotional_states ((conflict_details->>'consecutive_crises'))`. This is an optimization, not a correctness issue. |
| LOW | Schema Design | `last_crisis_at` is typed as `str | None` (ISO string) rather than a proper datetime type. This is consistent with the existing pattern (`last_temp_update: str | None` at `models.py:392`), so it follows project conventions. However, ISO strings in JSONB prevent temporal SQL operations without casting. | `spec.md:74-75`, `models.py:392` | Acceptable — follows existing project convention. Document that temporal comparisons require `::timestamptz` cast in raw SQL. |
| LOW | Documentation | The spec mentions `conflict_details` exists on both `users` table (line 61 in baseline) and `nikita_emotional_states` table (line 382). The spec targets `nikita_emotional_states.conflict_details` via `ConflictDetails.from_jsonb()` in the scoring service, but the breakup engine receives `conflict_details` as a parameter from the caller. The spec should clarify which table's `conflict_details` column is the source of truth for the breakup check. | `spec.md:136-138`, `breakup.py:147-152` | Add a note clarifying that `check_thresholds()` receives `conflict_details` from `nikita_emotional_states` (passed by the pipeline/caller). Both tables store the same JSONB shape but `nikita_emotional_states` is the authoritative source for temperature/crisis state. |

### Entity Inventory

| Entity | Attributes Affected | PK | FK | RLS | Notes |
|--------|------------|----|----|-----|-------|
| `nikita_emotional_states` | `conflict_details` JSONB (adding `consecutive_crises: int`, `last_crisis_at: str\|null` inside JSONB) | `state_id` (uuid) | `user_id -> users(id) ON DELETE CASCADE` | Yes (4 policies: service_role full, user insert/update/select own) | Primary table. GIN index on `conflict_details`. |
| `users` | `conflict_details` JSONB (same shape, passed to breakup engine) | `id` (uuid) | N/A | Yes (assumed, standard) | Secondary copy. NULL-able, no default. |
| `ConflictDetails` (Pydantic) | Adding `consecutive_crises: int = 0`, `last_crisis_at: str \| None = None` | N/A | N/A | N/A | Application-layer model. `from_jsonb()` filters unknown keys and applies defaults for missing keys. |

### Relationship Map

```
users 1──1 nikita_emotional_states (via user_id FK)
  Both tables carry conflict_details JSONB
  ConflictDetails Pydantic model deserializes both
```

### RLS Policy Checklist
- [x] `nikita_emotional_states` has RLS enabled — PASS (`baseline_schema.sql:787`)
- [x] Service role full access policy — PASS (`baseline_schema.sql:870`)
- [x] User isolation (SELECT/INSERT/UPDATE own rows via `auth.uid() = user_id`) — PASS (`baseline_schema.sql:871-873`)
- [x] No new tables introduced — N/A (JSONB-only change, no new RLS needed)
- [x] No new storage buckets — N/A
- [x] No new realtime subscriptions — N/A

### Index Requirements

| Table | Column(s) | Type | Query Pattern | Status |
|-------|-----------|------|---------------|--------|
| `nikita_emotional_states` | `conflict_details` | GIN | JSONB containment queries | EXISTS (line 683) |
| `nikita_emotional_states` | `user_id` | btree | User lookup | EXISTS (line 685) |
| `nikita_emotional_states` | `user_id, conflict_state` | btree (partial) | Active conflict lookup | EXISTS (line 682) |
| N/A | `conflict_details->>'consecutive_crises'` | expression btree | Admin dashboard (future) | NOT NEEDED YET |

### Backward Compatibility Analysis

This is the most critical aspect of this spec. Validation results:

1. **`from_jsonb()` safety** — VERIFIED SAFE. The method at `models.py:400-404` uses `{k: v for k, v in data.items() if k in cls.model_fields}`, which means:
   - Old JSONB rows without `consecutive_crises` / `last_crisis_at` keys will simply not pass those keys to the constructor
   - Pydantic defaults (`0` and `None`) will apply automatically
   - No `KeyError`, no `ValidationError`, no data loss

2. **`to_jsonb()` forward compatibility** — VERIFIED SAFE. `model_dump(mode="json")` at `models.py:408` will include the new fields in output. Old code that reads the JSONB and doesn't know about `consecutive_crises` will simply ignore the extra key (JSONB is schemaless).

3. **NULL handling** — VERIFIED SAFE. `from_jsonb(None)` returns `cls()` (all defaults) at line 402-403. The `users.conflict_details` column can be NULL.

4. **Empty dict handling** — VERIFIED SAFE. `from_jsonb({})` returns `cls()` because the dict comprehension produces no matching keys. The `nikita_emotional_states.conflict_details` defaults to `'{}'::jsonb`.

5. **No migration needed** — CONFIRMED. Adding fields to a Pydantic model that serializes to/from JSONB requires zero DDL changes. PostgreSQL JSONB is schemaless.

6. **GIN index compatibility** — CONFIRMED. The existing GIN index on `conflict_details` automatically indexes any new keys added to the JSONB blob. No index rebuild needed.

7. **Existing test regression** — LOW RISK. Mocks that construct `ConflictDetails()` without the new fields will get `consecutive_crises=0` (the default), which matches the previous hardcoded behavior.

### Supabase PostgreSQL Compatibility

- JSONB with Pydantic `from_jsonb()`/`to_jsonb()` is a well-established pattern in this project (used since Spec 057)
- `Field(ge=0)` validation is application-layer only — no CHECK constraint in PostgreSQL, but this is acceptable given all writes go through the Pydantic model
- `str | None` for timestamps in JSONB is consistent with `last_temp_update` pattern
- No Supabase-specific features (Edge Functions, Storage, Realtime) are affected

### Recommendations

1. **MEDIUM:** Document which table is the authoritative source for crisis state
   - Add a comment to the spec (Section 3, FR-004) clarifying that `breakup.py` receives `conflict_details` from `nikita_emotional_states` via the pipeline caller
   - This prevents future confusion between the `users.conflict_details` and `nikita_emotional_states.conflict_details` columns

2. **MEDIUM:** Consider adding DEFAULT to `users.conflict_details`
   - Currently `jsonb` (nullable, no default) vs `nikita_emotional_states` which has `DEFAULT '{}'::jsonb`
   - Low priority — `from_jsonb(None)` handles it correctly
   - Could be bundled with any future migration touching the `users` table

3. **LOW:** Expression index for admin queries (future)
   - If portal/admin needs to query crisis counts directly in SQL, add: `CREATE INDEX idx_crisis_count ON nikita_emotional_states ((conflict_details->>'consecutive_crises'))`
   - Not needed now — spec explicitly marks portal display as out of scope

4. **LOW:** ISO string timestamps in JSONB
   - Follows existing convention (`last_temp_update`), so no change needed
   - If the project ever standardizes JSONB temporal fields, both should be updated together

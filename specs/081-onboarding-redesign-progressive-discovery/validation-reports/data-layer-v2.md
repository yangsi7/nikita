## Data Layer Validation Report

**Spec:** `specs/081-onboarding-redesign-progressive-discovery/spec.md` (v2)
**Status:** FAIL
**Timestamp:** 2026-03-22T18:30:00Z
**Validator:** sdd-data-layer-validator
**Prior Report:** `data-layer.md` (v1 -- PASS with 4 MEDIUM, 3 LOW)

### Summary
- CRITICAL: 0
- HIGH: 2
- MEDIUM: 3
- LOW: 3

### Changes from v1 Report

v2 spec restructured from a Telegram-only drip system to a portal-first cinematic onboarding. The 3 new columns on `users` remain identical (`onboarding_completed_at`, `drips_delivered`, `welcome_completed`). v2 adds a new `POST /api/v1/onboarding/profile` endpoint that writes to `user_profiles` and `users`. The profile save code path introduces two new HIGH-severity findings against the existing codebase that were not present in v1 (which had no profile endpoint).

### Findings

| # | Severity | Category | Issue | Location | Recommendation |
|---|----------|----------|-------|----------|----------------|
| 1 | HIGH | Schema / API | Spec calls `ProfileRepository.upsert(user_id, location_city, social_scene, drug_tolerance)` but this method does not exist. `ProfileRepository` has `create_profile()` (line 61) and `update_from_onboarding()` (line 96), neither matching the call signature. | Spec line 1354; `nikita/db/repositories/profile_repository.py` lines 61-110 | Add an `upsert()` method to `ProfileRepository` that does INSERT ON CONFLICT UPDATE on `user_profiles.id`, or specify in the spec that the endpoint should call `create_profile()` with a try/except on duplicate key and fall back to field-level update. Document the chosen pattern explicitly. |
| 2 | HIGH | Schema / API | Spec calls `user_repo.complete_onboarding(user_id)` with 1 argument (spec line 1362), but `UserRepository.complete_onboarding()` requires 3 arguments: `(user_id, call_id, profile)` (user_repository.py line 579-584). The existing method sets `onboarding_call_id` and `onboarding_profile` which are voice-onboarding-specific fields. It does NOT set `onboarding_completed_at` (the new column). | Spec line 1362; `nikita/db/repositories/user_repository.py` lines 579-618 | Either: (a) add a new method `complete_portal_onboarding(user_id)` that sets `onboarding_status='completed'`, `onboarded_at=now()`, AND `onboarding_completed_at=now()`, or (b) refactor `complete_onboarding()` to accept optional `call_id`/`profile` with the portal path skipping them. Spec must document which approach to use and confirm that `onboarding_completed_at` is set (currently only `onboarded_at` is mentioned in the existing method). |
| 3 | MEDIUM | Schema | `welcome_completed` ORM model (spec line 1502) declares `default=False, nullable=False` but omits `server_default=text("false")`. When `ALTER TABLE` runs with `NOT NULL DEFAULT false`, PostgreSQL backfills existing rows. However, the ORM model should include `server_default` for consistency with the DDL, especially since `drips_delivered` (spec line 1485) correctly includes `server_default`. | Spec line 1502 | Add `server_default=text("false")` to the `welcome_completed` mapped_column definition to match DDL and maintain consistency with `drips_delivered`. |
| 4 | MEDIUM | Indexes | Phase 2 `check-drips` cron job (spec line 1714) runs every 5 minutes querying users with `onboarding_status = 'completed'`. No index is specified for this query pattern. As the users table grows, this becomes a sequential scan every 5 minutes. | Spec line 1714 (Phase 2 section) | Add a partial index: `CREATE INDEX idx_users_onboarding_completed ON users (id) WHERE onboarding_status = 'completed';` Include this in the migration section as a Phase 2 migration or document it as a deferred optimization. |
| 5 | MEDIUM | Data Integrity | `drips_delivered` JSONB column accepts arbitrary keys but only 7 drip IDs are valid (`first_score`, `portal_intro`, `first_decay`, `chapter_advance`, `boss_warning`, `boss_debrief`, `nikitas_world`). No CHECK constraint or app-layer validation is specified for key names. Invalid drip IDs would silently persist. | Spec lines 1470-1486, 1719-1729 | Document that drip ID validation is app-layer only (in `DripManager.evaluate_user()`), enforced by the `DRIP_DEFINITIONS` constant. Add a code comment in the model noting the 7 valid keys. A DB CHECK constraint is not practical for JSONB key validation, so app-layer is acceptable -- but it must be documented as intentional. |
| 6 | LOW | Schema | `onboarding_completed_at` column is nullable (correct -- NULL means not completed). The DDL (spec line 1454) omits a COMMENT explaining the NULL semantics, but the COMMENT is actually present (spec line 1456-1457). However, the ORM model (spec line 1465) specifies `default=None` which is redundant for a nullable column. Minor style inconsistency. | Spec line 1465 | Remove `default=None` from the ORM definition since `nullable=True` already implies NULL default. Or keep it for explicitness -- either way is acceptable. No action required. |
| 7 | LOW | Migration | The migration stub name (spec line 1522) `20260322100000_add_onboarding_completed_at_and_drips.sql` bundles all 3 column additions. This follows the project convention of comment-only stubs applied via Supabase MCP. The 3 ALTERs should be applied as a single atomic migration via MCP (one `apply_migration` call with all 3 ALTER TABLE statements). Spec does not explicitly state they are in one transaction. | Spec lines 1517-1524 | Clarify in the migration section that all 3 ALTER TABLE statements are applied in a single `apply_migration` call to ensure atomicity. This matches the project pattern (memory note: "apply via Supabase MCP, then create a 2-line comment stub locally"). |
| 8 | LOW | Naming | Spec references `user_repo.complete_onboarding(user_id)` for the portal path but the text onboarding fallback (spec line 1438) also needs to set `onboarding_completed_at`. The text flow currently calls the existing `complete_onboarding(user_id, call_id, profile)`. When adding `onboarding_completed_at` to the portal method, ensure the text/voice flow also sets this column. Otherwise text-onboarded users will not have `onboarding_completed_at` set, causing them to see `/onboarding` instead of `/dashboard`. | Spec lines 201, 1436-1438 | Add a note in the spec that the existing `complete_onboarding()` method (voice/text path) must ALSO set `onboarding_completed_at` so that returning user detection (FR-007, AC-8.1) works regardless of which onboarding path was taken. |

### Entity Inventory

| Entity | Attributes (spec changes) | PK | FK | RLS | Notes |
|--------|--------------------------|----|----|-----|-------|
| users | +`onboarding_completed_at` TIMESTAMPTZ NULL, +`drips_delivered` JSONB NOT NULL DEFAULT '{}', +`welcome_completed` BOOLEAN NOT NULL DEFAULT false | id (uuid, FK to auth.users) | -- | Existing `users_own_data` FOR ALL + per-op policies cover new columns | 3 new columns, no new RLS needed |
| user_profiles | No schema change. Existing: location_city, location_country, life_stage, social_scene, primary_interest, drug_tolerance | id (uuid, FK to users.id, CASCADE) | users.id | Existing per-op policies (INSERT/SELECT/UPDATE/DELETE) | Profile save uses existing table. No DDL. |
| user_backstories | No schema change. | id (uuid) | users.id (CASCADE, UNIQUE) | Existing policies | Backstory generated async after profile save |
| venue_cache | No schema change. | id (uuid) | -- | Existing policies | Venue research triggered async |
| onboarding_states | No schema change. | telegram_id (bigint) | -- | Existing policies | Used by text fallback flow only |
| scheduled_events | No schema change. Used for 5-min fallback. | id (uuid) | users.id (CASCADE) | Existing policies | New event_type: "onboarding_fallback" |

### Relationship Map

```
users 1──1 user_profiles    (id = user_profiles.id, CASCADE)
users 1──1 user_backstories (id = user_backstories.user_id, CASCADE)
users 1──N scheduled_events (id = scheduled_events.user_id, CASCADE)
venue_cache (standalone, no FK to users)
onboarding_states (standalone, PK = telegram_id)
```

### RLS Policy Checklist

- [x] `users` table: RLS ENABLED, existing `users_own_data` FOR ALL policy covers new columns -- PASS
- [x] `user_profiles` table: RLS ENABLED, per-operation policies (INSERT/SELECT/UPDATE/DELETE) using `id = auth.uid()` -- PASS
- [x] `scheduled_events` table: RLS ENABLED, existing policies cover new event_type -- PASS
- [x] Profile endpoint uses JWT auth (`get_current_user_id` dependency) -- server-side write, no direct client RLS bypass -- PASS
- [x] Admin access: existing `is_admin()` policies on users and user_profiles allow admin portal stats reads -- PASS
- [x] Service role: Profile endpoint backend uses service_role for `complete_onboarding` user update (ORM session, not Supabase client) -- N/A (server-side SQLAlchemy)
- [x] No new tables requiring RLS -- PASS

### Index Requirements

| Table | Column(s) | Type | Query Pattern | Status |
|-------|-----------|------|---------------|--------|
| users | onboarding_status (partial: = 'completed') | btree, partial | `check-drips` cron every 5 min (Phase 2) | MISSING -- MEDIUM finding #4 |
| users | onboarding_completed_at | btree (optional) | Fallback event handler: `WHERE onboarding_completed_at IS NULL` | Not critical -- small table scan acceptable for single-user lookup |
| user_profiles | drug_tolerance | btree | Existing `idx_user_profiles_drug_tolerance` | EXISTS |
| user_profiles | id (PK) | btree (implicit) | Profile upsert by user_id | EXISTS |

### Recommendations

1. **HIGH (Finding #1):** Add `upsert()` method to `ProfileRepository`
   - Implement as: check if profile exists by `user_id`, if yes call field-level update, if no call `create_profile()`
   - Alternatively, use PostgreSQL `INSERT ... ON CONFLICT (id) DO UPDATE SET ...` via SQLAlchemy `insert().on_conflict_do_update()`
   - Spec should specify which pattern to use since `ProfileRepository` does not use ON CONFLICT elsewhere

2. **HIGH (Finding #2):** Create `complete_portal_onboarding(user_id)` method or refactor existing
   - New method should set: `onboarding_status='completed'`, `onboarded_at=now()`, `onboarding_completed_at=now()`
   - Must NOT require `call_id` or `onboarding_profile` (portal path has no voice call)
   - Also update existing `complete_onboarding()` to set `onboarding_completed_at` for voice/text paths

3. **MEDIUM (Finding #3):** Add `server_default` to `welcome_completed` ORM model
   - One-line fix: `server_default=text("false")`

4. **MEDIUM (Finding #4):** Add partial index for check-drips cron
   - Can be deferred to Phase 2 migration but should be documented now

5. **MEDIUM (Finding #5):** Document drip ID validation as app-layer intentional
   - Add code comment to `drips_delivered` model field listing 7 valid keys

6. **LOW (Findings #6-8):** Minor style and documentation improvements
   - Remove redundant `default=None` on nullable column
   - Clarify single-transaction migration
   - Ensure text/voice path also sets `onboarding_completed_at`

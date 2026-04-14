## Data Layer Validation Report

**Spec:** `specs/081-onboarding-redesign-progressive-discovery/spec.md`
**Status:** PASS
**Timestamp:** 2026-03-22T12:00:00Z
**Validator:** sdd-data-layer-validator

### Summary
- CRITICAL: 0
- HIGH: 0
- MEDIUM: 4
- LOW: 3

### Findings

| # | Severity | Category | Issue | Location | Recommendation |
|---|----------|----------|-------|----------|----------------|
| 1 | MEDIUM | Schema Design | `drips_delivered` SQLAlchemy model declares `nullable=True` (line 1044) but the SQL DDL sets `DEFAULT '{}'::jsonb` with no explicit NOT NULL. The column will be nullable in the DB. Meanwhile, `DripManager._is_rate_limited()` (line 771) and `evaluate_user()` (line 746) iterate over the JSONB dict without null-guarding. If the column is NULL (e.g., for users created before migration), code calling `.values()` on None will raise `AttributeError`. | Spec lines 1031-1045 | Either (a) make the column `NOT NULL DEFAULT '{}'::jsonb` in the DDL and `nullable=False` in SQLAlchemy, or (b) add explicit null-guard in the DripManager: `drips = user.drips_delivered or {}`. Option (a) is preferred -- it matches the existing pattern for `onboarding_profile` and `routine_config` which use `DEFAULT '{}'::jsonb`. The migration should include `UPDATE users SET drips_delivered = '{}'::jsonb WHERE drips_delivered IS NULL;` before adding NOT NULL. |
| 2 | MEDIUM | Schema Design | `welcome_completed` SQLAlchemy model declares `nullable=False` (line 1063) but the SQL DDL has `DEFAULT false` without explicit NOT NULL (line 1052). This is a mismatch -- the DDL will create a nullable column while the ORM expects non-nullable. For existing rows, the column will be NULL (DEFAULT only applies to new INSERTs), which conflicts with the `nullable=False` ORM declaration. | Spec lines 1048-1064 | Add `NOT NULL` to the DDL: `ADD COLUMN welcome_completed BOOLEAN NOT NULL DEFAULT false;`. This is safe because DEFAULT fills the value for existing rows when NOT NULL is specified in an ALTER TABLE ADD COLUMN with a non-volatile DEFAULT (PostgreSQL backfills existing rows automatically). This ensures DB and ORM are aligned. |
| 3 | MEDIUM | Indexes | No index specified for the `check-drips` pg_cron query pattern. The DripManager queries `users WHERE onboarding_status = 'completed'` every 5 minutes (line 897). The `users` table currently has no index on `onboarding_status`. With a growing user base, this full-table scan runs every 5 minutes. | Spec lines 885-925, Drip Definitions section | Add a partial index: `CREATE INDEX idx_users_onboarding_completed ON users (onboarding_status) WHERE onboarding_status = 'completed';`. Alternatively, a composite index `(onboarding_status, game_status)` if the query also filters by game_status (e.g., excluding `game_over`/`won` users who should not receive drips). Document the query pattern and corresponding index in the spec. |
| 4 | MEDIUM | Data Integrity | No JSONB schema validation for `drips_delivered`. The spec defines the format as `{"drip_id": "iso_timestamp"}` (line 1036) but there is no CHECK constraint or application-layer validation to ensure drip IDs are from the valid set of 7 drip IDs. A typo in drip_id would silently create orphaned entries. | Spec lines 1029-1046 | Add a comment-level note that valid drip IDs are: `first_score`, `portal_intro`, `first_decay`, `chapter_advance`, `boss_warning`, `boss_debrief`, `nikitas_world`. Consider adding a `DRIP_IDS` constant in `drip_manager.py` and validating against it before writes. A DB CHECK constraint on JSONB keys is impractical, so app-layer validation is the right approach -- but it should be documented. |
| 5 | LOW | Schema Design | `drips_delivered` column placement in the User model. The spec shows adding it after the existing onboarding fields (line 1042-1045) but does not specify where in the SQLAlchemy model class it should be added relative to other fields. The existing model groups fields by feature (game state, voice caching, settings, onboarding, life simulation, conflict). | Spec line 1042 | Add `drips_delivered` and `welcome_completed` in the onboarding section of the User model (after `onboarding_call_id`, around line 122 in user.py) with a comment: `# Progressive discovery (Spec 081)`. This maintains the grouping convention. |
| 6 | LOW | Migration | The pg_cron registration SQL (lines 929-936) uses a placeholder URL `nikita-api-xxx.run.app`. This must be updated with the actual Cloud Run URL before deployment. Also, the TASK_AUTH_SECRET Bearer token is hardcoded -- consistent with existing cron jobs but worth flagging per the project's pg_cron auth sync gotcha. | Spec lines 929-936 | Document that the actual Cloud Run URL (`nikita-api-*.run.app`) and `TASK_AUTH_SECRET` must be substituted at deployment time. Reference the existing pg_cron auth sync pattern documented in `memory/MEMORY.md` (pg_cron Auth Token Sync section). |
| 7 | LOW | API Schema | The spec adds `welcome_completed` to the `GET /portal/stats` response (line 1125) and the `PUT /portal/settings` request (line 1136), but the existing Pydantic schemas (`UserStatsResponse` at portal.py:27-40 and `UpdateSettingsRequest` at portal.py:167-171) do not include these fields. The spec correctly identifies these as modifications but does not show the exact Pydantic schema changes. | Spec lines 1112-1138 | Add to the spec's Database Changes or API Changes section the exact Pydantic model modifications: (a) `UserStatsResponse` needs `welcome_completed: bool = False`, (b) `UpdateSettingsRequest` needs `welcome_completed: bool | None = None`. Also update the `get_user_stats` route handler to pass `welcome_completed=user.welcome_completed` in the response constructor. |

### Entity Inventory

| Entity | Attributes Modified | PK | FK | RLS | Notes |
|--------|-------------------|----|----|-----|-------|
| `users` | +`drips_delivered` (JSONB), +`welcome_completed` (BOOLEAN) | `id` (UUID, matches auth.users.id) | N/A (PK table) | Existing: 6 policies (own data SELECT/UPDATE, admin SELECT/UPDATE, service_role ALL, FOR ALL own data) | No new RLS needed -- existing policies cover new columns |
| `scheduled_events` | No changes -- reused for welcome messages | `id` (UUID) | `user_id -> users(id) ON DELETE CASCADE` | Existing: user SELECT + service_role ALL | Welcome messages use existing event_type mechanism |
| `score_history` | No changes -- queried by DripManager for decay detection | `id` (UUID) | `user_id -> users(id) ON DELETE CASCADE` | Existing | Drip 3 trigger queries this table for decay events |
| `conversations` | No changes -- queried by DripManager for conversation count | `id` (UUID) | `user_id -> users(id) ON DELETE CASCADE` | Existing | Drip 1/2 triggers query this table |
| `job_executions` | No changes -- reused for check-drips execution tracking | `id` (UUID) | N/A | Existing | Standard pg_cron job pattern |

### Relationship Map

```
users 1──N scheduled_events  (welcome messages via existing mechanism)
users 1──N conversations     (drip trigger: conversation count)
users 1──N score_history     (drip trigger: decay event detection)
users 1──N job_executions    (check-drips execution tracking)
```

No new entities or relationships are introduced. All data layer changes are column additions to the existing `users` table.

### RLS Policy Checklist

- [x] Users table has RLS enabled (baseline_schema.sql line 806)
- [x] Users can read own data: `"Users can read own data" ON users FOR SELECT USING (auth.uid() = id)` (line 964)
- [x] Users can update own data: `"Users can update own data" ON users FOR UPDATE USING (auth.uid() = id)` (line 965)
- [x] Service role full access: `"Service role full access users" ON users FOR ALL USING (true)` (line 963)
- [x] Admin read access: `"Admin reads all users" ON users FOR SELECT USING (... OR is_admin())` (line 961)
- [x] `welcome_completed` write via portal: Covered by "Users can update own data" policy (user updates own row via `PUT /portal/settings`)
- [x] `drips_delivered` write via DripManager: DripManager runs server-side with service_role (via `get_session_maker()`) -- covered by service_role policy
- [x] No new RLS policies needed -- confirmed

### Index Requirements

| Table | Column(s) | Type | Query Pattern | Status |
|-------|-----------|------|---------------|--------|
| `users` | `onboarding_status` | btree (partial WHERE = 'completed') | `check-drips` cron: find all completed-onboarding users | **Missing** (MEDIUM #3) |
| `users` | `game_status` | btree | Existing `ix_users_game_status` | Existing |
| `users` | `telegram_id` | btree | Existing `idx_users_telegram_id` | Existing |
| `scheduled_events` | `(status, scheduled_at)` | btree partial | Welcome message delivery | Existing: `idx_scheduled_events_due` |
| `conversations` | `(user_id, status)` | btree | Drip 1/2: count user's processed conversations | Existing: `idx_conversations_user_status` |
| `score_history` | `(user_id, recorded_at DESC)` | btree | Drip 3: check for decay events | Existing: `idx_score_history_user_recorded` |

### Storage & Realtime

- **Storage buckets**: None required. No file uploads or media storage in this feature.
- **Realtime subscriptions**: None required. All interactions are request-response (pg_cron -> API, portal -> API). No live collaborative data.

### Migration Checklist

- [x] Migration type: ALTER TABLE ADD COLUMN (2 columns on existing `users` table)
- [x] Migration approach: Apply via Supabase MCP, create comment stub locally (matches project convention)
- [x] Backward compatibility: Both columns have defaults, so existing rows get sensible values
- [x] Rollback: `ALTER TABLE users DROP COLUMN drips_delivered, DROP COLUMN welcome_completed;` (simple, no data dependencies)
- [x] pg_cron job registration: Separate from DDL migration -- manual via Supabase SQL editor (matches existing pattern)
- [x] No data migration needed: New columns with defaults, no backfill of existing data (spec explicitly scopes out re-triggering for existing users, line 1188)

### Recommendations

1. **MEDIUM #1 (drips_delivered nullability):** Change DDL to `ADD COLUMN drips_delivered JSONB NOT NULL DEFAULT '{}'::jsonb` and SQLAlchemy to `nullable=False`. This is safe for ALTER TABLE ADD COLUMN with a non-volatile DEFAULT in PostgreSQL 11+ (Supabase runs PG15). The existing `routine_config` and `meta_instructions` JSONB columns follow this same pattern with `DEFAULT '{}'::jsonb`.

2. **MEDIUM #2 (welcome_completed NOT NULL):** Add `NOT NULL` to the DDL. PostgreSQL will backfill `false` for all existing rows during the ALTER TABLE. The ORM already expects `nullable=False`.

3. **MEDIUM #3 (missing index):** Add a partial index for the check-drips query. Suggested DDL:
   ```sql
   CREATE INDEX idx_users_onboarding_completed
     ON users (id)
     WHERE onboarding_status = 'completed'
       AND game_status NOT IN ('game_over', 'won');
   ```
   This covers the DripManager's likely query pattern (only active/boss_fight users who completed onboarding need drip evaluation).

4. **MEDIUM #4 (JSONB validation):** Add a `VALID_DRIP_IDS` frozenset constant in `drip_manager.py` and validate drip_id membership before writing to `drips_delivered`. This prevents silent data corruption from typos.

5. **LOW #5-7:** Cosmetic and documentation improvements. Add the SQLAlchemy fields in the onboarding section, document the pg_cron URL/secret substitution requirement, and include the exact Pydantic schema diffs in the spec.

### Cross-Reference Validation

| Check | Result | Notes |
|-------|--------|-------|
| New columns vs baseline schema | OK | `drips_delivered` and `welcome_completed` do not conflict with any existing columns on `users` table |
| SQLAlchemy model vs DDL | MISMATCH | Nullability mismatches on both columns (MEDIUM #1, #2). Types (JSONB, BOOLEAN) and defaults are correct. |
| RLS coverage for new columns | OK | Existing 6 policies on `users` table cover all access patterns |
| Existing indexes for drip trigger queries | OK | `conversations`, `score_history`, `scheduled_events` all have suitable indexes for drip trigger evaluation |
| New index for check-drips query | MISSING | No index on `onboarding_status` (MEDIUM #3) |
| pg_cron registration pattern | OK | Matches existing 6 cron jobs (net.http_post with Bearer token) |
| Migration stub convention | OK | Comment-only stub matching project convention (90 existing stubs) |
| Portal API schema compatibility | OK | Additive changes to `UserStatsResponse` and `UpdateSettingsRequest` -- non-breaking |
| JSONB extension pattern | OK | Matches project's established JSONB column pattern (e.g., `onboarding_profile`, `conflict_details`, `routine_config`) |

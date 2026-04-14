# Data Layer Validation Report

**Spec:** `specs/213-onboarding-backend-foundation/spec.md`
**Status:** FAIL
**Timestamp:** 2026-04-14T18:30:00Z
**Iteration:** 2 (re-validation against iteration 1 findings)
**Validator:** sdd-data-layer-validator

---

### Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 1 |
| LOW | 1 |

---

### Iteration 1 Findings — Resolution Status

All 13 iteration-1 findings are RESOLVED in this spec iteration. Verified against DB state and spec text:

| ID | Finding | Resolution |
|----|---------|------------|
| D-C1 (CRITICAL) | `onboarding_completed_at` column does not exist | RESOLVED — FR-9 rewritten to use `onboarding_status` field; DB confirmed `onboarding_status` exists as `text DEFAULT 'pending'` |
| D-H1 (HIGH) | `user_profiles` ORM missing `name`/`occupation`/`age` mapped_column entries | RESOLVED — FR-1b now specifies all three with correct types (`SmallInteger`, `String`) |
| D-H2 (HIGH) | `pipeline_state` JSONB key has no writer defined | RESOLVED — FR-5.1 added with full state transition table and `update_onboarding_profile_key` repo method (FR-5.2) |
| D-H3 (HIGH) | `backstory_cache` table had no DDL | RESOLVED — FR-12 now specifies complete DDL, ORM model, and Repository interface |
| D-M1 (MEDIUM) | Migration naming used `0091_*` format | RESOLVED — FR-1a now uses `YYYYMMDDHHMMSS_*` format with explicit note matching project convention |
| D-M2 (MEDIUM) | No CHECK constraint on `age SMALLINT` | RESOLVED — FR-1a DDL includes `CHECK (age IS NULL OR (age BETWEEN 18 AND 99))` |
| D-M3 (MEDIUM) | BackstoryCache TTL strategy unclear | RESOLVED — FR-12 documents query-time filter `WHERE expires_at > NOW()` as authoritative strategy |
| D-M4 (MEDIUM) | Cache key composite uniqueness unspecified | RESOLVED — FR-12 uses single `cache_key TEXT` with `CONSTRAINT uq_backstory_cache_key UNIQUE (cache_key)`; bucketing happens in Python |
| D-M5 (MEDIUM) | `wizard_step` JSONB write atomicity unspecified | RESOLVED — Out of Scope explicitly delegates write ownership to Spec 214; FR-9 PATCH uses `jsonb_set` |
| D-L1 (LOW) | RLS coverage not acknowledged for new columns | RESOLVED — FR-1a now states "existing 5 policies cover new columns automatically (PostgreSQL is row-level, not column-level)" |
| D-L2 (LOW) | Migration rollback not documented | RESOLVED — FR-1a includes rollback script `ALTER TABLE user_profiles DROP COLUMN name, DROP COLUMN occupation, DROP COLUMN age` |
| D-L3 (LOW) | Pydantic vs DB CHECK constraint duplication | RESOLVED — FR-1d documents intentional dual enforcement with rationale |
| D-L4 (LOW) | Index for onboarding detection column | RESOLVED — `onboarding_completed_at` not added; FR-9 uses PK-indexed `user_id` lookup on existing `onboarding_status` column; no index gap |

---

### Findings

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| HIGH | RLS / Schema | `backstory_cache` migration DDL in FR-12 includes no `ALTER TABLE backstory_cache ENABLE ROW LEVEL SECURITY` and no `CREATE POLICY` statement. The table will be created with RLS disabled (PostgreSQL default). Any authenticated session can execute `SELECT * FROM backstory_cache`, exposing all bucketed profile shapes and their scenario JSONB. The spec prose in FR-12 says "RLS: deny by default (admin-only via `is_admin()` policy)" but this is not represented in the DDL block — prose is not a migration. | `spec.md` FR-12, migration DDL block (lines 398–407) | Add to the FR-12 migration SQL block: `ALTER TABLE backstory_cache ENABLE ROW LEVEL SECURITY;` followed by `CREATE POLICY "Admins can manage backstory cache" ON backstory_cache FOR ALL TO public USING (is_admin()) WITH CHECK (is_admin());` The `is_admin()` function already exists in the project (used by `user_profiles` and `user_backstories`). Verified: `backstory_cache` table does not yet exist in DB — the fix goes in the NEW migration only. |
| MEDIUM | RLS | `user_profiles` UPDATE policy has no `WITH CHECK` clause (DB-verified: `with_check=null` on "Users can update own profile"). Spec FR-7 identifies this gap and flags it as a needed fix but defers it to "Phase 8 implementation (out of spec scope)" without providing the DDL or an accepted-risk declaration. Under the user's absolute-zero policy, a spec-identified security gap with no resolution DDL and no explicit risk-acceptance is not passing. The implementation note says "Add WITH CHECK (id = auth.uid()) to UPDATE policy — belt-and-suspenders" — this must be in the spec, not just the implementation notes. | `spec.md` FR-7 and Implementation Notes (lines 344, 707–709) | Move the WITH CHECK fix from implementation notes into FR-7 with explicit DDL: `ALTER POLICY "Users can update own profile" ON user_profiles WITH CHECK (id = (SELECT auth.uid()));` This is a single DDL statement that can ship in PR 213-2 (the migration PR). Alternatively, mark FR-7 with an explicit "accepted risk: without WITH CHECK, a bug in the USING clause could allow cross-user writes; mitigated by application-layer auth check" — but the former is strongly preferred. |
| LOW | RLS | `user_profiles` DELETE policy uses bare `auth.uid()` (DB-verified: `qual = "(id = auth.uid())"`) rather than the subquery form `(id = (SELECT auth.uid()))`. This is a pre-existing issue not introduced by this spec, but the spec modifies `user_profiles` policies (FR-7) and audits all 5 existing policies, making this the appropriate time to fix it. The subquery form evaluates `auth.uid()` once per query rather than once per row — relevant for batch DELETE operations. | `spec.md` FR-7 (lines 344–347); DB policy "Users can delete own profile" | Add to FR-7: "Also update DELETE policy to use subquery form: `ALTER POLICY "Users can delete own profile" ON user_profiles USING (id = (SELECT auth.uid()));`" This is a one-line change that can be included in PR 213-2. Pre-existing issue: `user_profiles` DELETE, `users` "Users can read own data" and "Users can update own data" policies all use bare `auth.uid()` — the latter two are out of scope for this spec. |

---

### Entity Inventory

| Entity | Attributes | PK | FK | RLS | Notes |
|--------|------------|----|----|-----|-------|
| `user_profiles` (ALTER) | +`name TEXT NULL`, +`occupation TEXT NULL`, +`age SMALLINT NULL CHECK (age IS NULL OR age BETWEEN 18 AND 99)` | `id UUID` | `id` → `auth.users(id)` | Enabled — 5 policies cover new columns automatically | DB-verified: columns NOT YET present; migration pending |
| `backstory_cache` (CREATE) | `id UUID PK`, `cache_key TEXT NOT NULL UNIQUE`, `scenarios JSONB NOT NULL`, `created_at TIMESTAMPTZ DEFAULT now()`, `expires_at TIMESTAMPTZ NOT NULL` | `id UUID` | none | MISSING RLS ENABLE + POLICY DDL (HIGH finding) | Table does not yet exist in DB |
| `users` (method only) | `onboarding_profile JSONB` — new key `pipeline_state` written via `update_onboarding_profile_key` | `id UUID` | — | Enabled — 5 policies | DB-verified: `onboarding_profile JSONB DEFAULT '{}'` exists; `pipeline_state` key written by FR-5.1 |

---

### Relationship Map

```
users 1──1 user_profiles (id → id)
backstory_cache ── (no FK; keyed by computed cache_key string)
users.onboarding_profile JSONB ── pipeline_state key written by _bootstrap_pipeline
```

---

### RLS Policy Checklist

- [x] `user_profiles` SELECT (own) — `(id = (SELECT auth.uid()))` subquery form — PASS
- [x] `user_profiles` INSERT — `WITH CHECK (id = (SELECT auth.uid()))` — PASS
- [ ] `user_profiles` UPDATE — USING uses subquery form but `with_check=null` — FAIL (MEDIUM finding)
- [ ] `user_profiles` DELETE — bare `auth.uid()` not subquery form — FAIL (LOW finding)
- [x] `user_profiles` SELECT (admin) — `is_admin()` — PASS
- [ ] `backstory_cache` — RLS not enabled, no policy DDL in migration — FAIL (HIGH finding)
- [x] `users.onboarding_profile` write — uses `update_onboarding_profile_key` via service_role or user's own session — PASS (FR-5.2 specifies atomic `jsonb_set`)

---

### Index Requirements

| Table | Column(s) | Type | Query Pattern | Status |
|-------|-----------|------|---------------|--------|
| `user_profiles` | `age` WHERE age IS NOT NULL | Partial btree | FR-1a specifies `idx_user_profiles_age`; no query pattern yet documented (future analytics) | Specified in spec; not yet in DB |
| `backstory_cache` | `expires_at` | btree | Query-time TTL filter cleanup | Specified in FR-12; not yet in DB |
| `backstory_cache` | `cache_key` | Unique btree (auto via UNIQUE constraint) | Cache lookup `WHERE cache_key = ?` | Implicit via UNIQUE constraint |

---

### Recommendations

1. **HIGH — Add RLS DDL to FR-12 `backstory_cache` migration**
   - Add these two statements to the `YYYYMMDDHHMMSS_create_backstory_cache.sql` migration, after the `CREATE TABLE` and `CREATE INDEX` statements:
     ```sql
     ALTER TABLE backstory_cache ENABLE ROW LEVEL SECURITY;
     CREATE POLICY "Admins can manage backstory cache"
       ON backstory_cache FOR ALL TO public
       USING (is_admin())
       WITH CHECK (is_admin());
     ```
   - Verify `is_admin()` function exists: confirmed present on `user_profiles` and `user_backstories` policies.
   - No user-facing READ access is needed; the facade reads via the session that runs as the calling user but `is_admin()` ensures only admin-role can enumerate. Alternatively, use service_role for all backstory cache operations (no user-facing policy needed), which is cleaner.

2. **MEDIUM — Add WITH CHECK to user_profiles UPDATE policy in FR-7**
   - Include in the FR-7 specification body (not just implementation notes) the exact DDL:
     ```sql
     ALTER POLICY "Users can update own profile" ON user_profiles
       WITH CHECK (id = (SELECT auth.uid()));
     ```
   - Place in PR 213-2 alongside the user_profiles column migration.

3. **LOW — Fix user_profiles DELETE policy to use subquery auth.uid() form**
   - Include in FR-7 alongside the UPDATE WITH CHECK fix:
     ```sql
     ALTER POLICY "Users can delete own profile" ON user_profiles
       USING (id = (SELECT auth.uid()));
     ```
   - Can ship in same PR 213-2 with zero risk — pure performance improvement, identical access semantics.

---

### Migration Strategy Assessment

| Migration | Type | Status | Risk |
|-----------|------|--------|------|
| `YYYYMMDDHHMMSS_alter_user_profiles_add_name_occupation_age.sql` | DDL ALTER TABLE (3 nullable columns) | New; not yet in DB | Low — nullable columns, no default constraint issues |
| `YYYYMMDDHHMMSS_create_backstory_cache.sql` | DDL CREATE TABLE | New; not yet in DB | Medium — HIGH finding: missing RLS statements |

Both migrations target new columns/tables — no data migration risk, no existing row impact.

---

### Verdict

**FAIL** — 0 CRITICAL, 1 HIGH, 1 MEDIUM, 1 LOW

The HIGH finding (backstory_cache RLS missing from migration DDL) is a security gap that prevents implementation clearance. The MEDIUM (UPDATE policy WITH CHECK deferred without DDL in spec) and LOW (DELETE policy bare auth.uid()) are fixable with small spec edits to FR-7 and FR-12. All 13 iteration-1 findings are fully resolved. One targeted spec edit pass to FR-7 and FR-12 should reach PASS in iteration 3.

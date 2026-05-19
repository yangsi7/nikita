## Data Layer Validation Report

**Spec:** `specs/214-portal-onboarding-wizard/spec.md`
**Status:** PASS
**Timestamp:** 2026-04-15T15:30:00Z
**Validator:** sdd-data-layer-validator
**Iteration:** 3 (re-validation after iter-2 fix commit 1caaea8)

---

### Summary

- CRITICAL: 0
- HIGH: 0
- MEDIUM: 0
- LOW: 0

All iter-2 LOWs resolved in commit 1caaea8. No new data layer gaps introduced by any of the 11 changes in the commit (3 API HIGH fixes, 5 testing MEDIUM fixes, 2 auth LOWs, 1 frontend LOW, 3 architecture LOWs). Zero findings across all severities.

---

### Iter-2 Fix Confirmation

| Iter-2 Finding | Fix Commit | Status | Evidence |
|----------------|------------|--------|----------|
| LOW D1: Appendix D header "All endpoints are Spec 213 FROZEN contracts. Spec 214 is consumer-only." contradicted by table entries marked (new, FR-10.1) and (extended, FR-10.2) | 1caaea8 | RESOLVED | Line 984: header now reads "Backend endpoint reference for portal consumption. Endpoints marked (new, FR-10.1) and (extended, FR-10.2) are added by Spec 214 PR 214-D; all others are Spec 213 FROZEN contracts." |
| LOW D2: Out of Scope item 3 documented `users` UPDATE `with_check=NULL` gap but omitted the parallel `user_profiles` gap | 1caaea8 | RESOLVED | Line 782: note now includes "The same pattern exists on `user_profiles`: `Users can update own profile` (public role) UPDATE policy has `with_check = NULL`; the correct `Users update own profile` (authenticated role) WITH CHECK covers all authenticated writes. Track in the same standalone RLS hardening GH issue." |

---

### New Change Scan (commit 1caaea8 — 11 non-data-layer changes)

| Change ID | Category | Data Layer Impact | Verdict |
|-----------|----------|-------------------|---------|
| H1: `_ChoiceRateLimiter.check()` — bare UUID, not f-string prefix | API | Uses `DatabaseRateLimiter` subclass → writes to `rate_limits` table. Table confirmed live (verified via SQL). No new schema. | CLEAR |
| H2: `_ChoiceRateLimiter._get_day_window()` override added | API | Same as H1. In-memory key construction only. No schema change. | CLEAR |
| H3: `_PipelineReadyRateLimiter` full pseudocode + `get_pipeline_ready` signature | API | Same `rate_limits` table usage pattern. No new table. No new column. | CLEAR |
| T1–T5: Test file inventory additions | Testing | No DB schema involvement. Frontend/backend test coverage only. | N/A |
| A1: Rate-limit description correction | Auth | Prose-only. No DB involvement. | N/A |
| A2: `cache_key: string \| null` added to `WizardPersistedState` schema | Auth | localStorage-only (browser). Explicitly documented as write from `BackstoryPreviewResponse` to localStorage. No DB column. | CLEAR |
| F1: `DossierStamp` import path fix | Frontend | Component path correction. No DB involvement. | N/A |
| Arch changes (3) | Architecture | Rate-limiter pseudocode updates. No new tables, columns, indexes, or migrations. | CLEAR |

---

### Findings

None. Zero findings across all severities.

---

### Entity Inventory

| Entity | Attributes Relevant to Spec 214 | PK | FK | RLS | Notes |
|--------|----------------------------------|----|----|-----|-------|
| `users` | `onboarding_profile` JSONB (DEFAULT `'{}'::jsonb`), `onboarding_status` TEXT, `onboarded_at` TIMESTAMPTZ, `pending_handoff` BOOLEAN, `phone` VARCHAR | `id` UUID | — | ENABLED (5 policies) | JSONB keys `wizard_step` + `chosen_option` written by this spec via existing UPDATE surface. No schema change needed. |
| `user_profiles` | `name` VARCHAR, `age` SMALLINT, `occupation` VARCHAR, `location_city` VARCHAR, `social_scene` VARCHAR, `drug_tolerance` INTEGER NOT NULL DEFAULT 3, `life_stage` VARCHAR, `primary_interest` VARCHAR | `id` UUID | `users.id` | ENABLED (7 policies, 2 UPDATE) | All columns deployed in Spec 213 migration, confirmed live. Spec 214 reads and writes via existing PATCH endpoint. |
| `backstory_cache` | `cache_key` TEXT PK, `scenarios` JSONB NOT NULL, `venues_used` JSONB NOT NULL DEFAULT `'[]'`, `ttl_expires_at` TIMESTAMPTZ NOT NULL, `created_at` TIMESTAMPTZ NOT NULL DEFAULT now() | `cache_key` TEXT | — | ENABLED (2 policies) | NO `user_id` column — ownership validation is semantic (cache_key recompute from user_profiles), not a DB FK. Confirmed live. |
| `rate_limits` | (existing table, owned by DatabaseRateLimiter base class) | — | — | (internal) | Confirmed live. `_ChoiceRateLimiter` and `_PipelineReadyRateLimiter` write to this table via base class. No DDL changes. |

---

### Relationship Map

```
users 1──1 user_profiles        (user_profiles.id FK → users.id)
users.onboarding_profile JSONB  (keys: wizard_step int, chosen_option BackstoryOption dict)
backstory_cache (standalone)    (no FK to users; keyed by cache_key = segment hash of city|scene|life_stage|darkness)
rate_limits (standalone)        (keyed by rate-limiter prefix + user UUID + time window)
```

---

### RLS Policy Checklist

- [x] `users` RLS ENABLED — CONFIRMED live (5 policies)
- [x] `users` UPDATE covers `onboarding_profile` JSONB writes — `users_own_data` FOR ALL WITH CHECK `(id = (SELECT auth.uid()))` is the correct gate
- [x] `users_own_data` WITH CHECK correct — CONFIRMED via `pg_policies` live query
- [x] `user_profiles` RLS ENABLED — CONFIRMED live (7 policies)
- [x] `user_profiles` UPDATE (authenticated role) has WITH CHECK `(id = (SELECT auth.uid()))` — CONFIRMED (`Users update own profile`)
- [x] `backstory_cache` RLS ENABLED — CONFIRMED live
- [x] `backstory_cache_admin_only` — authenticated role `USING (false)` deny-all; service_role bypasses — CONFIRMED
- [x] `backstory_cache_anon_denied` — anon `USING (false)` — CONFIRMED
- [x] No new RLS policies required — Spec 214 adds no new tables; existing policies cover all read/write paths

**Pre-existing (acknowledged in Out of Scope item 3, line 782 — not Spec 214 findings):**
- `users` "Users can update own data" (public role) UPDATE — `with_check = NULL` — covered by `users_own_data` FOR ALL WITH CHECK. Documented.
- `user_profiles` "Users can update own profile" (public role) UPDATE — `with_check = NULL` — covered by `Users update own profile` (authenticated) WITH CHECK. Documented.

---

### Index Requirements

| Table | Column(s) | Type | Query Pattern | Status |
|-------|-----------|------|---------------|--------|
| `backstory_cache` | `cache_key` | UNIQUE BTREE (PK) | FR-10.1 cache_key lookup via `BackstoryCacheRepository.get(cache_key)` | EXISTS — `backstory_cache_pkey` |
| `backstory_cache` | `ttl_expires_at` | BTREE | TTL cleanup cron query | EXISTS — `idx_backstory_cache_ttl` |
| `users` | `id` | UNIQUE BTREE (PK) | All single-row reads by auth.uid() | EXISTS — `users_pkey` |
| `users` | `phone` | UNIQUE BTREE (partial) | HTTP 409 duplicate-phone check at step 10 | EXISTS — `uq_users_phone WHERE phone IS NOT NULL` |
| `user_profiles` | `id` | UNIQUE BTREE (PK) | All single-row reads in facade | EXISTS — `user_profiles_pkey` |

No new indexes required. All Spec 214 DB operations are single-row PK lookups or JSONB key writes to existing rows.

---

### Schema Design Verification

#### FR-10.1 — `chosen_option` JSONB write path

- Column: `users.onboarding_profile` JSONB, nullable, DEFAULT `'{}'::jsonb` — CONFIRMED live
- Write: `jsonb_set(onboarding_profile, '{chosen_option}', <BackstoryOption dict>)` — atomic key merge
- No new column: `chosen_option` is a JSONB key. Zero DDL required.
- Snapshot semantics: full `BackstoryOption` dict stored (not just id) so backstory_cache eviction does not orphan the selection. Enforced by AC-10.5.

#### FR-10.2 — `wizard_step` JSONB read path

- Read: `users.onboarding_profile->>'wizard_step'` — JSONB key written by PATCH endpoint (Spec 213 FR-6)
- Write source: `PATCH /onboarding/profile` with `OnboardingV2ProfileRequest.wizard_step` — confirmed in live contracts.py line 73 (`wizard_step: int | None = Field(...)`)
- Read path: extended `get_pipeline_ready` handler reads key and populates `PipelineReadyResponse.wizard_step`
- No migration: JSONB key addition to existing nullable JSONB column = zero DDL

#### NR-1 — Dual persistence (localStorage + JSONB)

- No schema conflict. `wizard_step` JSONB key already writable via Spec 213 PATCH endpoint.
- localStorage is browser-only; no DB schema concern.
- `cache_key` added to `WizardPersistedState` (A2 fix) is localStorage-only — confirmed by spec line 894.

#### Rate Limiter DB Dependency

- `_ChoiceRateLimiter` and `_PipelineReadyRateLimiter` subclass `DatabaseRateLimiter` which writes to `rate_limits` table.
- `rate_limits` table: confirmed live (SQL query: `rate_limits_exists = true`).
- No DDL change needed. Both subclasses use existing table with key-prefix isolation (`choice:`, `poll:`).

---

### Migration Requirements

**Spec 214 requires ZERO new migrations.**

1. No new tables
2. No new columns (all columns deployed in Spec 213, confirmed live)
3. No new indexes (no new query patterns)
4. No new RLS policies (existing policies cover all read/write paths)
5. `chosen_option` and `wizard_step` are JSONB keys, not columns — zero DDL
6. `rate_limits` table already deployed — no DDL for new rate-limiter subclasses

Only schema-adjacent changes are Python/Pydantic code additions in `nikita/onboarding/contracts.py` (PR 214-D): `BackstoryChoiceRequest` model + `PipelineReadyResponse.wizard_step` field extension.

---

### Data Integrity Constraints

| Constraint | Where | Enforced By | Status |
|-----------|-------|-------------|--------|
| `chosen_option_id` must appear in `backstory_cache.scenarios` for the given `cache_key` | App layer | `PortalOnboardingFacade.set_chosen_option()` → check id in scenarios list | Spec requires; no DB FK possible on JSONB array element |
| `cache_key` ownership match | App layer | Recompute cache_key from user's `user_profiles` row, compare to echoed cache_key | Spec requires; correct — `backstory_cache` has no `user_id` column |
| `wizard_step` range ge=1, le=11 | Pydantic + app | `PipelineReadyResponse.wizard_step = Field(default=None, ge=1, le=11)` | No DB CHECK needed; value originates from app-controlled PATCH |
| `BackstoryChoiceRequest.chosen_option_id` max_length=64 | Pydantic | `Field(..., min_length=1, max_length=64)` | No DB CHECK needed |
| `BackstoryChoiceRequest.cache_key` max_length=128 | Pydantic | `Field(..., min_length=1, max_length=128)` | No DB CHECK needed |
| Duplicate phone on step 10 POST | DB | `uq_users_phone` unique partial index on `users.phone` | 409 path covered by AC-7.2 |

No new DB-level CHECK constraints or triggers required.

---

### Recommendations

None. All prior findings resolved. Spec is clear for implementation planning.

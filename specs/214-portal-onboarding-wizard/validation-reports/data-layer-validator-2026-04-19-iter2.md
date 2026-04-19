# Data Layer Validation Report — Spec 214 Amended (GATE 2 iter-2)

**Spec**: `specs/214-portal-onboarding-wizard/spec.md` (amended 2026-04-19) + `technical-spec.md`
**Validator**: sdd-data-layer-validator
**Iteration**: GATE 2 iter-2 (post-amendment)
**Status**: **PASS**
**Timestamp**: 2026-04-19

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 2 |
| LOW | 3 |

**Verdict**: PASS (0 CRITICAL + 0 HIGH). Spec is ready for implementation planning.

iter-1 HIGH findings **both resolved**:

- **H10** (JSONB write concurrency): RESOLVED. tech-spec §2.3 step 8 specifies `select(User).where(User.id == user_id).with_for_update()` via SQLAlchemy ORM round-trip (MutableDict dirty-tracking), explicitly rejecting raw `jsonb_set` per PR #317 (double-encoded JSONB) / PR #319 (TEXT[] path land-mine) precedent. AC-NR1b.1b quoted in-line. Correct pattern.
- **H11** (legacy `user_onboarding_state`): RESOLVED. tech-spec §4.3 specifies FK-audit query (`information_schema.table_constraints` → zero rows required), in-flight row count (<15 per 2026-04-19 snapshot) documented as acceptable data loss, migration stub reserved at `migrations/YYYYMMDD_drop_user_onboarding_state.sql`, GDPR coupling during quiet period wired into `delete_user`, 30-day quiet period + Phase C PASS gate before drop.

---

## Findings

| # | Severity | Category | Issue | Location | Recommendation |
|---|----------|----------|-------|----------|----------------|
| M1 | MEDIUM | RLS policy — ownership model | `llm_spend_ledger` and `llm_idempotency_cache` use `is_admin() OR auth.role() = 'service_role'` as the ONLY policy. The owning `user_id` column is never referenced in the policy. The row owner (the authenticated user) CANNOT read their own spend ledger row via RLS, which is correct for secret-by-design tables but makes these tables **service-role-only** in practice. Confirm the app always uses the service-role client for these tables; an accidental anon/authenticated JWT read returns empty (silent policy miss). | tech-spec §4.3a, §4.3b | Either (a) add a comment in the migration stating "service-role only; never accessed via RLS-filtered JWT" OR (b) add a per-user SELECT policy `USING (user_id = (SELECT auth.uid()))` if users ever inspect their own spend. Option (a) is fine given current scope; call it out in the migration header comment. |
| M2 | MEDIUM | Index coverage — idempotency cache lookup | `llm_idempotency_cache` primary-key is `(user_id, turn_id)`. The endpoint's read path is `idempotency.get((user_id, turn_id))` which is a PK hit (fast). BUT the pg_cron prune job runs `DELETE ... WHERE created_at < now() - interval '5 minutes'` — the existing `idx_llm_idempotency_cache_created (created_at)` is declared, which covers this. Minor: `idx_llm_spend_ledger_day (day)` indexed but daily rollover uses `WHERE day < current_date - interval '30 days'` which is a range scan using this index. OK. No HIGH issue here. | tech-spec §4.3a, §4.3b | No change required. Index coverage is correct for both read and prune paths. |
| L1 | LOW | DDL stub location | The spec inlines the new-table DDL directly in tech-spec §4.3a/§4.3b, but references no concrete migration filename (unlike §4.3 which reserves `migrations/YYYYMMDD_drop_user_onboarding_state.sql`). | tech-spec §4.3a, §4.3b | Add migration-filename placeholders: `migrations/YYYYMMDD_create_llm_idempotency_cache.sql` and `migrations/YYYYMMDD_create_llm_spend_ledger.sql` to match §4.3 convention. |
| L2 | LOW | pg_cron job owner documentation | Four new pg_cron jobs added (`onboarding_conversation_nullify_90d`, `llm_idempotency_cache_prune`, `llm_spend_ledger_rollover`, `nikita_handoff_greeting_backstop`). Three are bare SQL (no HTTP auth needed); the fourth uses `net.http_post` with Bearer token. `TASK_AUTH_SECRET` coupling is documented in CLAUDE.md but not re-stated in-spec. | tech-spec §4.1, §4.3a, §4.3b, §2.5 step 5 | Add one-liner in tech-spec §2.5: "If `TASK_AUTH_SECRET` rotates, run `cron.alter_job()` on `nikita_handoff_greeting_backstop` per CLAUDE.md convention for pg_cron HTTP jobs." Prevents the same drift that bit the other 6 cron jobs. |
| L3 | LOW | Retention job idempotency | `onboarding_conversation_nullify_90d` runs `UPDATE users SET onboarding_profile = onboarding_profile - 'conversation' WHERE ... onboarding_profile ? 'conversation'`. The `? 'conversation'` guard makes it idempotent (second run on the same row is a no-op). No issue; note for completeness. | tech-spec §4.1 | No change required. Guard is correct. |

---

## Entity Inventory

| Entity | Status | Changes in Spec 214 | Attributes | PK | FK | RLS | Verified |
|--------|--------|---------------------|------------|----|----|-----|----------|
| `users` | **existing** | ADD COLUMN `handoff_greeting_dispatched_at TIMESTAMPTZ NULL`; additive JSONB subfield `onboarding_profile.conversation` (no DDL) | id, telegram_id, pending_handoff, handoff_greeting_dispatched_at (new), onboarding_profile (jsonb), onboarding_status, game_status | id | — | YES (6 policies — verified live via pg_policies) | Live DB shows `rowsecurity=true`, 6 policies incl. `users_own_data` with WITH CHECK matching SUBQUERY form `(id = (SELECT auth.uid()))`. `is_admin()` function exists. |
| `llm_idempotency_cache` | **NEW** | CREATE | user_id (FK→users CASCADE), turn_id, response_body (jsonb), status_code, created_at | (user_id, turn_id) | user_id → users(id) ON DELETE CASCADE | YES — `admin_and_service_role_only` FOR ALL with WITH CHECK | DDL in tech-spec §4.3a includes `ENABLE ROW LEVEL SECURITY` + CREATE POLICY + `WITH CHECK` mirror of USING clause. Compliant with `.claude/rules/testing.md` DB Migration Checklist. |
| `llm_spend_ledger` | **NEW** | CREATE | user_id (FK→users CASCADE), day, spend_usd, last_updated | (user_id, day) | user_id → users(id) ON DELETE CASCADE | YES — `admin_and_service_role_only` FOR ALL with WITH CHECK | DDL in tech-spec §4.3b includes `ENABLE ROW LEVEL SECURITY` + CREATE POLICY + WITH CHECK. Compliant. |
| `user_onboarding_state` | **legacy (drop scheduled)** | DROP IF EXISTS CASCADE (Phase D, after FK-audit + 30-day quiet + Phase C PASS) | — | — | — | — | FK-audit query reserved; in-flight row count snapshot documented; `delete_user` GDPR coupling enforced during quiet period. H11 resolved. |

---

## Relationship Map

```
users (existing, RLS ON)
  ├── 1:N llm_idempotency_cache.user_id  (ON DELETE CASCADE)
  └── 1:N llm_spend_ledger.user_id       (ON DELETE CASCADE)
```

No junction tables introduced. No circular FKs. CASCADE semantics correct (idempotency cache + spend ledger are owned by user; deleting the user should purge them).

---

## RLS Policy Checklist (per `.claude/rules/testing.md` DB Migration Checklist)

### `llm_idempotency_cache`

- [x] `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` present (line 443)
- [x] At least one `CREATE POLICY` present (line 444-447)
- [x] Policy is `FOR ALL` with both `USING` and `WITH CHECK` — UPDATE path covered (no null WITH CHECK privilege-escalation risk)
- [x] Policy uses `is_admin()` (admin) + `auth.role() = 'service_role'` (service) — service-role-only access model is intentional
- [x] No SUBQUERY form `user_id = (SELECT auth.uid())` — by design, since the row owner is not meant to read this table (it's an internal idempotency cache). Acceptable per M1.
- [x] Post-migration verify via `mcp__supabase__list_policies` — MUST be run after Apply

### `llm_spend_ledger`

- [x] `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` present (line 466)
- [x] At least one `CREATE POLICY` present (line 467-470)
- [x] `FOR ALL` with WITH CHECK — UPDATE path covered
- [x] Service-role + admin model — intentional (spend ledger is internal accounting)
- [x] Post-migration verify via `mcp__supabase__list_policies` — MUST be run after Apply

### `users.onboarding_profile.conversation` (JSONB subfield)

- [x] Inherits `users` RLS policies (6 existing policies incl. `users_own_data` with WITH CHECK SUBQUERY form `(id = (SELECT auth.uid()))`). Verified live.
- [x] tech-spec §4.1 explicitly states "inherits `users` table RLS policies (user-scoped); no separate policy needed because JSONB subfields share the row-level gate" — correct.

### `users.handoff_greeting_dispatched_at` (new column)

- [x] Inherits `users` RLS — no separate policy required. Column-level RLS not in scope.
- [x] Supporting partial index `idx_users_handoff_backstop ON users (handoff_greeting_dispatched_at) WHERE pending_handoff = TRUE AND telegram_id IS NOT NULL` — correct shape for the pg_cron backstop query.

---

## Index Requirements

| Table | Index | Purpose | Correct? |
|-------|-------|---------|----------|
| `users` | `idx_users_handoff_backstop (handoff_greeting_dispatched_at) WHERE pending_handoff = TRUE AND telegram_id IS NOT NULL` | pg_cron backstop query in §2.5 step 5 | YES — partial index matches predicate exactly |
| `llm_idempotency_cache` | PRIMARY KEY `(user_id, turn_id)` | endpoint idempotency-HIT lookup | YES — equality on both cols, PK is optimal |
| `llm_idempotency_cache` | `idx_llm_idempotency_cache_created (created_at)` | hourly prune `WHERE created_at < now() - 5 min` | YES — range scan covered |
| `llm_spend_ledger` | PRIMARY KEY `(user_id, day)` | daily `get_today(user_id)` read | YES — equality on both cols, PK |
| `llm_spend_ledger` | `idx_llm_spend_ledger_day (day)` | daily rollover `WHERE day < current_date - 30 days` | YES — range scan covered |

---

## Atomic Predicate-Filter UPDATE Pattern (§2.5 Step 2)

```sql
UPDATE users SET handoff_greeting_dispatched_at = now()
 WHERE id = :uid
   AND handoff_greeting_dispatched_at IS NULL
   AND pending_handoff = TRUE
 RETURNING id;
```

- [x] Single-statement atomic claim-intent pattern — correct.
- [x] `RETURNING id` allows caller to check `rowcount == 1` → proceed; `rowcount == 0` → another concurrent bind already claimed.
- [x] Predicate-filter guarantees idempotency under concurrent `/start <code>` from same user (spec AC-11e.3 test covers this explicitly).
- [x] No SELECT-then-UPDATE race (the pattern PR #317/#319 bit on).
- [x] Pairs correctly with Step 3 (`pending_handoff = FALSE` ONLY after confirmed Telegram send) and Step 5 (pg_cron backstop resets `handoff_greeting_dispatched_at=NULL` on retry-exhaust). Durability argument (Cloud Run eviction between claim and send) explicitly addressed.

---

## JSONB Concurrency Pattern (§2.3 Step 8)

```python
async with session.begin():
    stmt = select(User).where(User.id == user_id).with_for_update()
    user = (await session.execute(stmt)).scalar_one()
    profile = dict(user.onboarding_profile or {})  # defensive copy
    profile.setdefault("conversation", []).append(new_turn)
    user.onboarding_profile = profile  # dirty-tracking via MutableDict.as_mutable
```

- [x] `SELECT ... FOR UPDATE` row-lock acquired before mutation — prevents lost updates under concurrent `/converse` from same user.
- [x] ORM round-trip (defensive dict copy + reassignment) — NOT raw `jsonb_set`. Avoids PR #317 double-encoding and PR #319 TEXT[] path land-mine.
- [x] `MutableDict.as_mutable` required on the column type for SQLAlchemy dirty-tracking to fire on nested mutation. Implementor note: verify column definition has this wrapper; if not already present (Spec 213 PR 213-5 established this), the migration stub must not silently omit it.
- [x] AC-NR1b.1b directly quoted. H10 resolved.

---

## pg_cron Job Inventory (new in Spec 214)

| Job | Schedule | Auth | Action | Gate |
|-----|----------|------|--------|------|
| `onboarding_conversation_nullify_90d` | `0 3 * * *` (daily 03:00 UTC) | pure SQL (no HTTP) | Drop `conversation` key from `onboarding_profile` for completed users >90d | Retention (AC-NR1b.4b) |
| `llm_idempotency_cache_prune` | `0 * * * *` (hourly) | pure SQL | Delete rows older than 5 min | Cache TTL (§2.3) |
| `llm_spend_ledger_rollover` | `5 0 * * *` (daily 00:05 UTC) | pure SQL | Delete rows older than 30 days | Cost hygiene |
| `nikita_handoff_greeting_backstop` | every 60s | `net.http_post` + `TASK_AUTH_SECRET` Bearer | POST `/api/v1/tasks/retry-handoff-greetings`, picks up stranded rows | Durability (AC-11e.3c) |

The HTTP-authenticated job (`nikita_handoff_greeting_backstop`) inherits the CLAUDE.md gotcha: token rotation requires `cron.alter_job()` on ALL such jobs. Flagged as L2 above. Three pure-SQL jobs need no credential rotation, no action required.

---

## Recommendations (actionable, non-blocking)

1. **L1 — Migration filename placeholders**: add `migrations/YYYYMMDD_create_llm_idempotency_cache.sql` + `migrations/YYYYMMDD_create_llm_spend_ledger.sql` placeholders in tech-spec §4.3a/§4.3b so `/plan` knows where to drop the DDL. Matches §4.3 convention.
2. **L2 — TASK_AUTH_SECRET rotation note**: add one-line reminder in tech-spec §2.5 step 5: "If `TASK_AUTH_SECRET` rotates, run `cron.alter_job()` on `nikita_handoff_greeting_backstop` per CLAUDE.md pg_cron convention."
3. **M1 — Service-role intentionality comment**: add migration-header comment for both new tables documenting that the RLS policy is intentionally service-role-only; the row-owner is NOT expected to read these tables from an anon/authenticated JWT. Prevents future confusion on why "SELECT returns empty from user JWT."
4. **Post-migration**: after applying the DDL, run `mcp__supabase__list_policies` against `llm_spend_ledger` and `llm_idempotency_cache` and paste output in the implementation PR description. Enforces the `.claude/rules/testing.md` final bullet "verify every listed policy is active."

---

## Cross-reference verification

- [x] iter-1 H10 (JSONB write concurrency) → §2.3 step 8, AC-NR1b.1b. RESOLVED.
- [x] iter-1 H11 (legacy user_onboarding_state) → §4.3. RESOLVED.
- [x] `.claude/rules/testing.md` DB Migration Checklist: ENABLE RLS ✓, CREATE POLICY ✓, WITH CHECK on UPDATE-capable policies ✓ (both new tables use `FOR ALL` with WITH CHECK), SUBQUERY form on `users` policies ✓ (pre-existing, verified live).
- [x] No Spec 213 FR-12/FR-7 RLS-hardening drift introduced.
- [x] Live Supabase state confirms `users.rowsecurity=true`, `is_admin()` routine exists, pre-existing policies align with spec claims.

---

## Verdict

**PASS** — 0 CRITICAL + 0 HIGH. Spec 214 amended (iter-2) clears the data-layer gate.

Implementation planning may proceed. MEDIUM/LOW findings are non-blocking and should be folded into the `/plan` output as first-PR hygiene items.

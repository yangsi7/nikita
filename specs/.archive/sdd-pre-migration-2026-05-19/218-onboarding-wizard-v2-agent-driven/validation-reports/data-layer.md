# GATE 2: Data Layer Validation Report — Spec 218

**Spec**: `specs/218-onboarding-wizard-v2-agent-driven/spec.md` (553 lines)
**Brief**: `~/.claude/plans/immutable-wondering-gray.md` §23.5, §23.6, §23.7, §23.8, §23.10
**Validator**: sdd-data-layer-validator
**Timestamp**: 2026-05-09

## Verdict

**FAIL**

## Severity Counts

CRITICAL=2 HIGH=4 MEDIUM=3 LOW=2

---

## Summary

Spec 218 references the right concerns at a behavioral level (idempotency in FR-017, state replay in FR-016, single-fire phone demo in FR-011, DAG invalidation in FR-007, handoff timestamp in FR-002), but the spec itself does NOT enumerate the **schema artifacts** the brief commits to. The brief's §23.5 (`phone_demo_calls` table), §23.7 (DB unique constraint, cache schemas), §23.8 (`onboarding_profile` JSONB shape), and §23.10 PR-218-6 migration are all locked decisions, but the spec body never names the new table, never declares its required columns/constraints/RLS, never names the JSONB column on the user row, and never references the migration PR.

Because the spec is `technology_agnostic: true`, full DDL is correctly out of scope, but the CRITICAL gap is that the spec does not even NAME the new persistence surfaces (table, JSONB column, cache columns, FK relationships). Implementation planning cannot proceed without this — the planner has no way to know what to migrate.

Per `.claude/rules/testing.md` "DB Migration Checklist", every new Postgres table must ship with `ENABLE ROW LEVEL SECURITY` + `CREATE POLICY` + `WITH CHECK`. The spec is silent on RLS for the new `phone_demo_calls` table. This is a CRITICAL omission given the data is per-user and webhook-mutated.

---

## Findings

### CRITICAL

#### C-1 — `phone_demo_calls` table never named in spec
- **Category**: Schema Design / Migration
- **Location**: FR-009, FR-010, FR-011, AC-003-004 (mentions "real-time subscription"), Out-of-Scope
- **Issue**: Brief §23.5 LOCKED a new `phone_demo_calls` table with Realtime subscription + DB unique constraint; brief §23.10 commits this migration to PR-218-6. The spec NEVER mentions the table, its columns, or that a migration is required. FR-011 says "DB unique constraint" implicitly (via FR-017), but FR-009/010/011 do not even name the entity.
- **Why CRITICAL**: Implementation planning cannot proceed without knowing a new table is being introduced. The planner needs the entity to derive task #s, RLS work, FE Realtime channel name. Currently zero spec lines say "a new table is required."
- **Recommendation**: Add a "Data Entities" section (or expand FR-009/010/011) to enumerate:
  - `phone_demo_calls` (NEW): `user_id` (FK to `auth.users`, UNIQUE — enforces FR-011 single-fire), `phone_e164` (text), `status` (enum: pending/ringing/in_progress/ended/failed), `created_at`, `ended_at`, `provider_call_sid` (nullable), `failure_reason` (nullable). Realtime channel: `phone_demo_calls:user_id={uid}`.
  - Acknowledge the migration ships in PR-218-6 per brief §23.10.

#### C-2 — RLS posture for `phone_demo_calls` not declared
- **Category**: Row Level Security
- **Location**: NFR Security section, FR-009/010/011
- **Issue**: Per `.claude/rules/testing.md` DB Migration Checklist: every new table MUST `ENABLE ROW LEVEL SECURITY` + ≥1 `CREATE POLICY` + `WITH CHECK` clauses on UPDATE policies. Spec 218 introduces a per-user table with webhook mutation but never specifies the RLS posture.
- **Why CRITICAL**: A new table containing user PII (phone_e164) without RLS is open to all authenticated users by default. Webhook-driven status updates also need a privileged-role policy or service-role bypass — neither is mentioned.
- **Recommendation**: Add an RLS subsection to NFR Security:
  - `ALTER TABLE phone_demo_calls ENABLE ROW LEVEL SECURITY;`
  - User SELECT policy: `USING (user_id = (SELECT auth.uid()))` — user can read only their own row (FE Realtime subscribes via this).
  - INSERT policy: backend service role only (BE initiates the call, not the user).
  - UPDATE policy: backend/webhook only (status transitions). NO user-facing UPDATE policy. If any UPDATE policy is added later, it MUST include `WITH CHECK`.
  - DELETE policy: admin/service-role only.
  - Add an acceptance criterion in US-3 asserting `mcp__supabase__list_policies` shows the policies active post-migration.

### HIGH

#### H-1 — State replay JSONB schema not defined in spec
- **Category**: Schema Design / Persistence
- **Location**: FR-016, AC-005-002, AC-005-003
- **Issue**: Brief §23.8 locks the `onboarding_profile` JSONB shape on the `users` row: `{version, slots, phase, conversation[], elided_extracted, agent_envelope_cache}`. Spec FR-016 says "rebuild ... from the persisted conversation log AND a snapshot summary, with the conversation log winning on mismatch" — but never names the JSONB column, never declares the required keys, never specifies the version field, never mentions the `agent_envelope_cache` sub-key (critical for AC-005-003 — refresh-mid-turn re-serves from cache).
- **Why HIGH**: Without naming the column + keys, the planner cannot derive migration tasks, type definitions, or replay-correctness tests. AC-005-002 ("conversation log is the authoritative source on any mismatch") cannot be tested without the schema being declared.
- **Recommendation**: Add to FR-016 a "Persistence Schema" subsection naming:
  - Column: `users.onboarding_profile` (JSONB) — or whatever name the planner picks (existing pattern at `nikita/api/routes/portal_onboarding.py` may already have a column; spec must declare which it is).
  - Required keys: `version` (int, currently 2), `slots` (WizardSlots dict), `phase` ("phase1" | "phase2" | "complete"), `conversation` (list of turn objects with turn_id/role/envelope/extracted/timestamp/phase), `elided_extracted` (dict), `agent_envelope_cache` (dict keyed by state_hash).
  - Replay rule: snapshot is fast-path; conversation log wins on mismatch (already in FR-016 prose, but tie to the named schema keys).

#### H-2 — Idempotency cache columns / state_hash strategy not detailed
- **Category**: Data Integrity / Idempotency
- **Location**: FR-017
- **Issue**: FR-017 enumerates 5 idempotent surfaces (phone, cohort, firecrawl, envelope, backstory) but only gives cache-key shapes informally. Brief §23.7 specifies:
  - Phone: DB unique constraint on `phone_demo_calls.user_id` (NOT `(user_id, phone_e164)` despite phrasing in the brief — single-fire per user lifetime is the FR-011 invariant).
  - Envelope: cache-by-`(user_id, target_slot, state_hash)` stored in `agent_envelope_cache` sub-key of the JSONB profile (per §23.8).
  - Firecrawl Phase 2: cache-by-`(slot, user_id, prior_state_hash)` via existing `IdempotencyStore` (`nikita/onboarding/idempotency.py`).
- **Why HIGH**: AC-005-003 ("same envelope re-served from cache") is not testable without naming where the cache lives. FR-011 single-fire is not enforceable without naming the unique constraint column.
- **Recommendation**: Expand FR-017 with a per-side-effect persistence row:
  | Side-effect | Idempotency mechanism | Storage |
  |---|---|---|
  | Phone outbound | DB UNIQUE on phone_demo_calls.user_id | new table |
  | Envelope generation | cache key (user_id, target_slot, state_hash) | onboarding_profile.agent_envelope_cache JSONB sub-key |
  | Firecrawl Phase 2 | cache key (slot, user_id, prior_state_hash) | existing IdempotencyStore |
  | Cohort lookup | deterministic, no cache needed | static module |
  | Backstory | existing pattern, reused as-is | unchanged |

#### H-3 — DAG invalidation persistence side-effect not specified
- **Category**: Data Integrity
- **Location**: FR-007, AC-006-002
- **Issue**: FR-007 mandates "invalidate all downstream dependent slots and ask the user to re-confirm before applying the edit." But it does NOT specify the persistence-layer behavior: do the invalidated slots get NULLed in `onboarding_profile.slots`? Is the invalidation event appended to `conversation[]` (audit trail)? Is the `agent_envelope_cache` for downstream slots evicted?
- **Why HIGH**: Implementation will diverge based on which the planner picks. AC-006-002 ("hangouts is invalidated and re-asked with refreshed options") is not testable without specifying observable persistence state.
- **Recommendation**: Add to FR-007:
  - Invalidated downstream slot fields MUST be NULLed in `onboarding_profile.slots`.
  - Invalidation event MUST be appended to `onboarding_profile.conversation[]` with `role: "system"`, `kind: "dag_invalidation"`, listing edited slot + cleared slots.
  - Cached envelopes for invalidated slots MUST be evicted from `onboarding_profile.agent_envelope_cache` (otherwise stale cache re-serves wrong options after edit).

#### H-4 — `phase_2_started_at` field location not specified
- **Category**: Schema Design
- **Location**: FR-002, AC-001-004, Risk R3
- **Issue**: FR-002 says "persist a `phase_2_started_at` timestamp on the user profile." Ambiguous — is this a top-level column on `users` (or `user_profiles`), or a key in the `onboarding_profile` JSONB? Brief §23.8 places `phase` at JSONB top level but does NOT include `phase_2_started_at`.
- **Why HIGH**: AC-001-004 asserts persistence ordering ("`phase_2_started_at` is persisted before the first Phase 2 envelope is emitted"). Without naming the storage location, the test cannot inspect the right surface.
- **Recommendation**: Decide and document: place `phase_2_started_at` as a key inside `onboarding_profile` JSONB (consistent with `phase` co-located there per §23.8), OR add a new top-level `users.phase_2_started_at` column. Given solo-dev no-migration-ceremony posture, JSONB-key is cheaper.

### MEDIUM

#### M-1 — Cohort lookup storage modality confirmed but not pinned in spec
- **Category**: Schema Design
- **Location**: FR-012, AC-004-001, AC-004-002
- **Issue**: Brief §23.2 says cohort lookup is **static Python module** (`nikita/agents/onboarding/cohort_chips.py` extended). Spec FR-012 says "static lookup table" without explicitly stating no-DB. A reader could reasonably infer DB-backed.
- **Why MEDIUM**: Disambiguation prevents the planner spawning RLS / migration tasks for a non-existent table.
- **Recommendation**: Add to FR-012: "The static cohort lookup MUST be implemented as an in-memory Python module (no DB table, no migration). Extension of `nikita/agents/onboarding/cohort_chips.py` per brief §23.2."

#### M-2 — Cascade behavior on `auth.users` deletion not specified
- **Category**: Relationships / Cascade
- **Location**: FR-009/010/011 (implied), GDPR constraint at line 411
- **Issue**: Constraints section line 411 mandates "Slot data persistence must allow user-initiated deletion (existing GDPR pathway)." A new `phone_demo_calls` table FK'd to `auth.users` must specify ON DELETE behavior (CASCADE for GDPR conformance).
- **Why MEDIUM**: FK cascade behavior is a routine but consequential schema decision. Missing = either dangling rows or surprise CASCADE wipes.
- **Recommendation**: Add to the new "Data Entities" section (per C-1): `phone_demo_calls.user_id` REFERENCES `auth.users(id)` ON DELETE CASCADE. Same for `user_profiles.onboarding_profile` JSONB column — already cascades via existing pattern; spec should reaffirm.

#### M-3 — Realtime subscription channel name + filter not declared
- **Category**: Realtime
- **Location**: AC-003-004 ("FE receives a status update via real-time subscription")
- **Issue**: Brief §23.5 specifies Supabase Realtime on `phone_demo_calls`; spec mentions "real-time subscription (NOT polling)" but does not declare:
  - Channel naming convention (e.g., `phone_demo_calls:user_id=eq.{uid}`)
  - Subscription must be filtered to the authenticated user (FE cannot subscribe to all rows)
  - The RLS policy from C-2 enforces the per-user filter at the DB level, but the FE channel filter is the perf knob
- **Why MEDIUM**: Without channel-name + filter declaration, FE planner may build a too-broad subscription (perf issue) OR miss the filter (security signal — RLS catches it but defense-in-depth).
- **Recommendation**: Add to FR-010 or AC-003-004: "FE Realtime subscription MUST filter by `user_id = auth.uid()` at channel-creation time. Channel name MUST be of the form `phone_demo_calls:user_id={uid}`."

### LOW

#### L-1 — Conversation-log size growth bound not specified
- **Category**: Data Integrity
- **Location**: NFR Scalability ("Conversation log MUST handle 50+ turns per user")
- **Issue**: 50+ turns is a soft target; no hard cap stated. JSONB columns can grow unbounded; eventually `users` row size becomes a perf cliff.
- **Recommendation**: Add a soft cap (e.g., 200 turns) or commit to truncation/archival policy in v3. Non-blocking.

#### L-2 — `agent_envelope_cache` eviction policy unspecified
- **Category**: Data Integrity
- **Location**: FR-017 (envelope idempotency)
- **Issue**: Cache grows monotonically per state_hash. Solo-dev pre-launch + max ~12 Phase 1 + 8 Phase 2 turns = ~20 entries per user — bounded, fine. But declaring "eviction unnecessary; finite by Phase termination" makes the intent explicit.
- **Recommendation**: Add a one-liner to FR-017: "Envelope cache eviction unnecessary; bounded by total wizard turn count (~20 entries per user lifetime)."

---

## Schema Coverage Matrix

| Concern | Spec Section | Brief Reference | Status |
|---|---|---|---|
| State replay JSONB shape | FR-016 (behavioral) | §23.8 (named keys) | **GAP — H-1** |
| `phase_2_started_at` location | FR-002, AC-001-004 | not specified | **GAP — H-4** |
| `phone_demo_calls` table | FR-009/010/011 (implicit) | §23.5 (LOCKED table) | **GAP — C-1** |
| `phone_demo_calls` RLS | NFR Security (silent) | §23.5 + testing.md DB checklist | **GAP — C-2** |
| Phone single-fire constraint | FR-011 | §23.7 (UNIQUE on user_id) | partial (constraint not named) |
| Cohort lookup storage | FR-012 (ambiguous) | §23.2 (static py module) | partial — M-1 |
| Idempotency mechanisms | FR-017 (5 surfaces named) | §23.7 (per-surface table) | partial — H-2 |
| DAG invalidation persistence | FR-007 (behavioral) | §23.6 (DAG declared) | **GAP — H-3** |
| Realtime channel + filter | AC-003-004 (mention) | §23.5 (NO polling) | partial — M-3 |
| Migration plan / PR-218-6 | not mentioned in spec | §23.10 PR roadmap | partial (acceptable — out-of-scope reference) |
| FK cascade on auth.users delete | not specified | implied by GDPR constraint | partial — M-2 |

---

## Entity Inventory

| Entity | Type | Status in Spec | Required Fields (per brief) |
|---|---|---|---|
| `phone_demo_calls` | NEW table | NOT NAMED | `id`, `user_id` (FK auth.users, UNIQUE for FR-011), `phone_e164`, `status`, `created_at`, `ended_at`, `provider_call_sid?`, `failure_reason?` |
| `users.onboarding_profile` (JSONB) | existing column or new? | NOT NAMED | keys: `version`, `slots`, `phase`, `conversation[]`, `elided_extracted`, `agent_envelope_cache` |
| `phase_2_started_at` | new field | NAMED but location ambiguous | timestamp; either JSONB key or new column |
| `cohort_chips` (static) | Python module, not DB | inferred from FR-012 | M-1: pin the static-module modality |

---

## Relationship Map (proposed)

```
auth.users 1──1 user_profiles (existing)
auth.users 1──N phone_demo_calls (NEW; user_id UNIQUE → effectively 1:1 across lifetime)
auth.users 1──1 users.onboarding_profile JSONB (NEW key on users row, shape per §23.8)
```

ON DELETE CASCADE required on phone_demo_calls.user_id for GDPR conformance.

---

## RLS Policy Checklist (post-fix expectation)

- [ ] `ALTER TABLE phone_demo_calls ENABLE ROW LEVEL SECURITY;` — REQUIRED by C-2
- [ ] SELECT policy `USING (user_id = (SELECT auth.uid()))` — user reads own row (Realtime needs this)
- [ ] INSERT policy: service-role only (BE initiates outbound call)
- [ ] UPDATE policy: service-role only + `WITH CHECK (user_id = OLD.user_id)` if any user-update path added
- [ ] DELETE policy: admin/service-role only
- [ ] Verify post-migration via `mcp__supabase__list_policies`

---

## Index Requirements (proposed)

| Table | Column(s) | Type | Query Pattern |
|---|---|---|---|
| `phone_demo_calls` | `user_id` | UNIQUE (covers FR-011 single-fire) | enforces single-fire + FE-by-user lookup |
| `phone_demo_calls` | `created_at` | btree (optional) | observability/cost analytics queries |

`onboarding_profile` JSONB does not need a GIN index for v2 — read access is by `user_id` PK only.

---

## Recommendations (Priority-Ordered)

1. **CRITICAL — Add a "Data Entities" section to spec** enumerating `phone_demo_calls` table (columns, FK, UNIQUE constraint, ON DELETE CASCADE) and `users.onboarding_profile` JSONB shape with required keys per §23.8. This unblocks planning.
2. **CRITICAL — Add RLS posture to NFR Security** for `phone_demo_calls`: ENABLE RLS + SELECT (user-scoped) + INSERT/UPDATE/DELETE (service-role) + `WITH CHECK` on any UPDATE policies. Reference `.claude/rules/testing.md` DB Migration Checklist as the source.
3. **HIGH — Specify `phase_2_started_at` storage location** (recommend: JSONB key inside `onboarding_profile` to avoid migration). Tie AC-001-004 to the named field path.
4. **HIGH — Expand FR-007 with persistence side-effects** of DAG invalidation (NULL slots, append audit event, evict cache).
5. **HIGH — Expand FR-017 with a per-side-effect persistence row** (table from H-2) so each idempotency mechanism's storage is named.
6. **MEDIUM — Pin cohort lookup as static Python module** (M-1) to prevent planner spawning DB tasks.
7. **MEDIUM — Specify ON DELETE CASCADE** on the new FK + Realtime channel filter convention.
8. **LOW — Add conversation-log soft cap and envelope-cache eviction note** for completeness.

---

## Verdict Justification

PASS criteria: 0 CRITICAL + 0 HIGH findings.
Actual: 2 CRITICAL + 4 HIGH.

**FAIL** — spec must be amended on at least the 6 CRITICAL+HIGH findings before /plan (Phase 5).

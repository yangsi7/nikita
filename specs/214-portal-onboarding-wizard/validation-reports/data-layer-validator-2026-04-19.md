# Data Layer Validation Report, Spec 214 Amendment (FR-11c / FR-11d / FR-11e / NR-1b)

**Spec**: `/Users/yangsim/Nanoleq/sideProjects/nikita/specs/214-portal-onboarding-wizard/spec.md`
**Companion**: `/Users/yangsim/Nanoleq/sideProjects/nikita/specs/214-portal-onboarding-wizard/technical-spec.md`
**Status**: FAIL (2 HIGH, 5 MEDIUM, 3 LOW)
**Timestamp**: 2026-04-19
**Validator**: sdd-data-layer-validator
**Scope**: data-layer slice only (JSONB shape, RLS preservation, migration plan, write concurrency, index need, Spec 213 consistency). Out of scope: agent semantics, UI, auth.

---

## Summary

| Severity | Count |
|---|---|
| CRITICAL | 0 |
| HIGH | 2 |
| MEDIUM | 5 |
| LOW | 3 |

Pass/fail criterion (0 CRITICAL + 0 HIGH required): **FAIL** on HIGH-1 and HIGH-2. Both are addressable in spec (no DDL). After spec clarifications land, the amendment is implementation-ready.

---

## Findings

| # | Severity | Category | Issue | Location | Recommendation |
|---|---|---|---|---|---|
| HIGH-1 | HIGH | Concurrency / write pattern | `converse` write pattern for `users.onboarding_profile.conversation` is unspecified. Tech spec §2.3 step 6 says "persist turn to conversation JSONB" but does not define: full-replace vs JSONB `||` append vs `jsonb_set`. For JSONB in Postgres there is no partial update; the entire column is rewritten. With 100-turn cap ~20KB, that's fine per write, but a race between two concurrent `converse` calls for the same `user_id` (e.g., user double-taps send) can produce a lost-turn write under last-writer-wins without row-level locking. | tech spec §2.3, spec.md ~564 (AC-NR1b.1) | Specify exact write pattern: either (a) `SELECT ... FOR UPDATE` inside a transaction, read+append+write, OR (b) optimistic concurrency via a conversation-length precondition, OR (c) server-side serialization per user_id. Add an AC: "concurrent `converse` calls for the same user_id MUST NOT drop turns". |
| HIGH-2 | HIGH | Migration / legacy data | `user_onboarding_state` orphan handling is ambiguous for FR-11c. Spec says "rows stay as orphaned data for a 30-day quiet period; table drop ships in a follow-up migration" (spec.md ~680). But: (a) no explicit FK constraint audit (is there `ON DELETE CASCADE` from `users.id`?), (b) no mention of whether in-progress rows will be silently abandoned or back-filled to `users.onboarding_profile`, (c) no drop-migration draft file referenced. Risk: follow-up cleanup PR cannot be safely written without the drop plan documented alongside the semantic (is Q&A state transferred to the portal? If so, how? If not, that should be explicit). | spec.md FR-11c ~680, tech spec §6.3, §8.1 PR 5 | Add a subsection to the spec: "Legacy data disposition". Specify: (1) whether existing `user_onboarding_state` rows with `status='in_progress'` block the portal resume path or are ignored, (2) FK audit result (CASCADE vs no FK — run `\d user_onboarding_state` and paste), (3) a draft migration file stub `migrations/YYYYMMDD_drop_user_onboarding_state.sql` with the DROP statement and pre-flight check (`SELECT COUNT(*) FROM user_onboarding_state WHERE created_at > now() - interval '30 days'` must return 0 before drop). |
| MED-1 | MEDIUM | Schema integrity | No JSONB shape enforcement at DB level (no CHECK constraint on `onboarding_profile.conversation`). All validation lives in Pydantic `Turn` model and the API layer. This is consistent with Spec 213's approach (no CHECK on existing `onboarding_profile`) so it is not a regression, but a malformed client write via direct DB access would not be caught. | tech spec §4.1 | Acceptable trade-off; document explicitly in spec that DB-level shape validation is intentionally omitted (app-layer only). Optionally add a lightweight CHECK: `CHECK (jsonb_typeof(onboarding_profile->'conversation') IN ('array', 'null'))` as a cheap guardrail. |
| MED-2 | MEDIUM | Bounded-size enforcement | AC-NR1b.5 says "max 100 turns per user; if exceeded, oldest turn elided". Enforcement site is unspecified: client-side trim, server-side trim before write, or DB trigger. With chat-first flow, the server is authoritative (client localStorage is a mirror). | spec.md ~568, tech spec §2.3 | Specify enforcement: "server-side trim in `converse` endpoint before JSONB write; if `len(conversation) > 100`, pop oldest turn while preserving any `extracted` payload by merging it into `onboarding_profile.{field_name}` if not already present". Add unit test in `tests/api/routes/test_converse_endpoint.py::test_conversation_trim_preserves_extracted_fields`. |
| MED-3 | MEDIUM | RLS preservation audit | Spec does not explicitly assert that `users.onboarding_profile.conversation` inherits existing `users` table RLS (Spec 213). Reviewer must infer. For a reader, it's "obvious" JSONB subfields inherit row-level policies (RLS is row-scoped, not column-scoped), but amendment should surface this explicitly given the conversation may contain free-form PII (name, occupation, phone mentions). | spec.md NR-1b / tech spec §4.1 | Add an RLS note: "`onboarding_profile.conversation` inherits existing `users` RLS (Spec 213). Users can only SELECT / UPDATE their own row. Admin reads go through the existing service-role backend; no new policy required." Add a verification step: run `mcp__supabase__list_policies` post-merge and confirm no new policies exist on `users`. |
| MED-4 | MEDIUM | `pending_handoff` semantic migration | FR-11e changes `pending_handoff` clear-site from `message_handler` (first-user-message) to `_handle_start_with_payload` (bind-time). Spec says "legacy users who onboarded pre-FR-11c but whose `pending_handoff` was already cleared by an earlier message are unaffected" (tech spec §4.2). But: users currently in flight with `pending_handoff=true` at the merge moment (mid-handoff) are unaddressed. If they tap the CTA post-merge they get a proactive greeting; if they send a message first, the old `message_handler` path no longer exists (moved semantics). Risk: small population, one-time greeting might not fire. | tech spec §4.2, spec.md AC-11e.3 | Add an AC: "on FR-11e merge, run a one-shot backfill query: `SELECT COUNT(*) FROM users WHERE pending_handoff = true` — if count > 0, document the expected resolution path (next `/start` from those users triggers greeting; otherwise log and clear)". Alternatively, add a migration that clears stale `pending_handoff` flags older than 24h at merge time. |
| MED-5 | MEDIUM | Concurrent-access clarity on `pending_handoff` | AC-11e.3 says `pending_handoff` cleared "atomically" on greeting send. Tech spec §2.5 says "Clear `users.pending_handoff` in the same transaction". But the SQL form is not given. One-shot semantics require: `UPDATE users SET pending_handoff = false WHERE id = :user_id AND pending_handoff = true RETURNING pending_handoff` — the `AND pending_handoff = true` predicate prevents double-greet on race. | spec.md AC-11e.3, tech spec §2.5 | Add explicit SQL in tech spec: `UPDATE users SET pending_handoff = false WHERE id = :user_id AND pending_handoff = true RETURNING pending_handoff`. Add test asserting `rowcount` behavior: first call returns 1 row, second concurrent call returns 0 rows → greeting not dispatched. |
| LOW-1 | LOW | Index need analysis | Confirm no new indexes required. Read/write pattern on `onboarding_profile.conversation` is always PK-bound (`WHERE id = :user_id`). No JSONB GIN needed; no queries scan `conversation` contents. Existing PK index on `users.id` suffices. | tech spec §4.1 | Add a one-line note: "No new indexes required. All reads/writes are PK-bound on `users.id`." Prevents future reviewer from asking the same question. |
| LOW-2 | LOW | `schema_version` ownership | Spec says "v1 state hydrates to v2 by synthesizing empty conversation" (AC-NR1b.3). Unclear whether `schema_version` lives in the JSONB (server) or only in localStorage (client). Tech spec §4.1 example JSONB does not include `schema_version`. | spec.md ~554, tech spec §4.1 | Clarify: `schema_version` is client-localStorage-only (not persisted to JSONB). Server does not version `onboarding_profile`; it's additive-always. Document in tech spec §4.1. |
| LOW-3 | LOW | Extraction confidence storage | Extraction schemas have a `confidence: float` field (tech spec §2.2). AC-NR1b expects `conversation[].extracted?: Partial<OnboardingProfile>` on user turns but does NOT store confidence. Storage decision: confidence is transient (triggers `confirmation_required`) and NOT persisted. | tech spec §2.2 / §4.1 | Document explicitly: "confidence is a transient agent signal; NOT stored in `conversation[].extracted` nor in top-level `onboarding_profile` fields. Only the extracted value itself is persisted." This prevents implementation drift where confidence accidentally lands in JSONB. |

---

## Entity Inventory

| Entity | Attributes touched | PK | FK / RLS | New column? | Notes |
|---|---|---|---|---|---|
| `users` | `onboarding_profile` (JSONB, subfield `conversation` added), `pending_handoff` (bool, semantic change), `telegram_id`, `onboarding_status`, `game_status` | `id` (uuid) | Existing RLS from Spec 213 inherits; auth.uid() = users.id | NO | All changes additive; no DDL |
| `user_onboarding_state` | Entire table | `user_id` (uuid) | FK audit required (HIGH-2) | NO | Deferred drop, 30-day quiet period |
| `public.profiles` | Read-only via `profile_repository.get(user.id)` | `user_id` (uuid) | Existing RLS | NO | Used by `_handle_start` E6 limbo detection |
| `telegram_link_codes` | Consumed via `verify_code` (PR #322) | `code` | Existing | NO | Unchanged by this amendment |
| `backstory_cache` (Spec 213) | Read by `FirstMessageGenerator` extension (FR-11e) | `cache_key` | Existing RLS | NO | Unchanged |

---

## Relationship Map

```
users (id, onboarding_profile JSONB {conversation: Turn[], ...}, pending_handoff bool, telegram_id bigint UNIQUE)
  │
  ├── 1 : 0..1 ── public.profiles (user_id FK)          existing, read-only here
  │
  ├── 1 : N ── backstories (user_id FK, cache_key)       existing; read by FirstMessageGenerator
  │
  ├── 1 : 0..1 ── user_onboarding_state (user_id FK)    LEGACY, deferred drop (HIGH-2)
  │
  └── 1 : 0..1 ── telegram_link_codes (user_id FK)       single-use; consumed on /start <code>
```

No new tables. No new FKs. No new junctions. All graph edges preserved from Spec 213 baseline.

---

## RLS Policy Checklist

- [x] `users.onboarding_profile.conversation` JSONB subfield inherits existing Spec 213 `users` RLS — row-scoped, auth.uid() = id. No new policy. (MED-3: document this inheritance explicitly.)
- [x] `users.pending_handoff` — existing column, same RLS applies.
- [x] Admin / service-role reads — existing backend connection pool with service-role key; no new policy.
- [x] `user_onboarding_state` legacy — existing RLS unchanged during quiet period. Drop migration (post-30d) removes RLS implicitly via table drop.
- [ ] Post-merge verification — run `mcp__supabase__list_policies` and confirm zero new policies added. (Add to PR 3 smoke checklist.)

---

## Index Requirements

| Table | Column(s) | Type | Query Pattern | Status |
|---|---|---|---|---|
| `users` | `id` (PK) | B-tree | `WHERE id = :user_id` in `converse` and `update pending_handoff` | EXISTING, sufficient |
| `users` | `telegram_id` | UNIQUE B-tree | `_handle_start` lookup | EXISTING (Spec 213), sufficient |
| `users` | `onboarding_profile->>...` | GIN (not needed) | No content-scan queries on `conversation` | NOT REQUIRED |

No new indexes required. Confirm in spec (LOW-1).

---

## Migration Plan Review

Per tech spec §8.1 ship sequence and §4 data-model section:

| PR | DDL / data migration needed? | Verdict |
|---|---|---|
| PR 1 FR-11c routing | NO schema change. Code-only. | OK |
| PR 2 FR-11d backend | NO schema change. `conversation` subfield is additive to existing `onboarding_profile JSONB`. | OK |
| PR 3 FR-11d portal | NO schema change. localStorage `schema_version` v1→v2 is client-side only. | OK |
| PR 4 FR-11e handoff | NO schema change. `pending_handoff` exists already; semantic change only. | OK, but see MED-4 (stale-flag backfill concern). |
| PR 5 cleanup (30d later) | YES: `DROP TABLE user_onboarding_state`. | Needs spec per HIGH-2. |

Rollback per-PR documented in §8.2. All PRs independently revertable. No data-destruction on rollback (conversation JSONB survives; ignored on old portal path).

---

## Consistency with Spec 213 Patterns

- `PortalOnboardingFacade` pattern (Spec 213): FR-11d does NOT use a facade for the new `ConversationAgent`. The endpoint calls the agent directly via Pydantic AI's `Agent.run()` pattern. This is **consistent** because the agent itself is the facade equivalent; wrapping a Pydantic AI agent in another class adds no value. Consistent with `BackstoryGeneratorService` pattern from Spec 213 PR 213-3.
- `BackstoryCacheRepository` reuse: FR-11e's `generate_handoff_greeting` correctly receives `backstory_repo: BackstoryRepository` as a DI parameter (tech spec §2.4). Consistent.
- `FirstMessageGenerator` extension (FR-11e / tech spec §2.4): extends via `trigger` parameter rather than subclass. Backward compat preserved for `trigger="first_user_message"`. Clean.
- `schema_version` on client localStorage: new pattern; Spec 213 localStorage did not version. Acceptable evolution since this is the first backward-incompatible localStorage shape change.

No Spec 213 pattern violations.

---

## Strengths

1. **Zero-DDL migration** is well-motivated. Using additive JSONB subfield instead of a new `onboarding_conversations` table avoids join overhead for a per-user 1:1-bound dataset. ~20KB worst-case payload fits comfortably in a JSONB column.
2. **Persona reuse via import** (`NIKITA_PERSONA` verbatim, not forked) is the right pattern for preventing voice drift across 3 agents (main text, conversation, handoff greeting).
3. **Rate-limit sharing with `/preview-backstory`** (10/min/user) reuses existing infrastructure; no new rate-limit bucket to reason about.
4. **Per-PR rollback plan** (tech spec §8.2) is complete and each PR is independently revertable. Ship-sequence-safe.
5. **Idempotent `pending_handoff` clear + one-shot greeting** semantics (AC-11e.3) are correctly articulated; fully preventing double-greet with a predicate UPDATE is standard pattern once SQL is specified (MED-5).
6. **Bounded conversation cap** (100 turns) prevents unbounded JSONB growth. Well within PostgreSQL JSONB limits (<1MB) with 10x headroom.
7. **Zero new indexes** needed — confirmed via query-pattern audit; all access is PK-bound.
8. **Spec 213 pattern continuity** (facade-equivalent agents, repository DI, RLS inheritance) is preserved throughout. No architectural drift.

---

## Recommendations (Actionable)

Rank-ordered by blocking status:

1. **HIGH-1, HIGH-2** — must resolve before planning can proceed. Concurrency write pattern (explicit SQL or transaction model) and legacy-data-disposition subsection (FK audit + drop-migration stub). Add to spec/tech-spec before `/plan`.
2. **MED-4, MED-5** — resolve in `/plan`; add pre-merge backfill-count query for `pending_handoff` and explicit SQL for atomic clear.
3. **MED-1, MED-2, MED-3** — document-only clarifications; spec gets 3 short paragraphs (DB-level validation intentionally omitted; server-side trim at 100 turns; RLS inheritance).
4. **LOW-1, LOW-2, LOW-3** — one-line notes each in tech spec for reviewer clarity.

No CRITICAL findings. No new tables, no FK additions, no new RLS policies, no new indexes. All findings are addressable in spec text only; no implementation rework implied.

---

## Summary Verdict

**FAIL** (2 HIGH). Amendment's data-layer design is fundamentally sound — additive JSONB, RLS inheritance, zero-DDL, per-PR rollback. Two HIGH findings block planning readiness, both resolvable by spec text updates (write-concurrency pattern + legacy-data-disposition). Once HIGH-1/2 are addressed, re-validate and expect PASS.

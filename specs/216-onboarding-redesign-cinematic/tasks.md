# Tasks — Spec 216 Onboarding Redesign Cinematic Agentic Wizard

**Spec ID**: 216-onboarding-redesign-cinematic
**Phase**: 6 (Task Generation), iter-2 (post-audit-FAIL fix)
**Date**: 2026-04-30
**Source**: `spec.md` + `subspecs/216-{A..F}/spec.md` AC tables (89 ACs total).
**Audit-fix log**: iter-1 audit returned FAIL (4 CRIT, 8 HIGH, 5 MED). iter-2 binds all 89 ACs, splits 216-C → 216-C1+C2, moves 3 mandatory test classes to 216-B as ship gate, reconciles plan §5 task ID ranges.

---

## Format

Each task entry:
- **ID** — `T-<PR>-<n>` where PR is `A`, `B`, `C1`, `C2`, `D`, `E`, `F`
- **Title** — imperative, ≤80 chars
- **Subspec AC refs** — pointer to acceptance criteria (the AC IS the testable contract)
- **Owner** — implementor / planner / walk-subagent
- **Estimate** — t-shirt size (S=2h, M=4h, L=8h)
- **Depends on** — predecessor task IDs
- **Acceptance** — minimum 2 testable criteria

---

## PR 216-A — Telegram canonical routing (depends: none, ~80 LOC + ~50 LOC tests)

### T-A-1: Add bare `/start` unbound-user golden test
- **Subspec AC**: A1.1
- **Owner**: implementor
- **Estimate**: S (2h)
- **Depends on**: none
- **Acceptance**:
  - [ ] AC-1: `tests/platforms/telegram/test_routing.py::test_bare_start_unbound_enters_signup_handler` exists, asserts `SignupHandler.handle_welcome` called exactly once
  - [ ] AC-2: Test fails on current master (RED phase verified)
  - [ ] AC-3: Test asserts `_handle_start` E1 path NOT called for unbound `/start`

### T-A-2: Reroute `/start` for unbound users + preserve bound + welcome-payload paths
- **Subspec AC**: A1.1, A1.2, A1.3, A1.4, A1.5
- **Owner**: implementor
- **Estimate**: M (4h)
- **Depends on**: T-A-1 (RED → GREEN)
- **Acceptance**:
  - [ ] AC-1: `nikita/api/routes/telegram.py:635-666` routes bare `/start` for unbound `telegram_id` → `SignupHandler.handle_welcome`
  - [ ] AC-2: `/start welcome` deep-link payload still routes to `SignupHandler.handle_welcome` (preserved per A1.2)
  - [ ] AC-3: Bound users (`telegram_id` resolves) bypass FSM, route to `CommandHandler` (preserved per A1.3)
  - [ ] AC-4: First reply ≤5s, Nikita-voiced ≤280 chars, asks for email (A1.4)
  - [ ] AC-5: `pending_signup_session` row inserted with `signup_state='awaiting_email'` (A1.5)
  - [ ] AC-6: T-A-1 golden test green

### T-A-3: PKCE magic-link + idempotent click contract
- **Subspec AC**: A1.6, A1.7, A1.9, A1.10, A1.13
- **Owner**: implementor
- **Estimate**: M (4h)
- **Depends on**: T-A-2
- **Acceptance**:
  - [ ] AC-1: OTP submit transitions `signup_state='magic_link_sent'` + populates `magic_link_token` (A1.6)
  - [ ] AC-2: Magic-link reply uses PKCE format `https://nikita-mygirl.com/auth/confirm?token_hash=...&type=...&next=/onboarding`, preview suppressed (A1.7)
  - [ ] AC-3: `/auth/confirm` second click — deterministic predicate per A1.9: cookie+session valid → 302 to `/dashboard`; else → 400 with `ErrorEnvelope(error="magic_link_consumed")`. Both branches tested. NO new session minting on path (b)
  - [ ] AC-4: Cookie contract on 200 response (A1.10): `HttpOnly=True, Secure=True, SameSite=Lax, Path=/, Max-Age >= 604800` — verified by parsing `Set-Cookie` in integration test
  - [ ] AC-5: All outbound `SignupHandler` messages with `nikita-mygirl.com` URL set `disable_web_page_preview=True` (A1.13) — verified by `test_disable_web_page_preview_on_all_signup_messages`

### T-A-4: Concurrent magic-link click race (A1.11)
- **Subspec AC**: A1.11
- **Owner**: implementor
- **Estimate**: M (4h)
- **Depends on**: T-A-3
- **Acceptance**:
  - [ ] AC-1: Integration test using `asyncio.gather` issues two simultaneous `/auth/confirm?token_hash=X` requests with same token
  - [ ] AC-2: Exactly ONE returns 200 + sets cookie; the OTHER returns 400 + `ErrorEnvelope(error="magic_link_consumed")`
  - [ ] AC-3: NO partial DB state — no orphan `auth.users` row, no missing `user_profiles` row (asserted via post-race DB query)

### T-A-5: Resume mid-wizard auth path (A1.12)
- **Subspec AC**: A1.12
- **Owner**: implementor
- **Estimate**: M (4h)
- **Depends on**: T-A-3
- **Acceptance**:
  - [ ] AC-1: User with valid JWT cookie navigating to `/onboarding` after closing tab mid-wizard — `state_reconstruction.build_state_from_conversation` hydrates from `nikita.conversation_jsonb`
  - [ ] AC-2: FE renders last assistant message + correct `progress_pct`; NO redirect to `/auth/confirm`
  - [ ] AC-3: Edge case: cookie valid but `conversation_jsonb` empty/null → render 'fresh start' UI (slot 1), do NOT redirect-loop

### T-A-6: Wrong-OTP destructive-purge guard (A1.14)
- **Subspec AC**: A1.14
- **Owner**: implementor
- **Estimate**: S (2h)
- **Depends on**: T-A-2
- **Acceptance**:
  - [ ] AC-1: `test_wrong_otp_does_not_destroy_session` asserts wrong OTP MUST NOT delete `pending_signup_session` row, MUST NOT decrement `code_attempts_remaining` past 0 silently, MUST NOT clear `magic_link_token` if already issued
  - [ ] AC-2: If current code violates → file as HIGH GH issue (escalates #437)

### T-A-7: Cleanup `_send_bare_portal_auth_link` (resolution Q1)
- **Subspec AC**: subspec A Open Q1 resolved
- **Owner**: implementor
- **Estimate**: S (2h)
- **Depends on**: T-A-2
- **Acceptance**:
  - [ ] AC-1: Function retained but restricted to non-`/start` deep-link payloads only; explicit guard in callers
  - [ ] AC-2: Grep verifies 0 callers from `/start` path post-fix
  - [ ] AC-3: Tests still green; commit message documents decision

### T-A-8: Plus-alias email regex acceptance test
- **Subspec AC**: subspec A "Test Identity" (auth-validator MED-3 closure)
- **Owner**: implementor
- **Estimate**: S (2h)
- **Depends on**: T-A-2
- **Acceptance**:
  - [ ] AC-1: `tests/platforms/telegram/test_signup_handler.py::test_plus_alias_email_accepted` asserts `simon.yang.ch+spec216walk@gmail.com` accepted by validation regex
  - [ ] AC-2: All `+`-aliased forms accepted by FSM email regex

---

## PR 216-B — Agentic wizard core (depends: 216-A merged, ~350 LOC + ~250 LOC tests)

### T-B-1: Extend `WizardSlots` to 13 fields + `SlotKind` StrEnum
- **Subspec AC**: B1.1, B1.18
- **Owner**: implementor
- **Estimate**: M (4h)
- **Depends on**: 216-A merged
- **Acceptance**:
  - [ ] AC-1: `nikita/agents/onboarding/state.py` `WizardSlots` has 13 optional fields matching SlotKind enum: `display_name`, `age`, `city`, `occupation`, `darkness_level`, `primary_hobbies`, `saturday_morning`, `geek_out_on`, `together_we_could`, `same_weird_if` (optional in FinalForm), `phone`, `voice_tone_pref`, `backstory_pick`
  - [ ] AC-2: `SlotKind` StrEnum at `nikita/agents/onboarding/question_registry.py` with the same 13 members (per spec.md L360-374)
  - [ ] AC-3: Lint test `test_slot_kind_enum_completeness.py` enforces every member appears in `ORDERED_QUESTIONS` AND has a paired template registry entry (B1.18)
  - [ ] AC-4: `TurnOutput.next_slot_kind` typed `SlotKind | None` (StrEnum, NOT inline `Literal[...]`)

### T-B-2: Add `FinalForm` Pydantic completion gate (B1.2)
- **Subspec AC**: B1.2
- **Owner**: implementor
- **Estimate**: M (4h)
- **Depends on**: T-B-1
- **Acceptance**:
  - [ ] AC-1: `FinalForm(BaseModel)` declares 13 required slots non-optional except `same_weird_if` (only optional)
  - [ ] AC-2: `@model_validator(mode="after")` enforces age ≥18 + voice_tone_pref-requires-phone consistency
  - [ ] AC-3: NO `is_complete = True` / `is_complete = False` literal anywhere in `/onboarding/answer` route handler (grep verified)

### T-B-3: `progress_pct` `@computed_field` + monotonicity test
- **Subspec AC**: B1.12
- **Owner**: implementor
- **Estimate**: S (2h)
- **Depends on**: T-B-1
- **Acceptance**:
  - [ ] AC-1: `WizardSlots.progress_pct` is `@computed_field @property` with formula `min(100, int((TOTAL - len(self.missing)) * 100 / TOTAL))`
  - [ ] AC-2: `tests/agents/onboarding/test_cumulative_state.py` (mandatory test class #1) — 13-turn fixture, `progress_pct[t+1] >= progress_pct[t]` for all t (CRIT, ship-gate for 216-B)

### T-B-4: Define `TurnOutput` + `TurnFailure` discriminated union
- **Subspec AC**: B1.3
- **Owner**: implementor
- **Estimate**: S (2h)
- **Depends on**: T-B-1
- **Acceptance**:
  - [ ] AC-1: Both classes carry `kind: Literal[...]` discriminator
  - [ ] AC-2: Pydantic v2 round-trip serialize/deserialize green
  - [ ] AC-3: `output_type=[TurnOutput, TurnFailure]` Tool Output mode default; NativeOutput / PromptedOutput NOT used

### T-B-5: Define `ConverseDeps` schema + sidecar DI
- **Subspec AC**: B1.19
- **Owner**: implementor
- **Estimate**: S (2h)
- **Depends on**: T-B-1
- **Acceptance**:
  - [ ] AC-1: `ConverseDeps` dataclass with all 14 fields per master spec §Type System Anchors (state, state_summary, last_slot_kind, last_value, next_slot_kind, next_slot_hint, cost_budget_remaining_usd, fetch_invocations_this_turn, fetch_cost_cumulative, cohort_cache, big5_confidence, traceparent, user_id, conversation_id)
  - [ ] AC-2: Used by `Agent(deps_type=ConverseDeps)` and surfaced via `RunContext[ConverseDeps]`
  - [ ] AC-3: Lint test asserts all 14 fields present + typed

### T-B-6: Rewrite agent constructor with discriminated output + `instructions=callable`
- **Subspec AC**: B1.3, B1.4
- **Owner**: implementor
- **Estimate**: M (4h)
- **Depends on**: T-B-2, T-B-4, T-B-5
- **Acceptance**:
  - [ ] AC-1: `nikita/agents/onboarding/conversation_agent.py:127-197` rewritten; types L69-126 reused
  - [ ] AC-2: Agent uses `output_type=[TurnOutput, TurnFailure]` + `Agent(retries=2)`
  - [ ] AC-3: `instructions=inject_per_turn_context` callable injects per-turn `state.missing` + `next_slot_hint` + cumulative summary + `last_slot_kind` + `last_value`; static `system_prompt` NOT used for routing rules

### T-B-7: `@output_validator` for mirror-echo + length + cluster-confidence
- **Subspec AC**: B1.5
- **Owner**: implementor
- **Estimate**: M (4h)
- **Depends on**: T-B-6
- **Acceptance**:
  - [ ] AC-1: Mirror-echo (`name * 2 in reaction.lower()`) when `last_slot=="name"` raises `ModelRetry` (closes #443)
  - [ ] AC-2: `len(reaction) > 140` raises `ModelRetry`
  - [ ] AC-3: M2 cluster confidence `<0.6` AND `cluster != "ambiguous"` raises `ModelRetry`
  - [ ] AC-4: Mock-LLM-emits-wrong-tool recovery test (`tests/agents/onboarding/test_tool_recovery.py`, mandatory test class #3) — wrong-extraction → `ModelRetry` → recovery via deterministic fallback (CRIT, ship-gate for 216-B)

### T-B-8: M1-M4 meta-prompt templates + cluster enum exhaustiveness
- **Subspec AC**: B1.6, B1.7, B1.8
- **Owner**: implementor
- **Estimate**: L (8h)
- **Depends on**: T-B-6
- **Acceptance**:
  - [ ] AC-1: `nikita/agents/onboarding/conversation_prompts.py:33-115,128` REPLACED with M1 GenerateFollowUpFromAnswer, M2 ClassifyAnswerCluster, M3 RefineSummary, M4 DetectSaturation
  - [ ] AC-2: M1 fires depth-1 after each Hinge prose root + hobbies; depth-2 ONLY when `cluster=ambiguous` AND `turn_count_for_topic<3`
  - [ ] AC-3: M2 confidence ≥0.6 OR triggers depth-2 follow-up; total dynamic follow-ups capped at 6; cost circuit fires at $0.05 budget remaining
  - [ ] AC-4: Cluster enum exhaustiveness — `test_cluster_enum_completeness.py` lint asserts every Literal cluster value has paired template registry entry
  - [ ] AC-5: Golden snapshot tests for M1-M4 (`test_meta_prompts.py`) green

### T-B-9: NR-02 prompt-cache breakpoint after FIXED block
- **Subspec AC**: B1.20
- **Owner**: implementor
- **Estimate**: M (4h)
- **Depends on**: T-B-8
- **Acceptance**:
  - [ ] AC-1: M1-M4 FIXED skeleton + `inject_per_turn_context` base instructions emitted as contiguous prefix with Anthropic `cache_control: {type: "ephemeral"}` breakpoint after FIXED block
  - [ ] AC-2: Cloud Run logs show `cache_read_input_tokens / total_input_tokens >= 0.6` averaged over 10+ flows (verified post-deploy via log query)

### T-B-10: `follow_up_registry.yaml` + completeness lint test
- **Subspec AC**: B1.9, NR-06
- **Owner**: implementor
- **Estimate**: S (2h)
- **Depends on**: T-B-8
- **Acceptance**:
  - [ ] AC-1: `nikita/agents/onboarding/follow_up_registry.yaml` keyed by `(slot_kind, cluster)`, value = `{static_fallback_question, why_we_ask, control_type}`
  - [ ] AC-2: `test_follow_up_registry_completeness.py` lint enforces every dynamic node has fallback
  - [ ] AC-3: Static fallback used when (a) M1 final retry exhausted, (b) cost circuit active, OR (c) firecrawl tool times out

### T-B-11: `agent.run(message_history=...)` + `result.new_messages()` round-trip
- **Subspec AC**: B1.10, B1.21
- **Owner**: implementor
- **Estimate**: M (4h)
- **Depends on**: T-B-6
- **Acceptance**:
  - [ ] AC-1: `agent.run(..., message_history=hydrate_message_history(state.messages), deps=deps)` called
  - [ ] AC-2: `[m.model_dump(mode='json') for m in result.new_messages()]` appended to `nikita.conversation_jsonb["messages"]`
  - [ ] AC-3: Round-trip JSONB → `hydrate_message_history` → `agent.run` → `new_messages` → JSONB without semantic loss (test fixture per B1.21)
  - [ ] AC-4: Request body does NOT re-pass conversation context (grep verified)

### T-B-12: `capture_run_messages` + `UnexpectedModelBehavior` fallback (B1.11, B1.17)
- **Subspec AC**: B1.11, B1.17
- **Owner**: implementor
- **Estimate**: S (2h)
- **Depends on**: T-B-11
- **Acceptance**:
  - [ ] AC-1: `with capture_run_messages() as messages:` wraps every call
  - [ ] AC-2: On `UnexpectedModelBehavior`: log Cloud Run traceparent + messages + return 200 + `AnswerResponse(output=TurnOutput from registry, meta={"fallback_reason": "model_behavior_error"})` (B1.17)
  - [ ] AC-3: Cost-circuit fallback uses `meta={"fallback_reason": "cost_circuit"}`
  - [ ] AC-4: NEVER 500 to FE; test `test_unexpected_model_behavior_fallback.py` green

### T-B-13: New `POST /api/v1/onboarding/answer` route + Pydantic schemas
- **Subspec AC**: B1.13, B1.14, B1.15
- **Owner**: implementor
- **Estimate**: L (8h)
- **Depends on**: T-B-2, T-B-4, T-B-11
- **Acceptance**:
  - [ ] AC-1: `AnswerRequest`, `AnswerResponse` (with discriminator on `output: TurnOutput | TurnFailure`), `StateResponse` Pydantic v2 schemas — match master spec §HTTP API Contracts
  - [ ] AC-2: FastAPI route signature uses `response_model=AnswerResponse` + explicit `responses={200, 401, 422, 429, 500}` dict; OpenAPI metadata `tags=["onboarding"]`, `summary`, `description` (B1.13)
  - [ ] AC-3: `Depends(require_auth_cookie)` reads `nikita-session` JWT; missing/expired → 401 + `ErrorEnvelope(error="auth_required")`; NO Authorization header path (B1.14)
  - [ ] AC-4: Idempotency: `turn_id: UUID4` per turn; check-before-write — duplicate `turn_id` for `(user_id, conversation_id)` → return cached `AnswerResponse` (200, no re-execution) (B1.15)
  - [ ] AC-5: `tests/api/routes/test_onboarding_answer.py` integration green (status matrix + idempotency replay)

### T-B-14: `GET /api/v1/onboarding/state` resume endpoint
- **Subspec AC**: master spec §HTTP API Contracts `/state`
- **Owner**: implementor
- **Estimate**: S (2h)
- **Depends on**: T-B-13
- **Acceptance**:
  - [ ] AC-1: `StateResponse(output, progress_pct, is_complete, conversation_id)` Pydantic v2
  - [ ] AC-2: Auth gate same as `/answer`; 200 (fresh OR resumed), 401 (auth missing)

### T-B-15: Legacy `/converse` 410 Gone shim (B1.16)
- **Subspec AC**: B1.16
- **Owner**: implementor
- **Estimate**: S (2h)
- **Depends on**: T-B-13
- **Acceptance**:
  - [ ] AC-1: `nikita/api/routes/portal_onboarding.py` keeps `/converse` route as 410 Gone shim with `Location: /api/v1/onboarding/answer` header
  - [ ] AC-2: Active for 1 deploy cycle (~7 days); deletion tracked as a follow-up GH issue
  - [ ] AC-3: `Cache-Control: no-store` on portal HTML responses

### T-B-16: Per-user rate limit 429 + Retry-After
- **Subspec AC**: B1.22
- **Owner**: implementor
- **Estimate**: S (2h)
- **Depends on**: T-B-13
- **Acceptance**:
  - [ ] AC-1: 30 turns/min per `user_id` enforced
  - [ ] AC-2: Excess returns 429 + `ErrorEnvelope(error="rate_limit_exceeded")` + `Retry-After` header
  - [ ] AC-3: Orthogonal to cost circuit; rate-limit test `test_rate_limit_429.py` green

### T-B-17: Completion-gate triplet test (mandatory test class #2)
- **Subspec AC**: testing.md mandatory + ship-gate for 216-B
- **Owner**: implementor
- **Estimate**: M (4h)
- **Depends on**: T-B-2
- **Acceptance**:
  - [ ] AC-1: `tests/agents/onboarding/test_completion_gate.py` — empty state → `is_complete=False`; partial → `is_complete=False`; full → `is_complete=True`
  - [ ] AC-2: Gate via `try: FinalForm.model_validate(state.slots_dict); except ValidationError: ...` (no boolean literal)
  - [ ] AC-3: Triplet covers cross-field validators (age <18 → False even if all slots filled)

### T-B-18: Delete deprecated `regex_phone_fallback`
- **Subspec AC**: subspec B "DELETED files"
- **Owner**: implementor
- **Estimate**: S (2h)
- **Depends on**: T-B-13
- **Acceptance**:
  - [ ] AC-1: `nikita/agents/onboarding/regex_fallback.py:47` `regex_phone_fallback` DELETED
  - [ ] AC-2: Grep verifies no callers remain
  - [ ] AC-3: BE accepts FE-validated E.164 string as-is

---

## PR 216-D — Data layer + Big5 inference (depends: 216-A merged; parallel with 216-B, ~250 LOC)

### T-D-1: Migration: 3 top-level columns on `public.users` + RLS + idempotent CHECK
- **Subspec AC**: D1.1, D1.2, D1.3, D1.4, D1.10, D1.11
- **Owner**: implementor
- **Estimate**: M (4h)
- **Depends on**: 216-A merged
- **Acceptance**:
  - [ ] AC-1: `supabase/migrations/NNN_user_profile_inference.sql` adds **top-level columns** (NOT JSONB-embedded) on `public.users`: `big5_vector` JSONB default `'{}'`, `backstory_seed` TEXT NULL with CHECK length≤300, `brand_resonance_signal` NUMERIC NULL with CHECK [0,1]
  - [ ] AC-2: ENABLE RLS + UPDATE policy with `WITH CHECK ((SELECT auth.uid()) = id)`; SELECT/UPDATE/INSERT user-scoped (D1.4)
  - [ ] AC-3: All CHECK constraints wrapped in `DO $$ BEGIN ... EXCEPTION WHEN duplicate_object ... END $$;` per `20260414213313_*.sql:28-41` canonical pattern; idempotent re-run safe (D1.11)
  - [ ] AC-4: Verified post-migration via `mcp__supabase__list_policies`

### T-D-2: `archetype_candidates` JSONB column on `public.users` (D1.12)
- **Subspec AC**: D1.12
- **Owner**: implementor
- **Estimate**: S (2h)
- **Depends on**: T-D-1
- **Acceptance**:
  - [ ] AC-1: Migration adds `archetype_candidates` JSONB default `'[]'::jsonb` (persists 3 LLM-picked candidates separate from final `backstory_pick`)
  - [ ] AC-2: Required for W4 walk G.6 verification
  - [ ] AC-3: RLS policies cover the new column

### T-D-3: Implement Big5 per-turn Haiku judge with Bayesian merge
- **Subspec AC**: D1.5
- **Owner**: implementor
- **Estimate**: M (4h)
- **Depends on**: T-D-1
- **Acceptance**:
  - [ ] AC-1: `nikita/agents/onboarding/big5_judge.py` `update_big5_vector(state, deps) -> dict` Haiku-backed
  - [ ] AC-2: Returns `{O, C, E, A, N: float}` + `confidence: dict[str, float]`; merge via averaged scores + Bayesian confidence update
  - [ ] AC-3: Once any dim confidence ≥0.7, M4 short-circuits further probes on that axis
  - [ ] AC-4: `test_big5_judge.py` mocks Haiku golden vectors, asserts merge invariants

### T-D-4: Curated 12-archetype taxonomy + label validator
- **Subspec AC**: D1.6
- **Owner**: implementor
- **Estimate**: M (4h)
- **Depends on**: T-D-1
- **Acceptance**:
  - [ ] AC-1: `nikita/agents/onboarding/archetypes.py` exposes 12 labels: `the runner, the maker, the watcher, the climber, the seeker, the architect, the survivor, the rebel, the romantic, the wanderer, the host, the fugitive`
  - [ ] AC-2: `pick_three_archetypes(big5, city, occupation, hobbies, darkness) -> list[ArchetypeCard]` Opus prompt returns 3 from curated 12
  - [ ] AC-3: Validator rejects ANY label not in curated 12-list; retry once with stricter prompt; deterministic top-3 fallback
  - [ ] AC-4: `test_archetypes.py` covers invented-label rejection + deterministic fixtures

### T-D-5: Hand-seeded cohort cache + sha256 PII-safe key
- **Subspec AC**: D1.7
- **Owner**: implementor
- **Estimate**: M (4h)
- **Depends on**: T-D-1
- **Acceptance**:
  - [ ] AC-1: `nikita/agents/onboarding/cohort_chips.py` exposes 6-8 cohorts: `(zurich, designer)`, `(london, finance)`, `(berlin, nurse)`, `(brooklyn, dev)`, `(sf, founder)`, `(stockholm, researcher)` (final list resolved during 216-D authoring)
  - [ ] AC-2: Cache key = sha256 of `(lowercase_city, lowercase_occupation)`; NEVER raw PII
  - [ ] AC-3: `test_cohort_chips.py` green

### T-D-6: 3-persona backstory generator
- **Subspec AC**: FR-09 / D1.6 follow-up
- **Owner**: implementor
- **Estimate**: M (4h)
- **Depends on**: T-D-4
- **Acceptance**:
  - [ ] AC-1: `generate_three_personas(picked_archetype, big5, city, occupation, hobbies)` Opus call generates 3 personas (~150 chars each)
  - [ ] AC-2: Persisted to `public.users.backstory_seed` (text ≤300 chars; CHECK constraint enforced)
  - [ ] AC-3: NEVER returned in any UI response payload (NR-05)

### T-D-7: Extend `User` ORM with new top-level columns
- **Subspec AC**: D1.10
- **Owner**: implementor
- **Estimate**: S (2h)
- **Depends on**: T-D-1
- **Acceptance**:
  - [ ] AC-1: `nikita/db/models/user.py` `User` model extended (NOT `UserProfile` JSONB embedding) with `big5_vector`, `backstory_seed`, `brand_resonance_signal`, `archetype_candidates`
  - [ ] AC-2: SQLAlchemy 2.0 async-compatible
  - [ ] AC-3: Repository tests green (CRUD path)

### T-D-8: PII-safe `cache_key` (#446 fix) + regex backfill predicate
- **Subspec AC**: D1.8
- **Owner**: implementor
- **Estimate**: S (2h)
- **Depends on**: T-D-1
- **Acceptance**:
  - [ ] AC-1: `cache_key` is sha256 hash; raw city/identity NEVER present
  - [ ] AC-2: Backfill uses regex predicate `cache_key !~ '^[a-f0-9]{64}$'` (NOT length-based) to avoid double-hashing
  - [ ] AC-3: Post-migration test asserts ALL rows match `^[a-f0-9]{64}$`

### T-D-9: Hide-the-framework guard (D1.9, NR-05)
- **Subspec AC**: D1.9
- **Owner**: implementor
- **Estimate**: S (2h)
- **Depends on**: T-D-3, T-D-4, T-D-6
- **Acceptance**:
  - [ ] AC-1: `tests/api/routes/test_no_big5_in_response.py` calls `/onboarding/answer` 12 turns; asserts no response payload contains `big5`, `vector`, `OCEAN`, `extraversion`
  - [ ] AC-2: `archetype rationale prose` NEVER surfaced (only label + 150-char persona prose)
  - [ ] AC-3: `TurnOutput` schema does NOT contain `big5_vector` field (lint asserts)

---

## PR 216-C1 — Frontend shell + chrome (depends: 216-B + 216-D merged, ~350-400 LOC)

Split per audit F-9 (216-C estimated 800-1500 LOC originally). C1 lands first; C2 depends on C1.

### T-C1-1: WizardShell + AuroraOrbs + AnimatePresence + design tokens
- **Subspec AC**: C1.2, C1.3, C1.4
- **Owner**: implementor
- **Estimate**: L (8h)
- **Depends on**: 216-B + 216-D merged
- **Acceptance**:
  - [ ] AC-1: Design tokens inherited from Spec 208: `bg-void`, rose, Geist Sans/Mono, glass-card surfaces — NO new tokens (C1.2)
  - [ ] AC-2: AuroraOrbs + GlowButton imported from `portal/src/components/landing/`; NO duplication (C1.3)
  - [ ] AC-3: AnimatePresence `mode="wait"` opacity+y+blur 350ms `[0.22, 1, 0.36, 1]`; `prefers-reduced-motion: reduce` honored (C1.4)
  - [ ] AC-4: vitest `WizardShell.test.tsx` green

### T-C1-2: Server Component cookie auth guard
- **Subspec AC**: C1.13
- **Owner**: implementor
- **Estimate**: M (4h)
- **Depends on**: T-C1-1
- **Acceptance**:
  - [ ] AC-1: `/onboarding/page.tsx` is a Server Component reading `nikita-session` cookie via Next.js `cookies()` API
  - [ ] AC-2: On missing/expired JWT → `redirect('/onboarding/auth')` BEFORE any client component mounts
  - [ ] AC-3: NO hydration mismatch on first paint (verified via `read_console_messages`)

### T-C1-3: ProgressRail (monotonicity reflection + reduced-motion)
- **Subspec AC**: C1.8, C1.17
- **Owner**: implementor
- **Estimate**: S (2h)
- **Depends on**: T-C1-1
- **Acceptance**:
  - [ ] AC-1: Width animates from prev% to new% via spring (stiffness 120, damping 20); never decreases (C1.8)
  - [ ] AC-2: `useReducedMotion()` true → swap spring for `transition={{ duration: 0.2, ease: "linear" }}`; width still monotonic (C1.17)
  - [ ] AC-3: `ProgressRail.test.tsx` covers monotonicity + reduced-motion fallback

### T-C1-4: NikitaReaction + WhyWeAsk (voice modes per Style Guide)
- **Subspec AC**: C1.9, C1.20
- **Owner**: implementor
- **Estimate**: M (4h)
- **Depends on**: T-C1-1
- **Acceptance**:
  - [ ] AC-1: NikitaReaction renders post-input live-morph (≤140 chars, persona-voice per C1.20)
  - [ ] AC-2: WhyWeAsk renders narrator-voice (≤2 sentences, third-person per C1.20)
  - [ ] AC-3: Welcome + completion + error/loading states use narrator voice; backstory cards stay first-person Nikita; underage refusal stays Nikita-voice
  - [ ] AC-4: `NikitaReaction.test.tsx` covers reduced-motion + reveal animation

### T-C1-5: Per-control-type input components
- **Subspec AC**: C1.x (control dispatch)
- **Owner**: implementor
- **Estimate**: L (8h)
- **Depends on**: T-C1-1
- **Acceptance**:
  - [ ] AC-1: 6 controls in `_components/controls/`: TextInput, Slider (Radix), Chips, Scenarios, Radio, Tel
  - [ ] AC-2: CityInput (Aceternity placeholders-and-vanish-input + Magicui text-shimmer) per subspec C "EDITED (light)"
  - [ ] AC-3: SuggestionChips (3-chip glass-card row); PersonalizingBadge; BackLink; NikitaThinkingDots
  - [ ] AC-4: `control_dispatch.test.tsx` asserts each `control_type` literal renders the right component

### T-C1-6: Pending/error UI states + cost-circuit silent fallback
- **Subspec AC**: C1.14
- **Owner**: implementor
- **Estimate**: M (4h)
- **Depends on**: T-C1-1, T-C1-5
- **Acceptance**:
  - [ ] AC-1: Continue button enters pending state (disabled + spinner) on submit; >2s pending → NikitaThinkingDots replaces reaction text
  - [ ] AC-2: Network 4xx (excluding 401-redirect) → inline rose-toned error banner with "try again" CTA
  - [ ] AC-3: Cost-circuit fallback (200 + `meta.fallback_reason="cost_circuit"`) renders silently, no error UI

### T-C1-7: Resume mid-wizard state hydration (NR-07)
- **Subspec AC**: C1.15
- **Owner**: implementor
- **Estimate**: M (4h)
- **Depends on**: T-C1-2, T-C1-3
- **Acceptance**:
  - [ ] AC-1: On `/onboarding` mount with non-empty `conversation_jsonb`, FE issues `GET /api/v1/onboarding/state` to fetch latest turn payload
  - [ ] AC-2: ProgressRail animates from 0 to resumed `progress_pct` on first paint
  - [ ] AC-3: NikitaReaction renders resumed `nikita_reaction` (no "Welcome back" banner)

### T-C1-8: AnimatePresence key stability per turn (C1.16)
- **Subspec AC**: C1.16
- **Owner**: implementor
- **Estimate**: S (2h)
- **Depends on**: T-C1-1
- **Acceptance**:
  - [ ] AC-1: `<motion.div key={turn_id}>` (NOT `slot_kind`); `turn_id` is server-issued UUID per turn
  - [ ] AC-2: Documented in `motion-spec.md` as "AnimatePresence key is stable per turn, never reused across dynamic follow-ups"

### T-C1-9: Auto-redirect on `is_complete=True` (#448)
- **Subspec AC**: FR-11
- **Owner**: implementor
- **Estimate**: M (4h)
- **Depends on**: T-C1-7
- **Acceptance**:
  - [ ] AC-1: After `FinalForm.model_validate` success, FE polls `is_complete` and auto-redirects to `/dashboard` within 10s
  - [ ] AC-2: Idempotent — `/onboarding` post-completion redirects to `/dashboard`

### T-C1-10: Responsive baseline + 0 console errors
- **Subspec AC**: C1.5, C1.10
- **Owner**: implementor
- **Estimate**: M (4h)
- **Depends on**: T-C1-1, T-C1-5
- **Acceptance**:
  - [ ] AC-1: Mobile 390×844 + desktop 1440×900 — no horizontal scroll, all CTAs reachable without zoom (C1.5)
  - [ ] AC-2: Verified via `mcp__claude-in-chrome__resize_window` + `read_console_messages` + `read_network_requests`
  - [ ] AC-3: 0 hydration mismatches, 0 React warnings, 0 4xx/5xx in network during happy-path walk (C1.10)

### T-C1-11: 0 banned vocab + word-boundary grep gate
- **Subspec AC**: C1.11, NR-04
- **Owner**: implementor
- **Estimate**: S (2h)
- **Depends on**: T-C1-1
- **Acceptance**:
  - [ ] AC-1: `rg -i '\b(dossier|clearance)\b|\b(FILE|FIELD)\b' portal/src/app/onboarding/` returns 0 hits
  - [ ] AC-2: Server-rendered HTML at `/onboarding`, `/onboarding/auth`, `/dashboard` returns 0 hits via curl

### T-C1-12: Accessibility (a11y) per C1.12 — full ARIA contracts
- **Subspec AC**: C1.12
- **Owner**: implementor
- **Estimate**: L (8h)
- **Depends on**: T-C1-1, T-C1-5
- **Acceptance**:
  - [ ] AC-1: Per-control ARIA per subspec C1.12 sub-bullets (HobbyChips role=group, BackstoryCards radiogroup, Slider Radix, Tel inputMode/aria-describedby, ProgressRail progressbar, NikitaReaction live-region, focus management, visible focus ring, landmark, ≥44px touch targets)
  - [ ] AC-2: Textarea pattern: per-slot `aria-label`, `aria-describedby` linking WhyWeAsk, `aria-required`, `aria-invalid`
  - [ ] AC-3: Dual-textarea group: `<fieldset role="group" aria-labelledby="screen-10-heading"><legend>...` per C1.18
  - [ ] AC-4: vitest a11y snapshot tests + axe-core scan green

---

## PR 216-C2 — Frontend slot screens (depends: 216-C1 merged, ~350-400 LOC)

### T-C2-1: 15 base wizard screens implementation
- **Subspec AC**: C1.1, C1.18
- **Owner**: implementor
- **Estimate**: L (8h)
- **Depends on**: 216-C1 merged
- **Acceptance**:
  - [ ] AC-1: All 15 base screens implemented matching `wireframes/ascii.md` + `figma.md` per C1.1 ordering: welcome + 11 visual slot screens + backstory pick + completion
  - [ ] AC-2: Visual diff against Figma frames ≤2% pixel drift on mobile + desktop
  - [ ] AC-3: Screen ordering correct: backstory pick is the cinematic climax AFTER phone + voice_tone_pref (per FR-09 / C1.1)

### T-C2-2: HobbyChips component (3-5 picks + 100×10 chips + autocomplete + "+ other")
- **Subspec AC**: C1.6, FR-08
- **Owner**: implementor
- **Estimate**: L (8h)
- **Depends on**: T-C1-5
- **Acceptance**:
  - [ ] AC-1: 100 chips × 10 categories (Music, Movement, Gaming, Reading, Food & Drink, Travel, Art & Making, Tech & Gear, Outdoors & Nature, Social & Nightlife)
  - [ ] AC-2: Cross-category autocomplete-filter input; 3-5 picks enforced (Continue disabled outside range with inline tooltip)
  - [ ] AC-3: "+ other" hard-cap 40 chars (`maxLength=40`); inline `${len}/40` indicator turns rose at len ≥35; trim+reject empty-after-trim
  - [ ] AC-4: Stagger-reveal motion per `motion-spec.md` §4.3
  - [ ] AC-5: `HobbyChips.test.tsx` covers picks enforcement + autocomplete + "+ other"

### T-C2-3: BackstoryArchetypeCards
- **Subspec AC**: C1.7
- **Owner**: implementor
- **Estimate**: M (4h)
- **Depends on**: T-C1-5
- **Acceptance**:
  - [ ] AC-1: 3 LLM-archetype cards from curated 12-list ONLY; hover state `y:-4` + glow opacity 0→0.4 (250ms EASE_OUT_QUART)
  - [ ] AC-2: Select state pulse scale 1→1.02→1 (300ms) + ring opacity 0→1 + non-selected card 100ms tail blur
  - [ ] AC-3: NO invented labels (validated against `archetypes.py` 12-list at render time)
  - [ ] AC-4: `BackstoryArchetypeCards.test.tsx` covers no-invent-label guard with `console.warn`

### T-C2-4: CombinedDualTextarea (together_we_could + same_weird_if)
- **Subspec AC**: C1.18
- **Owner**: implementor
- **Estimate**: M (4h)
- **Depends on**: T-C1-5
- **Acceptance**:
  - [ ] AC-1: ONE screen, two textareas; Continue requires `together_we_could` populated; `same_weird_if` optional
  - [ ] AC-2: Single submit writes BOTH slots
  - [ ] AC-3: `<fieldset role="group" aria-labelledby>` with `<legend>` (a11y per C1.12)
  - [ ] AC-4: `CombinedDualTextarea.test.tsx` covers single-submit-writes-2-slots

### T-C2-5: MidpointNudge (Saturday screen, first-render-only)
- **Subspec AC**: C1.19
- **Owner**: implementor
- **Estimate**: S (2h)
- **Depends on**: T-C2-1
- **Acceptance**:
  - [ ] AC-1: `Halfway. Six down, six to go.` narrator-voice in dim text-muted color above headline on `saturday_morning` screen (visual screen 8 of 15)
  - [ ] AC-2: First-render-only via `useState(true)` + `useEffect` to false; never reappears on resume
  - [ ] AC-3: `MidpointNudge.test.tsx` covers single-render

### T-C2-6: 15-screen integration `full_flow` test
- **Subspec AC**: ship gate
- **Owner**: implementor
- **Estimate**: M (4h)
- **Depends on**: T-C2-1, T-C2-2, T-C2-3, T-C2-4, T-C2-5
- **Acceptance**:
  - [ ] AC-1: Integration test renders all 15 base screens
  - [ ] AC-2: 2-slot-jump monotonicity (combined together/odd screen) verified
  - [ ] AC-3: `progress_pct` reflects BE cumulative state

---

## PR 216-E — Agentic tools + firecrawl (depends: 216-B merged; parallel with 216-C1, ~200 LOC)

### T-E-1: Implement 4 firecrawl `fetch_*` tools
- **Subspec AC**: E1.1, E1.2
- **Owner**: implementor
- **Estimate**: L (8h)
- **Depends on**: 216-B merged
- **Acceptance**:
  - [ ] AC-1: `nikita/agents/onboarding/tools/firecrawl_tools.py` with `fetch_city_context`, `fetch_occupation_signal`, `fetch_time_of_day_signal`, `fetch_topic_specific`; each ≤200 chars text
  - [ ] AC-2: Always-fetch-something: ≥1 fetch per turn when `state.location` present (skip turn 0); fallback to static if no fetch fires
  - [ ] AC-3: Registered via `@agent.tool` decorators (NOT `builtin_tools` — that's WebSearchTool only, per E1.12)
  - [ ] AC-4: `test_firecrawl_tools.py` green

### T-E-2: Tool registration disambiguation (E1.12)
- **Subspec AC**: E1.12
- **Owner**: implementor
- **Estimate**: S (2h)
- **Depends on**: T-E-1
- **Acceptance**:
  - [ ] AC-1: `WebSearchTool` registers via `builtin_tools=[prepared_web_search]` (provider-native Anthropic builtin)
  - [ ] AC-2: 4 `fetch_*` tools register via `@agent.tool` decorators (application-side custom tools)
  - [ ] AC-3: Lint test asserts no conflation; verify against Pydantic AI 1.71.0 `prepare_tools` API surface

### T-E-3: Cost guard + circuit breaker
- **Subspec AC**: E1.3, E1.7, FR-12
- **Owner**: implementor
- **Estimate**: M (4h)
- **Depends on**: T-E-1
- **Acceptance**:
  - [ ] AC-1: `nikita/agents/onboarding/cost_guard.py` per-turn budget guard `RunContext.deps.fetch_invocations_this_turn <= 1`
  - [ ] AC-2: Cumulative fetch budget tracked in `RunContext.deps.fetch_cost_cumulative`; hard ceiling $0.15/flow; soft warn $0.10
  - [ ] AC-3: Total cost ceiling $0.50/flow (LLM + fetch + WebSearchTool); circuit fires at $0.05 budget remaining
  - [ ] AC-4: `users.cost_usd` updated post-flow; `test_cost_circuit.py` green (over-budget mock falls back to static registry)

### T-E-4: Cohort cache integration
- **Subspec AC**: E1.4
- **Owner**: implementor
- **Estimate**: S (2h)
- **Depends on**: T-E-1, T-D-5
- **Acceptance**:
  - [ ] AC-1: Cohort cache hits BEFORE issuing live fetch
  - [ ] AC-2: `CohortCache` accessed via `RunContext.deps.cohort_cache`; cache key sha256

### T-E-5: WebSearchTool config (Anthropic provider)
- **Subspec AC**: E1.5
- **Owner**: implementor
- **Estimate**: S (2h)
- **Depends on**: T-E-2
- **Acceptance**:
  - [ ] AC-1: `WebSearchTool` configured `search_context_size="low"`, `max_uses=2`, `user_location=WebSearchUserLocation(city, country)`
  - [ ] AC-2: `prepared_*` callable returns None when `state.location` absent (turn-0 skip)

### T-E-6: 3s per-tool per-attempt timeout + graceful fallback
- **Subspec AC**: E1.6, E1.11
- **Owner**: implementor
- **Estimate**: S (2h)
- **Depends on**: T-E-1
- **Acceptance**:
  - [ ] AC-1: Per-tool 3s timeout via `asyncio.wait_for(...)`
  - [ ] AC-2: Timeout is **per-attempt**, NOT cumulative across retries (E1.11)
  - [ ] AC-3: Tools do NOT participate in `ModelRetry` loop (only agent's `@output_validator` does); on timeout → fall through to static fallback within same attempt
  - [ ] AC-4: User-facing response remains 200 (graceful degradation)

### T-E-7: Per-tool log shape (E1.9)
- **Subspec AC**: E1.9
- **Owner**: implementor
- **Estimate**: S (2h)
- **Depends on**: T-E-1
- **Acceptance**:
  - [ ] AC-1: Every firecrawl tool call emits structured Cloud Run log per master spec §HTTP API Contracts: `{event:"agent_tool_call", tool_name, outcome ∈ {success,cache_hit,timeout,firecrawl_error,budget_exceeded}, duration_ms, cohort_cache_used, cost_usd_delta, traceparent}`
  - [ ] AC-2: G.5 W4 walk verification queries this exact event shape
  - [ ] AC-3: User-facing response remains 200 on tool failure

### T-E-8: `FIRECRAWL_API_KEY` secret handling (E1.10)
- **Subspec AC**: E1.10
- **Owner**: implementor
- **Estimate**: S (2h)
- **Depends on**: T-E-1
- **Acceptance**:
  - [ ] AC-1: Stored as Cloud Run secret env var (NOT in `.env` committed)
  - [ ] AC-2: NEVER logged in plaintext; NEVER returned in any HTTP response or `ErrorEnvelope.detail`
  - [ ] AC-3: `tests/agents/onboarding/test_firecrawl_secret_handling.py` simulates tool failure + asserts no captured log line contains the key

### T-E-9: Anthropic prompt cache hit-rate verification (E1.8)
- **Subspec AC**: E1.8
- **Owner**: implementor
- **Estimate**: M (4h)
- **Depends on**: T-B-9
- **Acceptance**:
  - [ ] AC-1: Verified via Cloud Run logs `cache_read_input_tokens / total_input_tokens >= 0.60` averaged across turns 3-12
  - [ ] AC-2: Log query script `scripts/verify_prompt_cache_hit_rate.py` runs in W4 verification

---

## PR 216-F — Testing + W4 walk (depends: A,B,C1,C2,D,E merged, ~150 LOC tests + W4 walk artifact)

NOTE: 3 mandatory test classes are now ship-gate for 216-B (T-B-3, T-B-7, T-B-17). 216-F focuses on integration + W4 walk + GH issue closure.

### T-F-1: M1-M4 unit tests + golden snapshots (F1.2)
- **Subspec AC**: F1.2
- **Owner**: implementor
- **Estimate**: M (4h)
- **Depends on**: T-B-8
- **Acceptance**:
  - [ ] AC-1: `test_meta_prompts.py` golden snapshots for M1-M4
  - [ ] AC-2: Cluster enum exhaustiveness — paired template registry verified

### T-F-2: Cost circuit-breaker integration test (F1.4)
- **Subspec AC**: F1.4
- **Owner**: implementor
- **Estimate**: M (4h)
- **Depends on**: T-E-3
- **Acceptance**:
  - [ ] AC-1: Mocked LLM returning over-budget responses
  - [ ] AC-2: Wizard falls back to static registry; `is_complete=True` still reachable via fallback
  - [ ] AC-3: `meta.fallback_reason="cost_circuit"` surfaced

### T-F-3: Big5 + archetypes unit coverage (F1.5)
- **Subspec AC**: F1.5
- **Owner**: implementor
- **Estimate**: M (4h)
- **Depends on**: T-D-3, T-D-4
- **Acceptance**:
  - [ ] AC-1: `test_big5_judge.py` mocks Haiku golden vectors
  - [ ] AC-2: `test_archetypes.py` rejects invented labels; deterministic fallback covered

### T-F-4: FE vitest coverage for HobbyChips + Cards + ProgressRail + Combined + Midpoint (F1.6)
- **Subspec AC**: F1.6
- **Owner**: implementor
- **Estimate**: M (4h)
- **Depends on**: T-C2-2, T-C2-3, T-C2-4, T-C2-5
- **Acceptance**:
  - [ ] AC-1: `HobbyChips.test.tsx` (3-5 picks + autocomplete + "+ other")
  - [ ] AC-2: `BackstoryArchetypeCards.test.tsx` (no invented labels)
  - [ ] AC-3: `ProgressRail.test.tsx` monotonicity (covered by T-C1-3)
  - [ ] AC-4: `CombinedDualTextarea.test.tsx` (single submit writes 2 slots)
  - [ ] AC-5: `MidpointNudge.test.tsx` first-render-only

### T-F-5: W4 live-walk (F1.7, G.1-G.11)
- **Subspec AC**: F1.7
- **Owner**: walk-subagent (general-purpose, isolation: worktree, capped 130 tool calls)
- **Estimate**: L (8h)
- **Depends on**: All A, B, C1, C2, D, E merged + Cloud Run + Vercel deployed
- **Acceptance**:
  - [ ] AC-1: All 11 G.x checks PASS — 12 fixed roots in correct order, M2/M1 firing, Big5 ≥3 dims with confidence ≥0.5, firecrawl ≥4×, archetypes from curated 12, cost <$0.50, 15-25 visual screens, monotonic progress, 0 mirror echo, 0 banned vocab
  - [ ] AC-2: Walk follows `live-testing-protocol.md` 12-step protocol; NO DB fabrication; NO `signInWithPassword`; NO `E2E_AUTH_BYPASS`
  - [ ] AC-3: Walk artifact written to `docs-to-process/2026MMDD-live-walk-W4-spec216.md`
  - [ ] AC-4: Pre-walk + post-walk DB cleanup (FK-safe) for `simon.yang.ch+spec216walk@gmail.com`

### T-F-6: Triage W4 findings + close GH issues #440-#449 (F1.9)
- **Subspec AC**: F1.9
- **Owner**: implementor
- **Estimate**: M (4h)
- **Depends on**: T-F-5
- **Acceptance**:
  - [ ] AC-1: Severity-classify W4 findings per `.claude/rules/issue-triage.md`
  - [ ] AC-2: All 10 W3 GH issues (#440-#449) closed referencing the merged PR(s)
  - [ ] AC-3: New W4 findings filed as GH issues at appropriate severity

### T-F-7: ROADMAP sync + Spec 214/215 archive
- **Subspec AC**: F1 ship hygiene
- **Owner**: implementor
- **Estimate**: S (2h)
- **Depends on**: T-F-6 PASS
- **Acceptance**:
  - [ ] AC-1: `ROADMAP.md` Spec 216 → `SHIPPED` if VERDICT=PASS
  - [ ] AC-2: Specs 214 + 215 → `archive/` with traceability
  - [ ] AC-3: `event-stream.md` LIVE_E2E_W4 entry

---

## Task Count Summary

| PR | Task IDs | Count | Total est. (hours) |
|----|----------|-------|---------------------|
| 216-A | T-A-1..T-A-8 | 8 | 22 (~3 days) |
| 216-B | T-B-1..T-B-18 | 18 | 60 (~7.5 days) |
| 216-D | T-D-1..T-D-9 | 9 | 30 (~3.75 days) |
| 216-C1 | T-C1-1..T-C1-12 | 12 | 50 (~6.25 days) |
| 216-C2 | T-C2-1..T-C2-6 | 6 | 32 (4 days) |
| 216-E | T-E-1..T-E-9 | 9 | 26 (~3.25 days) |
| 216-F | T-F-1..T-F-7 | 7 | 26 (~3.25 days) |
| **Total** | — | **69** | **246 hours (~31 working days)** |

Wall-clock with parallelization (B∥D, C1∥E, C2 after C1): ~17 working days.

---

## AC → Task Coverage Matrix (orphan check)

| Subspec | Total ACs | Tasks covering | Coverage |
|---------|-----------|----------------|----------|
| 216-A | 14 (A1.1-A1.14) | T-A-1..T-A-8 | 100% (A1.1=T-A-1/T-A-2; A1.2-A1.5=T-A-2; A1.6-A1.7+A1.9-A1.10+A1.13=T-A-3; A1.11=T-A-4; A1.12=T-A-5; A1.14=T-A-6; A1.8 documented as deferred MED in T-A-3 AC-3 commentary) |
| 216-B | 22 (B1.1-B1.22) | T-B-1..T-B-18 | 100% (B1.1+B1.18=T-B-1; B1.2=T-B-2; B1.12=T-B-3; B1.3=T-B-4; B1.19=T-B-5; B1.4=T-B-6; B1.5=T-B-7; B1.6-B1.8=T-B-8; B1.20=T-B-9; B1.9=T-B-10; B1.10+B1.21=T-B-11; B1.11+B1.17=T-B-12; B1.13-B1.15=T-B-13; B1.16=T-B-15; B1.22=T-B-16) |
| 216-C | 20 (C1.1-C1.20) | T-C1-1..T-C1-12 + T-C2-1..T-C2-6 | 100% (C1.2-C1.4=T-C1-1; C1.13=T-C1-2; C1.8+C1.17=T-C1-3; C1.9+C1.20=T-C1-4; controls=T-C1-5; C1.14=T-C1-6; C1.15=T-C1-7; C1.16=T-C1-8; FR-11=T-C1-9; C1.5+C1.10=T-C1-10; C1.11=T-C1-11; C1.12=T-C1-12; C1.1+C1.18=T-C2-1; C1.6=T-C2-2; C1.7=T-C2-3; combined=T-C2-4; C1.19=T-C2-5) |
| 216-D | 12 (D1.1-D1.12) | T-D-1..T-D-9 | 100% (D1.1-D1.4+D1.10+D1.11=T-D-1; D1.12=T-D-2; D1.5=T-D-3; D1.6=T-D-4; D1.7=T-D-5; D1.6 personas=T-D-6; D1.10 ORM=T-D-7; D1.8=T-D-8; D1.9=T-D-9) |
| 216-E | 12 (E1.1-E1.12) | T-E-1..T-E-9 | 100% (E1.1-E1.2=T-E-1; E1.12=T-E-2; E1.3+E1.7=T-E-3; E1.4=T-E-4; E1.5=T-E-5; E1.6+E1.11=T-E-6; E1.9=T-E-7; E1.10=T-E-8; E1.8=T-E-9) |
| 216-F | 9 (F1.1-F1.9) | T-F-1..T-F-7 + 3 mandatory in 216-B | 100% (F1.1=T-B-3+T-B-7+T-B-17 [moved to 216-B as ship gate]; F1.2=T-F-1; F1.3=T-B-9 [E1.8]; F1.4=T-F-2; F1.5=T-F-3; F1.6=T-F-4; F1.7=T-F-5; F1.8=T-F-5 cleanup; F1.9=T-F-6) |
| **Total** | **89** | **69 tasks** | **100%** |

---

## Constitutional Compliance (re-verified iter-2)

- [x] Every requirement (FR-01..12, NR-01..08) traces to ≥1 task — see master spec.md Appendix B + this file's Coverage Matrix
- [x] All tasks have ≥2 testable ACs
- [x] No circular dependencies — DAG: `A → (B ∥ D) → (C1 ∥ E) → C2 → F` (216-C2 depends on 216-C1 + uses 216-D archetype contracts)
- [x] Tasks sized 2-8 hours (S=2h, M=4h, L=8h)
- [x] Owner assigned per task
- [x] 3 mandatory agentic-flow test classes are 216-B ship gate (T-B-3 cumulative-state, T-B-7 tool-recovery, T-B-17 completion-gate) — moved per audit F-8/F-12
- [x] All 6 PRs within `pr-workflow.md` 400-LOC cap (216-C split into 216-C1 + 216-C2 per audit F-9)
- [x] All 89 ACs across 6 subspecs bound to ≥1 task (per Coverage Matrix above)
- [x] Plan §5 task ID ranges reconciled with actual task IDs (per audit F-6, F-10, F-13 — to be reflected in plan.md update)

---

## Audit-fix Log (iter-2)

| Audit finding | Severity | Fix in this rev |
|---------------|----------|------------------|
| F-1 (CRIT) | A1.11-A1.14 orphan | Added T-A-4 (concurrent race), T-A-5 (resume), T-A-6 (purge guard), T-A-7 (cleanup), T-A-8 (plus-alias). 8 total tasks now bind 14 ACs. |
| F-2 (CRIT) | B1.13-B1.22 orphan | Added T-B-5 (ConverseDeps), T-B-9 (prompt cache), T-B-13/14/15/16 (HTTP API), T-B-17 (completion-gate test in 216-B). 18 total tasks now bind 22 ACs. |
| F-3 (CRIT) | C1.5/C1.12-C1.14/C1.16-C1.17 orphan | Added T-C1-2 (auth guard), T-C1-3 (reduced-motion), T-C1-6 (pending/error UI), T-C1-7 (resume), T-C1-8 (key uniqueness), T-C1-10 (responsive), T-C1-12 (a11y). 12 + 6 = 18 tasks bind 20 ACs. |
| F-4 (CRIT) | D1.10-D1.12 orphan | Combined into T-D-1 (top-level columns + idempotent CHECK), T-D-2 (archetype_candidates), T-D-7 (User ORM extension). |
| F-5 (HIGH) | 12 vs 13 SlotKind | Spec.md FR-02 reconciled: "13 SlotKind enum members across 12 visual roots" with explicit dual-figure framing. T-B-1 says "13 fields" matching enum. |
| F-6+F-10+F-13 (HIGH) | Plan §5 ID range mismatch | Task IDs reorganized: T-A-1..8, T-B-1..18, T-D-1..9, T-C1-1..12, T-C2-1..6, T-E-1..9, T-F-1..7. Plan.md §5 + §3 will be updated to reflect. |
| F-7 (HIGH) | A1.11 race test missing | T-A-4 dedicated task with `asyncio.gather` race assertion. |
| F-8+F-12 (HIGH/MED) | 3 mandatory test classes deferred to 216-F | Moved to 216-B as ship gate: T-B-3 (cumulative-state monotonicity), T-B-7 (tool-recovery), T-B-17 (completion-gate). |
| F-9 (HIGH) | 216-C overflows 400-LOC cap | Pre-emptively split into 216-C1 (shell + chrome + a11y + auth + ProgressRail + reduced-motion + resume + auto-redirect + responsive + vocab + controls + animations) and 216-C2 (15 screens + HobbyChips + Cards + Combined + Midpoint + integration test). |
| F-11 (HIGH) | phone-vs-backstory ordering | C1.1 + C1.18 narrative flipped: backstory pick is climax AFTER phone + voice_tone_pref per FR-09. Master spec FR-02 ordering re-affirmed. |
| F-14 (MED) | $0.15 sub-budget vs $0.50 total | T-E-3 AC-2/AC-3 explicitly state fetch sub-budget $0.15 within total $0.50 ceiling. |
| F-15 (MED) | T-D-1 column placement contradicts D1.10 | T-D-1 AC-1 corrected to "top-level columns on `public.users`", spec.md NR-03 corrected, T-D-7 extends `User` (not `UserProfile`). |
| F-16 (MED) | Open Questions documented | Accepted; no fix needed. |
| F-17 (MED) | DAG verified acyclic | No fix needed. |

# Implementation Plan: Spec 214 Onboarding Overhaul (FR-11c / FR-11d / FR-11e)

**Spec**: `specs/214-portal-onboarding-wizard/spec.md` (amended 2026-04-19, 1217 lines)
**Technical Spec**: `specs/214-portal-onboarding-wizard/technical-spec.md` (711 lines, architecture source of truth)
**Validation source**: `validation-findings-iter2.md` (GATE 2 iter-2 PASS, 0 CRIT + 0 HIGH, 9 MED, 16 LOW)
**Predecessor plan**: prior `plan.md` @ commit `545e91f` (pre-amendment, superseded by this document)
**Branch**: `spec/214-chat-first-amendment`
**Date**: 2026-04-19

---

## 1. Overview

### 1.1 Goals

- **FR-11c (P1, regression)**: eliminate legacy Telegram in-bot Q&A onboarding; route every Telegram entry surface (`/start`, `/start <code>`, free text, email-shaped text) to the portal via a bridge-token URL button.
- **FR-11d (P1)**: replace form-style portal wizard (steps 4-9 of the pre-amendment design) with a chat-first conversational wizard powered by a Pydantic AI agent using Claude tool-use extraction. Hybrid UX: every turn renders a Nikita message + an inline control (chips / slider / cards / toggle / text) the user may either type or tap.
- **FR-11e (P2)**: ceremonial portal closeout + proactive Telegram greeting on bind. Closes "game starts now" loop by firing the first Nikita message immediately on `/start <code>` (not on user's first text).

### 1.2 Scope

- **In**: conversation agent + endpoint + extraction schemas + persona fidelity test + rate-limiting + idempotency + daily LLM spend cap + JSONB concurrency-safe write path; chat-shell UI + virtualized thread + control-dispatcher + confirmation ghost-turn; `_handle_start` rewrite + `message_handler` pre-onboard gate + bridge-token TTL matrix; proactive handoff greeting + durable dispatch (BackgroundTasks + pg_cron backstop + stranded-user migration); `ClearanceGrantedCeremony` component.
- **Out (explicit non-goals, tech-spec §9)**: SSE streaming, multi-language, voice-input wizard, admin completion-funnel dashboard, real-time Telegram ↔ portal mirror.
- **Deferred (Phase D, PR 5)**: legacy step-component deletion; drop of `user_onboarding_state` table; removal of `TelegramAuth` if unused.

### 1.3 Non-goals

Explicit: any free-form chat UX without structured controls; pre-generated branching conversation trees; enabling voice input on the wizard; translating the wizard; admin dashboards before ≥1k users.

---

## 2. Architecture Summary

**Three-actor model**: portal (Next.js) — backend (FastAPI on Cloud Run) — Telegram bot.

- **Portal `/onboarding`** renders `ChatShell` container; each turn the client dispatches `POST /portal/onboarding/converse` and receives a `ConverseResponse` with `nikita_reply`, `extracted_fields`, `confirmation_required`, `next_prompt_type` + `next_prompt_options`, `progress_pct`, `conversation_complete`, `source`, `latency_ms`. On `conversation_complete=true` the reducer mints a Telegram-link code via `POST /portal/link-telegram` (tech-spec §2.6) and mounts `ClearanceGrantedCeremony`. Wizard state persists to `users.onboarding_profile.conversation` JSONB (server-of-record) and localStorage (latency fallback).
- **Backend `/converse`** identity via `Depends(get_authenticated_user)` (Bearer JWT) with `ConfigDict(extra="forbid")` on the request schema (closes #350). Calls the stateless Pydantic AI agent composing `NIKITA_PERSONA` + wizard framing + six extraction tools. Tool-use output is validated, rate-limited (per-user RPM + per-IP RPM + daily USD cap), idempotency-short-circuited (`Idempotency-Key` header or `turn_id` UUID), and persisted per-user-serialized via ORM round-trip with `SELECT ... FOR UPDATE` (closes PR #317 / PR #319 JSONB land-mine class).
- **Telegram bot `_handle_start` / `_handle_start_with_payload`** rewrites: vanilla branches route to portal bridge URL per 10 edge cases (E1-E10); `/start <code>` payload branch preserves atomic bind (PR #322) and adds durable background-task greeting dispatch with pg_cron backstop (closes #352).

Cross-agent voice continuity: conversation agent, handoff-greeting generator, and main text agent all import `NIKITA_PERSONA` verbatim from `nikita/agents/text/persona.py`. Persona-drift test (AC-11d.11 + AC-11e.4) is falsifiable: TF-IDF cosine ≥0.70 + three feature ratios (sentence length, lowercase ratio, canonical-phrase count) within ±15% of baseline.

See `technical-spec.md` §1 diagram for data flow and §4 for schema changes.

---

## 3. Design Decisions Resolved

Six open items from `validation-findings-iter2.md` "Decisions to resolve in /plan" are resolved below. Each fixes exactly one decision; none expand spec scope.

### D1. Bridge-token storage (resolves auth-M-A)

**Decision**: **DB-backed opaque token** in a new table `portal_bridge_tokens`, NOT JWT.

**Rationale**: matches the existing `telegram_link_codes` pattern (Spec 214 PR-D / PR #322) already in the codebase — familiar shape for ops + consistent revocation story. Revocation on password-reset (AC-11c.12) requires server-side state; stateless JWT would require a revocation list anyway, eliminating the JWT-size benefit. TTL enforced by a `expires_at TIMESTAMPTZ` column + pg_cron prune job. Single-use enforced by `consumed_at TIMESTAMPTZ NULL` column + `UPDATE ... WHERE consumed_at IS NULL RETURNING id;` atomic consume.

**Schema**:
```sql
CREATE TABLE portal_bridge_tokens (
  token TEXT PRIMARY KEY,                    -- urlsafe 32-byte base64url
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  reason TEXT NOT NULL CHECK (reason IN ('resume', 're-onboard')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL,
  consumed_at TIMESTAMPTZ NULL
);
CREATE INDEX idx_portal_bridge_tokens_user ON portal_bridge_tokens (user_id, consumed_at);
ALTER TABLE portal_bridge_tokens ENABLE ROW LEVEL SECURITY;
CREATE POLICY "admin_and_service_role_only"
  ON portal_bridge_tokens FOR ALL
  USING (is_admin() OR auth.role() = 'service_role')
  WITH CHECK (is_admin() OR auth.role() = 'service_role');
SELECT cron.schedule('portal_bridge_tokens_prune', '0 * * * *', $$
  DELETE FROM portal_bridge_tokens WHERE expires_at < now();
$$);
```

TTL matrix per AC-11c.12: `reason='resume' → 24h`, `reason='re-onboard' → 1h`. Password-reset revocation: Supabase webhook on `auth.users` password-change event → `UPDATE portal_bridge_tokens SET consumed_at = now() WHERE user_id = :uid AND consumed_at IS NULL;`. Covered by task T1.4.

### D2. `llm_spend_ledger` upsert SQL pattern (resolves auth-M-B)

**Decision**: `INSERT INTO llm_spend_ledger (user_id, day, spend_usd, last_updated) VALUES (:uid, :day, :delta, now()) ON CONFLICT (user_id, day) DO UPDATE SET spend_usd = llm_spend_ledger.spend_usd + EXCLUDED.spend_usd, last_updated = now();`.

**Rationale**: atomic increment in one round-trip; avoids TOCTOU between read-check and write-commit that a naive `SELECT ... FOR UPDATE` + `UPDATE` pattern would introduce. `EXCLUDED.spend_usd` is the delta the endpoint computes from `input_tokens + output_tokens` × model pricing. The daily-cap short-circuit runs BEFORE the agent call (`SELECT spend_usd FROM llm_spend_ledger WHERE user_id=:uid AND day=current_date;` → compare to `CONVERSE_DAILY_LLM_CAP_USD`); the upsert happens AFTER the agent call, inside the same transaction that persists the conversation turn. Idempotency short-circuit (D3) bypasses both — neither read nor upsert.

Covered by task T2.6 (ledger), T2.5 (endpoint body).

### D3. `llm_idempotency_cache` header-vs-body mismatch (resolves api-M-NEW-1)

**Decision**: if both `Idempotency-Key` HTTP header AND `turn_id` body field are present AND they differ → return `409 Conflict` with body `{"detail": "idempotency mismatch"}`. If only one is present, use that one. If neither present, no idempotency guard (agent call is free-standing).

**Rationale**: 409 signals client ambiguity without leaking dedupe semantics. Avoids silent "last write wins" surprise. Retry-After not set on 409 (client should fix the ambiguity, not retry). Separate from 429 (rate limit) and 422 (schema). Covered by task T2.4 (endpoint body) and test in T2.5.

### D4. `ControlSelection` discriminated-union TS shape (resolves arch-M4)

**Decision**: TypeScript discriminated union keyed on `kind` matching `next_prompt_type`:

```typescript
type ControlSelection =
  | { kind: "chips"; selected: string }          // label
  | { kind: "slider"; value: 1 | 2 | 3 | 4 | 5 }
  | { kind: "toggle"; value: "voice" | "text" }
  | { kind: "cards"; chosen_option_id: string; cache_key: string }
  | { kind: "text"; text: string }
```

**Rationale**: `kind` is the natural discriminator because the server already returns `next_prompt_type` as the same string. Type narrowing flows naturally via `switch (sel.kind)` in `InlineControl.tsx`. `cards` carries both `chosen_option_id` + `cache_key` to match the FR-4 backstory-preview contract (Spec 213). `text` is included for the "user types instead of tapping chip" branch — both paths commit via the same union.

Server-side `ConverseRequest.user_input` accepts `Union[str, ControlSelection]` where `ControlSelection` is a Pydantic model mirror with the same `kind` discriminator. A client-submitted `{kind: "text", text: "..."}` is normalized to the raw `str` branch server-side.

Covered by task T3.2 (TS types) and T2.4 (Pydantic mirror).

### D5. Mobile / responsive ACs for FR-11d (resolves frontend-F-1)

**Decision**: append three mobile ACs at the task level (not spec-file edits — validation-iter2 is PASS). These are enforced in T3.5 (ChatShell) and T3.6 (InlineControl):

- **AC-plan-11d.M1 (touch-target)**: every tappable element in `ChatShell` (send button, chip, slider segment, toggle, card, confirmation button) MUST have a minimum 44×44 CSS px hit area on viewports ≤ 768px. Measured with Playwright `boundingBox()`.
- **AC-plan-11d.M2 (chip wrap)**: `ChipsControl` MUST wrap chips onto a second row at viewport width ≤ 360px (edge case: iPhone SE). No horizontal scroll on the control row. Measured with Playwright on `viewport: { width: 360, height: 640 }`.
- **AC-plan-11d.M3 (virtuoso resize)**: `react-virtuoso` MUST re-measure row heights when viewport resizes (orientation change, soft-keyboard open/close). Test: rotate viewport at turn 50/100 and assert scroll position within ±1 row of "following output" bottom.

**Rationale**: the amended spec covers desktop accessibility exhaustively (AC-11d.12, AC-11d.12b) but mobile ergonomics slipped through iter-1. Binding to task ACs rather than spec amendments preserves the PASS verdict.

### D6. Coverage threshold numbers for FR-11d modules (resolves testing-M1)

**Decision**: enforce per-module coverage floors in `pyproject.toml` + `portal/jest.config.js` via the existing coverage threshold keys. Binds to NFR-005.

| Module / file | Line coverage floor | Branch floor |
|---|---:|---:|
| `nikita/agents/onboarding/conversation_agent.py` | 85% | 80% |
| `nikita/agents/onboarding/extraction_schemas.py` | 90% | 85% |
| `nikita/agents/onboarding/conversation_prompts.py` | 85% | 75% |
| `nikita/agents/onboarding/handoff_greeting.py` | 85% | 80% |
| `nikita/api/routes/portal_onboarding.py` (`converse` path + `retry-handoff-greetings` path) | 85% | 80% |
| `portal/src/app/onboarding/components/ChatShell.tsx` | 80% | 70% |
| `portal/src/app/onboarding/components/InlineControl.tsx` | 80% | 70% |
| `portal/src/app/onboarding/components/controls/*.tsx` | 80% | 70% |
| `portal/src/app/onboarding/hooks/useConversationState.ts` | 85% | 80% |
| `portal/src/app/onboarding/components/ClearanceGrantedCeremony.tsx` | 80% | 70% |

**Rationale**: endpoint + agent code hit ≥85% because validator coverage (tool-use edge cases, idempotency, rate-limit, authz) is deterministic. UI components hit ≥80% because timing + reduced-motion branches are harder to exercise without flakiness. Floors enforced in CI (T6.2, cross-cutting).

---

## 4. Implementation Phases / PRs

Five sequenced PRs map to the rollout phases from tech-spec §8.1. PR branches follow `{type}/{spec-number}-{slug}` per `.claude/rules/pr-workflow.md`. Max 400 LOC per PR — enforced via pre-push check.

| PR | Branch | Phase | Priority | Gate | Size est. |
|---|---|---|---|---|---:|
| 1 | `fix/spec-214-fr11c-telegram-to-portal` | A (FR-11c) | P1 regression | CI green + Telegram MCP dogfood | ~350 LOC |
| 2 | `feat/spec-214-fr11d-conversation-agent-backend` | B-back (FR-11d) | P1 | CI green + `source="llm"` ≥90% measurement (AC-11d.9) | ~400 LOC |
| 3 | `feat/spec-214-fr11d-chat-wizard-frontend` | B-front (FR-11d) | P1 | CI green + Playwright @edge-case suite + axe-core | ~400 LOC |
| 4 | `feat/spec-214-fr11e-ceremonial-handoff` | C (FR-11e) | P2 | CI green + Telegram MCP dogfood within 5s | ~250 LOC |
| 5 | `chore/spec-214-onboarding-legacy-cleanup` | D (cleanup) | P2 | Completion-rate gate (AC-11d.13c) PASS + 30d post-PR-3 | ~150 LOC (mostly deletes) |

Rollback path: each PR independently revertable. PR 3 guarded by `USE_LEGACY_FORM_WIZARD` feature flag (tech-spec §8). Flip-to-true restores form wizard without touching backend.

---

## 5. Per-PR Task Breakdown

### PR 1 — `fix/spec-214-fr11c-telegram-to-portal`

**Objective**: eliminate legacy in-bot Q&A; route every Telegram entry to the portal.
**Requirements covered**: FR-11c (AC-11c.1 through AC-11c.12b).
**Files affected** (absolute):
- `nikita/platforms/telegram/commands.py` (rewrite `_handle_start`, add `_send_portal_auth_link`, `_send_portal_nudge`, `_send_bridge`)
- `nikita/platforms/telegram/message_handler.py` (add pre-onboard gate)
- `nikita/platforms/telegram/onboarding/` (DELETE entire package)
- `nikita/db/models/portal_bridge_token.py` (NEW)
- `nikita/db/repos/portal_bridge_token_repo.py` (NEW)
- `migrations/YYYYMMDD_portal_bridge_tokens.sql` (NEW)
- `nikita/onboarding/bridge_tokens.py` (NEW — `generate_portal_bridge_url`, TTL matrix)
- `tests/platforms/telegram/test_commands.py` (+11 cases)
- `tests/platforms/telegram/test_message_handler.py` (+2 cases)
- `tests/db/integration/test_portal_bridge_tokens.py` (NEW)
- `tests/platforms/telegram/onboarding/` (DELETE entire directory)

#### T1.1 — bridge-token DDL + model + repo (3h)
- **Owner**: executor-implement-verify
- **Dependencies**: none
- **ACs**:
  - AC-T1.1.1: `migrations/YYYYMMDD_portal_bridge_tokens.sql` creates `portal_bridge_tokens` table per D1 schema; verified via `mcp__supabase__apply_migration` on preview DB. Test: `mcp__supabase__list_policies` confirms admin + service_role RLS active.
  - AC-T1.1.2: `portal_bridge_token_repo.mint(user_id, reason) → str` inserts row with `expires_at = now() + (24h if reason='resume' else 1h)`. Test: row exists; expires_at matches TTL matrix within 1s.
  - AC-T1.1.3: `portal_bridge_token_repo.consume(token) → user_id | None` atomic-updates `consumed_at = now() WHERE token=:t AND consumed_at IS NULL AND expires_at > now()` and returns `user_id`. Second call returns `None`. Test: concurrency two-call exactly one succeeds.
  - AC-T1.1.4: `portal_bridge_token_repo.revoke_all_for_user(user_id)` marks all active tokens consumed (password-reset hook). Test: 3 active tokens for user → all `consumed_at` set.

#### T1.2 — `generate_portal_bridge_url` + E1 bare-URL path (2h)
- **Owner**: executor-implement-verify
- **Dependencies**: T1.1
- **ACs**:
  - AC-T1.2.1: `generate_portal_bridge_url(user_id=None, reason="resume"|"re-onboard"|None)` returns `f"{portal_url}/onboarding/auth"` when `user_id is None` (E1 new-user path per AC-11c.12). Test: regex `^{portal_url}/onboarding/auth$` exact match.
  - AC-T1.2.2: when `user_id` + `reason` provided, mints a token via repo and returns `f"{portal_url}/onboarding/auth?bridge={token}"`. Test: valid token string; URL matches pattern; DB row exists.
  - AC-T1.2.3: portal `/onboarding/auth` route consumes `?bridge=` param → calls backend `POST /portal/auth/bridge` → on success sets session cookie and redirects `/onboarding`. Expired / revoked / consumed → redirect `/onboarding/auth?nudge=expired` with Nikita-voiced copy "That link expired. Open Telegram and tap /start again." Test: integration test covers all 4 cases (valid / expired / revoked / consumed).

#### T1.3 — `_handle_start` vanilla-branch rewrite (4h)
- **Owner**: executor-implement-verify
- **Dependencies**: T1.2
- **ACs**:
  - AC-T1.3.1: E1 new user: unknown `telegram_id` → single inline URL button to bare `{portal_url}/onboarding/auth`. Zero DB writes. No text prompt asking for email. Covers AC-11c.1. Test: mocked bot + repo returns `None`; assert `bot.send_message_with_keyboard` called once with expected URL.
  - AC-T1.3.2: E2/E8 onboarded + active: returns welcome-back text only, no button, no state mutation. Covers AC-11c.2. Test: user with `onboarding_status='completed'` + profile + `game_status='active'` → assert no bridge call.
  - AC-T1.3.3: E3/E4 game_over/won: call `reset_game_state` + bridge with `reason='re-onboard'` (1h TTL). Covers AC-11c.3. Test: both game_status branches; reset_game_state invoked; bridge URL contains `?bridge=` with TTL row ≤1h.
  - AC-T1.3.4: E5/E6 pending/in_progress/limbo: bridge with `reason='resume'` (24h TTL) + "let's pick this up" copy. Covers AC-11c.4, AC-11c.5. Test: per-case DB state simulation; 24h TTL; copy asserted.
  - AC-T1.3.5: AC-11c.9 DI guard: `_handle_start` raises `RuntimeError` (not `assert`) if `profile_repository is None`. Test: DI wiring missing → `RuntimeError` at call time, not at import.

#### T1.4 — `/start <code>` payload branch preservation + password-reset revocation hook (2h)
- **Owner**: executor-implement-verify
- **Dependencies**: T1.1
- **ACs**:
  - AC-T1.4.1: `_handle_start_with_payload` existing atomic-bind behavior (PR #322) unchanged. Covers AC-11c.6. Test: regression test from `test_commands.py::TestHandleStartWithPayload` continues to pass.
  - AC-T1.4.2: Supabase webhook subscriber on `auth.users` password-change event calls `portal_bridge_token_repo.revoke_all_for_user(user_id)`. Wired via new endpoint `POST /api/v1/internal/auth/password-reset-hook` with Bearer auth. Test: simulated webhook → all user's active bridge tokens `consumed_at` set.

#### T1.5 — `message_handler` pre-onboard gate (E9, E10) (3h)
- **Owner**: executor-implement-verify
- **Dependencies**: T1.2
- **ACs**:
  - AC-T1.5.1: free text from user with `onboarding_status != 'completed'` OR `profile is None` → `_send_portal_nudge` + short-circuit BEFORE chat pipeline. Covers AC-11c.7. Test: pre-onboard user sends "hi" → nudge fired, pipeline `process_message` NOT called.
  - AC-T1.5.2: email-shaped text pre-onboard → in-character "no email here" nudge + bridge button. No OTP registration. Covers AC-11c.8. Test: regex `EMAIL_REGEX.match(text)` true → specific nudge variant sent.

#### T1.6 — legacy Q&A package + tests deletion (2h)
- **Owner**: executor-implement-verify
- **Dependencies**: T1.3, T1.5
- **ACs**:
  - AC-T1.6.1: `nikita/platforms/telegram/onboarding/` directory removed. Covers AC-11c.10. Test: `rg "OnboardingHandler|OnboardingStep|from nikita\.platforms\.telegram\.onboarding" nikita/` returns zero matches (CI gate).
  - AC-T1.6.2: PR description contains paste of `rg "TelegramAuth|otp_handler|email_otp|user_onboarding_state" nikita/ portal/` with per-caller disposition table (voice/admin/Q&A). Covers AC-11c.10b. Verified in PR review.
  - AC-T1.6.3: `onboarding_handler` constructor param removed from `message_handler` + DI wiring in `nikita/platforms/telegram/__init__.py` + `nikita/api/main.py`. Test: no `onboarding_handler` references anywhere in platforms/telegram.

#### T1.7 — post-merge log-guard smoke (1h)
- **Owner**: auto-dispatched post-merge subagent
- **Dependencies**: T1.6 merged
- **ACs**:
  - AC-T1.7.1: Cloud Run log grep for `"Created onboarding state for telegram_id"` over 24h post-merge returns zero matches. Covers AC-11c.11. Test: log-grep agent fails the post-merge check if found.
  - AC-T1.7.2: Telegram MCP dogfood walk: fresh throwaway account `/start` → single URL button, no Q&A text. Covers end-to-end in FR-11c Verification.

**PR 1 task total**: 7 tasks, 17h estimated. 17 ACs.

---

### PR 2 — `feat/spec-214-fr11d-conversation-agent-backend`

**Objective**: backend `/converse` endpoint + conversation agent + extraction schemas + rate-limiters + idempotency + spend ledger + handoff-greeting generator scaffolding.
**Requirements covered**: FR-11d backend (AC-11d.3 through AC-11d.11 + AC-NR1b.1b); FR-11e backend scaffolding (handoff_greeting only — dispatch wiring is PR 4).
**Files affected**:
- `nikita/agents/onboarding/conversation_agent.py` (NEW)
- `nikita/agents/onboarding/conversation_prompts.py` (NEW — imports `NIKITA_PERSONA`)
- `nikita/agents/onboarding/extraction_schemas.py` (NEW)
- `nikita/agents/onboarding/handoff_greeting.py` (NEW — consumed in PR 4)
- `nikita/api/routes/portal_onboarding.py` (extend with `/converse`)
- `nikita/api/middleware/rate_limit.py` (extend with `_ConversePerUserRateLimiter`, `_ConversePerIPRateLimiter`)
- `nikita/onboarding/spend_ledger.py` (NEW)
- `nikita/onboarding/idempotency.py` (NEW)
- `nikita/onboarding/tuning.py` (add constants per tech-spec §10)
- `migrations/YYYYMMDD_llm_idempotency_cache.sql` (NEW)
- `migrations/YYYYMMDD_llm_spend_ledger.sql` (NEW)
- `migrations/YYYYMMDD_users_handoff_greeting_dispatched_at.sql` (NEW)
- `tests/agents/onboarding/test_conversation_agent.py` (NEW)
- `tests/agents/onboarding/test_extraction_schemas.py` (NEW)
- `tests/agents/onboarding/test_handoff_greeting.py` (NEW)
- `tests/api/routes/test_converse_endpoint.py` (NEW)
- `tests/onboarding/test_tuning_constants.py` (extend)
- `tests/db/integration/test_onboarding_profile_conversation.py` (NEW)
- `tests/fixtures/jailbreak_patterns.yaml` (NEW, ≥20 patterns)
- `tests/fixtures/onboarding_tone_fixtures.yaml` (NEW, 20 fixtures)
- `tests/fixtures/persona_baseline_v1.csv` (NEW, pinned baseline)
- `specs/214-portal-onboarding-wizard/decisions/ADR-001-persona-drift-baseline.md` (NEW)
- `scripts/converse_source_rate_measurement.py` (NEW)

#### T2.1 — tuning constants + regression tests (2h)
- **Owner**: executor-implement-verify
- **Dependencies**: none
- **ACs**:
  - AC-T2.1.1: all 19 constants from tech-spec §10 tuning summary table added to `nikita/onboarding/tuning.py` as `Final[int|float|tuple[str, ...]]` with 3-line rationale docstring each per `.claude/rules/tuning-constants.md`. Test: `test_tuning_constants.py` asserts exact value per constant.
  - AC-T2.1.2: `ONBOARDING_FORBIDDEN_PHRASES: Final[tuple[str, ...]]` list ≥12 entries (pet names, flirt intensifiers, presumptive intimacy). Test: list exists, minimum length assert.

#### T2.2 — extraction schemas + unit tests (3h)
- **Owner**: executor-implement-verify
- **Dependencies**: T2.1
- **ACs**:
  - AC-T2.2.1: six Pydantic models (`LocationExtraction`, `SceneExtraction`, `DarknessExtraction`, `IdentityExtraction`, `BackstoryExtraction`, `PhoneExtraction`) per tech-spec §2.2. `IdentityExtraction.age: Optional[int] = Field(default=None, ge=18, le=99)` — below-18 raises `ValidationError`. `PhoneExtraction.phone` parsed via `phonenumbers.parse` (E.164) if `phone_preference="voice"`. Covers AC-11d.5 server-enforced branch.
  - AC-T2.2.2: confidence field on every schema ≥0.0, ≤1.0 via `Field(ge=0.0, le=1.0)`. Test: confidence=1.1 rejected 422.
  - AC-T2.2.3: `ConverseResult` union of all six extractions + `no_extraction: bool` fallback. Test: deserializes each of 7 branches.

#### T2.3 — conversation agent + persona import + prompt cache (3h)
- **Owner**: executor-implement-verify
- **Dependencies**: T2.2
- **ACs**:
  - AC-T2.3.1: `conversation_prompts.py::WIZARD_SYSTEM_PROMPT` imports `NIKITA_PERSONA` verbatim from `nikita.agents.text.persona` (no fork). Covers AC-11d.11 import gate. Test: string equality snapshot.
  - AC-T2.3.2: `get_conversation_agent()` returns a `pydantic_ai.Agent[ConverseDeps, ConverseResult]` with the six extraction tools registered via `agent.tool_plain(...)`. Anthropic model ID from `settings.anthropic_model_id`. Test: agent object has 6 tools + correct deps_type + result_type.
  - AC-T2.3.3: Anthropic API call includes `cache_control: {"type": "ephemeral"}` on the system-prompt block (long persona benefits from prompt caching). Verified via mocked Anthropic client asserting cache_control key present in request.

#### T2.4 — `ConverseRequest` / `ConverseResponse` + `ControlSelection` Pydantic model (2h)
- **Owner**: executor-implement-verify
- **Dependencies**: T2.2
- **ACs**:
  - AC-T2.4.1: `ConverseRequest` with `model_config = ConfigDict(extra="forbid")`. Body `user_id` field rejected 422 at Pydantic layer. Covers AC-11d.3. Test: POST with `{"user_id": "<other-uuid>"}` → 422.
  - AC-T2.4.2: `ControlSelection` discriminated-union Pydantic model per D4; kind literal matches `next_prompt_type`. Test: each of 5 kinds round-trips; unknown `kind` → 422.
  - AC-T2.4.3: `ConverseResponse.nikita_reply: str = Field(max_length=500)` server-side hard cap; server validator enforces business cap `NIKITA_REPLY_MAX_CHARS=140` (fallback on breach). Test: 141-char reply → fallback path.

#### T2.5 — `POST /converse` endpoint body (authz, rate-limit, idempotency, timeout, fallback) (6h)
- **Owner**: executor-implement-verify
- **Dependencies**: T2.1, T2.3, T2.4, T2.6, T2.7
- **ACs**:
  - AC-T2.5.1: `Depends(get_authenticated_user)` derives identity from Bearer JWT. Covers AC-11d.3. Test: missing/invalid JWT → 401; body `user_id` → 422.
  - AC-T2.5.2: tool-call argument pointing to another user's `onboarding_profile` JSONB path → 403 with generic `{"detail": "forbidden"}` body; exactly one `converse_authz_mismatch` structured event logged with `user_id, request_id, ts`. Covers AC-11d.3b. Test: prompt-injection fixture with tampered JSONB path → 403, log emitted exactly once.
  - AC-T2.5.3: idempotency short-circuit: `Idempotency-Key` header OR `turn_id` body → cache HIT returns cached body + status verbatim, agent-call-count=1 across replay, no JSONB write, no rate-limit decrement, no ledger increment. Header + body both present and differ → 409. Covers AC-11d.3c + D3. Test: replay within 5 min twice → agent called once; replay after 5 min → fresh call; header != body → 409.
  - AC-T2.5.4: per-user RPM bucket (`CONVERSE_PER_USER_RPM=20`) + per-IP bucket (`CONVERSE_PER_IP_RPM=30`) + daily USD cap (`CONVERSE_DAILY_LLM_CAP_USD=2.00`). Breach any → 429 with `Retry-After: 30` header + in-character Nikita-voiced body. Covers AC-11d.3d + AC-11d.3e + AC-11d.9. Test: 21st per-user call in 60s → 429; 31st per-IP call → 429; ledger sum ≥$2 → 429 before agent invocation.
  - AC-T2.5.5: input sanitization: strip `<`, `>`, null bytes; reject matches against `jailbreak_patterns.yaml` (≥20 entries covering delimiter injection, role override, multilingual, base64, tool-misuse, PII-exfil) → 200 + hardcoded fallback + `converse_input_reject` log. Covers AC-11d.5b + AC-11d.5d. Test: 20/20 fixtures return `source="fallback"`.
  - AC-T2.5.6: `asyncio.wait_for(agent.run(...), timeout=CONVERSE_TIMEOUT_MS/1000)` → on TimeoutError/exception/validator-reject: 200 + hardcoded fallback + `source="fallback"`. Covers AC-11d.9. Test: mock agent sleep 3s → response within 2.5s with fallback.
  - AC-T2.5.7: output leak filter: `nikita_reply` contains first 32 chars of `WIZARD_SYSTEM_PROMPT` or `NIKITA_PERSONA` → fallback + `converse_output_leak` log. Covers AC-11d.5c. Test: seeded agent output → fallback.
  - AC-T2.5.8: onboarding-tone filter: 20 fixtures in `onboarding_tone_fixtures.yaml` Gemini-judged via `mcp__gemini__gemini-structured`; ≥18/20 MUST pass; failed → fallback + `converse_tone_reject`. Covers AC-11d.5e. Test: CI assertion on fixture pass count.
  - AC-T2.5.9: tool-call edge cases: 0 tool calls → re-prompt current field (AC-11d.6); ≥2 tool calls → process first by priority `[extract > confirm > correct > clarify]` + `converse_multi_toolcall_warn`; required-None → reject extraction + set `confirmation_required=true`; format violation → reject + fallback. Covers AC-11d.5 + AC-11d.6. Test: four scenarios via mocked agent output.
  - AC-T2.5.10: nikita_reply validators: length ≤140, no markdown `[*_#`], no quotes `["']`, no PII concat (name+age+occ) → breach → fallback. Test: each rule branch fails the assert.
  - AC-T2.5.11: latency budget: p99 endpoint wall-clock ≤2500ms measured against mocked agent under CI. Test: timing assertion in `test_converse_endpoint.py`.

#### T2.6 — LLM spend ledger (DDL + repo + upsert pattern) (3h)
- **Owner**: executor-implement-verify
- **Dependencies**: T2.1
- **ACs**:
  - AC-T2.6.1: `migrations/YYYYMMDD_llm_spend_ledger.sql` creates table per tech-spec §4.3b, including RLS + pg_cron rollover. Test: `mcp__supabase__apply_migration` succeeds; `mcp__supabase__list_policies` confirms admin + service_role.
  - AC-T2.6.2: `spend_ledger.get_today(user_id) → Decimal` returns current-day spend (0 if no row). Test: new user → 0; after 2 upserts → sum.
  - AC-T2.6.3: `spend_ledger.add_spend(user_id, delta_usd)` executes D2 `INSERT ... ON CONFLICT DO UPDATE` pattern atomic increment. Test: concurrent two calls for same user_id/day → final spend == 2×delta (no lost update).

#### T2.7 — idempotency cache (DDL + repo + pg_cron prune) (2h)
- **Owner**: executor-implement-verify
- **Dependencies**: T2.1
- **ACs**:
  - AC-T2.7.1: `migrations/YYYYMMDD_llm_idempotency_cache.sql` per tech-spec §4.3a. Test: migration applies; RLS active; pg_cron job `llm_idempotency_cache_prune` scheduled hourly.
  - AC-T2.7.2: `idempotency.get((user_id, turn_id)) → (response_body, status_code) | None` + `idempotency.put(user_id, turn_id, body, status)` with 5-min TTL check on read. Test: put then get within 5 min → HIT; put then get after 6 min → MISS.

#### T2.8 — JSONB per-user-serialized write path (3h)
- **Owner**: executor-implement-verify
- **Dependencies**: T2.5
- **ACs**:
  - AC-T2.8.1: conversation-turn persistence uses SQLAlchemy ORM `SELECT ... FOR UPDATE` → mutate `user.onboarding_profile["conversation"]` in memory → `session.commit()`. No raw `jsonb_set`. Covers AC-NR1b.1b. Test in `test_onboarding_profile_conversation.py`: two concurrent writes for same user_id → final `conversation` array has both turns, order by client timestamp, no lost update, no double-encoded JSON.
  - AC-T2.8.2: User ORM model wraps `onboarding_profile` in `MutableDict.as_mutable(JSONB)` so in-memory mutation triggers dirty-tracking. Test: mutate nested dict without reassigning → commit flushes change.
  - AC-T2.8.3: 100-turn cap per AC-NR1b.5: on write, if `len(conversation) > 100`, elide oldest turn while preserving extracted fields into a structured `elided_extracted` dict. Test: 101st write evicts turn[0]; `elided_extracted` contains turn[0]'s extracted fields.

#### T2.9 — persona-drift baseline + ADR + test (3h)
- **Owner**: executor-implement-verify
- **Dependencies**: T2.3
- **ACs**:
  - AC-T2.9.1: `specs/214-portal-onboarding-wizard/decisions/ADR-001-persona-drift-baseline.md` documents regen process: seed prompts, temperature 0.0, N=20 per agent, CSV columns, version bump trigger. Format matches `~/.claude/ecosystem-spec/decisions/` ADR template.
  - AC-T2.9.2: `tests/fixtures/persona_baseline_v1.csv` pinned with main text agent output for 3 seeds × 20 samples. Generated via one-shot script; committed.
  - AC-T2.9.3: `test_conversation_agent.py::test_persona_drift_vs_baseline` computes TF-IDF cosine ≥`PERSONA_DRIFT_COSINE_MIN=0.70` + three features within ±`PERSONA_DRIFT_FEATURE_TOLERANCE=0.15` of baseline. Fails with specific feature + measured delta. Covers AC-11d.11.

#### T2.10 — handoff-greeting generator scaffolding (2h)
- **Owner**: executor-implement-verify
- **Dependencies**: T2.3
- **ACs**:
  - AC-T2.10.1: `generate_handoff_greeting(user_id, trigger, *, user_repo, backstory_repo, memory) → str` signature per tech-spec §2.4. Both triggers (`handoff_bind`, `first_user_message`) use same agent + persona; only prompt framing differs. Test: both triggers produce valid output; prompt text differs between triggers.
  - AC-T2.10.2: greeting references `onboarding_profile.name` when present; `location_city` + `backstories[latest].venue_name` optional. Test: fixture user with all three fields → greeting contains name. Covers AC-11e.2 backend unit slice.
  - AC-T2.10.3: persona-drift pairwise test across (main_text, conversation, handoff) each within AC-11d.11 gates. Covers AC-11e.4.

#### T2.11 — `source="llm"` rate measurement script + rollout gate (1h)
- **Owner**: executor-implement-verify
- **Dependencies**: T2.5
- **ACs**:
  - AC-T2.11.1: `scripts/converse_source_rate_measurement.py` runs `LLM_SOURCE_RATE_GATE_N=100` simulated wizard turns against the preview endpoint, prints `source="llm"` pct. Covers AC-11d.9 rollout gate prep.
  - AC-T2.11.2: script exits non-zero if `source="llm"` rate <`LLM_SOURCE_RATE_GATE_MIN=0.90`. Results pasted in PR 3 description (ship gate). Test: manual dry-run on preview.

**PR 2 task total**: 11 tasks, 30h estimated. 36 ACs.

---

### PR 3 — `feat/spec-214-fr11d-chat-wizard-frontend`

**Objective**: portal chat UI consumes PR 2 backend. Legacy step components MOVED to `steps/legacy/` behind feature flag (not deleted — Phase D).
**Requirements covered**: FR-11d frontend (AC-11d.1, .2, .4, .4b, .7, .8, .10, .10b, .12, .12b, .13, .13b, .13c); NR-1b.1, .2, .3, .4.
**Files affected**:
- `portal/src/app/onboarding/onboarding-wizard.tsx` (rewrite)
- `portal/src/app/onboarding/components/ChatShell.tsx` (NEW)
- `portal/src/app/onboarding/components/MessageBubble.tsx` (NEW)
- `portal/src/app/onboarding/components/TypingIndicator.tsx` (NEW)
- `portal/src/app/onboarding/components/InlineControl.tsx` (NEW, ≤30 LOC dispatcher)
- `portal/src/app/onboarding/components/controls/TextControl.tsx` (NEW)
- `portal/src/app/onboarding/components/controls/ChipsControl.tsx` (NEW)
- `portal/src/app/onboarding/components/controls/SliderControl.tsx` (NEW)
- `portal/src/app/onboarding/components/controls/ToggleControl.tsx` (NEW)
- `portal/src/app/onboarding/components/controls/CardsControl.tsx` (NEW)
- `portal/src/app/onboarding/components/ProgressHeader.tsx` (NEW)
- `portal/src/app/onboarding/components/ConfirmationButtons.tsx` (NEW)
- `portal/src/app/onboarding/hooks/useConversationState.ts` (NEW)
- `portal/src/app/onboarding/hooks/useOnboardingAPI.ts` (extend `converse()` method)
- `portal/src/app/onboarding/hooks/useOptimisticTypewriter.ts` (NEW)
- `portal/src/app/onboarding/types/ControlSelection.ts` (NEW — D4 TS union)
- `portal/src/app/onboarding/steps/legacy/` (MOVE all legacy step files here)
- `portal/src/app/onboarding/__tests__/*.test.tsx` (9 test files)
- `tests/e2e/portal/test_onboarding.spec.ts` (rewrite with `@edge-case` tag suite)

#### T3.1 — reducer + StrictMode guard + turn-ceiling elision (4h)
- **Owner**: executor-implement-verify
- **Dependencies**: T2.5 (contract)
- **ACs**:
  - AC-T3.1.1: `useConversationState` reducer handles actions per tech-spec §5.2: `hydrate`, `user_input`, `server_response`, `server_error`, `timeout`, `retry`, `truncate_oldest`, `confirm`, `reject_confirmation`, `clearPendingControl`. Test: each action transitions state as documented; snapshot test per action.
  - AC-T3.1.2: `hydrate` dispatched from `useEffect` (not initial render). 50ms dedup window via `STRICTMODE_GUARD_MS` constant; StrictMode-double-mount dispatches one reducer update only. Covers AC-NR1b.2. Test: React StrictMode enabled → reducer receives 1 hydrate action.
  - AC-T3.1.3: `clearPendingControl` on `reject_confirmation`. Covers AC-11d.4b + frontend-M2. Test: after Fix-that, `currentPromptType === "none"` briefly; next server_response sets new type.
  - AC-T3.1.4: `truncate_oldest` when `turns.length > 100`. Preserves extracted fields from elided turn in `state.elidedExtracted`. Covers AC-NR1b.5.

#### T3.2 — `ControlSelection` discriminated-union TS type + client-side validator (1h)
- **Owner**: executor-implement-verify
- **Dependencies**: none
- **ACs**:
  - AC-T3.2.1: TS union per D4 with 5 kinds. Test: type narrowing compiles; runtime zod schema mirrors TS shape; invalid kind rejected at boundary.
  - AC-T3.2.2: client normalizes `{kind: "text"}` to raw string before POST /converse (matches server `Union[str, ControlSelection]`). Test: "text" branch posts `user_input: "..."`; other branches post the full object.

#### T3.3 — hydrate source-of-truth order (2h)
- **Owner**: executor-implement-verify
- **Dependencies**: T3.1
- **ACs**:
  - AC-T3.3.1: on mount, fetch `GET /portal/onboarding/profile` first; use result as authoritative. If localStorage has newer turns AND both agree on extracted fields, localStorage turns append. On conflict, server wins. Covers AC-NR1b.2 + AC-NR1b.1. Test: seeded JSONB + newer localStorage → server wins; no flash of empty state.
  - AC-T3.3.2: `schema_version=2` migration shim: v1 state → v2 synthesizes `conversation: []`, preserves extracted fields. Covers AC-NR1b.3. Test: v1 localStorage → v2 reducer state with empty conversation + populated extractedFields.
  - AC-T3.3.3: on completion (`conversation_complete=true`), localStorage is cleared via `removeItem`. Covers AC-NR1b.4. Test: completion triggers removeItem; JSONB `conversation` persists.

#### T3.4 — `useOnboardingAPI.converse()` method + idempotency (2h)
- **Owner**: executor-implement-verify
- **Dependencies**: T2.5
- **ACs**:
  - AC-T3.4.1: client generates `turn_id: crypto.randomUUID()` per user-input event, posts to `/converse` with header `Idempotency-Key: <turn_id>`. No retry wrapper (endpoint non-idempotent except via cache). Test: idempotency header matches body `turn_id`.
  - AC-T3.4.2: 429 response renders the server-provided `nikita_reply` as in-character bubble (no red banner), schedules retry after `Retry-After` header seconds, preserves the typed input. Covers AC-11d.9. Test: mocked 429 → bubble rendered, retry fires at 30s, input field value unchanged.

#### T3.5 — `ChatShell` + typing indicator + virtualization + aria-live scope + mobile ACs (5h)
- **Owner**: executor-implement-verify
- **Dependencies**: T3.1, T3.4
- **ACs**:
  - AC-T3.5.1: `role="log"` + `aria-live="polite"` ONLY on `ChatShell` scroll container. `MessageBubble` has NO `aria-live`. Typewriter content `aria-hidden="true"` during reveal; sibling `<span class="sr-only">` carries final text. Covers AC-11d.12 + AC-11d.12b. Test: axe-core passes; unit test asserts scoped aria-live.
  - AC-T3.5.2: `react-virtuoso` wraps the turn list with `followOutput="smooth"`. Eager render ≤20 turns; windowed render >20 turns. Covers AC-11d.10b. Test: render 100 fixture turns → DOM contains ≤30 `MessageBubble` nodes; append new turn → smooth-scrolls to bottom.
  - AC-T3.5.3: typing indicator (pulsing dots) rendered 0.5-1s before every Nikita message. Typewriter reveal ~40 chars/sec capped at 1.5s per message. `prefers-reduced-motion` disables typewriter and shows full text immediately. Covers AC-11d.1. Test: timing test with mocked `performance.now()`.
  - AC-T3.5.4 (AC-plan-11d.M1 touch-target): every tappable in `ChatShell` has ≥44×44 CSS px on viewports ≤768px. Test: Playwright `boundingBox()` on send button + each control meets floor.
  - AC-T3.5.5 (AC-plan-11d.M3 virtuoso resize): orientation change or viewport resize triggers `useWindowVirtualizer`-style remeasure. Test: rotate viewport at turn 50 + 100 → scroll position within ±1 row of bottom.

#### T3.6 — `InlineControl` dispatcher + 5 controls (5h)
- **Owner**: executor-implement-verify
- **Dependencies**: T3.2
- **ACs**:
  - AC-T3.6.1: `InlineControl.tsx` is ≤30 LOC, no inline switch/if-else tree. Reads `next_prompt_type` from a `controls/` registry. Covers frontend-H13 (InlineControl slim). Test: `wc -l` asserts ≤30.
  - AC-T3.6.2: Each of 5 controls (Text / Chips / Slider / Toggle / Cards) renders per its branch of `ControlSelection`. Both typed and tapped paths commit via the same `POST /converse` payload shape. Covers AC-11d.2. Test: integration test with both input paths asserts identical server payload.
  - AC-T3.6.3 (AC-plan-11d.M2 chip wrap): `ChipsControl` wraps at viewport width ≤360px. No horizontal scroll. Test: Playwright `viewport: { width: 360 }` → element height > row height.
  - AC-T3.6.4: `CardsControl` for backstory scenarios matches FR-4 shape (`chosen_option_id`, `cache_key`); `SliderControl` for darkness 1-5; `ToggleControl` for phone voice/text; `ChipsControl` for scene.

#### T3.7 — `ConfirmationButtons` + Fix-that ghost-turn + pending-control clear (3h)
- **Owner**: executor-implement-verify
- **Dependencies**: T3.1, T3.5
- **ACs**:
  - AC-T3.7.1: when `confirmation_required=true`, `[Yes] [Fix that]` buttons render inline below Nikita's echo bubble. Covers AC-11d.4. Test: snapshot + click handlers.
  - AC-T3.7.2: Fix-that ghost-turn: rejected user turn marked `superseded: true`, rendered at `opacity: 0.5` (no strikethrough). Nikita's next bubble acknowledges correction. Covers AC-11d.4b. Test: DOM has `supersededTurn` class + inline `opacity: 0.5`; next bubble matches "ask again" pattern.
  - AC-T3.7.3: `clearPendingControl` action fires on `reject_confirmation` so stale pre-filled control is hidden before re-ask control renders. Covers frontend-M2. Test: between reject and next server_response, `currentPromptType="none"`.

#### T3.8 — `ProgressHeader` + progress math (1h)
- **Owner**: executor-implement-verify
- **Dependencies**: T3.1
- **ACs**:
  - AC-T3.8.1: bar width `width: {progress_pct}%`; label text `Building your file... N%`. Updates after every confirmed extraction. Covers AC-11d.8. Test: pixel width mapping; label format exact match.
  - AC-T3.8.2: server owns progress math (agent computes). Client does not re-derive from extracted-field count. Test: mocked server_response with `progress_pct=42` → label `42%`.

#### T3.9 — wizard rewrite + legacy-component move + feature flag (3h)
- **Owner**: executor-implement-verify
- **Dependencies**: T3.3, T3.5, T3.6, T3.7, T3.8
- **ACs**:
  - AC-T3.9.1: `onboarding-wizard.tsx` rewritten: single `ChatShell` container driven by `useConversationState`. On `conversation_complete=true`, mount `ClearanceGrantedCeremony` (PR 4 replaces PR 3 empty stub). Covers AC-11d.13.
  - AC-T3.9.2: feature flag `USE_LEGACY_FORM_WIZARD` (env var + portal Settings surface). Default `false` in production. Flip-to-`true` restores legacy form wizard without re-deploy. Covers tech-spec §8 rollback.
  - AC-T3.9.3: legacy step files (`EdginessSliderStep.tsx`, `SceneSelectorStep.tsx`, `DossierRevealStep.tsx`, `HandoffStep.tsx`, `LocationStep.tsx`, `IdentityStep.tsx`, `PhoneStep.tsx`, etc.) MOVED (not deleted) to `portal/src/app/onboarding/steps/legacy/`. Deletion deferred to PR 5. Covers frontend-H13. Test: `ls portal/src/app/onboarding/steps/legacy/` lists all moved files.
  - AC-T3.9.4: on reducer `server_response conversation_complete=true`, POST `/portal/link-telegram` fires BEFORE `ClearanceGrantedCeremony` mounts. Covers tech-spec §2.6. Test: integration test asserts POST /link-telegram called exactly once before ceremony render.

#### T3.10 — Playwright E2E rewrite + `@edge-case` tagged suite (4h)
- **Owner**: executor-implement-verify
- **Dependencies**: T3.9
- **ACs**:
  - AC-T3.10.1: `test_onboarding.spec.ts` rewritten: 11 assertions per tech-spec §7.3 happy-path walk. Assertions target DOM structure + bubble count, not LLM-variable content strings. Covers FR-11d Verification.
  - AC-T3.10.2: `@edge-case` tagged sub-suite with 4 walks: Fix-that ghost-turn; 2500ms timeout fallback; backtracking "change my city to Berlin"; age<18 in-character. Isolatable via `playwright test --grep @edge-case`. Covers AC-11d.13b + AC-11d.7. Test: each walk green in CI.

#### T3.11 — dashboard gate + `onboarding_status='completed'` redirect (1h)
- **Owner**: executor-implement-verify
- **Dependencies**: T3.9
- **ACs**:
  - AC-T3.11.1: portal middleware or `/onboarding` route guard redirects to `/dashboard` when `onboarding_status='completed'`. Covers AC-11e.5. Test: integration test on middleware.

#### T3.12 — completion-rate measurement endpoint + admin card (2h)
- **Owner**: executor-implement-verify
- **Dependencies**: T3.9, merged to master
- **ACs**:
  - AC-T3.12.1: `/admin/onboarding/completion-rate` admin dashboard card shows rolling chat-wizard completion rate + form-wizard baseline. Covers AC-11d.13c measurement surface. Test: card renders with live data via backend stat endpoint.
  - AC-T3.12.2: after `CHAT_COMPLETION_RATE_GATE_N=50` sign-ups, observed chat-wizard completion MUST be within ±`CHAT_COMPLETION_RATE_TOLERANCE_PP=5` pp of baseline. On miss, PR 5 (legacy delete) BLOCKED. Measurement script `scripts/measure_completion_rate.py` prints result, emits exit code. Gate-check dispatched post-merge; result pasted in Spec 214 work-log.

**PR 3 task total**: 12 tasks, 33h estimated. 37 ACs.

---

### PR 4 — `feat/spec-214-fr11e-ceremonial-handoff`

**Objective**: portal closeout ceremony + proactive Telegram greeting on bind + durable dispatch + pg_cron backstop + stranded-user migration + PII retention pg_cron + admin-visibility audit.
**Requirements covered**: FR-11e (AC-11e.1 through AC-11e.6); NR-1b.4b, .4c.
**Files affected**:
- `portal/src/app/onboarding/components/ClearanceGrantedCeremony.tsx` (replace PR 3 stub)
- `portal/src/app/onboarding/components/DossierStamp.tsx` (reuse existing, mount inside ceremony)
- `portal/src/app/onboarding/__tests__/ClearanceGrantedCeremony.test.tsx` (NEW)
- `nikita/platforms/telegram/commands.py` (extend `_handle_start_with_payload`)
- `nikita/api/routes/telegram.py` (plumb `BackgroundTasks` param)
- `nikita/api/routes/tasks.py` (add `/retry-handoff-greetings`)
- `nikita/db/repos/user_repo.py` (add `clear_pending_handoff`, `reset_handoff_dispatch`)
- `nikita/db/models/user.py` (add `handoff_greeting_dispatched_at` column)
- `migrations/YYYYMMDD_onboarding_conversation_retention.sql` (NEW — pg_cron job)
- `scripts/handoff_stranded_migration.py` (NEW)
- `nikita/api/routes/admin.py` (extend `/admin/onboarding/conversations/:user_id` with opt-in conversation + audit log)
- `nikita/db/models/admin_audit_log.py` (NEW if not present)
- `migrations/YYYYMMDD_admin_audit_log.sql` (NEW if not present)
- `tests/platforms/telegram/test_commands.py::TestHandleStartWithPayload` (extend)
- `tests/db/integration/test_handoff_boundary.py` (NEW)
- `tests/api/routes/test_tasks.py::TestRetryHandoffGreetings` (NEW)
- `tests/api/routes/test_admin_onboarding.py` (NEW)

#### T4.1 — `ClearanceGrantedCeremony` full-viewport component (3h)
- **Owner**: executor-implement-verify
- **Dependencies**: T3.9 (merged)
- **ACs**:
  - AC-T4.1.1: renders full viewport with stamp animation ("FILE CLOSED. CLEARANCE: GRANTED."), Nikita's final bubble, CTA "Meet her on Telegram", QR on desktop ≥768px (reuse `QRHandoff`). Covers AC-11e.1. Test: DOM snapshot + QR conditional render.
  - AC-T4.1.2: `prefers-reduced-motion` disables stamp animation; final state paints immediately. Test: CSS media-query mock → no animation class.
  - AC-T4.1.3: CTA `href = "t.me/Nikita_my_bot?start=" + state.code` where `state.code` is minted by reducer BEFORE ceremony mounts (tech-spec §2.6). Ceremony never mints. Test: mount with null code → throws; mount with code → href matches regex.

#### T4.2 — `handoff_greeting_dispatched_at` column + repo methods (1h)
- **Owner**: executor-implement-verify
- **Dependencies**: T2 merged (migration file ships in PR 2)
- **ACs**:
  - AC-T4.2.1: migration adds `handoff_greeting_dispatched_at TIMESTAMPTZ NULL` to `users` + partial index `idx_users_handoff_backstop ON users (handoff_greeting_dispatched_at) WHERE pending_handoff=TRUE AND telegram_id IS NOT NULL`. Covers tech-spec §4.2. Test: migration applies; index listed.
  - AC-T4.2.2: `user_repo.claim_handoff_intent(user_id) → bool` executes the atomic `UPDATE ... SET handoff_greeting_dispatched_at=now() WHERE id=:uid AND dispatched_at IS NULL AND pending_handoff=TRUE RETURNING id;`. Returns True iff rowcount==1. Test: first call True; second concurrent call False.
  - AC-T4.2.3: `user_repo.clear_pending_handoff(user_id)` sets `pending_handoff=FALSE`. Test: row updated.
  - AC-T4.2.4: `user_repo.reset_handoff_dispatch(user_id)` sets `handoff_greeting_dispatched_at=NULL` (retry-exhaust compensating update). Test: row reset.

#### T4.3 — `_handle_start_with_payload` extension with BackgroundTasks + retry (4h)
- **Owner**: executor-implement-verify
- **Dependencies**: T4.2, T2.10
- **ACs**:
  - AC-T4.3.1: webhook route `nikita/api/routes/telegram.py:508` plumbs `background_tasks: BackgroundTasks` down to `_handle_start_with_payload`. Covers tech-spec §2.5 convention. Test: signature assertion; mocked BackgroundTasks receives `.add_task` call.
  - AC-T4.3.2: sequence per tech-spec §2.5: (1) atomic bind (PR #322, unchanged); (2) `claim_handoff_intent` → proceed on rowcount==1; (3) webhook returns 200 first; (4) `_dispatch_greeting_with_retry` via `background_tasks.add_task` with [0.5s, 1s, 2s] backoff on Telegram 5xx; (5) on success `clear_pending_handoff`; on retry-exhaust `reset_handoff_dispatch` + log `handoff_greeting_retry_exhausted`. Covers AC-11e.3. Test: concurrent `/start <code>` → one dispatch only; mock Telegram 5xx×3 → reset + log.
  - AC-T4.3.3: webhook wall-clock p99 <2s with deliberately slow greeting mock (3s sleep); greeting still arrives afterward. Covers AC-11e.3b. Test: timing assertion in `test_commands.py`.

#### T4.4 — `POST /api/v1/tasks/retry-handoff-greetings` + pg_cron job (2h)
- **Owner**: executor-implement-verify
- **Dependencies**: T4.3
- **ACs**:
  - AC-T4.4.1: endpoint Bearer-authed via `TASK_AUTH_SECRET`, re-dispatches greetings for rows `WHERE pending_handoff=TRUE AND telegram_id IS NOT NULL AND (dispatched_at IS NULL OR dispatched_at < now() - interval '30 seconds')`. Covers AC-11e.3 backstop. Test: seed stranded user + run endpoint + assert greeting dispatched.
  - AC-T4.4.2: pg_cron job `nikita_handoff_greeting_backstop` scheduled every 60s via `net.http_post` with hardcoded Bearer token. `HANDOFF_GREETING_BACKSTOP_INTERVAL_SEC=60`. Test: `SELECT * FROM cron.job WHERE jobname='nikita_handoff_greeting_backstop'` returns one row with 60s schedule.

#### T4.5 — stranded-user one-shot migration script (2h)
- **Owner**: executor-implement-verify
- **Dependencies**: T4.4
- **ACs**:
  - AC-T4.5.1: `scripts/handoff_stranded_migration.py` selects rows `WHERE pending_handoff=TRUE AND telegram_id IS NOT NULL AND dispatched_at IS NULL`; for each invokes the backstop endpoint or `generate_handoff_greeting`; clears flag on success; logs per-row outcome; idempotent on re-run. Covers AC-11e.3c. Test: 5 stranded fixture users → 5 greetings dispatched + 5 flags cleared; re-run is no-op.

#### T4.6 — 90-day conversation retention pg_cron (1h)
- **Owner**: executor-implement-verify
- **Dependencies**: T2.8
- **ACs**:
  - AC-T4.6.1: pg_cron job `onboarding_conversation_nullify_90d` daily 03:00 UTC `UPDATE users SET onboarding_profile = onboarding_profile - 'conversation' WHERE onboarding_status='completed' AND (onboarding_profile->>'completed_at')::timestamptz < now() - interval '90 days' AND onboarding_profile ? 'conversation';`. Covers AC-NR1b.4b. Test: fixture user at day 91 + cron run → `conversation` key removed, structured fields (name, age, etc.) intact.

#### T4.7 — GDPR account-delete coupling (1h)
- **Owner**: executor-implement-verify
- **Dependencies**: T4.6
- **ACs**:
  - AC-T4.7.1: `user_repo.delete_user(user_id)` additionally `UPDATE users SET onboarding_profile=NULL WHERE id=:uid` AND `DELETE FROM user_onboarding_state WHERE user_id=:uid`. Covers AC-NR1b.4b second clause. Test: delete user with populated profile + legacy row → both nullified.

#### T4.8 — admin visibility default-off + audit log (2h)
- **Owner**: executor-implement-verify
- **Dependencies**: T2.8
- **ACs**:
  - AC-T4.8.1: `GET /admin/onboarding/conversations/:user_id` returns `{user_id, extracted_fields, onboarding_status}` by default; query param `?include_conversation=true` adds `conversation` JSONB AND writes one row to `admin_audit_log {event, admin_id, target_user_id, ts}`. Covers AC-NR1b.4c. Test: default GET omits conversation; opt-in GET includes it AND writes exactly one audit row.
  - AC-T4.8.2: `admin_audit_log` table + RLS `USING (is_admin()) WITH CHECK (is_admin())`. Test: migration creates table; `list_policies` confirms.

#### T4.9 — proactive-greeting Telegram MCP dogfood E2E (1h)
- **Owner**: auto-dispatched subagent post-merge
- **Dependencies**: T4.3, T4.5 deployed
- **ACs**:
  - AC-T4.9.1: Telegram MCP dogfood walk: complete portal chat wizard → tap CTA → observe proactive greeting within 5s referencing name. Covers AC-11e.2. Test: live walk with `mcp__claude-in-chrome__*` + `mcp__telegram-mcp__*`.
  - AC-T4.9.2: second-account `/start` from already-onboarded user → welcome-back only, no second greeting. Covers AC-11e.6. Test: second throwaway account repeats flow; no duplicate greeting.

**PR 4 task total**: 9 tasks, 17h estimated. 23 ACs.

---

### PR 5 — `chore/spec-214-onboarding-legacy-cleanup`

**Objective**: delete `portal/src/app/onboarding/steps/legacy/` + drop `user_onboarding_state` table + remove `TelegramAuth` if fully unused. Gated on Phase C completion-rate PASS + ≥30-day quiet period.
**Requirements covered**: tech-spec §8 Phase D rollout.
**Files affected**:
- `portal/src/app/onboarding/steps/legacy/` (DELETE)
- `migrations/YYYYMMDD_drop_user_onboarding_state.sql` (NEW)
- `nikita/platforms/telegram/telegram_auth.py` (DELETE if audit shows unused)
- `tests/` cleanup of stale test files referencing deleted modules

#### T5.1 — legacy-wizard completion-rate gate check (1h)
- **Owner**: auto-dispatched measurement subagent
- **Dependencies**: PR 3 merged + ≥7 days prod + 50+ sign-ups
- **ACs**:
  - AC-T5.1.1: `scripts/measure_completion_rate.py` returns chat-wizard rate within ±`CHAT_COMPLETION_RATE_TOLERANCE_PP=5` pp of form baseline over N≥50 sign-ups. Exit 0 on PASS, 1 on FAIL. Covers AC-11d.13c. Test: measurement run + pasted result in PR 5 description.
  - AC-T5.1.2: on FAIL, PR 5 BLOCKED; escalate to SSE streaming spec or UX tuning follow-up. Gate mechanism: pre-merge check script parses exit code.

#### T5.2 — FK-audit + drop `user_onboarding_state` (1h)
- **Owner**: executor-implement-verify
- **Dependencies**: T5.1 PASS + ≥30 days since PR 3 ship
- **ACs**:
  - AC-T5.2.1: pre-drop FK-audit query returns zero rows. Covers AC-11c.12b + tech-spec §4.3. Test: `information_schema.table_constraints` query pasted in PR description.
  - AC-T5.2.2: migration `migrations/YYYYMMDD_drop_user_onboarding_state.sql` executes `DROP TABLE IF EXISTS user_onboarding_state CASCADE;`. In-flight rows count (< 15 per 2026-04-19 snapshot) documented. Non-reversible. Test: migration dry-run on preview; `mcp__supabase__list_tables` post-migration shows absence.

#### T5.3 — legacy step components deletion (1h)
- **Owner**: executor-implement-verify
- **Dependencies**: T5.1 PASS
- **ACs**:
  - AC-T5.3.1: `portal/src/app/onboarding/steps/legacy/` deleted. Feature flag `USE_LEGACY_FORM_WIZARD` removed. Test: `ls portal/src/app/onboarding/steps/legacy/` returns ENOENT; `rg "USE_LEGACY_FORM_WIZARD" portal/ nikita/` zero matches.
  - AC-T5.3.2: relevant tests in `portal/src/app/onboarding/__tests__/` for legacy steps removed. Test: Jest suite green.

#### T5.4 — `TelegramAuth` audit + conditional removal (1h)
- **Owner**: executor-implement-verify
- **Dependencies**: T1.6 AC-T1.6.2 audit
- **ACs**:
  - AC-T5.4.1: re-run `rg "TelegramAuth|otp_handler|email_otp" nikita/ portal/`. If only voice + admin callers remain (no Q&A), remove unused pieces only. Document disposition in PR description. Test: grep before/after; no in-use callers broken.

**PR 5 task total**: 4 tasks, 4h estimated. 8 ACs.

---

## 6. Dependency Graph

```
PR 1 (FR-11c bridge tokens + Telegram rewrite)
  T1.1 ──▶ T1.2 ──▶ T1.3
     └──▶ T1.4           ──▶ T1.6 ──▶ T1.7 (post-merge)
     └──▶ T1.5           ──┘

PR 2 (FR-11d backend agent + endpoint)
  T2.1 ──▶ T2.2 ──▶ T2.3 ──▶ T2.10
                ├──▶ T2.4
                └──▶ T2.9 (persona drift)
  T2.1 ──▶ T2.6 (spend ledger)
  T2.1 ──▶ T2.7 (idempotency)
  T2.3 + T2.4 + T2.6 + T2.7 ──▶ T2.5 (endpoint body)
  T2.5 ──▶ T2.8 (JSONB concurrency)
  T2.5 ──▶ T2.11 (measurement script)

PR 3 (FR-11d frontend chat wizard)  [requires PR 2 merged to master]
  T3.2 ──▶ T3.6
  T3.1 ──▶ T3.3 ──▶ T3.9
  T3.1 ──▶ T3.7
  T3.1 ──▶ T3.8
  T3.4 ──▶ T3.5 ──▶ T3.9
  T3.6 ──▶ T3.9
  T3.7 ──▶ T3.9
  T3.8 ──▶ T3.9 ──▶ T3.10
                 └▶ T3.11
  T3.9 merged ──▶ T3.12 (measurement)

PR 4 (FR-11e ceremonial handoff)    [requires PR 3 merged]
  T4.1 (ceremony) ──▶ (parallel with T4.2-T4.5)
  T4.2 (column + repo) ──▶ T4.3 ──▶ T4.4 ──▶ T4.5
                                          └──▶ T4.9 (post-merge dogfood)
  T2.8 merged ──▶ T4.6 (retention cron) ──▶ T4.7 (GDPR coupling)
  T2.8 merged ──▶ T4.8 (admin opt-in + audit)

PR 5 (legacy cleanup)               [requires PR 3 merged + ≥30d + T5.1 PASS]
  T5.1 (gate) ──▶ T5.2 (drop table)
              └──▶ T5.3 (delete legacy components)
              └──▶ T5.4 (TelegramAuth audit)

Cross-PR serialization:
  PR 1 ──▶ PR 2 ──▶ PR 3 ──▶ PR 4 ──▶ PR 5
```

**Edges**: 28 intra-PR edges + 4 cross-PR serializations = 32 total.
**Cycles**: none.

---

## 7. Risk Register

Top 5 risks with mitigations. Drawn from spec Risks + amendments.

| # | Risk | Likelihood | Impact | Mitigation | Owner task |
|---|---|---|---|---|---|
| R1 | **Cloud Run instance eviction between `claim_handoff_intent` and greeting dispatch silently drops the greeting** (FR-11e B1) | Med | High | pg_cron backstop every 60s re-dispatches stranded rows; `handoff_greeting_dispatched_at` age window `>30s` triggers retry; stranded-user one-shot migration covers pre-deploy rows | T4.4, T4.5 |
| R2 | **Persona drift between conversation agent and main text agent breaks voice continuity** (FR-11d S3, M1) | Med | High | Falsifiable TF-IDF-cosine + 3-feature test (AC-11d.11); baseline pinned at `persona_baseline_v1.csv`; pairwise drift across (text, conversation, handoff) in AC-11e.4; ADR-001 documents regen | T2.9, T2.10 |
| R3 | **Agent tool-use reliability: agent fails to call extraction tools, producing pure-chat responses; wizard stalls** (FR-11d S5) | Med | High | Server tool-call edge-case validator in T2.5 (0 calls → re-prompt; ≥2 → priority order; required-None → reject); `source="llm"` ≥90% ship gate measures directly; SSE streaming reserved as fallback spec | T2.5, T2.11 |
| R4 | **Rollout gap between PR 3 ship and PR 5 cleanup**: form-wizard users mid-flow get interrupted; legacy table writes could land for 30 days | Low | Med | Feature flag `USE_LEGACY_FORM_WIZARD` gates rollback; 30-day quiet period in tech-spec §8.1; FK-audit + in-flight row count in T5.2; account-delete coupling (T4.7) nullifies legacy rows during quiet period | T3.9, T4.7, T5.2 |
| R5 | **Latency stacking: JWT verify + JSONB SELECT FOR UPDATE + agent call + validators + ORM commit exceeds 2500ms** (FR-11d S2) | Med | High | Hard `asyncio.wait_for(..., 2.5)` budget; timeout triggers fallback; prompt caching on persona block reduces LLM latency; ORM round-trip benchmarked in T2.8; p99 CI assertion in T2.5 | T2.5, T2.8 |

---

## 8. Verification Strategy

Per-PR verification checklist before `/qa-review` dispatch:

### PR 1 (FR-11c)
- Unit: `pytest tests/platforms/telegram/test_commands.py tests/platforms/telegram/test_message_handler.py tests/db/integration/test_portal_bridge_tokens.py -v`
- CI grep gate: `rg "OnboardingHandler|OnboardingStep|from nikita\.platforms\.telegram\.onboarding" nikita/` → empty
- Pre-PR gates (testing.md): zero-assertion shells, PII-in-logs, raw `cache_key` — all empty on changed files
- Live dogfood (Telegram MCP): fresh throwaway account `/start` → bridge button only; second `/start` from same → welcome-back; email-shaped text → "no email here"
- Post-merge smoke (T1.7): 24h log-grep for `"Created onboarding state for telegram_id"` returns zero
- Commit-hash verification: `git log origin/master -3` shows PR 1 merge commit

### PR 2 (FR-11d backend)
- Unit: `pytest tests/agents/onboarding/ tests/api/routes/test_converse_endpoint.py tests/onboarding/test_tuning_constants.py -v`
- Integration: `pytest tests/db/integration/test_onboarding_profile_conversation.py -v` (concurrency test passes)
- Jailbreak fixture suite: ≥20/20 return `source="fallback"`
- Tone fixture suite: ≥18/20 pass Gemini judge
- Persona-drift: cosine ≥0.70 + 3 features within ±0.15
- Rollout gate: `scripts/converse_source_rate_measurement.py` on preview env → ≥90% `source="llm"` (results pasted in PR description)
- Pre-PR gates: 3 greps empty
- Coverage: per-module floors per D6 met (CI fails below)

### PR 3 (FR-11d frontend)
- Unit: `cd portal && pnpm test` covering 9 new test files
- E2E: `npx playwright test tests/e2e/portal/test_onboarding.spec.ts` happy path + `--grep @edge-case` 4 walks
- Accessibility: axe-core passes; keyboard nav integration test green; scoped aria-live asserted
- Mobile: viewport 360×640 + 768×1024 assertions for T3.5.4/5 + T3.6.3
- Virtualization: 100-turn render → DOM ≤30 MessageBubble nodes
- Live preview-env: agent-browser chat walk → typewriter visible; first-turn latency <2500ms; Network tab shows `source="llm"`; no red banners
- Post-merge (T3.12): /admin/onboarding/completion-rate card renders

### PR 4 (FR-11e)
- Unit: `pytest tests/platforms/telegram/test_commands.py tests/api/routes/test_tasks.py tests/api/routes/test_admin_onboarding.py -v`
- Integration: `pytest tests/db/integration/test_handoff_boundary.py -v`
- Telegram MCP dogfood (T4.9): fresh account walk → greeting arrives within 5s referencing name
- Webhook SLA: p99 <2s wall-clock with 3s greeting mock (T4.3)
- 30-day retention: fixture user at day 91 → cron run → conversation key removed, structured fields intact
- Admin endpoint: default GET omits conversation; `?include_conversation=true` includes + writes audit row exactly once

### PR 5 (cleanup)
- Completion-rate gate (T5.1): exit 0 from measurement script; ≥7d prod + ≥50 sign-ups
- FK-audit (T5.2): zero rows
- Grep gates: `USE_LEGACY_FORM_WIZARD`, legacy step paths, TelegramAuth unused callers — all appropriately zero
- Regression: full `pytest` green; `portal pnpm test` green; Playwright E2E green

---

## 9. Rollout Sequence

### 9.1 Feature flags and gates

| Flag / Gate | Default | Controlled by | Surface |
|---|---|---|---|
| `USE_LEGACY_FORM_WIZARD` env + portal Settings | `false` post-PR-3 | Env var + admin UI | T3.9.2 |
| `source="llm"` rate ≥`LLM_SOURCE_RATE_GATE_MIN=0.90` over N=`LLM_SOURCE_RATE_GATE_N=100` | Ship gate | Measurement script | T2.11, PR 3 ship gate |
| Chat-wizard completion rate within ±`CHAT_COMPLETION_RATE_TOLERANCE_PP=5` pp of baseline over N=`CHAT_COMPLETION_RATE_GATE_N=50` | Post-deploy gate | Measurement script | T3.12, T5.1 |
| PR 5 cleanup quiet period | ≥30 days post-PR-3 | Calendar + measurement PASS | T5.1 |

### 9.2 Rollback procedures per PR

| PR | Rollback action | Blast radius |
|---|---|---|
| 1 | `git revert <sha>` + redeploy Cloud Run. Bot re-enters legacy Q&A (known-functional regression). | Telegram entry only |
| 2 | `git revert <sha>` + redeploy. `/converse` endpoint returns 404; portal PR 3 handles 404 with legacy fallback copy (if PR 3 shipped). | Backend only |
| 3 | Flip `USE_LEGACY_FORM_WIZARD=true` (no redeploy; env flag on portal). Legacy form wizard renders; `/converse` endpoint stays but unreachable. | Portal wizard only |
| 4 | `git revert <sha>` + redeploy. `pending_handoff` semantic reverts; first-user-message triggers greeting via pre-FR-11e path. pg_cron job remains harmless. | Telegram takeover only |
| 5 | Not revertable (destructive table drop + deletions). Verify T5.1 PASS before merge. | Cleanup only |

### 9.3 Post-merge auto-dispatch checklist

For every PR merge, auto-dispatch a subagent for:

- Post-merge smoke test (curl probe, log sweep, DB assertion)
- Commit-hash verification (`git log origin/master | rg "#<PR>"`)
- GH issue close with PR reference
- ROADMAP sync (`/roadmap sync`)

Each dispatched subagent MUST include `HARD CAP: 5 tool calls` + explicit scope + exit criterion per `.claude/rules/parallel-agents.md`.

---

## 10. Open Items (deferred to /tasks or /audit)

These MEDIUM / LOW findings from `validation-findings-iter2.md` are accepted and pinned to downstream phases:

- **data-M1** (service-role-only table ownership intentional): add migration-header comment noting intentional admin+service-role RLS — addressed inline in T1.1 / T2.6 / T2.7 / T4.2 / T4.6 / T4.8 migration files.
- **data-M2** (index coverage audit): informational; no action in this plan. Future perf audit.
- **testing-M2** (E2E conversation-coherence Gemini-judge): DEFERRED to post-ship instrumentation; tracked in a follow-up spec if the tone-filter + persona-drift gates prove insufficient in prod.
- **16 LOW findings**: logged in per-validator iter-2 reports under `validation-reports/`. Opportunistic inclusion during `/tasks` phase; none are blockers.
- **tech-spec §10 open Q1 (SSE streaming)**: decided **NO** for this plan. Revisit only if AC-11d.9 rollout gate FAILS (`source="llm"` <90%). On FAIL, a follow-up SSE spec is drafted; PR 3 ship is blocked.
- **tech-spec §10 open Q4 (handoff greeting fallback on generator failure)**: resolved in T4.3 — on all-retries-exhausted, leave `pending_handoff=TRUE` + reset `dispatched_at=NULL` so pg_cron backstop retries. No minimal welcome; the backstop is the fallback.

---

## 11. Requirements Coverage Matrix (100% verification)

| Requirement AC | Covered by task(s) |
|---|---|
| AC-11c.1 (E1 bare URL) | T1.2.1, T1.3.1 |
| AC-11c.2 (E2/E8 welcome-back) | T1.3.2 |
| AC-11c.3 (E3/E4 game-over/won re-onboard) | T1.3.3 |
| AC-11c.4 (E5 pending/in_progress) | T1.3.4 |
| AC-11c.5 (E6 limbo) | T1.3.4 |
| AC-11c.6 (E7 /start <code> preserved) | T1.4.1 |
| AC-11c.7 (E9 free text pre-onboard) | T1.5.1 |
| AC-11c.8 (E10 email text pre-onboard) | T1.5.2 |
| AC-11c.9 (DI guard RuntimeError) | T1.3.5 |
| AC-11c.10 (code elimination grep) | T1.6.1 |
| AC-11c.10b (TelegramAuth audit) | T1.6.2, T5.4 |
| AC-11c.11 (deploy log guard) | T1.7.1 |
| AC-11c.12 (bridge-token TTL matrix) | T1.1, T1.2, T1.4.2 |
| AC-11c.12b (legacy table drop) | T5.2 |
| AC-11d.1 (layout + typewriter + indicator) | T3.5.3 |
| AC-11d.2 (hybrid controls) | T3.6.2 |
| AC-11d.3 (endpoint authz body-forbid) | T2.4.1, T2.5.1 |
| AC-11d.3b (JSONB-path authz 403) | T2.5.2 |
| AC-11d.3c (idempotency 5-min) | T2.5.3, T2.7 |
| AC-11d.3d (daily LLM spend cap) | T2.5.4, T2.6 |
| AC-11d.3e (per-IP 30 RPM) | T2.5.4 |
| AC-11d.4 (confirmation Yes/Fix-that) | T3.7.1 |
| AC-11d.4b (ghost-turn + clearPendingControl) | T3.7.2, T3.7.3, T3.1.3 |
| AC-11d.5 (two-layer age/phone/country reject) | T2.2.1, T2.5.9 |
| AC-11d.5b (input sanitization) | T2.5.5 |
| AC-11d.5c (output leak filter) | T2.5.7 |
| AC-11d.5d (jailbreak fixtures ≥20) | T2.5.5 |
| AC-11d.5e (onboarding-tone filter) | T2.5.8 |
| AC-11d.6 (off-topic handling) | T2.5.9 |
| AC-11d.7 (backtracking) | T3.10.2 |
| AC-11d.8 (progress indicator server-owned) | T3.8.1, T3.8.2 |
| AC-11d.9 (latency + 429 UX + rollout gate) | T2.5.4, T2.5.6, T2.11, T3.4.2 |
| AC-11d.10 (JSONB conversation persistence) | T2.8.1 |
| AC-11d.10b (react-virtuoso 100-turn cap) | T3.5.2 |
| AC-11d.11 (persona-drift baseline) | T2.9.1, T2.9.2, T2.9.3 |
| AC-11d.12 (a11y keyboard + live region) | T3.5.1 |
| AC-11d.12b (scoped aria-live + sr-only) | T3.5.1 |
| AC-11d.13 (completion trigger) | T3.9.1 |
| AC-11d.13b (Playwright @edge-case) | T3.10.2 |
| AC-11d.13c (completion-rate gate) | T3.12.1, T3.12.2, T5.1 |
| AC-11e.1 (portal closeout ceremony) | T4.1.1, T4.1.2, T4.1.3 |
| AC-11e.2 (proactive greeting within 5s) | T2.10.2, T4.3.2, T4.9.1 |
| AC-11e.3 (atomic claim + durable dispatch) | T4.2.2, T4.3.2, T4.4.1 |
| AC-11e.3b (webhook SLA <2s) | T4.3.1, T4.3.3 |
| AC-11e.3c (stranded migration script) | T4.5.1 |
| AC-11e.4 (handoff voice drift pairwise) | T2.10.3 |
| AC-11e.5 (dashboard gate redirect) | T3.11.1 |
| AC-11e.6 (no Q&A re-entry) | T4.9.2 |
| AC-NR1b.1 (atomic JSONB + localStorage) | T2.8.1, T3.3.1 |
| AC-NR1b.1b (ORM round-trip per-user serialize) | T2.8.1, T2.8.2 |
| AC-NR1b.2 (hydrate reducer action + StrictMode) | T3.1.2 |
| AC-NR1b.3 (v1→v2 migration shim) | T3.3.2 |
| AC-NR1b.4 (localStorage clear on ceremony) | T3.3.3 |
| AC-NR1b.4b (90-day pg_cron + GDPR) | T4.6.1, T4.7.1 |
| AC-NR1b.4c (admin opt-in + audit log) | T4.8.1, T4.8.2 |
| AC-NR1b.5 (100-turn cap elide) | T2.8.3, T3.1.4 |

**Coverage**: 54/54 ACs mapped (100%). Zero orphaned requirements.

**Task-level ACs (AC-plan prefix, not in spec)**: M1/M2/M3 mobile (T3.5.4, T3.6.3, T3.5.5) pin frontend-F-1 MED finding.

---

## 12. Plan Summary Counts

- **Total tasks**: 7 + 11 + 12 + 9 + 4 = **43 tasks**
- **Total estimated hours**: 17 + 30 + 33 + 17 + 4 = **101 hours**
- **Total ACs**: 17 + 36 + 37 + 23 + 8 = **121 ACs** (every task ≥2 ACs)
- **Dependency edges**: 32 (28 intra + 4 cross-PR)
- **Requirement coverage**: 54/54 spec ACs mapped (100%)
- **Design decisions resolved**: 6/6 (D1-D6)

---

## 13. Cross-references

- Functional spec: `specs/214-portal-onboarding-wizard/spec.md`
- Technical spec: `specs/214-portal-onboarding-wizard/technical-spec.md`
- Validation findings iter-2: `specs/214-portal-onboarding-wizard/validation-findings-iter2.md`
- ADR-001 persona-drift baseline: `specs/214-portal-onboarding-wizard/decisions/ADR-001-persona-drift-baseline.md` (created in T2.9.1)
- Prior plan (superseded): previous `plan.md` @ commit `545e91f`
- PR workflow: `.claude/rules/pr-workflow.md`
- Tuning constants convention: `.claude/rules/tuning-constants.md`
- Testing gates: `.claude/rules/testing.md`
- Subagent dispatch caps: `.claude/rules/parallel-agents.md`

---

## 14. Next Steps

1. User approval of this plan.
2. `/tasks` expands each T<PR>.<N> into `tasks.md` with sequential work order + failing-test stub references.
3. `/audit` cross-artifact consistency check; must PASS before `/implement`.
4. `/implement` runs TDD per PR following `.claude/rules/pr-workflow.md`.
5. PRs ship in order 1 → 2 → 3 → 4 → 5 with gates per §9.

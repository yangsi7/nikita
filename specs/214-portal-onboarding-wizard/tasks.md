# Tasks: 214-portal-onboarding-wizard

**Generated**: 2026-04-15
**Feature**: 214 — Portal Onboarding Wizard ("The Dossier Form")
**Inputs**: [spec.md](./spec.md) (1013L), [plan.md](./plan.md)
**GATE 2**: PASS ✓ (absolute zero)

---

## Amendment: PR 1 — FR-11c Telegram→Portal Re-routing (branch `fix/spec-214-fr11c-telegram-to-portal`)

FR-11c sub-amendment adopted after the Chat-First amendment. Its job is to delete the 8-step Telegram Q&A and replace every new-user entry point with a one-button redirect to the portal onboarding wizard. Task IDs are tracked as T1.1–T1.6 (distinct from the D/A/B/C phase IDs below) because this sub-work predates the main 4-PR rollout.

- [x] **T1.1** Portal bridge token model + repo + migration — _commit `83978a9`_
  - AC-T1.1.1: `portal_bridge_tokens` table, TTL + single-use invariants
  - AC-T1.1.2: `PortalBridgeTokenRepository.mint/consume/revoke_all_for_user`
  - AC-T1.1.3: Atomic consume (UPDATE … WHERE … RETURNING)
- [x] **T1.2** `generate_portal_bridge_url` + E1 bare-URL path — _commit `6a8b4b8`_
  - AC-T1.2.1: URL mint via repo; bare `/onboarding/auth` path honored
- [x] **T1.3** Rewrite `_handle_start` for FR-11c routing — _commit `db19ef0`_
  - AC-T1.3.1: New-user no-payload → portal button (no email OTP fall-through)
  - AC-T1.3.2: `/start <payload>` deep-link binding preserved (GH #321)
- [x] **T1.4** `/start <code>` payload preservation + password-reset revocation hook — _commits `1d41407`_ (tests) _+ `1aaaa59`_ (impl)
  - AC-T1.4.1: Regression suite in `tests/platforms/telegram/test_commands.py::TestHandleStartWithPayload` (6 tests) continues to pass unchanged.
  - AC-T1.4.2: Bearer-auth `POST /api/v1/internal/auth/password-reset-hook` wired; `PortalBridgeTokenRepository.revoke_all_for_user` called on Supabase password-reset webhook.
- [x] **T1.5** Pre-onboard gate for free text + email — _commit `1febff0`_
  - AC-T1.5.1: Pre-onboard user sending free text / email gets the portal redirect, not the Q&A.
- [x] **T1.6** Legacy Q&A package + tests deletion + DI cleanup — _commits `00990ca`_ (tests) _+ `47fb834`_ (impl) _+ `84d74c5`_ (sweep)
  - AC-T1.6.1: `nikita/platforms/telegram/onboarding/` package deleted. Code-level grep returns zero matches. (Historical docstring mentions were also swept for clarity, though the test itself only gates on executable references.)
  - AC-T1.6.2: Disposition audit of `TelegramAuth | otp_handler | email_otp | user_onboarding_state` produced; see PR description.
  - AC-T1.6.3: `onboarding_handler` DI removed from `get_otp_handler`, `receive_webhook`, and `MessageHandler.__init__`. No refs remain in `platforms/telegram/` outside historical comments.
- [ ] **T1.7** Post-merge smoke test (deploy + live probe). Deferred to after PR 1 merges.

**Organization**: 4 phases mapping 1:1 to PRs (D→A→B→C). All user stories are P1; PR boundary serves as the natural delivery checkpoint. Each PR is independently QA-reviewed and merged before the next.

**Format**: `[ID] [P?] [US?] Description`
- `[P]` = parallel-safe (different files, no dependencies)
- `[USn]` = user-story tag (US-1..US-6); omitted for foundational/setup tasks
- RED/GREEN split commits per Article X (two commits minimum per user story)

---

## Conventions (All Phases)

- **Intelligence-first**: `project-intel.mjs --symbols <file>` BEFORE editing any existing file
- **TDD**: tests FIRST (RED), implementation SECOND (GREEN), never reversed
- **File-test pair [P]**: tests for different files are [P]; tests for same file are sequential
- **Commit cadence**: ≥2 commits per user story (RED tests + GREEN impl, optional REFACTOR)
- **Branch naming**: `feat/214-{pr-letter}-{short-name}` per PR
- **Pre-QA grep gates** (per `.claude/rules/testing.md`): zero-assertion shells, PII leakage, raw cache_key in logs

---

## Phase 1 — Setup (Shared Infrastructure)

**Purpose**: Project initialization + branch setup. No new infrastructure; all foundations inherited from Spec 213.

**Intelligence Query**:
```bash
project-intel.mjs --overview --json
project-intel.mjs --search "OnboardingV2ProfileResponse" --json
project-intel.mjs --search "PortalOnboardingFacade" --json
```

- [ ] T001 Verify Spec 213 artifacts present (`contracts.py`, `tuning.py`, `portal_onboarding.py` routes+facade, `BackstoryCacheRepository`). Non-editing sanity check.
- [ ] T002 [P] Verify Cloud Run revision `nikita-api-00250-4mm` serving 100% traffic (precondition for PR 214-D deploy).
- [ ] T003 [P] Verify `portal/` builds clean on master (baseline: `cd portal && npm run build`).

**Checkpoint**: Predecessor state verified. Ready for PR 214-D.

---

## Phase 2 — PR 214-D: Backend Sub-Amendment (Foundational)

**Branch**: `feat/214-d-backend-chosen-option`
**Purpose**: Ship new endpoint + additive contract extension so TypeScript mirror (PR-A) has a merged source of truth.
**Scope**: Backend-only. No portal changes.
**LOC target**: ≤250 soft cap.

**Intelligence Queries**:
```bash
project-intel.mjs --symbols nikita/onboarding/contracts.py --json
project-intel.mjs --symbols nikita/onboarding/tuning.py --json
project-intel.mjs --symbols nikita/api/middleware/rate_limit.py --json
project-intel.mjs --symbols nikita/api/routes/portal_onboarding.py --json
project-intel.mjs --symbols nikita/services/portal_onboarding.py --json
```

### Tests for PR 214-D ⚠️ WRITE FIRST (RED)

- [ ] T010 [P] [US-6] RED: `tests/services/test_portal_onboarding_facade.py` **NEW FILE** — unit tests for `set_chosen_option`:
  - `test_set_chosen_option_cache_key_mismatch_raises_403`
  - `test_set_chosen_option_unknown_option_id_raises_409`
  - `test_set_chosen_option_missing_cache_row_raises_404`
  - `test_set_chosen_option_success_writes_full_snapshot` (all 6 `BackstoryOption` fields)
  - `test_set_chosen_option_emits_backstory_chosen_event`
  - `test_set_chosen_option_idempotent_same_choice` (same option_id → same snapshot)
  - **Tests**: AC-10.1, AC-10.2, AC-10.3, AC-10.4, AC-10.5, AC-10.6
  - **Verify**: all FAIL before T020

- [ ] T011 [P] [US-6] RED: Extend `tests/api/routes/test_portal_onboarding.py` with PUT-endpoint tests:
  - `test_put_chosen_option_cross_user_returns_403` (AC-10.1)
  - `test_put_chosen_option_stale_cache_key_returns_404` (AC-10.2)
  - `test_put_chosen_option_unknown_option_id_returns_409` (AC-10.4)
  - `test_put_chosen_option_happy_path_writes_snapshot` (AC-10.5)
  - `test_put_chosen_option_response_has_no_pii_substrings` (negative assertion — no name/age/occupation/phone/city in 403/422/409/404 bodies)
  - `test_put_chosen_option_rate_limit_429_includes_retry_after` (AC-10.7)
  - `test_pipeline_ready_wizard_step_passthrough` (AC-10.8 — reads from `onboarding_profile.wizard_step` JSONB)
  - `test_pipeline_ready_rate_limit_429_retry_after_60` (AC-5.6)
  - **Verify**: all FAIL before T020..T024

- [ ] T012 [P] RED: Extend `tests/onboarding/test_contracts.py` with additive extension assertions:
  - `test_backstory_choice_request_round_trip` (JSON → model → JSON equality)
  - `test_pipeline_ready_response_wizard_step_optional` (None default; Field constraints ge=1, le=11)
  - **Verify**: FAIL before T020

**Commit RED**: `test(214-d): failing tests for chosen-option endpoint + wizard_step`

### Implementation for PR 214-D (GREEN)

- [ ] T020 [US-6] Add `BackstoryChoiceRequest` Pydantic model + extend `PipelineReadyResponse` with `wizard_step: int | None = Field(default=None, ge=1, le=11)` in `nikita/onboarding/contracts.py`. Update module docstring noting additive Spec 214 extension.
  - **Tests**: T012 passes
  - **Evidence**: plan.md §4 PR-D; spec FR-10.1 + FR-10.2

- [ ] T021 [P] Add `CHOICE_RATE_LIMIT_PER_MIN: Final[int] = 10` and `PIPELINE_POLL_RATE_LIMIT_PER_MIN: Final[int] = 30` to `nikita/onboarding/tuning.py` with docstrings referencing GH issue + rationale (per `.claude/rules/tuning-constants.md`).
  - **Evidence**: spec FR-10.1 rate-limiting block

- [ ] T022 Add `_ChoiceRateLimiter` + `choice_rate_limit` dependency AND `_PipelineReadyRateLimiter` + `pipeline_ready_rate_limit` dependency in `nikita/api/middleware/rate_limit.py`. Both subclasses override `_get_minute_window()` AND `_get_day_window()` with prefix (`choice:`/`poll:`) for isolation. 429 responses include `Retry-After: 60` header.
  - **Dependencies**: T021
  - **Tests**: T011 (Retry-After assertions pass)
  - **Evidence**: spec FR-10.1 `_ChoiceRateLimiter` pseudocode

- [ ] T023 [US-6] Implement `PortalOnboardingFacade.set_chosen_option(user_id, chosen_option_id, cache_key, session) -> BackstoryOption` in `nikita/services/portal_onboarding.py`. Implements SimpleNamespace bridge for `compute_backstory_cache_key` (duck-read `location_city`→`city`, `drug_tolerance`→`darkness_level`, etc. from `users.onboarding_profile` JSONB). Recompute + compare → 403 on mismatch. Load `BackstoryCacheRepository.get(cache_key)` → 404. Validate `chosen_option_id ∈ scenarios` → 409. Write full snapshot to `onboarding_profile.chosen_option`. Emit `onboarding.backstory_chosen` structured event.
  - **Dependencies**: T020
  - **Tests**: T010 all pass
  - **Evidence**: spec FR-10.1 facade docstring (iter-5 final)

- [ ] T024 [US-6] Add `PUT /profile/chosen-option` handler in `nikita/api/routes/portal_onboarding.py`. Dependency chain: `get_current_user_id`, `get_async_session`, `choice_rate_limit`. Call `PortalOnboardingFacade().set_chosen_option(...)` (no `__init__`, session as method param). Return `OnboardingV2ProfileResponse` with `chosen_option` populated + `backstory_options=[]` + poll metadata. Extend `get_pipeline_ready` to read `onboarding_profile.wizard_step` JSONB and apply `pipeline_ready_rate_limit` dependency.
  - **Dependencies**: T020, T022, T023
  - **Tests**: T011 all pass
  - **Evidence**: spec FR-10.1 PUT handler pseudocode

- [ ] T025 [P] Verify pre-QA grep gates (zero-assertion shells, PII in logs, raw cache_key not hashed in logs).

**Commit GREEN**: `feat(214-d): PUT /profile/chosen-option + wizard_step extension`

### Verification for PR 214-D

- [ ] T030 Run `pytest tests/services/test_portal_onboarding_facade.py tests/api/routes/test_portal_onboarding.py tests/onboarding/test_contracts.py -x -v` → all green
- [ ] T031 Run full suite `pytest tests/ -x -q --timeout 30 -m "not integration and not slow and not e2e"` → baseline 6153+ pass / 0 fail
- [ ] T032 `gh pr create --title "feat(214-d): chosen-option endpoint + wizard_step (Spec 214 PR 214-D)"` → `/qa-review --pr N` loop → absolute-zero → squash merge
- [ ] T033 Auto-dispatch smoke subagent post-merge: probe `PUT /api/v1/onboarding/profile/chosen-option` (expect 422 for missing fields; confirms route wired), `GET /pipeline-ready/{user_id}` includes `wizard_step` in response shape, Cloud Run deploy `nikita-api-00251-*` healthy.
- [ ] T034 Update ROADMAP.md `last_deploy` + `last_revision`.

**Checkpoint**: Backend endpoint live. TS mirror can safely reference `BackstoryChoiceRequest` + `wizard_step`.

---

## Phase 3 — PR 214-A: Portal Foundation (Plumbing, No UI)

**Branch**: `feat/214-a-portal-foundation`
**Purpose**: TypeScript contracts mirror + state machine + persistence + hooks. Zero visible UI changes.
**Scope**: Portal foundation only.
**LOC target**: ≤350 soft cap.
**Blocks**: PR-D must be merged first.

**Intelligence Queries**:
```bash
project-intel.mjs --symbols portal/src/lib/api/client.ts --json
project-intel.mjs --search "apiClient" --type ts --json
project-intel.mjs --symbols portal/src/app/onboarding/page.tsx --json
```

### Tests for PR 214-A ⚠️ WRITE FIRST (RED)

- [ ] T100 [P] RED: `portal/src/app/onboarding/state/__tests__/WizardStateMachine.test.ts` — transition guard rejects out-of-order; valid step 3→4→5→... sequence accepted; backwards edit from step 8 allowed
  - **Tests**: AC-NR1.3, AC-8.1 (step order enforcement)
- [ ] T101 [P] RED: `portal/src/app/onboarding/state/__tests__/WizardPersistence.test.ts` — user-scoped key `nikita_wizard_{user_id}`; version-byte mismatch → clear; round-trip `cache_key` + `chosen_option_id`
  - **Tests**: AC-NR1.1, AC-NR1.2, AC-NR1.4
- [ ] T102 [P] RED: `portal/src/app/onboarding/hooks/__tests__/useOnboardingAPI.test.ts` — `withRetry` 3-attempt exp backoff (500/1000/2000ms); POST excluded from retry; `selectBackstory(id, cache_key)` wraps PUT
  - **Tests**: AC-4.2, AC-6.2, AC-10.1
- [ ] T103 [P] RED: `portal/src/app/onboarding/hooks/__tests__/usePipelineReady.test.ts` — poll interval + timeout driven by server response (`poll_interval_seconds`, `poll_max_wait_seconds` — 20s per `PIPELINE_GATE_MAX_WAIT_S`); degraded after timeout; rate-limit 429 surfaces error
  - **Tests**: AC-5.1, AC-5.2, AC-5.3, AC-5.6

**Commit RED**: `test(214-a): failing tests for wizard foundation`

### Implementation for PR 214-A (GREEN)

- [ ] T110 [US-3] Create `portal/src/app/onboarding/types/contracts.ts` — TS mirror per spec Appendix B (`BackstoryOption`, `OnboardingV2ProfileRequest/Response`, `PipelineReadyResponse` incl. `wizard_step`, `BackstoryPreviewRequest/Response`, `BackstoryChoiceRequest`, `PipelineReadyState`, `ErrorResponse`). Interface-only — no runtime validation.
  - **Evidence**: spec Appendix B canonical mapping

- [ ] T111 [P] [US-3] Create `portal/src/app/onboarding/types/wizard.ts` — `WizardStep` enum (3..11), `WizardPersistedState`, `WizardFormValues`
  - **Evidence**: spec FR-1 step flow

- [ ] T112 [US-3] Create `portal/src/app/onboarding/state/WizardStateMachine.ts` — transition map + guard. `canTransition(from, to)`, `nextStep(current, formValues)`.
  - **Tests**: T100 passes

- [ ] T113 [US-3] Create `portal/src/app/onboarding/state/WizardPersistence.ts` — user-scoped localStorage RWX. Version byte (`WIZARD_STATE_VERSION = 1`). Writes `cache_key` alongside `chosen_option_id` when card selected.
  - **Tests**: T101 passes
  - **Evidence**: spec NR-1

- [ ] T114 [US-1] Extend `portal/src/lib/api/client.ts` with `api.patch<T>(path, body)` method matching existing `get/post/put` pattern.
  - **Evidence**: spec PR 214-A artifact table

- [ ] T115 [US-1] Create `portal/src/app/onboarding/hooks/use-onboarding-api.ts` — `useOnboardingAPI()` returning `previewBackstory`, `submitProfile` (POST /onboarding/profile), `patchProfile` (PATCH /onboarding/profile), `selectBackstory(option_id, cache_key)` (PUT /profile/chosen-option). Shared `withRetry` helper (3-attempt exp backoff, POST excluded).
  - **Dependencies**: T110, T114
  - **Tests**: T102 passes

- [ ] T116 [P] [US-1] Create `portal/src/app/onboarding/hooks/use-pipeline-ready.ts` — `useOnboardingPipelineReady(userId)` reading `poll_interval_seconds` + `poll_max_wait_seconds` from server response (authoritative; 20s timeout per `PIPELINE_GATE_MAX_WAIT_S`); 429 error surface.
  - **Dependencies**: T110
  - **Tests**: T103 passes

- [ ] T117 [P] [US-4] Create `portal/src/app/onboarding/constants/supported-phone-countries.ts` — ElevenLabs/Twilio supported country codes array.
  - **Evidence**: spec NR-3

- [ ] T118 [P] Update `portal/package.json` — add `qrcode.react`, `libphonenumber-js`; add `"prebuild": "tsc --noEmit"` script.
  - **Evidence**: spec NFR-006 Vercel CI gate

**Commit GREEN**: `feat(214-a): portal foundation — types, state, hooks, persistence`

### Verification for PR 214-A

- [ ] T120 `cd portal && npm run prebuild && npm test -- --testPathPattern="onboarding"` → all green
- [ ] T121 `gh pr create --title "feat(214-a): portal onboarding foundation (Spec 214 PR 214-A)"` → `/qa-review --pr N` loop → absolute-zero → squash merge
- [ ] T122 Vercel preview deploy auto-triggered on merge; verify build green

**Checkpoint**: Portal foundation ready. PR-B and PR-C can start author-parallel.

---

## Phase 4 — PR 214-B: Step Components + Dossier Styling

**Branch**: `feat/214-b-step-components` (dispatched via worktree agent)
**Purpose**: All 9 visible wizard step components + dossier aesthetic.
**Scope**: UI components only; orchestrator + shared components.
**LOC target**: ≤400 soft cap.
**Parallel with**: PR 214-C after PR-A merges.

**Intelligence Queries**:
```bash
project-intel.mjs --symbols portal/src/components/landing/system-terminal.tsx --json
project-intel.mjs --search "aurora-orbs" --json
project-intel.mjs --search "OnboardingCinematic" --json
```

### Tests for PR 214-B ⚠️ WRITE FIRST (RED)

- [ ] T200 [P] [US-1] RED: `portal/src/app/onboarding/steps/__tests__/DossierHeader.test.tsx` — renders classified-file header, metric bars
- [ ] T201 [P] [US-1] RED: `portal/src/app/onboarding/steps/__tests__/LocationStep.test.tsx` — city input + inline venue preview on blur
- [ ] T202 [P] [US-1] RED: `portal/src/app/onboarding/steps/__tests__/SceneStep.test.tsx` — button grid radiogroup a11y (role=radiogroup, role=radio, roving tabindex)
- [ ] T203 [P] [US-1] RED: `portal/src/app/onboarding/steps/__tests__/DarknessStep.test.tsx` — slider value ↔ live Nikita quote mapping
- [ ] T204 [P] [US-1] RED: `portal/src/app/onboarding/steps/__tests__/IdentityStep.test.tsx` — name/age/occupation validation (age ≥18, occupation min_length=1)
- [ ] T205 [P] [US-6] RED: `portal/src/app/onboarding/steps/__tests__/BackstoryReveal.test.tsx` — loading state, 3-card render, card selection calls `selectBackstory`, degraded path
- [ ] T206 [P] [US-4] RED: `portal/src/app/onboarding/steps/__tests__/PhoneStep.test.tsx` — country pre-flight validation, voice/text binary choice
- [ ] T207 [P] [US-1] RED: `portal/src/app/onboarding/steps/__tests__/PipelineGate.test.tsx` — poll state UI, `CLEARED` stamp on ready, `PROVISIONAL — CLEARED` on degraded, reduced-motion guard
- [ ] T208 [P] [US-2,US-5] RED: `portal/src/app/onboarding/steps/__tests__/HandoffStep.test.tsx` — Telegram CTA, voice ring, QRHandoff desktop-only render, voice-fallback-to-Telegram when agent unavailable
- [ ] T209 [P] [US-2] RED: `portal/src/app/onboarding/components/__tests__/QRHandoff.test.tsx` — desktop-only render (mobile → null), canvas/SVG mode, data URL
- [ ] T210 [P] [US-1] RED: `portal/src/app/onboarding/components/__tests__/DossierStamp.test.tsx` — CLEARED typewriter reveal, ANALYZED stamp-rotate, `prefers-reduced-motion` skips animation
- [ ] T211 [P] RED: `portal/src/app/onboarding/components/__tests__/WizardProgress.test.tsx` — "FIELD N OF 7" renders correctly

**Commit RED**: `test(214-b): failing tests for 9 step components + DossierStamp + QRHandoff`

### Implementation for PR 214-B (GREEN)

- [ ] T220 [US-1] Create `portal/src/app/onboarding/onboarding-wizard.tsx` orchestrator — consumes state machine + persistence + hooks; renders current step. **DELETE** `portal/src/app/onboarding/onboarding-cinematic.tsx` and its `sections/` subdirectory.
  - **Dependencies**: (PR-A merged)

- [ ] T221 [P] [US-1] `DossierHeader.tsx` — Tests: T200
- [ ] T222 [P] [US-1] `LocationStep.tsx` — Tests: T201
- [ ] T223 [P] [US-1] `SceneStep.tsx` (WAI-ARIA radiogroup) — Tests: T202
- [ ] T224 [P] [US-1] `DarknessStep.tsx` (EdginessSlider) — Tests: T203
- [ ] T225 [P] [US-1] `IdentityStep.tsx` — Tests: T204
- [ ] T226 [US-6] `BackstoryReveal.tsx` (BackstoryChooser, 3-card layout, degraded path) — Tests: T205
- [ ] T227 [P] [US-4] `PhoneStep.tsx` — Tests: T206
- [ ] T228 [US-1] `PipelineGate.tsx` — Tests: T207
- [ ] T229 [US-2,US-5] `HandoffStep.tsx` — Tests: T208
- [ ] T230 [P] [US-2] `components/QRHandoff.tsx` — Tests: T209
- [ ] T231 [P] [US-1] `components/DossierStamp.tsx` (typewriter + stamp-rotate + reduced-motion guard; import system-terminal.tsx timing constant if exists) — Tests: T210
- [ ] T232 [P] [US-1] `components/WizardProgress.tsx` — Tests: T211
- [ ] T233 [P] Create `docs/content/wizard-copy.md` — canonical Nikita copy reference for ALL wizard screens (per FR-3 zero-SaaS-copy rule)

**Commit GREEN**: `feat(214-b): 9 wizard step components + dossier aesthetic`

### Verification for PR 214-B

- [ ] T240 `cd portal && npm test -- --testPathPattern="onboarding/(steps|components)"` → all green
- [ ] T241 `npm run prebuild` + `npm run build` → clean
- [ ] T242 `gh pr create` → `/qa-review --pr N` loop → absolute-zero → squash merge
- [ ] T243 Regression check: US-1 walkthrough on Vercel preview (dogfood via agent-browser)

**Checkpoint**: Visible wizard rendering end-to-end. Ready for E2E.

---

## Phase 5 — PR 214-C: E2E + Build Chain + Vercel Deploy

**Branch**: `feat/214-c-e2e-deploy` (dispatched via worktree agent, parallel with PR-B)
**Purpose**: E2E tests, schema extensions, page wiring, deploy.
**Scope**: Integration + deployment.
**LOC target**: ≤200 soft cap.

**Intelligence Queries**:
```bash
project-intel.mjs --symbols portal/src/app/onboarding/schemas.ts --json
project-intel.mjs --symbols portal/src/app/onboarding/page.tsx --json
project-intel.mjs --symbols portal/src/lib/supabase/middleware.ts --json
```

### Tests for PR 214-C ⚠️ WRITE FIRST (RED)

- [ ] T300 [P] [US-1,US-6] RED: `portal/e2e/onboarding-wizard.spec.ts` — happy-path walkthrough on Chrome desktop viewport. Assertions:
  - All 11 steps render in order
  - `PUT /profile/chosen-option` called with `{chosen_option_id, cache_key}`
  - `GET /pipeline-ready/{user_id}` polled until `ready`
  - **US-6 continuity**: First Telegram bot message references chosen venue + hook (dogfood via Telegram MCP)
- [ ] T301 [P] [US-3] RED: `portal/e2e/onboarding-resume.spec.ts` — abandon mid-wizard → reload with `?resume=true` → resumes exact step
- [ ] T302 [P] [US-4,US-5] RED: `portal/e2e/onboarding-phone-country.spec.ts` — unsupported country code blocks voice path; voice-unavailable → Telegram fallback UI visible

**Commit RED**: `test(214-c): failing E2E specs for wizard, resume, phone`

### Implementation for PR 214-C (GREEN)

- [ ] T310 [P] [US-1] Extend `portal/src/app/onboarding/schemas.ts` with Zod validators for `name` (min 1), `age` (int ≥18), `occupation` (min 1), `wizard_step` (int 1..11 optional).
  - **Evidence**: spec FR-7, NR-2

- [ ] T311 [US-1] Update `portal/src/app/onboarding/page.tsx` — render `<OnboardingWizard />` instead of `<OnboardingCinematic />`; detect `?resume=true` param; use `supabase.auth.getUser()` for auth decisions (NOT `getSession()` — prevents Spec 081 session-spoofing regression); use `getSession()` ONLY for JWT extraction.
  - **Tests**: T301 passes
  - **Note** (PR #298 QA iter-2): the `page.tsx` render-target swap (Cinematic → OnboardingWizard) was pulled forward to PR 214-B (commit 52d0ef6) so the Vercel preview is user-testable immediately after PR-B merges — per the project's stated "first testable moment = PR-B merged" North Star. PR 214-C inherits the already-flipped `page.tsx`; this row now only covers the `?resume=true` query-param branch + `getUser()`/`getSession()` auth wiring that still lives on `feat/214-c-e2e-deploy`.

- [ ] T312 [P] [US-1] Update `portal/src/lib/supabase/middleware.ts` — add `pathname.startsWith("/onboarding/auth")` to public-route allowlist alongside `/login`, `/auth/*`.
  - **Evidence**: spec PR 214-C artifact table

- [ ] T313 [P] [US-1] Update `portal/src/app/onboarding/loading.tsx` — Nikita-voiced copy ("ACCESSING FILE..." + dossier skeleton) per FR-3.
  - **Evidence**: `docs/content/wizard-copy.md` (T233)

- [ ] T314 [P] Create `docs/content/magic-link-email.md` — Nikita-voiced Supabase magic-link copy for operator to paste into Supabase Dashboard. Manual infra task logged in PR 214-C checklist.

- [ ] T315 Pre-deploy verification: `cat portal/vercel.json | grep -A5 img-src` → confirm `data:` and `blob:` allowed for qrcode.react canvas/SVG output.

**Commit GREEN**: `feat(214-c): E2E specs, page wiring, magic-link copy`

### Verification for PR 214-C

- [ ] T320 `cd portal && npx playwright test` → 3 new specs green
- [ ] T321 `npm run prebuild` + `npm run build` → clean
- [ ] T322 `gh pr create` → `/qa-review --pr N` loop → absolute-zero → squash merge
- [ ] T323 Production deploy: `cd portal && npm run build && vercel --prod` (per spec PR 214-C)
- [ ] T324 Auto-dispatch post-deploy smoke subagent: probe prod Vercel URL for `/onboarding`, verify Lighthouse a11y ≥95, run Playwright E2E against prod URL, dogfood full US-1 walkthrough ending in Nikita chat message referencing chosen backstory venue/hook (US-6 SC-3).
- [ ] T325 Update ROADMAP.md: Spec 214 → `status: COMPLETE`; log deploy row.
- [ ] T326 Close Spec 214 GH issue (if any) with "Fixed in PR #{D-num}, #{A-num}, #{B-num}, #{C-num}".

**Checkpoint**: Full wizard live in production. Success criteria SC-1..SC-4 verified.

---

## Phase 6 — Polish & Cross-Cutting (Post-Deploy)

- [ ] T400 [P] Monitor Cloud Run error log 7 days post-deploy for 403/404/409 spike on `PUT /profile/chosen-option` (indicates cache_key drift regression)
- [ ] T401 [P] Monitor Sentry (if wired) / Vercel Analytics for wizard abandonment rate vs predecessor (SC-1 validation)
- [ ] T402 Write session report to `docs/session-reports/214-portal-onboarding-wizard-deploy.md` — before/after abandonment rates, first-message continuity sample
- [ ] T403 Auto-memory reflection: save any new patterns learned (e.g., cache_key recompute bridge, WAI-ARIA radiogroup setup) to `~/.claude/projects/-Users-yangsim-Nanoleq-sideProjects-nikita/memory/`

**Final Verification**: Run `/e2e full` — 13 epics, 363 scenarios regression sweep.

---

## Dependencies & Execution Order

| Phase | Branch | Depends On | Parallel? |
|-------|--------|-----------|-----------|
| 1 Setup | master | — | T002, T003 [P] |
| 2 PR 214-D | feat/214-d | Phase 1 | T010, T011, T012 [P] RED; T021, T025 [P] GREEN |
| 3 PR 214-A | feat/214-a | PR-D merged | T100..T103 [P] RED; T111, T116..T118 [P] GREEN |
| 4 PR 214-B | feat/214-b | PR-A merged | T200..T211 [P] RED; T221..T225, T230..T233 [P] GREEN |
| 5 PR 214-C | feat/214-c | PR-A merged (**parallel worktree with PR-B**) | T300..T302 [P] RED; T310, T312..T314 [P] GREEN |
| 6 Polish | master | PR-C deployed | T400, T401 [P] |

### Worktree Parallelization (per `.claude/rules/parallel-agents.md`)

After PR-A merges:
- Dispatch implementor agent for PR-B in `feat/214-b` worktree
- Dispatch implementor agent for PR-C in `feat/214-c` worktree
- Main orchestrator: verify branches with `git branch --show-current` post-completion; cross-ref `git log` to catch cross-contamination; create PRs sequentially; run `/qa-review --pr N` per branch.

---

## Intelligence-First Checklist

- [x] `project-intel.mjs --overview` in Phase 1
- [ ] `project-intel.mjs --symbols` before editing each existing file (Phases 2-5)
- [ ] `project-intel.mjs --dependencies` before modifying `contracts.py`, `portal_onboarding.py`, `api/client.ts`
- [ ] Ref MCP for `libphonenumber-js` and `qrcode.react` if usage unclear

---

## Test-First Checklist (Article III)

For every `[US*]`-tagged implementation task:
- [x] ≥2 ACs defined (inherited from spec)
- [x] RED commit present before GREEN
- [ ] Tests FAIL verified before impl (during execution)
- [ ] Tests PASS verified after impl
- [ ] All ACs satisfied per US-level verification gates

---

## CoD^Σ Evidence Requirements

All implementation tasks trace to:
- **Spec**: section ref (e.g., "spec FR-10.1 handler pseudocode")
- **Plan**: section ref (e.g., "plan.md §4 PR-D")
- **Contract**: Appendix B canonical mapping or FROZEN contracts
- **Prior art**: `file:line` via intel query (e.g., `system-terminal.tsx:L42` for typewriter timing)

---

## Complexity Tracking (populated during implementation)

| Task ID | Original Est | Actual | Factor | Notes |
|---------|-------------|--------|--------|-------|
| (to be filled in by implementor) | | | | |

---

## Notes

- **[P]**: different file, no shared dependency — safe for parallel execution
- **[US*]**: traces task to user story for spec→code traceability
- **TDD order**: T010..T012 → T020..T025 (PR-D); T100..T103 → T110..T118 (PR-A); T200..T211 → T220..T233 (PR-B); T300..T302 → T310..T315 (PR-C)
- **Branch cleanup**: delete feature branch after merge; worktree auto-clean if no changes
- **Anti-patterns**: zero-assertion test shells (`.claude/rules/testing.md`), PII in logs, bare magic numbers (tuning-constants rule)

---

**Generated by**: Phase 6 /tasks command
**Next step**: `/audit 214` — validates cross-artifact consistency before implementation can proceed

# Planning Brief: Onboarding Overhaul — Backend Foundation + Portal Wizard Redesign

## Meta
- **Date**: 2026-04-14
- **Approach selected**: C (Backend-first → Portal-UX) — expert panel vote 2-1
- **Decomposition**: 2 SDD specs (Spec 213 backend, Spec 214 portal UX) + 1 recovery PR
- **Status**: PROPOSED — awaiting `/feature` invocation

## Problem

Portal onboarding is structurally broken + aesthetically downgraded. User reports "5 → 1 experience" + Telegram evidence: Nikita opens with generic meta-message, then denies saying it when user quotes her back — zero conversation continuity. Four structural bugs + lost engagement features + cheap UI compared to landing page.

**Why now**: PR #273 (commit `350a717` / merge `70dff5c`) fixed 4 of the structural bugs but was **force-push-wiped** from master during Spec 212 recovery. Current master tip `87938db` does NOT contain any of #273's fixes. Production is serving the broken code.

## Confirmed Requirements

1. **R1 — Recover PR #273**: 4 structural bugfixes (pipeline bootstrap seed, profile JSONB persistence, conversation continuity, voice-path pipeline gap). 7 files, +495/-18 LOC, clean cherry-pick from `origin/fix/onboarding-pipeline-bootstrap`.
2. **R2 — Expand profile fields across THREE layers** (critical — devil's advocate C1/C2):
   - **R2a DB migration**: add nullable columns `name TEXT`, `occupation TEXT`, `age SMALLINT` to `user_profiles` table (`nikita/db/models/profile.py`). Nullable so existing users don't break. RLS: user can read/write own row only.
   - **R2b Pydantic domain model**: add `name`, `age` fields to `UserOnboardingProfile` (`nikita/onboarding/models.py:76`) — `occupation` already exists. Update `ProfileFieldUpdate.validate_field_name` allow-list at `:204-219`.
   - **R2c API request schema**: extend `PortalProfileRequest` (`nikita/api/routes/onboarding.py:647`) with `name`, `age`, `occupation` optional fields. Wire into `_trigger_portal_handoff` profile construction.
   - **Restored by #273** (NOT net-new — comes back via cherry-pick): `city`, `social_scene`, `life_stage`, `interest`, `age` on `UserOnboardingProfile`.
   - **Net-new in Spec 213**: `name` (both layers), `age` + `occupation` (DB columns), PortalProfileRequest extension.
3. **R3 — Wire engagement services to portal**: `VenueResearchService.research_venues(city, scene)` + `BackstoryGeneratorService.generate_scenarios(profile, venues)` exist in `nikita/services/` but are Telegram-only. Must plumb to portal submit path.
4. **R4 — Pipeline readiness gate**: User cannot interact with Nikita until pipeline bootstrap completes. Requires `/pipeline-ready` poll or SSE endpoint + UI spinner with timeout.
5. **R5 — Portal wizard redesign**: One-thing-at-a-time step flow (not scroll-snap). Match landing aesthetic (`text-[clamp(3rem,7vw,6rem)]`, `font-black`, `tracking-tighter`, void-ambient, glass cards, rose primary `oklch(0.75 0.15 350)`, aurora-orbs, falling-pattern).
6. **R6 — Progressive game-element introduction**: During onboarding, reveal scoring, chapters, friends (from backstory) — make the game start during onboarding, not after.
7. **R7 — Dynamic first message**: First Telegram message to use ALL collected data (city, scene, occupation, backstory scenario, selected friends).

8. **R8 — Conversation continuity (user's #1 complaint)**: "Nikita denies sending the first message when user quotes her back." Fix path:
   - Cherry-pick 350a717 restores `_seed_conversation()` which creates a `Conversation` row with `messages[0] = {role: "assistant", content: first_message}` BEFORE the user's first reply.
   - **Acceptance criterion**: after onboarding, user replies with the exact first-message text; Nikita's next response acknowledges (does not deny) the prior turn. Testable via E2E.
   - This is a pipeline memory/history problem, not a first-message-generation problem. R7 (dynamic message) and R8 (continuity) are independent — both must be verified.

### Type-layer disambiguation (load-bearing)
- `UserOnboardingProfile` = Pydantic model, lives in `nikita/onboarding/models.py`, persisted as JSONB on `users.onboarding_profile`.
- `UserProfile` = SQLAlchemy ORM model, lives in `nikita/db/models/profile.py`, persists to `user_profiles` table.
- `BackstoryGeneratorService.generate_scenarios(profile, venues)` at `:81` accepts `UserProfile` (ORM), NOT `UserOnboardingProfile` (Pydantic).
- Spec 213 MUST provide an adapter (in `portal_onboarding.py` facade) to bridge Pydantic → ORM before invoking the backstory service. Do not assume they are interchangeable.

## Research Summary (file:line evidence)

### Backend surface
- `nikita/onboarding/handoff.py:336` `execute_handoff`, `:459` `_bootstrap_pipeline` (BROKEN — queries empty conversation), `:505` `_send_first_message`, `:532` `execute_handoff_with_voice_callback`
- `nikita/api/routes/onboarding.py:647` `PortalProfileRequest`, `:726` `save_portal_profile`, `:822` `_trigger_portal_handoff`, `:871` **profile-stripping bug** (builds `UserOnboardingProfile(darkness_level=drug_tolerance)` only)
- `nikita/onboarding/models.py:76` `UserOnboardingProfile` (current fields: `timezone`, `occupation`, `hobbies`, `personality_type`, `hangout_spots`, `darkness_level`, `pacing_weeks`, `conversation_style`). `ProfileFieldUpdate.validate_field_name` at `:204-219` — **allow-list must be updated for each new field**.
- `nikita/services/venue_research.py:79` `VenueResearchService` — Firecrawl + 30-day `VenueCache`, timeout fallback
- `nikita/services/backstory_generator.py:81` `BackstoryGeneratorService` — Pydantic AI + Claude, 3 tones (romantic/intellectual/chaotic)
- `nikita/platforms/telegram/onboarding/handler.py` — OLD wiring reference (Telegram-only)
- `nikita/pipeline/orchestrator.py:31` — 11-stage pipeline

### Portal surface
- `portal/src/app/onboarding/onboarding-cinematic.tsx` — 5-section scroll-snap (to be replaced)
- `portal/src/app/onboarding/sections/profile-section.tsx` — collects city/scene/darkness/phone only
- `portal/src/app/onboarding/schemas.ts` — zod has `life_stage` + `interest` but UI doesn't collect them
- `portal/src/components/glass/glass-card.tsx` — 4 variants
- `portal/src/components/landing/hero-section.tsx` — typography reference
- `portal/src/components/landing/{aurora-orbs,falling-pattern,glow-button,pitch-section,stakes-section}.tsx` — reusable atmosphere components
- `portal/src/app/onboarding/components/ambient-particles.tsx` — canvas atmosphere

### Hygiene state (must clean BEFORE spec)
- 6 orphaned worktrees in `.claude/worktrees/` (will conflict with new parallel agents)
- 8 stale open PRs (#261, #249, #185, #212, #210, #206, #205, #186) — all superseded
- `specs/212-phone-capture-onboarding-ux/` missing (Spec 212 landed without spec dir)
- `specs/081-onboarding-redesign-progressive-discovery/` not archived (will be superseded by Spec 214)
- ROADMAP.md stale: tests_total 5533 → actual 5857+; last_deploy 2026-03-23 → actual 2026-04-14; Cloud Run 00235-lh8 → actual 00248-7vp; missing Specs 210, 212; 213/214 not yet registered

### Test surface gaps
- Zero tests exist for: city research from portal path, backstory from portal path, `age`/`occupation` fields, multi-step wizard navigation
- `test_pipeline_bootstrap.py::test_bootstrap_skipped_if_flag_disabled` — zero-assertion shell
- `test_bootstrap_pipeline_processes_conversation` — no sibling for EMPTY-recent case (production path)
- Portal: `tsc --noEmit` not chained into `next build` — PR #272's type-failure risk persists
- E2E: 13 `networkidle` occurrences in `onboarding.spec.ts` — will stall on async polling

## Approach Selection — Approach C (Backend-First → Portal-UX)

**Why (from approach evaluator panel 2-1)**:
- **Architect**: clean separation, each PR single blast radius, API contract forced upfront
- **SRE**: backend stream tested in isolation before portal traffic — `_bootstrap_pipeline`, service timeouts, fallback paths load-tested safely
- **UX (dissenting)**: prefers incremental wizard rollout; mitigated by shipping Spec A behind flag + short internal dogfood before Spec B merges

Rejected B (strangler fig) — wrapper-of-wrapper creates hidden coupling via shared `useForm` FormContext; doubles integration test surface.

Rejected A (big-bang v2 route) — single PR > 400 LOC; no incremental confidence signal; Firecrawl degradation on launch-day hangs every submit.

## Decomposition

```
Phase 0: Hygiene cleanup (non-SDD, pre-spec)
    ├── Cherry-pick 350a717 → master via 1 small PR (PR RESTORE)
    ├── Close 8 stale PRs
    ├── Prune 6 orphaned worktrees
    ├── Archive specs/081 → specs/archive/081
    ├── Create specs/212 directory (post-hoc, from landed code)
    └── Sync ROADMAP.md

Spec 213 — Onboarding Backend Foundation (SDD-driven)
    ├── R2: Model fields (age, name, occupation)
    ├── ProfileFieldUpdate allow-list update
    ├── R3: Wire VenueResearchService + BackstoryGeneratorService to portal path
    ├── Timeout guards + fallbacks (NEW: per-service budgets)
    ├── R4: /pipeline-ready poll endpoint + readiness gate
    ├── R7 backend: FirstMessageGenerator uses full profile + backstory
    └── Tests: unit + integration + @pytest.mark.integration for services

Spec 214 — Portal Onboarding Wizard (SDD-driven)
    ├── Requires: Spec 213 merged + API contract frozen
    ├── R5: One-at-a-time wizard using landing aesthetic
    ├── R6: Progressive game element introduction
    ├── New fields collected: age, name, occupation
    ├── Pipeline-ready gate with spinner + timeout UI
    ├── Fix networkidle + add tsc --noEmit to build step
    └── Archives specs/081
```

## Wizard Steps (Spec 214) — Enumerated — DOSSIER FORM APPROACH (revised after UX review)

**Approach**: "The Dossier Form" — panel vote 2-1 (Frontend + Backend) over "The Drop" (chat) and "The Audition" (full-screen Nikita video). Persona framing: Nikita is building a classified file on the user. Power dynamic: she's evaluating. Each field is a dossier entry.

**Reorder principle**: backstory reveal is the emotional climax and MUST precede phone ask (ride peak investment).

| # | Step | Field(s) / content | Gate / service call |
|---|---|---|---|
| 1 | Landing (dossier entry) | — | "Nikita has been watching. She wants to know if you're worth it." → magic link login |
| 2 | Auth | `email` | Nikita-voiced magic link email. Subject: "Someone wants to talk to you (it's me)." |
| 3 | Dossier header | — | Full-width classified file. Scores shown as REAL `50/50/50/50` (not fake 75/100). Copy: "Prove me wrong." |
| 4 | Location (dossier field) | `location_city` | Async VenueResearch fires on blur → inline venue preview appears below ("She found: Berghain, Tresor..."); poll `venue_research_status` via /pipeline-ready |
| 5 | Scene | `social_scene` | Pre-filled guess "Suspected: techno?" — user confirms/corrects |
| 6 | Darkness | `darkness_level` | Slider 1-5 with Nikita narration: "I'll know if you're lying about this." |
| 7 | Identity (dossier fields) | `name`, `age`, `occupation` | Three fields, Nikita-voiced. Occupation informs backstory. |
| 8 | **Backstory reveal (CLIMAX)** | user picks scenario | Portal calls `POST /onboarding/preview-backstory` (FR-4a). Shows 3 scenarios. Dossier stamps "ANALYZED". |
| 9 | Phone ask (post-climax) | `phone` | Dossier field "Direct line: [I want to call you]". Binary: [Give number] (voice = premium) vs [Start in Telegram] (default) |
| 10 | Pipeline ready gate | — | POST `/onboarding/profile` with `cache_key` (reuses preview cache) → poll `/pipeline-ready` → dossier stamps "CLEARANCE: CLEARED" → 20s timeout degrades to "PROVISIONAL" |
| 11 | Handoff | — | "Application... accepted. Barely." Telegram deeplink + QR (desktop→mobile). Voice path: call countdown UI. Text: "Open Telegram" CTA. |

Note: steps 1-2 are pre-wizard; 3 is dossier header (no input); 4-9 are 6 data-collection dossier fields; 10-11 are handoff.

## New Requirements (added from UX review)

These must be reflected in Spec 213 (backend) or Spec 214 (portal) scope:

| ID | Requirement | Owner | Status |
|---|---|---|---|
| **NR-1** | Wizard state persistence: partial profile + current step persist to `users.onboarding_profile.wizard_step` JSONB + localStorage keyed by user_id. Resume from last step on return (tab close, network loss, mobile interruption). | Spec 214 | ADD |
| **NR-2** | `/pipeline-ready` response exposes `venue_research_status` + `backstory_available` fields (for step-4 inline preview + step-8 reveal gate) | Spec 213 (added as FR-2a) | ADDED ✓ |
| **NR-3** | Phone country validation pre-flight: client-side check against ElevenLabs supported regions BEFORE submit. If unsupported → show inline + offer Telegram fallback | Spec 214 | ADD |
| **NR-4** | QRHandoff component for desktop→mobile Telegram handoff. No service dep, uses qrcode.react or similar. Shows alongside Telegram deeplink button on step 11. | Spec 214 | ADD |
| **NR-5** | Voice fallback polling UI: if phone provided, portal polls handoff result and shows appropriate state (calling → connected → ended OR call failed → Telegram fallback with explanation). No silent degradation. | Spec 214 | ADD |
| **NR-6** | `POST /onboarding/preview-backstory` endpoint (FR-4a) — portal-wizard step 8 backstory reveal BEFORE profile POST | Spec 213 (added as FR-4a) | ADDED ✓ |

## Copy Guidelines (Nikita Voice — Persona Consistency)

All portal copy in Nikita's voice. NO sterile SaaS language. Per `.claude/rules/review-findings.md` few-shot echo rule: grep all persona/prompt files when changing canonical phrases.

Examples (draft, refine during Spec 214 /feature):
- Button: "Show her" NOT "Get started"
- Field label: "Location: [REDACTED]" NOT "City"
- Slider label: "How far can I push you?" NOT "Darkness level"
- Stamp: "CLEARANCE: PENDING" → "CLEARED" / "PROVISIONAL" NOT "Processing..."
- Landing hero: "Nikita has been watching." NOT "Welcome to Nikita"
- Email subject: "Someone wants to talk to you (it's me)" NOT "Your magic link"
- Post-submit: "Application... accepted. Barely." NOT "Profile saved successfully"

## Pre-Spec-214 Standalone Fixes (ship independently, don't block on full redesign)

Per UX expert ROI top-5, these can ship as standalone portal PRs BEFORE Spec 214:
1. **Voice vs Telegram overlay split** — current shows identical "Opening Telegram..." for both paths → split into voice-countdown UI vs Telegram deeplink UI. Portal-only, 1 PR.
2. **Real demo scores** — ScoreSection currently shows hardcoded 75/100 + 68-76% bars → show 50/50/50/50 with "where you start" label. Portal-only, 1-line change.
3. **Pending_handoff trigger on /start** — Telegram `/start` handler doesn't check `pending_handoff`. Add explicit check after OTP verification → fire handoff immediately. Backend only, 1 PR.
4. **1500ms → 3000ms redirect + iOS fallback button immediately** — small portal change.
5. **Nikita-voiced copy rewrite** — pure text change, no logic. Can ship per-section incrementally.

## Edge-Case Decisions Needed (record in spec.md)

| Scenario | Decision |
|---|---|
| City research times out | Spec: 15s budget; on timeout, first message uses scene-only flavor. Log `portal_handoff.venue_research` outcome. |
| Backstory generation fails | Spec: 20s budget; on fail, cache-bust + pipeline uses default persona prompt (not scenario-specific). Log `portal_handoff.backstory` outcome. |
| Mobile tab-switch mid-wizard | Spec: persist step state to `users.onboarding_profile.wizard_step` JSONB key. Resume from last completed step on remount. |
| Phone 409 mid-wizard | Spec: phone step validates on step-advance (not final submit). 409 → inline error on phone field + rewind to that step. |
| Re-onboarding (existing partial) | Spec: detect via `users.onboarding_completed_at IS NULL AND onboarding_profile IS NOT NULL` → resume; else fresh start. |
| Pipeline gate timeout (>20s) | Spec: show "Nikita is getting ready..." spinner 0-15s, "Almost there..." 15-25s, then let user proceed with graceful message if 25s+. Log `pipeline_ready.timeout`. |
| Voice-first user (has phone) | Same wizard UI through step 9 (city research + backstory still relevant for voice prompt personalization); on step 10 pipeline gate, route to voice callback instead of Telegram (per Spec 212 routing). Voice agent receives same enriched profile + backstory. |
| Existing user re-onboarding (partial profile) | Detect via `users.onboarding_completed_at IS NULL AND users.onboarding_profile IS NOT NULL`. Resume from step matching last JSONB key written. Backfill missing new fields (`name`/`age`/`occupation`) by asking again. |
| New user on existing `user_profiles` row | Migration adds nullable columns (`name`, `age`, `occupation` default NULL). Re-onboarding prompts fill them. No data loss for completed-onboarding users. |
| Pipeline gate feature flag OFF | Fall back to 1s optimistic pass-through (not old no-gate behavior) — so rollback preserves wait-for-readiness UX. Flag governs gate TIMEOUT, not existence. |
| BackstoryGenerator cache | Key on `(city, scene, darkness_level, life_stage, interest, age_bucket, occupation_bucket)` — age bucketed to decade (20s/30s/40s/etc.), occupation bucketed to category (tech/arts/finance/service/other). 30-day TTL. |

## Verification Strategy

1. **Recovery smoke**: after `git cherry-pick 350a717`, run `pytest tests/onboarding/ -x -q` — green before touching anything else.
2. **Spec 213 integration contract**: `@pytest.mark.integration` test — mock Firecrawl + Claude, assert `research → scenarios → FirstMessageGenerator output` chain produces personalized text containing city + scene + backstory hook.
3. **Spec 213 contract freeze**: publish `OnboardingV2ProfileRequest` / `OnboardingV2ProfileResponse` as Pydantic schemas; Spec 214 imports them.
4. **Spec 214 visual**: Playwright screenshot (reference image) + explicit `waitForSelector('[data-testid="pipeline-ready"]')` replacing `networkidle`.
5. **Spec 214 UX**: Playwright full-journey test — start wizard → complete all 8 steps → pipeline gate → first Telegram message arrives → contains city + scene + occupation.
6. **Stochastic budget**: per `rules/stochastic-models.md`, if any timeout becomes a named distribution (e.g., `VENUE_RESEARCH_TIMEOUT_S: Final[float]`), add rationale comment with prior values + regression test.

## Risks

| Risk | Mitigation |
|---|---|
| `UserOnboardingProfile` schema change ripples to 15+ modules (voice agents, text agents) | Add fields as `Optional[T] = None`; no existing call sites break. |
| Pydantic vs ORM type confusion in `portal_onboarding.py` facade | Facade has ONE responsibility: accept `UserOnboardingProfile` + user_id, load/create `UserProfile` ORM row, call services, return scenarios. Canonical mapping table documented in spec.md. |
| BackstoryGenerator Claude cost explodes with onboarding volume | 30-day scenario cache keyed on `(city, scene, darkness, life_stage, interest, age_bucket, occupation_bucket)`; one Claude call per unique profile shape. Budget: <$0.05/unique profile shape; Anthropic docs: Haiku at $0.25/MTok input. |
| VenueResearchService Firecrawl cost on new cities | 30-day `VenueCache` already exists; new cities cost ~$0.02/scrape via Firecrawl. Budget alert if >100 unique cities/day. |
| PII exposure in logs/telemetry | `name`, `age`, `occupation`, `phone` are PII. Spec 213 MUST include: (a) Supabase RLS: user reads/writes only own `user_profiles` row, (b) log redaction — logger extras contain `user_id` only, never PII, (c) no PII in exception `%s` echoes (prior bug in `voice_flow.py` per PR #270). |
| Cherry-pick 350a717 conflicts with `87938db`-era changes to same files | Branch `origin/fix/onboarding-pipeline-bootstrap` confirmed reachable. Run `git cherry-pick 350a717` locally; on conflict, re-apply from diff (495 LOC already reviewed and merged once — known-good). |
| SSE pipeline-ready endpoint connection churn on Cloud Run scale-to-zero | Use poll (2s interval, 20s max) instead of SSE — simpler + robust to cold start. |
| Wizard state-preservation introduces XSS if JSONB rendered unsanitized | Never render `wizard_step` payload directly; treat as internal state only. |
| Spec 214 merges before Spec 213 contract is truly frozen | Spec 213 publishes `OnboardingV2ProfileRequest` / `OnboardingV2ProfileResponse` / `BackstoryOption` to a shared `nikita/onboarding/contracts.py` module EARLY (first Spec 213 PR). Spec 214 can stub against this module immediately — recovers parallelism UX reviewer wanted. |
| Pipeline gate flag-off regresses to "Nikita forgets first message" (user's #1 complaint) | Feature flag controls TIMEOUT only, not gate existence. Flag-off = 1s optimistic pass-through. Gate itself is permanent. |
| R8 (continuity) not independently testable from R7 (dynamic message) | E2E asserts: user replies with first-message text verbatim → Nikita's response references it ("yes, I did say that...") rather than denying. Mock pipeline with known first-message fixture. |

## Dependency DAG

```
  [Worktree prune]  ←  ONLY true blocker to /feature 213
         │
         ▼
  [PR RESTORE: cherry-pick 350a717]  (critical — fixes production bug)
         │                                                │
         ├──── parallel ──────────────────────────┐       │
         ▼                                        ▼       ▼
  [Close 8 stale PRs]      [Archive specs/081]  [Sync ROADMAP.md]
                                                          │
  ┌──────────────────────────────────────────────────────┘
  ▼
  [Spec 213: /feature → /plan → /tasks → /audit]
         │
         ▼
  [Spec 213 PR #1: contract module — `nikita/onboarding/contracts.py`] ← early freeze
         │                                                             │
         │ ────────────────────────── parallel possible ───────────────┤
         ▼                                                             ▼
  [Spec 213 PRs #2-N: TDD impl]                            [Spec 214: /feature → /plan → /tasks]
         │                                                             │
         ▼                                                             ▼
  [Merge Spec 213 + dogfood 1 day]                   [Spec 214 audit blocks on 213 merge]
         │                                                             │
         └──────────────────────────────┬──────────────────────────────┘
                                        ▼
                            [Spec 214 /implement — imports contracts]
                                        │
                                        ▼
                         [Spec 214 PRs — TDD loop, 2s poll gate]
                                        │
                                        ▼
                        [Merge Spec 214 + Cloud Run + Vercel deploy]
                                        │
                                        ▼
                        [E2E: full wizard + R7 + R8 verification]
```

**Critical path correction**: only worktree pruning blocks `/feature 213`. Closing stale PRs, archiving 081, syncing ROADMAP are hygiene parallels, not prerequisites.

## Files Most Likely Touched

### Spec 213
- `nikita/onboarding/contracts.py` (NEW — shared Pydantic types: `OnboardingV2ProfileRequest`, `OnboardingV2ProfileResponse`, `BackstoryOption`, `PipelineReadyState`) — ships FIRST so Spec 214 can stub against it
- `nikita/onboarding/models.py` (+2 fields `name`, `age` on `UserOnboardingProfile`; +allow-list entries at `:204-219`; `build_profile_from_jsonb` helper from #273 already handles this)
- `nikita/db/models/profile.py` (+3 nullable columns `name`, `occupation`, `age` on `user_profiles`)
- Supabase migration via MCP (`mcp__supabase__apply_migration`) — `alter_user_profiles_add_name_occupation_age`
- `nikita/api/routes/onboarding.py` (extend `PortalProfileRequest:647` with new fields; new `/pipeline-ready` endpoint; update `_trigger_portal_handoff:822` to call facade)
- `nikita/services/portal_onboarding.py` (NEW — thin facade: accepts `UserOnboardingProfile` + `user_id`, loads/creates `UserProfile` ORM row via `user_profile_repo`, invokes `VenueResearchService.research_venues` with 15s budget, invokes `BackstoryGeneratorService.generate_scenarios` with 20s budget, returns `list[BackstoryOption]`)
- `nikita/services/venue_research.py`, `nikita/services/backstory_generator.py` (add `asyncio.wait_for` timeout wrappers; extend cache key in backstory for new fields)
- `nikita/onboarding/handoff.py` (FirstMessageGenerator enhanced to reference backstory scenario; R8 continuity already covered by `_seed_conversation` from #273)
- `nikita/onboarding/tuning.py` (NEW — `VENUE_RESEARCH_TIMEOUT_S: Final[float] = 15.0`, `BACKSTORY_GEN_TIMEOUT_S: Final[float] = 20.0`, `PIPELINE_GATE_POLL_INTERVAL_S`, `PIPELINE_GATE_MAX_WAIT_S` — per `.claude/rules/tuning-constants.md`)
- `tests/onboarding/test_portal_onboarding.py` (NEW — facade unit + integration)
- `tests/services/test_venue_research_portal.py` (NEW — timeout + fallback)
- `tests/services/test_backstory_generator_portal.py` (NEW — cache key + timeout + PII-safe logs)
- `tests/api/routes/test_onboarding_pipeline_ready.py` (NEW — poll semantics)
- `tests/onboarding/test_r8_conversation_continuity.py` (NEW — E2E-style: seed message acknowledged, not denied)
- `tests/onboarding/test_tuning_constants.py` (regression guard on timeouts)

### Spec 214
- `portal/src/app/onboarding/onboarding-wizard.tsx` (NEW, replaces cinematic)
- `portal/src/app/onboarding/steps/` (NEW directory: 8 step components)
- `portal/src/app/onboarding/schemas.ts` (expanded)
- `portal/src/app/onboarding/hooks/use-pipeline-ready.ts` (NEW — poll hook)
- `portal/src/app/onboarding/components/wizard-progress.tsx` (NEW)
- `portal/src/components/landing/` (import atmosphere components — no modification)
- `portal/package.json` (add `"prebuild": "tsc --noEmit"` to prevent PR #272 recurrence)
- `portal/e2e/onboarding.spec.ts` (rewrite — fix networkidle + add wizard navigation)

## Next Action

Executable sequence:

```bash
# 0. Verify recovery target is reachable
git log origin/fix/onboarding-pipeline-bootstrap --oneline | head -5
# expect: 350a717 fix(onboarding): seed conversation before pipeline bootstrap + full profile passthrough

# 1. Worktree prune (only true blocker)
git worktree list
# for each stale worktree path:
git worktree remove --force <path>
git worktree prune

# 2. PR RESTORE (critical production recovery)
git checkout -b fix/restore-pr-273-onboarding-pipeline master
git cherry-pick 350a717
pytest tests/onboarding/ -x -q   # must be green
gh pr create --title "fix(onboarding): restore PR #273 (pipeline bootstrap + profile + continuity)" \
  --body "PR #273 was force-push-wiped from master during Spec 212 recovery. Cherry-picks commit 350a717 back onto master. Restores 4 structural fixes: pipeline bootstrap seed, profile JSONB persistence, conversation continuity, voice-path pipeline gap."
# then: /qa-review --pr N → 0/0/0 → squash merge

# 3. Parallel hygiene (non-blocking)
gh pr close 261 --comment "Superseded by Spec 210 (b0f7e7a)"
gh pr close 249 --comment "Superseded by PRs #252 + #253"
gh pr close 185 --comment "Landed via Spec 212"
gh pr close 212 --comment "Pre-sprint, stale"
gh pr close 210 --comment "Pre-sprint, stale (portal testing overhaul)"
gh pr close 206 --comment "Stale docs (Tier 2 diagrams)"
gh pr close 205 --comment "Superseded by Spec 210 v2 (b0f7e7a)"
gh pr close 186 --comment "Stale (deployment docs + E2E migration)"
git mv specs/081-onboarding-redesign-progressive-discovery specs/archive/081-onboarding-redesign-progressive-discovery
# Backfill specs/212 post-hoc from commit history (optional but recommended)
# Run /roadmap sync (or manual edit to match actual state)

# 4. Spec 213 SDD chain
/roadmap add 213 onboarding-backend-foundation
/feature 213   # author spec.md with R1-R8, edge cases, wizard step 1-11 (backend parts)
/plan 213
/tasks 213
/audit 213     # 6 parallel sdd-*-validator agents until PASS
/implement 213 # mandatory skill — not raw subagent dispatch

# 5. Spec 214 SDD chain (can start /feature + /plan while 213 implements, but /audit blocks on 213 merge)
/roadmap add 214 portal-onboarding-wizard
/feature 214   # imports contracts from Spec 213
/plan 214
/tasks 214
# wait for Spec 213 merged
/audit 214
/implement 214

# 6. Deploy + E2E
gcloud run deploy nikita-api --source . --region us-central1 --project gcp-transcribe-test --allow-unauthenticated
cd portal && npm run build && vercel --prod
# Run /e2e full — verify R1-R8 end-to-end
```

## References
- `~/.claude/plans/quirky-floating-liskov.md` — prior plan (user-home, covers WS-1 = PR RESTORE scope) — `ls ~/.claude/plans/` to verify
- `.claude/plans/post-compaction-handoff.md` — handoff state (contained incorrect claim that #273 was on master — confirmed orphaned)
- `specs/081-onboarding-redesign-progressive-discovery/spec.md` — prior portal onboarding spec (to archive)
- `specs/212-phone-capture-onboarding-ux/` — **missing directory** (Spec 212 landed without spec dir); backfill recommended but not blocking
- `.claude/rules/testing.md`, `.claude/rules/tuning-constants.md`, `.claude/rules/stochastic-models.md`, `.claude/rules/pr-workflow.md`, `.claude/rules/review-findings.md`, `.claude/rules/subagent-safety.md`

## Reviewer Findings Addressed
- **Devil's Advocate C1** (Pydantic vs ORM confusion): R2 split into R2a/R2b/R2c; type disambiguation block added.
- **Devil's Advocate C2** (PortalProfileRequest extension missing from Spec 213): R2c explicitly in Spec 213.
- **Devil's Advocate C3** (conversation continuity not tied to R7): R8 added with independent AC.
- **Devil's Advocate H1** (migration strategy): nullable columns in R2a + re-onboarding edge case.
- **Devil's Advocate H2** (ORM adapter): explicit in `portal_onboarding.py` facade description.
- **Devil's Advocate H3** (PII): risk row added; log redaction + RLS requirements.
- **Devil's Advocate H4** (DAG serialization): contracts.py ships in first 213 PR — enables parallel 214 development.
- **Devil's Advocate H5** (cache key): new key includes all personalization inputs.
- **Process P1** (8 steps unenumerated): wizard steps 1-11 table added.
- **Process P2** (350a717 reachability): verification command in Next Action step 0.
- **Process P3** (edge table header): "Decision required" → "Decision".
- **Process P4** (portal_onboarding.py missing from tasks): added to Spec 213 Files Touched.
- **Process P5** (R2 overlap confusing): split into restored-via-cherry-pick vs net-new.
- **Process P6** (hygiene blocking): DAG redrawn — only worktree prune is critical path.
- **Process P7** (Playwright not executable): spec.md authors will specify exact commands during /feature 214.

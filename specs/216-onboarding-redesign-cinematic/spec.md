# Feature Specification: Onboarding Redesign — Cinematic Agentic Wizard (Spec 216)

**Spec ID**: 216-onboarding-redesign-cinematic
**Status**: Draft (GATE 1)
**Predecessor**: Spec 215 (Telegram-first signup, COMPLETE) + Spec 214 v2 FR-11d (agentic wizard, partial — superseded by 216-B)
**Supersedes**: Spec 214 v2 FR-11d (chat-first slot-filling variant); Spec 215 portal-first auth chain (216-A rewires routing). Walks R-V patchwork (#392-396) closed by 216-B.
**Date**: 2026-04-29
**Author**: Orchestrator + read-only intel-explore subagents (STEP-0 routing trace + REUSE delta verify)

---

## Overview

### Problem Statement

W3 battle-test live walk (2026-04-28) returned **VERDICT FAIL** with 10 GH issues (#440-#449) against the deployed Spec 214 v2 + Spec 215 stack. Two CRITICAL findings ground the experience to a halt:

1. **#440 (CRIT) — PKCE magic-link unreachable**: Production `/start` reply contains a deep-link button to portal email form (Supabase template — untouched by PR #438), not the conversational FSM. PR #438's PKCE fix only patched `generate_magiclink_for_telegram_user`, but that path is never hit because `signup_handler.py` is not the live route for bare `/start`.
2. **#441 (CRIT) — Wizard completion gate never fires**: `onboarding_status='pending'` at 83% with 5/6 slots filled. Per-turn snapshot computation of `progress_pct == 100` is a false equivalence; cumulative state validation is missing.

Four HIGH (#442 identity ambiguous-accept, #443 simonsimon mirror-echo, #444 backstory converse_reply_reject, #445 telegram_signup_sessions never written), 3 MEDIUM (#446 PII raw city in cache_key, #447 send-button trailing-whitespace, #448 no auto-redirect), 1 LOW (#449 _vercel/insights 404). The portal-first email form is also visually sterile compared to Spec 208 landing — high-effort flow followed by generic SaaS UI.

Beyond bugs, the structural problems are deeper:
- **Two parallel `/start` handlers** in `nikita/api/routes/telegram.py` route bare `/start` to a deep-link button instead of the FSM (STEP-0 verdict 2026-04-29).
- **Procedural reflexes in agent code**: hardcoded boolean completion gates, 7 narrow `extract_*` tools fanout, per-turn state snapshots, static system-prompt routing rules. The 6 hard rules in `.claude/rules/agentic-design-patterns.md` exist precisely to prevent this regression — and the W3 codebase still violates them.
- **Missing personality + hobbies signal**: backstory generator runs on darkness-level alone. No Big Five inference, no hobby capture, no archetype selection logic.

### Proposed Solution — "Cinematic Agentic Wizard"

A single Telegram-canonical signup path → cinematic 12-screen wizard inheriting the Spec 208 landing design system, driven by a Pydantic AI 1.71.0 conversation agent that consolidates 7 narrow tools into one discriminated-union `output_type`, evaluates `instructions=callable` per-turn against cumulative `WizardSlots`, validates with `@output_validator + ModelRetry`, and gates completion via `FinalForm.model_validate(state.slots_dict)`. The agent has access to 4 firecrawl-backed tools (always-fetch-something directive: city context, occupation signal, time-of-day signal, topic-specific) for AGI-feel agency. Big Five personality is inferred (hidden, never surfaced in UI) from prose answers via per-turn Haiku judge, then drives a 12-archetype curated taxonomy for the 3-card backstory selector. Cost ceiling $0.50/flow hard, $0.30 median; latency p99 <8s/turn.

**Decomposition**: 6 PR boundaries (A-F). Subspec specs in `subspecs/216-{A..F}-*/spec.md` carry per-PR ACs + critical files + test inventory. Master spec.md (this file) holds product narrative + AC index. Wireframes in `wireframes/{ascii,figma,motion-spec}.md`.

### Success Criteria

- **W4 walk verdict**: PASS across G.1-G.11 (handover §Verification) + new ACs C.1-C.11.
- **Cumulative `progress_pct` monotonic** across all 12+ wizard turns (no regression vs Walk V).
- **Completion gate fires correctly**: `FinalForm.model_validate` returns success at all 12 slots filled; `is_complete=True` propagates to FE; auto-redirect to `/dashboard` within 10s.
- **Big Five vector populated** server-side after wizard; ≥3 dimensions at confidence ≥0.5; never present in any UI response payload (NR-05).
- **firecrawl tool fires ≥1×/turn when `state.location` present** (always-fetch-something); cost <$0.50/flow.
- **3 archetype labels rendered** on backstory card screen come from the curated 12-list (no LLM-invented labels).
- **0 banned vocab** (`FILE`, `dossier`, `clearance`, `FIELD`) in any portal page bundle.
- **0 simonsimon-style mirror echoes** in `users.onboarding_profile`.
- **Visual identity matches Spec 208 landing** verbatim: bg-void `oklch(0.08 0 0)`, rose `oklch(0.75 0.15 350)`, Geist Sans/Mono, glass-card surfaces, AuroraOrbs, GlowButton, `EASE_OUT_QUART`, AnimatePresence opacity+y+blur.

---

## Functional Requirements

### FR-01 — Single Telegram-canonical signup path (216-A)

Bare `/start` from an unbound `telegram_id` (no row in `public.users` for that telegram_id) MUST enter `nikita/platforms/telegram/signup_handler.py::SignupHandler.handle_welcome` directly. The current routing in `nikita/api/routes/telegram.py:635-666` requires `payload == "welcome"` literal match for the FSM entry; bare `/start` falls through to `CommandHandler._handle_start` E1 path → `_send_bare_portal_auth_link` deep-link button. This MUST change.

**Acceptance**: see subspec 216-A ACs A1.1–A1.9.

### FR-02 — One slot per screen wizard (12 fixed roots, 216-C)

The wizard renders ONE slot per screen across 12 fixed roots, in this order: `display_name` → `age` → `city` → `occupation` → `darkness_level` → `primary_hobbies` → `saturday_morning` → `geek_out_on` → `together_we_could` → `same_weird_if` (optional) → `phone + voice_tone_pref` → `backstory_pick`. Identity is split (was monolithic in Spec 214). Hobbies use chip multi-select 3-5 picks across 100 chips × 10 categories with autocomplete + "+ other" free text. Each screen carries `NikitaReaction` (≤140 chars) + `WhyWeAsk` (1 sentence) + `ProgressRail`. Dynamic follow-ups (M1) inject 0-6 additional screens after Hinge prose roots + hobbies.

**Acceptance**: see subspec 216-C ACs C1.1–C1.11.

### FR-03 — Cumulative WizardSlots + FinalForm completion gate (216-B)

Wizard state is held server-side in a Pydantic `WizardSlots` model (extends `nikita/agents/onboarding/state.py:88-328` with 12 fields). State accumulates via `model_copy(update={...})` (immutable update; reassign to caller). `progress_pct` is a `@computed_field @property` of cumulative slots; monotonic non-decreasing across all turns.

The completion gate is **Pydantic validation**, not a boolean literal:

```python
try:
    form = FinalForm.model_validate(state.slots_dict)
    is_complete = True
except ValidationError:
    is_complete = False
```

`FinalForm` declares all 12 required slots non-optional + `@model_validator(mode="after")` for cross-field business rules (age ≥18, voice-requires-phone). The validator IS the gate. NO `is_complete = True` / `is_complete = False` literal anywhere in the `/onboarding/answer` route handler. (Closes #441.)

**Acceptance**: see subspec 216-B ACs B1.1–B1.12.

### FR-04 — Agentic conversation agent (216-B)

A single Pydantic AI 1.71.0 agent powers each turn:

```python
class TurnOutput(BaseModel):
    nikita_reaction: str       # ≤140 chars
    why_we_ask_next: str       # 1 sentence Nikita-voiced
    next_slot_kind: Literal[...] | None
    next_question_text: str
    control_type: Literal["text","chips","slider","scenarios","radio","tel"]
    control_options: list[str] | None = None

class TurnFailure(BaseModel):
    explanation: str

agent = Agent[ConverseDeps, TurnOutput | TurnFailure](
    "anthropic:claude-opus-4-7",
    output_type=[TurnOutput, TurnFailure],   # discriminated union, Tool Output mode
    instructions=inject_per_turn_context,    # callable, ALWAYS reevaluated even with message_history
    deps_type=ConverseDeps,
    retries=2,
)
```

`instructions=callable` is mandatory (NOT `system_prompt`) — Pydantic AI doc explicitly states `system_prompt` is reused when `message_history` present, while `instructions` callable is reevaluated every turn. The callable injects `state.missing` + `next_slot_hint` + cumulative state summary + `last_slot_kind` + `last_value` per turn.

`@agent.output_validator` enforces post-tool validation:
- Mirror-echo rejection: if `last_slot=="name"` and `name * 2 in reaction.lower()` → `raise ModelRetry(...)` (closes #443).
- Reaction length: `len(reaction) > 140` → `raise ModelRetry(...)`.
- Cluster confidence: M2 cluster <0.6 AND `cluster != "ambiguous"` → `raise ModelRetry(...)`.

`agent.run(..., message_history=hydrate_message_history(state.messages), deps=deps)` — official multi-turn primitive (Rule #6). Request body does NOT re-pass conversation context. `result.new_messages()` is appended to `nikita.conversation_jsonb` between turns. `capture_run_messages` wraps every `agent.run`; on `UnexpectedModelBehavior` exception, the system logs traceparent + falls back gracefully (closes #444).

**Acceptance**: see subspec 216-B.

### FR-05 — M1-M4 meta-prompt set (216-B)

Four named meta-prompts compose the agent's per-turn behavior. M1-M4 templates live in `nikita/agents/onboarding/conversation_prompts.py` (replaces deprecated `_WIZARD_FRAMING` block at L33-115 + L128).

| Code | Name | Purpose | When fires |
|------|------|---------|-----------|
| M1 | `GenerateFollowUpFromAnswer` | Produce ONE non-leading follow-up question that references ≥1 detail from the user's last answer; cluster-aware | After each Hinge prose root + hobbies, depth-1 default |
| M2 | `ClassifyAnswerCluster` | Run once per Hinge-prose answer to classify into a 4-6 cluster taxonomy (per slot) with confidence ≥0.6 | After every prose answer |
| M3 | `RefineSummary` | Compress conversation_jsonb into ≤2 sentences for system-prompt injection (used by `inject_per_turn_context`) | When cumulative state summary >300 tokens |
| M4 | `DetectSaturation` | Decide continue-or-stop signal for dynamic follow-up depth | Before each dynamic follow-up; hard-overrides: `turn_count_for_topic >= 2 → stop`; depth-2 only when `cluster == "ambiguous"` AND `turn_count_for_topic < 3` |

Total dynamic follow-ups capped at **6 across the wizard**. Cost circuit fires at $0.05 budget remaining. When M1 generation fails OR cost circuit triggers, the system uses the paired `static_fallback_question` from `nikita/agents/onboarding/follow_up_registry.yaml` (NR-06).

Each meta-prompt template uses `[FIXED]` skeleton + `[DYNAMIC]` substitution markers; FIXED block is Anthropic-prompt-cached for ≥60% token savings (NR-02).

### FR-06 — Big Five hidden inference (216-D)

Per-turn `claude-haiku-4-5` judge runs after each prose answer to update `users.onboarding_profile.big5_vector` (JSONB: 5 floats `{O, C, E, A, N}` + `confidence: {O: 0.x, ...}`). Big Five (BFI-2-XS as inference TARGET, never as a survey) is hidden from UI per NR-05 — only used server-side for archetype selection (FR-09) + brand_resonance_signal computation. Once any dimension reaches confidence ≥0.7, M4 short-circuits further probes on that dimension.

**Cost**: ~$0.04/flow (5×Haiku turns × ~$0.008).

### FR-07 — 4 firecrawl agentic tools, always-fetch-something (216-E)

The wizard agent has 4 Pydantic-AI-registered async tools that the LLM MAY call to enrich its reaction/follow-up:

| Tool | Trigger | Returns |
|------|---------|---------|
| `fetch_city_context(city: str)` | After `state.location` set | 1-line cultural note + 2-3 distinctive landmarks/scenes |
| `fetch_occupation_signal(occupation: str, city: str)` | After `state.occupation` set | 1-line common gear/jargon for that role in that city |
| `fetch_time_of_day_signal(city: str, dt: datetime)` | Each turn | 1-line "what's happening in {city} right now" (scene/weather/event) |
| `fetch_topic_specific(topic: str, city: str)` | When prose answer mentions a hobby ("climbing" → gyms in Zurich; "DJing" → common gear) | 1-line topical riff |

**Always-fetch-something directive**: per turn (skip turn 0), the agent MUST call ≥1 fetch tool when `state.location` is present. Per-turn budget guard: max 1 fetch invocation; cumulative budget $0.10-0.15/flow tracked in `RunContext.deps`. Cohort cache hits via hashed `(city, occupation)` key BEFORE issuing live fetch. On 3s timeout per call → log + use cached fallback OR static fallback registry. (`WebSearchTool` configured with `search_context_size="low"`, `max_uses=2`, `user_location` derived from `state.location`, Anthropic provider.)

### FR-08 — Hobby chip multi-select (216-C)

`primary_hobbies` slot uses a custom `HobbyChips` component with:
- 100 chips × 10 categories: Music, Movement, Gaming, Reading, Food & Drink, Travel, Art & Making, Tech & Gear, Outdoors & Nature, Social & Nightlife (~10 chips per category).
- Cross-category autocomplete-filter input.
- Enforced 3-5 picks (Continue button disabled outside this range).
- "+ other" free-text fallback.
- Stagger-reveal motion (per `wireframes/motion-spec.md` §4.3).

### FR-09 — LLM-generated 3-card backstory archetype selector (216-C, 216-D)

Curated 12-archetype taxonomy in `nikita/agents/onboarding/archetypes.py`: `the runner`, `the maker`, `the watcher`, `the climber`, `the seeker`, `the architect`, `the survivor`, `the rebel`, `the romantic`, `the wanderer`, `the host`, `the fugitive`. After wizard turn 11 (phone), the system runs a one-shot Opus prompt taking `(big5_vector, city, occupation, hobbies, darkness_level)` and returning 3 archetype label picks from the curated 12 + ranked rationale text. UI renders 3 `BackstoryArchetypeCards`. User selects 1; `backstory_pick` slot fills.

A second Opus call generates 3 personas (~150 chars each) for the picked archetype, persisted to `users.onboarding_profile.backstory_seed` (text ≤300 chars).

Anti-pattern guard: validator rejects ANY label not in the curated 12-list (closes a class of LLM-invent-a-label bugs).

### FR-10 — Visual identity inheritance (216-C)

The wizard inherits the Spec 208 landing design system **verbatim**:
- Tokens: `bg-void` `oklch(0.08 0 0)`, rose primary `oklch(0.75 0.15 350)`, Geist Sans + Mono, glass-card utilities.
- Components reused (NO duplication): `portal/src/components/landing/{aurora-orbs,glow-button}.tsx`, `portal/src/lib/easing.ts`.
- Motion: `EASE_OUT_QUART` (`[0.16, 1, 0.3, 1]`), AnimatePresence `mode="wait"` opacity+y+blur 350ms (`[0.22, 1, 0.36, 1]`). Full per-component motion spec in `wireframes/motion-spec.md`.
- `prefers-reduced-motion` honored on all transitions (NR-08).

### FR-11 — Idempotent magic-link click + auto-redirect (216-A, 216-C)

After OTP confirmation, Telegram surfaces the PKCE-format magic-link `https://nikita-mygirl.com/auth/confirm?token_hash=...&type=...&next=/onboarding`. First click consumes the token, sets the JWT cookie, and lands on `/onboarding` with FSM-resumable state. Second click (same token) MUST 400 cleanly OR redirect to `/dashboard` if session is still live (closes #F.1 idempotency case).

After `FinalForm.model_validate` success, FE polls `is_complete` and auto-redirects to `/dashboard` within 10s (closes #448).

### FR-12 — Cost circuit-breaker + latency budget (216-E)

| Bound | Value | Mechanism |
|-------|-------|-----------|
| Hard cost ceiling | $0.50/flow | `CostGuard.check_budget()` aborts further LLM calls; FE shows static fallback question |
| Median cost target | $0.30/flow | telemetry SLO |
| p99 latency/turn | 8s | per-tool 3s timeout; firecrawl `prepared_*` callable returns None when `state.location` absent |
| Cache hit rate | ≥60% | Anthropic prompt caching on FIXED instructions block |

Cumulative `cost_usd` written to `users.cost_usd` post-flow (existing column from Spec 215 B2).

---

## User Stories

### US-1 — Cold-start Telegram user (Anya, 28, designer in Zurich)

> Anya taps the landing-page CTA → opens `t.me/Nikita_my_bot` → types `/start`. Within 5s she gets a Nikita-voiced reply asking for her email (no preview thumbnail, ≤280 chars). She replies, gets a 6-digit OTP via email, types it in chat, and Telegram surfaces a `nikita-mygirl.com` link. She taps it on her phone → portal opens to `/onboarding` showing a glass-card with her name being asked.

**Coverage**: FR-01, FR-04 (turn-0 routing), FR-11.

### US-2 — Wizard prose path (Anya continues)

> Anya types her name "Anya" → reaction "Anya. Got it." → next ask: age. After name/age/city/occupation, she gets a darkness slider (0-10), picks 4. Then hobby chips: she autocompleted "techno", picked it; clicked "climbing", "vintage cinema", "ramen". 4 picks. Continue. Saturday morning prose: "running along the Limmat then pulling shots". M1 follow-up: "Wave or steady? When the music lands what counts more?". She answers. Big5 inference happens server-side. firecrawl fetches Zurich climbing gyms invisibly.

**Coverage**: FR-02, FR-04, FR-05 (M1, M2), FR-06, FR-07, FR-08.

### US-3 — Backstory reveal (Anya, climax)

> After phone + voice-tone choice, the screen pivots: 3 backstory cards appear staggered. Labels: `the watcher`, `the climber`, `the seeker`. Each card has 150 chars of persona prose tailored to her Big5 + city + occupation + hobbies. She picks `the seeker`. Continue → dashboard.

**Coverage**: FR-09, FR-10 (motion).

### US-4 — Resume mid-wizard (Anya tab-switches)

> Anya closes the tab at slot 8 (geek_out_on), takes a call. Comes back 20 min later, navigates to `nikita-mygirl.com/onboarding`. JWT cookie is valid. Wizard hydrates from `nikita.conversation_jsonb`, lands at slot 8 with last assistant message visible. progress_pct unchanged.

**Coverage**: NR-07.

### US-5 — Wrong OTP (Anya fat-fingers)

> Anya types `999999`. Bot replies: "That code didn't match — check the email and try again." `signup_state` unchanged. (Spec 216 inherits #437 wrong-OTP behavior and tracks separately; if session purges in current implementation, that's a known issue.)

**Coverage**: FR-01 (subspec 216-A AC A1.8).

### US-6 — Big Five hidden inference (server-side)

> While Anya answers prose questions, a server-side Haiku judge updates `big5_vector` after each turn. After saturday/geek/together/hobbies, dimensions O=0.78, E=0.62, A=0.45, C=0.55, N=0.30 with confidences. M4 sees O+E+C confidences ≥0.7 and short-circuits further probes. Backstory archetype picks lean into high-O + moderate-E (the seeker, the wanderer, the watcher).

**Coverage**: FR-06, NR-05.

---

## Non-Functional Requirements

### NR-01 — Pydantic AI 1.71.0 primitives only (216-B)

Approved primitives:
- `Agent(output_type=[X, Y])` discriminated union (Tool Output mode default)
- `Agent(instructions=callable)` per-turn dynamic system prompt
- `Agent(deps_type=X)` + `RunContext[X]` sidecar state DI
- `agent.run(..., message_history=...)` multi-turn context
- `@agent.output_validator` + `raise ModelRetry(...)` self-correcting loop
- `@model_validator(mode="after")` cross-field validation
- `@computed_field @property` derived state
- `capture_run_messages` for production debugging

Forbidden:
- `output_type=str` (loses validation)
- `system_prompt` for routing rules (NOT reevaluated with message_history)
- 7 narrow `extract_*` tools (Walk V incident; tool-selection bias quantified by BiasBusters arXiv:2510.00307)
- `pydantic-graph` FSM (overkill for linear flow per agentic-design-patterns.md)

### NR-02 — Anthropic prompt caching on FIXED skeletons

The FIXED portion of M1-M4 templates + agent base instructions MUST be wrapped in Anthropic prompt-cache markers. Target: ≥60% cache hit rate measured via Cloud Run logs `cache_read_input_tokens / total_input_tokens`. Validates 60-80% token savings on repeated structure across turns.

### NR-03 — RLS + policies on all new columns (216-D)

Migration `supabase/migrations/NNN_user_profile_inference.sql` adds 3 new columns to `users.onboarding_profile` (JSONB embedding):
- `big5_vector` (JSONB)
- `backstory_seed` (text ≤300)
- `brand_resonance_signal` (numeric [0,1])

ALL must include `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` + at least one `CREATE POLICY` (admin-only OR user-scoped per access model). UPDATE policies MUST include `WITH CHECK (...)`. DELETE policies use subquery `USING (user_id = (SELECT auth.uid()))`. Verified post-migration via `mcp__supabase__list_policies`.

### NR-04 — No banned vocab in any portal page bundle

`FILE`, `dossier`, `clearance`, `FIELD` — re-grep PR #430 vocab list across `portal/src/app/onboarding/**` server-rendered HTML AND component source. 0 hits required.

### NR-05 — Hide-the-framework

`big5_vector`, `brand_resonance_signal`, archetype rationale prose are NEVER returned in any UI response payload. Server-side only. Replika 2025 / Pi.ai precedent: surfacing the inference framework breaks the relational illusion.

### NR-06 — Static fallback registry per dynamic node (216-B)

`nikita/agents/onboarding/follow_up_registry.yaml` declares 1 paired `static_fallback_question` per dynamic-follow-up node. Triggers when (a) M1 generation fails (LLM error / output validator final retry exhausted), (b) cost circuit fires, OR (c) firecrawl tool times out. Lint test `test_follow_up_registry_completeness.py` enforces every dynamic node has a fallback.

### NR-07 — Resume mid-wizard (216-A, 216-C)

JWT cookie issued at `/auth/confirm` lasts ≥7 days. Wizard state hydrates from `nikita.conversation_jsonb` via `state_reconstruction.build_state_from_conversation`. Progress_pct, last assistant message, last slot_kind reconstructed accurately. Resume verified manually + by integration test.

### NR-08 — Reduced-motion + responsive baselines (216-C)

`prefers-reduced-motion: reduce` honored: instant transitions, paused AuroraOrbs, disabled hover effects. ProgressRail still animates (informational, not decorative). Responsive baselines verified at mobile 390×844 (iPhone 14) + desktop 1440×900. No horizontal scroll. All CTAs reachable without zoom.

---

## Constraints and Assumptions

### Constraints

- **Single LLM provider for wizard agent**: Anthropic `claude-opus-4-7` (primary) + `claude-haiku-4-5` (Big5 judge + M2 cluster classify). Gemini is mutually exclusive with `output_type` + builtin_tools per Pydantic AI doc — DO NOT use for wizard.
- **`isolation: "worktree"` mandatory** for any file-mutating subagent dispatched during implementation per `subagent-safety.md`.
- **NEVER fabricate DB rows in W4 walk** per `live-testing-protocol.md` Critical Anti-Patterns.
- **Telegram bot session**: Telegram MCP must hold a live session (`mcp__telegram-mcp__get_me` returns), or W4 cannot run.
- **No new design primitives**: every visual element must use existing Spec 208 tokens or extend via composition, not duplication.
- **Hobby chip universe is universal at launch**: NO per-cohort chip lists pre-launch; cohort tuning happens via telemetry post-launch only.
- **Big5 framework hidden**: NEVER surface BFI-2-XS, OCEAN, MBTI, Enneagram, attachment style in any UI string.

### Assumptions

- Cloud Run revision post-216-merge will inherit existing `TASK_AUTH_SECRET`, `ANTHROPIC_API_KEY`, `SUPABASE_*` env. No new secrets needed.
- `nikita/agents/onboarding/` module is the canonical home for all wizard logic; no duplication elsewhere.
- `signup_handler.py` FSM is fully wired except for the bare-`/start` routing gap; STEP-0 fix is sufficient.
- Production users with in-flight Spec 214 v2 wizard sessions (`onboarding_status='pending'`) are <100; safe to invalidate via migration on deploy.
- Vercel canonical = apex `nikita-mygirl.com`; CORS allowlist already correct per `vercel-cors-canonical.md`.
- `pending_signup_session` table from Spec 215 is reusable as-is for Spec 216 FSM.

---

## Out of Scope

- **Voice-note input** (defer to v2; user explicitly excluded).
- **Attachment-style inference** (defer to v2 per research file `personality-hobbies-research.md`; BFI-2-XS focus).
- **Per-cohort hobby chip lists** at launch (telemetry-driven post-launch).
- **Tree-of-Thought / MCTS / Branch-Solve-Merge** (research said overkill for linear flow; defer).
- **Multi-language i18n** (English-only at launch).
- **AB testing infrastructure** (post-W4 ship; manual cohort comparison via Cloud Run logs).
- **Wrong-OTP session-purge fix** (#437 tracked separately; documented in subspec 216-A AC A1.8 but not fixed in scope).
- **Vercel `_vercel/insights` 404** (#449; orthogonal LOW; defer).

---

## Edge-Case Decisions

1. **Bare `/start` for BOUND users** (`telegram_id` resolves to existing `users.id`): bypass FSM, route to normal `CommandHandler`. Existing behavior preserved (AC A1.3).
2. **`/start welcome` deep-link payload**: still routes to `SignupHandler.handle_welcome` (existing behavior preserved per AC A1.2). Two routes converge to the same FSM entry.
3. **User submits malformed email** at slot 1: bot rejects + re-prompts; `signup_state` unchanged (AC A1 inherited).
4. **Mid-flow `/start` re-trigger**: FSM resets gracefully OR resumes (current Spec 215 behavior; document-and-test in 216-A regression).
5. **Hobby pick count = 0 or 1 or 2 or 6+**: Continue button disabled with inline tooltip "pick 3-5".
6. **Hobby "+ other" free-text >40 chars**: trim and warn (FE component validation).
7. **Big5 judge returns null/error**: increment retry counter; on 2nd failure, skip the update for this turn (graceful degradation, NOT block the wizard).
8. **firecrawl tool returns 5xx or >3s**: log + cached fallback OR static fallback OR skip. NEVER block the turn.
9. **M1 generates a question that echoes user's last word verbatim**: `@output_validator` rejects → `raise ModelRetry(...)`. After 2nd retry exhausted, use `static_fallback_question`.
10. **Cost circuit breaker fires mid-flow at $0.05 budget remaining**: skip remaining dynamic follow-ups; force-jump to next required slot via M4 `move_on` directive; static fallback for any remaining prose roots.
11. **JWT cookie expired mid-wizard**: redirect to `/auth/confirm` with re-prompt; conversation_jsonb retained server-side for 24h.
12. **User completes wizard but `is_complete` is False due to validation edge case**: log to Cloud Run with traceparent; FE shows "We hit a snag — try again" + "Continue" button retries `/onboarding/answer` with current slot. Single retry; if it fails again, escalate to GH issue auto-create.
13. **Concurrent magic-link clicks (2 tabs)**: only one establishes session; the other yields graceful 400 + "Already signed in" page. No DB row corruption (AC F.2).
14. **Backstory archetype picker LLM returns 2 valid + 1 invented label**: validator rejects whole response; retry with stricter prompt; on 2nd failure, fall back to deterministic top-3 from cohort_chips taxonomy.

---

## Test File Inventory

Backend (Python, `tests/`):
- `tests/platforms/telegram/test_routing.py` (NEW) — bare `/start` unbound user → `SignupHandler.handle_welcome` (AC A1.1)
- `tests/agents/onboarding/test_cumulative_state.py` (NEW) — Rule #1 monotonicity (12 turns) + Rule #4 progress_pct
- `tests/agents/onboarding/test_completion_gate.py` (NEW) — empty/partial/full FinalForm validation triplet
- `tests/agents/onboarding/test_tool_recovery.py` (NEW) — mock LLM emits wrong-tool-args, ModelRetry recovers
- `tests/agents/onboarding/test_meta_prompts.py` (NEW) — M1-M4 golden snapshot outputs
- `tests/agents/onboarding/test_cluster_enum_completeness.py` (NEW) — every Literal cluster value has a paired template
- `tests/agents/onboarding/test_follow_up_registry_completeness.py` (NEW) — every dynamic node has a static_fallback_question
- `tests/agents/onboarding/test_big5_judge.py` (NEW) — mock Haiku golden vectors
- `tests/agents/onboarding/test_archetypes.py` (NEW) — 12-list validator rejects invented labels
- `tests/agents/onboarding/test_firecrawl_tools.py` (NEW) — budget guard + cohort cache + timeout fallback
- `tests/agents/onboarding/test_cost_circuit.py` (NEW) — over-budget mock LLM falls back to static registry
- `tests/api/routes/test_onboarding_answer.py` (NEW) — POST /onboarding/answer integration

Frontend (vitest, `portal/src/**/__tests__/`):
- `portal/src/app/onboarding/_components/__tests__/HobbyChips.test.tsx` (NEW) — 3-5 picks enforcement, autocomplete, "+ other"
- `portal/src/app/onboarding/_components/__tests__/BackstoryArchetypeCards.test.tsx` (NEW) — 3-card render, no-invent-label guard
- `portal/src/app/onboarding/_components/__tests__/ProgressRail.test.tsx` (NEW) — monotonicity reflection
- `portal/src/app/onboarding/_components/__tests__/WizardShell.test.tsx` (NEW) — AnimatePresence, reduced-motion

Live-walk (W4):
- `docs-to-process/20260{XXXX}-live-walk-W4-spec216.md` (artifact, not committed test) — verifies G.1-G.11 + new ACs.

---

## Open Questions

1. **firecrawl provider key + budget plumbing**: which firecrawl service tier, which API key env var? (To be resolved in 216-E during /clarify.)
2. **Backstory generator model choice**: claude-opus-4-7 vs claude-sonnet-4-6 for the 3-persona generation? Cost tradeoff: ~$0.04 vs ~$0.01. Default to opus until signal says otherwise.
3. **Big5 judge confidence calibration**: are dimension confidences linearly weighted or per-dim thresholds? Default: per-dim 0.7 short-circuit; review after 50 production flows.
4. **Hobby chip universe content**: 100 chips × 10 categories — exact list TBD via subspec 216-C authoring + UX review.
5. **Cohort cache seed for `cohort_chips.py`**: 6-8 (city, occupation) pairs hand-seeded; confirm pairs in 216-D authoring.

---

## Appendix A — PR Decomposition (for /plan phase)

6 PR boundaries map 1:1 to `subspecs/216-{A..F}-*/spec.md`. Each subspec spec.md carries its own ACs + critical files + test inventory. Master spec.md (this file) holds product narrative + AC index.

| PR | Subspec | Title | Depends on | Lines (est.) |
|----|---------|-------|------------|-------------|
| 216-A | 216-A-telegram-canonical-routing | Bare `/start` routing fix + signup_handler verification | (none — independent) | ~80 |
| 216-B | 216-B-agentic-wizard-core | Pydantic AI agent rewrite + M1-M4 + FinalForm gate | 216-A | ~350 |
| 216-D | 216-D-data-layer-inference | Migration + Big5 judge + archetypes + cohort cache | 216-A (parallel with 216-B) | ~250 |
| 216-C | 216-C-cinematic-frontend | 10-screen wizard + components + animations | 216-B + 216-D | ~400 |
| 216-E | 216-E-agentic-tools-firecrawl | 4 firecrawl tools + budget guard + prompt cache | 216-B (parallel with 216-C) | ~200 |
| 216-F | 216-F-testing-and-w4-walk | 3 mandatory test classes + M1-M4 unit + W4 walk | All A-E | ~300 |

Ship order: A → (B || D) → (C || E) → F.

---

## Appendix B — AC Index by Subspec

For full AC tables see each subspec's `spec.md`. This index lists AC counts per subspec for traceability.

| Subspec | AC count | CRIT | HIGH | MED |
|---------|----------|------|------|-----|
| 216-A | 9 | 5 | 3 | 1 |
| 216-B | 12 | 5 | 7 | 0 |
| 216-C | 11 | 1 | 9 | 1 |
| 216-D | 9 | 3 | 6 | 0 |
| 216-E | 8 | 1 | 5 | 2 |
| 216-F | 9 | 2 | 6 | 1 |
| **Total** | **58** | **17** | **36** | **5** |

---

## References

- Handover brief: `~/.claude/plans/spec216-handover-brief.md`
- Plan w/ orchestration: `~/.claude/plans/docs-to-process-20260424-wizard-redesig-composed-micali.md` Appendix 2
- Question tree: `~/.claude/plans/onboarding-redesign-spec216-question-tree.md`
- W3 walk report: `docs-to-process/20260428-live-walk-W3-post-pkce.md` (10 GH issues)
- Pydantic AI patterns: `docs-to-process/20260428-spec216-pydantic-ai-best-practices.md`
- Personality + hobbies research: `docs-to-process/20260428-spec216-personality-hobbies-research.md`
- Meta-prompts research: `docs-to-process/20260428-spec216-metaprompts-tree-research.md`
- Backstory + agent tools research: `docs-to-process/20260428-spec216-backstory-agent-tools.md`
- Wireframes: `wireframes/{ascii,figma,motion-spec}.md` (this directory)
- Rules: `.claude/rules/agentic-design-patterns.md`, `.claude/rules/testing.md`, `.claude/rules/live-testing-protocol.md`, `.claude/rules/pr-workflow.md`

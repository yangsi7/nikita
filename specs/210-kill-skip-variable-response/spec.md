# Feature Specification: Kill Skip-Rates + New-Conversation-Gated Variable Response Times

**Spec ID**: 210-kill-skip-variable-response
**Status**: Draft
**Domain**: 2 — Humanization
**Supersedes**: `specs/026-text-behavioral-patterns/` AC-5.x (skip-rate acceptance criteria)
**Created**: 2026-04-12
**Branch**: `feat/210-kill-skip-variable-response`
**Source Brief**: `~/.claude/plans/delightful-orbiting-ladybug.md`

---

## Overview

### Problem Statement

Two broken behaviors in the text agent hurt early-game experience:

1. **Nikita drops messages silently.** A "realism" probability gate in `nikita/agents/text/skip.py` (`SKIP_RATES`) causes her to ignore 25–40% of Chapter 1 messages. Players who start the game and send their first message may get no reply at all, interpreted as a bug or dead chatbot. User verdict: *"What's the point of starting a game if, when you write the fucking chatbot, it doesn't answer you?"*
2. **Variable response timing is inverted.** `nikita/agents/text/timing.py` already implements a chapter-scaled delay (`TIMING_RANGES`), but the values are backwards from design intent — Chapter 1 delays are 10 minutes to 8 hours (should be fastest), Chapter 5 delays are 5–30 minutes (should feel "settled-in"). Worse, `ResponseTimer.calculate_delay()` fires on **every** message, not just new conversation starts, so ongoing ping-pong exchanges inherit hours-long waits.

Combined, these make Chapter 1 feel broken: half the messages go unanswered, and the ones that do get answered appear hours later.

### Proposed Solution

1. **Delete the skip feature entirely.** Remove `nikita/agents/text/skip.py` (`SkipDecision`, `SKIP_RATES`, `REPETITION_BOOST`, `CONSECUTIVE_SKIP_REDUCTION`), strip all wiring from `handler.py`, remove the `skip_rates_enabled` feature flag, and delete/patch the dependent tests. Nikita always responds.
2. **Re-tune and gate the existing variable-response-time feature.** Invert `TIMING_RANGES` so Chapter 1 is near-instant and Chapter 5 is the slowest. Add an `is_new_conversation: bool` parameter to `ResponseTimer.calculate_delay()`; return `0` when the conversation is ongoing (last message <15 min ago). Delays only apply to fresh-session starts — the "how available does Nikita feel when you re-engage after a break" knob.
3. **Wire the gate through the handler.** Extend `TextAgentHandler.handle()` to accept `last_message_at: datetime | None`, add a private `_is_new_conversation()` helper that reuses `TEXT_SESSION_TIMEOUT_MINUTES = 15` from `nikita/context/session_detector.py`, and update the Telegram call site at `nikita/platforms/telegram/message_handler.py:350–357` to pass `conversation.last_message_at`.
4. **Preserve existing behavior for critical game states.** The boss-fight and won-state paths in `handler.py:330–356` already bypass delays (always `delay_seconds=0`); the new-conversation gate does NOT apply to those paths — a boss fight is urgent regardless of session gap.

### Success Criteria

- [ ] SC-1 — Zero "skipped" responses in Chapter 1 under normal play. Player sends N messages, receives N responses.
- [ ] SC-2 — Two messages within the same 10-second window both trigger immediate responses (ongoing conversation, gate=False).
- [ ] SC-3 — Message after a ≥15-minute gap in Chapter 1 arrives within 10 seconds (new-conversation gate fires with re-tuned range).
- [ ] SC-4 — Message after a ≥15-minute gap in Chapter 5 arrives within 30 minutes (new-conversation gate fires with Chapter-5 range).
- [ ] SC-5 — Boss-fight state responds immediately regardless of session gap.
- [ ] SC-6 — `pytest tests/ -x -q` passes with zero failures after all patches.
- [ ] SC-7 — `rg "SkipDecision|SKIP_RATES|REPETITION_BOOST|skip_rates_enabled|from nikita.agents.text.skip" --type py` returns zero hits outside archived specs.

---

## Functional Requirements

### FR-001: Delete skip feature code

**Priority**: P1
**Description**: Remove `nikita/agents/text/skip.py` entirely (136 lines — `SkipDecision` class, `SKIP_RATES`, `SKIP_RATES_DISABLED`, `REPETITION_BOOST`, `CONSECUTIVE_SKIP_REDUCTION`). After deletion, `rg "from nikita.agents.text.skip" --type py` MUST return zero hits in the `nikita/` tree. Maps to R210-1.

### FR-002: Remove skip wiring from handler

**Priority**: P1
**Description**: Remove from `nikita/agents/text/handler.py`:
- Line 33: `from nikita.agents.text.skip import SkipDecision` import
- Line 189: `skip_decision` constructor/handler param
- Line 203: `self.skip_decision = skip_decision or SkipDecision()` assignment
- Lines 358–373: Skip decision block (the `if self.skip_decision.should_skip(chapter): return ResponseDecision(should_respond=False, ...)` branch)

Maps to R210-2.

### FR-003: Remove skip feature flag

**Priority**: P1
**Description**: Delete the `skip_rates_enabled: bool` setting at `nikita/config/settings.py:197–201` (including field definition, default value, env var mapping, and any docstring references). Maps to R210-3.

### FR-004: Delete and patch skip-related tests

**Priority**: P1
**Description**:
- **Delete entirely**: `tests/agents/text/test_skip.py`, `tests/agents/text/test_handler_skip.py`
- **Patch** (remove skip references, keep remaining coverage intact):
  - `tests/integration/test_flag_group_a.py` — entire `TestSkipRatesEnabled` class
  - `tests/integration/test_all_flags.py` lines 30, 259, 357
  - `tests/integration/test_boss_flow.py` lines 206, 235, 254
  - `tests/engine/chapters/test_agent_integration.py` lines 109, 255, 272, 273

After all patches, `pytest tests/ -x -q --ignore=tests/e2e --ignore=tests/db/integration` MUST pass with zero failures. Maps to R210-4, R210-5.

### FR-005: Log-normal base + chapter coefficients + per-chapter caps (v2)

**Priority**: P1
**Description**: Replace `TIMING_RANGES` Gaussian model with log-normal × chapter coefficient × per-chapter cap in `nikita/agents/text/timing.py`. Formula: `delay = min(cap_ch, exp(μ + σ·Z) × c_ch × M)`.

Constants (module-level `Final` values):
- `LOGNORMAL_MU = 2.996`, `LOGNORMAL_SIGMA = 1.714` (median base ≈ 20s)
- `CHAPTER_COEFFICIENTS = {1:0.15, 2:0.30, 3:0.50, 4:0.75, 5:1.00}`
- `CHAPTER_CAPS_SECONDS = {1:10, 2:60, 3:300, 4:900, 5:1800}`

Legacy `TIMING_RANGES` kept for reference only (no longer used by `calculate_delay`). Module docstring updated to document log-normal model and link to `docs/models/response-timing.md`.

### FR-006: ResponseTimer.calculate_delay with momentum + gate (v2)

**Priority**: P1
**Description**: `ResponseTimer.calculate_delay(self, chapter, *, is_new_conversation=True, momentum=1.0) -> int`:
- `is_new_conversation=False` → return 0 (ongoing conversation, no delay)
- Dev-mode bypass (environment=development or debug=True) → return 0
- Otherwise: sample `raw = exp(μ + σ·Z) × c_ch × momentum`, clamp to `[0, cap_ch]`, return int
- `calculate_delay_human_readable` forwards both kwargs
- Full formula components logged at INFO: `[TIMING] ch=N is_new=T m=X.XX base=Ys coeff=Z -> delay=Ws (cap=C)`

### FR-007: New-conversation detection in handler

**Priority**: P1
**Description**: Add a private helper `_is_new_conversation(self, last_message_at: datetime | None) -> bool` in `TextAgentHandler` (located in `nikita/agents/text/handler.py`, NOT in `session_detector.py` — that class is batch-only per its docstring at line 24). Semantics:

- If `last_message_at is None` → return `True` (first message ever; feels like a fresh conversation).
- Else: return `True` if `datetime.now(tz=UTC) - last_message_at > timedelta(minutes=TEXT_SESSION_TIMEOUT_MINUTES)`, where `TEXT_SESSION_TIMEOUT_MINUTES = 15` is imported from `nikita.context.session_detector`.

Maps to R210-7.

### FR-008: Extend handler.handle() signature + wire gate at line 391

**Priority**: P1
**Description**:
- Extend `TextAgentHandler.handle()` (currently at `handler.py:185+`) with a new keyword-only parameter: `last_message_at: datetime | None = None`. Default `None` preserves current behavior for callers that don't yet pass the value.
- At the current line 391 (`delay_seconds = self.timer.calculate_delay(chapter)`), replace with:
  ```python
  is_new_conv = self._is_new_conversation(last_message_at)
  delay_seconds = self.timer.calculate_delay(chapter, is_new_conversation=is_new_conv)
  ```
- Log the decision at INFO level: `logger.info("[TIMING] user=%s chapter=%s is_new_conv=%s delay=%ds", ...)`.

Maps to R210-6, R210-7.

### FR-009: Pass last_message_at through Telegram caller

**Priority**: P1
**Description**: Update `nikita/platforms/telegram/message_handler.py:350–357` (the `text_agent_handler.handle(...)` call site) to pass `last_message_at=conversation.last_message_at` (from the loaded `Conversation` row — field at `nikita/db/models/conversation.py:97`). Do NOT re-query; the value is already in the pipeline context. Maps to R210-6, R210-7.

### FR-010: Preserve boss-state / won-state bypass

**Priority**: P1
**Description**: The existing bypass at `handler.py:330–356` (which returns `ResponseDecision(delay_seconds=0, ...)` during `game_status == 'won'` and `game_status == 'boss_fight'`) MUST remain unchanged. The new-conversation gate applies ONLY to the normal response path (the current line 391). Document this in both the handler docstring AND the `timing.py` module docstring: "Boss fights and post-game (won) states always respond immediately, bypassing the new-conversation gate." Maps to R210-10.

### FR-011: Runtime timing override setting

**Priority**: P2
**Description**: Add `timing_ranges_override: dict[int, tuple[int, int]] | None = None` to `nikita/config/settings.py` (Pydantic field). When set, `ResponseTimer.calculate_delay` MUST merge the override over `TIMING_RANGES` per chapter (missing chapter keys fall back to the module constants). Enables runtime tuning via env var without a code redeploy. Must be parsed defensively — malformed JSON/values MUST NOT crash Cloud Run boot; fall back to `None` and log a warning. Maps to R210-9.

### FR-012: Supersede Spec 026 AC-5.x

**Priority**: P2
**Description**: Add a prominent header note to `specs/026-text-behavioral-patterns/spec.md`: "⚠️ AC-5.x (skip-rate acceptance criteria) superseded by Spec 210 as of 2026-04-12. Skip feature deleted — see Spec 210 for replacement (new-conversation-gated variable response times)." Do NOT move Spec 026 to `specs/archive/` — the rest of its content (typing cadence, behavioral patterns) remains in effect. Only the skip-related ACs (AC-5.2.1 and AC-5.2.5 per `handler.py` comment references) are superseded. Update ROADMAP.md Domain 2 row 026 notes accordingly. Maps to R210-11.

### FR-013: Momentum coefficient (EWMA ratio)

**Priority**: P1
**Description**: Add `compute_momentum(gap_history, chapter) -> float` and `_compute_user_gaps(messages) -> list[float]` in `nikita/agents/text/conversation_rhythm.py`.

Momentum M adapts Nikita's responsiveness to the user's recent messaging cadence via EWMA seeded at `B_ch` (chapter baseline). Constants:
- `CHAPTER_BASELINES_SECONDS = {1:300, 2:240, 3:180, 4:120, 5:90}`
- `MOMENTUM_ALPHA = 0.35`, bounds `[0.1, 5.0]`, window size 10
- `SESSION_BREAK_SECONDS = 900` (gaps ≥ this are dropped)

Gap extraction: filter to user-only turns, parse timestamps, drop session breaks (≥900s), floor at 1s, return last 10 deltas.

Handler wiring: `handler.py` computes gaps + momentum before calling `calculate_delay(chapter, is_new_conversation=is_new, momentum=momentum)`. Feature-flagged via `settings.momentum_enabled` (default True). `MOMENTUM_ENABLED=false` → M=1.0 (no-op rollback).

Bayesian interpretation: EWMA ≈ Normal-Normal conjugate posterior mean (σ_obs=0.6, σ_prior=0.8).

### FR-014: Monte Carlo validator

**Priority**: P2
**Description**: `scripts/models/response_timing_mc.py` validates the model via MC simulation:
- Percentile CSV per chapter → `docs/models/response-timing-percentiles.csv`
- Histogram + CDF + momentum-trace PNGs → `docs/models/`
- Assertions: Ch1 cap enforcement, monotonic medians, feedback-spiral boundedness (200 sessions × 20 msgs), EWMA unbiasedness (10k sessions, E[M] = 1.0 ± 0.05)
- Exit 0/1. Runtime <30s. Run via `uv run python scripts/models/response_timing_mc.py`.

### FR-015: Model documentation + interactive artifact

**Priority**: P2
**Description**:
- Long-form doc at `docs/models/response-timing.md`: formula, parameters, MC results, citations, pitfalls
- Interactive artifact at `portal/src/app/admin/research-lab/response-timing/page.tsx`: 14-section native React page with MC simulator, momentum traces, conversation transient, cold-start distribution, chapter × cadence heatmap, persona day, Bayesian equivalence
- Stochastic-models rule at `.claude/rules/stochastic-models.md`: codifies distribution → MC → docs → artifact workflow

---

## User Stories

### US-1: Chapter 1 player gets responses to every message

**As a** new player in Chapter 1
**I want to** receive a response to every message I send
**So that** the game feels alive and I don't question whether the chatbot is broken

**Acceptance Criteria**:
- [ ] AC-1.1: When I send a message in Chapter 1, Nikita always responds (no silent drops). Verified: integration test sends 20 messages in Chapter 1, asserts 20 `ResponseDecision(should_respond=True)` results.
- [ ] AC-1.2: The `nikita/agents/text/skip.py` module does not exist after this spec ships. Verified: `ls nikita/agents/text/skip.py` returns "No such file."
- [ ] AC-1.3: No `skip_rates_enabled` feature flag exists in settings. Verified: `rg "skip_rates_enabled" nikita/ tests/` returns zero hits.

**Priority**: P1

### US-2: Chapter 1 player gets near-instant responses in an active conversation

**As a** Chapter 1 player in an ongoing back-and-forth
**I want to** receive responses within seconds of sending a message
**So that** the conversation feels live and human, not like waiting for an email reply

**Acceptance Criteria**:
- [ ] AC-2.1: Two messages sent within 10 seconds of each other each receive responses with `delay_seconds == 0` (ongoing conversation, gate=False). Verified: unit test calls `ResponseTimer.calculate_delay(chapter=1, is_new_conversation=False)` → returns 0.
- [ ] AC-2.2: When the new-conversation gate is True at Chapter 1, the returned delay is in `[1, 10]` seconds across N=200 samples (statistical check). Verified: unit test with gaussian sampling distribution assertion.
- [ ] AC-2.3: The Telegram call site at `message_handler.py:350–357` passes `last_message_at` to `handler.handle()`. Verified: unit test inspects the call kwargs.

**Priority**: P1

### US-3: Returning player feels Nikita's "availability" scale with chapter

**As a** player returning to the conversation after a long break
**I want to** wait longer for the first reply in later chapters
**So that** the relationship feels like it's evolving — early chapters feel eager, later chapters feel comfortable/settled

**Acceptance Criteria**:
- [ ] AC-3.1: New-conversation delay at Chapter 1 is within `[1, 10]` seconds. Verified: statistical sampling unit test.
- [ ] AC-3.2: New-conversation delay at Chapter 5 is within `[120, 1800]` seconds (2 to 30 min). Verified: statistical sampling unit test.
- [ ] AC-3.3: `_is_new_conversation(last_message_at)` returns True when `now() - last_message_at > 15 min`, False otherwise, True when `last_message_at is None` (first message ever). Verified: unit test with `freezegun` or manual datetime injection.

**Priority**: P1

### US-4: Boss fights stay urgent regardless of session gap

**As a** player in a boss encounter
**I want to** get immediate responses even if I haven't messaged Nikita in hours
**So that** the fight feels tense and real-time

**Acceptance Criteria**:
- [ ] AC-4.1: When `deps.user.game_status == 'boss_fight'`, `handler.handle()` returns `delay_seconds=0` regardless of `last_message_at` value. Verified: integration test sets `last_message_at = now() - 2 hours`, game_status='boss_fight', asserts delay=0.
- [ ] AC-4.2: Same for `game_status == 'won'` (post-game conversation). Verified: parallel test case.

**Priority**: P1

### US-5: Platform operator can tune timing without a deploy

**As a** platform operator
**I want to** override `TIMING_RANGES` via an environment variable
**So that** I can A/B-test delay ranges or tune for latency without redeploying

**Acceptance Criteria**:
- [ ] AC-5.1: Setting `TIMING_RANGES_OVERRIDE='{"1": [0, 1]}'` (or equivalent) makes Chapter 1 new-conversation delays collapse to 0–1s while other chapters stay at their defaults. Verified: unit test injects override, calls `calculate_delay(1, True)`, asserts return value ∈ [0, 1].
- [ ] AC-5.2: Malformed override (e.g., non-JSON string, non-integer values) does NOT crash the app; it's logged as a warning and the override is ignored. Verified: unit test with invalid env var, asserts ResponseTimer still loads and uses constants.

**Priority**: P2

### US-6: Existing tests stay green

**As a** developer maintaining the codebase
**I want to** be confident that removing the skip feature does not break unrelated tests
**So that** this spec ships cleanly and doesn't leave a graveyard of skipped tests

**Acceptance Criteria**:
- [ ] AC-6.1: After all deletions and patches, `pytest tests/ -x -q --ignore=tests/e2e --ignore=tests/db/integration` passes with zero failures.
- [ ] AC-6.2: No test is marked `@pytest.mark.skip` or `@pytest.mark.xfail` as a workaround for this spec. If a test is no longer applicable, it is deleted outright (not silenced).

**Priority**: P1

---

## Non-Functional Requirements

### NFR-001: Performance

- Removing skip reduces branch count in `handle()` — should have no measurable perf regression.
- `calculate_delay` short-circuit at `is_new_conversation=False` returns in <1μs (no gaussian sampling, no settings lookup beyond an early return).

### NFR-002: Observability

- `[TIMING]` log line at INFO level for every response decision MUST include: `user_id`, `chapter`, `is_new_conversation`, `delay_seconds`. This enables post-hoc diagnosis of unexpected delays.
- No new metrics endpoint required.

### NFR-003: Backward Compatibility

- `handler.handle()` accepts `last_message_at: datetime | None = None` with a default — existing callers that don't pass the value MUST continue to work (they'll be treated as new-conversation, which is safe-default behavior).
- Deleting `skip.py` is breaking for any external consumers, but `rg` confirms no external consumers exist in the `nikita/` tree.

### NFR-004: Rollback

- This spec has no feature flag (the feature is deleted, not toggled). Rollback path: `git revert` the spec's merge commit.
- Rationale: a flag for `skip_rates_enabled` already exists and it's OFF by default in production (see current `settings.py`). The feature was effectively already dead in prod — we're cleaning it up, not changing live behavior of active users.

### NFR-005: Test Coverage

- Unit test coverage for `ResponseTimer.calculate_delay` with all 5 chapters × 2 gate states (10 cases).
- Integration test coverage: handler with last_message_at fresh (<15min) and stale (>15min), across at least Chapter 1 and Chapter 5.
- Statistical test for gaussian distribution of re-tuned `TIMING_RANGES` (Chapter 1: N=200 samples in [1,10]; Chapter 5: N=200 samples in [120,1800]).

---

## Constraints & Assumptions

### Constraints (from `.claude/CLAUDE.md` and project rules)

- PR MUST be under 400 lines. Mostly deletions, so this is feasible in one PR.
- TDD enforced: write failing tests FIRST, commit separately from implementation.
- Supabase migrations MUST go through `mcp__supabase__apply_migration` (not applicable here — no schema change).
- Feature-flag naming convention: `{feature}_enabled: bool` (we're removing one, not adding).
- Commit scopes: `feat(agent)`, `chore(agent)`, `test(agent)`, `refactor(agent)`.
- GATE 2 validators: 6 parallel SDD validator agents (frontend N/A, api N/A, auth N/A — backend logic only; data-layer N/A — no schema; testing + architecture fully in scope).

### Assumptions

- The `skip_rates_enabled` flag is currently OFF in production. Verified in the brief's codebase orientation — `SKIP_RATES_DISABLED` returns zeros when flag is off, so prod behavior is "never skip." Deleting the feature preserves current prod behavior; it only removes dead code.
- `conversation.last_message_at` is populated correctly in the DB. Verified: `Conversation` model at `nikita/db/models/conversation.py:97` has the column with proper timestamping in the message-write path.
- `TEXT_SESSION_TIMEOUT_MINUTES = 15` from `session_detector.py:21` is the canonical "new conversation" boundary across the codebase. Other domains (voice, onboarding) may have different boundaries but this spec uses the text-domain constant.
- No voice-agent code depends on `skip.py` — verified by `rg` in the brief.

---

## Out of Scope

- **Activity-aware delay** (delays driven by "what is Nikita doing right now" from the life-simulation engine). `nikita/life_simulation/` works at a daily granularity; hourly per-message routing is a follow-up spec, not 210.
- **Voice call availability changes.** `AVAILABILITY_RATES`, `CHAPTER_TTS`, and other chapter-keyed gates unrelated to text response timing are NOT touched.
- **New cron jobs.** The existing `/tasks/deliver` endpoint (every-minute) already processes the `scheduled_events` queue that `timing.py` writes to. No new cron needed.
- **Nikita-initiated voice calls from the text side.** That is Spec 211 (phone-reveal gate) and beyond.
- **Portal UI changes.** This spec is backend-only.
- **ElevenLabs / Twilio API calls.** Not touched.
- **Re-tuning `AVAILABILITY_RATES`, `CHAPTER_TTS`, or `CHAPTER_BEHAVIORS`.** Those are chapter-keyed but unrelated to message-response timing.

---

## Open Questions

_None._ The planning brief at `~/.claude/plans/delightful-orbiting-ladybug.md` was devil's-advocate-reviewed and process-audited. All CRITICAL and HIGH findings were remediated before this spec was drafted. Any remaining ambiguities are intentionally left to the implementer's judgment (e.g., exact jitter factor for gaussian sampling — current default of 0.1 is retained).

---

## Traceability

| Brief Requirement | Spec Artifact |
|-------------------|---------------|
| R210-1 (delete skip.py) | FR-001, AC-1.2, SC-7 |
| R210-2 (remove handler wiring) | FR-002 |
| R210-3 (remove flag) | FR-003, AC-1.3 |
| R210-4, R210-5 (delete + patch tests) | FR-004, US-6 |
| R210-6 (is_new_conversation gate) | FR-006, FR-008, AC-2.1, AC-3.3 |
| R210-7 (session detector reuse) | FR-007, AC-3.3 |
| R210-8 (re-tune TIMING_RANGES + human_readable) | FR-005, FR-006, AC-3.1, AC-3.2 |
| R210-9 (runtime override setting) | FR-011, US-5 |
| R210-10 (boss-state bypass preserved) | FR-010, US-4 |
| R210-11 (supersede 026 AC-5.x) | FR-012 |

---

## Files Affected (from brief)

### Source (modify/delete)

| Action | Path | Notes |
|--------|------|-------|
| **DELETE** | `nikita/agents/text/skip.py` | 136 lines, all skip machinery |
| **MODIFY** | `nikita/agents/text/handler.py` | Remove lines 33, 189, 203, 358–373; rework line 391; extend handle() sig; add `_is_new_conversation()` helper |
| **MODIFY** | `nikita/agents/text/timing.py` | Extend `calculate_delay` sig; re-tune `TIMING_RANGES`; update `calculate_delay_human_readable` |
| **MODIFY** | `nikita/platforms/telegram/message_handler.py` | Pass `last_message_at` through at lines 350–357 |
| **MODIFY** | `nikita/config/settings.py` | Remove lines 197–201 (`skip_rates_enabled`); add `timing_ranges_override` field |
| **MODIFY** | `specs/026-text-behavioral-patterns/spec.md` | Add supersession header note |
| **MODIFY** | `ROADMAP.md` | Already done in pre-spec registration step |

### Tests (delete/patch/add)

| Action | Path | Notes |
|--------|------|-------|
| **DELETE** | `tests/agents/text/test_skip.py` | Entire file |
| **DELETE** | `tests/agents/text/test_handler_skip.py` | Entire file |
| **PATCH** | `tests/integration/test_flag_group_a.py` | Remove `TestSkipRatesEnabled` class |
| **PATCH** | `tests/integration/test_all_flags.py` | Lines 30, 259, 357 |
| **PATCH** | `tests/integration/test_boss_flow.py` | Lines 206, 235, 254 |
| **PATCH** | `tests/engine/chapters/test_agent_integration.py` | Lines 109, 255, 272, 273 |
| **NEW** | `tests/agents/text/test_timing.py` (extend existing if present, else new) | Cover new `is_new_conversation` gate + re-tuned ranges + statistical sampling |
| **NEW** | `tests/agents/text/test_handler_new_conversation.py` | Cover `_is_new_conversation` helper + handler wire-through |

---

## References

- Planning brief: `~/.claude/plans/delightful-orbiting-ladybug.md`
- Superseded spec: `specs/026-text-behavioral-patterns/spec.md` (AC-5.x only)
- Related: Spec 022 (life-simulation-engine), Spec 038 (conversation-continuity — defines 15-min session timeout), Spec 108 (voice-agent-optimization)
- Paired future spec: Spec 211 (phone-reveal gate) — not blocked by 210, but shares text-agent code surface

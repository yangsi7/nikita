# Frontend Validation Report — Spec 214 (GATE 2 iter-2)

**Spec**: `specs/214-portal-onboarding-wizard/spec.md` (amended 2026-04-19)
**Companion**: `specs/214-portal-onboarding-wizard/technical-spec.md`
**Iteration**: 2 (re-validation after iter-1 patches)
**Validator**: sdd-frontend-validator
**Timestamp**: 2026-04-19
**Status**: **PASS**
**Verdict**: 0 CRITICAL + 0 HIGH (PASS bar met). 1 MEDIUM + 1 LOW.

---

## Scoreboard

| Severity | Count | Delta vs iter-1 |
|---|---|---|
| CRITICAL | 0 | -1 (C1 resolved) |
| HIGH | 0 | -4 (H12, H13, H14, H15 resolved) |
| MEDIUM | 1 | unchanged class |
| LOW | 1 | unchanged class |

---

## Iter-1 Finding Resolution Verification

### C1 — useConversationState reducer hydrate action — RESOLVED

**Original gap**: reducer lacked `{type: "hydrate"}` action; race risk between server JSONB and localStorage on mount; no StrictMode dedup.

**Verification**:
- `spec.md:566` AC-NR1b.2 mandates explicit `{ type: "hydrate", turns, extractedFields, progressPct, awaitingConfirmation }` action dispatched from `useEffect` (NOT initial render).
- Hydrate source order specified: (1) server JSONB via `GET /portal/onboarding/profile`, (2) localStorage as latency fallback, (3) JSONB wins on conflict.
- 50ms dedup window (`STRICTMODE_GUARD_MS` in `nikita/onboarding/tuning.py`) explicitly named — see `technical-spec.md:693` tuning table.
- `technical-spec.md:500-509` enumerates the full action union: `hydrate | user_input | server_response | server_error | timeout | retry | truncate_oldest | confirm | reject_confirmation | clearPendingControl`. All five new action types from the iter-1 finding are typed.
- Test specified: "mounted component dispatches `hydrate` exactly once (StrictMode enabled); server-data-post-local overrides local turns; no flash of empty state."

**Verdict**: fully resolved. Action shape, dispatch site, dedup window, conflict resolution, and test all spec'd.

### H12 — Fix-that ghost-turn UX — RESOLVED

**Original gap**: spec didn't define how rejected user input renders after `Fix that` tap.

**Verification**:
- `spec.md:737` AC-11d.4b: rejected user turn marked `superseded: true`, rendered at `opacity: 0.5` (no strikethrough), Nikita's next bubble explicitly acknowledges ("OK let me ask again." hardcoded fallback if LLM variant absent).
- Reducer dispatches `{ type: "clearPendingControl" }` on REJECTED so prior control is hidden and replaced by re-ask control (no stale pre-fill from superseded turn).
- Snapshot test specified: `supersededTurn` class + inline `opacity: 0.5`; next Nikita bubble matches "ask again" pattern; pending control cleared before next control renders.
- Persistence: `spec.md:749` AC-11d.10 includes `superseded?: boolean` in the `Turn` JSONB shape; round-trip test specified.

**Verdict**: fully resolved. Visual state, reducer action, screen-reader behavior, and persistence all spec'd.

### H13 — InlineControl god-dispatcher + retired subcomponents — RESOLVED

**Original gap**: `InlineControl.tsx` was a fat switch over 5 prompt types; retired `EdginessSlider` / `SceneSelector` / `DossierStamp` / `HandoffStep` had ambiguous fates.

**Verification** (`technical-spec.md:304-313`):
- `InlineControl` reduced to slim ~30 LOC dispatcher reading from a `controls/` registry.
- Decomposed into 5 typed controls: `TextControl`, `ChipsControl`, `SliderControl`, `ToggleControl`, `CardsControl` — each at `portal/src/app/onboarding/components/controls/`.
- Subcomponent fates explicit:
  - `EdginessSliderStep` → SUPERSEDED by `SliderControl` (Phase D delete deferred, moved to `legacy/`).
  - `SceneSelectorStep` → SUPERSEDED by `CardsControl`.
  - `DossierStamp` → REMAINS mounted inside `ClearanceGrantedCeremony`.
  - `HandoffStep` → refactored to render `ClearanceGrantedCeremony`.
  - All others → MOVED (not deleted) to `portal/src/app/onboarding/steps/legacy/` behind feature flag `USE_LEGACY_FORM_WIZARD`.
- `technical-spec.md:635, 644` rollback path: flip `USE_LEGACY_FORM_WIZARD=true` → form wizard restored from `legacy/` directory.

**Verdict**: fully resolved. Decomposition + subcomponent disposition + rollback path all spec'd.

### H14 — aria-live per-bubble semantics — RESOLVED

**Original gap**: per-bubble `aria-live` would cause duplicate NVDA/JAWS announcements (nested live regions); spec didn't address.

**Verification** (`spec.md:753` AC-11d.12b):
- `role="log"` + `aria-live="polite"` ONLY on `ChatShell` scroll container.
- `MessageBubble` MUST NOT carry `aria-live` (explicitly forbidden).
- Typewriter content `aria-hidden="true"` during reveal.
- Sibling `<span class="sr-only">` carries the full final string after typewriter completion → screen readers announce exactly once.
- Test specified: axe-core passes + unit test asserts `MessageBubble` has no `aria-live` attr + sr-only sibling contains final text after typewriter completion tick.

**Verdict**: fully resolved. Container-only live region + sr-only final-string pattern matches WCAG + NVDA/JAWS best practice.

### H15 — No virtualization / no turn ceiling — RESOLVED

**Original gap**: `ChatShell` would DOM-bloat past ~50 turns; no documented turn ceiling.

**Verification** (`spec.md:750` AC-11d.10b + `spec.md:571` AC-NR1b.5):
- 100-turn hard cap (AC-NR1b.5; oldest elided on overflow with extracted fields preserved).
- `react-virtuoso` (or equivalent windowed list) with `followOutput="smooth"`.
- Threshold: <20 turns eager render permitted; ≥20 turns windowing active.
- Test specified: render 100 fixture turns and assert DOM contains ≤30 `MessageBubble` nodes at any scroll offset; new-turn append smooth-scrolls to bottom.
- Reducer action `truncate_oldest` typed explicitly in `technical-spec.md:506`.

**Verdict**: fully resolved. Library choice, threshold, hard cap, and reducer truncation action all spec'd.

---

## New Additions Verification

### USE_LEGACY_FORM_WIZARD feature flag — VERIFIED

- `technical-spec.md:310, 635-644` defines flag as env var + portal Settings surface; default `false` post-PR-3 ship; `true` for break-glass rollback.
- Phase A: legacy step components MOVED (not deleted) to `portal/src/app/onboarding/steps/legacy/`.
- Phase D (PR 5, ≥7 days post-Phase-A AND after AC-11d.13c gate PASS): legacy directory deleted.
- Rollback path enumerated per PR.

**Status**: spec'd correctly. Flag presence + rollback path both explicit.

### localStorage v1→v2 synthesis path (AC-NR1b.3) — VERIFIED

- `spec.md:560, 567`: v1 state (without `conversation`) hydrates to v2 by synthesizing empty `conversation: []`.
- Extracted fields from v1 state preserved (user does not repeat questions).
- Wizard starts a fresh conversation on first `converse` call.
- Schema-version bump triggers the migration shim explicitly.
- Additive only; no DB schema migration required.

**Status**: synthesis path is NON-LOSSY for mid-wizard returning users — extracted fields survive intact; only the conversation thread starts fresh, which is the correct UX (resuming with empty thread + filled fields means agent sees prior extractions and only asks what's missing).

### Mint-timing: POST /portal/link-telegram BEFORE ClearanceGrantedCeremony paint — VERIFIED

- `technical-spec.md §2.6` (lines 289-291) explicitly addresses the S9 diagram gap.
- Sequence: reducer's `server_response` action with `conversation_complete=true` → calls `POST /portal/link-telegram` → stores `{ code, expiresAt }` in state → THEN dispatches transition to CEREMONY.
- `ClearanceGrantedCeremony` reads `code` from reducer state (pure presentation, never initiates the mint).
- Test specified: "on the final confirm turn, assert POST /portal/link-telegram is called exactly once before `ClearanceGrantedCeremony` paints; subsequent mounts of the ceremony do not re-mint."

**Status**: gap closed. Mint happens in reducer transition handler before ceremony component mounts; no race, no duplicate mint on re-render.

### React 19 StrictMode double-fire guard (50ms dedup window) — VERIFIED

- `technical-spec.md:693` tuning constant `STRICTMODE_GUARD_MS = 50` with rationale comment.
- `spec.md:566` AC-NR1b.2 references the constant in the dedup window pattern.
- Reducer records last hydrate timestamp; ignores re-dispatches within 50ms.
- StrictMode-enabled mount-test specified.

**Status**: spec'd at the correct level (tuning constant + AC + test).

### Ghost turn + REJECTED clearPendingControl reducer flag — VERIFIED

- `technical-spec.md:509`: `{ type: "clearPendingControl" }` action typed in the union, comment "(M2) REJECTED state clears stale pre-filled control".
- `spec.md:737` AC-11d.4b: dispatched on REJECTED state so prior control is hidden and replaced by re-ask control.
- Snapshot test asserts pending control is cleared before next control renders.

**Status**: action typed + dispatch site + test all spec'd.

---

## Standing Frontend Checks (re-verified for completeness)

### Accessibility (WCAG 2.1 AA)

| Check | Spec ref | Status |
|---|---|---|
| Keyboard nav (Tab cycle input → send → controls → back; Enter submits) | spec.md:752 AC-11d.12 | PASS |
| Visible focus rings on controls | spec.md:752, technical-spec.md:338 | PASS |
| Visible label on input field | spec.md:752 | PASS |
| `role="log"` + `aria-live="polite"` on chat scroll region (container only) | spec.md:753 AC-11d.12b | PASS |
| `aria-hidden="true"` on typewriter mid-reveal | spec.md:753 | PASS |
| sr-only sibling for final-string announcement | spec.md:753 | PASS |
| `prefers-reduced-motion` disables typewriter + stamp | spec.md:778 AC-11e.1, technical-spec.md:339 | PASS |
| Cards radiogroup with managed tabindex (existing pattern) | spec.md:285 AC-9.4 | PASS (carry-over) |
| QR `<figure>` + `<figcaption>` (not aria-label on canvas) | spec.md:622 AC-NR4.4 | PASS (carry-over) |
| axe-core suite specified | spec.md:752 | PASS |

### Responsive Design

| Check | Spec ref | Status |
|---|---|---|
| Desktop QR breakpoint ≥768px | spec.md:619 AC-NR4.1 | PASS |
| Mobile reflow on chat shell | not breakpoint-explicit | LOW finding (see below) |
| Touch targets ≥44px on inline controls | not explicit | LOW finding (see below) |

### Dark Mode

The portal is a single-theme dark site (per existing onboarding pages). Spec does not introduce theme-toggle requirements. Existing theme tokens apply. No new requirement.

### Forms & Validation

| Check | Spec ref | Status |
|---|---|---|
| In-character validation (no red banner) | spec.md:721, 738 AC-11d.5 | PASS |
| Server-enforced extraction hard-block (age <18, non-E.164, country) | spec.md:738 AC-11d.5 (b) | PASS |
| Confirmation loop UI ([Yes] [Fix that]) | spec.md:736 AC-11d.4 | PASS |
| Loading/typing-indicator state | spec.md:717, 729 AC-11d.1 | PASS |
| Error/timeout fallback (in-character, source="fallback") | spec.md:746 AC-11d.9 | PASS |
| 429 in-character bubble + Retry-After + transparent retry | spec.md:746 AC-11d.9 | PASS |

### State Management

| Check | Spec ref | Status |
|---|---|---|
| Reducer action union typed | technical-spec.md:499-510 | PASS |
| Hydrate from JSONB + localStorage with conflict resolution | spec.md:566 AC-NR1b.2 | PASS |
| Optimistic UI (push user turn, push Nikita on response) | technical-spec.md:512 | PASS |
| 100-turn ceiling + windowing | spec.md:571, 750 | PASS |
| useOnboardingAPI.converse() — no retry wrapper (non-idempotent) | technical-spec.md:320 | PASS |
| Idempotency-Key / turn_id client-generated UUIDv4 | spec.md:733, technical-spec.md:149 | PASS |

### Performance

| Check | Spec ref | Status |
|---|---|---|
| Lazy load / suspense for chat shell | not specified | not applicable (chat shell is the route's primary concern) |
| Bundle size budget +50KB gzipped max | spec.md:908 | PASS (carry-over from NR-1) |
| Virtualization above 20 turns | spec.md:750 | PASS |
| Typewriter rate (40 char/sec, 1.5s cap) | spec.md:717 | PASS |

---

## Findings

| ID | Severity | Category | Location | Issue | Recommendation |
|----|----------|----------|----------|-------|----------------|
| F-1 | MEDIUM | Responsive | `spec.md` chat-UI section | No explicit mobile-vs-desktop breakpoint behavior for `ChatShell` (input height, send button placement, control wrap, virtuoso item heights). Spec covers QR @ 768px breakpoint (AC-NR4.1) and pixel widths for progress bar but is silent on mobile-keyboard interaction with the input form (visualViewport API, scroll-into-view on focus). | Add an AC under FR-11d covering: (a) on mobile, the input field stays visible above the soft keyboard via `visualViewport.height` listener; (b) tap targets on inline controls ≥44×44px (AAA touch target); (c) chip grid wraps to 1-column at <360px viewport; (d) virtuoso item-height measurement re-runs on `resize` event. Non-blocking — most tooling defaults work, but spec'ing prevents regression. |
| F-2 | LOW | Performance | `technical-spec.md:303-309` | `controls/` registry not literally defined. Spec says InlineControl "reads from a controls/ registry" but doesn't show the registry shape (e.g. `Record<PromptType, ComponentType>` vs lazy import map). Implementation will likely choose static imports given React Server Component constraints, but a one-line TS shape would lock in tree-shake-friendly authoring. | Add a 5-line snippet under §3.1: `export const CONTROL_REGISTRY: Record<NextPromptType, ComponentType<ControlProps>> = { text: TextControl, chips: ChipsControl, slider: SliderControl, toggle: ToggleControl, cards: CardsControl };` and cite that lazy import is OUT (would force Suspense around every control). Optional — implementation will resolve this. |

---

## Verdict

**PASS** — 0 CRITICAL + 0 HIGH satisfies the GATE 2 PASS bar.

All 5 iter-1 findings (1 CRITICAL + 4 HIGH) are explicitly resolved with cited AC numbers, action types, test specifications, and tuning constants. New additions (USE_LEGACY_FORM_WIZARD flag, v1→v2 synthesis, mint-before-paint, StrictMode dedup, clearPendingControl reducer flag) are all spec'd at the correct artifact level (AC + technical-spec section + test).

The 1 MEDIUM (F-1: mobile keyboard / touch targets / chip wrap) and 1 LOW (F-2: controls registry shape) are non-blocking quality refinements suitable for capture as MEDIUM/LOW issues in `validation-findings.md` per `.claude/CLAUDE.md` GATE 2 protocol step (c). Neither blocks Phase 5 (planning).

Frontend domain clears for Phase 5.

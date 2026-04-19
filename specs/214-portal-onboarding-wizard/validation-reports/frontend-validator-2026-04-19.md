# Frontend Validation Report, Spec 214 Amendment (FR-11c/d/e + NR-1b)

**Spec**: `/Users/yangsim/Nanoleq/sideProjects/nikita/specs/214-portal-onboarding-wizard/spec.md`
**Technical Spec**: `/Users/yangsim/Nanoleq/sideProjects/nikita/specs/214-portal-onboarding-wizard/technical-spec.md`
**Status**: FAIL (1 CRITICAL, 4 HIGH, 6 MEDIUM, 3 LOW)
**Timestamp**: 2026-04-19
**Scope**: FR-11d (AC-11d.1 to AC-11d.13), FR-11e (AC-11e.1), NR-1b, Portal component tree §3

---

## Summary

- CRITICAL: 1
- HIGH: 4
- MEDIUM: 6
- LOW: 3

Strengths outweigh issues. The amendment is 80% ready; the CRITICAL is a single underspecified behavior that is easy to patch in a spec revision before `/plan` begins.

---

## Findings

### CRITICAL

**C-1: Resume-from-localStorage / resume-from-JSONB behavior undefined in `useConversationState` reducer**
Location: technical-spec.md:331-337 (reducer actions); spec.md:537-567 (NR-1b)
The reducer action enumeration is `user_input | server_response | server_error | confirm | reject_confirmation`. NR-1b mandates full-thread rehydration on page refresh (localStorage + JSONB), but there is no `hydrate` / `resume` action in the state machine. Without an explicit hydration action, either (a) the parent component does an imperative mutation of reducer state (anti-pattern, React 19 StrictMode will double-fire and corrupt turns), or (b) the initial-state factory reads localStorage synchronously inside `useReducer(init, initialArg, initializer)` — which works but MUST be specified because SSR + Next.js client hydration will mismatch unless the initializer uses a `useEffect` deferred-hydrate pattern. This is the same SSR-mismatch trap that necessitated the `useMediaQuery` `defaultValue: false` pattern called out elsewhere in the spec (spec.md:605).
Recommendation: Add `{ type: "hydrate"; turns: Turn[]; extractedFields: Partial<OnboardingProfile>; progressPct: number; awaitingConfirmation: boolean }` to the action union. Specify that hydration fires inside `useEffect(() => dispatch({type: "hydrate", ...}), [])` on mount, never during initial render, to keep SSR output deterministic. Specify precedence when localStorage and JSONB disagree (JSONB wins, per NR-1 AC-NR1.4 which already covers extracted fields but NR-1b currently doesn't restate for `conversation`).

---

### HIGH

**H-1: Optimistic UI flicker on confirmation-loop rejection is undefined**
Location: technical-spec.md:339 (reducer optimistic behavior); spec.md:726 (AC-11d.4)
Spec says "pushes user's turn immediately; pushes Nikita's turn on server response." But when the user types a value that triggers `confirmation_required=true` and the user then taps "Fix that", the already-pushed user turn is stale — it still shows the wrong value. Does the "Fix that" branch delete the user's turn? Mark it visually struck-through? Insert an "OK, let's correct that" Nikita bubble? No AC resolves this. Live users will see a ghost of their wrong answer sitting above the correction prompt.
Recommendation: Add AC-11d.4 sub-clause: on `reject_confirmation`, either (a) the rejected user turn remains visible and Nikita's next bubble says "OK let me ask again" then re-prompts, OR (b) the rejected turn is visually dimmed (`opacity: 0.5`) to signal it was superseded. Choose one and snapshot-test it.

**H-2: `InlineControl.tsx` dispatcher risks becoming a god-component; decomposition not specified**
Location: technical-spec.md:235 (single dispatcher for 5 sub-types)
A single `InlineControl.tsx` dispatching on `next_prompt_type` for text / chips / slider / toggle / cards conflates five distinct UIs. Today that may be ~200 LOC; six months from now, when "darkness" adds a haptic preview, "backstory" adds card-deck keyboard nav, and chips get chip-selection-state timing, this becomes a 600+-LOC switch. Existing portal already has `edginess-slider.tsx` (Radix-based per Spec 081) and `scene-selector.tsx` (custom card picker) that are reusable Radix primitives. The technical spec does NOT say whether these survive or are rewritten. Dead-import risk in the rewritten `onboarding-wizard.tsx`.
Recommendation: Decompose into `InlineControl.tsx` (dispatcher only, ~30 LOC) + `controls/TextControl.tsx`, `controls/ChipsControl.tsx`, `controls/SliderControl.tsx`, `controls/ToggleControl.tsx`, `controls/CardsControl.tsx`. Explicitly document in §3.3 whether existing `edginess-slider.tsx` and `scene-selector.tsx` are (a) reused by the new controls, (b) rewritten, or (c) deleted. Today's §3.3 only enumerates the top-level step-component deletions.

**H-3: `role="log"` + `aria-live="polite"` semantics per-message-bubble vs. per-container are conflated**
Location: technical-spec.md:259; spec.md:734 (AC-11d.12)
W3C ARIA 1.2 says `role="log"` implies `aria-live="polite"` by default, so declaring both on `ChatShell` is redundant but harmless. However, AC-11d.12 says "every new message announces via `aria-live='polite'` to screen readers". The correct pattern is the live region on the CONTAINER (ChatShell), with new children appended to it — the screen reader announces each appended child. Per-`MessageBubble` `aria-live` attributes would double-announce and is an anti-pattern. This is NOT disambiguated in either the spec or tech spec. A naive implementor will add `aria-live="polite"` to every MessageBubble and ship a broken screen-reader experience.
Recommendation: §3.4 should explicitly state: "`aria-live="polite"` lives ONLY on `ChatShell`'s log region. `MessageBubble` does NOT carry `aria-live` attributes. New messages are announced by the container live-region as children append." Also add an AC that screen readers narrate the FINAL state of a typewriter-revealed message, not each character tick — best practice is to render the full text into an `aria-hidden="true"` typewriter DOM node, then hold the full string in a sibling `<span class="sr-only">` that appears AFTER the typewriter finishes. This is a non-trivial pattern and unspecified today.

**H-4: Large-conversation rendering performance unaddressed (virtualization)**
Location: technical-spec.md:232 (ChatShell container) and no mention of virtualization
AC-11d.10 persists the full conversation array indefinitely. A resumed session from a user who previously corrected 4 fields could easily hit 30-50 turns. A pathological backtracking session could hit 100. React will re-render every `MessageBubble` on each new turn push because the `turns` array identity changes. On low-end mobile (the stated adult-playtime primary device per original NR-5), this will jank. No virtualization library (`react-virtuoso`, `tanstack-virtual`) is specified. Typewriter reveal + layout thrash from N>50 DOM nodes is a known hazard.
Recommendation: Either (a) add an explicit NR stating "typical wizard completes in ≤20 turns; virtualization out of scope" (accept the risk with documented ceiling), OR (b) specify `react-virtuoso` or equivalent for `ChatShell`, with `followOutput="smooth"` for scroll-to-latest behavior. One-liner spec change, big future-regression prevention.

---

### MEDIUM

**M-1: Typewriter implementation technology unspecified**
Location: spec.md:723 (AC-11d.1 ~40 chars/sec, cap 1.5s); technical-spec.md:246 (`useOptimisticTypewriter.ts`)
The hook exists in §3.2 but its internals are undefined. Three viable choices with different tradeoffs: (a) `setInterval` with React state updates (simple, 40 renders/sec per bubble, stops on unmount cleanup), (b) `requestAnimationFrame` with calculated character count from elapsed time (smooth, better on React 19 concurrent), (c) CSS `@keyframes` with `width` animation on a monospace mask (no JS but requires monospace font or `max-width` approximation). Framer Motion `animate={{ width }}` is option-c dressed up. Each has different behavior under React 19 concurrent rendering + Suspense.
Recommendation: Pick one and document in §3.2. Given cap 1.5s and ≤40 chars, `requestAnimationFrame` with a reducer-tracked character offset is the boring-obvious choice and cleanest on unmount. Also call out: typewriter MUST be tied to `useEffect` cleanup — unmount during reveal should NOT leak timers.

**M-2: Typing indicator placement (inline-in-thread vs. above-input) not specified**
Location: spec.md:723 (AC-11d.1 "typing indicator precedes every Nikita message by 0.5-1s")
"Precedes" is ambiguous. Two patterns: (a) the indicator renders AS the next turn in the message thread (iMessage-style bubble containing pulsing dots, replaced by the actual Nikita bubble when server responds), or (b) the indicator renders above or next to the input field (WhatsApp-style presence line). Each has different DOM structure + `role="log"` consequences. Option (a) is standard; option (b) is easier to reset but confuses the log semantic.
Recommendation: Pick (a) inline-in-thread, document that the indicator is treated as a transient log entry with `aria-hidden="true"` (so screen readers don't announce "loading" three times).

**M-3: Responsive breakpoints for `ClearanceGrantedCeremony` QR visibility not stated**
Location: spec.md:757 (AC-11e.1 "QR on desktop per NR-4")
NR-4 AC-NR4.2 defines desktop as ≥768px. AC-11e.1 says "QR on desktop per NR-4" but does not explicitly say QR is hidden on mobile. A mobile user already has the phone; showing a QR to scan with your own phone is absurd. The existing `QRHandoff.tsx` handles this per spec.md:605 (useMediaQuery defaultValue:false). AC-11e.1 should restate the mobile-hides-QR contract explicitly so the `ClearanceGrantedCeremony` DOM snapshot test passes unambiguously.
Recommendation: AC-11e.1 sub-clause: "On viewport <768px, the QR block is not rendered; only the CTA button is visible. Same useMediaQuery SSR pattern as `QRHandoff.tsx` (defaultValue: false, mount-effect hydrate)."

**M-4: Dark-mode bubble color contrast not specified**
Location: No AC addresses color tokens
Portal is dark-mode default per NFR-004 (original spec) and PR #294 aesthetic. No AC or §3 entry specifies bubble colors, contrast ratios, or design-token references. Nikita bubbles and user bubbles need distinct colors passing WCAG AA (4.5:1) on the dark background. Typing indicator dots must be visible — a pulsing gray-on-gray fails readability. No reference to existing `tailwind.config.ts` token set.
Recommendation: §3.4 should add: "Nikita bubbles use `bg-secondary/90`, user bubbles use `bg-primary/20 border-primary/40`, both with `text-foreground`. Typing indicator dots use `bg-muted-foreground` with 60%-100% opacity pulse. All pairs must pass WCAG AA on the current dark-theme `--background`. Verified by an axe-core contrast check in the accessibility suite."

**M-5: Focus management on new Nikita message not specified**
Location: spec.md:734 (AC-11d.12 keyboard nav listed but focus-on-new-message silent)
When a new Nikita message arrives (especially after typewriter reveal finishes), does focus stay on the chat input, jump to the new controls (chips / slider), or remain where the user left it? The tab order is specified but the imperative focus decision is not. Best practice: focus STAYS on the chat input; new controls become Tab-reachable but are not auto-focused (auto-focus steals from typing users). This needs to be said out loud.
Recommendation: AC-11d.12 addendum: "On new Nikita turn arrival, focus does NOT move automatically. The chat input retains focus. Inline controls are Tab-reachable per declared tab order but are never auto-focused."

**M-6: Error-state rendering for `server_error` action unspecified**
Location: technical-spec.md:334 (reducer has `server_error` action); spec.md:727 (AC-11d.5 covers in-character validation, NOT network errors)
AC-11d.5 covers in-character validation errors (age <18, etc.) with no red banner. But the reducer's `server_error` branch handles the case where the fetch to `/converse` fails entirely (network drop, 500 server error not caught by the fallback contract). What does the UI show? A Nikita "something glitched, try again" bubble? A retry button? Toast? AC-11d.9 only covers server-side fallbacks; it doesn't cover client-side network failures.
Recommendation: Add AC-11d.9 sub-clause or new AC-11d.14 covering client-side error UX: "On fetch failure (network, 5xx not recovered by server fallback), render a Nikita-voiced bubble `I'm glitching, one sec — tap to retry.` with a retry button that replays the last `converse` call. No toast, no red banner."

---

### LOW

**L-1: `ClearanceGrantedCeremony` transition-in style not specified**
Location: spec.md:757 (AC-11e.1)
Does the ceremony crossfade from the chat thread, slide up, instant cut? Given a stamp animation is the centerpiece, an instant cut may feel jarring; a 200ms crossfade is typical. Not a blocker but will bike-shed in review.
Recommendation: Add a sentence to AC-11e.1: "Ceremony scene crossfades from the chat thread over 300ms (Framer Motion AnimatePresence with `mode='wait'`). Reduced-motion replaces the crossfade with an instant swap."

**L-2: i18n/locale flow for fallback strings not explicit**
Location: technical-spec.md:148 (`locale: Literal["en"] = "en"`); tech-spec §11 out-of-scope says multi-language not supported
Locale is pinned to "en" in the backend schema and LLM replies are English-only. Fallback copy in `copy.ts` (new location per spec) is presumably English. This is internally consistent but should be stated: fallback and LLM share the same locale contract for forward compatibility.
Recommendation: Add a line in §3.3: "All wizard copy (fallback + LLM) is English. Fallbacks are loaded from `portal/src/app/onboarding/steps/copy.ts`. Future localization is out of scope and guarded by the `locale` schema field."

**L-3: Progress-bar animation not specified**
Location: spec.md:730 (AC-11d.8 "bar width maps to progress_pct")
Should the bar snap to new width instantly or animate? A ~300ms `width` transition is almost universal but not stated. Snapshot test may fail ambiguously without this contract.
Recommendation: "`ProgressHeader` progress bar animates width over 400ms with `ease-out`. Reduced-motion renders the final width instantly."

---

## Component Inventory (derived from §3.1-3.3)

| Component | Type | Shadcn/Radix? | Notes |
|---|---|---|---|
| ChatShell.tsx | Custom | Uses Tailwind + scroll | Owner of `role="log"` + `aria-live` |
| MessageBubble.tsx | Custom | Framer Motion | Typewriter host; impl tech unresolved (M-1) |
| TypingIndicator.tsx | Custom | CSS keyframes | Placement unresolved (M-2) |
| InlineControl.tsx | Dispatcher | Delegates | Risk of god-component (H-2) |
| ProgressHeader.tsx | Custom | Radix Progress? | Token unspecified (L-3) |
| ConfirmationButtons.tsx | Custom | Shadcn Button | Standard usage |
| ClearanceGrantedCeremony.tsx | Custom | Framer Motion + QRHandoff | Transition unspecified (L-1) |
| PipelineGate.tsx (keep) | Existing | - | Unchanged |
| HandoffStep.tsx (refactor) | Existing | - | Becomes thin wrapper |
| Retired: LocationStep, SceneStep, DarknessStep, IdentityStep, BackstoryReveal, PhoneStep | DELETED | - | Dead-import risk in rewrite |

Existing sub-components (`DossierStamp.tsx`, `DossierReveal.tsx`, `edginess-slider.tsx`, `scene-selector.tsx`, `ambient-particles.tsx`, `scroll-progress.tsx`, `nikita-quote.tsx`, `section-header.tsx`): survival/reuse/deletion not documented. See H-2.

---

## Accessibility Checklist (against AC-11d.12 + §3.4)

- [x] `role="log"` on ChatShell
- [x] `aria-live="polite"` (ambiguity in scope, see H-3)
- [x] Keyboard tab order declared: input → send → controls → progress bar
- [x] Visible input label required
- [x] Visible focus rings on controls
- [x] `prefers-reduced-motion` disables typewriter + stamp
- [ ] Focus-on-new-message policy (MISSING, M-5)
- [ ] Screen-reader final-vs-streaming character strategy (MISSING, part of H-3)
- [ ] Color contrast tokens (MISSING, M-4)
- [ ] axe-core target in CI (mentioned, not concrete)

---

## Responsive / Dark Mode Checklist

- [x] Desktop-only QR stated (mobile hidden inferred from NR-4, not restated in AC-11e.1, see M-3)
- [ ] MessageBubble max-width per viewport (not specified)
- [ ] Dark-mode color tokens (MISSING, M-4)
- [x] `prefers-reduced-motion` handled
- [ ] Typing indicator dark-mode contrast (MISSING, M-4)

---

## Strengths

1. **Accessibility baseline is serious**: `role="log"`, `aria-live`, reduced-motion, axe-core enforcement, keyboard-nav integration test, visible labels + focus rings. Few onboarding specs I have reviewed commit to axe-core in CI; this one does. (AC-11d.12)
2. **Retirement plan is explicit**: LocationStep / SceneStep / DarknessStep / IdentityStep / BackstoryReveal / PhoneStep are named for deletion. PipelineGate and HandoffStep kept-and-refactored are called out. This is cleaner than most spec rewrites. (§3.3)
3. **State-machine replacement is principled**: typed `ConversationState` + `ConversationAction` union in TypeScript. Reducer semantics (optimistic user turn, server-response Nikita turn) documented. Parent-owned `isComplete` → ceremony mount is clean. (§5.2)
4. **Persistence contract is per-turn and symmetric**: localStorage + JSONB mirror on every `converse` call. Schema shape example given verbatim. Version-bumped localStorage key. NR-1b is cleanly additive. (AC-11d.10, NR-1b)
5. **Fallback contract is rigorous**: 2500ms endpoint SLA, `source="fallback"` sentinel field, validator gates (140-char cap, markdown reject, quote reject, PII concat reject) on LLM output. Client renders fallback transparently. This is better than most LLM-backed endpoints. (AC-11d.9)
6. **Persona fidelity is load-bearing and testable**: cross-agent persona-drift test compares conversation agent vs. main text agent vs. handoff greeting with ≥80% tone overlap. This is the right primitive. (AC-11d.11, AC-11e.4)
7. **Ceremonial closeout is well-motivated**: clear theatrical boundary between portal and Telegram, reduced-motion fallback, QR desktop-only, CTA reuses the PR #322 deep-link mechanism (no duplication). (FR-11e, AC-11e.1)
8. **Testing plan covers both layers**: component unit tests (ChatShell / MessageBubble / InlineControl / ProgressHeader / ClearanceGrantedCeremony), hook test (useConversationState), E2E Playwright walk. (§7.2, §7.3)

---

## Pass/Fail Criteria

- **PASS** requires 0 CRITICAL + 0 HIGH findings.
- **This validation: FAIL** (1 CRITICAL, 4 HIGH).

## Must-Fix Before Planning (`/plan`)

1. **C-1**: Add `hydrate` action to reducer; specify SSR-safe `useEffect` hydration pattern; document localStorage vs JSONB precedence.
2. **H-1**: Define optimistic-UI behavior on "Fix that" rejection (ghost-turn handling).
3. **H-2**: Decompose `InlineControl.tsx` into dispatcher + 5 sub-components; document fate of existing `edginess-slider.tsx`, `scene-selector.tsx`, `DossierStamp.tsx`, `DossierReveal.tsx`.
4. **H-3**: Clarify `aria-live` lives on container only, not on MessageBubbles; document screen-reader narration strategy for typewriter reveal.
5. **H-4**: Either accept ≤20-turn ceiling in writing or specify `react-virtuoso`.

MEDIUM items (M-1..M-6) should be resolved during `/plan` phase; LOW items (L-1..L-3) are cleanup for the planner.

# GATE 2: Frontend Validation Report — Spec 218

**Spec**: `specs/218-onboarding-wizard-v2-agent-driven/spec.md` (553 lines)
**Brief**: `~/.claude/plans/immutable-wondering-gray.md` (8-component lock §23.1, REUSE LOCKS §20)
**Validator**: sdd-frontend-validator
**Timestamp**: 2026-05-09
**Tool-call budget**: 8 (used: 2 — Read spec, Write report)

---

## Verdict

**FAIL** — Two HIGH findings on shadcn-primitive mapping and reusable shell-component identification leave frontend implementation under-specified despite excellent single-thread + 8-shape lock + accessibility scaffolding.

---

## Severity Counts

- CRITICAL: 0
- HIGH: 2
- MEDIUM: 4
- LOW: 3

---

## Findings

### HIGH-1 — shadcn primitive mapping per component shape is absent from spec body
**FR/AC**: FR-005 (Supported Component Shapes), Constraints §Technical Constraints
**Issue**: FR-005 enumerates 8 shapes by name (short text, long text, single_select, chip_multi, slider, calendar, phone, completion celebration) but never declares the shadcn primitive each shape MUST compose from. Per `feedback_use_shadcn_via_components_json_strictly.md` and `portal/components.json` (new-york style, `@/components/ui` aliases), every FE component shape must map to a registered shadcn primitive BEFORE planning. The brief §20 REUSE LOCKS reportedly contain this mapping; the spec does not echo it. Implementation will drift to ad-hoc primitives.
**Recommended fix**: Add a table to FR-005 (or a new FR-005a) of the form:

| Shape | shadcn primitive(s) | Notes |
|---|---|---|
| short text | `Input` + `Form` | RHF + zod via `Form` provider |
| long text | `Textarea` + `Form` | autoresize wrapper |
| single_select | `RadioGroup` OR `Select` | declare which |
| chip_multi | `ToggleGroup type="multiple"` OR `Badge`-as-chip | declare which |
| slider | `Slider` | with `aria-valuetext` |
| calendar | `Calendar` + `Popover` | DOB-mode |
| phone | `Input` + libphonenumber-js | format-as-you-type |
| completion celebration | `Card` + animated emblem | NOT a Dialog |

### HIGH-2 — Reusable wizard shell components ("Ask card", waveform, modal) are unnamed
**FR/AC**: FR-001 (single-thread DOM), FR-009 (opt-in modal), FR-010 (full-screen takeover)
**Issue**: Spec mandates ONE narrator-voiced prompt + ONE typed control per turn but does NOT name the reusable React component that holds them (e.g., `<AskCard>` or `<TurnContainer>`). It also does not name the phone-demo modal component, the full-screen takeover surface, or the animated waveform component. Without component-shape names in spec, the planner cannot enforce the single-thread invariant via component contract — the invariant becomes prose-only.
**Recommended fix**: Add FR-001a "Wizard Shell Component Contract" naming: `<TurnContainer>` (single child slot for prompt + single child slot for component), `<PhoneOptInModal>` (shadcn `AlertDialog`), `<PhoneDemoTakeover>` (full-viewport surface, NOT a Dialog), `<CallingWaveform>` (decorative animation). The single-thread invariant becomes structurally enforceable.

### MEDIUM-1 — FR-010 phone-demo takeover does not specify focus-trap mechanics
**FR/AC**: FR-010, AC-003-003, AC-003-006, NFR Accessibility ("Phone-demo opt-in modal MUST trap focus and announce via aria-live")
**Issue**: NFR-Accessibility correctly requires focus trap + aria-live for the OPT-IN MODAL (FR-009). FR-010 introduces a SECOND blocking surface (the full-screen takeover during the call) but never states whether it trap-focuses, whether it has an aria-live region announcing "Nikita's calling… connected… ended", and whether ESC is suppressed (it should be — call is in flight). AC-003-006 covers timeout but not announcement.
**Recommended fix**: Extend FR-010 with: "Takeover MUST trap focus, announce call lifecycle transitions via `aria-live="polite"` ('Nikita is calling', 'Connected', 'Call ended'), and MUST NOT respond to ESC or back-navigation while call is in flight."

### MEDIUM-2 — FR-007 DAG invalidation modal text contract not specified
**FR/AC**: FR-007, AC-006-001
**Issue**: AC-006-001 contains the only modal text ("changing city will reset hangouts — proceed?"). For other anchor slots (age, occupation) that also gate hangouts_personalized (FR-006), the modal text is unspecified. Spec also does not declare the shadcn primitive (should be `AlertDialog`, not `Dialog`, given destructive-edit semantics) or button labels ("Proceed" / "Cancel" vs. "Reset" / "Keep").
**Recommended fix**: Add an AC-006-001a covering age/occupation modal text + naming `AlertDialog` as the primitive. Decide button labels (recommend: "Reset hangouts" destructive variant + "Cancel" outline variant).

### MEDIUM-3 — FR-016 state replay UX (conversation log re-render) not specified for FE
**FR/AC**: FR-016, US-5, AC-005-001, AC-005-002, AC-005-003
**Issue**: FR-016 is BE-state-replay focused ("rebuild cumulative slot state from log + snapshot"). AC-005-001 says "wizard resumes at the next unanswered slot in the same single-thread layout" but does NOT specify whether prior conversation turns are RE-RENDERED above the active turn (creating a scrollback log) or whether only the active turn shows. US-5 prose suggests "with prior conversation visible" but the AC lacks the visibility requirement. Independent Test references "3 prior turns visible" — confirming intent — but FR-016 doesn't codify it.
**Recommended fix**: Amend AC-005-001 to: "Then the wizard resumes at the next unanswered slot AND the prior N submitted turns are rendered above it as a read-only scrollback log (each turn showing the narrator-voiced prompt and the user's submitted value)." This makes the FE re-render contract testable.

### MEDIUM-4 — FR-014 voice dictation accessibility incomplete
**FR/AC**: FR-014, AC-008-001, AC-008-002, NFR Accessibility
**Issue**: AC-008-002 covers graceful degradation (toggle hidden if API unavailable) — good. But: (a) no aria-label specified for the mic toggle (recommend: "Start voice dictation" / "Stop voice dictation"), (b) no aria-live announcement when transcription engages or ends, (c) no specification of behavior when permission is denied vs. unavailable (different states; iOS Safari prompts on tap). Permission-denied is the common failure mode and is unhandled.
**Recommended fix**: Add AC-008-003: "Given dictation permission is denied by the user, When they tap the mic toggle, Then an inline tooltip or toast explains how to grant permission and the toggle returns to off-state without breaking text entry."

### LOW-1 — No explicit responsive breakpoint requirements
**FR/AC**: Constraints §User Constraints ("Mobile-first design, target completion <90s on a phone")
**Issue**: Spec is mobile-first by intent but doesn't enumerate the Tailwind breakpoints (sm/md/lg) at which layout might shift (e.g., does the scrollback log become a side panel on `lg`?). Likely fine to defer to plan.md.
**Recommended fix**: Consider adding a one-liner: "Layout MUST be single-column on `<lg`; `lg+` MAY render scrollback in a side rail." Or accept LOW and defer.

### LOW-2 — Dark mode not addressed
**FR/AC**: NFR Accessibility
**Issue**: Spec does not mention dark mode, theme toggle, or contrast requirements per theme. Portal already runs dark — assumed inherited — but the spec doesn't say so.
**Recommended fix**: Add one line to NFR Accessibility: "All component shapes MUST render correctly under the portal's dark theme (already canonical) with WCAG AA contrast." Or accept LOW.

### LOW-3 — Animated waveform performance / `prefers-reduced-motion` unspecified
**FR/AC**: FR-010 ("animated waveform")
**Issue**: Spec mandates an animated waveform during call takeover but doesn't address `prefers-reduced-motion` users. WCAG 2.3.3 (Animation from Interactions) says non-essential animation must be disable-able.
**Recommended fix**: Add a note to FR-010: "Waveform animation MUST respect `prefers-reduced-motion`; users with reduced-motion preference see a static iconography variant."

---

## Component Inventory (derived from spec)

| Component | Type | Shadcn primitive (recommended) | Status in spec |
|---|---|---|---|
| TurnContainer (single-thread shell) | Custom | `Card` body | UNNAMED (HIGH-2) |
| ShortTextSlot | Custom | `Input` + `Form` | shape named, primitive missing |
| LongTextSlot | Custom | `Textarea` + `Form` | shape named, primitive missing |
| SingleSelectSlot | Custom | `RadioGroup` or `Select` | shape named, primitive missing |
| ChipMultiSlot | Custom | `ToggleGroup type="multiple"` | shape named, primitive missing |
| SliderSlot | Custom | `Slider` | shape named, primitive missing |
| CalendarSlot (DOB) | Custom | `Calendar` + `Popover` | shape named, primitive missing |
| PhoneSlot | Custom | `Input` + intl-tel-input | shape named, primitive missing |
| CompletionCelebration | Custom | `Card` + emblem | shape named, primitive missing |
| PhoneOptInModal | Custom | `AlertDialog` | UNNAMED (HIGH-2) |
| PhoneDemoTakeover | Custom | full-viewport surface | UNNAMED (HIGH-2) |
| CallingWaveform | Custom | SVG/Lottie | UNNAMED (HIGH-2) |
| BackEditConfirmModal | Custom | `AlertDialog` | UNNAMED (MEDIUM-2) |
| MicDictationToggle | Custom | `Button` ghost+icon | UNNAMED (MEDIUM-4) |

---

## Coverage Map

| FR/AC | Frontend concern | Status |
|---|---|---|
| FR-001 | Single-thread DOM (one prompt + one control, no siblings) | PASS — clearly enforced; AC-001-005 falsifiable |
| FR-005 | 8-component-shape lock | PASS for shape count; FAIL for shadcn-primitive mapping (HIGH-1) |
| FR-005 | No 9th `reaction_only` shape | PASS — explicitly forbidden in FR-005 + Constraints |
| FR-007 | DAG invalidation modal | PASS for invalidation logic; FAIL for modal text contract beyond city (MEDIUM-2) |
| FR-009 | Phone-demo opt-in modal w/ default-skip | PASS — AC-003-001 covers default-focus, modal text, branches |
| FR-010 | Phone-demo full-screen takeover | PASS for takeover requirement; FAIL for focus-trap + aria-live mechanics (MEDIUM-1) |
| FR-014 | Voice dictation toggle | PASS for happy + unavailable; FAIL for permission-denied (MEDIUM-4) |
| FR-016 | State replay UX | PASS for BE-state replay; FAIL for FE conversation-log re-render contract (MEDIUM-3) |
| AC-001-005 | Single-thread DOM assertion | PASS — directly testable |
| AC-006-001 | DAG invalidation confirmation modal | PARTIAL — text given for city only |
| AC-008-002 | Voice dictation graceful degradation (browser API absent) | PASS — toggle hidden when unavailable |
| NFR Accessibility | WCAG 2.1 AA | PASS at high level; PARTIAL on focus-trap of takeover (MEDIUM-1) |
| NFR Accessibility | Voice dictation not sole text path | PASS — FR-014 explicit |
| Mobile-first <90s target | Responsive breakpoints | LOW gap (LOW-1) |
| Dark mode contract | Theme | LOW gap (LOW-2) |
| `prefers-reduced-motion` | Waveform animation | LOW gap (LOW-3) |

---

## What is excellent (worth keeping)

- **Single-thread DOM invariant (FR-001 + AC-001-005)** is exemplary. The "ONE narrator-voiced prompt + ONE typed control, NEVER sibling streams" rule is unambiguous and falsifiable via DOM inspection.
- **8-component-shape lock with explicit no-9th-shape clause (FR-005)** correctly cites the bulldoze rationale and prevents `reaction_only` re-introduction.
- **Phone-demo opt-in (FR-009)** with default-skip + TCPA rationale + AC-003-001 covering default-focus is well-formed.
- **DAG invalidation (FR-007)** has explicit user-confirm-before-apply semantics and AC coverage for confirm/cancel branches.
- **State replay separation (FR-016)** between log-authoritative + snapshot fast-path is a sound pattern.
- **Independent test specifications** for every user story name the walk (B6, B7, etc.) and assertions concretely.

---

VERDICT: FAIL — CRITICAL=0 HIGH=2 MEDIUM=4 LOW=3

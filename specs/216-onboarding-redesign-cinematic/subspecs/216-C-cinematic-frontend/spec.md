# Subspec 216-C — Cinematic Frontend

**Parent**: `specs/216-onboarding-redesign-cinematic/spec.md` FR-02, FR-08, FR-09, FR-10, FR-11, NR-04, NR-07, NR-08
**PR boundary**: 216-C (depends on 216-B + 216-D merged for endpoint + archetype contracts)
**Estimated**: ~400 LOC TSX components + ~150 LOC vitest tests
**Status**: Draft (GATE 1)

---

## Scope

Implement the 12-screen cinematic wizard inheriting Spec 208 landing design system verbatim. Components composed from existing landing primitives (AuroraOrbs, GlowButton, glass-card utilities, Geist Sans/Mono, EASE_OUT_QUART). 10 base screens + 0-6 dynamic follow-up screens depending on agent decisions. Per-slot input components dispatch by `control_type` from `TurnOutput`. Backstory archetype card screen renders 3 LLM-picked archetypes from the curated 12-list. Magic-link landing → `/onboarding` resumes mid-wizard from `nikita.conversation_jsonb`. Auto-redirect to `/dashboard` on `is_complete=true`.

Wireframes in `wireframes/{ascii,figma,motion-spec}.md` — ASCII has full per-screen layouts (mobile + desktop), Figma has 20 frames live at file key `3c5uJdNeAnAnIV5cZXvamM`.

## Acceptance Criteria

| AC | Description | Severity |
|----|-------------|----------|
| **C1.1** | All 15 base wizard screens implemented matching `wireframes/ascii.md` + `wireframes/figma.md` (welcome + 11 visual slot screens + backstory pick + completion; `together_we_could` and `same_weird_if` slots collected from one combined screen with two textareas per C1.18). Visual screen ordering (post-welcome): `display_name → age → city → occupation → darkness_level → primary_hobbies → saturday_morning → geek_out_on → together/odd combined → phone → voice_tone_pref → backstory_pick → completion`. Backstory pick is the cinematic climax AFTER phone + voice_tone_pref (per FR-09). Visual diff against Figma frames ≤2% pixel drift on mobile + desktop. | HIGH |
| **C1.2** | Design tokens inherited from Spec 208: `bg-void` `oklch(0.08 0 0)`, rose primary `oklch(0.75 0.15 350)`, Geist Sans + Mono, glass-card surfaces. NO new tokens introduced. | CRIT |
| **C1.3** | AuroraOrbs + GlowButton imported from `portal/src/components/landing/`. NO duplication. Aurora orb opacity dimmed (0.4 → 0.25) on wizard surface via prop, not new component. | HIGH |
| **C1.4** | AnimatePresence `mode="wait"` on screen transitions. opacity + y + blur 350ms `[0.22, 1, 0.36, 1]`. `prefers-reduced-motion: reduce` honored: instant transitions, paused AuroraOrbs, disabled hover. ProgressRail still animates (informational). | HIGH |
| **C1.5** | Wizard renders correctly mobile 390×844 + desktop 1440×900. NO horizontal scroll. All CTAs reachable without zoom. Tested via `mcp__claude-in-chrome__resize_window`. | HIGH |
| **C1.6** | `HobbyChips` component: 100 chips × 10 categories (Music, Movement, Gaming, Reading, Food & Drink, Travel, Art & Making, Tech & Gear, Outdoors & Nature, Social & Nightlife). Cross-category autocomplete-filter. Enforced 3-5 picks (Continue disabled outside this range with inline tooltip "pick 3-5"). "+ other" free-text: **hard cap at 40 chars** (`maxLength=40`); inline helper text shows `${len}/40` and turns rose at len ≥35; trim leading/trailing whitespace pre-submit; reject empty-after-trim. Stagger-reveal motion per `wireframes/motion-spec.md` §4.3. (Resolves frontend-validator HIGH-2 hard-cap-vs-warn ambiguity.) | HIGH |
| **C1.7** | `BackstoryArchetypeCards`: 3 LLM-archetype cards from curated 12-list ONLY. Hover state translates `y: -4` + glow opacity 0 → 0.4 (250ms EASE_OUT_QUART). Select state: pulse scale 1.0 → 1.02 → 1.0 (300ms) + ring opacity 0 → 1 + non-selected card 100ms tail blur. NO invented labels (validated against `archetypes.py` 12-list at render time). | HIGH |
| **C1.8** | `ProgressRail`: width animates from prev % to new % via spring (stiffness 120, damping 20). Width never decreases (matches BE `progress_pct` monotonic guarantee). FE simply reflects BE `progress_pct`; no FE-side computation. | HIGH |
| **C1.9** | `NikitaReaction` (≤140 chars typewriter-reveal 200ms after screen settle) + `WhyWeAsk` (1 sentence Nikita-voiced) per screen. | MED |
| **C1.10** | All CTAs reachable mobile + desktop. 0 hydration mismatches in console. 0 React warnings. 0 4xx/5xx in network tab during happy-path walk (verified via `mcp__claude-in-chrome__read_console_messages` + `read_network_requests`). | HIGH |
| **C1.11** | 0 banned vocab (`FILE`, `dossier`, `clearance`, `FIELD`) in server-rendered HTML at `/onboarding`, `/onboarding/auth`, `/dashboard`. Verified via `curl -s https://nikita-mygirl.com/onboarding \| rg -i '\b(dossier\|clearance)\b\|\b(FILE\|FIELD)\b'` (word-boundary; uppercase-only for FILE/FIELD) returning 0 matches. | HIGH |
| **C1.12** | **Accessibility (a11y) — closes frontend-validator HIGH-1**. Per-control ARIA + keyboard contracts: <br/>• `HobbyChips`: `role="group"` + `aria-label="primary hobbies"`; each chip is `<button>` with `aria-pressed={selected}`; autocomplete input has `role="combobox"` + `aria-expanded` + `aria-autocomplete="list"`; live-region (`aria-live="polite"`) announces `${count}/5 picked`. <br/>• `BackstoryArchetypeCards`: `role="radiogroup"` + `aria-label="pick a backstory"`; cards are `<button role="radio" aria-checked>`; arrow-key roving `tabindex` (use Radix `RadioGroup` from shadcn). <br/>• `controls/Slider.tsx`: uses Radix `<Slider>` (NOT custom-built); `aria-valuetext` formatted as `darkness ${value}/10`. <br/>• `controls/Tel.tsx`: `inputMode="tel"`, `autocomplete="tel"`, `aria-describedby` for E.164 hint, `aria-invalid` on validation fail. <br/>• `ProgressRail`: `role="progressbar"` + `aria-valuenow={progress_pct}` + `aria-valuemin=0` + `aria-valuemax=100` + `aria-label="onboarding progress"`. <br/>• `NikitaReaction`: typewriter wrapped in `aria-live="polite" aria-atomic="true"`; `prefers-reduced-motion` reveals text instantly into the same live region. <br/>• `WizardShell`: focus auto-moves to new screen's `<h1 tabIndex={-1}>` after `AnimatePresence` exit; ESC blocked (no modal); Tab order: Back → headline → control → Continue. <br/>• Visible focus ring on `GlowButton` + chips + cards (`focus-visible:ring`); never `focus:outline-none` without alternative. <br/>• `<main id="wizard">` landmark with `aria-label="onboarding wizard"`. <br/>• Mobile touch targets ≥44px on `HobbyChips`, `BackstoryArchetypeCards`, `SuggestionChips`. <br/>• **Textarea pattern (Geek-Out screen + Together/Odd combined per C1.18)**: each `<textarea>` carries per-slot `aria-label`, `aria-describedby` linking the slot's WhyWeAsk block, `aria-required="true"`, `aria-invalid` on length-fail. <br/>• **Dual-textarea group (Screen 10, combined Together/Odd)**: outer `<fieldset role="group" aria-labelledby="screen-10-heading">` wraps both textareas so screen-reader users perceive them as co-required; group-level `<legend>` summarizes "what we'd do together / the specific weird thing"; Continue button has `aria-describedby` linking the combined helper "both fields ≥10 chars". | HIGH |
| **C1.13** | **Auth guard (Server Component cookie read) — closes frontend-validator HIGH-4**. `/onboarding/page.tsx` is a Server Component that reads `nikita-session` cookie via Next.js `cookies()` API. On missing/expired JWT → `redirect('/onboarding/auth')` BEFORE any client component mounts. `WizardShell` never sees an unauthenticated render. Idempotent `/auth/confirm` second-click handled per master spec §HTTP API Contracts (302 if session live, 400 if not). NO hydration mismatch on first paint (verified via `mcp__claude-in-chrome__read_console_messages`). | HIGH |
| **C1.14** | Pending/error UI states: Continue button enters pending state (disabled + spinner) on submit; on >2s pending, `NikitaThinkingDots` replaces reaction text; on network 4xx (excluding 401-redirect), inline rose-toned error banner with "try again" CTA; on cost-circuit fallback (200 + `meta.fallback_reason="cost_circuit"`), the static fallback question renders silently without error UI. | MED |
| **C1.15** | Resume mid-wizard UX (NR-07): on `/onboarding` mount with non-empty `conversation_jsonb`, FE issues `GET /api/v1/onboarding/state` to fetch latest turn payload; `ProgressRail` animates from 0 to resumed `progress_pct` on first paint; `NikitaReaction` renders resumed `nikita_reaction` (or "welcome back" if first hydrated turn after resume). NO "Welcome back" banner. (Closes frontend-validator MEDIUM-2.) | MED |
| **C1.16** | AnimatePresence key uniqueness on dynamic follow-ups: `<motion.div key={turn_id}>` (NOT `slot_kind`) — `turn_id` is the server-issued UUID per turn. Documented in motion-spec.md as "AnimatePresence key is stable per turn, never reused across dynamic follow-ups sharing slot_kind." (Closes frontend-validator MEDIUM-3.) | MED |
| **C1.17** | ProgressRail reduced-motion: `useReducedMotion()` returns true → swap spring for `transition={{ duration: 0.2, ease: "linear" }}`. Width still updates monotonically; no overshoot. (Closes frontend-validator MEDIUM-4.) | MED |
| **C1.18** | **Wizard total = 15 visual screens** (welcome + 11 visual slot screens + backstory pick + completion); BE captures 13 SlotKind enum members per FR-02. `together_we_could` and `same_weird_if` are both populated from ONE combined screen with two textareas (headline `T O G E T H E R   /   O D D`), per CRO free-text-fatigue mitigation. Both slots remain individually validated by FinalForm (B1.2). Resume mid-wizard restores to last incomplete slot per C1.15. Screen ordering fixed by C1.1. | HIGH |
| **C1.19** | **Midpoint sunk-cost nudge**: on `saturday_morning` screen (visual screen 8 of 15), narrator-voice line `Halfway. Six down, six to go.` renders ONCE in dim text-muted color above headline, only on first render of that screen (not on resume). Implementation: `useState(true)` + `useEffect` to false post-render. Industry pattern (Bumble/Hinge): explicit midpoint acknowledgment lifts completion 2-4%. (Per CRO review §8.) | MED |
| **C1.20** | **Narrator vs persona voice modes** (per Style Guide in plan brief Appendix 3): `WhyWeAsk` text uses third-person narrator voice ("Your city sets where Nikita lives"); `NikitaReaction` text uses first-person Nikita voice ≤140 chars ("zürich. okay."). Welcome screen + completion screen + all error/loading states use narrator voice. Underage-gate refusal stays Nikita-voice (`"sorry. you have to leave."`) as the in-character refusal moment. Backstory cards stay first-person Nikita ("I wrote three versions of us") as the diegetic arrival beat. | HIGH |

## Critical Files

### NEW components (`portal/src/app/onboarding/_components/`)
| File | Role |
|------|------|
| `WizardShell.tsx` | Top-level wrapper: AuroraOrbs background, AnimatePresence orchestration, slot dispatch, JWT cookie auth guard |
| `QuestionCard.tsx` | Glass-card surface containing NikitaReaction + WhyWeAsk + control + Continue/Back |
| `ProgressRail.tsx` | Top-of-screen monotonic progress bar |
| `NikitaReaction.tsx` | Typewriter reveal of agent's reaction text |
| `WhyWeAsk.tsx` | "Why we ask" expandable 1-sentence helper |
| `HobbyChips.tsx` | 100-chip multi-select 3-5 with category groups + autocomplete + "+ other" |
| `BackstoryArchetypeCards.tsx` | 3-card archetype selector with hover/select states |
| `controls/TextInput.tsx` | text slot |
| `controls/Slider.tsx` | darkness 0-10 |
| `controls/Chips.tsx` | small-set chip select (e.g., voice_tone_pref radio) |
| `controls/Scenarios.tsx` | scenario picker (3-card option) |
| `controls/Radio.tsx` | radio buttons |
| `controls/Tel.tsx` | E.164 phone input |
| `controls/CityInput.tsx` (NEW) | Aceternity `placeholders-and-vanish-input` wrapper — placeholder cycle 2.5s; Magicui `text-shimmer` live morph as user types (closes frontend-validator HIGH-3) |
| `SuggestionChips.tsx` (NEW) | 3-chip glass-card row (e.g., Zürich · Berlin · Lisbon for city); hover rose-30%; click → fills input + submits (closes frontend-validator HIGH-3) |
| `PersonalizingBadge.tsx` (NEW) | Top-right pulsing-dot badge during agent.run (closes frontend-validator wireframe gap) |
| `BackLink.tsx` (NEW) | Back-arrow link on screens 2+; absent on S0/S1 (entry guard) |
| `NikitaThinkingDots.tsx` (NEW) | Loading-state ellipsis replacing NikitaReaction during >2s pending (per C1.14) |
| `FallingPattern.tsx` | REUSED from Spec 208 — sparse char rain background |

### REUSED (no edits)
- `portal/src/components/landing/aurora-orbs.tsx`
- `portal/src/components/landing/glow-button.tsx`
- `portal/src/lib/easing.ts`
- `portal/src/app/globals.css` (tokens + glass utilities)

### EDITED (light)
- `portal/src/app/onboarding/page.tsx` — replace legacy wizard component import with `WizardShell`. JWT cookie auth retained.
- `portal/src/app/onboarding/auth/page.tsx` — small copy update; ensure no banned vocab.
- `portal/src/app/onboarding/auth/page-client.tsx` — same.

### DELETED
- Legacy 11-step form wizard components (gated by `NEXT_PUBLIC_USE_LEGACY_FORM_WIZARD` flag; flag removed post-216 ship).

## Tests to Write (vitest)

| Test File | Focus | AC |
|-----------|-------|-----|
| `__tests__/HobbyChips.test.tsx` | 3-5 picks enforced, autocomplete filter, category groups, "+ other" with 40-char warn | C1.6 |
| `__tests__/BackstoryArchetypeCards.test.tsx` | 3-card render, no-invent-label guard rejects invalid labels with console.warn | C1.7 |
| `__tests__/ProgressRail.test.tsx` | monotonicity reflection — pass {progress_pct: 50, then 30}; assert width never <50 | C1.8 |
| `__tests__/WizardShell.test.tsx` | AnimatePresence wraps single screen at a time, reduced-motion sets `transition.duration=0` | C1.4 |
| `__tests__/NikitaReaction.test.tsx` | reveal animation runs 200ms after mount; respects reduced-motion | C1.9 |
| `__tests__/control_dispatch.test.tsx` | each `control_type` literal renders the right component | FR-02 |

## Implementation Notes

### Layout per screen (canonical)

```tsx
<WizardShell>
  <AuroraOrbs opacity={0.25} />
  <ProgressRail progressPct={progress_pct} />
  <AnimatePresence mode="wait">
    <motion.div key={slot_kind} {...screenTransition}>
      <QuestionCard>
        <NikitaReaction text={nikita_reaction} />
        <h1 className="text-clamp-display">{next_question_text}</h1>
        <WhyWeAsk text={why_we_ask} />
        {renderControl(control_type, control_options)}
        <GlowButton onClick={submit} disabled={!isValid}>Continue</GlowButton>
      </QuestionCard>
    </motion.div>
  </AnimatePresence>
</WizardShell>
```

### Design tokens (verbatim from Spec 208)

```css
--bg-void: oklch(0.08 0 0);
--rose: oklch(0.75 0.15 350);
--glass-card-bg: rgba(255 255 255 / 0.04);
--glass-card-border: rgba(255 255 255 / 0.08);
--ease-out-quart: cubic-bezier(0.16, 1, 0.3, 1);
```

### Hobby chip taxonomy (locked)

10 categories × ~10 chips = ~100 chips total. **Universal at launch** (no per-cohort variation pre-launch). Examples:
- **Music**: techno, jazz, indie rock, classical, hip-hop, reggae, ambient, folk, metal, opera
- **Movement**: running, climbing, yoga, lifting, swimming, cycling, dance, martial arts, hiking, pilates
- **Gaming**: ARPG, FPS, MOBA, indie, retro, MMO, fighting, strategy, sandbox, VR
- (full list TBD via UX review during implementation; ship with placeholder and refine)

## Open Questions

- **Q1**: Hobby chip exact list per category — draft list TBD by UX review during 216-C implementation. Master taxonomy structure (10 cat × 10 chips) is locked.
- **Q2**: BackstoryArchetypeCards — show 1-line persona prose ON the card or behind a flip? Default: 150-char prose visible; richer prose post-select.
- **Q3**: Voice-tone preference UI — radio (text/voice/both) or chip select? Default: 3 radio buttons inline with phone input.
- **Q4**: Resume mid-wizard UX — show "Welcome back. Pick up where you left off." banner OR silent resume? Default: silent + greet via NikitaReaction on first hydrated turn.

## References

- Master spec FR-02, FR-08, FR-09, FR-10, FR-11, NR-04, NR-07, NR-08
- Wireframes: `wireframes/ascii.md` (127K, 10 screens × mobile+desktop), `wireframes/figma.md` (file key `3c5uJdNeAnAnIV5cZXvamM`, 20 frames), `wireframes/motion-spec.md`
- Spec 208 design system: `specs/208-marketing-website-redesign/spec.md`
- W3 walk findings #443, #447, #448

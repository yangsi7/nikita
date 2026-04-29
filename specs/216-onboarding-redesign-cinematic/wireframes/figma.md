# Spec 216 — Onboarding Wizard Wireframes (Figma)

**Date**: 2026-04-28
**Source plan**: `~/.claude/plans/onboarding-redesign-spec216.md` §6 (verbatim wireframe specs)
**Recipe**: `docs-to-process/20260428-spec216-wireframes-figma-recipe.md`

## Auth status

Authenticated as `simon.yang.ch@gmail.com` (Simon Yang) on team `Simon Yang's team` (planKey `team::1271499138637451132`, Pro tier). No auth gap.

## Figma file

| Field | Value |
|---|---|
| File name | Nikita Onboarding Wizard — Spec 216 Wireframes |
| File key | `3c5uJdNeAnAnIV5cZXvamM` |
| File URL | https://www.figma.com/design/3c5uJdNeAnAnIV5cZXvamM |
| Page | "Wizard Wireframes — Spec 216" (id `0:1`) |
| Editor type | design |

## Frames (20 total — 10 screens × 2 viewports)

Open any frame URL in Figma to land directly on it. Node IDs follow Figma's `file:nodeId` format.

### Desktop — 1440×900

| # | Screen | Frame name | Node ID | Direct URL |
|---|---|---|---|---|
| 0 | Welcome | D0 — WELCOME | `3:2` | https://www.figma.com/design/3c5uJdNeAnAnIV5cZXvamM?node-id=3-2 |
| 1 | Location | D1 — WHERE | `3:15` | https://www.figma.com/design/3c5uJdNeAnAnIV5cZXvamM?node-id=3-15 |
| 2 | Scene | D2 — SCENE | `3:29` | https://www.figma.com/design/3c5uJdNeAnAnIV5cZXvamM?node-id=3-29 |
| 3 | Darkness | D3 — DARKNESS | `3:44` | https://www.figma.com/design/3c5uJdNeAnAnIV5cZXvamM?node-id=3-44 |
| 4 | Name | D4 — NAME | `3:59` | https://www.figma.com/design/3c5uJdNeAnAnIV5cZXvamM?node-id=3-59 |
| 5 | Age | D5 — AGE | `3:74` | https://www.figma.com/design/3c5uJdNeAnAnIV5cZXvamM?node-id=3-74 |
| 6 | Occupation | D6 — WORK | `3:89` | https://www.figma.com/design/3c5uJdNeAnAnIV5cZXvamM?node-id=3-89 |
| 7 | Backstory | D7 — STORY | `3:104` | https://www.figma.com/design/3c5uJdNeAnAnIV5cZXvamM?node-id=3-104 |
| 8 | Phone/Reach | D8 — REACH | `3:119` | https://www.figma.com/design/3c5uJdNeAnAnIV5cZXvamM?node-id=3-119 |
| 9 | Completion | D9 — KNOWN | `3:134` | https://www.figma.com/design/3c5uJdNeAnAnIV5cZXvamM?node-id=3-134 |

### Mobile — 390×844

| # | Screen | Frame name | Node ID | Direct URL |
|---|---|---|---|---|
| 0 | Welcome | M0 — WELCOME | `4:2` | https://www.figma.com/design/3c5uJdNeAnAnIV5cZXvamM?node-id=4-2 |
| 1 | Location | M1 — WHERE | `4:15` | https://www.figma.com/design/3c5uJdNeAnAnIV5cZXvamM?node-id=4-15 |
| 2 | Scene | M2 — SCENE | `4:29` | https://www.figma.com/design/3c5uJdNeAnAnIV5cZXvamM?node-id=4-29 |
| 3 | Darkness | M3 — DARKNESS | `4:44` | https://www.figma.com/design/3c5uJdNeAnAnIV5cZXvamM?node-id=4-44 |
| 4 | Name | M4 — NAME | `4:59` | https://www.figma.com/design/3c5uJdNeAnAnIV5cZXvamM?node-id=4-59 |
| 5 | Age | M5 — AGE | `4:74` | https://www.figma.com/design/3c5uJdNeAnAnIV5cZXvamM?node-id=4-74 |
| 6 | Occupation | M6 — WORK | `4:89` | https://www.figma.com/design/3c5uJdNeAnAnIV5cZXvamM?node-id=4-89 |
| 7 | Backstory | M7 — STORY | `4:104` | https://www.figma.com/design/3c5uJdNeAnAnIV5cZXvamM?node-id=4-104 |
| 8 | Phone/Reach | M8 — REACH | `4:119` | https://www.figma.com/design/3c5uJdNeAnAnIV5cZXvamM?node-id=4-119 |
| 9 | Completion | M9 — KNOWN | `4:134` | https://www.figma.com/design/3c5uJdNeAnAnIV5cZXvamM?node-id=4-134 |

## Layout

- Desktop frames laid out 5-col × 2-row grid: row 1 screens 0-4, row 2 screens 5-9. Origin (100, 100), 80px gutters.
- Mobile frames laid out 5-col × 2-row grid: row 1 screens 0-4, row 2 screens 5-9. Origin (100, 2300), 60px gutters.
- Annotation blocks placed to the right of the mobile grid.

## Frame anatomy (every frame)

Each frame contains the §6 structural elements verbatim:

1. **ProgressRail** — 3px gradient (rose→cyan), filled to `(screen_index/9) * 100%`. Welcome (S0) shows track only.
2. **AmbientOrb** — rose ellipse, 15% opacity, layer-blur 120px (Desktop) / 80px (Mobile). Approximates AuroraOrbs.
3. **Eyebrow** — Geist Mono Medium 12px (Desktop) / 11px (Mobile), 2.4/2.2px tracking, uppercase, muted-foreground.
4. **Headline** — Geist Black 56px (Desktop) / 36px (Mobile), -4% tracking, 100% leading, foreground.
5. **Why-we-ask** — Geist Regular 16px / 14px, 162% leading, muted-foreground. (Italic style unavailable in Figma's Geist; rendered Regular with annotation.)
6. **Control placeholder** — glass-card rectangle (white@5% fill, white@10% stroke, radius 12) containing Geist Mono prose describing the live control type, options, and behavior per §6.
7. **Personalization hint** — small italic-styled line capturing the per-screen "wow" beat.
8. **GlowButton CTA** — rose pill, fully-rounded, padding 16x32 (Desktop) / 14x28 (Mobile), drop-shadow 0/0/20 + 0/0/40 rose glow, with trailing `↗` arrow.
9. **Back link** — `← back` text, only visible on screens 2+ (per §6 "no back from Welcome" rule).
10. **"personalizing..." badge** — top-right pulsing-dot text per §6 spec.
11. **Frame-name label** — sticky note above each frame in rose mono.

## Tokens & components

Local **paint styles** created (visible in the Figma file under "color/"):

| Style | Value (oklch source) | Hex approx |
|---|---|---|
| color/void | oklch(0.08 0 0) | #141414 |
| color/background | oklch(0.10 0 0) | #1A1A1A |
| color/card | oklch(0.13 0 0) | #212121 |
| color/foreground | oklch(0.95 0 0) | #F2F2F2 |
| color/muted-foreground | oklch(0.60 0 0) | #999999 |
| color/primary-rose | oklch(0.75 0.15 350) | #E89BB2 |
| color/cyan-glow | oklch(0.70 0.15 190) | #5FCFD8 |
| color/amber-glow | oklch(0.75 0.15 80) | #D9B879 |
| color/destructive | oklch(0.65 0.20 25) | #D85A4A |
| color/glass | white @ 5% opacity | — |
| color/glass-border | white @ 10% opacity | — |

**Fonts**: Geist (display) + Geist Mono (mono) loaded successfully. Note: `Geist Italic` style not present in Figma's Geist family — italic copy renders in Regular weight with text-callout annotation. Visual identity is approximate, not pixel-perfect.

**Components**: GlowButton + GlassCard surface conventions are inlined per frame (not extracted as Figma components in this pass — sufficient for wireframe review). Promotion to local components recommended in next pass when copy/visual decisions converge.

## Annotation blocks (right of mobile grid)

Three reference blocks placed at x=2400-3000, y=2300:

- **MOTION CALLOUTS** (rose border) — 9 motion-only behaviors that don't translate to static frames: AnimatePresence transitions, Aceternity placeholders-and-vanish, Magicui text-shimmer, slider live-morph, ProgressRail width animation, AuroraOrbs drift, hero stagger, typewriter reveal, prefers-reduced-motion fallback.
- **OPEN VISUAL DECISIONS** (amber border) — 7 decisions from plan §10 flagged but NOT pre-decided: STEP-0 routing investigation, backstory eyebrow vocab (NORTH/WEST/SOUTH vs VARIANT 1/2/3), migration strategy, voice-note inclusion, suggestion-chip data source, persona-preview chip on/off, "why we ask" agent-generated vs static.
- **TOKENS REFERENCE** (white border) — full token table + typography spec + component summary for designer reference.

## Caveats

1. **Static rendering**: Figma frames cannot animate. All motion behaviors (AnimatePresence transitions, text-shimmer, slider live-morph, aurora drift, typewriter reveals, ProgressRail width animation) are described as text-callout annotations adjacent to the relevant frame and consolidated in the MOTION CALLOUTS block.
2. **Aceternity / Magicui registry components** have no Figma counterparts; placeholder rectangles + behavior callout used.
3. **Geist Italic unavailable** in Figma's Geist family — italic copy rendered in Regular weight. Visual identity is approximate.
4. **Visual assets** (`nikita-hero.png`, intimate mood portraits) not embedded — frames use named glass-card placeholders with text notes pointing to file paths per plan §6.
5. **Backstory eyebrow vocab** (S7): rendered as "NORTH / WEST / SOUTH" in the control note since FILE-A/B/C violates PR #430 vocab-kill rule. VARIANT 1/2/3 alternative is also documented in the OPEN VISUAL DECISIONS block. User decision pending.
6. **Components not extracted as Figma library** — GlowButton + GlassCard surfaces are inlined per frame for this review pass. Promote to local components when copy/visuals converge.
7. **Code untouched**: this run did not modify anything under `nikita/` or `portal/` — Figma write-only.

## Next actions (post-review)

1. User reviews 20 frames + open-question annotations. Decisions on §10 items 2-7 surface here.
2. STEP-0 codebase-intel investigation (separate from wireframes): why production `/start` bypasses signup_handler.
3. After wireframe approval + decisions: invoke `/sdd new-spec 216 onboarding-redesign-cinematic` with this plan + decisions as input.
4. SDD chains through phases 0-9 with full validator suite.
5. Implementation via worktree + PR + QA loop.
6. W4 battle-test walk after merge.

---

**Tool calls used**: 8 (whoami, create_new_file, 4× use_figma, plus this Write). Well under the 30-cap.

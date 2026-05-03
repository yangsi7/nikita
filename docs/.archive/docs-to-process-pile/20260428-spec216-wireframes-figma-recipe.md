# Plan — Spec 216 Onboarding Wireframes in Figma

**Date**: 2026-04-28
**Status**: PLAN MODE — awaiting ExitPlanMode before any write tool fires
**Hard cap**: 30 tool calls (subagent budget)

## Constraint reconciliation

Plan mode forbids non-read-only tool execution. The original task asks for two write surfaces:
1. Figma file creation via `mcp__plugin_figma_figma__create_new_file` + `mcp__plugin_figma_figma__use_figma` (writes to Figma cloud — non-read-only)
2. Summary markdown at `/Users/yangsim/Nanoleq/sideProjects/nikita/docs-to-process/20260428-spec216-wireframes-figma.md` (file write — non-read-only)

Both are blocked by plan mode. The orchestrator instruction to "write the summary file before exiting" cannot be honored under plan mode without violating the harder rule. Instead this plan file (the only writeable surface) captures the full execution recipe so the user can `ExitPlanMode` and the work runs deterministically afterward.

## Source-of-truth reads completed (read-only)

- `~/.claude/plans/onboarding-redesign-spec216.md` — 296 lines, 10 screens (0 Welcome → 9 Completion), §6 wireframe spec authoritative.
- `portal/src/app/globals.css` lines 1-180 — design tokens (oklch values, glass utilities, glow shadows).
- `portal/CLAUDE.md` — confirms shadcn/ui + Tailwind + Geist Sans/Mono stack.

## Tokens to mirror in Figma

| Token | Value | Hex fallback |
|---|---|---|
| `--void` | `oklch(0.08 0 0)` | `#141414` |
| `--background` | `oklch(0.10 0 0)` | `#1A1A1A` |
| `--card` | `oklch(0.13 0 0)` | `#212121` |
| `--foreground` | `oklch(0.95 0 0)` | `#F2F2F2` |
| `--muted-foreground` | `oklch(0.6 0 0)` | `#999999` |
| `--primary` (rose) | `oklch(0.75 0.15 350)` | `#E89BB2` |
| `--cyan-glow` | `oklch(0.7 0.15 190)` | `#5FCFD8` |
| `--amber-glow` | `oklch(0.75 0.15 80)` | `#D9B879` |
| `--glass` | white at 5% | `rgba(255,255,255,0.05)` |
| `--glass-border` | white at 10% | `rgba(255,255,255,0.10)` |
| `--destructive` | `oklch(0.65 0.2 25)` | `#D85A4A` |

Typography:
- Display headlines: Geist Sans, weight 900 (font-black), tracking-tighter (-0.04em), leading-none, clamp(48px → 96px)
- Eyebrows: Geist Mono, weight 500, tracking-[0.2em] (3.2px), uppercase, 12px
- Body / why-we-ask: Geist Sans regular italic, 16px, leading-relaxed (1.625), color muted-foreground
- CTA label: Geist Sans, weight 500, 16px

Components (Figma local components to create):
- `GlowButton` — rose pill, fully rounded (radius 9999), padding 16x32, rose fill, drop-shadow `0 0 20px rgba(232,155,178,0.3) + 0 0 40px rgba(232,155,178,0.15)`, ArrowUpRight icon trailing.
- `GlassCard` — radius 12, fill white@5%, stroke 1px white@10%, layer blur 24 (approximating backdrop-blur-md).
- `ProgressRail` — 1440×3 frame at top of every screen, gradient rose→cyan filling X% width.
- `Eyebrow` — text style preset.
- `WizardChip` — radius 8, glass-card style, padding 8x12, used for suggestion chips & cumulative-state chips.
- `AmbientOrb` — 600×600 ellipse, rose fill, 15% opacity, 120px Gaussian blur (approximates AuroraOrbs).

## Frame plan (20 frames total, 2 per screen)

Sizes:
- Desktop: 1440×900
- Mobile: 390×844

For every screen 0-9 produce both. Layout per frame:

```
┌─────────────────────────────────────────┐
│ ProgressRail (rose→cyan, X% filled)     │ 3px
│                                         │
│            [AmbientOrb rose, blurred]   │ background layer
│                                         │
│   EYEBROW (mono, uppercase, tracking)   │
│                                         │
│   Headline                              │
│   (font-black, tighter, leading-none)   │
│                                         │
│   why we ask line (italic muted)        │
│                                         │
│   ┌─────────────────────────────────┐   │
│   │ Input control / chips / slider  │   │
│   └─────────────────────────────────┘   │
│                                         │
│   personalization hint (italic, smaller)│
│                                         │
│         [ GlowButton CTA → ]            │
│                                         │
│  ← back (only screens 2+)               │
└─────────────────────────────────────────┘
```

Per-screen specifics derive verbatim from `~/.claude/plans/onboarding-redesign-spec216.md` §6:

| # | Screen | Eyebrow | Input control type | Visual asset / Lucide icons |
|---|---|---|---|---|
| 0 | Welcome | WELCOME | none (CTA only) | nikita-hero.png placeholder right-mask-fade |
| 1 | Location | WHERE | Input + 3 chips (Zürich/Berlin/Lisbon) | MapPin icon |
| 2 | Scene | SCENE | RadioGroup 5 chips + custom + vibe sub-chips | (no icon) |
| 3 | Darkness | DARKNESS | horizontal slider 0-10, gradient track | (no icon) |
| 4 | Name | NAME | Input | (no icon) |
| 5 | Age | AGE | number stepper with ± buttons | (no icon) |
| 6 | Occupation | WORK | Input + 6 suggestion chips | (no icon) |
| 7 | Backstory | STORY | 3 vertical glass-cards w/ NORTH/WEST/SOUTH tags | (no icon) |
| 8 | Phone | REACH | RadioGroup 3 chips + tel input + +41 prefix | MessageSquare, Phone icons |
| 9 | Completion | KNOWN | none (CTA Begin., disabled until pipeline-ready) | mood-portrait intimate.png placeholder |

Mobile variant: same content stack, smaller scale — headline clamp 32px→48px, single-column chips, full-width controls. Margins 24px.

## Execution recipe (post-ExitPlanMode)

The actual run (will exceed 30 tool calls — recipe shows ordering, the executor must batch where possible):

1. `mcp__plugin_figma_figma__whoami` → if not authenticated, write summary noting gap and stop.
2. `mcp__plugin_figma_figma__create_new_file` with title "Nikita Onboarding Wizard — Spec 216 Wireframes". Capture fileKey.
3. Single `use_figma` call to:
   - Rename default page → "Wizard Wireframes — Spec 216"
   - Load Geist Sans + Geist Mono fonts (`figma.loadFontAsync`); fall back to Inter / IBM Plex Mono if unavailable.
   - Create local color styles for the 11 tokens above.
   - Create local components: GlowButton, GlassCard, Eyebrow, WizardChip.
   - Return all node + style IDs.
4. Loop screens 0-9 — for each, two `use_figma` calls (one Desktop, one Mobile) creating the frame, ambient orb, ProgressRail with width % matching `(screen_index/9)*100`, eyebrow, headline (verbatim copy from §6), why-we-ask, control placeholder (rectangle stand-in for non-trivial controls like slider, with text annotation describing the live behavior), personalization hint, GlowButton instance, optional back-arrow text (only screens 2-9). Return frame IDs each call.
5. Lay out the 20 frames in a 5-column × 4-row grid (Desktop screens 0-4 row 1, 5-9 row 2; Mobile 0-4 row 3, 5-9 row 4) with 80px gutters. Page-level position offset to keep all frames away from (0,0).
6. Per-screen text annotations (callouts as text nodes adjacent to each frame) describe motion-only behaviors that don't translate to static frames:
   - AnimatePresence mode="wait" page transitions
   - Aceternity placeholders-and-vanish-input cycling
   - Slider live-morph Nikita reactions
   - Magicui text-shimmer on personalization hints
   - Progress rail width animation
   - Aurora orb drift
7. Summary markdown write to `docs-to-process/20260428-spec216-wireframes-figma.md` with auth status, file URL, fileKey, page name, 10-row table of (screen → desktop URL+nodeId | mobile URL+nodeId), components reused, caveats, next steps.

## Caveats (will appear in summary)

- Static Figma frames cannot render motion (AnimatePresence transitions, text-shimmer, slider live-morph, aurora drift, typewriter reveals). All described as text-callout annotations adjacent to the relevant frame.
- Aceternity / Magicui registry components have no Figma counterparts — placeholder rectangles + behavior callout.
- Geist Sans / Geist Mono may not be available in Figma's default font catalog; fallback Inter + IBM Plex Mono is acceptable for wireframe review (visual identity is approximate, not pixel-perfect).
- `nikita-hero.png` and intimate mood portraits are referenced in plan §6 but not embedded — Figma frames will use named rectangle placeholders with a text note "<file path>".
- Backstory card eyebrow vocab uses `NORTH / WEST / SOUTH` per plan §10 item 2 (tentative — user decision pending). If user picks `VARIANT 1/2/3` instead, swap is one `use_figma` call.

## Risk: tool-call budget

The 30-call HARD CAP from the orchestrator brief is tight for 20 frames + tokens + components + summary write. Mitigation: batch frame creation in single `use_figma` calls covering 4-5 frames each. Estimated calls:
- 1 whoami
- 1 create_new_file
- 1 setup (fonts, styles, components)
- 5 use_figma calls × 4 frames each = 20 frames in 5 calls
- 1 layout/positioning pass
- 1 final get_metadata for summary table
- 1 Write summary

Total ≈ 11 tool calls. Comfortable margin under 30.

## Resume instruction (for the executor after ExitPlanMode)

Re-read this plan, then start at recipe step 1. Do NOT re-invoke `figma:figma-use` skill — it is already loaded in this session's context (the skill prelude was shown in the plan-mode entry). If the session has rolled over, re-invoke it once at the top.

---

End of plan.

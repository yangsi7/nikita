## Architecture Validation Report

**Spec:** specs/208-portal-landing-page-hero/spec.md
**Status:** PASS
**Timestamp:** 2026-04-03T00:00:00Z

### Summary
- CRITICAL: 0
- HIGH: 0
- MEDIUM: 2
- LOW: 3

### Findings

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| MEDIUM | Module Organization | 12 new components in `portal/src/components/landing/` but the spec does not include `index.ts` barrel export — future imports from page.tsx will need individual paths | spec.md §New Files | Add `portal/src/components/landing/index.ts` barrel to modified files list |
| MEDIUM | Separation of Concerns | `SystemSection` spec embeds hardcoded stats (`742 Python files`, `5,533 Tests passing`, `86 Specifications`) as static copy — these values will drift from reality immediately. No source of truth or update strategy documented | spec.md §Section 3 | Accept as static marketing copy (acceptable) OR add a note that these values are updated manually at release time — document the decision |
| LOW | File Naming | Spec lists `falling-pattern.tsx` (kebab-case) but `AmbientParticles` reference is `ambient-particles.tsx` — consistent with project convention. No concern, just confirming | spec.md §FallingPattern | No action needed — naming is consistent |
| LOW | Import Patterns | The spec references Magic UI components (`blur-fade`, `number-ticker`, `text-shimmer`) via `npx shadcn@latest add` — if these become `@/components/ui/` files, their import aliases should follow `@/components/ui/blur-fade` not `magicui/blur-fade` | spec.md §Dependencies | Confirm post-install import paths in plan/tasks |
| LOW | Co-location | Test files specified at `portal/src/components/landing/__tests__/` — this is consistent with the project's test co-location pattern (vitest). No deviation. | spec.md §Unit Tests | No action needed |

### Proposed Structure

```
portal/src/
├── app/
│   ├── page.tsx                    # REWRITTEN — server component, LandingPage
│   └── globals.css                 # MODIFIED — aurora/cursor-blink keyframes
├── components/
│   ├── landing/                    # NEW directory (13 files)
│   │   ├── index.ts               # RECOMMEND adding barrel export
│   │   ├── hero-section.tsx
│   │   ├── pitch-section.tsx
│   │   ├── system-section.tsx
│   │   ├── stakes-section.tsx
│   │   ├── cta-section.tsx
│   │   ├── landing-nav.tsx
│   │   ├── glow-button.tsx
│   │   ├── aurora-orbs.tsx
│   │   ├── falling-pattern.tsx
│   │   ├── telegram-mockup.tsx
│   │   ├── system-terminal.tsx
│   │   ├── chapter-timeline.tsx
│   │   └── __tests__/             # co-located unit tests
│   └── glass/
│       └── glass-card.tsx          # REUSED — no changes
└── lib/
    └── supabase/
        └── middleware.ts           # MODIFIED — add "/" to public routes
```

### Module Dependency Graph

```
app/page.tsx (server)
    ├── LandingNav (client) ← scrollY, isAuthenticated
    ├── HeroSection (client) ← isAuthenticated
    │   ├── FallingPattern (canvas client)
    │   └── GlowButton (client)
    ├── PitchSection (client)
    │   └── TelegramMockup (client)
    ├── SystemSection (client)
    │   └── SystemTerminal (client)
    ├── StakesSection (client)
    │   ├── GlassCard (reused)
    │   └── ChapterTimeline (client)
    └── CtaSection (client) ← isAuthenticated
        ├── GlowButton (client)
        └── AuroraOrbs (css-only)
```

No circular dependencies detected. Clean tree — server root passes props to client leaves.

### Separation of Concerns Analysis

| Layer | Responsibility | Violation? |
|-------|---------------|------------|
| `app/page.tsx` (server) | Auth check + prop passing | None |
| `components/landing/*` (client) | Presentation + animation | None |
| `lib/supabase/middleware.ts` | Route guard logic | None (single change) |
| `globals.css` | Global keyframes/utilities | None |

The pattern is correct: server component reads auth, passes `isAuthenticated` boolean down. No client component fetches auth independently.

### Import Pattern Checklist
- [x] `@/` alias configured in `tsconfig.json` paths: `"@/*": ["./src/*"]`
- [x] New landing components will use `@/components/landing/...`
- [x] `GlassCard` reuse via `@/components/glass/glass-card`
- [x] No relative `../` imports needed (components at same level)
- [ ] Barrel export (`index.ts`) not specified — MEDIUM

### Security Architecture
- [x] No user-generated content rendered in landing page (no XSS surface)
- [x] `isAuthenticated` is a boolean prop derived server-side — no sensitive data leaked to client
- [x] External link to `https://t.me/Nikita_my_bot` is hardcoded (no URL injection)
- [x] No new API routes introduced

### Recommendations

1. **MEDIUM — Add barrel export**: Include `portal/src/components/landing/index.ts` in the modified files list (spec §New Files). Single export file keeps imports in `page.tsx` clean.

2. **MEDIUM — Stats staleness policy**: Document in spec §Section 3 that terminal stats (`742 Python files`, `5,533 tests`) are static marketing copy updated manually at major releases. This prevents implementors from creating a live data dependency.

3. **LOW — Magic UI import paths**: After `npx shadcn@latest add`, confirm components land at `@/components/ui/blur-fade` etc. Update plan/tasks if paths differ.

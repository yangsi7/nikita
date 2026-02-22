# Tasks 062: Portal Visual Polish & Mobile (RETROACTIVE)

**Spec**: 062-portal-visual-polish/spec.md
**Plan**: 062-portal-visual-polish/plan.md
**Total**: 14 tasks | **Est**: ~6h
**Note**: Generated retroactively. All tasks verified complete via commit 63da5da.

---

## Phase 1: Page Transitions (US-1)

### T1.1: PageTransition Component
- [x] Create `portal/src/components/shared/page-transition.tsx`
- [x] Framer Motion `motion.div` wrapper
- [x] Initial: opacity 0, y 8
- [x] Animate: opacity 1, y 0
- [x] Transition: 200ms easeOut
- [x] Accept children and optional className prop
- **File**: `portal/src/components/shared/page-transition.tsx` (21 lines)
- **AC**: US-1

---

## Phase 2: Modal/Drawer Animations (US-2)

### T2.1: Verify Radix Animations
- [x] Dialog/Sheet components use Radix primitives with CSS enter/exit animations
- [x] OfflineBanner demonstrates AnimatePresence + Framer Motion pattern
- [x] No additional code changes needed — Radix handles natively
- **AC**: US-2

---

## Phase 3: Skeleton Shimmer (US-3)

### T3.1: Shimmer CSS Animation
- [x] Add `.shimmer` utility class to `portal/src/app/globals.css`
- [x] Gradient: `white/5 -> white/10 -> white/5`
- [x] Background-size: 200% 100%
- [x] Add `@keyframes shimmer` — background-position sweep from -200% to 200%
- [x] Duration: 1.5s, ease-in-out, infinite
- **File**: `portal/src/app/globals.css` (+6 lines)
- **AC**: US-3

### T3.2: Apply Shimmer to LoadingSkeleton
- [x] Add `shimmer` class to all Skeleton elements in LoadingSkeleton component
- [x] Applied to variants: ring, chart, card-grid, table, kpi, card, default
- **File**: `portal/src/components/shared/loading-skeleton.tsx`
- **AC**: US-3

---

## Phase 4: Mobile Bottom Tab Navigation (US-4)

### T4.1: MobileNav Component
- [x] Create `portal/src/components/layout/mobile-nav.tsx`
- [x] Uses `useIsMobile()` hook — returns null on desktop
- [x] 5 tabs: Dashboard (LayoutDashboard), Engage (TrendingUp), Nikita (Sparkles), Vices (Heart), Chat (MessageSquare)
- [x] Active state detection via `usePathname()` — exact match for /dashboard, startsWith for others
- [x] Active tab: `text-rose-400`, inactive: `text-muted-foreground`
- [x] Fixed bottom positioning with `pb-[env(safe-area-inset-bottom)]`
- [x] Glass-card background: `backdrop-blur-md bg-white/5 border-t border-white/10`
- [x] Touch targets: `min-h-11 min-w-11` on each tab link
- **File**: `portal/src/components/layout/mobile-nav.tsx` (49 lines)
- **AC**: US-4, US-5

### T4.2: Wire MobileNav into Sidebar Layout
- [x] Add `<MobileNav />` component in player variant of AppLayout
- [x] MobileNav self-guards on desktop (returns null)
- **File**: `portal/src/components/layout/sidebar.tsx`
- **AC**: US-4

### T4.3: Hide Sidebar on Mobile
- [x] SidebarProvider (shadcn) handles responsive collapse natively
- [x] MobileNav replaces sidebar navigation on small screens
- **AC**: US-4

---

## Phase 5: Touch Target Optimization (US-5)

### T5.1: Touch Targets on MobileNav
- [x] `min-h-11 min-w-11` applied to all Link elements in MobileNav (44x44px)
- [x] Verified via component inspection
- **AC**: US-5

---

## Phase 6: Empty State CTAs (US-6)

### T6.1: Extend EmptyState with Action Prop
- [x] Add optional `action` prop: `{ label: string; href?: string; onClick?: () => void }`
- [x] href: render Button wrapped in Link (primary variant)
- [x] onClick: render Button with onClick handler
- [x] Backward compatible — existing EmptyState usages unaffected
- **File**: `portal/src/components/shared/empty-state.tsx` (33 lines)
- **AC**: US-6

---

## Phase 7: Custom Loading Spinner (US-7)

### T7.1: NikitaSpinner Component
- [x] Create `portal/src/components/shared/nikita-spinner.tsx`
- [x] Three sizes: sm (h-5 w-5), md (h-8 w-8), lg (h-12 w-12)
- [x] Double-ring design: outer static ring (rose-400/20), inner spinning ring (rose-400)
- [x] Uses `animate-spin` Tailwind utility
- [x] Centered flex container
- **File**: `portal/src/components/shared/nikita-spinner.tsx` (25 lines)
- **AC**: US-7

---

## Phase 8: Verification

### T8.1: Portal Build Verification
- [x] `npm run build` completes with 0 TypeScript errors
- **AC**: All

### T8.2: Visual Verification
- [x] Page transitions animate on route change
- [x] Skeletons shimmer during loading
- [x] Mobile nav visible on small screens, hidden on desktop
- [x] Empty state CTA buttons render correctly
- [x] NikitaSpinner displays at all sizes
- **AC**: All

---

## Summary

| Phase | Tasks | Key Output |
|-------|-------|------------|
| 1: Page Transitions | T1.1 | PageTransition component (Framer Motion) |
| 2: Modal Animations | T2.1 | Radix audit (no changes) |
| 3: Skeleton Shimmer | T3.1-T3.2 | CSS animation + LoadingSkeleton update |
| 4: Mobile Nav | T4.1-T4.3 | MobileNav + sidebar wiring |
| 5: Touch Targets | T5.1 | 44x44px minimum on mobile nav |
| 6: Empty State CTA | T6.1 | Action prop on EmptyState |
| 7: Spinner | T7.1 | NikitaSpinner (rose-colored) |
| 8: Verify | T8.1-T8.2 | Build + visual check |
| **Total** | **14** | **3 new files, 4 modified** |

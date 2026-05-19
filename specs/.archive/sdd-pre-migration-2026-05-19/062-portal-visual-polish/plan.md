# Plan: Spec 062 — Portal Visual Polish & Mobile (RETROACTIVE)

**Spec**: `specs/062-portal-visual-polish/spec.md` | **Wave**: D | **Tasks**: 14 | **Effort**: ~6h
**Note**: This plan was generated retroactively after implementation (commit 63da5da).

---

## 1. Summary

This plan implements page transitions (Framer Motion), skeleton shimmer animation, mobile bottom tab navigation, touch target optimization, empty state CTAs, and a branded loading spinner. All changes are frontend-only (Next.js 16 + Framer Motion + Tailwind CSS). No backend modifications.

---

## 2. Implementation Phases

### Phase 1: Page Transitions (US-1)

**T1.1 — PageTransition component**
- **Create**: `portal/src/components/shared/page-transition.tsx`
- Framer Motion `motion.div` with fade-in (opacity 0->1) and slide-up (y 8->0, 200ms easeOut). Wraps page content.
- **AC**: US-1

### Phase 2: Modal/Drawer Animations (US-2)

**T2.1 — Verify Radix + Framer Motion integration**
- Existing Dialog/Sheet components use Radix primitives which include built-in enter/exit animations via CSS. Framer Motion variants can overlay if needed. OfflineBanner already demonstrates AnimatePresence pattern.
- **AC**: US-2

### Phase 3: Skeleton Shimmer (US-3)

**T3.1 — Add shimmer CSS animation**
- **Modify**: `portal/src/app/globals.css`
- Add `.shimmer` utility class with gradient sweep animation (white/5 -> white/10 -> white/5, 1.5s infinite). Add `@keyframes shimmer` rule.
- **AC**: US-3

**T3.2 — Apply shimmer to LoadingSkeleton**
- **Modify**: `portal/src/components/shared/loading-skeleton.tsx`
- Add `shimmer` class to all Skeleton elements in every variant (ring, chart, card-grid, table, kpi, card).
- **AC**: US-3

### Phase 4: Mobile Bottom Tab Navigation (US-4)

**T4.1 — MobileNav component**
- **Create**: `portal/src/components/layout/mobile-nav.tsx`
- Fixed bottom nav visible only on mobile (< 768px via `useIsMobile` hook). 5 tabs: Dashboard, Engage, Nikita, Vices, Chat. Active state with rose accent. Glass-card background with safe-area-inset-bottom padding. `min-h-11 min-w-11` touch targets.
- **AC**: US-4

**T4.2 — Wire MobileNav into sidebar layout**
- **Modify**: `portal/src/components/layout/sidebar.tsx`
- Add `<MobileNav />` component. Only renders on player routes (dashboard/*), hidden on admin routes.
- **AC**: US-4

**T4.3 — Hide sidebar on mobile**
- **Modify**: `portal/src/components/layout/sidebar.tsx`
- Sidebar already uses shadcn SidebarProvider which handles responsive collapse. MobileNav replaces sidebar navigation on small screens.
- **AC**: US-4

### Phase 5: Touch Target Optimization (US-5)

**T5.1 — Apply min-h-11 min-w-11 to MobileNav links**
- Already applied in T4.1 MobileNav component (`min-h-11 min-w-11` on Link elements).
- **AC**: US-5

### Phase 6: Empty State CTAs (US-6)

**T6.1 — Extend EmptyState with action prop**
- **Modify**: `portal/src/components/shared/empty-state.tsx`
- Add optional `action` prop: `{ label: string, href?: string, onClick?: () => void }`. Render Button (primary variant) with Link wrapper for href, onClick handler otherwise.
- **AC**: US-6

### Phase 7: Custom Loading Spinner (US-7)

**T7.1 — NikitaSpinner component**
- **Create**: `portal/src/components/shared/nikita-spinner.tsx`
- Rose-colored pulse ring spinner. Three sizes (sm/md/lg). Double-ring design: outer static border (rose-400/20), inner spinning border (rose-400). Uses animate-spin utility.
- **AC**: US-7

### Phase 8: Verification

**T8.1 — Portal build verification**
- Run `npm run build` with 0 TypeScript errors.

**T8.2 — Visual verification**
- Verify page transitions, shimmer, mobile nav, empty state CTA, spinner render correctly.

---

## 3. Dependency Graph

```
T1.1 (independent)
T2.1 (audit only)
T3.1 ──→ T3.2
T4.1 ──→ T4.2 ──→ T4.3
T5.1 (included in T4.1)
T6.1 (independent)
T7.1 (independent)
All ──→ T8.1 ──→ T8.2
```

**Parallelizable**: All phases are independent.

---

## 4. Files Summary

### Create (3)
| File | Task | Purpose |
|------|------|---------|
| `portal/src/components/shared/page-transition.tsx` | T1.1 | Framer Motion fade + slide wrapper |
| `portal/src/components/layout/mobile-nav.tsx` | T4.1 | Bottom tab navigation for mobile |
| `portal/src/components/shared/nikita-spinner.tsx` | T7.1 | Branded rose-colored spinner |

### Modify (3)
| File | Task | Change |
|------|------|--------|
| `portal/src/app/globals.css` | T3.1 | Add .shimmer utility + @keyframes |
| `portal/src/components/shared/loading-skeleton.tsx` | T3.2 | Add shimmer class to all variants |
| `portal/src/components/shared/empty-state.tsx` | T6.1 | Add action prop with CTA button |
| `portal/src/components/layout/sidebar.tsx` | T4.2 | Add MobileNav integration |

---

## 5. Risk Mitigations

| Risk | Mitigation |
|------|------------|
| Framer Motion bundle size | Already installed, < 15KB gzipped. Only motion.div used |
| Mobile nav overlaps content | Fixed bottom with safe-area-inset-bottom; content area has bottom padding |
| Shimmer animation performance | CSS-only animation, GPU-accelerated via background-position |
| Touch targets too small | min-h-11 min-w-11 (44x44px) on all interactive elements |

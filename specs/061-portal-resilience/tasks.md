# Tasks 061: Portal Resilience & Accessibility (RETROACTIVE)

**Spec**: 061-portal-resilience/spec.md
**Plan**: 061-portal-resilience/plan.md
**Total**: 16 tasks | **Est**: ~8h
**Note**: Generated retroactively. All tasks verified complete via commit 63da5da.

---

## Phase 1: Error Boundaries (US-1)

### T1.1: ErrorBoundaryWrapper Component
- [x] Create `portal/src/components/shared/error-boundary-wrapper.tsx`
- [x] React class component with getDerivedStateFromError + componentDidCatch
- [x] Fallback UI: glass-card with AlertCircle icon, error message, "Try Again" button
- [x] handleReset clears error state to re-render children
- [x] Optional `fallbackMessage` prop
- **File**: `portal/src/components/shared/error-boundary-wrapper.tsx` (69 lines)
- **AC**: US-1

### T1.2: Wire Error Boundaries into Layouts
- [x] Modify `portal/src/app/dashboard/layout.tsx` — wrap children in `<ErrorBoundaryWrapper>`
- [x] Modify `portal/src/app/admin/layout.tsx` — wrap children in `<ErrorBoundaryWrapper>`
- [x] Add `id="main-content"` div inside both layouts for skip link target
- **File**: `portal/src/app/dashboard/layout.tsx`, `portal/src/app/admin/layout.tsx`
- **AC**: US-1

---

## Phase 2: Offline Detection (US-2)

### T2.1: useOnlineStatus Hook
- [x] Create `portal/src/hooks/use-online-status.ts`
- [x] useState initialized to `true`, updated via navigator.onLine on mount
- [x] Add/remove `online`/`offline` event listeners with cleanup
- **File**: `portal/src/hooks/use-online-status.ts` (29 lines)
- **AC**: US-2

### T2.2: OfflineBanner Component
- [x] Create `portal/src/components/shared/offline-banner.tsx`
- [x] AnimatePresence wrapping motion.div with slide-down animation
- [x] glass-card-amber styling, WifiOff icon, descriptive text
- [x] `role="alert"` for accessibility
- **File**: `portal/src/components/shared/offline-banner.tsx` (27 lines)
- **AC**: US-2

### T2.3: Wire OfflineBanner into Providers
- [x] Add `<OfflineBanner />` in Providers component before children
- **File**: `portal/src/app/providers.tsx`
- **AC**: US-2

---

## Phase 3: Exponential Backoff Retry (US-3)

### T3.1: Configure QueryClient Retry
- [x] Set `retry: 3` in QueryClient defaultOptions
- [x] Set `retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000)`
- [x] Set `refetchOnWindowFocus: false`
- **File**: `portal/src/app/providers.tsx`
- **AC**: US-3

---

## Phase 4: Keyboard Navigation (US-4)

### T4.1: SkipLink Component
- [x] Create `portal/src/components/shared/skip-link.tsx`
- [x] sr-only anchor to `#main-content`, visible on focus
- [x] Primary background color styling on focus
- **File**: `portal/src/components/shared/skip-link.tsx` (10 lines)
- **AC**: US-4

### T4.2: Wire SkipLink into Providers
- [x] Add `<SkipLink />` as first element in Providers
- **File**: `portal/src/app/providers.tsx`
- **AC**: US-4

---

## Phase 5: Focus Management (US-5)

### T5.1: Verify Radix Focus Trapping
- [x] Audited Dialog and Sheet components — Radix UI handles focus trap, return-to-trigger, and auto-focus natively
- [x] No code changes required
- **AC**: US-5

---

## Phase 6: aria-live Regions (US-6)

### T6.1: SrAnnouncer Component
- [x] Create `portal/src/components/shared/sr-announcer.tsx`
- [x] Visually hidden div with `aria-live="polite"` and `role="status"`
- [x] Export `announce()` function for programmatic announcements
- [x] requestAnimationFrame pattern to re-announce identical messages
- **File**: `portal/src/components/shared/sr-announcer.tsx` (40 lines)
- **AC**: US-6

### T6.2: Wire SrAnnouncer into Providers
- [x] Add `<SrAnnouncer />` in Providers before children
- **File**: `portal/src/app/providers.tsx`
- **AC**: US-6

---

## Phase 7: Route Code Splitting (US-7)

### T7.1: Verify Next.js Code Splitting
- [x] Next.js App Router automatically code-splits per route segment
- [x] LoadingSkeleton used as Suspense fallback in loading states
- [x] No manual React.lazy needed
- **AC**: US-7

---

## Phase 8: Web Vitals (US-8)

### T8.1: Install Analytics Packages
- [x] Add `@vercel/analytics` to portal/package.json
- [x] Add `@vercel/speed-insights` to portal/package.json
- **File**: `portal/package.json`
- **AC**: US-8

### T8.2: Wire Analytics into Root Layout
- [x] Add `<Analytics />` and `<SpeedInsights />` in root layout
- **File**: `portal/src/app/layout.tsx`
- **AC**: US-8

---

## Phase 9: Verification

### T9.1: Portal Build Verification
- [x] `npm run build` completes with 0 TypeScript errors
- **AC**: All

### T9.2: Backend Test Regression
- [x] `pytest tests/ -x -q` passes (4,908 tests)
- **AC**: All

---

## Summary

| Phase | Tasks | Key Output |
|-------|-------|------------|
| 1: Error Boundaries | T1.1-T1.2 | ErrorBoundaryWrapper + layout wiring |
| 2: Offline Detection | T2.1-T2.3 | useOnlineStatus + OfflineBanner + providers |
| 3: Retry | T3.1 | Exponential backoff in QueryClient |
| 4: Keyboard Nav | T4.1-T4.2 | SkipLink + providers |
| 5: Focus Mgmt | T5.1 | Radix audit (no changes) |
| 6: aria-live | T6.1-T6.2 | SrAnnouncer + providers |
| 7: Code Splitting | T7.1 | Next.js audit (no changes) |
| 8: Web Vitals | T8.1-T8.2 | Analytics packages + layout |
| 9: Verify | T9.1-T9.2 | Build + test regression |
| **Total** | **16** | **5 new files, 4 modified** |

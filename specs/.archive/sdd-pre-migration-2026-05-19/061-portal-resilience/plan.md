# Plan: Spec 061 — Portal Resilience & Accessibility (RETROACTIVE)

**Spec**: `specs/061-portal-resilience/spec.md` | **Wave**: D | **Tasks**: 16 | **Effort**: ~8h
**Note**: This plan was generated retroactively after implementation (commit 63da5da).

---

## 1. Summary

This plan implements error boundaries, offline detection, exponential backoff retry, keyboard navigation, focus management, aria-live regions, route code splitting, and web vitals for the Nikita portal. All changes are frontend-only (Next.js 16 + shadcn/ui), requiring no backend modifications.

---

## 2. Implementation Phases

### Phase 1: Error Boundaries (US-1)

**T1.1 — ErrorBoundaryWrapper component**
- **Create**: `portal/src/components/shared/error-boundary-wrapper.tsx`
- React class component with getDerivedStateFromError, componentDidCatch, and "Try Again" reset button. Uses glass-card styling with AlertCircle icon.
- **AC**: US-1

**T1.2 — Wire error boundaries into layouts**
- **Modify**: `portal/src/app/dashboard/layout.tsx`, `portal/src/app/admin/layout.tsx`
- Wrap children in `<ErrorBoundaryWrapper>` inside each layout. Add `id="main-content"` div for skip link target.
- **AC**: US-1

### Phase 2: Offline Detection (US-2)

**T2.1 — useOnlineStatus hook**
- **Create**: `portal/src/hooks/use-online-status.ts`
- Uses `navigator.onLine` + `online`/`offline` event listeners. Returns boolean.
- **AC**: US-2

**T2.2 — OfflineBanner component**
- **Create**: `portal/src/components/shared/offline-banner.tsx`
- AnimatePresence + motion.div yellow banner at top. Shows WifiOff icon and message. Has `role="alert"`.
- **AC**: US-2

**T2.3 — Wire OfflineBanner into Providers**
- **Modify**: `portal/src/app/providers.tsx`
- Add `<OfflineBanner />` before children.
- **AC**: US-2

### Phase 3: Exponential Backoff Retry (US-3)

**T3.1 — Configure QueryClient with exponential backoff**
- **Modify**: `portal/src/app/providers.tsx`
- Set `retry: 3`, `retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000)`.
- **AC**: US-3

### Phase 4: Keyboard Navigation (US-4)

**T4.1 — SkipLink component**
- **Create**: `portal/src/components/shared/skip-link.tsx`
- sr-only link to `#main-content`, visible on focus with primary styling.
- **AC**: US-4

**T4.2 — Wire SkipLink into Providers**
- **Modify**: `portal/src/app/providers.tsx`
- Add `<SkipLink />` before OfflineBanner.
- **AC**: US-4

### Phase 5: Focus Management (US-5)

**T5.1 — Verify Radix focus trapping**
- Audit existing Dialog/Sheet components. Radix UI handles focus trap, return-to-trigger, and auto-focus natively. No code changes needed.
- **AC**: US-5

### Phase 6: aria-live Regions (US-6)

**T6.1 — SrAnnouncer component**
- **Create**: `portal/src/components/shared/sr-announcer.tsx`
- Visually hidden div with `aria-live="polite"` and `role="status"`. Exports `announce()` function for programmatic announcements. Uses requestAnimationFrame for re-announcement of identical messages.
- **AC**: US-6

**T6.2 — Wire SrAnnouncer into Providers**
- **Modify**: `portal/src/app/providers.tsx`
- Add `<SrAnnouncer />` before children.
- **AC**: US-6

### Phase 7: Route Code Splitting (US-7)

**T7.1 — Verify Next.js automatic code splitting**
- Next.js App Router automatically code-splits per route. No React.lazy needed. LoadingSkeleton already used as loading.tsx fallback. No code changes needed.
- **AC**: US-7

### Phase 8: Web Vitals (US-8)

**T8.1 — Install @vercel/analytics and @vercel/speed-insights**
- **Modify**: `portal/package.json`
- Add `@vercel/analytics` and `@vercel/speed-insights` dependencies.
- **AC**: US-8

**T8.2 — Wire analytics into root layout**
- **Modify**: `portal/src/app/layout.tsx`
- Add `<Analytics />` and `<SpeedInsights />` components.
- **AC**: US-8

### Phase 9: Verification

**T9.1 — Portal build verification**
- Run `npm run build` with 0 TypeScript errors.

**T9.2 — Backend test regression**
- Run `pytest tests/ -x -q` to verify no regressions.

---

## 3. Dependency Graph

```
T1.1 ──→ T1.2
T2.1 ──→ T2.2 ──→ T2.3
T3.1 (independent)
T4.1 ──→ T4.2
T5.1 (audit only)
T6.1 ──→ T6.2
T7.1 (audit only)
T8.1 ──→ T8.2
All ──→ T9.1 ──→ T9.2
```

**Parallelizable**: Phases 1-8 are fully independent and can be implemented in any order.

---

## 4. Files Summary

### Create (5)
| File | Task | Purpose |
|------|------|---------|
| `portal/src/components/shared/error-boundary-wrapper.tsx` | T1.1 | React error boundary with recovery UI |
| `portal/src/hooks/use-online-status.ts` | T2.1 | Online/offline detection hook |
| `portal/src/components/shared/offline-banner.tsx` | T2.2 | Animated offline notification banner |
| `portal/src/components/shared/skip-link.tsx` | T4.1 | Keyboard skip-to-content link |
| `portal/src/components/shared/sr-announcer.tsx` | T6.1 | Screen reader live region |

### Modify (4)
| File | Task | Change |
|------|------|--------|
| `portal/src/app/providers.tsx` | T2.3, T3.1, T4.2, T6.2 | Add OfflineBanner, SkipLink, SrAnnouncer; configure retry |
| `portal/src/app/dashboard/layout.tsx` | T1.2 | Wrap with ErrorBoundaryWrapper |
| `portal/src/app/admin/layout.tsx` | T1.2 | Wrap with ErrorBoundaryWrapper |
| `portal/src/app/layout.tsx` | T8.2 | Add Analytics + SpeedInsights |

---

## 5. Risk Mitigations

| Risk | Mitigation |
|------|------------|
| Error boundary catches too aggressively | Per-layout boundaries; individual section errors don't crash whole app |
| Offline banner SSR mismatch | useOnlineStatus initializes to true, updates after mount |
| Analytics overhead | @vercel/analytics is <1KB, loads async |
| Screen reader noise | aria-live="polite" (not assertive) for most announcements |

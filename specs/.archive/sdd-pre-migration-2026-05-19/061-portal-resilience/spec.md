# Spec 061: Portal Resilience & Accessibility

## Overview
Error handling, offline detection, accessibility hardening, and performance optimization for the Nikita portal.

## Complexity: 2 (Solo /sdd)

## User Stories

### US-1: React Error Boundaries
- Add ErrorBoundary component wrapping dashboard and admin layouts
- Recovery UI with "Try Again" button that resets state
- Catches render errors, shows fallback instead of blank page

### US-2: Offline Detection
- `useOnlineStatus()` hook detecting navigator.onLine + event listeners
- Network indicator banner when offline (yellow banner at top)
- Graceful degradation: show cached data when offline

### US-3: Exponential Backoff Retry
- Configure TanStack Query with exponential backoff: `retryDelay: attempt => Math.min(1000 * 2 ** attempt, 30000)`
- Increase retry count from 1 to 3
- Add `onError` callback to show toast on final failure

### US-4: Keyboard Navigation
- All interactive elements focusable via Tab
- Focus-visible ring using existing ring color token
- Skip-to-content link on layouts

### US-5: Focus Management
- Focus trap in modals/dialogs (already in Radix, verify)
- Return focus to trigger on close
- Auto-focus first interactive element on modal open

### US-6: aria-live Regions
- Toast container has `aria-live="polite"` and `role="status"`
- Score change announcements via `aria-live="assertive"` visually-hidden span

### US-7: Route Code Splitting
- React.lazy + Suspense for heavy page components
- LoadingSkeleton as fallback for each route
- Reduce initial bundle size

### US-8: Web Vitals
- Add `@vercel/analytics` and `@vercel/speed-insights`
- Wire into root layout

## Acceptance Criteria
- [ ] Error boundary catches render errors and shows recovery UI
- [ ] Offline banner appears when network disconnects
- [ ] Query retry uses exponential backoff (3 retries, up to 30s delay)
- [ ] All interactive elements reachable via keyboard
- [ ] Toast region has aria-live attributes
- [ ] Portal builds with 0 TypeScript errors
- [ ] No regressions in existing functionality

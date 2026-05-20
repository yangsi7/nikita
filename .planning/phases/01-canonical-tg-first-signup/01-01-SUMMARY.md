---
phase: "01"
plan: "01"
subsystem: portal-fe
tags: [spec-220, tg-first-signup, auth-flow, fe-bulldoze]
lifecycle: frozen

dependency_graph:
  requires: []
  provides: [TG-first-entry-point, 410-login, dead-route-cleanup, T3-safety-gate]
  affects: [portal/src/middleware, portal/src/app/login, portal/src/components/landing]

tech_stack:
  added: []
  patterns: [Next.js 410 route handler, middleware TG redirect, ?start=new deep-link param]

key_files:
  created:
    - portal/src/app/login/route.ts
  modified:
    - portal/src/lib/supabase/middleware.ts
    - portal/src/components/landing/hero-section.tsx
    - portal/src/components/landing/cta-section.tsx
    - portal/src/components/landing/landing-nav.tsx
    - portal/src/__tests__/middleware.test.ts
    - portal/src/__tests__/page-metadata.test.ts
    - portal/src/components/landing/__tests__/cta-href.test.tsx
    - portal/src/components/landing/__tests__/hero-section.test.tsx
    - portal/src/components/landing/__tests__/cta-section.test.tsx
    - portal/src/components/landing/__tests__/landing-nav.test.tsx
  deleted:
    - portal/src/app/login/page.tsx
    - portal/src/app/login/page-client.tsx
    - portal/src/app/login/CLAUDE.md
    - portal/src/app/login/__tests__/login-cta-href.test.tsx
    - portal/src/app/auth/interstitial/page.tsx
    - portal/src/app/auth/interstitial/InterstitialClient.tsx
    - portal/src/app/auth/interstitial/__tests__/InterstitialClient.test.tsx
    - portal/src/app/auth/bridge/route.ts
    - portal/src/app/onboarding/auth/route.ts

decisions:
  - "ADR-220-1 (locked): ?start=new is canonical CTA parameter; ?start=welcome (Spec 217 legacy) purged everywhere"
  - "T-3 safety gate committed in Task 1 before /login 410 in Task 2 (per ADR-220-3 PR-A ordering)"
  - "/auth/confirm exemption kept as exact-match only; /auth/interstitial pass-through removed"

metrics:
  duration_minutes: ~40
  tasks_completed: 2
  tasks_total: 2
  files_changed: 19
  insertions: 68
  deletions: 683
  completed_date: "2026-05-20"
---

# Phase 01 Plan 01: Canonical TG-First Signup — Portal FE Bulldoze Summary

Deletion-dominant portal FE change (~600 LOC net) establishing the canonical Telegram-first entry point for Spec 220 PR-A. Middleware now redirects unauthenticated users to the TG bot URL with `?start=new` instead of `/login`. The `/login` route returns 410 Gone. Three dead route directories deleted.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | T-3 safety gate: middleware redirect to TG bot URL | f2a25f7 | middleware.ts |
| 2 | Collapse CTAs to ?start=new, 410 /login, delete dead routes | cad1fad | 18 files |

## Verification Results

- Vitest: 84 test files, 584 tests — all PASS
- Next.js build: clean (0 errors, 0 warnings)
- ESLint: clean

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Purged `?start=welcome` in favor of locked `?start=new`**
- **Found during:** Task 2
- **Issue:** All three CTA components (`hero-section.tsx`, `cta-section.tsx`, `landing-nav.tsx`) used `?start=welcome` (Spec 217-1 legacy). ADR-220-1 (locked by user) specifies `?start=new` as the canonical parameter.
- **Fix:** Updated all three components and all associated tests to use `?start=new`.
- **Files modified:** `hero-section.tsx`, `cta-section.tsx`, `landing-nav.tsx`, `cta-href.test.tsx`, `hero-section.test.tsx`, `cta-section.test.tsx`, `landing-nav.test.tsx`
- **Commit:** cad1fad

**2. [Rule 1 - Bug] Updated middleware tests for new interstitial behavior**
- **Found during:** Task 1/2
- **Issue:** Three middleware tests asserted "authenticated user on `/auth/interstitial` passes through" — but this was only correct when the interstitial pass-through exemption existed. After removing that exemption per plan, authenticated users hitting `/auth/*` are now routed through the standard auth check and redirected to `/dashboard` or `/admin`.
- **Fix:** Updated three middleware tests to assert `/dashboard` (player) and `/admin` (admin) redirects instead of pass-through.
- **Files modified:** `portal/src/__tests__/middleware.test.ts`
- **Commit:** cad1fad

**3. [Rule 2 - Missing critical functionality] page-metadata test count updated**
- **Found during:** Task 2
- **Issue:** `page-metadata.test.ts` had a count assertion of 24 pages and included `login` in the list. After deleting `login/page.tsx`, this would fail.
- **Fix:** Removed login entry, updated count to 23, updated test description to document the change.
- **Files modified:** `portal/src/__tests__/page-metadata.test.ts`
- **Commit:** cad1fad

## Known Stubs

None. All production code paths are fully wired. No placeholder text, hardcoded empty values, or TODO markers introduced.

## Threat Surface Scan

No new network endpoints introduced. The `/login` route.ts handler returns 410 with no body (no data surface). No new auth paths created. No schema changes.

The `NEXT_PUBLIC_TG_BOT_URL` env var fallback in middleware (`?? "https://t.me/Nikita_my_bot"`) is intentional — hardcoded fallback ensures the redirect works even without env var. No secrets involved.

## Self-Check: PASSED

- `portal/src/app/login/route.ts` — FOUND
- `portal/src/lib/supabase/middleware.ts` — FOUND (modified)
- Commit f2a25f7 — FOUND in git log
- Commit cad1fad — FOUND in git log
- Deleted routes confirmed absent: `portal/src/app/auth/interstitial/`, `portal/src/app/auth/bridge/`, `portal/src/app/onboarding/auth/`

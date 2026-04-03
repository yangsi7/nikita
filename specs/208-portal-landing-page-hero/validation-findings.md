# GATE 2 Validation Findings — Spec 208: Portal Landing Page Hero

**Date:** 2026-04-03
**Validators run:** 6 (frontend, architecture, auth, testing, api, data-layer)
**Gate status:** PASS — 0 CRITICAL, 0 HIGH findings

---

## Overall Result

| Validator | Status | CRITICAL | HIGH | MEDIUM | LOW |
|-----------|--------|----------|------|--------|-----|
| sdd-frontend-validator | PASS | 0 | 0 | 3 | 4 |
| sdd-architecture-validator | PASS | 0 | 0 | 2 | 3 |
| sdd-auth-validator | PASS | 0 | 0 | 2 | 2 |
| sdd-testing-validator | PASS | 0 | 0 | 3 | 3 |
| sdd-api-validator | PASS | 0 | 0 | 0 | 2 |
| sdd-data-layer-validator | PASS | 0 | 0 | 0 | 1 |
| **TOTALS** | **PASS** | **0** | **0** | **10** | **15** |

**Gate 2 Decision: PASS** — No blocking issues. Spec may proceed to Phase 5 (planning).

---

## MEDIUM Findings (10) — Must Create GH Issues or Document as Accepted

### M-01 · Auth · Middleware authenticated-user conflict on `/`
**Validator:** auth  
**Finding:** The spec adds `pathname === "/"` to the public-route block in `handleRouting()`. That block currently redirects authenticated users to `/dashboard` or `/admin`. This means authenticated users visiting `/` will be redirected away BEFORE reaching the landing page — making the `isAuthenticated=true` "Go to Dashboard" CTA variant unreachable.  
**Fix required:** Modify the middleware change spec to use a separate early-return for `/`:
```typescript
if (pathname === "/") {
  return supabaseResponse // always pass through
}
if (pathname === "/login" || pathname.startsWith("/auth/")) {
  if (user) return NextResponse.redirect(...)
  return supabaseResponse
}
```
**Decision:** Fix spec before implementation (spec correctness issue, not just enhancement).

### M-02 · Auth · Existing E2E test conflicts with new behavior
**Validator:** auth  
**Finding:** `portal/e2e/auth-flow.spec.ts` line 6-14 asserts that unauthenticated visit to `/` redirects to `/login`. After this spec, `/` renders a landing page — this test must be inverted.  
**Fix required:** Add to spec §E2E Tests: "Update `e2e/auth-flow.spec.ts` unauthenticated redirect test — assert landing page renders, not `/login` redirect."  
**Decision:** Fix spec before implementation.

### M-03 · Frontend · Floating nav keyboard accessibility not fully specified
**Validator:** frontend  
**Finding:** `landing-nav.tsx` appears on scroll — keyboard focus management when it appears is unspecified. Users tabbing past the hero have no way to reach the nav naturally.  
**Fix required:** Add `role="navigation"` and `aria-label="Site navigation"` to nav spec. Note that existing Providers skip-link handles pre-nav keyboard flow.  
**Decision:** Fix spec (minor spec addition, not blocking implementation — acceptable to document).

### M-04 · Frontend · Breakpoints not explicit for pitch-section and stakes-section
**Validator:** frontend  
**Finding:** Only hero section (`< 768px`) has explicit breakpoints. Pitch section (2-column) and stakes section (2×2 grid) have no breakpoint specifications.  
**Fix required:** Add responsive table: pitch 2-col → 1-col at `md`, stakes 2×2 → 1-col at `sm`.  
**Decision:** Fix spec before implementation.

### M-05 · Frontend · `aria-hidden` not enumerated per decorative component
**Validator:** frontend  
**Finding:** Spec states "Decorative elements: `aria-hidden=true`" globally but doesn't enumerate which components need it. FallingPattern (canvas), AuroraOrbs, ChapterTimeline dots are all candidates.  
**Fix required:** Add per-component `aria-hidden` requirement table to §Accessibility.  
**Decision:** Document as accepted (spec captures intent, implementor will apply correctly).

### M-06 · Architecture · No barrel export (`index.ts`) for `components/landing/`
**Validator:** architecture  
**Finding:** 12 new components with no `index.ts` barrel. `page.tsx` will need 12 individual import paths.  
**Fix required:** Add `portal/src/components/landing/index.ts` to the "New Files" list.  
**Decision:** Fix spec before implementation (small addition).

### M-07 · Architecture · Terminal stats will immediately become stale
**Validator:** architecture  
**Finding:** Hardcoded `742 Python files`, `5,533 Tests passing`, `86 Specifications` in `system-section.tsx` will drift from reality. No update strategy documented.  
**Fix required:** Add a note in spec: "These values are static marketing copy. Update manually at major releases."  
**Decision:** Document as accepted (marketing copy intentionally static — confirmed design decision).

### M-08 · Testing · Incomplete framer-motion mock
**Validator:** testing  
**Finding:** Mock covers `motion.div`, `motion.p`, `motion.h1` but not `motion.button`, `motion.span`, `motion.a`, `motion.canvas`. GlowButton likely uses `motion.button` — tests will crash.  
**Fix required:** Replace partial mock with Proxy-based catch-all covering all `motion.*` variants.  
**Decision:** Fix spec before implementation.

### M-09 · Testing · `chapter-timeline.test.tsx` missing from test file list
**Validator:** testing  
**Finding:** Acceptance criteria "Chapter timeline shows 5 dots" has no corresponding unit test file.  
**Fix required:** Add `chapter-timeline.test.tsx` to §Unit Tests list.  
**Decision:** Fix spec before implementation.

### M-10 · Testing · `system-terminal.test.tsx` missing (or gap in system-section test)
**Validator:** testing  
**Finding:** 14 system names testability requires either a dedicated `system-terminal.test.tsx` or an explicit call-out that `system-section.test.tsx` covers them.  
**Fix required:** Add `system-terminal.test.tsx` OR explicitly state `system-section.test.tsx` covers the 14-system-name check.  
**Decision:** Fix spec before implementation.

---

## LOW Findings (15) — Log as Enhancement Issues or Accept

| ID | Validator | Finding | Decision |
|----|-----------|---------|----------|
| L-01 | frontend | `FallingPattern` (canvas) needs `next/dynamic` SSR-off — not specified | Accept; note in plan |
| L-02 | frontend | `next/image` usage for hero image not explicitly mandated — no `priority`, `sizes` spec | Fix in plan/tasks |
| L-03 | frontend | `landing-nav.tsx` must be `"use client"` — not called out in spec | Accept; implementor will know |
| L-04 | frontend | `useInView({ once: true })` not confirmed in animation table | Accept; once:true is the obvious choice |
| L-05 | architecture | No concern with kebab-case file naming — consistent with project | Accepted (non-issue) |
| L-06 | architecture | Magic UI import paths after `shadcn add` to confirm | Note in tasks |
| L-07 | architecture | Co-located `__tests__/` is consistent with existing vitest pattern | Accepted (non-issue) |
| L-08 | auth | `supabase.auth.getUser()` server-side pattern is correct | Accepted (confirmation) |
| L-09 | auth | Telegram URL hardcoded — no env var | Accept; fixed product URL |
| L-10 | testing | No E2E test for mobile hero-image hidden at 375px | Add to E2E test spec |
| L-11 | testing | Floating nav scroll E2E needs `page.evaluate` scroll specifics | Fix in tasks |
| L-12 | testing | `matchMedia` mock needed for reduced-motion unit tests — not specified | Add to vitest.setup.ts in tasks |
| L-13 | api | No new API routes — clean | Accepted (confirmation) |
| L-14 | api | Telegram URL could be env var | Accept |
| L-15 | data-layer | `auth.getUser()` SSR pattern confirmed correct | Accepted (confirmation) |

---

## Required Spec Fixes Before Implementation (5 items)

These MEDIUM findings must be addressed in the spec before implementation begins:

- [ ] **M-01**: Fix middleware change logic — separate `/` pass-through from `/login` block
- [ ] **M-02**: Add `e2e/auth-flow.spec.ts` update instruction to §E2E Tests
- [ ] **M-04**: Add responsive breakpoint table for pitch-section and stakes-section
- [ ] **M-08**: Replace partial framer-motion mock with Proxy-based catch-all
- [ ] **M-09 + M-10**: Add `chapter-timeline.test.tsx` and `system-terminal.test.tsx` to test file list

## Accepted as-is (document only)

- M-03, M-05, M-07: Spec intent is clear; implementor can apply without spec change

## User Approval

- [ ] User approves proceeding to Phase 5 (planning) after spec fixes above are applied

---

## Individual Validator Reports

- [Frontend](validation-reports/frontend.md)
- [Architecture](validation-reports/architecture.md)
- [Auth](validation-reports/auth.md)
- [Testing](validation-reports/testing.md)
- [API](validation-reports/api.md)
- [Data Layer](validation-reports/data-layer.md)

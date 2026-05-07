# Subspec 217-1 — Cold-Start CTA + Interstitial Reskin + Loading Flash

**Parent**: `specs/217-onboarding-wizard-deterministic-redesign/spec.md` FR-1, FR-2, FR-3
**PR boundary**: 217-1 (depends on 217-0 merged)
**Estimated**: ~150 LOC (FE only)
**Status**: Draft (GATE 1)

---

## Scope

Three coupled FE-only fixes for user-reported failures #1, #2, #3 of the post-Walk-A1 onboarding regression:

1. **Cold-start CTA static `?start=welcome` payload** so Telegram renders a START button regardless of prior chat history.
2. **Interstitial reskin** — replace generic "You're cleared. Enter the portal." copy with Spec 208 brand veil (bg-void + AuroraOrbs + Geist Sans) while preserving the Spec 215 FR-6 iOS PWA + Telegram IAB user-gesture requirement (real touch event for cookie commit).
3. **Loading flash diagnosis + remediation** — eliminate the visible "in development / in progress" copy flash between magic-link click and first wizard frame.

## Acceptance Criteria

| AC | Description | Severity |
|---|---|---|
| AC-1.1 | `portal/src/components/landing/hero-section.tsx:24` ctaHref appended with `?start=welcome` via `URLSearchParams.set("start","welcome")`; URL-parse safe even with pre-existing UTM tags | HIGH |
| AC-1.2 | Same applied to `portal/src/components/landing/cta-section.tsx:17` | HIGH |
| AC-1.3 | Same applied to `portal/src/app/login/page-client.tsx:31` UNAUTHENTICATED branch only; authenticated branch (redirects to `/dashboard`) UNCHANGED | HIGH |
| AC-1.4 | Live walk: real-iPhone Safari (or Chrome MCP iPhone UA spoof), tap landing CTA → assert URL is `t.me/Nikita_my_bot?start=welcome` (parsed); START button at chat bottom; tap; Nikita first reply within 5s (216-A AC A1.4) | HIGH |
| AC-2.1 | `InterstitialClient.tsx` ALWAYS renders Spec 208 brand veil (bg-void + AuroraOrbs + Geist Sans heading + GlowButton tap surface "tap to enter") | HIGH |
| AC-2.2 | Tap surface fires real `click` handler → `router.push(searchParams.get("next") || "/onboarding")` | HIGH (preserves Spec 215 FR-6) |
| AC-2.3 | Programmatic auto-advance fires ONLY when UA is **confirmed** non-iOS + non-IAB (Chrome desktop, Firefox, Edge); iOS + Telegram IAB + spoofed/unknown UAs degrade to brand-veil + tap (default-safe) | HIGH |
| AC-2.4 | UA detection via `next/server` `userAgent()` or `next/headers` for SSR consistency | MEDIUM |
| AC-2.5 | `router.prefetch("/onboarding")` invoked in a `useEffect` for instant transition | MEDIUM |
| AC-2.6 | JWT cookie persists across the interstitial advance (verify via `Set-Cookie` parse on `/onboarding` request post-tap) | HIGH |
| AC-3.1 | Loading flash root cause identified via Chrome MCP DevTools network/Performance trace on cold `/onboarding` mount; documented in PR body | MEDIUM |
| AC-3.2 | Replacement: Spec 208 brand veil + shadcn/ui `Skeleton` matching wizard card silhouette | HIGH |
| AC-3.3 | Time-to-first-deterministic-card ≤200ms p95 warm-cache, ≤500ms p95 cold-start (Playwright `performance.getEntriesByType("navigation")[0].domContentLoadedEventEnd`, 10 runs each) | HIGH |
| AC-3.4 | `expect(page).not.toContainText(/in development|in progress/i)` on `/onboarding` mount | HIGH |
| AC-1.5 | New e2e fixture `portal/e2e/auth-interstitial-pwa.spec.ts` exercising 3 UA cases: desktop Chrome (auto-advance), iOS Safari standalone (brand-veil + tap), Telegram IAB UA (brand-veil + tap) | HIGH |
| AC-1.6 | Pre-push HARD GATE green | HIGH |
| AC-1.7 | `/qa-review --pr <N>` returns 0 findings ALL severities | HIGH |
| AC-1.8 | Live Walk B1 from `simon.yang.ch+walkB1@gmail.com` per `live-testing-protocol.md` 12-step protocol; DB cleanup post-walk | HIGH |

## Files Touched

- `portal/src/components/landing/hero-section.tsx:24`
- `portal/src/components/landing/cta-section.tsx:17`
- `portal/src/app/login/page-client.tsx:31` (unauth branch only)
- `portal/src/app/auth/interstitial/page.tsx` (server-side UA detection)
- `portal/src/app/auth/interstitial/InterstitialClient.tsx` (brand veil + tap surface)
- `portal/src/app/onboarding/loading.tsx` (Skeleton + brand veil — IF identified as flash source per AC-3.1)
- `portal/e2e/auth-interstitial-pwa.spec.ts` (NEW)
- `portal/src/app/onboarding/_components/__tests__/loading-flash.test.tsx` (NEW vitest covering Skeleton render)

## Out of Scope

- Wizard internals (217-3B).
- Backstory hang (217-2).
- BE changes (none required).

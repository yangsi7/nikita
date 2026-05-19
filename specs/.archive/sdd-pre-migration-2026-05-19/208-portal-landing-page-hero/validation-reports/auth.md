## Auth Validation Report

**Spec:** specs/208-portal-landing-page-hero/spec.md
**Status:** PASS
**Timestamp:** 2026-04-03T00:00:00Z

### Summary
- CRITICAL: 0
- HIGH: 0
- MEDIUM: 2
- LOW: 2

### Findings

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| MEDIUM | Middleware Logic | Spec adds `pathname === "/"` to the PUBLIC routes guard at line 58 of `middleware.ts`. However, the current `handleRouting` function has a fallthrough: if `pathname === "/"` is NOT in the public block, unauthenticated users fall to the "Protected routes" block and get redirected to `/login`. Adding `/` to the public block is correct — but the spec must also address the authenticated user path: currently `app/page.tsx` does a server-side `redirect()` for authenticated users. Post-change, `page.tsx` must NOT redirect — it should render the landing page with auth-aware CTAs. The spec handles this but doesn't explicitly call out removal of the `redirect()` calls in `page.tsx`. | spec.md §Routing Change + §Root Page | Explicitly note in spec that the `if (!user) redirect("/login")` and `redirect(role === "admin" ? "/admin" : "/dashboard")` lines in current `page.tsx` are REMOVED, replaced by the new `LandingPage` component. |
| MEDIUM | E2E Auth Bypass | The existing E2E auth bypass (`E2E_AUTH_BYPASS=true`) in `middleware.ts` will also bypass the `/` public route check. The `auth-flow.spec.ts` test "unauthenticated user at / redirects to /login or errors" (line 6-14) will need updating — after this spec, `/` should NOT redirect. The spec includes this as Playwright test case 1 but does not flag the existing conflicting E2E test. | spec.md §E2E Tests + portal/e2e/auth-flow.spec.ts | Add to spec: "Update `e2e/auth-flow.spec.ts` — the existing `/` redirect test must be inverted to assert landing page renders (not redirect to `/login`)." |
| LOW | Session Management | The spec shows `page.tsx` calling `supabase.auth.getUser()` server-side and passing `isAuthenticated` as a boolean. This is the correct, safe pattern (avoids trusting JWT alone). No change to session management architecture. | spec.md §Root Page | No action — confirmed correct. |
| LOW | Admin Route Integrity | The middleware `handleRouting` for `/admin` routes is unchanged. No new routes are added. Existing protected routes (`/dashboard`, `/admin`, `/onboarding`) remain protected. The spec acceptance criteria confirms this: "Existing routes still work." | spec.md §Acceptance Criteria | No action — confirmed. |

### Auth Flow Analysis

**Pre-spec flow (current):**
```
GET /
  → middleware: pathname "/" not in public list → falls to protected block
  → no user: redirect /login
  → user: page.tsx server-side redirect /dashboard (or /admin)
```

**Post-spec flow:**
```
GET /
  → middleware: pathname "/" IS in public list → no redirect
  → no user: page.tsx renders LandingPage, isAuthenticated=false → "Meet Nikita" CTA
  → user: page.tsx renders LandingPage, isAuthenticated=true → "Go to Dashboard" CTA
```

**Critical correctness check:**
The spec middleware change (add `pathname === "/"`) is in `handleRouting()` at line 58. The current condition is:
```typescript
if (pathname === "/login" || pathname.startsWith("/auth/")) {
```
Post-change:
```typescript
if (pathname === "/" || pathname === "/login" || pathname.startsWith("/auth/")) {
```

The logic inside this block redirects **authenticated** users visiting public routes to dashboard/admin. This means:
- Unauthenticated users visiting `/` → pass through → `page.tsx` renders landing (isAuthenticated=false) ✓
- Authenticated users visiting `/` → middleware redirects them to `/dashboard` or `/admin` — **BUT the spec says authenticated users should see the landing page with "Go to Dashboard" CTA**

**THIS IS A CONFLICT.** The middleware public-route block redirects authenticated users AWAY from `/`. But the spec's `LandingPage` component design assumes authenticated users can stay on `/` and see the "Go to Dashboard" button.

**Resolution required**: The spec's middleware change must be more nuanced. Option A: Remove the authenticated redirect from the `/` branch only (let authenticated users stay on `/`). Option B: Keep redirecting authenticated users who explicitly visit `/` to `/dashboard` — but then the "Go to Dashboard" CTA variant is never seen (which defeats the purpose).

**Recommendation: The spec needs to explicitly modify the authenticated redirect logic for `/`.** The middleware change as written in the spec will cause authenticated users to be redirected away from the landing page before they ever see it.

### Protected Routes Checklist
- [x] `/dashboard` — still protected (unchanged middleware logic)
- [x] `/admin` — still protected + role-checked
- [x] `/login` — still public
- [x] `/auth/**` — still public
- [x] `/onboarding` — still protected
- [x] `/` — becomes public (spec intent)
- [ ] Authenticated user behavior on `/` — CONFLICT IDENTIFIED (MEDIUM)

### Recommendations

1. **MEDIUM — Middleware authenticated redirect conflict**: Revise the middleware change spec. The public route block currently redirects authenticated users to dashboard. For `/` specifically, authenticated users should be allowed through (to see the landing page with "Go to Dashboard" CTA). Add this logic:
   ```typescript
   if (pathname === "/") {
     return supabaseResponse // always pass through — page handles auth-aware CTA
   }
   if (pathname === "/login" || pathname.startsWith("/auth/")) {
     if (user) return NextResponse.redirect(...)
     return supabaseResponse
   }
   ```

2. **MEDIUM — Update conflicting E2E test**: Add to spec §E2E Tests: "Also update `e2e/auth-flow.spec.ts` test at line 6-14 — assert that unauthenticated visit to `/` renders landing page (status 200, heading visible), not that it redirects to `/login`."

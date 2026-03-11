# Auth Validation Report

**Spec:** `specs/112-portal-e2e-hardening/spec.md`
**Status:** PASS
**Timestamp:** 2026-03-11T00:00:00Z

## Summary
- CRITICAL: 0
- HIGH: 0
- MEDIUM: 3
- LOW: 2

## Findings

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| MEDIUM | Auth Bypass Safety | Spec relies on `NODE_ENV !== "production"` dead-code elimination in Next.js middleware, but middleware runs in the Edge Runtime where tree-shaking behavior differs from client bundles. The code is NOT statically eliminated -- it remains in the production bundle but the condition evaluates to false at runtime. This is functionally safe but not "dead-code-eliminated" as claimed in AC-2.6. | spec.md:89,113 | Add a secondary guard: check that `E2E_AUTH_BYPASS` is not set in Vercel environment variables. Document that the guard is runtime (not compile-time) for middleware. Consider adding a startup warning log if `E2E_AUTH_BYPASS=true` is detected in production NODE_ENV. |
| MEDIUM | Auth Bypass Safety | No explicit test verifying the production guard. The existing middleware vitest tests (`portal/src/__tests__/middleware.test.ts`) do not test that the bypass is inactive when `NODE_ENV=production`. | middleware.test.ts | Add vitest tests: (1) with `NODE_ENV=production` + `E2E_AUTH_BYPASS=true`, verify bypass is NOT active and real `getUser()` is called; (2) with `NODE_ENV=test` + `E2E_AUTH_BYPASS=true`, verify bypass IS active. |
| MEDIUM | Mock User Shape | Mock admin user uses `{ user_metadata: { role: "admin" } }` (AC-2.3) but the real admin check in middleware also accepts `@nanoleq.com` email domain (line 35-36 of middleware.ts). The mock admin email `e2e-admin@nanoleq.com` passes BOTH checks, which means tests cannot distinguish which admin path was taken. | spec.md:110 | Consider using a non-nanoleq email for mock admin (e.g., `e2e-admin@test.local`) with `user_metadata: { role: "admin" }` to test the metadata path explicitly. Or add a separate test for domain-based admin. |
| LOW | Env Var Documentation | `.env.example` does not mention `E2E_AUTH_BYPASS` or `E2E_AUTH_ROLE`. Developers may not know these exist. | portal/.env.example | Add commented-out entries: `# E2E_AUTH_BYPASS=true` and `# E2E_AUTH_ROLE=player` with a comment explaining they are for Playwright E2E only and must never be set in production. |
| LOW | Security Headers | `vercel.json` has security headers (X-Content-Type-Options, X-Frame-Options, Referrer-Policy) but is missing HSTS. Not directly related to the E2E bypass but noted during review. | portal/vercel.json:12-20 | Add `Strict-Transport-Security: max-age=31536000; includeSubDomains` header. |

## Auth Flow Analysis

**Primary Method:** Supabase SSR with PKCE (magic link login)
**Session Type:** Cookie-based (Supabase SSR cookies managed via `createServerClient`)
**Token Handling:** Supabase handles JWT internally; cookies set/refreshed in middleware via `setAll` callback

### E2E Auth Bypass Design Review

The spec proposes an env-gated middleware bypass. Here is my security assessment of each layer:

**Layer 1 -- Server-side only env var (no `NEXT_PUBLIC_` prefix):**
- SECURE. `E2E_AUTH_BYPASS` and `E2E_AUTH_ROLE` without `NEXT_PUBLIC_` prefix are never bundled into client-side JavaScript. They are only accessible in server-side code (middleware, API routes, server components). A browser cannot set or read these values.

**Layer 2 -- `NODE_ENV !== "production"` runtime guard:**
- SECURE but mischaracterized. The spec claims dead-code elimination (AC-2.6), but Next.js middleware compiles to Edge Runtime where `process.env.NODE_ENV` is a runtime check, not a compile-time constant. The bypass code WILL exist in the production bundle but will never execute because `NODE_ENV === "production"` in Vercel deployments. This is functionally equivalent but the spec should clarify the mechanism.

**Layer 3 -- Not set in Vercel/Cloud Run:**
- SECURE by convention. These env vars are never configured in Vercel dashboard. However, this is a process control, not a technical control. Recommendation: add a CI lint step or deployment checklist item.

**Layer 4 -- Two Playwright projects (player port 3003, admin port 3004):**
- SECURE. Each project gets its own `webServer` with the appropriate `E2E_AUTH_ROLE`. The dev servers are ephemeral and only run during test execution.

**Overall assessment: The multi-layer defense is sound.** No single failure point can enable the bypass in production. Even if someone accidentally set `E2E_AUTH_BYPASS=true` in Vercel, the `NODE_ENV !== "production"` guard would prevent activation.

## Role & Permission Matrix

| Role | `/login` | `/dashboard/*` | `/admin/*` | Bypass Mock Shape |
|------|----------|----------------|------------|-------------------|
| Unauthenticated | Allowed | Redirect to `/login` | Redirect to `/login` | N/A |
| Player | Redirect to `/dashboard` | Allowed | Redirect to `/dashboard` | `{ id: "e2e-player-id", email: "e2e-player@test.local", user_metadata: {} }` |
| Admin (metadata) | Redirect to `/admin` | Allowed | Allowed | `{ id: "e2e-admin-id", email: "e2e-admin@nanoleq.com", user_metadata: { role: "admin" } }` |
| Admin (domain) | Redirect to `/admin` | Allowed | Allowed | Not separately mocked |

The mock user shapes in AC-2.2 and AC-2.3 correctly match the existing `isAdmin()` logic in `portal/src/lib/supabase/middleware.ts` lines 33-37.

## Protected Resources

| Resource | Auth Required | Allowed Roles | E2E Coverage (Current) | E2E Coverage (Target) |
|----------|--------------|---------------|------------------------|----------------------|
| `/login` | No (public) | All | Yes (login.spec.ts) | Yes |
| `/auth/callback` | No (public) | All | Yes (auth-flow.spec.ts) | Yes |
| `/dashboard` | Yes | Player, Admin | Yes (dashboard.spec.ts) | Yes (rewrite) |
| `/dashboard/*` (14 routes) | Yes | Player, Admin | Partial (5/14) | Yes (25/25) |
| `/admin/*` (9 routes) | Yes | Admin only | Partial (3/9) | Yes (25/25) |

## Security Checklist
- [x] Rate limiting on login - N/A (Supabase handles rate limiting on magic link sends)
- [x] Account lockout policy - N/A (Supabase handles this)
- [x] Session invalidation on logout - Handled by Supabase SSR
- [x] CSRF protection - Supabase PKCE flow provides CSRF protection
- [x] Security headers (CSP, HSTS) - Partial (X-Content-Type-Options, X-Frame-Options, Referrer-Policy present; HSTS missing)
- [x] E2E bypass cannot reach production - Multi-layer guard (server-only env + NODE_ENV check)
- [x] Mock user shapes match real auth logic - Yes (metadata role + domain check)
- [x] No NEXT_PUBLIC_ prefix on bypass vars - Specified in AC-2.5
- [x] Separate Playwright projects per role - Specified in AC-2.4

## Recommendations

1. **MEDIUM -- Add production guard tests.** Write vitest tests in `portal/src/__tests__/middleware.test.ts` that verify: (a) when `NODE_ENV=production` and `E2E_AUTH_BYPASS=true`, the bypass is NOT active; (b) when `NODE_ENV=test` and `E2E_AUTH_BYPASS=true`, the bypass IS active. This prevents regressions on the safety guard itself.

2. **MEDIUM -- Clarify dead-code elimination claim.** Update AC-2.6 wording from "dead-code-eliminated in production builds" to "guarded by runtime `NODE_ENV` check; bypass code exists in bundle but cannot execute in production (`NODE_ENV === 'production'`)." This sets correct expectations for implementers.

3. **MEDIUM -- Consider separating mock admin paths.** Use `e2e-admin@test.local` (non-nanoleq email) for the mock admin user so tests exercise the `user_metadata.role === "admin"` path explicitly. The current mock email `e2e-admin@nanoleq.com` satisfies both admin checks simultaneously, masking which path the middleware took.

4. **LOW -- Document E2E env vars in `.env.example`.** Add commented-out entries for `E2E_AUTH_BYPASS` and `E2E_AUTH_ROLE` with a warning comment: `# Playwright E2E only -- NEVER set in production`.

5. **LOW -- Add HSTS header to `vercel.json`.** Add `Strict-Transport-Security: max-age=31536000; includeSubDomains` to the existing security headers block.

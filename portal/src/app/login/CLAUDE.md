# portal/src/app/login/ — Magic-Link Login

## Purpose

Magic-link authentication entry surface for the portal. Sends a one-time link via Supabase `signInWithOtp`, then poll-waits in a Suspense-backed UI with 60s resend cooldown. Alternative entry to `/onboarding/auth/` (the wizard-flow login).

## Key Files

- `page.tsx` — server component shell wrapping the client component; sets metadata.
- `page-client.tsx` — `"use client"` component:
  - Email input + submit → `supabase.auth.signInWithOtp({ email, options: { emailRedirectTo: ${origin}/auth/confirm } })` (`page-client.tsx:97`, post-EM-1).
  - `ResendButton` component with 60s cooldown timer (`page-client.tsx:11-43`).
  - Resend handler at `:21` (second `signInWithOtp` call, also `/auth/confirm`).
  - Toast feedback via `sonner`; rate-limit branch resets cooldown to 60s.

## Callers

- Direct user navigation to `/login`.
- Linked from `portal/src/app/page.tsx` landing-page nav (login link).
- Server-side redirect from middleware when an unauthenticated user hits a protected route.
- NOT the canonical onboarding entry — see `portal/src/app/onboarding/auth/` for the wizard-flow login. **Dual auth surface** flagged as smell in `memory/user-journeys.md` (W4 audit 2026-05-05).

## Gotchas

- **Dual `signInWithOtp` surface**: this page (`page-client.tsx:97,26`) AND `onboarding/auth/page-client.tsx:52,106` both issue magic-link sign-in. Both target unified `/auth/confirm` handler post-EM-1. Duplicated copy remains; consolidate when convenient.
- **`emailRedirectTo`** uses `window.location.origin` — Next.js 16 SSR/CSR boundary; must run in client component (already enforced by `"use client"`).
- **Cooldown is client-side only**: 60s timer is for UX; Supabase enforces the actual rate limit server-side. Rate-limit error message check at `:30-34` is substring match (`"rate"` or `"limit"`) — fragile if Supabase error wording changes.
- **Suspense boundary**: `page-client.tsx` wraps `useSearchParams()` consumer in `<Suspense>` to avoid Next.js 16 build-time error on prerender.
- **Auth callback URL is `/auth/confirm`** (EM-1, post-fix/216-EM1): the unified PKCE handler lives at `src/app/auth/confirm/route.ts` and is always live. Failure redirects target `/onboarding/auth?error=...` for funnel-copy consistency.

## Navigation

- Parent: [`portal/CLAUDE.md`](../../../CLAUDE.md)
- Sibling onboarding entry: `portal/src/app/onboarding/auth/`
- Auth callback (downstream): `portal/src/app/auth/`
- Backend auth model: [`memory/integrations.md`](../../../../memory/integrations.md) §Supabase

Last verified: 2026-05-05

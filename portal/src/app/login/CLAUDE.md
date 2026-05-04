# portal/src/app/login/ — Magic-Link Login

## Purpose

Magic-link authentication entry surface for the portal. Sends a one-time link via Supabase `signInWithOtp`, then poll-waits in a Suspense-backed UI with 60s resend cooldown. Alternative entry to `/onboarding/auth/` (the wizard-flow login).

## Key Files

- `page.tsx` — server component shell wrapping the client component; sets metadata.
- `page-client.tsx` — `"use client"` component:
  - Email input + submit → `supabase.auth.signInWithOtp({ email, options: { emailRedirectTo: ${origin}/auth/callback } })` (`page-client.tsx:24`).
  - `ResendButton` component with 60s cooldown timer (`page-client.tsx:11-43`).
  - Resend handler at `:94` (second `signInWithOtp` call).
  - Toast feedback via `sonner`; rate-limit branch resets cooldown to 60s.

## Callers

- Direct user navigation to `/login`.
- Linked from `portal/src/app/page.tsx` landing-page nav (login link).
- Server-side redirect from middleware when an unauthenticated user hits a protected route.
- NOT the canonical onboarding entry — see `portal/src/app/onboarding/auth/` for the wizard-flow login. **Dual auth surface** flagged as smell in `memory/user-journeys.md` (W4 audit 2026-05-05).

## Gotchas

- **Dual `signInWithOtp` surface**: this page (`page-client.tsx:24,94`) AND `onboarding/auth/page-client.tsx:50,101` both issue magic-link sign-in. Duplicated copy/redirect logic; consolidate when convenient.
- **`emailRedirectTo`** uses `window.location.origin` — Next.js 16 SSR/CSR boundary; must run in client component (already enforced by `"use client"`).
- **Cooldown is client-side only**: 60s timer is for UX; Supabase enforces the actual rate limit server-side. Rate-limit error message check at `:30-34` is substring match (`"rate"` or `"limit"`) — fragile if Supabase error wording changes.
- **Suspense boundary**: `page-client.tsx` wraps `useSearchParams()` consumer in `<Suspense>` to avoid Next.js 16 build-time error on prerender.
- **Auth callback URL**: `/auth/callback` route handler must exist (Supabase exchanges code for session there). Comment at `onboarding/auth/page.tsx:7` references it; `page.tsx` for `/auth/callback` not located in current portal tree (route handler `route.ts` may exist — verify on master before relying).

## Navigation

- Parent: [`portal/CLAUDE.md`](../../../CLAUDE.md)
- Sibling onboarding entry: `portal/src/app/onboarding/auth/`
- Auth callback (downstream): `portal/src/app/auth/`
- Backend auth model: [`memory/integrations.md`](../../../../memory/integrations.md) §Supabase

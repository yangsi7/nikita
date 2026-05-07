# portal/ — Player Dashboard & Admin Portal

## Purpose

Next.js web application for player stats, admin tools, and game monitoring. Deployed on Vercel.

## Status: Complete

## Tech Stack

- **Framework**: Next.js 16 (App Router)
- **UI**: shadcn/ui + Tailwind CSS
- **Auth**: Supabase SSR (`@supabase/ssr`)
- **Data**: TanStack React Query + Supabase client
- **Testing**: Playwright E2E

## Commands

```bash
npm run dev            # Local dev server
npm run build          # Production build
npm run test:e2e       # Playwright E2E tests
npm run lint           # ESLint
```

## Architecture

```
portal/
├── src/
│   ├── app/                    # App Router pages
│   │   ├── layout.tsx          # Root layout (providers, fonts)
│   │   ├── page.tsx            # Landing page
│   │   ├── login/              # Login page (magic link)
│   │   ├── auth/               # Auth callback handler
│   │   ├── dashboard/          # Player dashboard (stats, score history)
│   │   └── admin/              # Admin pages
│   │       ├── users/          # User management
│   │       ├── pipeline/       # Pipeline health monitor
│   │       ├── prompts/        # Prompt testing
│   │       ├── text/           # Text conversation viewer
│   │       ├── voice/          # Voice session viewer
│   │       └── jobs/           # Background job monitor
│   ├── components/             # Shared UI components (shadcn/ui)
│   ├── hooks/                  # Custom React hooks
│   └── lib/                    # Utilities, Supabase client, API helpers
├── e2e/                        # Playwright test files
├── middleware.ts               # Auth middleware (route protection)
├── components.json             # shadcn/ui configuration
└── vercel.json                 # Vercel deployment config
```

## Patterns

### Supabase Auth (SSR)
```typescript
// src/lib/supabase/server.ts — server-side client
import { createServerClient } from '@supabase/ssr'

// middleware.ts — route protection
// Redirects unauthenticated users to /login
// Admin routes require admin role
```

### API Calls
All backend calls go through the FastAPI backend URL configured in env vars.
Use TanStack React Query for caching and state management.

### Design System
- Use shadcn/ui components via `components.json` configuration
- Tailwind CSS for styling — no inline styles
- Follow existing component patterns in `src/components/`

## Environment Variables

Set via Vercel dashboard or `.env.local`:
- `NEXT_PUBLIC_SUPABASE_URL` — Supabase project URL
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` — Supabase anon key
- `NEXT_PUBLIC_API_URL` — Backend API base URL

## Documentation

- [Deployment](../CLAUDE.md#deployment)
- [Backend API](../nikita/api/CLAUDE.md)

## Callers

- Vercel — receives all inbound HTTPS traffic; canonical apex `nikita-mygirl.com` (no redirect); www → 308 → apex.
- Direct user navigation (landing → onboarding → dashboard).
- Push notifications deep-linking to `/dashboard/nikita/{day,mind,circle,stories}`.
- E2E tests (Playwright) at `portal/e2e/`.

## Gotchas

- **Apex is canonical, www redirects 308 → apex**. CORS allowlist on backend MUST include the canonical apex (post-redirect Origin header). PR #294 precedent — see `.claude/rules/vercel-cors-canonical.md`.
- **`E2E_AUTH_BYPASS=true` shortcut** at `src/app/onboarding/page.tsx:49-51` hard-codes `userId="e2e-player-id"`. Guarded by `NODE_ENV !== "production"` (parity with `src/lib/supabase/middleware.ts:10`). Spec 216-EM3a hardened the parity invariant via comment + test coverage; smell #6 from the wizard-redesign-composed-micali plan resolved.
- **Public env fail-fast**: `src/lib/env.ts` throws at module load when `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_API_URL`, or `NEXT_PUBLIC_TELEGRAM_BOT_USERNAME` is missing (skipped under `NODE_ENV=test`). Use `env.X` over bare `process.env.X!` non-null assertions when adding new code (Spec 216-EM3a). NOTE: `env.TELEGRAM_BOT_USERNAME` has no consumer on master yet — module exists to unblock EM-2 (Telegram auto-bind PR), do NOT delete during drift audits.
- **Single `signInWithOtp` surface (post-217-0)**: `src/app/login/page-client.tsx:24,94` is the only surviving caller. The `src/app/onboarding/auth/page-client.tsx` was deleted in PR #537 (Spec 216-G) when the canonical signup flipped to TG-first. The route now lives only as a 410 GONE stub at `src/app/onboarding/auth/route.ts` (TODO delete-after 2026-06-06 per Spec 217-0 tombstone window).
- **Auth callback URL unified to `/auth/confirm`** (EM-1, fix/216-EM1): magic-link `emailRedirectTo` from both `/login` and `/onboarding/auth` targets the PKCE handler at `src/app/auth/confirm/route.ts`. The legacy `/auth/callback` shim was removed; failures redirect to `/onboarding/auth?error=...` for funnel-copy consistency.
- **Vercel project-rename gotcha**: renaming a Vercel project leaves stale auto-generated aliases attached. Audit + clean per `.claude/rules/vercel-cors-canonical.md`.
- **CSP + Suspense**: pages with `Math.random()` / `Date.now()` / `new Date()` in SSR'd Client Components hydrate-mismatch. Wrap in `useEffect` mount-guard or `next/dynamic({ ssr: false })`.
- **Per-page loading skeletons**: every data-driven page should use `<LoadingSkeleton variant="..." />` from `src/components/shared/loading-skeleton.tsx` — DO NOT roll one-off spinners.

## Navigation

- Sub-page CLAUDE.md (W5 + W7b backfill):
  - [`src/app/login/CLAUDE.md`](src/app/login/CLAUDE.md)
  - [`src/app/admin/prompts/CLAUDE.md`](src/app/admin/prompts/CLAUDE.md)
  - [`src/app/admin/research-lab/CLAUDE.md`](src/app/admin/research-lab/CLAUDE.md)
  - [`src/app/admin/users/CLAUDE.md`](src/app/admin/users/CLAUDE.md)
  - [`src/app/dashboard/nikita/CLAUDE.md`](src/app/dashboard/nikita/CLAUDE.md)
- Root toolkit: [`../.claude/CLAUDE.md`](../.claude/CLAUDE.md)
- User journeys canonical: [`../memory/user-journeys.md`](../memory/user-journeys.md)
- Backend integration: [`../memory/integrations.md`](../memory/integrations.md)

Last verified: 2026-05-05

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

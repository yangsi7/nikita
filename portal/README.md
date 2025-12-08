# Nikita Portal

**Nikita: Don't Get Dumped** - AI Girlfriend Game Player Dashboard

## Overview

Player-facing web portal for tracking relationship stats, conversation history, and game progress with Nikita.

## Features

✅ **Authentication**: Magic link login via Supabase
✅ **Dashboard**: Real-time stats with 30s auto-refresh
✅ **Score Tracking**: Circular progress with trend analysis
✅ **Chapter Progress**: Visual journey through 5 chapters
✅ **Engagement Monitor**: 6-state system (calibrating, in_zone, drifting, clingy, distant, out_of_zone)
✅ **Hidden Metrics**: Intimacy (30%), Passion (25%), Trust (25%), Secureness (20%)
✅ **Vice Tracking**: 8 personality categories
✅ **Decay Warnings**: Real-time score decay alerts
✅ **History**: Score graphs + daily summaries
✅ **Conversations**: Past interactions with score impact

## Tech Stack

- **Framework**: Next.js 16.0.7 (App Router)
- **UI**: shadcn/ui + Tailwind CSS v4
- **Data**: TanStack Query v5 (30s polling)
- **Auth**: Supabase SSR
- **Charts**: Recharts 3.5.1
- **Theme**: Dark + red accents

## Quick Start

```bash
# Install
pnpm install

# Dev server
pnpm dev

# Build
pnpm build

# Production
pnpm start
```

## Environment Variables

Create `.env.local`:

```bash
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_API_URL=https://your-backend.run.app
```

## Deploy to Vercel

1. Push to GitHub
2. Import in Vercel dashboard
3. Add environment variables
4. Deploy!

**Or use Vercel CLI:**

```bash
vercel
vercel --prod
```

## Project Structure

```
portal/
├── src/app/              # Pages (Next.js App Router)
├── src/components/       # React components
├── src/lib/              # API client, utilities
├── src/hooks/            # React Query hooks
└── public/               # Static assets
```

## API Endpoints

- `GET /api/v1/portal/stats` - User stats
- `GET /api/v1/portal/engagement` - Engagement state
- `GET /api/v1/portal/vices` - Vice preferences
- `GET /api/v1/portal/conversations` - History
- `GET /api/v1/portal/score-history` - Timeline
- `GET /api/v1/portal/daily-summary/:date` - Daily recap

## Design System

**Colors**: Deep black background, red primary, subtle borders
**Typography**: Geist Sans (clean, minimal)
**Components**: shadcn/ui (New York style)

## License

MIT

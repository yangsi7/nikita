# Memory Changelog

Documents changes to what is currently implemented in the Nikita codebase.

## [0.3.0] - 2025-12-09

### Portal Frontend
- **Added** `portal/src/lib/supabase/proxy.ts` - Supabase SSR session refresh utility
- **Changed** `portal/src/proxy.ts` - Refactored to use shared updateSession utility
- **Fixed** Session cookie handling - Proper refresh for both server components and browser

### Backend
- **No changes** - Backend JWT auth already deployed in 0.2.0

## [0.2.0] - 2025-12-09

### Backend
- **Added** `nikita/api/dependencies/auth.py` - Supabase JWT authentication
  - PyJWT-based token validation with HS256 algorithm
  - Validates `sub` claim for user ID extraction
  - Proper 401/403 error responses with WWW-Authenticate header
- **Added** `SUPABASE_JWT_SECRET` environment variable to Cloud Run
- **Added** PyJWT 2.8.0 dependency to pyproject.toml
- **Changed** `nikita/api/routes/portal.py` - Uses JWT auth dependency
  - All endpoints now require valid Supabase JWT
  - Portal-first users auto-created on first dashboard visit
- **Changed** `nikita/api/schemas/portal.py` - Added metrics to UserStatsResponse

### Portal Frontend
- **Fixed** Next.js 16 proxy naming (confirmed `proxy.ts` is correct, not middleware.ts)
- **Added** Magic link code detection on landing page

## [0.1.0] - 2025-12-08

### Portal Frontend (008-player-portal)
- **Added** Next.js 16.0.7 application in `portal/` directory
- **Added** Magic link authentication with Supabase
- **Added** Dashboard layout with:
  - Stats card (relationship score, chapter, metrics)
  - Score history chart
  - Engagement state display
  - Conversation history
- **Added** Playwright E2E test suite (28 tests)
- **Added** CI/CD with ESLint, TypeScript, and pre-commit hooks

### Tech Stack
| Component | Technology |
|-----------|------------|
| Framework | Next.js 16.0.7 |
| Auth | @supabase/ssr 0.8.0 |
| Styling | Tailwind CSS 4 + shadcn/ui |
| Testing | Playwright 1.57.0 |

## [Previous] - 2025-12-01 to 2025-12-07

### Phase 2: Telegram Integration
- Telegram bot deployed to Cloud Run
- Webhook endpoint at `/api/v1/telegram/webhook`
- Message handling with text agent integration
- Rate limiting and error handling

### Phase 1: Text Agent
- Pydantic AI text agent with Claude Sonnet
- 156 tests passing
- Context engineering pipeline
- Memory integration with Graphiti

---

## File Status

| File | Purpose | Last Updated |
|------|---------|--------------|
| architecture.md | System design | 2025-12-03 |
| backend.md | API patterns | 2025-12-01 |
| constitution.md | Development principles | 2025-11-29 |
| game-mechanics.md | Scoring, chapters, decay | 2025-12-05 |
| integrations.md | External services | 2025-12-04 |
| product.md | Product definition | 2025-11-28 |
| user-journeys.md | User flows | 2025-11-29 |

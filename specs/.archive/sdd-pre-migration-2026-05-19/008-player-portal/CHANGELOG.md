# 008-player-portal Changelog

All notable changes to this specification are documented here.

## [0.3.0] - 2025-12-09

### Fixed
- **Supabase SSR session handling** - Added `lib/supabase/proxy.ts` with `updateSession` utility per official Supabase SSR docs
- **Session cookie refresh** - Cookies now properly set on both request (for server components) and response (for browser)
- **Token validation** - Using `getUser()` instead of `getSession()` for server-side JWT validation

### Changed
- **proxy.ts refactored** - Now uses shared `updateSession` utility instead of inline cookie handling

### Added
- `portal/src/lib/supabase/proxy.ts` - Session refresh utility with proper cookie handling

## [0.2.0] - 2025-12-09

### Fixed
- **Backend JWT authentication** - Implemented proper Supabase JWT validation (was TODO placeholder returning 401)
- **Portal-first user auto-creation** - Users created on first dashboard visit if they don't exist in DB
- **Next.js 16 proxy naming** - Confirmed `proxy.ts` (not middleware.ts) is correct for Next.js 16

### Added
- `nikita/api/dependencies/auth.py` - JWT validation with PyJWT
- `pyproject.toml` - Added PyJWT dependency
- Environment variable: `SUPABASE_JWT_SECRET` on Cloud Run

### Changed
- `nikita/api/routes/portal.py` - Now uses JWT auth dependency + auto-creates portal-first users
- `nikita/api/schemas/portal.py` - Added metrics to UserStatsResponse

## [0.1.0] - 2025-12-08

### Added
- Initial portal frontend with Next.js 16
- Magic link authentication via Supabase
- Dashboard layout with stats, history, and engagement components
- Playwright E2E test suite (28 tests)
- CI/CD pipeline with ESLint, TypeScript, and pre-commit hooks

### Technical Details
- Framework: Next.js 16.0.7
- Auth: @supabase/ssr 0.8.0
- Styling: Tailwind CSS 4 + shadcn/ui
- Testing: Playwright 1.57.0

## Implementation Status

| Phase | Status | Description |
|-------|--------|-------------|
| Frontend | ✅ Complete | Next.js 16 dashboard with magic link auth |
| Backend Auth | ✅ Complete | JWT validation + portal-first user flow |
| Supabase SSR | ✅ Complete | Proper session refresh with updateSession |
| API Integration | 🔄 Testing | Dashboard data loading |
| Vercel Deploy | ⏳ Pending | Deploy with new proxy changes |

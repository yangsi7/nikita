# Event Stream
<!-- Max 25 lines, prune oldest when exceeded -->

[2025-12-06T00:15:00Z] BUG: Magic link redirects to localhost:3000 (Supabase SITE_URL default)
[2025-12-06T00:20:00Z] RCA: Verified with Supabase docs - email_redirect_to parameter needed
[2025-12-06T00:25:00Z] FIX: Added email_redirect_to in auth.py + /auth/confirm endpoint
[2025-12-06T00:30:00Z] DEPLOY: Cloud Run revision 00032-nc8 deployed to gcp-transcribe-test
[2025-12-06T00:35:00Z] DOCS: Updated CLAUDE.md with strict documentation-first enforcement rule
[2025-12-07T01:00:00Z] BUG: Magic link shows error in fragment (#error=otp_expired) but displays JSON
[2025-12-07T01:15:00Z] RCA: /auth/confirm has no error handling, Supabase sends errors in URL fragment
[2025-12-07T01:30:00Z] FIX: Added error page + JS fragment extraction + dual registration flows
[2025-12-07T01:45:00Z] DEPLOY: Cloud Run revision 00033-wbl deployed - magic link error handling
[2025-12-07T02:00:00Z] GIT: Committed magic link fix (a0412e6) - error handling + dual flows
[2025-12-07T02:05:00Z] GIT: Committed portal backend (ce3ff09) - routes, models, repos (1631 lines)
[2025-12-07T02:10:00Z] GIT: Committed portal frontend (fd120cc) - Next.js dashboard (7211 lines)
[2025-12-07T02:15:00Z] GIT: Pushed feature/008-player-portal branch to origin
[2025-12-08T20:25:00Z] CICD: Created GitHub Actions workflow for portal (lint, type-check, format)
[2025-12-08T20:30:00Z] LINT: Added Prettier config (.prettierrc.json, .prettierignore)
[2025-12-08T20:35:00Z] LINT: Installed prettier, husky, lint-staged dev dependencies
[2025-12-08T20:40:00Z] HOOKS: Configured Husky pre-commit hooks (ESLint, Prettier, TypeScript)
[2025-12-08T20:45:00Z] FORMAT: Formatted all portal source files with Prettier (29 files)
[2025-12-08T20:50:00Z] BUILD: Verified portal production build succeeds (Next.js 16.0.7)
[2025-12-08T20:55:00Z] DOCS: Created TESTING.md - comprehensive manual testing guide
[2025-12-08T21:00:00Z] DOCS: Created VERCEL_SETUP.md - step-by-step Vercel deployment guide

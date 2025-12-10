# Event Stream
<!-- Max 25 lines, prune oldest when exceeded -->

[2025-12-10T10:30:00Z] BUG_REPORT: Magic link PKCE error - "both auth code and code verifier should be non-empty"
[2025-12-10T10:35:00Z] RESEARCH: Supabase PKCE flow docs + auth logs analysis
[2025-12-10T10:40:00Z] RCA: Code verifier stored in browser, but server callback can't access it
[2025-12-10T10:45:00Z] PLAN: Redirect to / (client page) instead of /auth/callback (server route)
[2025-12-10T10:50:00Z] FILE_EDIT: portal/src/lib/supabase/client.ts - emailRedirectTo changed to /
[2025-12-10T10:52:00Z] FILE_EDIT: portal/src/app/page.tsx - removed manual code forwarding
[2025-12-10T10:53:00Z] FILE_EDIT: portal/src/proxy.ts - skip dashboard redirect if code param present
[2025-12-10T10:54:00Z] FILE_EDIT: portal/src/app/auth/callback/route.ts - fallback handler + logging
[2025-12-10T10:55:00Z] VERIFY: pnpm type-check ✅ passing
[2025-12-10T10:56:00Z] GIT: Committed PKCE fix (bda75ef) - 4 files changed
[2025-12-10T10:57:00Z] GIT: Pushed to origin/feature/008-player-portal
[2025-12-10T11:05:00Z] RCA: Domain mismatch - NEXT_PUBLIC_SITE_URL=portal-yangsi7s vs access via portal-phi-orcin
[2025-12-10T11:10:00Z] SOLUTION: Use window.location.origin for dynamic redirect (same-domain PKCE)
[2025-12-10T11:12:00Z] FILE_EDIT: portal/src/lib/supabase/client.ts - loginWithMagicLink uses window.location.origin
[2025-12-10T11:13:00Z] VERIFY: pnpm type-check ✅ passing
[2025-12-10T11:14:00Z] GIT: Committed domain fix (ddce4f9) - 1 file changed
[2025-12-10T11:15:00Z] GIT: Pushed to origin/feature/008-player-portal
[2025-12-10T11:16:00Z] DEPLOY: Vercel production ✅ Ready (portal-1h8b1l5cw)
[2025-12-10T11:20:00Z] RCA: Browser client doesn't auto-detect PKCE codes - manual exchange required
[2025-12-10T11:25:00Z] SOLUTION: Add useEffect to manually call exchangeCodeForSession(code)
[2025-12-10T11:30:00Z] FILE_EDIT: portal/src/app/page.tsx - manual PKCE code exchange on page load
[2025-12-10T11:35:00Z] VERIFY: pnpm type-check ✅ passing
[2025-12-10T11:40:00Z] GIT: Committed manual exchange (428a883) - 1 file changed
[2025-12-10T11:45:00Z] GIT: Pushed to origin/feature/008-player-portal
[2025-12-10T11:50:00Z] DEPLOY: Vercel production ✅ Ready (portal-euiwp1jnd)

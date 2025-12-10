# Event Stream
<!-- Max 25 lines, prune oldest when exceeded -->

[2025-12-10T11:10:00Z] SOLUTION: Use window.location.origin for dynamic redirect (same-domain PKCE)
[2025-12-10T11:12:00Z] FILE_EDIT: portal/src/lib/supabase/client.ts - loginWithMagicLink uses window.location.origin
[2025-12-10T11:14:00Z] GIT: Committed domain fix (ddce4f9) - 1 file changed
[2025-12-10T11:20:00Z] RCA: Browser client doesn't auto-detect PKCE codes - manual exchange required
[2025-12-10T11:25:00Z] SOLUTION: Add useEffect to manually call exchangeCodeForSession(code)
[2025-12-10T11:30:00Z] FILE_EDIT: portal/src/app/page.tsx - manual PKCE code exchange on page load
[2025-12-10T11:40:00Z] GIT: Committed manual exchange (428a883) - 1 file changed
[2025-12-10T11:50:00Z] DEPLOY: Vercel production ✅ Ready (portal-euiwp1jnd)
[2025-12-10T12:00:00Z] BUG_REPORT: "Failed to fetch user stats" after successful login
[2025-12-10T12:05:00Z] DEEP_RCA: Complete flow analysis (auth logs, backend logs, DB schema, RLS)
[2025-12-10T12:10:00Z] ROOT_CAUSE_1: NEXT_PUBLIC_API_URL missing from Vercel environment
[2025-12-10T12:11:00Z] ROOT_CAUSE_2: User exists in auth.users but not in public.users
[2025-12-10T12:12:00Z] ROOT_CAUSE_3: Portal-first flow needs user creation on first API call
[2025-12-10T12:15:00Z] EVIDENCE: Cloud Run logs show 401 Unauthorized on /portal/stats
[2025-12-10T12:16:00Z] EVIDENCE: fetch() calling "undefined/api/v1/portal/stats" (API_URL undefined)
[2025-12-10T12:17:00Z] EVIDENCE: RLS policies verified - service_role has full access to users table
[2025-12-10T12:20:00Z] FIX: Added NEXT_PUBLIC_API_URL to all Vercel environments (prod/preview/dev)
[2025-12-10T12:21:00Z] VALUE: https://nikita-api-7xw52ajcea-uc.a.run.app
[2025-12-10T12:25:00Z] FILE_EDIT: portal/src/lib/api/client.ts - enhanced logging (API_URL, errors)
[2025-12-10T12:30:00Z] GIT: Committed env config (57967a7) + logging (04f0525)
[2025-12-10T12:31:00Z] GIT: Pushed to origin/feature/008-player-portal
[2025-12-10T12:32:00Z] DEPLOY: Vercel auto-deploying with new environment variables
[2025-12-10T12:35:00Z] NEXT: User needs to test magic link flow + verify dashboard loads

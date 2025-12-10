# Event Stream
<!-- Max 25 lines, prune oldest when exceeded -->

[2025-12-10T12:00:00Z] BUG_REPORT: "Failed to fetch user stats" after successful login
[2025-12-10T12:05:00Z] DEEP_RCA: Complete flow analysis (auth logs, backend logs, DB schema, RLS)
[2025-12-10T12:10:00Z] ROOT_CAUSE_1: NEXT_PUBLIC_API_URL missing from Vercel environment
[2025-12-10T12:16:00Z] EVIDENCE: fetch() calling "undefined/api/v1/portal/stats" (API_URL undefined)
[2025-12-10T12:20:00Z] FIX: Added NEXT_PUBLIC_API_URL to Vercel (https://nikita-api-7xw52ajcea-uc.a.run.app)
[2025-12-10T12:25:00Z] FILE_EDIT: portal/src/lib/api/client.ts - enhanced logging (API_URL, errors)
[2025-12-10T12:30:00Z] GIT: Committed env config (57967a7) + logging (04f0525)
[2025-12-10T12:32:00Z] DEPLOY: Vercel auto-deploying with new environment variables
[2025-12-10T17:20:00Z] DEBUG: MCP-driven magic link flow test via Chrome DevTools + Gmail
[2025-12-10T17:21:00Z] ROOT_CAUSE: CORS blocking - cors_origins only had localhost:3000
[2025-12-10T17:22:00Z] EVIDENCE: Console shows "No Access-Control-Allow-Origin header"
[2025-12-10T17:23:00Z] EVIDENCE: All /portal/* requests fail with net::ERR_FAILED
[2025-12-10T17:24:00Z] FIX: Added portal URLs to settings.py cors_origins (90d8a93)
[2025-12-10T17:25:00Z] BLOCKED: GCP deploy permissions - user needs to redeploy backend
[2025-12-10T17:26:00Z] NEXT: Deploy backend to Cloud Run to apply CORS fix

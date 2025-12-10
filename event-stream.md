# Event Stream
<!-- Max 25 lines, prune oldest when exceeded -->

[2025-12-10T17:20:00Z] DEBUG: MCP-driven magic link flow test via Chrome DevTools + Gmail
[2025-12-10T17:21:00Z] ROOT_CAUSE_1: CORS blocking - cors_origins only had localhost:3000
[2025-12-10T17:24:00Z] FIX: Added portal URLs to settings.py cors_origins (90d8a93)
[2025-12-10T18:20:00Z] DEPLOY: Cloud Run nikita-api-00035-9hk with CORS fix (gcp-transcribe-test)
[2025-12-10T18:25:00Z] ROOT_CAUSE_2: AttributeError - get_by_user vs get_by_user_id method names
[2025-12-10T18:26:00Z] FIX: portal.py method names corrected (a2bdc99)
[2025-12-10T18:30:00Z] DEPLOY: Cloud Run nikita-api-00036-hhv with method fix
[2025-12-10T18:32:00Z] ROOT_CAUSE_3: TypeError - float/Decimal division in boss progress calc
[2025-12-10T18:33:00Z] FIX: portal.py Decimal arithmetic (37e2b86)
[2025-12-10T18:35:00Z] DEPLOY: Cloud Run nikita-api-00037-tnl with Decimal fix
[2025-12-10T18:40:00Z] ROOT_CAUSE_4: toFixed() error - frontend expects numbers, API returns strings
[2025-12-10T18:41:00Z] EVIDENCE: Pydantic Decimal serializes to "50.00" string, JS needs 50.0 number
[2025-12-10T18:42:00Z] FIX: portal.py schemas Decimal→float for JSON compatibility (9a810bf)
[2025-12-10T18:45:00Z] DEPLOY: Cloud Run nikita-api-00038-6gz with float serialization
[2025-12-10T18:46:00Z] SUCCESS: Dashboard fully working - score 50, chapter 1, 91% progress
[2025-12-10T18:47:00Z] CLAUDE_MD: Added GCP deployment section (gcp-transcribe-test, not nikita-prod)

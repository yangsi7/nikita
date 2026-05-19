# Spec 050: Portal Fixes

**Status**: IMPLEMENTED | **Priority**: MEDIUM | **Source**: Deep Audit 2026-02-14

## Fixes Implemented

1. **FRONT-04**: Type alignment — `tone` → `emotional_tone`, `conversation_count` → `conversations_count`, nullability
2. **FRONT-07**: Error handling — explicit `ApiError` type + retry config on all 15 hooks
3. **FRONT-09**: Global 401 handler — redirect to `/login` on auth failures
4. **FRONT-10**: Request timeouts — 30s `AbortSignal.timeout()` on API client
5. **FRONT-02**: Admin role unification — check `user_metadata.role` OR `@nanoleq.com` email domain

## Files Changed
- `portal/src/lib/api/types.ts` — Type corrections
- `portal/src/lib/api/client.ts` — 401 handler + 30s timeout
- `portal/middleware.ts` — Dual admin role check
- `portal/src/hooks/*.ts` — 15 hooks with error types
- `portal/src/components/dashboard/conversation-card.tsx` — `tone` → `emotional_tone`
- `portal/src/components/dashboard/diary-entry.tsx` — `conversation_count` → `conversations_count`

## Verification
- `npx next build`: 0 TypeScript errors
- Backend: 3905 tests pass

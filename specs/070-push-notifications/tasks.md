# Tasks 070 — Push Notifications

## Story 1: Database Migration

### T1: Create push_subscriptions table
- [ ] Apply migration via Supabase MCP: CREATE TABLE, RLS, policy
- [ ] Verify table exists with `list_tables`
- AC: AC-1.1, AC-1.4

## Story 2: Backend Tests

### T2: Commit and verify existing tests
- [ ] Stage `tests/api/routes/test_push_subscribe.py`
- [ ] Run: `pytest tests/api/routes/test_push_subscribe.py tests/api/routes/test_push_lifecycle_integration.py -v`
- [ ] All 6 tests pass
- AC: AC-1.2, AC-1.3

## Story 3: Portal Integration

### T3: Mount PushPermissionBanner in dashboard
- [ ] Import and render `PushPermissionBanner` in `portal/src/app/dashboard/layout.tsx`
- [ ] Ensure service worker registration in `providers.tsx`
- [ ] Run: `cd portal && npm run build`
- [ ] Run: `cd portal && npm run lint`
- AC: AC-2.1, AC-2.2, AC-2.3, AC-2.4

### T4: Verify notification click behavior
- [ ] sw.js `notificationclick` handler focuses existing tab or opens dashboard
- [ ] Manual or E2E verification
- AC: AC-2.5

## Story 4: Edge Function

### T5: Implement web-push delivery in Edge Function
- [ ] Add `npm:web-push` import via Deno compat
- [ ] Implement VAPID JWT signing
- [ ] Implement payload encryption + POST to endpoint
- [ ] Handle 410 Gone → delete subscription from DB
- [ ] Handle missing subscriptions → return `{ sent: 0 }`
- [ ] Deploy via Supabase MCP `deploy_edge_function`
- AC: AC-3.1, AC-3.2, AC-3.3, AC-3.4

## Story 5: Game Triggers

### T6: Create push notification helper
- [ ] Create `nikita/notifications/push.py` with `send_push(user_id, title, body, url?, tag?)`
- [ ] Uses httpx to invoke Supabase Edge Function
- [ ] Catches all errors (logged, never raised)
- [ ] Tests: 4 unit tests (success, no subs, failure, error handling)
- AC: AC-4.5, AC-3.3

### T7: Wire message handler trigger
- [ ] After Nikita responds via Telegram, call `send_push`
- [ ] Test: mock `send_push`, verify called with message preview
- AC: AC-4.1

### T8: Wire decay processor trigger
- [ ] When score drops below 30%, call `send_push` with decay warning
- [ ] Test: mock `send_push`, verify called on low score
- AC: AC-4.2

### T9: Wire chapter/boss triggers
- [ ] Chapter advance → push notification
- [ ] Boss encounter ready → push notification
- [ ] Tests: 2 tests verifying push calls
- AC: AC-4.3, AC-4.4

## Story 6: Config & Docs

### T10: VAPID key setup
- [ ] Generate VAPID key pair
- [ ] Set `NEXT_PUBLIC_VAPID_PUBLIC_KEY` in Vercel
- [ ] Set `VAPID_PRIVATE_KEY`, `VAPID_PUBLIC_KEY`, `VAPID_SUBJECT` in Supabase secrets
- [ ] Document in `docs/deployment.md`
- AC: AC-3.4

## Summary

| Task | Story | ACs | Status |
|------|-------|-----|--------|
| T1 | DB Migration | AC-1.1, AC-1.4 | TODO |
| T2 | Backend Tests | AC-1.2, AC-1.3 | TODO |
| T3 | Portal Mount | AC-2.1-2.4 | TODO |
| T4 | Click Behavior | AC-2.5 | TODO |
| T5 | Edge Function | AC-3.1-3.4 | TODO |
| T6 | Push Helper | AC-4.5, AC-3.3 | TODO |
| T7 | Message Trigger | AC-4.1 | TODO |
| T8 | Decay Trigger | AC-4.2 | TODO |
| T9 | Chapter/Boss Trigger | AC-4.3, AC-4.4 | TODO |
| T10 | VAPID Setup | AC-3.4 | TODO |

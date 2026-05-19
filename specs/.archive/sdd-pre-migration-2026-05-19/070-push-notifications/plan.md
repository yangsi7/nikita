# Plan 070 — Push Notifications

## Implementation Order

### Story 1: Database Migration (AC-1.1, AC-1.4)

Create `push_subscriptions` table with RLS via Supabase MCP.

**Files**: Supabase migration only (MCP `apply_migration`)

**AC Verification**:
- Table exists with correct columns
- RLS enabled, policy restricts to own user_id
- CASCADE on user delete

### Story 2: Wire Existing Backend Tests (AC-1.2, AC-1.3)

The subscribe/unsubscribe endpoints already exist. Ensure untracked test file is committed and tests pass.

**Files**:
- `tests/api/routes/test_push_subscribe.py` (commit existing)
- Verify `tests/api/routes/test_push_lifecycle_integration.py` passes

**AC Verification**:
- All 6 tests pass (3 unit + 3 integration)

### Story 3: Portal Integration (AC-2.1, AC-2.2, AC-2.3, AC-2.4, AC-2.5)

Mount push permission banner in dashboard layout. Wire service worker registration.

**Files**:
- `portal/src/app/dashboard/layout.tsx` — Add PushPermissionBanner
- `portal/src/app/providers.tsx` — Ensure SW registration on mount
- `portal/public/sw.js` — Already complete

**AC Verification**:
- Portal builds without errors
- Banner renders on dashboard for new users
- Notification click navigates to dashboard

### Story 4: Edge Function — Web Push Delivery (AC-3.1, AC-3.2, AC-3.3, AC-3.4)

Implement actual web-push protocol in Supabase Edge Function using `web-push` npm package via Deno compatibility.

**Files**:
- `supabase/functions/push-notify/index.ts` — Implement VAPID + delivery

**AC Verification**:
- Function deploys successfully
- Sends to valid subscriptions
- Handles 410 Gone (expired) by deleting subscription
- Returns `{ sent: N, failed: M }`

### Story 5: Game Event Triggers (AC-4.1, AC-4.2, AC-4.3, AC-4.4, AC-4.5)

Wire game events to push notifications via Edge Function invocation.

**Files**:
- `nikita/platforms/telegram/message_handler.py` — Trigger push after Nikita response
- `nikita/engine/decay/processor.py` — Trigger push on low score
- `nikita/engine/chapters/boss.py` — Trigger push on chapter advance / boss ready
- `nikita/notifications/push.py` (NEW) — Helper to invoke Edge Function

**AC Verification**:
- Each trigger calls push helper
- Push failures don't raise exceptions (logged only)
- Tests verify trigger behavior with mocked push helper

### Story 6: VAPID Key Setup & Environment Config (AC-3.4)

Generate VAPID keys, configure in Vercel + Supabase.

**Files**:
- `docs/deployment.md` — Document VAPID setup
- Vercel env: `NEXT_PUBLIC_VAPID_PUBLIC_KEY`
- Supabase secrets: `VAPID_PRIVATE_KEY`, `VAPID_PUBLIC_KEY`, `VAPID_SUBJECT`

**AC Verification**:
- Keys configured in both environments
- Portal can subscribe using public key
- Edge function can sign using private key

## Test Strategy

| Layer | Count | Coverage |
|-------|-------|----------|
| Unit: subscription CRUD | 3 | AC-1.2, AC-1.3 |
| Integration: lifecycle | 3 | AC-1.2, AC-1.3 |
| Unit: push helper | 4 | AC-4.5, AC-3.3 |
| Unit: game triggers | 4 | AC-4.1-4.4 |
| Portal: build + lint | 1 | AC-2.* |
| **Total** | **15** | |

## Risks

1. **Deno web-push**: No native Deno library. Use `npm:web-push` via Deno compatibility layer.
2. **VAPID key management**: Keys must be consistent between portal (public) and edge function (private).
3. **Rate limiting**: Web Push APIs may rate-limit. Should be fine for per-user notifications.

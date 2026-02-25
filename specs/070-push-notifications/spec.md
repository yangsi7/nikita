# Spec 070 — Push Notifications

## Problem

Players miss messages and decay events because the portal has no push notification system. Nikita's responses, boss encounters, and decay warnings go unnoticed until the player opens the app.

## Solution

Web Push API integration with VAPID authentication, backed by a Supabase `push_subscriptions` table and Edge Function for delivery.

## Components

### 1. Database: `push_subscriptions` table

```sql
CREATE TABLE push_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    endpoint TEXT NOT NULL,
    p256dh TEXT NOT NULL,
    auth TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, endpoint)
);

-- RLS: users can only manage their own subscriptions
ALTER TABLE push_subscriptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage own subscriptions"
    ON push_subscriptions FOR ALL
    USING (auth.uid() = user_id);
```

### 2. Backend API (already scaffolded)

- `POST /api/v1/portal/push-subscribe` — Store subscription (upsert)
- `DELETE /api/v1/portal/push-subscribe` — Remove subscription

Both endpoints exist in `nikita/api/routes/portal.py:859-914`.

### 3. Service Worker (`portal/public/sw.js`)

Already implemented:
- Listens for `push` events, shows notification
- Handles `notificationclick` to focus/open dashboard
- Uses icon/badge assets

### 4. Push Permission Component (`portal/src/components/notifications/push-permission.tsx`)

Already implemented:
- Shows permission banner when notifications not yet granted
- Handles enable/dismiss flows
- Registers service worker and subscribes to push
- Stores subscription via backend API

### 5. Supabase Edge Function (`supabase/functions/push-notify/`)

Sends push notifications using Web Push protocol:
- Input: `{ user_id, title, body, url?, tag? }`
- Queries `push_subscriptions` for user
- Signs VAPID JWT, encrypts payload
- POSTs to each subscription endpoint
- Cleans up expired/invalid subscriptions (410 Gone)

### 6. Game Event Triggers

Wire push notifications to game events via `tasks.py` endpoints:

| Event | Title | Body | Tag |
|-------|-------|------|-----|
| Nikita message | "Nikita" | First 100 chars of message | `nikita-message` |
| Decay warning (score < 30%) | "Don't forget about me..." | "Your connection with Nikita is fading" | `decay-warning` |
| Chapter advance | "New chapter unlocked" | Chapter name | `chapter-advance` |
| Boss encounter ready | "Nikita wants to talk..." | "Something important is happening" | `boss-ready` |

### 7. Environment Variables

| Variable | Where | Purpose |
|----------|-------|---------|
| `NEXT_PUBLIC_VAPID_PUBLIC_KEY` | Vercel + Portal | Browser push subscribe |
| `VAPID_PRIVATE_KEY` | Supabase Edge Function secrets | Push signing |
| `VAPID_PUBLIC_KEY` | Supabase Edge Function secrets | Push signing |
| `VAPID_SUBJECT` | Supabase Edge Function secrets | `mailto:` contact |

## Acceptance Criteria

### AC-1: Subscription Management
- AC-1.1: `push_subscriptions` table exists with RLS
- AC-1.2: POST subscribe stores endpoint + keys (upsert on conflict)
- AC-1.3: DELETE unsubscribe removes subscription
- AC-1.4: Cascade delete when user is deleted

### AC-2: Browser Integration
- AC-2.1: Service worker registers on portal load
- AC-2.2: Permission banner shows for new users
- AC-2.3: Clicking "Enable" requests permission and subscribes
- AC-2.4: Dismissing banner persists to localStorage
- AC-2.5: Notification click focuses existing tab or opens dashboard

### AC-3: Push Delivery
- AC-3.1: Edge function sends push to all user subscriptions
- AC-3.2: Invalid subscriptions (410 Gone) are auto-cleaned
- AC-3.3: Missing subscriptions return `{ sent: 0 }` (no error)
- AC-3.4: VAPID signing uses correct keys

### AC-4: Game Integration
- AC-4.1: Telegram message handler triggers push after Nikita responds
- AC-4.2: Decay processor triggers push when score drops below 30%
- AC-4.3: Chapter advance triggers push notification
- AC-4.4: Boss encounter readiness triggers push notification
- AC-4.5: Push failures are logged but don't block game flow

## Out of Scope

- Native mobile push (iOS/Android)
- Push notification preferences per event type
- Push analytics (open rates, click-through)
- Batch push to multiple users (admin broadcast)

## Dependencies

- Web Push API (browser support)
- VAPID key pair (generate with `web-push generate-vapid-keys`)
- Supabase Edge Functions runtime (Deno)

## Existing Code

| File | Status | Notes |
|------|--------|-------|
| `portal/public/sw.js` | Draft | Complete, needs registration in layout |
| `portal/src/components/notifications/push-permission.tsx` | Draft | Complete, needs mounting in dashboard |
| `portal/src/app/providers.tsx` | Modified | Has SW registration code |
| `supabase/functions/push-notify/index.ts` | Stub | Interface defined, delivery not implemented |
| `nikita/api/routes/portal.py:859-914` | Committed | Subscribe/unsubscribe endpoints |
| `tests/api/routes/test_push_subscribe.py` | Untracked | 3 unit tests |
| `tests/api/routes/test_push_lifecycle_integration.py` | Committed | 3 integration tests |

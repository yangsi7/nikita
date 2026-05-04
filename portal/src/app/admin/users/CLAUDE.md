# portal/src/app/admin/users/ — User Management

## Purpose

Admin-only user management surface: paginated list of all users, drill-down to per-user detail with metric history, conversation counts, vice prefs, scheduled events, and "god mode" admin actions (force chapter advance, score override, game-status reset, etc.).

## Key Files

- `page.tsx` — list view (paginated user table; query params for filter/sort).
- `[id]/page.tsx` + `[id]/page-client.tsx` — per-user detail:
  - `useAdminUser(id)` hook (`@/hooks/use-admin-user`) for user data load.
  - `<UserDetail user={user} />` (`@/components/admin/user-detail`) — composite display: profile, metrics, chapter, game status, recent activity.
  - `<GodModePanel userId={id} />` (`@/components/admin/god-mode-panel`) — destructive admin actions; gated by separate confirmation.
  - Breadcrumb nav: Admin → Users → [phone OR `TG: ${telegram_id}` OR `id.slice(0,8)`] (`[id]/page-client.tsx:21-29`).

## Callers

- Admin nav `/admin/users` — direct entry.
- Deep-linked from `/admin/conversations/[id]` (per-conversation viewer) when triaging a specific user's flow.
- E2E tests — Playwright walks land here to assert admin god-mode actions take effect.

## Gotchas

- **Admin auth gate** — same as `prompts/`: enforce in middleware (`portal/middleware.ts` or `proxy.ts`). Do NOT rely on client-side `<AdminGuard>`.
- **3 user-row creation call-sites** in backend `nikita/api/routes/portal.py:126,477,513` — divergent init paths. If a user shows up in this list with missing `user_metrics` or `user_vice_preferences`, the bug is upstream in the backend creation drift (W4 audit 2026-05-05). Don't try to "fix it on the admin side".
- **God-mode destructiveness**: `GodModePanel` actions (force chapter, score override, game-status reset) bypass the normal scoring engine. Each action MUST emit an audit event to `event-stream` table for traceability. Verify the backend endpoint logs an audit row before declaring success in UI.
- **Breadcrumb fallback**: phone is preferred display; falls back to `TG: <telegram_id>` then `id.slice(0,8)`. If the user has neither phone nor telegram_id (unusual but possible for portal-only signups via Spec 216), the short ID is the only locator.
- **`useAdminUser`** caches via React Query — destructive god-mode actions MUST invalidate the query key after mutating, or the UI will show stale data until the user navigates away.

## Navigation

- Parent: [`portal/src/app/admin/`](../)
- User model: [`nikita/db/models/user.py`](../../../../../nikita/db/models/user.py) (`User`, `UserMetrics`, `UserVicePreference`)
- Game-state model: [`memory/game-mechanics.md`](../../../../../memory/game-mechanics.md)
- Auth-gate convention: [`portal/CLAUDE.md`](../../../../CLAUDE.md) §"Patterns" — Supabase Auth (SSR)

# Plan: Spec 063 — Portal Data Viz & Notifications (RETROACTIVE)

**Spec**: `specs/063-portal-data-viz-notifications/spec.md` | **Wave**: D | **Tasks**: 18 | **Effort**: ~12h
**Note**: This plan was generated retroactively after implementation (commit 63da5da).

---

## 1. Summary

This plan implements data visualization charts (engagement timeline, decay sparkline, vice radar), an in-app notification center, data export functionality, and actionable toasts. Frontend-heavy with chart components using Recharts and a client-side notification system driven by existing API data. One backend endpoint added for data export (`GET /portal/export/{type}`). Push notifications (US-5) deferred to future work.

---

## 2. Implementation Phases

### Phase 1: Engagement State Timeline (US-1)

**T1.1 — EngagementTimeline chart component**
- **Create**: `portal/src/components/charts/engagement-timeline.tsx`
- Recharts AreaChart with score data over time. XAxis (date), YAxis (0-100), rose gradient fill. Reference lines at y=75 (Boss threshold, cyan) and y=30 (Danger, red). Uses existing `portalApi.getScoreHistory()`. GlassCardWithHeader wrapper. Loading skeleton fallback.
- **AC**: US-1

### Phase 2: Decay Rate Visualization (US-2)

**T2.1 — DecaySparkline component**
- **Create**: `portal/src/components/charts/decay-sparkline.tsx`
- Compact card showing decay status. Grace period progress bar or active decay rate indicator. Color-coded urgency: cyan (safe), amber (warning <12h), red (decaying). Uses existing `portalApi.getDecayStatus()`. Progressbar with role="progressbar" for accessibility.
- **AC**: US-2

### Phase 3: Vice Intensity Radar Chart (US-3)

**T3.1 — ViceRadar chart component**
- **Create**: `portal/src/components/charts/vice-radar.tsx`
- Recharts RadarChart showing vice categories. PolarGrid, PolarAngleAxis (category names), PolarRadiusAxis (0-5). Rose fill with 20% opacity. Uses existing `portalApi.getVices()`. GlassCardWithHeader wrapper. Loading skeleton fallback.
- **AC**: US-3

### Phase 4: Notification Center (US-4)

**T4.1 — PortalNotification type**
- **Modify**: `portal/src/lib/api/types.ts`
- Add `PortalNotification` interface: id, type (chapter_advance | boss_encounter | decay_warning | engagement_shift), title, message, timestamp, read, actionHref.
- **AC**: US-4

**T4.2 — useNotifications hook**
- **Create**: `portal/src/hooks/use-notifications.ts`
- Client-side notification generation from existing API data (score history events, engagement transitions, decay status). Read state persisted in localStorage. Returns: notifications[], unreadCount, markAsRead(), markAllAsRead().
- **AC**: US-4

**T4.3 — NotificationCenter component**
- **Create**: `portal/src/components/notifications/notification-center.tsx`
- Popover trigger: Bell icon with unread count badge (rose-500). Popover content: header with "Mark all read" button, scrollable notification list. Each item shows type icon, title, message, relative timestamp. Unread items have rose left border. Items link to relevant page via actionHref.
- **AC**: US-4

**T4.4 — Wire NotificationCenter into sidebar header**
- **Modify**: `portal/src/components/layout/sidebar.tsx`
- Add NotificationCenter in sidebar header area for player variant.
- **AC**: US-4

### Phase 5: Browser Push Notifications (US-5) — DEFERRED

**T5.1 — Service Worker + push subscription**
- DEFERRED: Requires Supabase Edge Function for push event triggers, service worker registration, and browser permission flow. Tracked as follow-up item in master-todo.md.
- **AC**: US-5 (NOT MET — deferred)

### Phase 6: Data Export (US-6)

**T6.1 — Export utility**
- **Create**: `portal/src/lib/export.ts`
- `downloadExport(type, format, days)`: fetches from backend export endpoint, triggers browser file download via blob URL + anchor click pattern. Gets Supabase JWT for auth header.
- **AC**: US-6

**T6.2 — ExportButton component**
- **Create**: `portal/src/components/shared/export-button.tsx`
- Button with Download icon. Props: type, label, format (csv/json), days. Loading state during export. Success/error toasts via sonner. Accessible aria-label.
- **AC**: US-6

**T6.3 — Backend export endpoint**
- **Modify**: `nikita/api/routes/portal.py`
- Add `GET /portal/export/{type}` endpoint. Accepts format (csv/json) and days query params. Returns file response.
- **AC**: US-6

### Phase 7: Actionable Toasts (US-7)

**T7.1 — Verify sonner action support**
- Sonner toast library supports action prop natively. NotificationCenter items use Link for navigation (actionHref). Export buttons use toast.success/error with descriptions. No additional code needed.
- **AC**: US-7

### Phase 8: Verification

**T8.1 — Portal build verification**
- Run `npm run build` with 0 TypeScript errors.

**T8.2 — Backend test regression**
- Run `pytest tests/ -x -q` to verify no regressions.

---

## 3. Dependency Graph

```
T1.1, T2.1, T3.1 (independent chart components)
T4.1 ──→ T4.2 ──→ T4.3 ──→ T4.4
T6.1 ──→ T6.2
T6.3 (independent backend)
T5.1 (deferred)
T7.1 (audit only)
All ──→ T8.1 ──→ T8.2
```

**Parallelizable**: Charts (Phase 1-3), notifications (Phase 4), and export (Phase 6) are independent.

---

## 4. Files Summary

### Create (6)
| File | Task | Purpose |
|------|------|---------|
| `portal/src/components/charts/engagement-timeline.tsx` | T1.1 | Score timeline AreaChart |
| `portal/src/components/charts/decay-sparkline.tsx` | T2.1 | Decay rate indicator |
| `portal/src/components/charts/vice-radar.tsx` | T3.1 | Vice intensity RadarChart |
| `portal/src/hooks/use-notifications.ts` | T4.2 | Client-side notification generation |
| `portal/src/components/notifications/notification-center.tsx` | T4.3 | Bell icon + notification dropdown |
| `portal/src/lib/export.ts` | T6.1 | Browser file download utility |
| `portal/src/components/shared/export-button.tsx` | T6.2 | Export trigger button |

### Modify (3)
| File | Task | Change |
|------|------|--------|
| `portal/src/lib/api/types.ts` | T4.1 | Add PortalNotification type |
| `portal/src/components/layout/sidebar.tsx` | T4.4 | Add NotificationCenter |
| `nikita/api/routes/portal.py` | T6.3 | Add export endpoint |

---

## 5. Risk Mitigations

| Risk | Mitigation |
|------|------------|
| Recharts bundle size | Already installed for Spec 047. Tree-shaking keeps unused chart types out |
| Notification noise | Client-side generation from existing data — no separate API needed |
| localStorage unavailable | try/catch in getReadIds/saveReadIds — graceful fallback to empty set |
| Export timeout | AbortSignal.timeout(60_000) on fetch call |
| Push notifications complexity | Deferred to future spec — requires service worker + Edge Function |

---

## 6. Deferred Items

| Item | Reason | Tracking |
|------|--------|----------|
| US-5: Browser Push Notifications | Requires service worker, Supabase Edge Function, browser permission UX | `todos/master-todo.md` follow-up |

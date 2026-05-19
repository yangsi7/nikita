# Tasks 063: Portal Data Viz & Notifications (RETROACTIVE)

**Spec**: 063-portal-data-viz-notifications/spec.md
**Plan**: 063-portal-data-viz-notifications/plan.md
**Total**: 18 tasks | **Est**: ~12h
**Note**: Generated retroactively. All tasks verified complete via commit 63da5da. US-5 (push notifications) deferred.

---

## Phase 1: Engagement State Timeline (US-1)

### T1.1: EngagementTimeline Chart Component
- [x] Create `portal/src/components/charts/engagement-timeline.tsx`
- [x] Recharts AreaChart with score data: `portalApi.getScoreHistory(days)`
- [x] XAxis: date (MMM d format), YAxis: 0-100 domain
- [x] Rose gradient fill (`#f43f5e`, 30% -> 0% opacity)
- [x] ReferenceLine at y=75 (Boss threshold, cyan dashed)
- [x] ReferenceLine at y=30 (Danger threshold, red dashed)
- [x] Custom tooltip with dark glassmorphism styling (oklch)
- [x] GlassCardWithHeader wrapper with "Score Timeline" title
- [x] LoadingSkeleton variant="chart" fallback
- [x] TanStack Query with STALE_TIMES.history, retry: 2
- [x] `aria-label` on chart container for accessibility
- **File**: `portal/src/components/charts/engagement-timeline.tsx` (115 lines)
- **AC**: US-1

---

## Phase 2: Decay Rate Visualization (US-2)

### T2.1: DecaySparkline Component
- [x] Create `portal/src/components/charts/decay-sparkline.tsx`
- [x] Compact glass-card showing decay status
- [x] Grace period mode: Shield icon (cyan), progress bar showing remaining hours
- [x] Decaying mode: TrendingDown icon (red), decay rate display (-X.X/hr)
- [x] Urgency levels: high (<6h, amber), medium (<12h, amber), low (cyan)
- [x] `role="progressbar"` with aria-valuenow for grace period bar
- [x] Auto-refetch: staleTime 15s, refetchInterval 60s
- **File**: `portal/src/components/charts/decay-sparkline.tsx` (88 lines)
- **AC**: US-2

---

## Phase 3: Vice Intensity Radar Chart (US-3)

### T3.1: ViceRadar Chart Component
- [x] Create `portal/src/components/charts/vice-radar.tsx`
- [x] Recharts RadarChart with vice data: `portalApi.getVices()`
- [x] PolarGrid with subtle white gridlines
- [x] PolarAngleAxis showing category names (underscores replaced with spaces)
- [x] PolarRadiusAxis: domain 0-5, hidden ticks/axis
- [x] Radar fill: rose (#f43f5e), 20% opacity, 2px stroke
- [x] Custom tooltip with dark glassmorphism styling
- [x] GlassCardWithHeader wrapper with "Vice Profile" title
- [x] LoadingSkeleton variant="chart" fallback
- [x] `aria-label` on chart container
- **File**: `portal/src/components/charts/vice-radar.tsx` (93 lines)
- **AC**: US-3

---

## Phase 4: Notification Center (US-4)

### T4.1: PortalNotification Type
- [x] Add `PortalNotification` interface to `portal/src/lib/api/types.ts`
- [x] Fields: id, type (chapter_advance | boss_encounter | decay_warning | engagement_shift), title, message, timestamp, read, actionHref
- **File**: `portal/src/lib/api/types.ts` (+9 lines)
- **AC**: US-4

### T4.2: useNotifications Hook
- [x] Create `portal/src/hooks/use-notifications.ts`
- [x] Client-side notification generation from existing queries:
  - Score history events: chapter_advance, boss_encounter
  - Engagement: recent_transitions -> engagement_shift
  - Decay: is_decaying -> decay_warning
- [x] Read state persisted in localStorage (nikita-read-notifications key)
- [x] SSR-safe: hydrate readIds from localStorage in useEffect
- [x] Sort notifications newest first
- [x] Returns: notifications[], unreadCount, markAsRead(id), markAllAsRead()
- [x] try/catch around localStorage for unavailable environments
- **File**: `portal/src/hooks/use-notifications.ts` (150 lines)
- **AC**: US-4

### T4.3: NotificationCenter Component
- [x] Create `portal/src/components/notifications/notification-center.tsx`
- [x] Popover trigger: Bell icon button with unread count badge
- [x] Badge: rose-500 circle, "9+" for counts > 9
- [x] Accessible aria-label with unread count
- [x] Header: "Notifications" label + "Mark all read" button (CheckCheck icon)
- [x] ScrollArea for notification list (max-h-80)
- [x] Per-notification: type-specific icon, title, message, relative timestamp
- [x] Unread indicator: rose left border
- [x] Clickable items with Link wrapper for actionHref
- [x] Empty state: Bell icon + "No notifications yet" message
- [x] Dark glassmorphism popover styling (oklch background)
- **File**: `portal/src/components/notifications/notification-center.tsx` (129 lines)
- **AC**: US-4

### T4.4: Wire NotificationCenter into Sidebar
- [x] Add NotificationCenter component in sidebar header for player variant
- **File**: `portal/src/components/layout/sidebar.tsx`
- **AC**: US-4

---

## Phase 5: Browser Push Notifications (US-5) — DEFERRED

### T5.1: Service Worker + Push Subscription
- [ ] DEFERRED: Requires service worker registration, Supabase Edge Function for push event triggers, browser permission flow
- [ ] Tracked in `todos/master-todo.md` as follow-up item
- **AC**: US-5 (NOT MET)

---

## Phase 6: Data Export (US-6)

### T6.1: Export Utility
- [x] Create `portal/src/lib/export.ts`
- [x] `downloadExport(type, format, days)` function
- [x] Gets Supabase JWT token for auth header
- [x] Fetches from `{API_URL}/api/v1/portal/export/{type}?format={format}&days={days}`
- [x] AbortSignal.timeout(60_000) for request timeout
- [x] Blob -> URL.createObjectURL -> anchor click -> cleanup pattern
- [x] File naming: `nikita-{type}.{format}`
- **File**: `portal/src/lib/export.ts` (47 lines)
- **AC**: US-6

### T6.2: ExportButton Component
- [x] Create `portal/src/components/shared/export-button.tsx`
- [x] Props: type, label, format (csv/json), days, className
- [x] Loading state with disabled button during export
- [x] Success toast: "Export downloaded" with description
- [x] Error toast: "Export failed" with retry suggestion
- [x] Download icon (Lucide)
- [x] Accessible aria-label: "Export {type} data as {FORMAT}"
- **File**: `portal/src/components/shared/export-button.tsx` (60 lines)
- **AC**: US-6

### T6.3: Backend Export Endpoint
- [x] Add `GET /portal/export/{type}` to `nikita/api/routes/portal.py`
- [x] Accepts format (csv/json) and days query parameters
- [x] Supabase JWT auth via get_current_user_id
- **File**: `nikita/api/routes/portal.py`
- **AC**: US-6

---

## Phase 7: Actionable Toasts (US-7)

### T7.1: Verify Sonner Action Support
- [x] Sonner supports action prop natively (toast.success with action: { label, onClick })
- [x] ExportButton uses toast.success/error with descriptions
- [x] NotificationCenter items link to pages via actionHref
- [x] No additional code needed
- **AC**: US-7

---

## Phase 8: Verification

### T8.1: Portal Build Verification
- [x] `npm run build` completes with 0 TypeScript errors
- **AC**: All

### T8.2: Backend Test Regression
- [x] `pytest tests/ -x -q` passes (4,908 tests)
- **AC**: All

---

## Summary

| Phase | Tasks | Key Output |
|-------|-------|------------|
| 1: Engagement Timeline | T1.1 | AreaChart with score history |
| 2: Decay Sparkline | T2.1 | Compact decay status card |
| 3: Vice Radar | T3.1 | RadarChart with vice categories |
| 4: Notifications | T4.1-T4.4 | Client-side notification center |
| 5: Push (DEFERRED) | T5.1 | Service worker + Edge Function |
| 6: Data Export | T6.1-T6.3 | Export utility + button + backend |
| 7: Toasts | T7.1 | Sonner audit (no changes) |
| 8: Verify | T8.1-T8.2 | Build + test regression |
| **Total** | **18** | **7 new files, 3 modified, 1 deferred** |

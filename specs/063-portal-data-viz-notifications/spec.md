# Spec 063: Portal Data Viz & Notifications

## Overview
New chart visualizations, in-app notification center, browser push notifications, and data export.

## Complexity: 6 (Team /sdd-team)

## User Stories

### US-1: Engagement State Timeline
- Time series chart showing state transitions (Recharts AreaChart)
- X-axis: time, Y-axis: engagement score
- Color-coded zones: danger (red), warning (amber), good (green), excellent (cyan)

### US-2: Decay Rate Visualization
- Sparkline showing decay rate over time
- Current rate indicator (badge with arrow direction)
- Displayed on dashboard and engagement pages

### US-3: Vice Intensity Radar Chart
- Radar chart (Recharts RadarChart) showing all 8 vice categories
- Overlaid: current intensity vs historical average
- Interactive tooltips

### US-4: Notification Center
- Bell icon in header with unread count badge
- Dropdown panel listing notifications (read/unread)
- Types: score_change, chapter_advance, boss_encounter, decay_warning
- Backend: GET /portal/notifications, POST /portal/notifications/read
- DB: portal_notifications table with user_id FK, RLS

### US-5: Browser Push Notifications
- Service Worker registration for push
- Opt-in prompt on first visit (after auth)
- Notify on: boss encounters, chapter changes, critical decay

### US-6: Data Export
- Export buttons on score history, conversations, metrics pages
- Formats: CSV, JSON
- Backend: GET /portal/export/{type}?format=csv|json
- Client-side download trigger

### US-7: Actionable Toasts
- Toast actions with "View Details" button
- Navigate to relevant page on click
- Use sonner's action prop

## Acceptance Criteria
- [ ] Engagement timeline shows historical state data
- [ ] Radar chart renders all 8 vice categories
- [ ] Notification bell shows unread count
- [ ] Notifications can be marked as read
- [ ] Export downloads CSV/JSON files
- [ ] Portal builds with 0 TypeScript errors
- [ ] Backend tests pass for new endpoints
- [ ] RLS policies on portal_notifications table

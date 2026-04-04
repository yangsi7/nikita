# Phase 14: Portal Settings & Cross-cutting

## Scope

Settings page interactions with real API calls, mobile viewport testing, console error sweep, and export verification.

Portal URL: `https://portal-phi-orcin.vercel.app`

## Prerequisites

- Authenticated player session
- Settings page functional (use-settings hook loads data)

## Scenarios Covered

**Settings & Cross-cutting (S-PS)**: S-PS-001–S-PS-025

---

## Section A: Settings — Timezone

### Steps

1. Navigate to `/dashboard/settings`
2. Wait 3s for data load
3. Verify: Settings page renders with "Settings" heading
4. Locate "Timezone" select under "Account" card
5. Note current timezone value
6. Change timezone to "Europe/Zurich" (or another value different from current)
7. Wait 3s for API call

### Verification

- [ ] PUT request to `/portal/settings` fired (or equivalent API endpoint)
- [ ] Toast notification "Settings saved" appears (via sonner)
- [ ] Timezone select shows updated value
- [ ] Refresh page → timezone persists

### DB Cross-check
```sql
SELECT timezone FROM user_profiles
WHERE id = (SELECT id FROM auth.users WHERE email = 'simon.yang.ch@gmail.com');
```
**Verify**: `timezone` matches the selected value.

---

## Section B: Settings — Notifications

### Steps

1. On `/dashboard/settings`, find "Notifications" card
2. Locate "Push notifications" toggle (Switch component)
3. Note current state (checked/unchecked)
4. Toggle the switch
5. Wait 3s

### Verification

- [ ] PUT request to `/portal/settings` fired
- [ ] Switch state changes visually
- [ ] No error toast

### DB Cross-check
```sql
SELECT notifications_enabled FROM user_profiles
WHERE id = (SELECT id FROM auth.users WHERE email = 'simon.yang.ch@gmail.com');
```
**Verify**: `notifications_enabled` matches toggled state.

---

## Section C: Settings — Link Telegram

### Steps

1. On `/dashboard/settings`, find "Telegram" card
2. If Telegram already linked: verify badge shows "Linked" status, skip to Section D
3. If not linked: click "Link Telegram" button
4. Wait 3s

### Verification

- [ ] 6-character alphanumeric code appears
- [ ] Code is displayed clearly for user to copy
- [ ] Code format: `/^[A-Za-z0-9]{6}$/`
- [ ] "Link Telegram" button state changes (disabled or shows "Pending")

---

## Section D: Settings — Delete Account

### D1: Cancel Path

1. On `/dashboard/settings`, find danger zone / delete section
2. Click "Delete Account" button (Trash2 icon)
3. Wait for confirmation dialog to appear
4. Verify: Dialog asks for confirmation with clear warning text
5. Click "Cancel"
6. Wait 2s

**Verification**:
- [ ] Dialog closes
- [ ] No changes to account state
- [ ] Still on `/dashboard/settings`

### DB Cross-check (no change)
```sql
SELECT id FROM auth.users WHERE email = 'simon.yang.ch@gmail.com';
```
**Verify**: User still exists.

### D2: Confirm Path

> **CAUTION**: This will delete the test account. Only run at end of simulation or when re-setup is acceptable.

1. Click "Delete Account" again
2. Confirmation dialog appears
3. Click "Delete Everything" (or equivalent confirm button)
4. Wait 5s

**Verification**:
- [ ] Redirected to `/login`
- [ ] Navigating to `/dashboard` redirects to `/login` (session destroyed)

### DB Cross-check (deleted)
```sql
SELECT id FROM auth.users WHERE email = 'simon.yang.ch@gmail.com';
```
**Verify**: No rows returned (user deleted from auth.users).

```sql
SELECT id FROM users WHERE email = 'simon.yang.ch@gmail.com';
```
**Verify**: No rows returned (cascade delete or manual cleanup).

> **After delete**: Re-run Phase 00 (Prerequisites) if continuing simulation.

---

## Section E: Mobile Viewport (375px)

### Steps

1. Set browser viewport to 375px width (mobile)
   - Use browser agent resize or Chrome DevTools device emulation
2. Navigate to `/dashboard`

### Verification

- [ ] Bottom navigation bar visible (data-testid: `nav-mobile`)
- [ ] Sidebar is hidden (collapsed)
- [ ] Sidebar trigger (hamburger) works: click → sidebar slides in
- [ ] Dashboard content is not horizontally scrollable (no overflow)
- [ ] Score ring and mood orb stack vertically

3. Navigate to `/dashboard/conversations`

### Verification

- [ ] Conversation cards stack vertically
- [ ] Tab bar is scrollable or wraps properly
- [ ] Bottom nav still visible

4. Navigate to `/admin` (if admin role)

### Verification

- [ ] KPI cards stack into grid (2 columns or 1 column)
- [ ] Admin navigation accessible via sidebar trigger

5. Reset viewport to desktop width after testing.

---

## Section F: Console Error Sweep

### Steps

For each of the following routes, navigate and check for console errors:

**Player routes**:
1. `/dashboard`
2. `/dashboard/engagement`
3. `/dashboard/nikita`
4. `/dashboard/nikita/day`
5. `/dashboard/nikita/mind`
6. `/dashboard/nikita/stories`
7. `/dashboard/nikita/circle`
8. `/dashboard/vices`
9. `/dashboard/conversations`
10. `/dashboard/insights`
11. `/dashboard/diary`
12. `/dashboard/settings`

**Admin routes**:
13. `/admin`
14. `/admin/users`
15. `/admin/pipeline`
16. `/admin/text`
17. `/admin/voice`
18. `/admin/jobs`
19. `/admin/prompts`

**Public routes**:
20. `/`
21. `/login`

### Per-route Process

1. Navigate to route
2. Wait 3s for full load
3. Read console messages (filter for errors):
   ```
   mcp__claude-in-chrome__read_console_messages(pattern="error|Error|ERR")
   ```
4. Log any errors found

### Verification

- [ ] Zero console errors across all routes (ideal)
- [ ] Any console errors logged as findings:
  - React hydration mismatches → **MEDIUM**
  - Unhandled promise rejections → **HIGH**
  - Network 4xx/5xx errors → **HIGH**
  - Missing resource warnings → **LOW**
  - Development-only warnings → **OBSERVATION**

---

## Section G: Export (CSV Download)

### Steps

1. Navigate to a page with export functionality (e.g., `/admin/users` or `/dashboard/conversations`)
2. Locate "Download CSV" or export button
3. Click the export button
4. Wait 5s

### Verification

- [ ] Download initiated (browser download prompt or file saved)
- [ ] File is valid CSV (if accessible, check first few lines)
- [ ] No error toast after clicking export

---

## Portal Accuracy Recording

```xml
<portal_check phase="14-settings-cross">
  <route path="/dashboard/settings">
    <field name="timezone_change" api_fired="true|false" persisted="true|false"/>
    <field name="notification_toggle" api_fired="true|false" persisted="true|false"/>
    <field name="telegram_link_code" format_valid="true|false"/>
    <field name="delete_cancel_no_change" value="true|false"/>
    <field name="delete_confirm_redirect" value="true|false"/>
  </route>
  <section name="mobile-375px">
    <field name="bottom_nav_visible" value="true|false"/>
    <field name="sidebar_trigger_works" value="true|false"/>
    <field name="no_horizontal_overflow" value="true|false"/>
  </section>
  <section name="console-errors">
    <field name="total_routes_checked" value="21"/>
    <field name="routes_with_errors" value="..."/>
    <field name="error_details" value="[...]"/>
  </section>
  <section name="export">
    <field name="csv_download_initiated" value="true|false"/>
  </section>
</portal_check>
```

---

## Decision Gate

- Settings mutations persist → PASS
- Delete account works end-to-end → PASS (if tested)
- Mobile nav functional → PASS
- Console errors = 0 → PASS
- Console errors > 0 but no HIGH/CRITICAL → **MEDIUM findings**, continue
- Any CRITICAL console error (security, data leak) → **CRITICAL finding, stop**
- Export functional → PASS

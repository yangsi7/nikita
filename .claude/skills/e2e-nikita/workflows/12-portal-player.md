# Phase 12: Portal Player Dashboard

## Scope

All 13 player dashboard routes. For each route: navigate, verify rendering, check data accuracy against DB.

Portal URL: `https://portal-phi-orcin.vercel.app`

## Prerequisites

- Authenticated player session (from Phase 11 Section A)
- Test user has gameplay data (conversations, scores, engagement, vices)
- If running standalone: SQL-setup user to Chapter 3+ with rich data

### Data Setup (if needed)
```sql
-- Ensure test user has conversations, score_history, engagement, and vices
SELECT COUNT(*) as convs FROM conversations WHERE user_id = '<USER_ID>';
SELECT COUNT(*) as scores FROM score_history WHERE user_id = '<USER_ID>';
SELECT state FROM engagement_state WHERE user_id = '<USER_ID>';
SELECT COUNT(*) as vices FROM user_vice_preferences WHERE user_id = '<USER_ID>';
```

## Scenarios Covered

**Player Dashboard (S-PP)**: S-PP-001–S-PP-040

---

## Route: /dashboard

### Steps

1. Navigate to `/dashboard`
2. Wait 3s for data load

### Verification

- [ ] RelationshipHero card visible (data-testid: `card-score-ring`)
- [ ] ScoreRing SVG renders (data-testid: `chart-score-ring`)
- [ ] MoodOrb card visible (data-testid: `card-mood-orb`)
- [ ] Score value displayed matches DB
- [ ] Chapter name displayed (e.g., "Curiosity", "Intrigue")

### Empty State (if no interactions)
- [ ] DashboardEmptyState visible (data-testid: `dashboard-empty-state`) when no conversations exist

### DB Cross-check
```sql
SELECT u.relationship_score, u.chapter, u.game_status,
       um.intimacy, um.passion, um.trust, um.secureness
FROM users u
JOIN user_metrics um ON um.user_id = u.id
WHERE u.email = 'simon.yang.ch@gmail.com';
```
**Verify**: Displayed score matches `relationship_score`, chapter name matches `chapter`.

---

## Route: /dashboard/engagement

### Steps

1. Navigate to `/dashboard/engagement`
2. Wait 3s for data load

### Verification

- [ ] EngagementPulse card visible (data-testid: `card-engagement-chart`)
- [ ] Current engagement state label displayed
- [ ] If decay warning applies: DecayWarning component visible
- [ ] Transitions timeline shows state change history (if any)

### DB Cross-check
```sql
SELECT state, multiplier, messages_last_hour, last_message_at, calibration_score
FROM engagement_state
WHERE user_id = '<USER_ID>';
```
**Verify**: Displayed state matches `state` column.

---

## Route: /dashboard/nikita

### Steps

1. Navigate to `/dashboard/nikita`
2. Wait 3s for data load

### Verification

- [ ] MoodOrb visible
- [ ] "Today's Events" section (or empty state if none today)
- [ ] "What's on Her Mind" section
- [ ] Nav cards to sub-pages: Day, Mind, Stories, Circle

---

## Route: /dashboard/nikita/day

### Prerequisites
```sql
SELECT COUNT(*) FROM life_events WHERE user_id = '<USER_ID>';
```

### Steps

1. Navigate to `/dashboard/nikita/day`
2. Wait 3s for data load

### Verification

- [ ] Date navigation buttons visible (prev/next day)
- [ ] Events list renders for current date (or empty state)
- [ ] Click prev day button → date changes, events update
- [ ] Date displayed matches the navigated date

---

## Route: /dashboard/nikita/mind

### Steps

1. Navigate to `/dashboard/nikita/mind`
2. Wait 3s for data load

### Verification

- [ ] Thoughts list renders (or empty state)
- [ ] "Load More" button visible if more than initial batch
- [ ] Filter select present (if applicable)
- [ ] Click "Load More" → additional thoughts appended

---

## Route: /dashboard/nikita/stories

### Steps

1. Navigate to `/dashboard/nikita/stories`
2. Wait 3s for data load

### Verification

- [ ] Arc cards render (or empty state)
- [ ] "Show resolved" toggle visible
- [ ] Toggle on → resolved arcs appear
- [ ] Toggle off → resolved arcs hidden

---

## Route: /dashboard/nikita/circle

### Steps

1. Navigate to `/dashboard/nikita/circle`
2. Wait 3s for data load

### Verification

- [ ] Friend gallery renders (or empty state)
- [ ] Count displayed matches number of friend entries
- [ ] Each friend card has name and relationship info

---

## Route: /dashboard/vices

### Steps

1. Navigate to `/dashboard/vices`
2. Wait 3s for data load

### Verification

- [ ] Discovered vices display with category labels (data-testid: `card-vice-{category}`)
- [ ] Undiscovered vices show as locked cards
- [ ] Vice intensity level visible for each discovered vice
- [ ] No sensitive vices shown beyond chapter-appropriate caps

### DB Cross-check
```sql
SELECT category, intensity_level, discovered_at
FROM user_vice_preferences
WHERE user_id = '<USER_ID>'
ORDER BY intensity_level DESC;
```
**Verify**: Each displayed vice matches a DB row; intensity values match.

---

## Route: /dashboard/conversations

### Steps

1. Navigate to `/dashboard/conversations`
2. Wait 3s for data load

### Verification

- [ ] Tabs visible: All, Text, Voice, Boss
- [ ] Default tab (All) shows conversation cards
- [ ] Click "Text" tab → filters to text conversations only
- [ ] Click "Voice" tab → filters to voice conversations only
- [ ] Click "Boss" tab → filters to boss encounters only
- [ ] Pagination present if > page size
- [ ] Click a conversation card → navigates to `/dashboard/conversations/[id]`

### DB Cross-check
```sql
SELECT id, type, status, score_delta, created_at
FROM conversations
WHERE user_id = '<USER_ID>'
ORDER BY created_at DESC LIMIT 10;
```
**Verify**: Conversation count in tab matches DB count per type.

---

## Route: /dashboard/conversations/[id]

### Prerequisites

Note the conversation ID from the previous route's card click.

### Steps

1. Navigate to `/dashboard/conversations/<ID>` (from card click)
2. Wait 3s for data load

### Verification

- [ ] Transcript renders with message bubbles
- [ ] User messages are right-aligned
- [ ] Nikita messages are left-aligned
- [ ] Score delta shown (if conversation is processed)
- [ ] Timestamp displayed per message

---

## Route: /dashboard/insights

### Steps

1. Navigate to `/dashboard/insights`
2. Wait 3s for data load

### Verification

- [ ] ScoreDetailChart SVG renders (breakdown of intimacy, passion, trust, secureness)
- [ ] ThreadCards visible (insight summaries)
- [ ] Score breakdown matches metric values from DB

### DB Cross-check
```sql
SELECT intimacy, passion, trust, secureness
FROM user_metrics
WHERE user_id = '<USER_ID>';
```
**Verify**: Chart values reflect metric proportions.

---

## Route: /dashboard/diary

### Steps

1. Navigate to `/dashboard/diary`
2. Wait 3s for data load

### Verification

- [ ] DiaryEntry cards render (data-testid: `card-diary-{id}`)
- [ ] Each entry has date and emotional tone indicator
- [ ] Entries ordered by date (most recent first)
- [ ] Empty state shown if no diary entries exist

---

## Portal Accuracy Recording

```xml
<portal_check phase="12-player-dashboard">
  <route path="/dashboard">
    <field name="score" db="..." portal="..." match="true|false"/>
    <field name="chapter" db="..." portal="..." match="true|false"/>
    <field name="mood_orb" visible="true|false"/>
    <field name="empty_state" visible="true|false" note="if no interactions"/>
  </route>
  <route path="/dashboard/engagement">
    <field name="state" db="..." portal="..." match="true|false"/>
    <field name="decay_warning" visible="true|false"/>
  </route>
  <route path="/dashboard/vices">
    <field name="vice_count" db="..." portal="..." match="true|false"/>
    <field name="categories" db="[...]" portal="[...]" match="true|false"/>
  </route>
  <route path="/dashboard/conversations">
    <field name="total_count" db="..." portal="..." match="true|false"/>
    <field name="text_count" db="..." portal="..." match="true|false"/>
    <field name="voice_count" db="..." portal="..." match="true|false"/>
  </route>
  <route path="/dashboard/insights">
    <field name="intimacy" db="..." portal="..." match="true|false"/>
    <field name="passion" db="..." portal="..." match="true|false"/>
    <field name="trust" db="..." portal="..." match="true|false"/>
    <field name="secureness" db="..." portal="..." match="true|false"/>
  </route>
  <!-- remaining routes -->
</portal_check>
```

---

## Decision Gate

- All 13 routes render without error → **continue to Phase 13**
- Data accuracy ≥ 80% (matches DB) → PASS
- Any route returns 500 or blank → **HIGH finding**
- Data mismatch → **MEDIUM finding** (log in findings, continue)
- Missing components (empty state when data exists) → **HIGH finding**

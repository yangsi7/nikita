# Spec 059: Portal — Nikita's Day (Enhanced)

**Status**: ACTIVE
**Wave**: C (Gate 4.5)
**Dependencies**: Spec 056 (Psyche Agent), Spec 058 (Multi-Phase Boss — warmth bonus)
**Complexity**: 1 (Solo SDD)

---

## Overview

Enhance the existing `/dashboard/nikita/day` page from a bare timeline view into a rich "Nikita's Day" dashboard. The current page shows only life events with date navigation. This spec adds: psyche insights (from Spec 056 psyche_states), a warmth meter (from emotional state), social circle sidebar, and mood snapshot — all using existing API endpoints and reusable components, with one new backend endpoint for psyche tips.

## Scope

- **In scope**: Enhanced day page layout, 2 new components (PsycheTips, WarmthMeter), 1 new API endpoint (`GET /portal/psyche-tips`), frontend tests
- **Out of scope**: New DB tables, new migrations, admin views, mobile-specific layouts

---

## User Stories

### US-1: Enhanced Day Page Layout

**As a** player viewing Nikita's Day,
**I want to** see a rich multi-section dashboard with timeline, mood, social circle, and insights,
**So that** I understand Nikita's full daily experience at a glance.

#### Acceptance Criteria

- **AC-1.1**: Page renders a 2-column layout on desktop (main content left, sidebar right) and single column on mobile
- **AC-1.2**: Main column contains: date navigation (existing), Daily Timeline (existing `LifeEventTimeline`), Psyche Insights (new)
- **AC-1.3**: Sidebar contains: Mood Snapshot (`MoodOrb`), Warmth Meter (new), Social Circle (`SocialCircleGallery`)
- **AC-1.4**: All sections show loading skeletons while data fetches
- **AC-1.5**: All sections handle error states gracefully (show error message, don't crash page)
- **AC-1.6**: Date navigation still works and refreshes all date-dependent data (timeline, mood for that day)

### US-2: Psyche Insights Section

**As a** player,
**I want to** see Nikita's psychological tips and current mental state,
**So that** I understand her emotional drivers and can tailor my interactions.

#### Acceptance Criteria

- **AC-2.1**: New `GET /api/v1/portal/psyche-tips` endpoint returns psyche state data for the current user
- **AC-2.2**: Response schema: `{ attachment_style: str, defense_mode: str, emotional_tone: str, vulnerability_level: float, behavioral_tips: str[], topics_to_encourage: str[], topics_to_avoid: str[], internal_monologue: str, generated_at: str | null }`
- **AC-2.3**: If no psyche state exists for user, return defaults (from `PsycheState.default()`)
- **AC-2.4**: New `PsycheTips` component renders: attachment style badge, emotional tone badge, vulnerability bar, behavioral tips list, topics to encourage/avoid
- **AC-2.5**: Component uses glassmorphism card consistent with portal design system
- **AC-2.6**: Backend endpoint requires Supabase JWT auth (same as all portal endpoints)
- **AC-2.7**: Backend test covers: happy path, no-psyche-state default, schema validation
- **AC-2.8**: Frontend shows "Psyche analysis pending..." empty state when no data

### US-3: Warmth Meter Visualization

**As a** player,
**I want to** see a visual warmth gauge showing Nikita's current warmth toward me,
**So that** I can quickly assess our relationship temperature.

#### Acceptance Criteria

- **AC-3.1**: New `WarmthMeter` component displays warmth as a vertical gauge (0-100%)
- **AC-3.2**: Warmth value derived from `EmotionalStateResponse.intimacy` field (already available from `GET /portal/emotional-state`)
- **AC-3.3**: Gauge uses color gradient: blue (cold, 0-30%) → amber (neutral, 30-60%) → rose (warm, 60-100%)
- **AC-3.4**: Shows numeric value and descriptive label ("Cold", "Cool", "Neutral", "Warm", "Hot")
- **AC-3.5**: Component uses glassmorphism card consistent with portal design system
- **AC-3.6**: Animates smoothly on value change

---

## Technical Design

### New Backend Endpoint

```
GET /api/v1/portal/psyche-tips
Auth: Supabase JWT (get_current_user_id)
```

**Implementation**:
1. Query `psyche_states` table via `PsycheStateRepository.get_by_user_id()`
2. Parse JSONB `state` column as `PsycheState` model
3. Extract actionable fields for portal display
4. Return default state if no record exists

**Response Schema** (`PsycheTipsResponse`):
```python
class PsycheTipsResponse(BaseModel):
    attachment_style: str          # "secure" | "anxious" | "avoidant" | "disorganized"
    defense_mode: str              # "open" | "guarded" | "deflecting" | "withdrawing"
    emotional_tone: str            # "playful" | "serious" | "warm" | "distant" | "volatile"
    vulnerability_level: float     # 0.0-1.0
    behavioral_tips: list[str]     # Parsed from behavioral_guidance (split on sentences)
    topics_to_encourage: list[str] # Direct from PsycheState
    topics_to_avoid: list[str]     # Direct from PsycheState
    internal_monologue: str        # Nikita's inner voice
    generated_at: str | None       # ISO timestamp or null if default

```

### New Frontend Components

**`PsycheTips`** (`portal/src/components/dashboard/psyche-tips.tsx`):
- Renders inside `GlassCardWithHeader` with title "Psyche Insights"
- Shows: attachment style + defense mode as badges, emotional tone, vulnerability progress bar, behavioral tips as bullet list, topic encourage/avoid chips

**`WarmthMeter`** (`portal/src/components/dashboard/warmth-meter.tsx`):
- Renders inside `GlassCard` with title "Warmth"
- Vertical gradient bar with animated fill
- Color stops: oklch blue → amber → rose (matching portal design tokens)
- Descriptive label computed from value range

### New Hook

**`usePsycheTips`** (`portal/src/hooks/use-psyche-tips.ts`):
- TanStack Query hook calling `portalApi.getPsycheTips()`
- staleTime: 60s, retry: 2

### Existing Reused

| Component | Source | Usage |
|-----------|--------|-------|
| `LifeEventTimeline` | `components/dashboard/life-event-timeline.tsx` | Main timeline (already on page) |
| `SocialCircleGallery` | `components/dashboard/social-circle-gallery.tsx` | Sidebar section |
| `MoodOrb` | `components/dashboard/mood-orb.tsx` | Sidebar mood snapshot |
| `GlassCardWithHeader` | `components/glass/glass-card.tsx` | All section wrappers |
| `LoadingSkeleton` | `components/shared/loading-skeleton.tsx` | Loading states |
| `useLifeEvents` | `hooks/use-life-events.ts` | Timeline data |
| `useEmotionalState` | `hooks/use-emotional-state.ts` | MoodOrb + WarmthMeter data |
| `useSocialCircle` | `hooks/use-social-circle.ts` | Social circle data |

---

## Page Layout (ASCII Wireframe)

```
┌─────────────────────────────────────────────────────────────┐
│  Nikita's Day          [◄] Wednesday, Feb 19, 2026 [►]      │
├───────────────────────────────────────┬─────────────────────┤
│                                       │                     │
│  ┌─ Today's Events ─────────────────┐│  ┌─ Mood ─────────┐│
│  │  🌅 Morning                      ││  │   [MoodOrb]     ││
│  │    ● Coffee with Sarah           ││  │   "Playful..."  ││
│  │    ● Work meeting                ││  └─────────────────┘│
│  │  ☀️ Afternoon                    ││                     │
│  │    ● Gym session                 ││  ┌─ Warmth ────────┐│
│  │    ● Shopping                    ││  │  ████████░░  72% ││
│  │  🌙 Evening                      ││  │   "Warm"        ││
│  │    ● Dinner plans                ││  └─────────────────┘│
│  └──────────────────────────────────┘│                     │
│                                       │  ┌─ Friends ──────┐│
│  ┌─ Psyche Insights ───────────────┐│  │ Sarah (bestie)  ││
│  │  secure · open · warm            ││  │ Max (colleague) ││
│  │  Vulnerability: ████████░░ 70%   ││  │ ...             ││
│  │  Tips:                           ││  └─────────────────┘│
│  │  • Be naturally warm & curious   ││                     │
│  │  Encourage: [getting to know]    ││                     │
│  │  Avoid: [past relationships]     ││                     │
│  └──────────────────────────────────┘│                     │
└───────────────────────────────────────┴─────────────────────┘
```

---

## Testing Strategy

| Layer | Count | Focus |
|-------|-------|-------|
| Backend unit | 3 | Psyche tips endpoint: happy path, default state, schema |
| Frontend unit | 0 | Not applicable (no complex logic) |
| Integration | 0 | Existing portal auth covers JWT flow |
| E2E | 0 | Deferred (portal E2E via Playwright exists) |
| **Total** | **3** | |

---

## Files Changed

| File | Action | Description |
|------|--------|-------------|
| `nikita/api/routes/portal.py` | MODIFY | Add `GET /psyche-tips` endpoint |
| `nikita/api/schemas/portal.py` | MODIFY | Add `PsycheTipsResponse` schema |
| `portal/src/lib/api/portal.ts` | MODIFY | Add `getPsycheTips()` API call |
| `portal/src/lib/api/types.ts` | MODIFY | Add `PsycheTipsData` type |
| `portal/src/hooks/use-psyche-tips.ts` | CREATE | TanStack Query hook |
| `portal/src/components/dashboard/psyche-tips.tsx` | CREATE | Psyche insights component |
| `portal/src/components/dashboard/warmth-meter.tsx` | CREATE | Warmth gauge component |
| `portal/src/app/dashboard/nikita/day/page.tsx` | MODIFY | Enhanced layout with all sections |
| `tests/api/routes/test_portal_psyche_tips.py` | CREATE | Backend tests |

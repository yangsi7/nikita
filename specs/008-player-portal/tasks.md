# Implementation Tasks: 008-Player-Portal

**Generated**: 2025-11-29
**From**: plan.md (9 high-level tasks)
**Priority**: P3 (Nice-to-Have)
**Total Tasks**: 42 granular tasks across 10 phases

---

## Phase 1: Project Setup

### T001: Initialize Next.js Portal Project
**Priority**: P1 | **User Story**: Foundation | **Estimate**: 30min

Create new Next.js 14+ project with App Router:

```bash
npx create-next-app@latest portal --typescript --tailwind --eslint --app
```

**Acceptance Criteria**:
- [ ] AC-T001-1: `portal/` directory created at project root
- [ ] AC-T001-2: TypeScript configured with strict mode
- [ ] AC-T001-3: Tailwind CSS installed and configured
- [ ] AC-T001-4: App Router structure in place

---

### T002: Install UI Dependencies
**Priority**: P1 | **User Story**: Foundation | **Estimate**: 20min

Install Shadcn/ui, Recharts, and other dependencies:

```bash
npx shadcn@latest init
pnpm add recharts @tanstack/react-query @supabase/auth-helpers-nextjs
```

**Acceptance Criteria**:
- [ ] AC-T002-1: Shadcn/ui initialized with components.json
- [ ] AC-T002-2: Recharts installed for charting
- [ ] AC-T002-3: TanStack Query installed for data fetching
- [ ] AC-T002-4: Supabase auth helpers installed

---

### T003: Create Project Structure
**Priority**: P1 | **User Story**: Foundation | **Estimate**: 15min

Set up directory structure:

```
portal/
├── app/
│   ├── layout.tsx
│   ├── page.tsx (landing/login)
│   ├── dashboard/
│   │   ├── page.tsx
│   │   ├── history/page.tsx
│   │   ├── call/page.tsx
│   │   └── settings/page.tsx
│   └── auth/callback/route.ts
├── components/
│   ├── ui/
│   ├── dashboard/
│   ├── charts/
│   └── layout/
├── lib/
│   ├── supabase.ts
│   └── api.ts
└── hooks/
```

**Acceptance Criteria**:
- [ ] AC-T003-1: All directories created as specified
- [ ] AC-T003-2: Root layout.tsx with providers skeleton
- [ ] AC-T003-3: Empty page files as placeholders

---

## Phase 2: Authentication (US-1 Prerequisite)

### ⚠️ WRITE TESTS FIRST

### T004: Write Authentication Tests
**Priority**: P1 | **User Story**: US-1 | **Estimate**: 45min

```typescript
// __tests__/auth/login.test.tsx
describe('Magic Link Authentication', () => {
  it('sends magic link to valid email');
  it('redirects to dashboard after callback');
  it('shows error for invalid email format');
  it('handles auth callback token');
});

describe('Session Management', () => {
  it('persists session across page reloads');
  it('redirects to login when session expired');
});
```

**Acceptance Criteria**:
- [ ] AC-T004-1: Login flow tests written
- [ ] AC-T004-2: Session persistence tests written
- [ ] AC-T004-3: Auth callback tests written

---

### T005: Implement Supabase Client Setup
**Priority**: P1 | **User Story**: US-1 | **Estimate**: 30min

**File**: `portal/lib/supabase.ts`

```typescript
import { createClientComponentClient } from "@supabase/auth-helpers-nextjs";

export const supabase = createClientComponentClient();

export async function loginWithMagicLink(email: string) {
  const { error } = await supabase.auth.signInWithOtp({
    email,
    options: {
      emailRedirectTo: `${window.location.origin}/auth/callback`,
    },
  });
  return { error };
}
```

**Acceptance Criteria**:
- [ ] AC-T005-1: Supabase client configured for Next.js
- [ ] AC-T005-2: Magic link function implemented
- [ ] AC-T005-3: Environment variables validated

**References**: plan.md Task 2, FR-001

---

### T006: Implement Login Page
**Priority**: P1 | **User Story**: US-1 | **Estimate**: 45min

**File**: `portal/app/page.tsx`

Login form with magic link flow and error handling.

**Acceptance Criteria**:
- [ ] AC-T006-1: Email input with validation
- [ ] AC-T006-2: Submit triggers magic link send
- [ ] AC-T006-3: Success message shown after send
- [ ] AC-T006-4: Error handling for failed sends

---

### T007: Implement Auth Callback
**Priority**: P1 | **User Story**: US-1 | **Estimate**: 30min

**File**: `portal/app/auth/callback/route.ts`

Handle auth callback and redirect to dashboard.

**Acceptance Criteria**:
- [ ] AC-T007-1: Token exchange on callback
- [ ] AC-T007-2: Session cookie set
- [ ] AC-T007-3: Redirect to /dashboard

---

### T008: Implement Auth Middleware
**Priority**: P1 | **User Story**: US-1 | **Estimate**: 30min

**File**: `portal/middleware.ts`

Protect dashboard routes, redirect unauthenticated users.

**Acceptance Criteria**:
- [ ] AC-T008-1: /dashboard/* routes protected
- [ ] AC-T008-2: Unauthenticated users redirect to /
- [ ] AC-T008-3: Session refresh on each request

---

## Phase 3: Dashboard View (US-1)

### ⚠️ WRITE TESTS FIRST

### T009: Write Dashboard Tests
**Priority**: P1 | **User Story**: US-1 | **Estimate**: 45min

```typescript
describe('Dashboard View', () => {
  it('displays current relationship score');
  it('displays chapter name and number');
  it('shows metric breakdown');
  it('shows game status badge');
  it('shows days in relationship');
});
```

**Acceptance Criteria**:
- [ ] AC-T009-1: Score display test written
- [ ] AC-T009-2: Chapter display test written
- [ ] AC-T009-3: Metrics grid test written

---

### T010: Implement usePlayerStats Hook
**Priority**: P1 | **User Story**: US-1 | **Estimate**: 30min

**File**: `portal/hooks/use-player-stats.ts`

TanStack Query hook to fetch player dashboard data.

**Acceptance Criteria**:
- [ ] AC-T010-1: Fetches from /api/v1/portal/stats
- [ ] AC-T010-2: Returns typed PlayerStats object
- [ ] AC-T010-3: Handles loading/error states

**References**: plan.md Task 3

---

### T011: Implement ScoreCard Component
**Priority**: P1 | **User Story**: US-1 | **Estimate**: 30min

**File**: `portal/components/dashboard/score-card.tsx`

Display composite relationship score with visual indicator.

**Acceptance Criteria**:
- [ ] AC-T011-1: Shows score percentage prominently
- [ ] AC-T011-2: Color coded (green/yellow/red)
- [ ] AC-T011-3: Accessible (aria-label)

---

### T012: Implement ChapterCard Component
**Priority**: P1 | **User Story**: US-1 | **Estimate**: 30min

**File**: `portal/components/dashboard/chapter-card.tsx`

Display current chapter with name and progress.

**Acceptance Criteria**:
- [ ] AC-T012-1: Shows chapter number (1-5)
- [ ] AC-T012-2: Shows chapter name
- [ ] AC-T012-3: Progress bar to next boss

---

### T013: Implement MetricsGrid Component
**Priority**: P1 | **User Story**: US-1 | **Estimate**: 45min

**File**: `portal/components/dashboard/metrics-grid.tsx`

Display 4 individual metrics (intimacy, passion, trust, secureness).

**Acceptance Criteria**:
- [ ] AC-T013-1: All 4 metrics displayed
- [ ] AC-T013-2: Each with percentage and icon
- [ ] AC-T013-3: Responsive grid layout

---

### T014: Implement GameStatusBadge Component
**Priority**: P1 | **User Story**: US-1 | **Estimate**: 20min

**File**: `portal/components/dashboard/game-status-badge.tsx`

Show game status (active, boss_fight, game_over, won).

**Acceptance Criteria**:
- [ ] AC-T014-1: Different colors per status
- [ ] AC-T014-2: Appropriate icons
- [ ] AC-T014-3: Boss fight has special styling

---

### T015: Implement Dashboard Page
**Priority**: P1 | **User Story**: US-1 | **Estimate**: 45min

**File**: `portal/app/dashboard/page.tsx`

Assemble all dashboard components with grid layout.

**Acceptance Criteria**:
- [ ] AC-T015-1: All cards rendered in grid
- [ ] AC-T015-2: Loading skeleton shown
- [ ] AC-T015-3: Error state handled

**References**: plan.md Task 3, FR-002

---

## Phase 4: Decay Warning (US-4)

### ⚠️ WRITE TESTS FIRST

### T016: Write Decay Warning Tests
**Priority**: P1 | **User Story**: US-4 | **Estimate**: 30min

```typescript
describe('DecayWarning', () => {
  it('shows hours remaining until grace period expires');
  it('shows decay active warning when grace expired');
  it('calculates projected score correctly');
  it('applies warning styling when < 6 hours');
});
```

**Acceptance Criteria**:
- [ ] AC-T016-1: Grace period countdown tests
- [ ] AC-T016-2: Decay active warning tests
- [ ] AC-T016-3: Score projection tests

---

### T017: Implement DecayWarning Component
**Priority**: P1 | **User Story**: US-4 | **Estimate**: 45min

**File**: `portal/components/dashboard/decay-warning.tsx`

Display decay status with countdown and projected score.

**Acceptance Criteria**:
- [ ] AC-T017-1: Hours remaining calculated
- [ ] AC-T017-2: Projected score if no interaction
- [ ] AC-T017-3: Warning border when < 6 hours
- [ ] AC-T017-4: Active decay shown with emphasis

**References**: plan.md Task 7, FR-007

---

## Phase 5: Score History Charts (US-2)

### ⚠️ WRITE TESTS FIRST

### T018: Write Score Chart Tests
**Priority**: P2 | **User Story**: US-2 | **Estimate**: 30min

```typescript
describe('ScoreChart', () => {
  it('renders line chart with score data');
  it('marks significant events on timeline');
  it('updates when time range changes');
  it('shows tooltip on hover');
});
```

**Acceptance Criteria**:
- [ ] AC-T018-1: Chart rendering tests
- [ ] AC-T018-2: Event marker tests
- [ ] AC-T018-3: Time range filter tests

---

### T019: Implement useScoreHistory Hook
**Priority**: P2 | **User Story**: US-2 | **Estimate**: 30min

**File**: `portal/hooks/use-score-history.ts`

Fetch score history with time range parameter.

**Acceptance Criteria**:
- [ ] AC-T019-1: Fetches from /api/v1/portal/score-history
- [ ] AC-T019-2: Supports week/month/all range
- [ ] AC-T019-3: Returns ScoreHistoryEntry[]

---

### T020: Implement ScoreChart Component
**Priority**: P2 | **User Story**: US-2 | **Estimate**: 60min

**File**: `portal/components/charts/score-chart.tsx`

Line chart with Recharts showing score trends.

**Acceptance Criteria**:
- [ ] AC-T020-1: Responsive line chart
- [ ] AC-T020-2: Y-axis 0-100
- [ ] AC-T020-3: Event markers as reference dots
- [ ] AC-T020-4: Custom tooltip with details

**References**: plan.md Task 4, FR-003

---

### T021: Implement TimeRangeSelector Component
**Priority**: P2 | **User Story**: US-2 | **Estimate**: 20min

**File**: `portal/components/charts/time-range-selector.tsx`

Buttons to select week/month/all time range.

**Acceptance Criteria**:
- [ ] AC-T021-1: Three range options
- [ ] AC-T021-2: Active state styling
- [ ] AC-T021-3: onChange callback

---

## Phase 6: Conversation History (US-5)

### ⚠️ WRITE TESTS FIRST

### T022: Write Conversation History Tests
**Priority**: P3 | **User Story**: US-5 | **Estimate**: 30min

```typescript
describe('ConversationHistory', () => {
  it('lists conversations with dates');
  it('shows score impact per conversation');
  it('expands to show conversation detail');
  it('filters by date range');
});
```

**Acceptance Criteria**:
- [ ] AC-T022-1: List rendering tests
- [ ] AC-T022-2: Detail expansion tests
- [ ] AC-T022-3: Filter tests

---

### T023: Implement useConversationHistory Hook
**Priority**: P3 | **User Story**: US-5 | **Estimate**: 30min

**File**: `portal/hooks/use-conversation-history.ts`

Paginated fetch of conversation history.

**Acceptance Criteria**:
- [ ] AC-T023-1: Fetches from /api/v1/portal/conversations
- [ ] AC-T023-2: Supports pagination (limit, offset)
- [ ] AC-T023-3: Returns ConversationSummary[]

---

### T024: Implement ConversationList Component
**Priority**: P3 | **User Story**: US-5 | **Estimate**: 45min

**File**: `portal/components/history/conversation-list.tsx`

List of conversations with selection capability.

**Acceptance Criteria**:
- [ ] AC-T024-1: Shows date, type (text/voice), summary
- [ ] AC-T024-2: Score delta badge (+X / -X)
- [ ] AC-T024-3: Click to select
- [ ] AC-T024-4: Virtualized for performance

---

### T025: Implement ConversationDetail Component
**Priority**: P3 | **User Story**: US-5 | **Estimate**: 45min

**File**: `portal/components/history/conversation-detail.tsx`

Expanded view of selected conversation.

**Acceptance Criteria**:
- [ ] AC-T025-1: Shows full summary/excerpt
- [ ] AC-T025-2: Metric impacts listed
- [ ] AC-T025-3: Timestamp and duration

**References**: plan.md Task 5, FR-004

---

### T026: Implement History Page
**Priority**: P3 | **User Story**: US-5 | **Estimate**: 30min

**File**: `portal/app/dashboard/history/page.tsx`

Assemble history components with filters.

**Acceptance Criteria**:
- [ ] AC-T026-1: ConversationList + ConversationDetail layout
- [ ] AC-T026-2: Date filter controls
- [ ] AC-T026-3: Empty state handled

---

## Phase 7: Voice Call Interface (US-3)

### ⚠️ WRITE TESTS FIRST

### T027: Write Voice Call Tests
**Priority**: P1 | **User Story**: US-3 | **Estimate**: 30min

```typescript
describe('VoiceCallInterface', () => {
  it('shows call button when available');
  it('shows unavailable message with reason');
  it('initiates call on button click');
  it('displays call history');
});
```

**Acceptance Criteria**:
- [ ] AC-T027-1: Availability check tests
- [ ] AC-T027-2: Call initiation tests
- [ ] AC-T027-3: History display tests

---

### T028: Implement useCallAvailability Hook
**Priority**: P1 | **User Story**: US-3 | **Estimate**: 30min

**File**: `portal/hooks/use-call-availability.ts`

Check if voice calls available for user.

**Acceptance Criteria**:
- [ ] AC-T028-1: Fetches from /api/v1/voice/availability
- [ ] AC-T028-2: Returns { available: boolean, reason?: string }
- [ ] AC-T028-3: Chapter-based availability logic

---

### T029: Implement CallButton Component
**Priority**: P1 | **User Story**: US-3 | **Estimate**: 30min

**File**: `portal/components/call/call-button.tsx`

Large "Call Nikita" button with loading state.

**Acceptance Criteria**:
- [ ] AC-T029-1: Prominent call-to-action styling
- [ ] AC-T029-2: Loading spinner during initiation
- [ ] AC-T029-3: Disabled when unavailable

---

### T030: Implement CallUnavailable Component
**Priority**: P1 | **User Story**: US-3 | **Estimate**: 20min

**File**: `portal/components/call/call-unavailable.tsx`

Message explaining why calls unavailable.

**Acceptance Criteria**:
- [ ] AC-T030-1: Shows reason text
- [ ] AC-T030-2: Suggests when available
- [ ] AC-T030-3: Not alarming styling

---

### T031: Implement VoiceCallPage
**Priority**: P1 | **User Story**: US-3 | **Estimate**: 45min

**File**: `portal/app/dashboard/call/page.tsx`

Assemble voice call interface with history.

**Acceptance Criteria**:
- [ ] AC-T031-1: Call button or unavailable message
- [ ] AC-T031-2: Past call history list
- [ ] AC-T031-3: Integration with 007-voice-agent

**References**: plan.md Task 6, FR-006

---

## Phase 8: Settings (US-6)

### ⚠️ WRITE TESTS FIRST

### T032: Write Settings Tests
**Priority**: P3 | **User Story**: US-6 | **Estimate**: 30min

```typescript
describe('Settings', () => {
  it('displays notification preferences');
  it('handles data export request');
  it('confirms account deletion');
  it('logs out successfully');
});
```

**Acceptance Criteria**:
- [ ] AC-T032-1: Preference toggle tests
- [ ] AC-T032-2: Export request tests
- [ ] AC-T032-3: Deletion flow tests

---

### T033: Implement NotificationSettings Component
**Priority**: P3 | **User Story**: US-6 | **Estimate**: 30min

**File**: `portal/components/settings/notification-settings.tsx`

Toggle switches for email notifications.

**Acceptance Criteria**:
- [ ] AC-T033-1: Decay warning toggle
- [ ] AC-T033-2: Weekly summary toggle
- [ ] AC-T033-3: Persists to user preferences

---

### T034: Implement DataExportButton Component
**Priority**: P3 | **User Story**: US-6 | **Estimate**: 30min

**File**: `portal/components/settings/data-export-button.tsx`

Request data export (GDPR compliance).

**Acceptance Criteria**:
- [ ] AC-T034-1: Shows request button
- [ ] AC-T034-2: Confirms request sent
- [ ] AC-T034-3: Explains delivery timeline

---

### T035: Implement DeleteAccountButton Component
**Priority**: P3 | **User Story**: US-6 | **Estimate**: 30min

**File**: `portal/components/settings/delete-account-button.tsx`

Account deletion with confirmation dialog.

**Acceptance Criteria**:
- [ ] AC-T035-1: Requires confirmation
- [ ] AC-T035-2: Explains consequences
- [ ] AC-T035-3: Deletes and redirects

---

### T036: Implement Settings Page
**Priority**: P3 | **User Story**: US-6 | **Estimate**: 30min

**File**: `portal/app/dashboard/settings/page.tsx`

Assemble settings components.

**Acceptance Criteria**:
- [ ] AC-T036-1: All settings sections rendered
- [ ] AC-T036-2: Logout button at bottom
- [ ] AC-T036-3: Save confirmation for changes

**References**: plan.md Task 8, FR-008

---

## Phase 9: Backend API Routes

### T037: Implement Portal Stats Endpoint
**Priority**: P1 | **User Story**: US-1 | **Estimate**: 45min

**File**: `nikita/api/routes/portal.py`

```python
@router.get("/stats/{user_id}")
async def get_player_stats(user_id: UUID):
    """Dashboard data: score, chapter, metrics, status."""
```

**Acceptance Criteria**:
- [ ] AC-T037-1: Returns PlayerStats schema
- [ ] AC-T037-2: Auth validation (user_id matches JWT)
- [ ] AC-T037-3: Includes decay info

**References**: plan.md Task 9

---

### T038: Implement Score History Endpoint
**Priority**: P2 | **User Story**: US-2 | **Estimate**: 30min

**File**: `nikita/api/routes/portal.py`

```python
@router.get("/score-history/{user_id}")
async def get_score_history(user_id: UUID, range: str = "week"):
    """Score history for charts."""
```

**Acceptance Criteria**:
- [ ] AC-T038-1: Returns ScoreHistoryEntry[]
- [ ] AC-T038-2: Filters by time range
- [ ] AC-T038-3: Includes event markers

---

### T039: Implement Conversations Endpoint
**Priority**: P3 | **User Story**: US-5 | **Estimate**: 30min

**File**: `nikita/api/routes/portal.py`

```python
@router.get("/conversations/{user_id}")
async def get_conversations(user_id: UUID, limit: int = 20, offset: int = 0):
    """Paginated conversation history."""
```

**Acceptance Criteria**:
- [ ] AC-T039-1: Returns ConversationSummary[]
- [ ] AC-T039-2: Pagination working
- [ ] AC-T039-3: Score delta included

---

## Phase 10: Final Integration & Polish

### T040: Implement Responsive Layout
**Priority**: P1 | **User Story**: FR-010 | **Estimate**: 60min

Ensure all components work on mobile, tablet, desktop.

**Acceptance Criteria**:
- [ ] AC-T040-1: Mobile-first breakpoints
- [ ] AC-T040-2: Touch-friendly controls
- [ ] AC-T040-3: No horizontal scroll

---

### T041: Add Loading States
**Priority**: P1 | **User Story**: UX | **Estimate**: 30min

Skeleton loaders for all async data.

**Acceptance Criteria**:
- [ ] AC-T041-1: Dashboard skeleton
- [ ] AC-T041-2: Chart skeleton
- [ ] AC-T041-3: List skeletons

---

### T042: Add Error Boundaries
**Priority**: P1 | **User Story**: UX | **Estimate**: 30min

Error boundaries with retry capability.

**Acceptance Criteria**:
- [ ] AC-T042-1: Component-level error boundaries
- [ ] AC-T042-2: User-friendly error messages
- [ ] AC-T042-3: Retry button

---

## Progress Summary

| Phase | User Story | Tasks | Completed | Status |
|-------|------------|-------|-----------|--------|
| Phase 1 | Foundation | 3 | 0 | Pending |
| Phase 2 | US-1 (Auth) | 5 | 0 | Pending |
| Phase 3 | US-1 (Dashboard) | 7 | 0 | Pending |
| Phase 4 | US-4 (Decay) | 2 | 0 | Pending |
| Phase 5 | US-2 (Charts) | 4 | 0 | Pending |
| Phase 6 | US-5 (History) | 5 | 0 | Pending |
| Phase 7 | US-3 (Voice) | 5 | 0 | Pending |
| Phase 8 | US-6 (Settings) | 5 | 0 | Pending |
| Phase 9 | API Routes | 3 | 0 | Pending |
| Phase 10 | Polish | 3 | 0 | Pending |
| **Total** | | **42** | **0** | **Not Started** |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-29 | Initial tasks from plan.md |

# Implementation Tasks: 008-Player-Portal with Admin Dashboard

**Generated**: 2025-12-04
**From**: plan.md v2.0
**Priority**: P2
**Total Tasks**: 50 granular tasks across 6 phases

---

## Phase 1: Database & Backend Foundation

### T1: Create generated_prompts Migration
**Priority**: P1 | **User Story**: FR-017 | **Estimate**: 30min

Create Supabase migration for prompt logging table.

**File**: `supabase/migrations/YYYYMMDD_create_generated_prompts.sql`

```sql
CREATE TABLE generated_prompts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    prompt_content TEXT NOT NULL,
    token_count INTEGER NOT NULL,
    generation_time_ms FLOAT NOT NULL,
    meta_prompt_template VARCHAR(100) NOT NULL,
    context_snapshot JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_generated_prompts_user ON generated_prompts(user_id);
CREATE INDEX idx_generated_prompts_created ON generated_prompts(created_at DESC);
CREATE INDEX idx_generated_prompts_template ON generated_prompts(meta_prompt_template);
```

**Acceptance Criteria**:
- [ ] AC-T1.1: Table created via `mcp__supabase__apply_migration`
- [ ] AC-T1.2: All indexes created
- [ ] AC-T1.3: Foreign key constraints work

---

### T2: Create is_admin() Function
**Priority**: P1 | **User Story**: FR-013 | **Estimate**: 15min

Create admin check function based on email domain.

```sql
CREATE OR REPLACE FUNCTION is_admin()
RETURNS BOOLEAN AS $$
BEGIN
    RETURN (
        SELECT email LIKE '%@silent-agents.com'
        FROM auth.users
        WHERE id = auth.uid()
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

**Acceptance Criteria**:
- [ ] AC-T2.1: Function created via Supabase migration
- [ ] AC-T2.2: Returns true for @silent-agents.com emails
- [ ] AC-T2.3: Returns false for other emails

---

### T3: Add RLS Policies for generated_prompts
**Priority**: P1 | **User Story**: FR-017 | **Estimate**: 15min

Enable RLS and create policies.

```sql
ALTER TABLE generated_prompts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users see own prompts" ON generated_prompts
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Admin sees all prompts" ON generated_prompts
    FOR SELECT USING (is_admin());
```

**Acceptance Criteria**:
- [ ] AC-T3.1: RLS enabled
- [ ] AC-T3.2: User can only see own prompts
- [ ] AC-T3.3: Admin can see all prompts

---

### T4: Add Admin RLS Bypass Policies
**Priority**: P1 | **User Story**: FR-013 | **Estimate**: 30min

Add admin bypass policies to all required tables.

**Tables**: users, user_metrics, engagement_state, engagement_history, engagement_metrics, conversations, score_history, daily_summaries, user_vice_preferences

**Acceptance Criteria**:
- [ ] AC-T4.1: Admin can read all users
- [ ] AC-T4.2: Admin can update users
- [ ] AC-T4.3: Admin can read all related tables
- [ ] AC-T4.4: Regular users still scoped to own data

---

### T5: Create Portal API Schemas
**Priority**: P1 | **User Story**: US-3 | **Estimate**: 45min

**File**: `nikita/api/schemas/portal.py`

```python
class UserStatsResponse(BaseModel):
    id: UUID
    relationship_score: Decimal
    chapter: int
    chapter_name: str
    boss_threshold: Decimal
    progress_to_boss: Decimal
    days_played: int
    game_status: str
    last_interaction_at: datetime | None

class UserMetricsResponse(BaseModel):
    intimacy: Decimal
    passion: Decimal
    trust: Decimal
    secureness: Decimal
    weights: dict[str, Decimal]

class EngagementResponse(BaseModel):
    state: str
    multiplier: Decimal
    calibration_score: Decimal
    consecutive_in_zone: int
    consecutive_clingy_days: int
    consecutive_distant_days: int
    recent_transitions: list[dict]

class VicePreferenceResponse(BaseModel):
    category: str
    intensity_level: int
    engagement_score: Decimal
    discovered_at: datetime

class DecayStatusResponse(BaseModel):
    grace_period_hours: int
    hours_remaining: float
    decay_rate: Decimal
    current_score: Decimal
    projected_score: Decimal
    is_decaying: bool
```

**Acceptance Criteria**:
- [ ] AC-T5.1: All response schemas defined
- [ ] AC-T5.2: Pydantic validation works
- [ ] AC-T5.3: Types match database columns

---

### T6: Create Portal API Routes
**Priority**: P1 | **User Story**: US-1-US-8 | **Estimate**: 2hr

**File**: `nikita/api/routes/portal.py`

Implement all portal endpoints:
- GET /stats - Full dashboard data
- GET /metrics - 4 hidden metrics
- GET /engagement - Engagement state + history
- GET /vices - Vice preferences
- GET /score-history - For charts
- GET /daily-summaries - Daily summaries list
- GET /conversations - Conversation list
- GET /conversations/{id} - Conversation detail
- GET /decay - Decay status

**Acceptance Criteria**:
- [ ] AC-T6.1: All endpoints return correct data
- [ ] AC-T6.2: Auth required on all endpoints
- [ ] AC-T6.3: User can only access own data
- [ ] AC-T6.4: Response schemas match spec

---

### T7: Create Admin API Schemas
**Priority**: P1 | **User Story**: US-9-US-12 | **Estimate**: 30min

**File**: `nikita/api/schemas/admin.py`

```python
class AdminUserListItem(BaseModel):
    id: UUID
    telegram_id: int | None
    email: str | None
    relationship_score: Decimal
    chapter: int
    engagement_state: str
    game_status: str
    last_interaction_at: datetime | None

class AdminSetScoreRequest(BaseModel):
    score: Decimal = Field(ge=0, le=100)
    reason: str = Field(min_length=1)

class AdminSetChapterRequest(BaseModel):
    chapter: int = Field(ge=1, le=5)
    reason: str

class GeneratedPromptResponse(BaseModel):
    id: UUID
    user_id: UUID
    conversation_id: UUID | None
    prompt_content: str
    token_count: int
    generation_time_ms: float
    meta_prompt_template: str
    created_at: datetime
```

**Acceptance Criteria**:
- [ ] AC-T7.1: All admin schemas defined
- [ ] AC-T7.2: Request validation works
- [ ] AC-T7.3: Field constraints enforced

---

### T8: Create Admin API Routes
**Priority**: P1 | **User Story**: US-9-US-12 | **Estimate**: 2hr

**File**: `nikita/api/routes/admin.py`

Implement all admin endpoints:
- GET /users - List all users (paginated)
- GET /users/{id} - User detail
- GET /users/{id}/metrics - User metrics
- GET /users/{id}/engagement - User engagement
- GET /users/{id}/vices - User vices
- GET /users/{id}/conversations - User conversations
- PUT /users/{id}/score - Set score
- PUT /users/{id}/chapter - Set chapter
- PUT /users/{id}/status - Set game_status
- PUT /users/{id}/engagement - Set engagement_state
- POST /users/{id}/reset-boss - Reset boss_attempts
- POST /users/{id}/clear-engagement - Clear engagement history
- GET /prompts - List prompts (filtered)
- GET /prompts/{id} - Prompt detail
- GET /health - System health

**Acceptance Criteria**:
- [ ] AC-T8.1: Admin check on all endpoints
- [ ] AC-T8.2: 403 for non-admin users
- [ ] AC-T8.3: All modifications logged
- [ ] AC-T8.4: Pagination works

---

### T9: Update MetaPromptService for Logging
**Priority**: P1 | **User Story**: FR-017 | **Estimate**: 45min

**File**: `nikita/meta_prompts/service.py`

Add prompt logging after generation:

```python
async def generate_system_prompt(self, context: MetaPromptContext) -> str:
    start_time = time.time()
    prompt = await self._generate(context)
    generation_time_ms = (time.time() - start_time) * 1000

    # Log to database
    await self._log_prompt(
        user_id=context.user_id,
        conversation_id=context.conversation_id,
        prompt_content=prompt,
        token_count=self._count_tokens(prompt),
        generation_time_ms=generation_time_ms,
        meta_prompt_template="system_prompt"
    )
    return prompt
```

**Acceptance Criteria**:
- [ ] AC-T9.1: All prompts logged to generated_prompts
- [ ] AC-T9.2: Token count calculated correctly
- [ ] AC-T9.3: Generation time measured
- [ ] AC-T9.4: Template type recorded

---

### T10: Register Routes in main.py
**Priority**: P1 | **User Story**: Foundation | **Estimate**: 15min

**File**: `nikita/api/main.py`

```python
from nikita.api.routes import portal, admin

app.include_router(portal.router, prefix="/api/v1/portal", tags=["portal"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
```

**Acceptance Criteria**:
- [ ] AC-T10.1: Portal routes accessible
- [ ] AC-T10.2: Admin routes accessible
- [ ] AC-T10.3: OpenAPI docs updated

---

## Phase 2: Frontend Foundation

### T11: Initialize Next.js Portal Project
**Priority**: P1 | **User Story**: Foundation | **Estimate**: 30min

```bash
cd /Users/yangsim/Nanoleq/sideProjects/nikita
npx create-next-app@latest portal --typescript --tailwind --eslint --app --src-dir
```

**Acceptance Criteria**:
- [ ] AC-T11.1: portal/ directory created
- [ ] AC-T11.2: TypeScript configured
- [ ] AC-T11.3: Tailwind configured
- [ ] AC-T11.4: App Router in place

---

### T12: Install UI Dependencies
**Priority**: P1 | **User Story**: Foundation | **Estimate**: 20min

```bash
cd portal
npx shadcn@latest init
pnpm add recharts @tanstack/react-query @supabase/auth-helpers-nextjs
```

**Acceptance Criteria**:
- [ ] AC-T12.1: shadcn/ui initialized
- [ ] AC-T12.2: Recharts installed
- [ ] AC-T12.3: TanStack Query installed
- [ ] AC-T12.4: Supabase helpers installed

---

### T13: Configure Supabase SSR Clients
**Priority**: P1 | **User Story**: US-1, US-2 | **Estimate**: 30min | **Status**: ✅ COMPLETE

**Files**:
- `portal/src/lib/supabase/client.ts` - Browser client
- `portal/src/lib/supabase/server.ts` - Server component client
- `portal/src/lib/supabase/proxy.ts` - Session refresh utility

Uses @supabase/ssr (not deprecated auth-helpers-nextjs) with three-file pattern per official docs.

**Acceptance Criteria**:
- [x] AC-T13.1: Browser client (createBrowserClient) configured
- [x] AC-T13.2: Server client (createServerClient) configured
- [x] AC-T13.3: updateSession utility with proper cookie handling
- [x] AC-T13.4: Environment variables set (NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY)

---

### T14: Implement Login Page
**Priority**: P1 | **User Story**: US-1, US-2 | **Estimate**: 45min | **Status**: ✅ COMPLETE

**File**: `portal/src/app/page.tsx`

Login form with:
- Email input with validation
- Magic link submission
- Success message
- Error handling
- Code parameter detection (redirects to /auth/callback)

**Acceptance Criteria**:
- [x] AC-T14.1: Email validation works
- [x] AC-T14.2: Magic link sent via Supabase signInWithOtp
- [x] AC-T14.3: Success message shown
- [x] AC-T14.4: Errors displayed
- [x] AC-T14.5: Code param detected and redirected to callback

---

### T15: Implement Auth Callback
**Priority**: P1 | **User Story**: US-1, US-2 | **Estimate**: 30min | **Status**: ✅ COMPLETE

**File**: `portal/src/app/auth/callback/route.ts`

Handle magic link callback via route handler (not page).

**Acceptance Criteria**:
- [x] AC-T15.1: Token exchange via exchangeCodeForSession
- [x] AC-T15.2: Session cookie set by Supabase SSR
- [x] AC-T15.3: Redirects to /dashboard

---

### T15b: Backend JWT Authentication
**Priority**: P1 | **User Story**: US-1, US-2 | **Estimate**: 45min | **Status**: ✅ COMPLETE

**Files**:
- `nikita/api/dependencies/auth.py` - JWT validation dependency
- `nikita/config/settings.py` - SUPABASE_JWT_SECRET config

Backend validates Supabase JWTs and extracts user_id from 'sub' claim.

**Implementation**:
- PyJWT for HS256 token validation
- Validates against SUPABASE_JWT_SECRET
- Returns 401 for expired/invalid tokens
- Returns 403 for missing 'sub' claim

**Acceptance Criteria**:
- [x] AC-T15b.1: PyJWT dependency added to pyproject.toml
- [x] AC-T15b.2: SUPABASE_JWT_SECRET configured in settings
- [x] AC-T15b.3: get_current_user_id dependency validates tokens
- [x] AC-T15b.4: All portal routes use JWT auth dependency
- [x] AC-T15b.5: Cloud Run deployed with SUPABASE_JWT_SECRET env var

---

### T16: Implement Next.js 16 Proxy (Auth)
**Priority**: P1 | **User Story**: US-1, US-2 | **Estimate**: 30min | **Status**: ✅ COMPLETE

**File**: `portal/src/proxy.ts` (Next.js 16 renamed middleware.ts to proxy.ts)

Protect /dashboard/* routes using updateSession utility.

**Implementation**:
- Uses `updateSession()` from `lib/supabase/proxy.ts`
- Redirects unauthenticated users to / with error=auth_required
- Redirects authenticated users from / to /dashboard
- Properly refreshes session cookies

**Acceptance Criteria**:
- [x] AC-T16.1: Unauthenticated users redirected to /
- [x] AC-T16.2: Session refreshed via updateSession utility
- [x] AC-T16.3: Authenticated users auto-redirected to /dashboard
- [x] AC-T16.4: File exports `proxy()` function (not `middleware()`)

---

### T17: Create Dashboard Layout
**Priority**: P1 | **User Story**: US-3 | **Estimate**: 45min

**File**: `portal/src/app/dashboard/layout.tsx`

Dashboard shell with:
- Header with user info
- Sidebar navigation
- Main content area
- Responsive layout

**Acceptance Criteria**:
- [ ] AC-T17.1: Layout renders correctly
- [ ] AC-T17.2: Navigation works
- [ ] AC-T17.3: Responsive on mobile

---

## Phase 3: User Dashboard Components

### T18: Implement ScoreCard Component
**Priority**: P1 | **User Story**: US-3 | **Estimate**: 30min

**File**: `portal/src/components/dashboard/score-card.tsx`

Display relationship score with:
- Large score number
- Color-coded (green/yellow/red)
- Trend indicator
- Accessible labels

**Acceptance Criteria**:
- [ ] AC-T18.1: Score displayed prominently
- [ ] AC-T18.2: Colors based on thresholds
- [ ] AC-T18.3: Trend shows up/down/stable

---

### T19: Implement ChapterCard Component
**Priority**: P1 | **User Story**: US-3 | **Estimate**: 30min

**File**: `portal/src/components/dashboard/chapter-card.tsx`

Display chapter with:
- Chapter number and name
- Progress bar to boss threshold
- Boss threshold value

**Acceptance Criteria**:
- [ ] AC-T19.1: Chapter number shown
- [ ] AC-T19.2: Chapter name displayed
- [ ] AC-T19.3: Progress bar accurate

---

### T20: Implement MetricsGrid Component
**Priority**: P1 | **User Story**: US-3 | **Estimate**: 45min

**File**: `portal/src/components/dashboard/metrics-grid.tsx`

Display 4 metrics with:
- Intimacy (30%)
- Passion (25%)
- Trust (25%)
- Secureness (20%)
- Visual bars
- Weight percentages

**Acceptance Criteria**:
- [ ] AC-T20.1: All 4 metrics displayed
- [ ] AC-T20.2: Weights shown correctly
- [ ] AC-T20.3: Responsive grid

---

### T21: Implement EngagementCard Component
**Priority**: P1 | **User Story**: US-4 | **Estimate**: 45min

**File**: `portal/src/components/dashboard/engagement-card.tsx`

Display engagement state with:
- State name and badge
- Multiplier value
- State explanation
- Recent transitions

**Acceptance Criteria**:
- [ ] AC-T21.1: State displayed correctly
- [ ] AC-T21.2: Multiplier shown
- [ ] AC-T21.3: Transitions listed

---

### T22: Implement VicesCard Component
**Priority**: P2 | **User Story**: US-5 | **Estimate**: 45min

**File**: `portal/src/components/dashboard/vices-card.tsx`

Display discovered vices with:
- Vice category names
- Intensity bars (1-5)
- Only show discovered vices
- Category descriptions on hover

**Acceptance Criteria**:
- [ ] AC-T22.1: Vices listed
- [ ] AC-T22.2: Intensity bars accurate
- [ ] AC-T22.3: Empty state if none

---

### T23: Implement DecayWarning Component
**Priority**: P2 | **User Story**: US-8 | **Estimate**: 45min

**File**: `portal/src/components/dashboard/decay-warning.tsx`

Display decay status with:
- Grace period countdown
- Decay rate
- Projected score
- Warning styling when < 6 hours

**Acceptance Criteria**:
- [ ] AC-T23.1: Countdown displayed
- [ ] AC-T23.2: Projection calculated
- [ ] AC-T23.3: Warning at < 6 hours

---

### T24: Create TanStack Query Hooks
**Priority**: P1 | **User Story**: US-3-US-8 | **Estimate**: 1hr

**Files**: `portal/src/hooks/use-*.ts`

Create hooks:
- useStats() - Full dashboard data
- useMetrics() - 4 metrics
- useEngagement() - Engagement state
- useVices() - Vice preferences
- useDecay() - Decay status

All with:
- refetchInterval: 30000
- staleTime: 10000
- Error handling

**Acceptance Criteria**:
- [ ] AC-T24.1: All hooks implemented
- [ ] AC-T24.2: Polling at 30s
- [ ] AC-T24.3: Loading states work
- [ ] AC-T24.4: Errors handled

---

### T25: Assemble Dashboard Page
**Priority**: P1 | **User Story**: US-3 | **Estimate**: 45min

**File**: `portal/src/app/dashboard/page.tsx`

Combine all components:
- ScoreCard + ChapterCard (row 1)
- MetricsGrid (row 2)
- EngagementCard + VicesCard (row 3)
- DecayWarning (row 4)

**Acceptance Criteria**:
- [ ] AC-T25.1: All components render
- [ ] AC-T25.2: Grid layout correct
- [ ] AC-T25.3: Loading skeleton shown

---

## Phase 4: History & Conversations

### T26: Implement ScoreChart Component
**Priority**: P2 | **User Story**: US-6 | **Estimate**: 1hr

**File**: `portal/src/components/charts/score-chart.tsx`

Recharts line chart with:
- Score over time
- Y-axis 0-100
- Event markers
- Custom tooltip

**Acceptance Criteria**:
- [ ] AC-T26.1: Chart renders correctly
- [ ] AC-T26.2: Events marked
- [ ] AC-T26.3: Tooltip shows values

---

### T27: Implement TimeRangeSelector
**Priority**: P2 | **User Story**: US-6 | **Estimate**: 20min

**File**: `portal/src/components/charts/time-range-selector.tsx`

Buttons for week/month/all.

**Acceptance Criteria**:
- [ ] AC-T27.1: Three options shown
- [ ] AC-T27.2: Active state styled
- [ ] AC-T27.3: onChange callback works

---

### T28: Create History Page
**Priority**: P2 | **User Story**: US-6 | **Estimate**: 30min

**File**: `portal/src/app/dashboard/history/page.tsx`

Combine ScoreChart + TimeRangeSelector.

**Acceptance Criteria**:
- [ ] AC-T28.1: Chart + selector render
- [ ] AC-T28.2: Range changes chart
- [ ] AC-T28.3: Loading state handled

---

### T29: Implement ConversationList Component
**Priority**: P2 | **User Story**: US-7 | **Estimate**: 45min

**File**: `portal/src/components/history/conversation-list.tsx`

Paginated list with:
- Platform icon
- Date
- Score delta badge (+/-)
- Summary preview

**Acceptance Criteria**:
- [ ] AC-T29.1: List renders
- [ ] AC-T29.2: Pagination works
- [ ] AC-T29.3: Click to select

---

### T30: Implement ConversationDetail Component
**Priority**: P2 | **User Story**: US-7 | **Estimate**: 45min

**File**: `portal/src/components/history/conversation-detail.tsx`

Expanded view with:
- Full messages (read-only)
- Score impact
- Emotional tone
- Extracted entities

**Acceptance Criteria**:
- [ ] AC-T30.1: Messages displayed
- [ ] AC-T30.2: No send button
- [ ] AC-T30.3: Metadata shown

---

### T31: Create Conversations Page
**Priority**: P2 | **User Story**: US-7 | **Estimate**: 30min

**File**: `portal/src/app/dashboard/conversations/page.tsx`

Combine list + detail.

**Acceptance Criteria**:
- [ ] AC-T31.1: List + detail layout
- [ ] AC-T31.2: Selection works
- [ ] AC-T31.3: Empty state handled

---

### T32: Implement DailySummaryCard
**Priority**: P2 | **User Story**: FR-010 | **Estimate**: 30min

**File**: `portal/src/components/dashboard/daily-summary-card.tsx`

Display summary with:
- Date
- Score change
- Expandable text
- Emotional tone badge

**Acceptance Criteria**:
- [ ] AC-T32.1: Summary renders
- [ ] AC-T32.2: Expansion works
- [ ] AC-T32.3: Tone shown

---

### T33: Create Summaries Page
**Priority**: P2 | **User Story**: FR-010 | **Estimate**: 30min

**File**: `portal/src/app/dashboard/summaries/page.tsx`

List of daily summaries.

**Acceptance Criteria**:
- [ ] AC-T33.1: List renders
- [ ] AC-T33.2: Pagination works
- [ ] AC-T33.3: Empty state handled

---

## Phase 5: Admin Dashboard

### T34: Create Admin Layout
**Priority**: P1 Admin | **User Story**: US-9 | **Estimate**: 45min

**File**: `portal/src/app/admin/layout.tsx`

Admin shell with:
- Domain check (@silent-agents.com)
- Admin navigation
- Different styling
- Error for non-admins

**Acceptance Criteria**:
- [ ] AC-T34.1: Domain check works
- [ ] AC-T34.2: 403 for non-admins
- [ ] AC-T34.3: Navigation works

---

### T35: Implement UserList Component
**Priority**: P1 Admin | **User Story**: US-9 | **Estimate**: 1hr

**File**: `portal/src/components/admin/user-list.tsx`

Paginated table with:
- Sortable columns
- Search input
- User stats display
- Click to view detail

**Acceptance Criteria**:
- [ ] AC-T35.1: Table renders
- [ ] AC-T35.2: Sorting works
- [ ] AC-T35.3: Search filters

---

### T36: Create Admin Users Page
**Priority**: P1 Admin | **User Story**: US-9 | **Estimate**: 30min

**File**: `portal/src/app/admin/users/page.tsx`

User list page.

**Acceptance Criteria**:
- [ ] AC-T36.1: List renders
- [ ] AC-T36.2: Pagination works
- [ ] AC-T36.3: Links to detail

---

### T37: Implement UserDetail Component
**Priority**: P1 Admin | **User Story**: US-10 | **Estimate**: 1hr

**File**: `portal/src/components/admin/user-detail.tsx`

Full user view with:
- All user data
- Metrics, engagement, vices
- Score history chart
- Recent conversations

**Acceptance Criteria**:
- [ ] AC-T37.1: All data displayed
- [ ] AC-T37.2: Charts work
- [ ] AC-T37.3: Responsive layout

---

### T38: Implement GameControls Component
**Priority**: P1 Admin | **User Story**: US-11 | **Estimate**: 1.5hr

**File**: `portal/src/components/admin/game-controls.tsx`

Admin control forms:
- Set score (0-100) + reason
- Set chapter (1-5) + reason
- Set game_status dropdown
- Set engagement_state dropdown
- Reset boss_attempts button
- Clear engagement history button

**Acceptance Criteria**:
- [ ] AC-T38.1: Score form works
- [ ] AC-T38.2: Chapter form works
- [ ] AC-T38.3: Status dropdowns work
- [ ] AC-T38.4: Reset buttons work
- [ ] AC-T38.5: Confirmation dialogs

---

### T39: Create Admin User Detail Page
**Priority**: P1 Admin | **User Story**: US-10, US-11 | **Estimate**: 45min

**File**: `portal/src/app/admin/users/[id]/page.tsx`

Combine UserDetail + GameControls.

**Acceptance Criteria**:
- [ ] AC-T39.1: Detail + controls render
- [ ] AC-T39.2: Modifications persist
- [ ] AC-T39.3: Success feedback

---

### T40: Implement PromptViewer Component
**Priority**: P2 Admin | **User Story**: US-12 | **Estimate**: 1hr

**File**: `portal/src/components/admin/prompt-viewer.tsx`

Prompt list + detail with:
- Paginated list
- Filters (user, date, template)
- Full content view
- Token count display

**Acceptance Criteria**:
- [ ] AC-T40.1: List renders
- [ ] AC-T40.2: Filters work
- [ ] AC-T40.3: Content expandable

---

### T41: Create Admin Prompts Page
**Priority**: P2 Admin | **User Story**: US-12 | **Estimate**: 30min

**File**: `portal/src/app/admin/prompts/page.tsx`

Prompt viewer page.

**Acceptance Criteria**:
- [ ] AC-T41.1: Viewer renders
- [ ] AC-T41.2: Pagination works
- [ ] AC-T41.3: Search works

---

### T42: Implement Admin Health Display
**Priority**: P3 Admin | **User Story**: FR-019 | **Estimate**: 30min

**File**: `portal/src/components/admin/health-display.tsx`

System health with:
- API status
- Database status
- Recent error count

**Acceptance Criteria**:
- [ ] AC-T42.1: Status indicators work
- [ ] AC-T42.2: Auto-refresh

---

### T43: Create Admin Overview Page
**Priority**: P2 Admin | **User Story**: US-9 | **Estimate**: 30min

**File**: `portal/src/app/admin/page.tsx`

Admin dashboard with:
- User count
- Active users
- Quick links
- Health status

**Acceptance Criteria**:
- [ ] AC-T43.1: Stats displayed
- [ ] AC-T43.2: Links work
- [ ] AC-T43.3: Health shown

---

## Phase 6: Settings & Polish

### T44: Implement Settings Page
**Priority**: P2 | **User Story**: FR-008 | **Estimate**: 45min

**File**: `portal/src/app/dashboard/settings/page.tsx`

Settings with:
- Notification preferences
- Account section
- Link Telegram button
- Logout button

**Acceptance Criteria**:
- [ ] AC-T44.1: Preferences toggle
- [ ] AC-T44.2: Settings persist
- [ ] AC-T44.3: Logout works

---

### T45: Implement Account Deletion
**Priority**: P3 | **User Story**: FR-008 | **Estimate**: 30min

Delete account with:
- Confirmation dialog
- Warning text
- Actual deletion

**Acceptance Criteria**:
- [ ] AC-T45.1: Confirmation required
- [ ] AC-T45.2: Account deleted
- [ ] AC-T45.3: Redirects to home

---

### T46: Implement Telegram Linking
**Priority**: P3 | **User Story**: US-13 | **Estimate**: 45min

Linking flow:
- Generate unique code
- Display code with instructions
- Code expires in 10 minutes

**Acceptance Criteria**:
- [ ] AC-T46.1: Code generated
- [ ] AC-T46.2: Instructions shown
- [ ] AC-T46.3: Expiry displayed

---

### T47: Add Responsive Design
**Priority**: P1 | **User Story**: FR-021 | **Estimate**: 1hr

Mobile-first responsive:
- Collapsible sidebar
- Stacked cards on mobile
- Touch-friendly controls

**Acceptance Criteria**:
- [ ] AC-T47.1: Mobile layout works
- [ ] AC-T47.2: Tablet layout works
- [ ] AC-T47.3: No horizontal scroll

---

### T48: Add Error Boundaries
**Priority**: P1 | **User Story**: UX | **Estimate**: 30min

Error handling:
- Component-level boundaries
- Retry buttons
- User-friendly messages

**Acceptance Criteria**:
- [ ] AC-T48.1: Errors caught
- [ ] AC-T48.2: Retry works
- [ ] AC-T48.3: Messages clear

---

### T49: Add Loading Skeletons
**Priority**: P1 | **User Story**: UX | **Estimate**: 30min

Loading states:
- Dashboard skeleton
- List skeletons
- Chart skeleton

**Acceptance Criteria**:
- [ ] AC-T49.1: Skeletons match layout
- [ ] AC-T49.2: Smooth transitions

---

### T50: Configure Vercel Deployment
**Priority**: P1 | **User Story**: Foundation | **Estimate**: 30min

Deployment setup:
- vercel.json configuration
- Environment variables
- Build settings

**Acceptance Criteria**:
- [ ] AC-T50.1: Builds successfully
- [ ] AC-T50.2: Environment vars set
- [ ] AC-T50.3: Deploys to Vercel

---

## Progress Summary

| Phase | User Story | Tasks | Completed | Status |
|-------|------------|-------|-----------|--------|
| Phase 1 | Backend Foundation | 10 | 0 | Pending |
| Phase 2 | Frontend Foundation | 7 | 0 | Pending |
| Phase 3 | User Dashboard | 8 | 0 | Pending |
| Phase 4 | History & Conversations | 8 | 0 | Pending |
| Phase 5 | Admin Dashboard | 10 | 0 | Pending |
| Phase 6 | Settings & Polish | 7 | 0 | Pending |
| **Total** | | **50** | **0** | **Not Started** |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-29 | Initial tasks from plan.md v1 (42 tasks) |
| 2.0 | 2025-12-04 | Complete rewrite with admin dashboard, prompt logging (50 tasks) |

# Implementation Plan: 008-Player-Portal with Admin Dashboard

**Generated**: 2025-12-04
**Feature**: 008 - Player Portal with Admin Dashboard
**Input**: spec.md v2.0
**Priority**: P2

---

## Overview

The Player Portal is a Next.js web dashboard providing:
1. **User Dashboard**: Full transparency into game state (score, metrics, engagement, vices)
2. **Admin Dashboard**: Developer tools for testing, debugging, game state manipulation
3. **Prompt Logging**: System for storing and viewing all generated prompts

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Player Portal Architecture                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                     Next.js 14+ Frontend (Vercel)                   │ │
│  │                                                                      │ │
│  │  ┌──────────────────────────────────────────────────────────────┐  │ │
│  │  │                      Authentication Layer                      │  │ │
│  │  │   Portal-First (email) ←→ Telegram-First (magic link)         │  │ │
│  │  │                   ↓ Supabase Auth JWT                          │  │ │
│  │  └──────────────────────────────────────────────────────────────┘  │ │
│  │                                                                      │ │
│  │  ┌─────────────────────────┐  ┌─────────────────────────┐          │ │
│  │  │     User Dashboard      │  │    Admin Dashboard      │          │ │
│  │  │  ┌─────────────────┐   │  │  ┌─────────────────┐   │          │ │
│  │  │  │ ScoreCard       │   │  │  │ UserList        │   │          │ │
│  │  │  │ ChapterCard     │   │  │  │ UserDetail      │   │          │ │
│  │  │  │ MetricsGrid     │   │  │  │ GameControls    │   │          │ │
│  │  │  │ EngagementCard  │   │  │  │ PromptViewer    │   │          │ │
│  │  │  │ VicesCard       │   │  │  │ Telemetry       │   │          │ │
│  │  │  │ DecayWarning    │   │  │  └─────────────────┘   │          │ │
│  │  │  │ ScoreChart      │   │  │  @silent-agents.com    │          │ │
│  │  │  └─────────────────┘   │  │  email domain check    │          │ │
│  │  └─────────────────────────┘  └─────────────────────────┘          │ │
│  │                                                                      │ │
│  │  ┌──────────────────────────────────────────────────────────────┐  │ │
│  │  │                    TanStack Query (Polling)                    │  │ │
│  │  │          refetchInterval: 30s | staleTime: 10s                │  │ │
│  │  └──────────────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                      │                                   │
│                              API Calls (HTTPS)                           │
│                                      ▼                                   │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                  Backend API (Cloud Run - Existing)                  │ │
│  │                                                                      │ │
│  │  ┌───────────────────────────┐  ┌───────────────────────────┐     │ │
│  │  │  /api/v1/portal/* (NEW)   │  │  /api/v1/admin/* (NEW)    │     │ │
│  │  │  - /stats                 │  │  - /users                 │     │ │
│  │  │  - /metrics               │  │  - /users/{id}/score      │     │ │
│  │  │  - /engagement            │  │  - /users/{id}/chapter    │     │ │
│  │  │  - /vices                 │  │  - /prompts               │     │ │
│  │  │  - /score-history         │  │  - /health                │     │ │
│  │  │  - /conversations         │  │                           │     │ │
│  │  │  - /decay                 │  │  Admin: is_admin() check  │     │ │
│  │  └───────────────────────────┘  └───────────────────────────┘     │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                      │                                   │
│                                      ▼                                   │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                       Supabase Database                              │ │
│  │                                                                      │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐ │ │
│  │  │   users     │  │user_metrics │  │    generated_prompts (NEW)  │ │ │
│  │  │engagement_  │  │user_vice_   │  │  - user_id                  │ │ │
│  │  │  state      │  │ preferences │  │  - prompt_content           │ │ │
│  │  │score_history│  │conversations│  │  - token_count              │ │ │
│  │  │daily_       │  │engagement_  │  │  - generation_time_ms       │ │ │
│  │  │ summaries   │  │  history    │  │  - meta_prompt_template     │ │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────────┘ │ │
│  │                                                                      │ │
│  │  RLS: auth.uid() = user_id | is_admin() bypass for admin             │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Frontend | Next.js 14+ (App Router) | React framework with SSR |
| UI Components | shadcn/ui + Tailwind CSS | Consistent, accessible UI |
| Charts | Recharts | Score history visualization |
| Auth | Supabase Auth | Magic link, JWT, RLS |
| State | TanStack Query | Data fetching + polling |
| API Client | Supabase JS Client | Type-safe API calls |
| Hosting | Vercel | Edge deployment |
| Backend | FastAPI (existing) | API endpoints |
| Database | Supabase PostgreSQL | Data persistence |

---

## Data Flow

### User Dashboard Flow
```
User Login (Magic Link) → Supabase Auth → JWT Token
    ↓
Portal Frontend → TanStack Query
    ↓
GET /api/v1/portal/stats
    ↓
JWT Validation (PyJWT) → Extract user_id from 'sub' claim
    ↓
UserRepository.get(user_id)
    ↓
┌─────────────────────────────────────────────────┐
│ Portal-First User Detection (IMPLEMENTED)       │
│                                                  │
│ if user not found:                              │
│   → UserRepository.create_with_metrics(user_id) │
│   → Default: score=50, chapter=1, metrics=50   │
│   → session.commit()                            │
└─────────────────────────────────────────────────┘
    ↓
MetricsRepository.get() → UserStatsResponse includes nested metrics
    ↓
Response: UserStatsResponse {
    score, chapter, boss_attempts, metrics: {intimacy, passion, trust, secureness}
}
    ↓
Dashboard Components Render
    ↓
Polling: refetch every 30s
```

### Admin Flow
```
Admin Login (@silent-agents.com) → Supabase Auth → JWT Token
    ↓
Admin Frontend → TanStack Query
    ↓
Request to /api/v1/admin/*
    ↓
is_admin() Check (email domain)
    ↓
RLS Bypass → Full database access
    ↓
Response: All user data
```

### Prompt Logging Flow
```
User Message → Telegram/Portal
    ↓
NikitaAgent.generate_response()
    ↓
MetaPromptService.generate_system_prompt()
    ↓
Log to generated_prompts table:
    - user_id, conversation_id
    - prompt_content (full text)
    - token_count (tiktoken)
    - generation_time_ms
    - meta_prompt_template
    ↓
Admin: GET /api/v1/admin/prompts
```

---

## Database Changes

### New Table: generated_prompts

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

### New Function: is_admin()

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

### RLS Policy Updates

```sql
-- Enable RLS on generated_prompts
ALTER TABLE generated_prompts ENABLE ROW LEVEL SECURITY;

-- Users see own prompts
CREATE POLICY "Users see own prompts" ON generated_prompts
    FOR SELECT USING (auth.uid() = user_id);

-- Admin bypass on all tables
CREATE POLICY "Admin reads all" ON users
    FOR SELECT USING (auth.uid() = id OR is_admin());
CREATE POLICY "Admin updates all" ON users
    FOR UPDATE USING (is_admin());

-- Repeat for: user_metrics, engagement_state, engagement_history,
-- engagement_metrics, conversations, score_history, daily_summaries,
-- user_vice_preferences, generated_prompts
```

---

## API Endpoints

### Portal Routes (nikita/api/routes/portal.py)

| Endpoint | Method | Description | Response Schema |
|----------|--------|-------------|-----------------|
| /api/v1/portal/stats | GET | Full dashboard data | UserStatsResponse |
| /api/v1/portal/metrics | GET | 4 hidden metrics | UserMetricsResponse |
| /api/v1/portal/engagement | GET | Engagement state + history | EngagementResponse |
| /api/v1/portal/vices | GET | Vice preferences | VicePreferencesResponse |
| /api/v1/portal/score-history | GET | Score history for charts | ScoreHistoryResponse |
| /api/v1/portal/daily-summaries | GET | Daily summaries list | DailySummariesResponse |
| /api/v1/portal/conversations | GET | Conversation list | ConversationsResponse |
| /api/v1/portal/conversations/{id} | GET | Conversation detail | ConversationDetailResponse |
| /api/v1/portal/decay | GET | Decay status | DecayStatusResponse |
| /api/v1/portal/settings | GET | User settings | UserSettingsResponse |
| /api/v1/portal/settings | PUT | Update settings | UserSettingsResponse |
| /api/v1/portal/link-telegram | POST | Generate link code | LinkCodeResponse |
| /api/v1/portal/account | DELETE | Delete account | SuccessResponse |

### Admin Routes (nikita/api/routes/admin.py)

| Endpoint | Method | Description | Response Schema |
|----------|--------|-------------|-----------------|
| /api/v1/admin/users | GET | List all users | AdminUserListResponse |
| /api/v1/admin/users/{id} | GET | User detail | AdminUserDetailResponse |
| /api/v1/admin/users/{id}/metrics | GET | User metrics | UserMetricsResponse |
| /api/v1/admin/users/{id}/engagement | GET | User engagement | EngagementResponse |
| /api/v1/admin/users/{id}/vices | GET | User vices | VicePreferencesResponse |
| /api/v1/admin/users/{id}/conversations | GET | User conversations | ConversationsResponse |
| /api/v1/admin/users/{id}/score | PUT | Set score | SuccessResponse |
| /api/v1/admin/users/{id}/chapter | PUT | Set chapter | SuccessResponse |
| /api/v1/admin/users/{id}/status | PUT | Set game_status | SuccessResponse |
| /api/v1/admin/users/{id}/engagement | PUT | Set engagement_state | SuccessResponse |
| /api/v1/admin/users/{id}/reset-boss | POST | Reset boss_attempts | SuccessResponse |
| /api/v1/admin/users/{id}/clear-engagement | POST | Clear engagement history | SuccessResponse |
| /api/v1/admin/prompts | GET | List prompts (filtered) | PromptsListResponse |
| /api/v1/admin/prompts/{id} | GET | Prompt detail | PromptDetailResponse |
| /api/v1/admin/health | GET | System health | HealthResponse |

---

## Frontend Structure

```
portal/
├── app/
│   ├── layout.tsx                     # Root layout with providers
│   ├── page.tsx                       # Landing/login page
│   ├── auth/
│   │   └── callback/page.tsx          # Magic link callback
│   ├── dashboard/
│   │   ├── layout.tsx                 # Dashboard shell with nav
│   │   ├── page.tsx                   # Main dashboard (metrics, engagement, vices)
│   │   ├── history/page.tsx           # Score history charts
│   │   ├── conversations/page.tsx     # Conversation list
│   │   ├── conversations/[id]/page.tsx # Conversation detail
│   │   ├── summaries/page.tsx         # Daily summaries
│   │   └── settings/page.tsx          # User settings
│   └── admin/
│       ├── layout.tsx                 # Admin shell (domain check)
│       ├── page.tsx                   # Admin overview
│       ├── users/page.tsx             # User list
│       ├── users/[id]/page.tsx        # User detail + controls
│       └── prompts/page.tsx           # Prompt viewer
├── components/
│   ├── ui/                            # shadcn/ui components
│   ├── dashboard/
│   │   ├── score-card.tsx             # Main score display
│   │   ├── chapter-card.tsx           # Chapter + boss progress
│   │   ├── metrics-grid.tsx           # 4 metrics display
│   │   ├── engagement-card.tsx        # Engagement state + multiplier
│   │   ├── vices-card.tsx             # Vice preferences
│   │   ├── decay-warning.tsx          # Decay countdown
│   │   └── daily-summary-card.tsx     # Summary display
│   ├── charts/
│   │   ├── score-chart.tsx            # Recharts line chart
│   │   └── time-range-selector.tsx    # Week/month/all selector
│   ├── admin/
│   │   ├── user-list.tsx              # Paginated user table
│   │   ├── user-detail.tsx            # Full user view
│   │   ├── game-controls.tsx          # State modification forms
│   │   └── prompt-viewer.tsx          # Prompt content display
│   └── layout/
│       ├── header.tsx                 # Top navigation
│       ├── sidebar.tsx                # Side navigation
│       └── footer.tsx                 # Footer
├── hooks/
│   ├── use-stats.ts                   # TanStack Query: /stats
│   ├── use-metrics.ts                 # TanStack Query: /metrics
│   ├── use-engagement.ts              # TanStack Query: /engagement
│   ├── use-vices.ts                   # TanStack Query: /vices
│   ├── use-score-history.ts           # TanStack Query: /score-history
│   ├── use-conversations.ts           # TanStack Query: /conversations
│   ├── use-decay.ts                   # TanStack Query: /decay
│   └── use-admin.ts                   # Admin-specific hooks
├── lib/
│   ├── supabase.ts                    # Supabase client config
│   ├── api.ts                         # Fetch wrapper with auth
│   └── constants.ts                   # Game constants (mirrored)
├── types/
│   └── api.ts                         # TypeScript types from backend
└── middleware.ts                      # Auth middleware
```

---

## Implementation Phases

### Phase 1: Database & Backend Foundation (T1-T8)
**Duration**: 1-2 days

1. Create `generated_prompts` table via Supabase migration
2. Create `is_admin()` function
3. Add RLS policies for admin bypass
4. Create `nikita/api/routes/portal.py` with user endpoints
5. Create `nikita/api/routes/admin.py` with admin endpoints
6. Create Pydantic schemas for responses
7. Update `nikita/meta_prompts/service.py` to log prompts
8. Register routes in `nikita/api/main.py`

### Phase 2: Frontend Foundation (T9-T15)
**Duration**: 1 day

1. Initialize Next.js portal project
2. Install shadcn/ui and configure Tailwind
3. Set up Supabase Auth client
4. Create root layout with providers
5. Implement login page (portal-first + Telegram-first)
6. Implement auth callback handler
7. Create dashboard shell layout

### Phase 3: User Dashboard Components (T16-T24)
**Duration**: 2-3 days

1. Implement ScoreCard component
2. Implement ChapterCard component
3. Implement MetricsGrid component
4. Implement EngagementCard component
5. Implement VicesCard component
6. Implement DecayWarning component
7. Create TanStack Query hooks with 30s polling
8. Assemble main dashboard page
9. Add loading skeletons

### Phase 4: History & Conversations (T25-T32)
**Duration**: 1-2 days

1. Implement ScoreChart with Recharts
2. Implement TimeRangeSelector
3. Create history page
4. Implement ConversationList
5. Implement ConversationDetail (read-only)
6. Create conversations page
7. Implement DailySummaryCard
8. Create summaries page

### Phase 5: Admin Dashboard (T33-T42)
**Duration**: 2-3 days

1. Create admin layout with domain check
2. Implement UserList with search/sort
3. Implement UserDetail view
4. Implement GameControls form (score, chapter, engagement)
5. Implement reset/clear actions
6. Create admin user detail page
7. Implement PromptViewer with filters
8. Create prompts page
9. Implement health check display
10. Add admin navigation

### Phase 6: Settings & Polish (T43-T50)
**Duration**: 1 day

1. Implement settings page (notifications, account)
2. Implement account deletion with confirmation
3. Implement Telegram linking flow
4. Add responsive design (mobile-first)
5. Add error boundaries
6. Add empty states
7. Configure Vercel deployment
8. Test end-to-end

---

## User Story Mapping

| User Story | Priority | Phase | Tasks |
|------------|----------|-------|-------|
| US-1: Portal-First Registration | P1 | 2 | T10-T12 |
| US-2: Telegram User Portal Access | P1 | 2 | T10-T12 |
| US-3: View Full Metrics Dashboard | P1 | 3 | T16-T19, T23 |
| US-4: View Engagement State | P1 | 3 | T20, T23 |
| US-5: View Vice Preferences | P2 | 3 | T21, T23 |
| US-6: View Score History | P2 | 4 | T25-T28 |
| US-7: View Conversation History | P2 | 4 | T29-T31 |
| US-8: View Decay Status | P2 | 3 | T22, T23 |
| US-9: Admin User List | P1 Admin | 5 | T33-T35 |
| US-10: Admin View User Detail | P1 Admin | 5 | T36 |
| US-11: Admin Modify Game State | P1 Admin | 5 | T37-T39 |
| US-12: Admin View Prompts | P2 Admin | 5 | T40-T41 |
| US-13: Account Linking | P3 | 6 | T45 |

---

## Dependencies

### Internal Dependencies

| Spec | Requirement | Blocking? | Notes |
|------|-------------|-----------|-------|
| 009-database | Tables exist | No | All required tables exist |
| 010-api | FastAPI patterns | No | Follow existing patterns |
| 013-configuration | YAML configs | No | Load chapter thresholds |
| 014-engagement | Engagement tables | No | Tables implemented |
| 003-scoring | Scoring logic | Soft | Display only, no calculation |
| 005-decay | Decay constants | Soft | Use existing constants |

### External Dependencies

| Dependency | Version | Purpose | Blocking? |
|------------|---------|---------|-----------|
| Supabase | Existing | Auth, Database | Yes |
| Vercel | Latest | Hosting | Yes |
| Next.js | 14+ | Frontend framework | Yes |
| shadcn/ui | Latest | UI components | No |
| Recharts | 2.x | Charts | No |
| TanStack Query | 5.x | Data fetching | No |

---

## Security Considerations

1. **Authentication**: Supabase Auth JWT validation on all endpoints
   - **IMPLEMENTED**: `nikita/api/dependencies/auth.py`
   - Uses PyJWT to decode and validate tokens
   - Validates `audience: "authenticated"` claim
   - Extracts `sub` claim as user_id (UUID)
   - Requires `SUPABASE_JWT_SECRET` environment variable
2. **Authorization**: RLS policies enforce user-scoped data access
3. **Admin Access**: Email domain check (`@silent-agents.com`)
4. **HTTPS**: Enforced by Vercel
5. **Rate Limiting**: Existing FastAPI rate limiter
6. **Audit Logging**: Admin modifications logged to score_history

---

## Constitution Alignment

### Article I: Architecture Principles
- ✅ Portal is view-only, preserves Telegram immersion (FR-022)
- ✅ No messaging from portal

### Article III: Game Mechanics
- ✅ Score calculations displayed, not modified
- ✅ Admin changes logged to score_history

### Article VI: UX Principles
- ✅ Mobile-first responsive design (FR-021)
- ✅ WCAG 2.1 AA accessibility
- ✅ Loading states and error handling

### Article VII: Development Principles
- ✅ TDD approach (tests before implementation)
- ✅ Type-safe with TypeScript + Pydantic

---

## Success Criteria

1. Portal loads in < 2 seconds
2. All 4 metrics visible on dashboard
3. Engagement state shows with multiplier
4. Admin can modify any user's game state
5. All prompts logged and viewable
6. Works on mobile and desktop
7. 100% data accuracy vs database

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-29 | Initial plan from spec.md v1 |
| 2.0 | 2025-12-04 | Complete rewrite with admin dashboard, prompt logging, full transparency |

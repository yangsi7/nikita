---
feature: 008-player-portal
created: 2025-11-28
updated: 2025-12-04
status: Draft
priority: P2
technology_agnostic: false
constitutional_compliance:
  article_iv: specification_first
---

# Feature Specification: Player Portal with Admin Dashboard

---

## Summary

The Player Portal is a Next.js web dashboard providing **full transparency** into game state for players, plus an **Admin Dashboard** for developers to test, debug, and manipulate game state.

**Problem Statement**: The core game (Telegram) has no visible UI by design. Players need visibility into their hidden metrics, engagement state, and relationship progress. Developers need tools to test the game and debug issues.

**Value Proposition**:
1. **Players**: See everything - score, all 4 hidden metrics, engagement state, vice preferences, decay status
2. **Admins**: Full control - view any user, modify game state, view all generated prompts

### Key Features
- **Dual Auth**: Portal-first registration OR Telegram-first login
- **Full Transparency**: Users see ALL hidden metrics (intimacy, passion, trust, secureness)
- **Engagement Display**: Current state, multiplier, transition history
- **Vice Preferences**: Discovered vices with intensity levels
- **Admin Controls**: Reset score, change chapter, modify engagement state
- **Prompt Logging**: All generated system prompts stored and viewable

---

## Functional Requirements

### Authentication

#### FR-001: Portal-First Registration
System MUST allow users to create accounts directly on the portal:
- Email registration with magic link (Supabase Auth OTP)
- Creates new user record with default game state (score=50, chapter=1)
- Optional Telegram linking later via settings

**Rationale**: Not all users start via Telegram; portal-first expands accessibility
**Priority**: Must Have

#### FR-002: Telegram-First Login
System MUST allow existing Telegram users to access portal:
- Login via email magic link (same email used in Telegram registration)
- Single auth.users.id spans both platforms
- Same game state visible across Telegram and Portal

**Rationale**: Existing Telegram users should seamlessly access the portal
**Priority**: Must Have

#### FR-003: Account Linking
System MUST allow linking between Portal and Telegram accounts:
- Portal users can link Telegram via generated code
- Telegram users can access portal with same magic link
- Bi-directional: either platform can initiate linking

**Rationale**: Users may start on one platform and want the other
**Priority**: Should Have

### User Dashboard

#### FR-004: Score Display
System MUST display current relationship score (0-100):
- Prominent score display with visual indicator
- Color-coded: green (70+), yellow (40-69), red (<40)
- Shows trend (up/down/stable) from last interaction

**Rationale**: Core "where am I" visibility
**Priority**: Must Have

#### FR-005: Chapter Display
System MUST display current chapter with progress:
- Chapter number (1-5) and chapter name
- Progress bar to boss threshold (e.g., "65% to boss at 60%")
- Boss threshold varies by chapter (55%, 60%, 65%, 70%, 75%)

**Rationale**: Clear progress toward milestones
**Priority**: Must Have

#### FR-006: Full Metrics Transparency
System MUST display ALL 4 hidden metrics:
- Intimacy (30% weight): 0-100
- Passion (25% weight): 0-100
- Trust (25% weight): 0-100
- Secureness (20% weight): 0-100
- Composite formula explanation

**Rationale**: Full transparency - users understand how score is calculated
**Priority**: Must Have

#### FR-007: Engagement State Display
System MUST display current engagement state:
- State name: calibrating, in_zone, drifting, clingy, distant, out_of_zone
- Current multiplier (0.2x - 1.0x)
- Explanation of what state means
- Recent transition history (last 5 transitions with reasons)

**Rationale**: Users understand why their score changes faster/slower
**Priority**: Must Have

#### FR-008: Vice Preferences Display
System MUST display discovered vice preferences:
- Each discovered vice category (8 total possible)
- Intensity level (1-5) with visual bar
- Only show vices with intensity > 0
- Brief explanation of each vice category

**Rationale**: Users understand how Nikita personalizes to them
**Priority**: Should Have

#### FR-009: Score History Visualization
System MUST visualize score trends:
- Line chart of composite score over time
- Time range selection (week, month, all time)
- Event markers (boss encounters, chapter advances, decay)
- Hover for exact score and timestamp

**Rationale**: Trends show relationship trajectory
**Priority**: Should Have

#### FR-010: Daily Summaries
System MUST display Nikita's daily recaps:
- List of daily summaries with date
- Shows: score_start, score_end, decay_applied
- Expandable to see summary_text (Nikita's voice)
- Emotional tone indicator (positive/neutral/negative)

**Rationale**: Nikita's perspective on the relationship
**Priority**: Should Have

#### FR-011: Conversation History (Read-Only)
System MUST provide read-only conversation history:
- Paginated list of past conversations
- Shows: platform, date, score_delta, emotional_tone
- Expandable to see messages
- CANNOT send messages from portal

**Rationale**: Review what happened, but gameplay stays in Telegram
**Priority**: Should Have

#### FR-012: Decay Warning
System MUST warn about upcoming decay:
- Grace period countdown (hours remaining)
- Current decay rate per chapter
- Projected score if no interaction
- Visual warning when < 6 hours remaining

**Rationale**: Helps users avoid unintentional relationship damage
**Priority**: Should Have

### Admin Dashboard

#### FR-013: Admin Authentication
System MUST verify admin access via email domain:
- Admin = email ends with `@silent-agents.com`
- No role column needed in database
- Function: `is_admin()` checks auth.users.email

**Rationale**: Simple, secure admin identification without database changes
**Priority**: Must Have

#### FR-014: User List
System MUST display all users for admin:
- Paginated table with key stats
- Columns: telegram_id, email, score, chapter, engagement_state, game_status
- Search by telegram_id, email, user_id
- Sort by any column

**Rationale**: Admin needs to find and monitor users
**Priority**: Must Have

#### FR-015: User Detail View
System MUST display complete user state for admin:
- All data from FR-004 through FR-012
- Plus: user_id, telegram_id, email, created_at
- Score history chart
- Recent conversations list

**Rationale**: Full visibility for debugging and testing
**Priority**: Must Have

#### FR-016: Game State Controls (MVP)
System MUST allow admin to modify game state:
- Set relationship_score (0-100) with reason (logs to score_history)
- Change chapter (1-5) with validation
- Toggle game_status (active/boss_fight/game_over/won)
- Change engagement_state enum
- Reset boss_attempts to 0
- Clear engagement_history / reset calibration

**Rationale**: Testing requires modifying game state
**Priority**: Must Have

#### FR-017: Prompt Logging
System MUST store all generated system prompts:
- New table: generated_prompts
- Fields: user_id, conversation_id, prompt_content, token_count, generation_time_ms, meta_prompt_template
- Log every MetaPromptService generation

**Rationale**: Debug prompts to understand Nikita's behavior
**Priority**: Must Have

#### FR-018: Prompt Viewer
System MUST allow admin to view stored prompts:
- Paginated list with filters (user_id, date range, template type)
- Click to view full prompt content
- Shows token count and generation time
- Search prompt content

**Rationale**: Admin needs to debug and review prompts
**Priority**: Should Have

#### FR-019: Admin Telemetry
System SHOULD display system health:
- API health status
- Database connection status
- Recent error counts (from logs)

**Rationale**: Quick health check for admin
**Priority**: Nice to Have

### General

#### FR-020: Real-Time Updates (Polling)
System MUST update dashboard data via polling:
- Default interval: 30 seconds
- Configurable: 5-60 seconds
- Shows "Last updated" timestamp
- Uses TanStack Query refetchInterval

**Rationale**: Near real-time without WebSocket complexity
**Priority**: Must Have

#### FR-021: Responsive Design
System MUST work across devices:
- Mobile-first design
- Desktop optimized
- Tablet supported
- Core functionality on all screen sizes

**Rationale**: Users access from any device
**Priority**: Must Have

#### FR-022: No Gameplay from Portal
System MUST NOT enable direct messaging:
- Cannot send text messages to Nikita
- Portal viewing does NOT reset decay timer
- Clear separation: Portal = viewing, Telegram = playing

**Rationale**: Maintain Telegram as sole interaction point
**Priority**: Must Have

---

## Non-Functional Requirements

### Performance
- Dashboard load: < 2 seconds
- Chart rendering: < 1 second
- Polling updates: < 500ms processing

### Reliability
- Availability: 99% uptime (Vercel)
- Data consistency: Portal reflects database truth
- Graceful degradation: Show cached data if API unavailable

### Security
- HTTPS only (Vercel enforces)
- Supabase Auth JWT validation
- RLS policies for data isolation
- Admin domain check (@silent-agents.com)

### Accessibility
- WCAG 2.1 AA compliance
- Screen reader compatible
- Keyboard navigable
- Sufficient color contrast

---

## User Stories

### US-1: Portal-First Registration (P1)
```
New user visits portal → enters email → receives magic link → creates account → sees default game state
```

**Acceptance Criteria**:
- AC-1.1: Email input validates format
- AC-1.2: Magic link sent within 30 seconds
- AC-1.3: User record created with score=50, chapter=1
- AC-1.4: user_metrics row created with defaults (50 each)
- AC-1.5: Dashboard displays immediately after auth

**Independent Test**: Register with new email, verify default state
**Dependencies**: Supabase Auth

---

### US-2: Telegram User Portal Access (P1)
```
Telegram user wants stats → visits portal → enters email → magic link → sees same game state
```

**Acceptance Criteria**:
- AC-2.1: Same email as Telegram registration works
- AC-2.2: Auth links to existing auth.users record
- AC-2.3: Dashboard shows current relationship_score, chapter
- AC-2.4: All data matches what Telegram gameplay produced

**Independent Test**: Play on Telegram, login to portal, verify same data
**Dependencies**: Existing Telegram user

---

### US-3: View Full Metrics Dashboard (P1)
```
User logs in → views dashboard → sees score, chapter, ALL 4 hidden metrics with weights
```

**Acceptance Criteria**:
- AC-3.1: relationship_score displayed (0-100)
- AC-3.2: Chapter with name and boss progress
- AC-3.3: Intimacy (30%), Passion (25%), Trust (25%), Secureness (20%)
- AC-3.4: Composite formula visible
- AC-3.5: Data refreshes every 30 seconds

**Independent Test**: Verify metrics match user_metrics table
**Dependencies**: US-1 or US-2

---

### US-4: View Engagement State (P1)
```
User views dashboard → sees engagement state → understands multiplier impact
```

**Acceptance Criteria**:
- AC-4.1: Current state displayed (6 possible states)
- AC-4.2: Multiplier shown (0.2x - 1.0x)
- AC-4.3: State explanation text
- AC-4.4: Recent transitions shown with reasons

**Independent Test**: Verify state matches engagement_state table
**Dependencies**: US-1 or US-2

---

### US-5: View Vice Preferences (P2)
```
User views dashboard → sees discovered vices → understands personalization
```

**Acceptance Criteria**:
- AC-5.1: Each discovered vice shown with category name
- AC-5.2: Intensity level (1-5) displayed visually
- AC-5.3: Only vices with intensity > 0 shown
- AC-5.4: Vice category descriptions available

**Independent Test**: Verify vices match user_vice_preferences table
**Dependencies**: User with vices discovered

---

### US-6: View Score History (P2)
```
User wants trends → views history → sees score over time with events
```

**Acceptance Criteria**:
- AC-6.1: Line chart of score over time
- AC-6.2: Time range selector (week/month/all)
- AC-6.3: Events marked (boss_pass, decay, etc.)
- AC-6.4: Hover shows exact values

**Independent Test**: Verify chart data matches score_history table
**Dependencies**: User with score history

---

### US-7: View Conversation History (P2)
```
User reviews history → browses conversations → sees score impact
```

**Acceptance Criteria**:
- AC-7.1: Paginated conversation list
- AC-7.2: Shows platform, date, score_delta
- AC-7.3: Expand to see messages
- AC-7.4: No send button (read-only enforced)

**Independent Test**: Verify conversations match database
**Dependencies**: User with conversations

---

### US-8: View Decay Status (P2)
```
User checks decay → sees countdown → sees projected score
```

**Acceptance Criteria**:
- AC-8.1: Grace period countdown displayed
- AC-8.2: Current decay rate shown
- AC-8.3: Projected score if no interaction
- AC-8.4: Warning styling when < 6 hours

**Independent Test**: Verify decay calculation matches game engine
**Dependencies**: US-1 or US-2

---

### US-9: Admin User List (P1 Admin)
```
Admin logs in → sees all users → can search and filter
```

**Acceptance Criteria**:
- AC-9.1: Admin verified by @silent-agents.com email
- AC-9.2: Paginated user list with stats
- AC-9.3: Search by telegram_id, email, user_id
- AC-9.4: Sort by any column

**Independent Test**: Login with admin email, verify access
**Dependencies**: Admin account

---

### US-10: Admin View User Detail (P1 Admin)
```
Admin selects user → sees complete state → all data accessible
```

**Acceptance Criteria**:
- AC-10.1: Full user record displayed
- AC-10.2: All metrics, vices, engagement visible
- AC-10.3: Score history chart
- AC-10.4: Recent conversations

**Independent Test**: Select any user, verify complete data
**Dependencies**: US-9

---

### US-11: Admin Modify Game State (P1 Admin)
```
Admin needs to test → modifies user state → changes take effect
```

**Acceptance Criteria**:
- AC-11.1: Set score (0-100) with reason → logs to score_history
- AC-11.2: Change chapter (1-5) → validates constraints
- AC-11.3: Change engagement_state → updates immediately
- AC-11.4: Reset boss_attempts → sets to 0
- AC-11.5: Clear engagement_history → deletes records

**Independent Test**: Modify state, verify in database
**Dependencies**: US-10

---

### US-12: Admin View Prompts (P2 Admin)
```
Admin debugs → views generated prompts → sees content and stats
```

**Acceptance Criteria**:
- AC-12.1: Paginated prompt list
- AC-12.2: Filter by user, date, template type
- AC-12.3: Click to view full content
- AC-12.4: Shows token_count, generation_time_ms

**Independent Test**: Verify prompts match generated_prompts table
**Dependencies**: Prompt logging implemented

---

### US-13: Account Linking (P3)
```
Portal user links Telegram → settings → generates code → sends to bot
```

**Acceptance Criteria**:
- AC-13.1: "Link Telegram" generates unique code
- AC-13.2: Code expires in 10 minutes
- AC-13.3: Bot validates code and links telegram_id
- AC-13.4: Both platforms share game state

**Independent Test**: Link accounts, verify shared state
**Dependencies**: Telegram bot linkage command

---

## Database Schema

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

ALTER TABLE generated_prompts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users see own prompts" ON generated_prompts
    FOR SELECT USING (auth.uid() = user_id);
```

### Admin Function

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

### Admin RLS Bypass

```sql
-- Apply to all tables admin needs to read
CREATE POLICY "Admin reads all users" ON users
    FOR SELECT USING (auth.uid() = id OR is_admin());

CREATE POLICY "Admin modifies users" ON users
    FOR UPDATE USING (is_admin());

-- Repeat for: user_metrics, engagement_state, engagement_history,
-- conversations, score_history, daily_summaries, user_vice_preferences
```

---

## API Endpoints

### Portal Routes (/api/v1/portal/*)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | /stats | Full dashboard stats | User |
| GET | /metrics | 4 hidden metrics | User |
| GET | /engagement | Engagement state + history | User |
| GET | /vices | Vice preferences | User |
| GET | /score-history | Score history for charts | User |
| GET | /daily-summaries | Daily summaries list | User |
| GET | /conversations | Conversation list (paginated) | User |
| GET | /conversations/{id} | Conversation detail | User |
| GET | /decay | Decay status | User |
| PUT | /settings | Update user settings | User |
| POST | /link-telegram | Generate linking code | User |
| DELETE | /account | Delete account | User |

### Admin Routes (/api/v1/admin/*)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | /users | List all users (paginated) | Admin |
| GET | /users/{id} | User detail | Admin |
| GET | /users/{id}/metrics | User metrics | Admin |
| GET | /users/{id}/engagement | User engagement | Admin |
| GET | /users/{id}/vices | User vices | Admin |
| GET | /users/{id}/conversations | User conversations | Admin |
| PUT | /users/{id}/score | Set score | Admin |
| PUT | /users/{id}/chapter | Set chapter | Admin |
| PUT | /users/{id}/status | Set game_status | Admin |
| PUT | /users/{id}/engagement | Set engagement_state | Admin |
| POST | /users/{id}/reset-boss | Reset boss_attempts | Admin |
| POST | /users/{id}/clear-engagement | Clear engagement history | Admin |
| GET | /prompts | List prompts (filtered) | Admin |
| GET | /prompts/{id} | Prompt detail | Admin |
| GET | /health | System health | Admin |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14+ (App Router) |
| UI Components | shadcn/ui + Tailwind CSS |
| Charts | Recharts |
| Auth | Supabase Auth (magic link) |
| State | TanStack Query |
| API Client | Supabase JS Client |
| Hosting | Vercel |
| Database | Supabase (existing) |

---

## Infrastructure Dependencies

| Spec | Dependency | Blocking? |
|------|------------|-----------|
| 009-database | Tables exist | No |
| 010-api | API patterns | No |
| 013-configuration | YAML configs | No |
| 014-engagement | Engagement tables | No |
| 003-scoring | Score display | Soft |
| 005-decay | Decay calculations | Soft |

---

## Scope

### In-Scope
- Dual authentication (portal-first + Telegram-first)
- Full transparency user dashboard
- Admin dashboard with controls
- Prompt logging and viewing
- Responsive design
- Vercel deployment

### Out-of-Scope
- Direct messaging to Nikita (Telegram only)
- Voice call initiation (defer to 007-voice-agent)
- Payment/subscription management
- Social features (leaderboards)
- Mobile native app (web only)
- Real-time WebSocket (use polling)

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Users obsess over metrics | Medium | Medium | Show trends, not decimals |
| Portal replaces Telegram | Low | High | No messaging, clear guidance |
| Admin abuse | Low | High | Domain-restricted, audit logs |
| Prompt storage costs | Low | Medium | Auto-delete after 90 days |

---

## Success Metrics

- Portal adoption: 60%+ of active users visit weekly
- Dashboard load: < 2 seconds
- Admin effectiveness: State changes work first try
- Data accuracy: 100% match between portal and database

---

**Version**: 2.0
**Last Updated**: 2025-12-04

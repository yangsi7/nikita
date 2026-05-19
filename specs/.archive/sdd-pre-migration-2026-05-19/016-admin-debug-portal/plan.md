---
plan_id: "016-admin-debug-portal"
status: "draft"
owner: "claude-code"
created_at: "2025-12-12"
updated_at: "2025-12-12"
type: "plan"
naming_pattern: "016-admin-debug-portal/plan.md"
---

# Implementation Plan: Admin Debug Portal

## Goal

**Objective:** Create an admin debug portal for Nikita developers to visualize game state, monitor scheduled jobs, and debug user issues.

**Success Definition:** Developers with `@silent-agents.com` emails can access `/admin` routes to view system overview, user state machines, and job status within 3 seconds load time.

**Based On:** [specs/016-admin-debug-portal/spec.md](spec.md)

---

## Summary

**Overview**: Implement a read-only admin debug portal with backend endpoints for system stats, user debugging, and job monitoring, plus frontend pages using card-based visualization. Access restricted via email domain validation on JWT tokens.

**Tech Stack**:
- **Frontend**: Next.js 16, React Query, shadcn-style components
- **Backend**: FastAPI, SQLAlchemy async, Pydantic schemas
- **Database**: Supabase PostgreSQL + new job_executions table
- **Testing**: pytest (backend), vitest (frontend)
- **Deployment**: Cloud Run (backend), Vercel (portal)

**Deliverables**:
1. Admin auth dependency - email domain validation (`@silent-agents.com`)
2. Job execution tracking - model, repository, and logging
3. Admin debug API - 5 endpoints for system/users/jobs
4. Frontend admin portal - dashboard, user browser, user detail, jobs pages
5. Admin components - 7 card components for visualization

---

## Technical Context

### Existing Architecture (Intelligence Evidence)

**Intelligence Queries Executed**:
```bash
# Portal patterns
project-intel.mjs --search "portal dashboard" --type tsx --json
# Output: portal/src/app/dashboard/page.tsx, portal/src/hooks/use-dashboard-data.ts

# Auth dependency
project-intel.mjs --search "auth dependency" --type py --json
# Output: nikita/api/dependencies/auth.py (get_current_user_id pattern)

# Repository patterns
project-intel.mjs --search "repository" --type py --json
# Output: 7 repositories in nikita/db/repositories/
```

**Patterns Discovered** (CoD^Σ Evidence):
- **Auth Pattern**: `get_current_user_id()` @ `nikita/api/dependencies/auth.py:17-88`
  - Usage: JWT decode → validate → extract user_id
  - Applicability: Extend with `get_current_admin_user()` adding email domain check

- **Repository Pattern**: `EngagementRepository` @ `nikita/db/repositories/engagement_repository.py`
  - Usage: SQLAlchemy async session → CRUD operations
  - Applicability: Create `JobExecutionRepository` following same pattern

- **Portal API Pattern**: `portal.py` @ `nikita/api/routes/portal.py`
  - Usage: Pydantic schemas → JSON responses with float conversion
  - Applicability: Use same pattern for admin_debug.py endpoints

- **React Query Hook Pattern**: `use-dashboard-data.ts` @ `portal/src/hooks/use-dashboard-data.ts`
  - Usage: useQuery with refetchInterval for polling
  - Applicability: Create `use-admin-data.ts` with 30-60s polling

**External Research** (MCP Queries):
- **Supabase JWT**: Email stored in `payload["email"]` claim
  - Verified: Supabase JWT includes email for authenticated users

**CoD^Σ Evidence Chain**:
```
spec_requirements ∘ intel_patterns → tech_decisions
Evidence: spec.md + auth.py:17-88 + portal.py + engagement_repository.py → plan.md
```

---

## Constitution Check (Article VI)

**Constitutional Authority**: Article VI (Simplicity & Anti-Abstraction)

### Pre-Design Gates

```
Gate₁: Project Count (≤3)
  Status: PASS ✓
  Count: 1 project (admin portal within existing nikita)
  Details: All code within existing nikita backend + portal frontend
  Decision: PROCEED

Gate₂: Abstraction Layers (≤2 per concept)
  Status: PASS ✓
  Details: Model → Repository → Endpoint (standard 2-layer)
  Decision: PROCEED

Gate₃: Framework Trust (use directly)
  Status: PASS ✓
  Details: Using FastAPI dependencies directly, no wrapper
  Decision: PROCEED
```

**Overall Pre-Design Gate**: PASS ✓

---

## Architecture (CoD^Σ)

### Component Breakdown

**System Flow**:
```
Admin → Frontend → API → Repository → Database
  ↓        ↓         ↓         ↓           ↓
Email   /admin/*  Auth_Check  Query     State_Data
```

**Access Control Flow**:
```
JWT → decode → email ∈ *@silent-agents.com → isAdmin ⇒ access
                  ↓
              ¬@silent-agents.com → 403 Forbidden
```

**Dependencies** (CoD^Σ Notation):
```
AdminAuth ⇐ Auth ⇐ JWT
JobExecution ⊥ User (independent tables)
AdminEndpoints → [UserRepo, EngagementRepo, MetricsRepo, JobExecRepo]
Frontend → AdminAPI → Database
```

**Data Flow**:
```
Request ≫ Auth ≫ Query → Aggregate → Response
  ↓        ↓       ↓         ↓          ↓
Token   Email  SQL_ORM  Pydantic    JSON
```

**Modules**:
1. **Admin Auth**: `nikita/api/dependencies/auth.py`
   - Purpose: Validate admin email domain
   - Exports: `get_current_admin_user()`
   - Imports: JWT decode, settings

2. **Job Execution**: `nikita/db/models/job_execution.py`
   - Purpose: Track scheduled job runs
   - Exports: `JobExecution` model
   - Imports: SQLAlchemy Base

3. **Admin API**: `nikita/api/routes/admin_debug.py`
   - Purpose: Debug endpoints for admin
   - Exports: Router with 5 endpoints
   - Imports: All repositories, admin auth

4. **Frontend Admin**: `portal/src/app/admin/`
   - Purpose: Admin dashboard UI
   - Exports: Admin pages
   - Imports: API client, components

---

## User Story Implementation Plan

### US-1: Admin Authentication (Priority: P1 - Must-Have)

**Goal**: Restrict debug portal access to `@silent-agents.com` emails

**Acceptance Criteria** (from spec.md):
- AC-FR001-001: @silent-agents.com email → admin dashboard access
- AC-FR001-002: Other emails → 403 Forbidden
- AC-FR001-003: Unauthenticated → redirect to login

**Implementation Approach**:
1. Add `get_current_admin_user()` to `auth.py` extending `get_current_user_id()`
2. Extract email from JWT payload, validate domain ends with `@silent-agents.com`
3. Frontend layout checks email domain, redirects non-admins

**Evidence**: Based on pattern at `nikita/api/dependencies/auth.py:17-88`

---

### US-2: System Overview Dashboard (Priority: P1 - Must-Have)

**Goal**: Display aggregate statistics about all users

**Acceptance Criteria** (from spec.md):
- AC-FR002-001: User counts by game_status displayed
- AC-FR002-002: User distribution by chapter (1-5) displayed
- AC-FR002-003: User distribution by engagement state (6 states) displayed
- AC-FR010-001: Active user counts (24h, 7d, 30d) displayed

**Implementation Approach**:
1. Create `/admin/debug/system` endpoint with aggregate queries
2. Create `SystemOverviewCard` component with stat displays
3. Build dashboard page composing overview cards

**Evidence**: Based on pattern at `nikita/api/routes/portal.py`

---

### US-3: User Browser and Search (Priority: P1 - Must-Have)

**Goal**: Paginated user list with filtering

**Acceptance Criteria** (from spec.md):
- AC-FR003-001: Paginated user list (50 per page)
- AC-FR003-002: Filter by game_status
- AC-FR003-003: Filter by chapter
- AC-FR003-004: Click user → navigate to detail

**Implementation Approach**:
1. Create `/admin/debug/users` endpoint with pagination + filters
2. Create user list page with filter controls
3. Link rows to user detail pages

**Evidence**: Based on pattern at `nikita/db/repositories/user_repository.py`

---

### US-4: User State Machine Visualization (Priority: P1 - Must-Have)

**Goal**: Display engagement and chapter state for a user

**Acceptance Criteria** (from spec.md):
- AC-FR005-001: Current engagement state and multiplier
- AC-FR005-002: Counter values (consecutive_in_zone, clingy_days, distant_days)
- AC-FR005-003: Recent state transitions (last 5) with timestamps
- AC-FR006-001: Current chapter, name, relationship score
- AC-FR006-002: Boss threshold, progress %, boss attempts
- AC-FR006-003: Decay rate and grace period hours

**Implementation Approach**:
1. Create `/admin/debug/state-machines/{user_id}` endpoint
2. Create `EngagementStateCard` and `ChapterProgressCard` components
3. Compose into user detail page

**Evidence**: Based on pattern at `nikita/engine/engagement/state_machine.py`

---

### US-5: User Timing and Scheduling (Priority: P1 - Must-Have)

**Goal**: Display timing info and decay countdowns

**Acceptance Criteria** (from spec.md):
- AC-FR009-001: last_interaction_at timestamp displayed
- AC-FR009-002: Hours since interaction calculated
- AC-FR009-003: Grace period remaining displayed
- AC-FR009-004: Decay countdown ("20h 30m until decay")
- AC-FR009-005: "Currently decaying" indicator when past grace

**Implementation Approach**:
1. Create `/admin/debug/users/{user_id}` endpoint with timing calculations
2. Create `UserTimingCard` component with countdown display
3. Calculate decay timing using chapter-specific grace periods

**Evidence**: Based on pattern at `nikita/engine/decay/calculator.py`

---

### US-6: Scheduled Job Monitoring (Priority: P1 - Must-Have)

**Goal**: Track and display job execution history

**Acceptance Criteria** (from spec.md):
- AC-FR008-001: All 5 job types listed
- AC-FR008-002: Last run timestamp with relative time
- AC-FR008-003: Status (running, completed, failed)
- AC-FR008-004: Duration_ms of last run
- AC-FR008-005: Error indicator for failed jobs

**Implementation Approach**:
1. Create `JobExecution` model and migration
2. Add logging to task endpoints in `tasks.py`
3. Create `/admin/debug/jobs` endpoint
4. Create `JobStatusCard` component and jobs page

**Evidence**: Based on pattern at `nikita/api/routes/tasks.py`

---

### US-7: Vice Profile Visualization (Priority: P2 - Important)

**Goal**: Display vice profile data

**Acceptance Criteria** (from spec.md):
- AC-FR007-001: Top vices (up to 3) with intensities
- AC-FR007-002: Expression level based on chapter
- AC-FR007-003: Total signals detected count

**Implementation Approach**:
1. Query vice data in user detail endpoint
2. Create `ViceProfileCard` component
3. Add to user detail page

**Evidence**: Based on pattern at `nikita/engine/vice/service.py`

---

### US-8: User Metrics Display (Priority: P2 - Important)

**Goal**: Display 4 relationship metrics

**Acceptance Criteria** (from spec.md):
- AC-FR004-001: All 4 metrics (intimacy, passion, trust, secureness) 0-100
- AC-FR004-002: Compact grid format

**Implementation Approach**:
1. Include metrics in user detail endpoint response
2. Display in existing user detail layout

**Evidence**: Based on pattern at `nikita/db/models/user.py:UserMetrics`

---

## Tasks

**Organization**: Tasks map to user stories for SDD progressive delivery

**CoD^Σ Dependencies**: → (sequential), ⊥ (independent), ⇒ (causal)

### Phase 1: Backend Foundation

#### T1.1: [US-1] Create Admin Auth Dependency
- **ID:** T1.1
- **User Story**: US-1 (Admin Authentication)
- **Owner:** claude-code
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): None (foundation)
- **Estimated Complexity:** Low

**Acceptance Criteria**:
- [ ] AC-FR001-001: @silent-agents.com email gets admin access
- [ ] AC-FR001-002: Other emails receive 403 Forbidden

**Implementation Notes:**
- **File**: `nikita/api/dependencies/auth.py`
- **Pattern Evidence**: Extend `get_current_user_id()` at auth.py:17-88
- **Testing**: `tests/api/dependencies/test_auth_admin.py`

---

#### T1.2: [US-6] Create JobExecution Model
- **ID:** T1.2
- **User Story**: US-6 (Job Monitoring)
- **Owner:** claude-code
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T1.1 ⊥ T1.2 (independent)
- **Estimated Complexity:** Low

**Acceptance Criteria**:
- [ ] AC-FR008-001: Model supports all 5 job types
- [ ] AC-FR008-003: Model has status field (running, completed, failed)

**Implementation Notes:**
- **File**: `nikita/db/models/job_execution.py`
- **Pattern Evidence**: Based on existing models in `nikita/db/models/`
- **Testing**: Model instantiation tests

---

#### T1.3: [US-6] Create JobExecution Migration
- **ID:** T1.3
- **User Story**: US-6 (Job Monitoring)
- **Owner:** claude-code
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T1.2 → T1.3 (requires model)
- **Estimated Complexity:** Low

**Acceptance Criteria**:
- [ ] job_executions table created
- [ ] Index on (job_name, started_at DESC) created

**Implementation Notes:**
- **Migration**: Via Supabase MCP `apply_migration`
- **Testing**: Run migration, verify table exists

---

#### T1.4: [US-6] Create JobExecution Repository
- **ID:** T1.4
- **User Story**: US-6 (Job Monitoring)
- **Owner:** claude-code
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T1.3 → T1.4 (requires table)
- **Estimated Complexity:** Low

**Acceptance Criteria**:
- [ ] CRUD operations for job executions
- [ ] Query latest by job_name

**Implementation Notes:**
- **File**: `nikita/db/repositories/job_execution_repository.py`
- **Pattern Evidence**: Based on `engagement_repository.py`
- **Testing**: `tests/db/repositories/test_job_execution_repository.py`

---

#### T1.5: Register Router in main.py
- **ID:** T1.5
- **User Story**: N/A (infrastructure)
- **Owner:** claude-code
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T1.1 → T1.5 (requires auth)
- **Estimated Complexity:** Low

**Acceptance Criteria**:
- [ ] admin_debug router registered at `/admin/debug`

**Implementation Notes:**
- **File**: `nikita/api/main.py`
- **Pattern Evidence**: Existing router registration pattern

---

### Phase 2: Backend Endpoints

#### T2.1: [US-2] Implement /admin/debug/system Endpoint
- **ID:** T2.1
- **User Story**: US-2 (System Overview)
- **Owner:** claude-code
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T1.5 → T2.1 (requires router)
- **Estimated Complexity:** Medium

**Acceptance Criteria**:
- [ ] AC-FR002-001: User counts by game_status returned
- [ ] AC-FR002-002: User distribution by chapter returned
- [ ] AC-FR002-003: User distribution by engagement state returned
- [ ] AC-FR010-001: Active user counts (24h, 7d, 30d) returned

**Implementation Notes:**
- **File**: `nikita/api/routes/admin_debug.py`
- **Schemas**: `nikita/api/schemas/admin_debug.py`
- **Testing**: `tests/api/routes/test_admin_debug.py`

---

#### T2.2: [US-6] Implement /admin/debug/jobs Endpoint
- **ID:** T2.2
- **User Story**: US-6 (Job Monitoring)
- **Owner:** claude-code
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T1.4 → T2.2 (requires repository)
- **Estimated Complexity:** Medium

**Acceptance Criteria**:
- [ ] AC-FR008-001: All 5 job types listed
- [ ] AC-FR008-002: Last run with relative time
- [ ] AC-FR008-003: Status field returned
- [ ] AC-FR008-004: Duration_ms returned
- [ ] AC-FR008-005: Error info for failed jobs

**Implementation Notes:**
- **File**: `nikita/api/routes/admin_debug.py`
- **Testing**: `tests/api/routes/test_admin_debug.py`

---

#### T2.3: [US-3] Implement /admin/debug/users Endpoint
- **ID:** T2.3
- **User Story**: US-3 (User Browser)
- **Owner:** claude-code
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T1.5 → T2.3 (requires router)
- **Estimated Complexity:** Medium

**Acceptance Criteria**:
- [ ] AC-FR003-001: Paginated list (50 per page)
- [ ] AC-FR003-002: Filter by game_status
- [ ] AC-FR003-003: Filter by chapter

**Implementation Notes:**
- **File**: `nikita/api/routes/admin_debug.py`
- **Testing**: `tests/api/routes/test_admin_debug.py`

---

#### T2.4: [US-4, US-5, US-7, US-8] Implement /admin/debug/users/{user_id} Endpoint
- **ID:** T2.4
- **User Story**: US-4, US-5, US-7, US-8 (User Detail)
- **Owner:** claude-code
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T2.3 → T2.4 (requires user list)
- **Estimated Complexity:** High

**Acceptance Criteria**:
- [ ] AC-FR004-001: All 4 metrics returned
- [ ] AC-FR005-001: Engagement state and multiplier
- [ ] AC-FR005-002: Counter values
- [ ] AC-FR006-001: Chapter, name, score
- [ ] AC-FR006-002: Boss threshold, progress, attempts
- [ ] AC-FR006-003: Decay rate, grace period
- [ ] AC-FR007-001: Top vices with intensities
- [ ] AC-FR007-002: Expression level
- [ ] AC-FR009-001: last_interaction_at
- [ ] AC-FR009-002: Hours since interaction
- [ ] AC-FR009-003: Grace period remaining
- [ ] AC-FR009-004: Decay countdown
- [ ] AC-FR009-005: "Currently decaying" indicator

**Implementation Notes:**
- **File**: `nikita/api/routes/admin_debug.py`
- **Queries**: Join user, metrics, engagement, vice tables
- **Testing**: `tests/api/routes/test_admin_debug.py`

---

#### T2.5: [US-4] Implement /admin/debug/state-machines/{user_id} Endpoint
- **ID:** T2.5
- **User Story**: US-4 (State Machines)
- **Owner:** claude-code
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T2.4 ⊥ T2.5 (can parallel)
- **Estimated Complexity:** Medium

**Acceptance Criteria**:
- [ ] AC-FR005-003: Recent transitions (last 5) with timestamps

**Implementation Notes:**
- **File**: `nikita/api/routes/admin_debug.py`
- **Query**: engagement_state_history if exists, or compute from logs
- **Testing**: `tests/api/routes/test_admin_debug.py`

---

#### T2.6: [US-6] Add Job Logging to Task Endpoints
- **ID:** T2.6
- **User Story**: US-6 (Job Monitoring)
- **Owner:** claude-code
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T1.4 → T2.6 (requires repository)
- **Estimated Complexity:** Medium

**Acceptance Criteria**:
- [ ] All 5 task endpoints log start/end to job_executions
- [ ] Duration calculated and stored
- [ ] Error info captured on failure

**Implementation Notes:**
- **File**: `nikita/api/routes/tasks.py`
- **Testing**: `tests/api/routes/test_tasks_logging.py`

---

### Phase 3: Frontend Foundation

#### T3.1: [US-1] Create Admin Layout with Auth Check
- **ID:** T3.1
- **User Story**: US-1 (Admin Auth)
- **Owner:** claude-code
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T2.1 → T3.1 (requires backend)
- **Estimated Complexity:** Medium

**Acceptance Criteria**:
- [ ] AC-FR001-001: @silent-agents.com users see admin dashboard
- [ ] AC-FR001-003: Unauthenticated redirected to login

**Implementation Notes:**
- **File**: `portal/src/app/admin/layout.tsx`
- **Pattern**: Check session email domain
- **Testing**: Manual E2E test

---

#### T3.2: Create Admin API Client
- **ID:** T3.2
- **User Story**: N/A (infrastructure)
- **Owner:** claude-code
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T2.4 → T3.2 (requires endpoints)
- **Estimated Complexity:** Low

**Acceptance Criteria**:
- [ ] Admin API client with all endpoint functions

**Implementation Notes:**
- **Files**: `portal/src/lib/api/admin-client.ts`, `portal/src/lib/api/admin-types.ts`
- **Pattern Evidence**: Based on `client.ts`

---

#### T3.3: Create Admin Data Hooks
- **ID:** T3.3
- **User Story**: N/A (infrastructure)
- **Owner:** claude-code
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T3.2 → T3.3 (requires client)
- **Estimated Complexity:** Low

**Acceptance Criteria**:
- [ ] useSystemOverview, useAdminUsers, useUserDetail, useJobStatus hooks
- [ ] Polling intervals: 30s for jobs, 60s for users

**Implementation Notes:**
- **File**: `portal/src/hooks/use-admin-data.ts`
- **Pattern Evidence**: Based on `use-dashboard-data.ts`

---

#### T3.4: Create AdminNavigation Component
- **ID:** T3.4
- **User Story**: N/A (infrastructure)
- **Owner:** claude-code
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T3.1 → T3.4 (requires layout)
- **Estimated Complexity:** Low

**Acceptance Criteria**:
- [ ] Navigation links for dashboard, users, jobs

**Implementation Notes:**
- **File**: `portal/src/components/admin/AdminNavigation.tsx`

---

### Phase 4: Frontend Components

#### T4.1: [US-2] Create SystemOverviewCard Component
- **ID:** T4.1
- **User Story**: US-2 (System Overview)
- **Owner:** claude-code
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T3.3 → T4.1 (requires hooks)
- **Estimated Complexity:** Medium

**Acceptance Criteria**:
- [ ] AC-FR002-001: User counts by status displayed
- [ ] AC-FR002-002: Chapter distribution displayed
- [ ] AC-FR002-003: Engagement state distribution displayed
- [ ] AC-FR010-001: Active user counts displayed

**Implementation Notes:**
- **File**: `portal/src/components/admin/SystemOverviewCard.tsx`

---

#### T4.2: [US-4] Create EngagementStateCard Component
- **ID:** T4.2
- **User Story**: US-4 (State Machines)
- **Owner:** claude-code
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T4.1 ⊥ T4.2 (parallel)
- **Estimated Complexity:** Medium

**Acceptance Criteria**:
- [ ] AC-FR005-001: State and multiplier
- [ ] AC-FR005-002: Counter values
- [ ] AC-FR005-003: Recent transitions

**Implementation Notes:**
- **File**: `portal/src/components/admin/EngagementStateCard.tsx`

---

#### T4.3: [US-4] Create ChapterProgressCard Component
- **ID:** T4.3
- **User Story**: US-4 (State Machines)
- **Owner:** claude-code
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T4.1 ⊥ T4.3 (parallel)
- **Estimated Complexity:** Medium

**Acceptance Criteria**:
- [ ] AC-FR006-001: Chapter, name, score
- [ ] AC-FR006-002: Boss threshold, progress, attempts
- [ ] AC-FR006-003: Decay rate, grace period

**Implementation Notes:**
- **File**: `portal/src/components/admin/ChapterProgressCard.tsx`

---

#### T4.4: [US-7] Create ViceProfileCard Component
- **ID:** T4.4
- **User Story**: US-7 (Vice Profile)
- **Owner:** claude-code
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T4.1 ⊥ T4.4 (parallel)
- **Estimated Complexity:** Medium

**Acceptance Criteria**:
- [ ] AC-FR007-001: Top vices with intensities
- [ ] AC-FR007-002: Expression level
- [ ] AC-FR007-003: Total signals count

**Implementation Notes:**
- **File**: `portal/src/components/admin/ViceProfileCard.tsx`

---

#### T4.5: [US-6] Create JobStatusCard Component
- **ID:** T4.5
- **User Story**: US-6 (Job Monitoring)
- **Owner:** claude-code
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T4.1 ⊥ T4.5 (parallel)
- **Estimated Complexity:** Medium

**Acceptance Criteria**:
- [ ] AC-FR008-002: Last run with relative time
- [ ] AC-FR008-003: Status badge
- [ ] AC-FR008-004: Duration
- [ ] AC-FR008-005: Error indicator

**Implementation Notes:**
- **File**: `portal/src/components/admin/JobStatusCard.tsx`

---

#### T4.6: [US-5] Create UserTimingCard Component
- **ID:** T4.6
- **User Story**: US-5 (Timing)
- **Owner:** claude-code
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T4.1 ⊥ T4.6 (parallel)
- **Estimated Complexity:** Medium

**Acceptance Criteria**:
- [ ] AC-FR009-001: last_interaction_at
- [ ] AC-FR009-002: Hours since interaction
- [ ] AC-FR009-003: Grace period remaining
- [ ] AC-FR009-004: Decay countdown
- [ ] AC-FR009-005: Currently decaying indicator

**Implementation Notes:**
- **File**: `portal/src/components/admin/UserTimingCard.tsx`

---

### Phase 5: Page Integration

#### T5.1: [US-2] Build Admin Dashboard Page
- **ID:** T5.1
- **User Story**: US-2 (System Overview)
- **Owner:** claude-code
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T4.1 → T5.1 (requires components)
- **Estimated Complexity:** Medium

**Acceptance Criteria**:
- [ ] Dashboard shows system overview cards
- [ ] Page loads within 3 seconds

**Implementation Notes:**
- **File**: `portal/src/app/admin/page.tsx`

---

#### T5.2: [US-3] Build User List Page
- **ID:** T5.2
- **User Story**: US-3 (User Browser)
- **Owner:** claude-code
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T5.1 → T5.2 (requires dashboard)
- **Estimated Complexity:** Medium

**Acceptance Criteria**:
- [ ] AC-FR003-001: Paginated list
- [ ] AC-FR003-002: game_status filter
- [ ] AC-FR003-003: Chapter filter
- [ ] AC-FR003-004: Click navigates to detail

**Implementation Notes:**
- **File**: `portal/src/app/admin/users/page.tsx`

---

#### T5.3: [US-4, US-5, US-7, US-8] Build User Detail Page
- **ID:** T5.3
- **User Story**: US-4, US-5, US-7, US-8
- **Owner:** claude-code
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T4.2 ∧ T4.3 ∧ T4.4 ∧ T4.6 → T5.3 (requires all cards)
- **Estimated Complexity:** High

**Acceptance Criteria**:
- [ ] All state machine cards displayed
- [ ] All timing info displayed
- [ ] Vice profile displayed
- [ ] Metrics displayed

**Implementation Notes:**
- **File**: `portal/src/app/admin/users/[id]/page.tsx`

---

#### T5.4: [US-6] Build Jobs Page
- **ID:** T5.4
- **User Story**: US-6 (Job Monitoring)
- **Owner:** claude-code
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T4.5 → T5.4 (requires JobStatusCard)
- **Estimated Complexity:** Medium

**Acceptance Criteria**:
- [ ] All 5 job types displayed
- [ ] Status, duration, timestamps shown
- [ ] 30s auto-refresh

**Implementation Notes:**
- **File**: `portal/src/app/admin/jobs/page.tsx`

---

#### T5.5: Add Conditional Admin Link to Navigation
- **ID:** T5.5
- **User Story**: US-1 (Admin Auth)
- **Owner:** claude-code
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T5.1 → T5.5 (requires dashboard)
- **Estimated Complexity:** Low

**Acceptance Criteria**:
- [ ] @silent-agents.com users see "Admin" link in main nav
- [ ] Other users don't see the link

**Implementation Notes:**
- **File**: `portal/src/components/layout/Navigation.tsx`

---

## Dependencies

### Task Dependency Graph (CoD^Σ)
```
Phase 1 (Foundation):
T1.1 → T1.5               (auth → router)
T1.2 → T1.3 → T1.4        (model → migration → repository)
T1.1 ⊥ T1.2               (parallel)

Phase 2 (Endpoints):
T1.5 → [T2.1, T2.3]       (router → system, users endpoints)
T1.4 → [T2.2, T2.6]       (job repo → jobs endpoint, task logging)
T2.3 → T2.4               (users list → user detail)
T2.4 ⊥ T2.5               (parallel)

Phase 3 (Frontend Foundation):
T2.1 → T3.1               (backend → layout)
T2.4 → T3.2 → T3.3        (endpoints → client → hooks)
T3.1 → T3.4               (layout → nav)

Phase 4 (Components):
T3.3 → [T4.1, T4.2, T4.3, T4.4, T4.5, T4.6]  (hooks → all cards in parallel)

Phase 5 (Pages):
T4.1 → T5.1               (overview card → dashboard)
T5.1 → T5.2               (dashboard → user list)
[T4.2, T4.3, T4.4, T4.6] → T5.3  (cards → user detail)
T4.5 → T5.4               (job card → jobs page)
T5.1 → T5.5               (dashboard → nav link)
```

**Critical Path**: T1.1 → T1.5 → T2.1 → T3.1 → T3.2 → T3.3 → T4.1 → T5.1

**Parallelizable**:
- Phase 1: {T1.1} ∥ {T1.2, T1.3, T1.4}
- Phase 2: {T2.1, T2.3} ∥ {T2.2, T2.6}
- Phase 4: All T4.x components parallel

### External Dependencies
- **Supabase JWT**: Email claim available in JWT payload
- **shadcn**: Components via MCP tool
- **React Query**: Already installed in portal

---

## Risks (CoD^Σ)

### Risk 1: JWT Missing Email Claim
- **Likelihood (p):** Low (0.2) - Supabase standard includes email
- **Impact:** High (8) - Admin auth completely broken
- **Risk Score:** r = 1.6
- **Mitigation**:
  ```
  Risk → Test JWT → Fallback to user query → Admin verified
  ```
  - Test JWT decoding in dev before implementation
  - Fallback: Query user table for email if not in JWT

### Risk 2: Performance with Large User Counts
- **Likelihood (p):** Low (0.2) - Current user count < 1000
- **Impact:** Medium (5) - Slow dashboard loading
- **Risk Score:** r = 1.0
- **Mitigation**:
  ```
  Risk → Aggregate queries → Indexed columns → <1s response
  ```
  - Use database aggregates (COUNT, GROUP BY)
  - Add indexes on game_status, chapter, engagement_state

### Risk 3: Admin Portal Down Affects Main Portal
- **Likelihood (p):** Very Low (0.1) - Separate routes
- **Impact:** High (8) - User-facing impact
- **Risk Score:** r = 0.8
- **Mitigation**:
  ```
  Risk → Separate routes → Isolated queries → No cascade
  ```
  - Admin routes completely isolated from user routes
  - No shared database connections

---

## Verification (CoD^Σ)

### Test Strategy
```
Unit → Integration → E2E
  ↓         ↓          ↓
Models   Endpoints   Pages

Coverage: 80%+ backend, manual E2E frontend
```

- **Unit Tests**: Models, repositories
- **Integration Tests**: API endpoints with mocked DB
- **E2E Tests**: Manual admin workflow testing

### AC Coverage Map
```
US-1: AC-FR001-* → test_auth_admin.py
US-2: AC-FR002-*, AC-FR010-001 → test_admin_debug.py:test_system_overview
US-3: AC-FR003-* → test_admin_debug.py:test_users_list
US-4: AC-FR005-*, AC-FR006-* → test_admin_debug.py:test_user_detail
US-5: AC-FR009-* → test_admin_debug.py:test_user_timing
US-6: AC-FR008-* → test_admin_debug.py:test_jobs
US-7: AC-FR007-* → test_admin_debug.py:test_vice_profile
US-8: AC-FR004-* → test_admin_debug.py:test_user_metrics
```

### Verification Command
```bash
# Backend
pytest tests/api/routes/test_admin_debug.py tests/api/dependencies/test_auth_admin.py -v

# Type check
pnpm type-check

# Frontend (manual E2E)
# 1. Login with @silent-agents.com email
# 2. Navigate to /admin
# 3. Verify dashboard, users, jobs pages load
```

---

## Progress Tracking (CoD^Σ)

**Completion Metrics**:
```
Total Tasks (N):     ∑(tasks) = 22
Completed (X):       0
In Progress (Y):     0
Blocked (Z):         0

Progress Ratio:      0/22 = 0%
```

**Status Distribution**:
```
Completed: ░░░░░░░░░░ 0/22
Progress:  ░░░░░░░░░░ 0/22
Blocked:   ░░░░░░░░░░ 0/22

Health: Starting
```

**Last Updated:** 2025-12-12
**Next Review:** After Phase 1 complete

---

## Notes (CoD^Σ Evidence)

**Implementation Phases**:
- **Phase 1** (Backend Foundation): T1.1-T1.5
- **Phase 2** (Backend Endpoints): T2.1-T2.6
- **Phase 3** (Frontend Foundation): T3.1-T3.4
- **Phase 4** (Frontend Components): T4.1-T4.6
- **Phase 5** (Page Integration): T5.1-T5.5

**Key Patterns to Follow**:
- Auth: Extend `auth.py:17-88` pattern
- Repository: Follow `engagement_repository.py` pattern
- API: Follow `portal.py` response pattern (floats, not Decimal)
- Hooks: Follow `use-dashboard-data.ts` pattern
- Components: Use shadcn MCP tool for base components

**Out of Scope** (Phase 2+):
- Admin actions (reset user, trigger boss)
- Real-time WebSocket updates
- Audit logging
- RBAC

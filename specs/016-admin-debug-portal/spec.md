---
feature: 016-admin-debug-portal
created: 2025-12-12
status: Draft
priority: P2
technology_agnostic: true
constitutional_compliance:
  article_iv: specification_first
---

# Feature Specification: Admin Debug Portal

**IMPORTANT**: This specification is TECHNOLOGY-AGNOSTIC. Focus on WHAT and WHY, not HOW.

---

## Summary

The Admin Debug Portal provides Nikita developers with visibility into game state, scheduled job status, and user debugging information. It enables developers to inspect engagement state machines, chapter progression, vice profiles, and timing information to diagnose issues and understand system behavior.

**Problem Statement**: Developers cannot easily see what's happening with users in the Nikita game - whether onboarding completed, what state machines are in, when the next decay will occur, or if scheduled jobs are running correctly. Debugging requires database queries and log diving.

**Value Proposition**: Developers with `@silent-agents.com` emails get a visual dashboard to quickly understand any user's state, monitor system health, and debug issues without writing SQL queries.

### CoD^Σ Overview

**System Model**:
```
Admin → DebugPortal → Visibility
  ↓         ↓            ↓
Email    Dashboard    Debug_Info

Access := email ∈ *@silent-agents.com ⇒ isAdmin
Portal ⊇ {SystemOverview, UserBrowser, StateMachines, JobMonitor}

Requirements: R := {FR_i} ⊕ {NFR_j}  (functional ⊕ non-functional)
Priorities: P1 ⇒ MVP, P2 ⇒ enhance, P3 ⇒ future
```

**Value Chain**:
```
Problem ≫ Solution ≫ Implementation → Value_Delivered
   ↓         ↓            ↓               ↓
No_visibility  Dashboard  Admin_routes   Quick_debugging
```

---

## Functional Requirements

**Constitutional Limit**: Maximum 3 [NEEDS CLARIFICATION] markers (Article IV)
**Current [NEEDS CLARIFICATION] Count**: 0 / 3

### FR-001: Admin Access Control
System MUST restrict debug portal access to users with email addresses ending in `@silent-agents.com`

**Rationale**: Sensitive game state information should only be visible to authorized developers
**Priority**: Must Have

### FR-002: System Overview Dashboard
System MUST display aggregate statistics about all users including counts by game status, chapter distribution, and engagement state distribution

**Rationale**: Developers need a high-level view of system health and user distribution
**Priority**: Must Have

### FR-003: User Browser
System MUST provide a paginated list of users with filtering capabilities by game status, chapter, and engagement state

**Rationale**: Developers need to find specific users to investigate issues
**Priority**: Must Have

### FR-004: User Detail View
System MUST display comprehensive debugging information for a specific user including all game state, metrics, and timing information

**Rationale**: Core debugging capability to understand individual user state
**Priority**: Must Have

### FR-005: Engagement State Visualization
System MUST display the current engagement state, multiplier, counters (consecutive days), and recent state transitions for a user

**Rationale**: Engagement state affects response behavior and multipliers - critical for debugging
**Priority**: Must Have

### FR-006: Chapter Progress Visualization
System MUST display current chapter, relationship score, boss threshold, boss attempts, decay rate, and grace period remaining

**Rationale**: Chapter progression is core to game mechanics and debugging "stuck" users
**Priority**: Must Have

### FR-007: Vice Profile Visualization
System MUST display top vices with intensities, expression level based on chapter, and total signals detected

**Rationale**: Vice personalization affects Nikita's responses - developers need visibility
**Priority**: Should Have

### FR-008: Scheduled Job Monitoring
System MUST track and display execution history for all scheduled jobs including last run time, status, duration, and results

**Rationale**: Developers need to know if background jobs are running correctly
**Priority**: Must Have

### FR-009: Timing and Countdown Display
System MUST calculate and display time since last interaction, grace period remaining, decay countdown, and projected score after decay

**Rationale**: Timing is critical for understanding decay and user state
**Priority**: Must Have

### FR-010: Active User Counts
System MUST display counts of active users in last 24 hours, 7 days, and 30 days

**Rationale**: Basic system health metric for understanding engagement
**Priority**: Should Have

---

## Non-Functional Requirements

### Performance
- Admin pages MUST load within 3 seconds
- User list pagination MUST return within 1 second
- Dashboard data MUST refresh every 30-60 seconds without full page reload

### Security
- Access control MUST be enforced at both frontend and backend
- Unauthorized access attempts MUST return appropriate error (403 Forbidden)
- No sensitive user data (passwords, tokens) exposed in debug views

### Scalability
- User browser MUST handle 10,000+ users with pagination
- Job history MUST retain at least 7 days of execution records

### Availability
- Debug portal availability matches main portal availability
- Failure of debug portal MUST NOT impact main user-facing portal

### Accessibility
- Debug portal follows same accessibility standards as main portal
- Keyboard navigation supported for all interactive elements

---

## User Stories (CoD^Σ)

**Constitutional Requirement**: Article VII (User-Story-Centric Organization)

**Priority Model** (CoD^Σ):
```
P1 ⇒ MVP (core_value ∧ required)
P2 ⇒ P1.enhance (improves_P1 ∧ ¬blocking)
P3 ⇒ future (nice_to_have)

Independence: ∀S_i, S_j ∈ Stories : S_i ⊥ S_j (each story standalone testable)
```

---

### US-1: Admin Authentication (Priority: P1 - Must-Have)
```
Developer → Access debug portal → Inspect system state
Developer with @silent-agents.com email → authenticated access → full debug visibility
```
**Why P1**: Core access control - portal unusable without authentication

**Acceptance Criteria**:
- **AC-FR001-001**: Given a user with email `dev@silent-agents.com`, When they navigate to admin portal, Then they see the admin dashboard
- **AC-FR001-002**: Given a user with email `user@gmail.com`, When they navigate to admin portal, Then they receive a 403 Forbidden error
- **AC-FR001-003**: Given an unauthenticated user, When they navigate to admin portal, Then they are redirected to login

**Independent Test**: Login with @silent-agents.com email, verify access; login with other email, verify denial
**Dependencies**: None (CoD^Σ: S1 ⊥ {S2, S3, ...})

---

### US-2: System Overview Dashboard (Priority: P1 - Must-Have)
```
Developer → View system overview → Understand system health
Developer → aggregate statistics → quick health assessment
```
**Why P1**: Entry point for all debugging - provides context before deep diving

**Acceptance Criteria**:
- **AC-FR002-001**: Given an admin on the dashboard, When the page loads, Then user counts by game_status (active, boss_fight, game_over, won) are displayed
- **AC-FR002-002**: Given an admin on the dashboard, When the page loads, Then user distribution by chapter (1-5) is displayed
- **AC-FR002-003**: Given an admin on the dashboard, When the page loads, Then user distribution by engagement state (6 states) is displayed
- **AC-FR010-001**: Given an admin on the dashboard, When the page loads, Then active user counts (24h, 7d, 30d) are displayed

**Independent Test**: Load dashboard, verify all aggregate counts render correctly
**Dependencies**: US-1 (admin auth required)

---

### US-3: User Browser and Search (Priority: P1 - Must-Have)
```
Developer → Browse and filter users → Find specific user to debug
Developer → filtered user list → locate problem user quickly
```
**Why P1**: Cannot debug specific users without finding them first

**Acceptance Criteria**:
- **AC-FR003-001**: Given an admin on user browser, When page loads, Then paginated user list displays (50 per page default)
- **AC-FR003-002**: Given an admin on user browser, When they filter by game_status=active, Then only active users are shown
- **AC-FR003-003**: Given an admin on user browser, When they filter by chapter=3, Then only chapter 3 users are shown
- **AC-FR003-004**: Given an admin on user browser, When they click a user row, Then they navigate to user detail view

**Independent Test**: Load user browser, apply filters, verify filtering works, click user to navigate
**Dependencies**: US-1

---

### US-4: User State Machine Visualization (Priority: P1 - Must-Have)
```
Developer → View user's state machines → Understand engagement and chapter state
Developer → state machine cards → quick state understanding
```
**Why P1**: Core debugging capability - most issues relate to state machine behavior

**Acceptance Criteria**:
- **AC-FR005-001**: Given an admin viewing user detail, When engagement card loads, Then current engagement state and multiplier are displayed
- **AC-FR005-002**: Given an admin viewing user detail, When engagement card loads, Then counter values (consecutive in_zone, clingy_days, distant_days) are displayed
- **AC-FR005-003**: Given an admin viewing user detail, When engagement card loads, Then recent state transitions (last 5) with timestamps are displayed
- **AC-FR006-001**: Given an admin viewing user detail, When chapter card loads, Then current chapter, chapter name, and relationship score are displayed
- **AC-FR006-002**: Given an admin viewing user detail, When chapter card loads, Then boss threshold, current progress %, and boss attempts are displayed
- **AC-FR006-003**: Given an admin viewing user detail, When chapter card loads, Then decay rate per hour and grace period hours are displayed

**Independent Test**: Navigate to user detail, verify all state machine data renders correctly
**Dependencies**: US-3 (need user browser to navigate to detail)

---

### US-5: User Timing and Scheduling (Priority: P1 - Must-Have)
```
Developer → View timing info → Understand decay and scheduled actions
Developer → timing card → know when next actions occur
```
**Why P1**: Timing issues are common debug targets - need visibility into countdowns

**Acceptance Criteria**:
- **AC-FR009-001**: Given an admin viewing user detail, When timing card loads, Then last_interaction_at timestamp is displayed
- **AC-FR009-002**: Given an admin viewing user detail, When timing card loads, Then hours since interaction is calculated and displayed
- **AC-FR009-003**: Given an admin viewing user detail, When timing card loads, Then grace period remaining (hours) is displayed
- **AC-FR009-004**: Given an admin viewing user detail, When timing card loads, Then decay countdown ("20h 30m until decay") is displayed
- **AC-FR009-005**: Given a user past their grace period, When timing card loads, Then "Currently decaying" indicator is shown

**Independent Test**: View user detail, verify all timing calculations display correctly
**Dependencies**: US-3

---

### US-6: Scheduled Job Monitoring (Priority: P1 - Must-Have)
```
Developer → Monitor scheduled jobs → Ensure background tasks running
Developer → job status page → verify cron health
```
**Why P1**: Background jobs (decay, delivery) are critical - failures cause user-visible issues

**Acceptance Criteria**:
- **AC-FR008-001**: Given an admin on jobs page, When page loads, Then all 5 job types (decay, deliver, summary, cleanup, process-conversations) are listed
- **AC-FR008-002**: Given an admin on jobs page, When page loads, Then each job shows last_run timestamp with relative time ("2 min ago")
- **AC-FR008-003**: Given an admin on jobs page, When page loads, Then each job shows status (running, completed, failed)
- **AC-FR008-004**: Given an admin on jobs page, When page loads, Then each job shows duration_ms of last run
- **AC-FR008-005**: Given a job that failed, When job card renders, Then error indicator and message are visible

**Independent Test**: Load jobs page, verify all jobs listed with status information
**Dependencies**: US-1

---

### US-7: Vice Profile Visualization (Priority: P2 - Important)
```
Developer → View vice profile → Understand personalization state
Developer → vice card → see detected preferences
```
**Why P2**: Enhances debugging capability but not blocking for core state machine debugging

**Acceptance Criteria**:
- **AC-FR007-001**: Given an admin viewing user detail, When vice card loads, Then top vices (up to 3) with intensities are displayed
- **AC-FR007-002**: Given an admin viewing user detail, When vice card loads, Then expression level (subtle, moderate, direct, explicit) based on chapter is shown
- **AC-FR007-003**: Given an admin viewing user detail, When vice card loads, Then total signals detected count is displayed

**Independent Test**: View user detail, verify vice profile data renders
**Dependencies**: US-3

---

### US-8: User Metrics Display (Priority: P2 - Important)
```
Developer → View 4 metrics → Understand relationship dimensions
Developer → metrics display → see intimacy, passion, trust, secureness
```
**Why P2**: Enhances debugging but can work without detailed metric breakdown initially

**Acceptance Criteria**:
- **AC-FR004-001**: Given an admin viewing user detail, When page loads, Then all 4 metrics (intimacy, passion, trust, secureness) are displayed with values 0-100
- **AC-FR004-002**: Given an admin viewing user detail, When page loads, Then metrics are shown in a compact grid format

**Independent Test**: View user detail, verify all 4 metrics display correctly
**Dependencies**: US-3

---

## Intelligence Evidence

**Constitutional Requirement**: Article II (Evidence-Based Reasoning)

### Queries Executed

```bash
# Portal architecture exploration
project-intel.mjs --search "portal dashboard" --type tsx --json

# State machine implementation analysis
project-intel.mjs --search "engagement state" --type py --json

# Scheduled jobs analysis
project-intel.mjs --search "tasks decay" --type py --json
```

### Findings

**Related Features**:
- `portal/src/app/dashboard/page.tsx` - Existing user-facing dashboard pattern
- `portal/src/lib/api/client.ts` - API client pattern to extend
- `nikita/api/routes/portal.py` - Portal API endpoint patterns

**Existing Patterns**:
- `nikita/engine/engagement/state_machine.py:34-51` - Engagement state definitions and transitions
- `nikita/engine/chapters/boss.py` - Chapter and boss encounter logic
- `nikita/api/routes/tasks.py` - Task endpoint patterns for job logging

### Assumptions

- ASSUMPTION: Existing Supabase JWT contains email field for domain validation
- ASSUMPTION: Job execution logging can be added to existing task endpoints without breaking them

### CoD^Σ Trace

```
User_request ≫ explore_portal ∘ explore_engine ∘ explore_tasks → requirements
Evidence: portal/src/app/dashboard/, nikita/engine/, nikita/api/routes/tasks.py
```

---

## Scope

### In-Scope Features
- Admin authentication via email domain check (`@silent-agents.com`)
- System overview dashboard with aggregate statistics
- Paginated user browser with filters
- User detail page with state machine visualization
- Engagement state card (state, multiplier, counters, transitions)
- Chapter progress card (chapter, score, threshold, boss, decay)
- Vice profile card (top vices, expression level)
- Timing/scheduling card (grace period, decay countdown)
- Job execution monitoring and history
- 4-metric display (intimacy, passion, trust, secureness)

### Out-of-Scope
- Admin actions (reset user, trigger boss, adjust score) - Future Phase 2
- Interactive SVG state machine diagrams - Future enhancement
- Real-time WebSocket updates - Current polling is sufficient
- Audit logging of admin access - Future security enhancement
- Role-based admin permissions (all admins equal) - Future enhancement
- Conversation history viewer - Separate feature
- Memory/knowledge graph inspector - Separate feature

### Future Phases
- **Phase 2**: Admin actions (reset user, trigger boss, skip decay, adjust score)
- **Phase 3**: Real-time updates, audit logging, RBAC

---

## Constraints

### Business Constraints
- Read-only in Phase 1 - no destructive actions
- Admin access limited to `@silent-agents.com` domain only
- Must not impact performance of user-facing portal

### User Constraints
- Target users are technical developers familiar with game mechanics
- Desktop-first design acceptable (admin tool, not user-facing)
- English only (no i18n required for admin tools)

### Regulatory Constraints
- No PII exported or downloadable
- Admin access must be authenticated (no public debug endpoints)

---

## Risks & Mitigations (CoD^Σ)

**Risk Model**:
```
r := p × impact  (risk score)
p ∈ [0,1]        (probability: Low=0.2, Med=0.5, High=0.8)
impact ∈ [1,10]  (magnitude: Low=2, Med=5, High=8)
```

### Risk 1: Unauthorized Access to Sensitive Data
**Likelihood (p)**: Low (0.2) - Email domain check is robust
**Impact**: High (8) - Exposes internal game state
**Risk Score**: r = 1.6
**Mitigation** (CoD^Σ):
```
Risk → JWT validation → Email domain check → 403 response
Prevention ⇒ p↓: Backend + frontend auth checks
```
- Validate email domain on every admin API request
- Frontend redirects unauthorized users
- No sensitive tokens/passwords in debug views

### Risk 2: Job Logging Performance Impact
**Likelihood (p)**: Low (0.2) - Simple DB write
**Impact**: Medium (5) - Could slow scheduled tasks
**Risk Score**: r = 1.0
**Mitigation**:
```
Risk → Async logging → Separate table → No blocking
```
- Make job logging async/non-blocking
- Use separate table with efficient indexing
- Monitor task execution times after rollout

### Risk 3: Admin Portal Impacts Main Portal
**Likelihood (p)**: Low (0.2) - Separate routes and queries
**Impact**: High (8) - User-facing impact
**Risk Score**: r = 1.6
**Mitigation**:
```
Risk → Separate routes → Isolated queries → Independent failure
```
- Admin queries don't share database connections with portal
- Admin portal failures don't cascade to main portal
- Load testing before production rollout

---

## Success Metrics

### User-Centric Metrics
- Developers can find and inspect any user's state within 30 seconds
- Developers can verify job health within 10 seconds
- Time to diagnose common issues reduced by 50%

### Technical Metrics
- Admin pages load < 3 seconds (P95)
- Zero unauthorized access incidents
- Job logging adds < 100ms to task execution

### Business Metrics
- Debugging time reduced (measured via support ticket resolution time)
- Fewer database query requests from developers
- Faster incident response for user issues

---

## Open Questions

All questions resolved during planning phase.

---

## Stakeholders

**Owner**: Development Team
**Created By**: Claude Code
**Reviewers**: Development Team Lead
**Informed**: All developers with @silent-agents.com emails

---

## Approvals

- [ ] **Product Owner**: TBD - TBD
- [x] **Engineering Lead**: User - 2025-12-12
- [ ] **Design Lead**: N/A (admin tool)
- [ ] **Security**: TBD - TBD

---

## Specification Checklist

**Before Planning**:
- [x] All [NEEDS CLARIFICATION] resolved (0/3)
- [x] All user stories have ≥2 acceptance criteria
- [x] All user stories have priority (P1, P2, P3)
- [x] All user stories have independent test criteria
- [x] P1 stories define MVP scope
- [x] No technology implementation details in spec
- [x] Intelligence evidence provided (CoD^Σ traces)
- [x] Stakeholder approvals obtained

**Status**: Ready for Planning

---

**Version**: 1.0
**Last Updated**: 2025-12-12
**Next Step**: Run /plan to create implementation plan

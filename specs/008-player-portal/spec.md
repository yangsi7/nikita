---
feature: 008-player-portal
created: 2025-11-28
status: Draft
priority: P3
technology_agnostic: true
constitutional_compliance:
  article_iv: specification_first
---

# Feature Specification: Player Portal

**IMPORTANT**: This specification is TECHNOLOGY-AGNOSTIC. Focus on WHAT and WHY, not HOW.

---

## Summary

The Player Portal is a web dashboard that provides players with visibility into their relationship status, game progress, and history—elements intentionally hidden during gameplay to maintain the "no UI" immersion. It serves as the "behind the curtain" view for players who want to understand their progress.

**Problem Statement**: The core game (Telegram) has no visible UI by design. But players need somewhere to see their score, chapter, history, and access voice calls. Without a portal, there's no way to know game state.

**Value Proposition**: Players can check their relationship "health" via the portal—see their score, chapter progress, conversation history, and upcoming milestones. It's the game dashboard without breaking the in-conversation immersion.

### CoD^Σ Overview

**System Model**:
```
Player → Portal → View_state → [Optional] Initiate_action
   ↓        ↓          ↓              ↓
Browser   Auth     Score/Chapter   Voice_call
                    History         Settings

Portal_views := {dashboard, history, settings, voice_call}
Portal_does_NOT := {send messages, replace Telegram, count as interaction}
```

---

## Functional Requirements

### FR-001: Authentication
System MUST authenticate users before portal access:
- Login via email magic link (same as Telegram auth)
- Session persistence (stay logged in)
- Account linking (Telegram ↔ Portal same account)
- Logout capability

**Rationale**: Portal shows sensitive game data—must verify identity
**Priority**: Must Have

### FR-002: Dashboard View
System MUST display current game state:
- Current relationship score (composite %)
- Current chapter (1-5) with chapter name
- Individual metric breakdown (intimacy, passion, trust, secureness)
- Days in relationship
- Game status (active, boss_fight, game_over, won)

**Rationale**: Core "where am I" visibility users expect
**Priority**: Must Have

### FR-003: Score History Visualization
System MUST visualize score trends:
- Line chart of composite score over time
- Mark significant events (boss encounters, game events)
- Time range selection (last week, month, all time)
- Metric breakdown option (show individual metrics)

**Rationale**: Trends show relationship trajectory—important feedback
**Priority**: Must Have

### FR-004: Conversation History
System MUST provide conversation history access:
- List of past conversations (text and voice)
- Conversation summaries or excerpts
- Score impact per conversation
- Searchable/filterable by date

**Rationale**: Users want to review what happened, understand score changes
**Priority**: Should Have

### FR-005: Chapter Progress Display
System MUST show chapter progression:
- Current chapter with milestone progress
- Boss threshold distance (X% until boss fight)
- Past chapter completion dates
- Chapter-specific achievements if any

**Rationale**: Clear progress toward goals increases engagement
**Priority**: Should Have

### FR-006: Voice Call Access
System MUST enable voice call initiation:
- "Call Nikita" button (primary voice entry point)
- Call availability status (based on chapter, game state)
- Past call history with summaries
- Call duration and score impact

**Rationale**: Portal is the gateway to voice feature
**Priority**: Must Have (if Voice Agent implemented)

### FR-007: Decay Warning
System MUST warn about upcoming decay:
- Time until grace period expires
- Current decay rate for chapter
- Last interaction timestamp
- Projected score if no interaction

**Rationale**: Helps users avoid unintentional relationship damage
**Priority**: Should Have

### FR-008: Settings Management
System MUST provide user settings:
- Email notification preferences
- Account deletion capability
- Data export request
- Password/auth method management

**Rationale**: Standard user account management expectations
**Priority**: Should Have

### FR-009: No Gameplay from Portal
System MUST NOT enable direct messaging from portal:
- Cannot send text messages to Nikita
- Cannot replace Telegram as chat interface
- Portal viewing does NOT reset decay timer
- Clear separation: Portal = viewing, Telegram = playing

**Rationale**: Maintaining Telegram as sole interaction point preserves immersion
**Priority**: Must Have

### FR-010: Responsive Design
System MUST work across devices:
- Mobile-friendly (primary for Telegram users)
- Desktop supported
- Tablet optimized
- Core functionality on all screen sizes

**Rationale**: Users may access from any device
**Priority**: Must Have

### FR-011: Real-Time Updates
System SHOULD provide real-time state updates:
- Score changes reflected without refresh
- Chapter transitions shown immediately
- Boss encounter status live
- Game over/victory announced in real-time

**Rationale**: Live updates feel more connected to the relationship
**Priority**: Nice to Have

### FR-012: Achievement Display
System MAY display achievements and milestones:
- Chapter completion badges
- Special moment commemorations
- Streak tracking (consecutive days engaged)
- Victory celebration for game completion

**Rationale**: Achievements add game feel without breaking immersion elsewhere
**Priority**: Nice to Have

---

## Non-Functional Requirements

### Performance
- Dashboard load: < 2 seconds
- Chart rendering: < 1 second
- Real-time updates: < 500ms propagation

### Reliability
- Availability: 99% uptime
- Data consistency: Portal reflects database truth
- Graceful degradation: Show cached data if API unavailable

### Security
- HTTPS only
- Session timeout for inactive users
- Rate limiting on API calls
- No exposed sensitive data in client

### Accessibility
- WCAG 2.1 AA compliance
- Screen reader compatible
- Keyboard navigable
- Sufficient color contrast

---

## User Stories (CoD^Σ)

### US-1: View Dashboard (Priority: P1 - Must-Have)
```
Player logs in → sees score and chapter → understands status
```
**Acceptance Criteria**:
- **AC-FR001-001**: Given user has Telegram account, When logging into portal, Then magic link sent to email
- **AC-FR002-001**: Given authenticated user, When viewing dashboard, Then current score displayed
- **AC-FR002-002**: Given dashboard view, When displaying chapter, Then chapter name and number shown

**Independent Test**: Log in, verify dashboard shows correct game state
**Dependencies**: Auth (Supabase), Database

---

### US-2: View Score History (Priority: P2 - Important)
```
Player wants trends → views chart → sees relationship trajectory
```
**Acceptance Criteria**:
- **AC-FR003-001**: Given user on dashboard, When clicking history, Then score chart displayed
- **AC-FR003-002**: Given chart displayed, When selecting time range, Then chart updates
- **AC-FR003-003**: Given significant events, When viewing chart, Then events marked on timeline

**Independent Test**: View history, verify chart accurate to database records
**Dependencies**: US-1, Score History data

---

### US-3: Initiate Voice Call (Priority: P1 - Must-Have)
```
Player wants to call → clicks button → voice interface opens
```
**Acceptance Criteria**:
- **AC-FR006-001**: Given Ch3+ user, When clicking "Call Nikita", Then voice interface launches
- **AC-FR006-002**: Given Ch1 user, When checking call, Then availability shows restricted
- **AC-FR006-003**: Given call completed, When returning to portal, Then call logged in history

**Independent Test**: Click call button, verify voice connection established
**Dependencies**: Voice Agent (007)

---

### US-4: Check Decay Status (Priority: P2 - Important)
```
Player worried about decay → checks portal → sees time remaining
```
**Acceptance Criteria**:
- **AC-FR007-001**: Given user hasn't messaged today, When viewing dashboard, Then decay countdown shown
- **AC-FR007-002**: Given grace period info, When displayed, Then hours until decay clear
- **AC-FR007-003**: Given projection shown, When calculated, Then shows score if no interaction

**Independent Test**: Don't interact, verify decay warning accurate
**Dependencies**: US-1, Decay System (005)

---

### US-5: Review Conversation History (Priority: P3 - Nice-to-Have)
```
Player wants context → browses history → sees past conversations
```
**Acceptance Criteria**:
- **AC-FR004-001**: Given conversation history, When viewing, Then list of conversations shown
- **AC-FR004-002**: Given conversation selected, When expanded, Then summary/excerpt visible
- **AC-FR004-003**: Given score change, When viewing conversation, Then impact shown

**Independent Test**: Browse history, verify conversations match database
**Dependencies**: US-1, Conversation Storage

---

### US-6: Manage Settings (Priority: P3 - Nice-to-Have)
```
Player wants control → accesses settings → manages preferences
```
**Acceptance Criteria**:
- **AC-FR008-001**: Given settings page, When viewing, Then notification preferences shown
- **AC-FR008-002**: Given delete account option, When requested, Then confirmation required
- **AC-FR008-003**: Given data export, When requested, Then export generated

**Independent Test**: Access settings, verify all options functional
**Dependencies**: US-1

---

## Intelligence Evidence

### Findings
- memory/product.md - Player portal mentioned for score/history visibility
- Portal serves as voice call entry point (FR-006)
- Portal intentionally does NOT replace Telegram (FR-009)

### Assumptions
- ASSUMPTION: Supabase Auth available for portal login
- ASSUMPTION: Frontend framework (Next.js) for portal implementation
- ASSUMPTION: Real-time via Supabase Realtime or polling

---

## Scope

### In-Scope
- Authentication (email magic link)
- Dashboard with score/chapter display
- Score history visualization
- Voice call initiation
- Decay warning display
- Settings management
- Responsive design

### Out-of-Scope
- Direct messaging to Nikita (Telegram only)
- Payment/subscription management (future)
- Social features (leaderboards, sharing)
- Mobile native app (web only)

---

## Infrastructure Dependencies

This feature depends on the following infrastructure specs:

| Spec | Dependency | Usage |
|------|------------|-------|
| 009-database-infrastructure | Stats queries, history retrieval | UserRepository.get_stats(), ScoreHistoryRepository.get_history() |
| 010-api-infrastructure | Portal API endpoints | GET /api/v1/portal/* with Supabase JWT auth |
| 011-background-tasks | Daily summary generation | daily_summaries table populated by generate-summaries Edge Function |

**Database Tables Used**:
- `users` (relationship_score, chapter, game_status, days_played)
- `user_metrics` (detailed metric display)
- `conversations` (history view with messages JSONB)
- `score_history` (score trend graphs)
- `daily_summaries` (Nikita's daily recaps)

**API Endpoints Required**:
- `GET /api/v1/portal/stats/{user_id}` - Dashboard data
- `GET /api/v1/portal/conversations/{user_id}` - Conversation history
- `GET /api/v1/portal/daily-summary/{user_id}/{date}` - Daily recap

**Background Tasks Required**:
- `generate-daily-summaries` Edge Function (FR-003 in 011-background-tasks)

---

## Risks & Mitigations

### Risk 1: Portal Replaces Telegram
**Description**: Users try to play entirely from portal, losing immersion
**Likelihood**: Low (0.2) | **Impact**: High (8) | **Score**: 1.6
**Mitigation**: No messaging capability, clear messaging about Telegram

### Risk 2: Score Obsession
**Description**: Users obsess over score numbers instead of enjoying game
**Likelihood**: Medium (0.5) | **Impact**: Medium (5) | **Score**: 2.5
**Mitigation**: Emphasize trends over exact numbers, don't show every decimal

### Risk 3: Portal as Obligation
**Description**: Checking portal feels like homework, not fun
**Likelihood**: Low (0.3) | **Impact**: Medium (5) | **Score**: 1.5
**Mitigation**: Keep portal optional, no gameplay locked behind portal visits

---

## Success Metrics

- Portal adoption: 60%+ of active users visit portal at least weekly
- Voice call conversions: 30%+ of portal visits include voice call
- Session duration: Average 2-5 minutes (quick check, not replacement for Telegram)
- Decay prevention: Users who check portal have lower decay game-over rate

---

**Version**: 1.0
**Last Updated**: 2025-11-28

# Admin Monitoring Implementation Analysis

**Generated**: 2026-01-22
**Scope**: nikita/api/routes/admin*.py, portal/src/app/admin/*, specs/016-020

---

## 1. Backend API Endpoints

### admin.py (nikita/api/routes/admin.py)

| Method | Path | Purpose | Auth | Line |
|--------|------|---------|------|------|
| GET | /users | List users (paginated) | admin.py:46 stub | :62-94 |
| GET | /users/{user_id} | User detail | admin.py:46 stub | :97-122 |
| GET | /users/{user_id}/metrics | User metrics (4 scores) | admin.py:46 stub | :125-143 |
| GET | /users/{user_id}/engagement | Engagement state + transitions | admin.py:46 stub | :146-177 |
| GET | /users/{user_id}/vices | Vice preferences | admin.py:46 stub | :180-198 |
| GET | /users/{user_id}/conversations | Conversations list | admin.py:46 stub | :201-233 |
| PUT | /users/{user_id}/score | Set score | admin.py:46 stub | :241-268 |
| PUT | /users/{user_id}/chapter | Set chapter | admin.py:46 stub | :271-293 |
| PUT | /users/{user_id}/status | Set game status | admin.py:46 stub | :296-320 |
| PUT | /users/{user_id}/engagement | Set engagement state | admin.py:46 stub | :323-361 |
| POST | /users/{user_id}/reset-boss | Reset boss attempts | admin.py:46 stub | :364-384 |
| POST | /users/{user_id}/clear-engagement | Clear history | admin.py:46 stub | :387-406 |
| GET | /prompts | List prompts (TODO stub) | admin.py:46 stub | :414-434 |
| GET | /prompts/{prompt_id} | Prompt detail (TODO stub) | admin.py:46 stub | :437-445 |
| GET | /health | System health | admin.py:46 stub | :453-484 |
| GET | /stats | Admin statistics | admin.py:46 stub | :487-525 |
| GET | /processing-stats | Post-processing stats | admin.py:46 stub | :528-595 |

**Note**: admin.py:46-54 has stub auth that always raises 403. These endpoints are NOT functional via this router.

### admin_debug.py (nikita/api/routes/admin_debug.py) - FUNCTIONAL

| Method | Path | Purpose | Auth | Line |
|--------|------|---------|------|------|
| GET | /system | System overview (distributions) | get_current_admin_user | :82-176 |
| GET | /jobs | Scheduled jobs status | get_current_admin_user | :184-262 |
| GET | /users | User list (filtered) | get_current_admin_user | :270-336 |
| GET | /users/{user_id} | User detail + timing | get_current_admin_user | :344-410 |
| GET | /state-machines/{user_id} | All state machines | get_current_admin_user | :418-498 |
| POST | /neo4j-test | Test Neo4j connection | get_current_admin_user | :506-572 |
| GET | /prompts/{user_id} | User prompts list | get_current_admin_user | :580-619 |
| GET | /prompts/{user_id}/latest | Latest prompt detail | get_current_admin_user | :622-665 |
| POST | /prompts/{user_id}/preview | Generate prompt preview | get_current_admin_user | :668-710 |
| GET | /voice/conversations | Voice conversations list | get_current_admin_user | :718-790 |
| GET | /voice/conversations/{id} | Voice conversation detail | get_current_admin_user | :793-847 |
| GET | /voice/stats | Voice statistics | get_current_admin_user | :850-908 |
| GET | /voice/elevenlabs | ElevenLabs calls list | get_current_admin_user | :911-963 |
| GET | /voice/elevenlabs/{id} | ElevenLabs call detail | get_current_admin_user | :966-1010 |
| GET | /text/conversations | Text conversations list | get_current_admin_user | :1018-1086 |
| GET | /text/conversations/{id} | Text conversation detail | get_current_admin_user | :1089-1145 |
| GET | /text/stats | Text statistics | get_current_admin_user | :1148-1216 |
| GET | /text/pipeline/{id} | Pipeline status (9 stages) | get_current_admin_user | :1219-1316 |
| GET | /text/threads | Threads list | get_current_admin_user | :1319-1367 |
| GET | /text/thoughts | Thoughts list | get_current_admin_user | :1370-1412 |

**Total**: 21 functional endpoints in admin_debug.py

---

## 2. Data Models & Schemas

### admin.py schemas (nikita/api/schemas/admin.py)
- `AdminUserListItem` - :10-21
- `AdminUserDetailResponse` - :24-37
- `AdminSetScoreRequest` / `AdminSetChapterRequest` / `AdminSetGameStatusRequest` / `AdminSetEngagementStateRequest` - :40-69
- `AdminResetResponse` - :72-76
- `GeneratedPromptResponse` / `GeneratedPromptsResponse` - :79-98
- `AdminHealthResponse` / `AdminStatsResponse` - :101-118
- `ProcessingStatsResponse` - :121-133

### admin_debug.py schemas (nikita/api/schemas/admin_debug.py)
**System Overview** (:16-66):
- `GameStatusDistribution`, `ChapterDistribution`, `EngagementDistribution`, `ActiveUserCounts`, `SystemOverviewResponse`

**Job Monitoring** (:69-90):
- `JobExecutionStatus`, `JobStatusResponse`

**User Data** (:93-226):
- `UserListItem`, `UserListResponse`, `UserTimingInfo`, `UserNextActions`, `UserDetailResponse`
- `EngagementStateInfo`, `ChapterStateInfo`, `ViceInfo`, `ViceProfileInfo`, `StateMachinesResponse`

**Prompt Viewing** (:229-279):
- `PromptListItem`, `PromptListResponse`, `PromptDetailResponse`

**Voice Monitoring** (:282-396):
- `VoiceConversationListItem`, `VoiceConversationListResponse`, `TranscriptEntryResponse`, `VoiceConversationDetailResponse`
- `ElevenLabsCallListItem`, `ElevenLabsCallListResponse`, `ElevenLabsTranscriptTurn`, `ElevenLabsCallDetailResponse`
- `VoiceStatsResponse`

**Text Monitoring** (:399-531):
- `TextConversationListItem`, `TextConversationListResponse`, `MessageResponse`, `TextConversationDetailResponse`
- `PipelineStageStatus`, `PipelineStatusResponse`, `TextStatsResponse`
- `ThreadListItem`, `ThreadListResponse`, `ThoughtListItem`, `ThoughtListResponse`

---

## 3. Frontend UI Components

### Portal Admin Pages (portal/src/app/admin/)

| Page | Path | Purpose | File |
|------|------|---------|------|
| Layout | /admin/* | Admin shell + nav + auth check | layout.tsx:1-99 |
| Overview | /admin | System stats dashboard | page.tsx |
| Users | /admin/users | User list + filters | users/page.tsx |
| User Detail | /admin/users/[id] | User drill-down | users/[id]/page.tsx |
| Voice | /admin/voice | Voice conversations | voice/page.tsx |
| Text | /admin/text | Text conversations | text/page.tsx |
| Prompts | /admin/prompts | Prompt viewer | prompts/page.tsx |
| Jobs | /admin/jobs | Job monitoring | jobs/page.tsx |

### Navigation (portal/src/components/admin/AdminNavigation.tsx:7-14)
```typescript
const adminNavigation = [
  { name: 'Overview', href: '/admin', emoji: '📊' },
  { name: 'Users', href: '/admin/users', emoji: '👥' },
  { name: 'Voice', href: '/admin/voice', emoji: '🎙️' },
  { name: 'Text', href: '/admin/text', emoji: '💬' },
  { name: 'Prompts', href: '/admin/prompts', emoji: '📝' },
  { name: 'Jobs', href: '/admin/jobs', emoji: '⚙️' },
]
```

### Hooks (portal/src/hooks/use-admin-data.ts)
- `useIsAdmin()` - :15-21
- `useSystemOverview()` - :27-33 (60s poll)
- `useJobStatus()` - :40-46 (30s poll)
- `useAdminUsers()` - :53-59 (60s poll)
- `useAdminUserDetail()` - :66-73
- `useStateMachines()` - :79-86
- `useVoiceConversations()` - :96-102 (30s poll)
- `useVoiceConversationDetail()` - :109-115
- `useVoiceStats()` - :122-128 (30s poll)
- `useElevenLabsCalls()` - :135-141 (30s poll)
- `useElevenLabsCallDetail()` - :148-154
- `useTextConversations()` - :165-171 (30s poll)
- `useTextConversationDetail()` - :178-184
- `useTextStats()` - :191-197 (30s poll)
- `usePipelineStatus()` - :204-210
- `useThreads()` - :217-223
- `useThoughts()` - :230-236
- `useUserPrompts()` - :247-253
- `usePromptDetail()` - :260-266
- `useLatestPrompt()` - :273-279

---

## 4. Authentication/Authorization Pattern

**Backend** (nikita/api/dependencies/auth.py):
- `get_current_admin_user()` - :118-203
- Admin check: `_is_admin_email()` - :95-115
- Domain: `@silent-agents.com` OR in `settings.admin_emails` list
- Uses Supabase JWT decode with HS256 algorithm

**Frontend** (portal/src/app/admin/layout.tsx):
- `useIsAdmin()` hook to check access - :13
- Redirects non-admins to `/dashboard` - :15-20
- Loading/error states handled - :28-68

---

## 5. Reusable Patterns

### Backend Patterns
1. **Admin auth dependency**: `Annotated[UUID, Depends(get_current_admin_user)]`
2. **Async session**: `Annotated[AsyncSession, Depends(get_async_session)]`
3. **Pagination**: `page: int = Query(default=1)`, `page_size: int = Query(default=50)`
4. **Time-based aggregation**: 24h/7d/30d stats pattern (admin_debug.py:145-162)
5. **Status distribution**: Group by status, count, return as dict

### Frontend Patterns
1. **React Query hooks**: All use TanStack Query with polling intervals
2. **Admin layout**: Consistent header with nav + logout
3. **Poll intervals**: 30s for jobs/voice/text, 60s for users/system

---

## 6. Coverage vs Specs

### Spec 016 (Admin Debug Portal) - COMPLETE
- FR-001 Admin access: Implemented (auth.py:118-203)
- FR-002 System overview: Implemented (admin_debug.py:82-176)
- FR-003 User browser: Implemented (admin_debug.py:270-336)
- FR-004 User detail: Implemented (admin_debug.py:344-410)
- FR-005 Engagement state: Implemented (admin_debug.py:418-498)
- FR-006 Chapter progress: Implemented (admin_debug.py:418-498)
- FR-007 Vice profile: Implemented (admin_debug.py:476-491)
- FR-008 Job monitoring: Implemented (admin_debug.py:184-262)

### Spec 018 (Admin Prompt Viewing) - COMPLETE
- Prompt list: Implemented (admin_debug.py:580-619)
- Latest prompt: Implemented (admin_debug.py:622-665)
- Preview generation: Implemented (admin_debug.py:668-710)

### Spec 019 (Admin Voice Monitoring) - COMPLETE
- Voice conversations: Implemented (admin_debug.py:718-847)
- ElevenLabs integration: Implemented (admin_debug.py:911-1010)
- Voice stats: Implemented (admin_debug.py:850-908)

### Spec 020 (Admin Text Monitoring) - COMPLETE
- Text conversations: Implemented (admin_debug.py:1018-1145)
- Pipeline status: Implemented (admin_debug.py:1219-1316)
- Stats + threads + thoughts: Implemented (admin_debug.py:1148-1412)

---

## 7. Identified Gaps

### Gap G1: Stub Auth in admin.py
- `admin.py:46-54` has placeholder auth that always raises 403
- All endpoints in admin.py are NOT accessible
- Recommend: Remove admin.py or redirect to admin_debug.py

### Gap G2: Missing Entities in Current Implementation
Based on analysis, the following entities exist but have no admin visibility:
- **Scheduled messages** (scheduled_messages table) - no CRUD endpoints
- **Memory/Graphiti graphs** - only neo4j-test endpoint, no browse capability
- **Score history** - exists in DB but no admin endpoint

### Gap G3: No Charts/Visualizations
- All data returned as JSON, no time-series endpoints
- No trend data (score over time, engagement transitions over time)
- Frontend would need to aggregate for charts

### Gap G4: No Drill-Down Links
- API returns IDs but no navigation helpers
- user_id in conversations doesn't link to user detail
- conversation_id in threads doesn't link to conversation

### Gap G5: No Export/Bulk Operations
- No CSV/JSON export endpoints
- No bulk actions (reset multiple users, etc.)

---

## 8. Summary Statistics

| Category | Count |
|----------|-------|
| Functional backend endpoints | 21 |
| Stub/non-functional endpoints | 17 |
| Pydantic schemas | 40+ |
| Frontend pages | 8 |
| React Query hooks | 20 |
| Specs covered | 4/4 (100%) |
| Major gaps identified | 5 |

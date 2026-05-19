---
feature: 018-admin-prompt-viewing
created: 2025-12-18
status: Draft
priority: P1
technology_agnostic: false  # This is a backend API feature
constitutional_compliance:
  article_iv: specification_first
---

# Feature Specification: Admin Prompt Viewing for Debugging

---

## Summary

Add admin dashboard endpoints to view system prompts used in conversations - both historical prompts (what was actually used) and preview prompts (what would be generated for the next message).

**Problem Statement**: Developers cannot see the exact system prompts being generated for each user, making it impossible to debug persona behavior, verify context injection, or understand why Nikita responds in certain ways.

**Value Proposition**: Enable developers to inspect, analyze, and debug the dynamic prompt generation system by viewing the full prompts with all context injected.

### CoD^Σ Overview

**System Model**:
```
Admin → Prompt Viewer → Debug Insights
  ↓          ↓              ↓
Need    Capability      Understanding

Requirements: R := {FR_i} ⊕ {NFR_j}
- FR: List prompts, view latest, preview next
- NFR: Auth-protected, fast response, no side effects
```

**Value Chain**:
```
Debug_need ≫ Prompt_visibility ≫ Endpoints → Developer_insight
    ↓              ↓                 ↓              ↓
Blind_debugging  Full_context     API_access   Fast_resolution
```

---

## Functional Requirements

**[NEEDS CLARIFICATION] Count**: 0 / 3

### FR-001: List Recent Prompts
System MUST provide an endpoint to list recent generated prompts for a specific user.

**Rationale**: Developers need to see the history of prompts generated to track how context changes over conversations.
**Priority**: Must Have

### FR-002: View Latest Prompt with Full Content
System MUST provide an endpoint to retrieve the most recent prompt with full content and context snapshot.

**Rationale**: Quick access to the last prompt used helps debug the most recent interaction.
**Priority**: Must Have

### FR-003: Preview Next Prompt
System MUST provide an endpoint to generate a preview of what the next system prompt would look like for a user, without actually sending a message.

**Rationale**: Developers need to verify prompt context before testing, especially after making configuration changes.
**Priority**: Must Have

### FR-004: Admin Authentication Required
System MUST require admin authentication for all prompt viewing endpoints.

**Rationale**: Prompts contain sensitive game state and persona information; access must be restricted.
**Priority**: Must Have

---

## Non-Functional Requirements

### Performance
- Prompt list endpoint response time < 500ms
- Latest prompt endpoint response time < 200ms
- Preview generation response time < 2s (includes LLM call)

### Security
- All endpoints require admin authentication (existing `get_current_admin_user` dependency)
- Rate limiting inherited from admin routes
- Prompt content not cached (fresh from database)

### Scalability
- Pagination support for prompt list (default 10, max 50)
- Preview generation is on-demand, not cached

---

## User Stories (CoD^Σ)

### US-1: List Recent Prompts (Priority: P1 - Must-Have)
```
Admin → List user's recent prompts → Debug prompt evolution
```
**Why P1**: Core functionality - can't debug without seeing prompt history

**Acceptance Criteria**:
- **AC-018-001**: Given an authenticated admin, When requesting `GET /admin/prompts/{user_id}`, Then return list of recent prompts (default 10) with id, token_count, generation_time_ms, meta_prompt_template, created_at
- **AC-018-002**: Given an authenticated admin, When requesting with `?limit=N` parameter, Then return N prompts (max 50)
- **AC-018-003**: Given a non-admin user, When requesting any prompt endpoint, Then return 403 Forbidden
- **AC-018-004**: Given a user_id that doesn't exist, When requesting prompts, Then return empty list (not 404)

**Independent Test**: Call endpoint with valid admin token, verify response structure
**Dependencies**: None

---

### US-2: View Latest Prompt Detail (Priority: P1 - Must-Have)
```
Admin → View full latest prompt → Understand exact context used
```
**Why P1**: Core debugging - need full prompt content to understand LLM behavior

**Acceptance Criteria**:
- **AC-018-005**: Given an authenticated admin, When requesting `GET /admin/prompts/{user_id}/latest`, Then return full prompt_content, token_count, generation_time_ms, meta_prompt_template, context_snapshot, created_at
- **AC-018-006**: Given a user with no prompts, When requesting latest, Then return null/empty with appropriate message
- **AC-018-007**: Given the latest prompt has conversation_id, Then include it in response

**Independent Test**: Generate a prompt for test user, then retrieve via endpoint, verify content matches
**Dependencies**: None

---

### US-3: Preview Next Prompt (Priority: P2 - Important)
```
Admin → Preview what next prompt would be → Verify configuration before testing
```
**Why P2**: Enhances P1 by allowing proactive debugging before conversation starts

**Acceptance Criteria**:
- **AC-018-008**: Given an authenticated admin, When requesting `POST /admin/prompts/{user_id}/preview`, Then generate and return a preview prompt without logging it to database
- **AC-018-009**: Given a user that doesn't exist, When requesting preview, Then return 404 Not Found
- **AC-018-010**: Given the preview generation, Then include the context_snapshot used for generation
- **AC-018-011**: Given the preview, Then indicate it's a preview (not a logged prompt) via `is_preview: true` flag

**Independent Test**: Request preview, verify prompt generated, verify NOT logged to generated_prompts table
**Dependencies**: P1 complete (need basic infrastructure)

---

## Intelligence Evidence

### Existing Infrastructure

**generated_prompts table** (Supabase):
```
id: uuid (PK)
user_id: uuid (FK → users)
conversation_id: uuid (nullable, FK → conversations)
prompt_content: text
token_count: integer
generation_time_ms: double precision
meta_prompt_template: varchar
context_snapshot: jsonb (nullable)
created_at: timestamptz
```

**Existing Admin Patterns** (nikita/api/routes/admin_debug.py):
- `GET /admin/system` - System overview stats
- `GET /admin/jobs` - Job execution status
- `GET /admin/users` - User list with pagination
- `GET /admin/users/{user_id}` - User detail
- `GET /admin/state-machines/{user_id}` - State machine status
- `POST /admin/neo4j-test` - Neo4j integration test

**MetaPromptService** (nikita/meta_prompts/service.py):
- `generate_system_prompt(user_id)` - Generates prompt and logs via `_log_prompt()`
- `_load_context(user_id)` - Loads full MetaPromptContext from DB
- Already handles all context injection

### CoD^Σ Trace
```
User_request ≫ existing_patterns ∘ table_analysis → requirements
Evidence: admin_debug.py patterns, generated_prompts schema, MetaPromptService._log_prompt()
```

---

## Scope

### In-Scope Features
- List recent prompts for a user (paginated)
- View full content of latest prompt
- Preview what next prompt would be
- Context snapshot visibility in all responses

### Out-of-Scope
- Editing or modifying prompts
- Deleting prompt history
- Comparing prompts side-by-side (future)
- Prompt template management (separate feature)
- Real-time prompt streaming (not needed)

### Future Phases
- **Phase 2**: Prompt diff viewer (compare two prompts)
- **Phase 3**: Prompt search by content

---

## Constraints

### Business Constraints
- Must integrate with existing admin dashboard patterns
- Must not require frontend changes (API-only for now)

### User Constraints
- Only admin users can access (not regular players)
- Admin must know user_id to query prompts

### Regulatory Constraints
- Prompts may contain user data - access logging recommended
- Prompts should not be exported in bulk (privacy)

---

## Risks & Mitigations (CoD^Σ)

### Risk 1: Preview generates but doesn't log - inconsistent with production
**Likelihood (p)**: 0.2 (Low)
**Impact**: 5 (Medium)
**Risk Score**: r = 1.0
**Mitigation**:
```
Risk → is_preview flag → Clear UI indication → No confusion
```
- Preview endpoint returns `is_preview: true` to distinguish from logged prompts
- Preview uses same generation path, just skips logging

### Risk 2: Large prompts cause slow responses
**Likelihood (p)**: 0.5 (Medium)
**Impact**: 2 (Low)
**Risk Score**: r = 1.0
**Mitigation**:
```
Risk → Pagination → Truncation option → Fast responses
```
- List endpoint returns metadata only (not full content)
- Full content only on latest/single prompt endpoints
- Optional `truncate=N` parameter for very long prompts

---

## Success Metrics

### User-Centric Metrics
- Admin can view any user's prompts within 2 clicks
- Debug time reduced by 50%+ (subjective, measured via dev feedback)

### Technical Metrics
- All endpoints respond in < 2s
- No errors in production (0 5xx responses)
- Test coverage > 80% for new endpoints

### Business Metrics
- Faster debugging of persona issues
- Reduced time to resolve user-reported "Nikita doesn't remember X" bugs

---

## Open Questions

None - all requirements clear from user description.

---

## Stakeholders

**Owner**: Simon (Developer/Admin)
**Created By**: Claude Code (SDD workflow)
**Reviewers**: N/A (solo project)
**Informed**: N/A

---

## Approvals

- [x] **Product Owner**: Simon - 2025-12-18
- [x] **Engineering Lead**: Simon - 2025-12-18

---

## Specification Checklist

**Before Planning**:
- [x] All [NEEDS CLARIFICATION] resolved (0/3)
- [x] All user stories have ≥2 acceptance criteria
- [x] All user stories have priority (P1, P2, P3)
- [x] All user stories have independent test criteria
- [x] P1 stories define MVP scope
- [x] Intelligence evidence provided (CoD^Σ traces)
- [x] Stakeholder approvals obtained

**Status**: Approved - Ready for Planning

---

**Version**: 1.0
**Last Updated**: 2025-12-18
**Next Step**: Run `/plan specs/018-admin-prompt-viewing/spec.md` to create implementation plan

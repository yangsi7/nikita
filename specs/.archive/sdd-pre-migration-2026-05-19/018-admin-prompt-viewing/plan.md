# Implementation Plan: Admin Prompt Viewing for Debugging

**Spec**: specs/018-admin-prompt-viewing/spec.md
**Created**: 2025-12-18
**Status**: Ready for Implementation

---

## CoD^Σ Dependency Analysis

```
Repository Layer (T1.x) → Schema Layer (T2.x) → Endpoint Layer (T3.x)
     ↓                         ↓                      ↓
get_recent_by_user_id    PromptListResponse    GET /admin/prompts/{user_id}
get_latest_by_user_id    PromptDetailResponse  GET /admin/prompts/{user_id}/latest
     ↓                         ↓                      ↓
MetaPromptService ───────────────────────────→ POST /admin/prompts/{user_id}/preview
```

**Critical Path**: T1.1 → T2.1 → T3.1 (list prompts) | T1.2 → T2.2 → T3.2 (latest) | T3.3 (preview uses existing MetaPromptService)

---

## User Story Tasks

### US-1: List Recent Prompts (P1)

#### T1.1: Add Repository Method for Recent Prompts
- **Description**: Add `get_recent_by_user_id(user_id, limit)` method to GeneratedPromptRepository
- **File**: `nikita/db/repositories/generated_prompt_repository.py`
- **Dependencies**: None
- **Acceptance Criteria**:
  - [AC-T1.1.1] Method returns list of GeneratedPrompt ordered by created_at DESC
  - [AC-T1.1.2] Method accepts limit parameter (default 10, max 50)
  - [AC-T1.1.3] Returns empty list for non-existent user_id (not exception)

#### T2.1: Create Pydantic Schemas for Prompt List
- **Description**: Add PromptListItem and PromptListResponse schemas
- **File**: `nikita/api/schemas/admin.py` (new file)
- **Dependencies**: None
- **Acceptance Criteria**:
  - [AC-T2.1.1] PromptListItem includes: id, token_count, generation_time_ms, meta_prompt_template, created_at
  - [AC-T2.1.2] PromptListResponse includes: items (list), count, user_id

#### T3.1: Implement List Prompts Endpoint
- **Description**: Add GET /admin/prompts/{user_id} endpoint
- **File**: `nikita/api/routes/admin_debug.py`
- **Dependencies**: T1.1, T2.1
- **Acceptance Criteria**:
  - [AC-T3.1.1] Endpoint requires admin authentication (get_current_admin_user)
  - [AC-T3.1.2] Accepts ?limit=N query parameter (clamped to 1-50)
  - [AC-T3.1.3] Returns 200 with PromptListResponse
  - [AC-T3.1.4] Returns empty list for non-existent user (not 404)
  - [AC-T3.1.5] Response time < 500ms

**US-1 Verification**: `AC-018-001, AC-018-002, AC-018-003, AC-018-004`

---

### US-2: View Latest Prompt Detail (P1)

#### T1.2: Add Repository Method for Latest Prompt
- **Description**: Add `get_latest_by_user_id(user_id)` method to GeneratedPromptRepository
- **File**: `nikita/db/repositories/generated_prompt_repository.py`
- **Dependencies**: None
- **Acceptance Criteria**:
  - [AC-T1.2.1] Method returns single GeneratedPrompt or None
  - [AC-T1.2.2] Returns most recent by created_at DESC LIMIT 1

#### T2.2: Create Pydantic Schema for Prompt Detail
- **Description**: Add PromptDetailResponse schema with full content
- **File**: `nikita/api/schemas/admin.py`
- **Dependencies**: T2.1 (same file)
- **Acceptance Criteria**:
  - [AC-T2.2.1] Includes all fields: id, prompt_content, token_count, generation_time_ms, meta_prompt_template, context_snapshot, conversation_id, created_at
  - [AC-T2.2.2] context_snapshot is Optional[dict]

#### T3.2: Implement Latest Prompt Endpoint
- **Description**: Add GET /admin/prompts/{user_id}/latest endpoint
- **File**: `nikita/api/routes/admin_debug.py`
- **Dependencies**: T1.2, T2.2
- **Acceptance Criteria**:
  - [AC-T3.2.1] Endpoint requires admin authentication
  - [AC-T3.2.2] Returns 200 with PromptDetailResponse or null body
  - [AC-T3.2.3] Returns null/empty with message for user with no prompts
  - [AC-T3.2.4] Response time < 200ms

**US-2 Verification**: `AC-018-005, AC-018-006, AC-018-007`

---

### US-3: Preview Next Prompt (P2)

#### T3.3: Implement Preview Prompt Endpoint
- **Description**: Add POST /admin/prompts/{user_id}/preview endpoint
- **File**: `nikita/api/routes/admin_debug.py`
- **Dependencies**: T2.2 (reuses PromptDetailResponse with is_preview flag)
- **Acceptance Criteria**:
  - [AC-T3.3.1] Endpoint requires admin authentication
  - [AC-T3.3.2] Calls MetaPromptService.generate_system_prompt() with skip_logging=True
  - [AC-T3.3.3] Returns 404 for non-existent user_id
  - [AC-T3.3.4] Returns PromptDetailResponse with is_preview=true flag
  - [AC-T3.3.5] Does NOT log to generated_prompts table
  - [AC-T3.3.6] Response time < 2s (includes LLM call)

#### T1.3: Add skip_logging Parameter to MetaPromptService
- **Description**: Modify generate_system_prompt() to accept skip_logging parameter
- **File**: `nikita/meta_prompts/service.py`
- **Dependencies**: None
- **Acceptance Criteria**:
  - [AC-T1.3.1] New parameter: skip_logging: bool = False
  - [AC-T1.3.2] When skip_logging=True, skips _log_prompt() call
  - [AC-T1.3.3] All existing callers unaffected (default False)

**US-3 Verification**: `AC-018-008, AC-018-009, AC-018-010, AC-018-011`

---

## Test Plan

### Unit Tests (required before implementation)

| Test File | Coverage |
|-----------|----------|
| `tests/db/repositories/test_generated_prompt_repository.py` | T1.1, T1.2 |
| `tests/api/routes/test_admin_debug.py` | T3.1, T3.2, T3.3 (add to existing) |
| `tests/meta_prompts/test_service.py` | T1.3 |

### Integration Tests

| Test | Description |
|------|-------------|
| test_list_prompts_with_data | Create prompts, verify list returns them |
| test_latest_prompt_content | Verify full prompt_content returned |
| test_preview_not_logged | Generate preview, verify NOT in database |

---

## Implementation Order

```
Phase 1 (Repository + Schemas):
T1.1 ⊕ T1.2 ⊕ T1.3 ⊕ T2.1 ⊕ T2.2  (parallel, no dependencies)

Phase 2 (Endpoints):
T3.1 ∘ T3.2 ∘ T3.3  (sequential, after Phase 1)
```

**Estimated Time**: 45-60 minutes

---

## Files to Modify

| File | Action | Tasks |
|------|--------|-------|
| `nikita/db/repositories/generated_prompt_repository.py` | MODIFY | T1.1, T1.2 |
| `nikita/meta_prompts/service.py` | MODIFY | T1.3 |
| `nikita/api/schemas/admin.py` | CREATE | T2.1, T2.2 |
| `nikita/api/routes/admin_debug.py` | MODIFY | T3.1, T3.2, T3.3 |
| `tests/db/repositories/test_generated_prompt_repository.py` | MODIFY | Tests for T1.1, T1.2 |
| `tests/meta_prompts/test_service.py` | MODIFY | Tests for T1.3 |
| `tests/api/routes/test_admin_debug.py` | MODIFY | Tests for T3.1, T3.2, T3.3 |

---

## Requirement Traceability

| Spec Requirement | Plan Tasks | Coverage |
|------------------|------------|----------|
| FR-001: List Recent Prompts | T1.1, T2.1, T3.1 | 100% |
| FR-002: View Latest Prompt | T1.2, T2.2, T3.2 | 100% |
| FR-003: Preview Next Prompt | T1.3, T3.3 | 100% |
| FR-004: Admin Auth Required | T3.1, T3.2, T3.3 | 100% |
| AC-018-001 through AC-018-011 | Mapped above | 100% |

---

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| MetaPromptService changes break callers | Default skip_logging=False |
| Large prompts slow responses | Only full content on /latest, not /list |
| Preview confused with logged | is_preview flag in response |

---

**Status**: Ready for `/tasks` generation

# Tasks: Admin Prompt Viewing for Debugging

**Spec**: specs/018-admin-prompt-viewing/spec.md
**Plan**: specs/018-admin-prompt-viewing/plan.md
**Created**: 2025-12-18
**Status**: Ready for Implementation

---

## US-1: List Recent Prompts (P1 - Must-Have)

### T1.1: Add Repository Method for Recent Prompts
- **Status**: [x] Complete
- **File**: `nikita/db/repositories/generated_prompt_repository.py`
- **Dependencies**: None
- **ACs**:
  - [ ] AC-T1.1.1: Method returns list of GeneratedPrompt ordered by created_at DESC
  - [ ] AC-T1.1.2: Method accepts limit parameter (default 10, max 50)
  - [ ] AC-T1.1.3: Returns empty list for non-existent user_id (not exception)
- **Test**: `tests/db/repositories/test_generated_prompt_repository.py::test_get_recent_by_user_id`

### T2.1: Create Pydantic Schemas for Prompt List
- **Status**: [x] Complete
- **File**: `nikita/api/schemas/admin.py` (CREATE)
- **Dependencies**: None
- **ACs**:
  - [ ] AC-T2.1.1: PromptListItem includes: id, token_count, generation_time_ms, meta_prompt_template, created_at
  - [ ] AC-T2.1.2: PromptListResponse includes: items (list), count, user_id
- **Test**: Schema validation in endpoint tests

### T3.1: Implement List Prompts Endpoint
- **Status**: [x] Complete
- **File**: `nikita/api/routes/admin_debug.py`
- **Dependencies**: T1.1, T2.1
- **ACs**:
  - [ ] AC-T3.1.1: Endpoint requires admin authentication (get_current_admin_user)
  - [ ] AC-T3.1.2: Accepts ?limit=N query parameter (clamped to 1-50)
  - [ ] AC-T3.1.3: Returns 200 with PromptListResponse
  - [ ] AC-T3.1.4: Returns empty list for non-existent user (not 404)
  - [ ] AC-T3.1.5: Response time < 500ms
- **Test**: `tests/api/routes/test_admin_debug.py::TestPromptEndpoints::test_list_prompts_*`
- **Spec ACs**: AC-018-001, AC-018-002, AC-018-003, AC-018-004

---

## US-2: View Latest Prompt Detail (P1 - Must-Have)

### T1.2: Add Repository Method for Latest Prompt
- **Status**: [x] Complete
- **File**: `nikita/db/repositories/generated_prompt_repository.py`
- **Dependencies**: None
- **ACs**:
  - [ ] AC-T1.2.1: Method returns single GeneratedPrompt or None
  - [ ] AC-T1.2.2: Returns most recent by created_at DESC LIMIT 1
- **Test**: `tests/db/repositories/test_generated_prompt_repository.py::test_get_latest_by_user_id`

### T2.2: Create Pydantic Schema for Prompt Detail
- **Status**: [x] Complete
- **File**: `nikita/api/schemas/admin.py`
- **Dependencies**: T2.1 (same file)
- **ACs**:
  - [ ] AC-T2.2.1: Includes all fields: id, prompt_content, token_count, generation_time_ms, meta_prompt_template, context_snapshot, conversation_id, created_at
  - [ ] AC-T2.2.2: context_snapshot is Optional[dict]
- **Test**: Schema validation in endpoint tests

### T3.2: Implement Latest Prompt Endpoint
- **Status**: [x] Complete
- **File**: `nikita/api/routes/admin_debug.py`
- **Dependencies**: T1.2, T2.2
- **ACs**:
  - [ ] AC-T3.2.1: Endpoint requires admin authentication
  - [ ] AC-T3.2.2: Returns 200 with PromptDetailResponse or null body
  - [ ] AC-T3.2.3: Returns null/empty with message for user with no prompts
  - [ ] AC-T3.2.4: Response time < 200ms
- **Test**: `tests/api/routes/test_admin_debug.py::TestPromptEndpoints::test_latest_prompt_*`
- **Spec ACs**: AC-018-005, AC-018-006, AC-018-007

---

## US-3: Preview Next Prompt (P2 - Important)

### T1.3: Add skip_logging Parameter to MetaPromptService
- **Status**: [x] Complete
- **File**: `nikita/meta_prompts/service.py`
- **Dependencies**: None
- **ACs**:
  - [ ] AC-T1.3.1: New parameter: skip_logging: bool = False
  - [ ] AC-T1.3.2: When skip_logging=True, skips _log_prompt() call
  - [ ] AC-T1.3.3: All existing callers unaffected (default False)
- **Test**: `tests/meta_prompts/test_service.py::test_generate_system_prompt_skip_logging`

### T3.3: Implement Preview Prompt Endpoint
- **Status**: [x] Complete
- **File**: `nikita/api/routes/admin_debug.py`
- **Dependencies**: T1.3, T2.2
- **ACs**:
  - [ ] AC-T3.3.1: Endpoint requires admin authentication
  - [ ] AC-T3.3.2: Calls MetaPromptService.generate_system_prompt() with skip_logging=True
  - [ ] AC-T3.3.3: Returns 404 for non-existent user_id
  - [ ] AC-T3.3.4: Returns PromptDetailResponse with is_preview=true flag
  - [ ] AC-T3.3.5: Does NOT log to generated_prompts table
  - [ ] AC-T3.3.6: Response time < 2s (includes LLM call)
- **Test**: `tests/api/routes/test_admin_debug.py::TestPromptEndpoints::test_preview_prompt_*`
- **Spec ACs**: AC-018-008, AC-018-009, AC-018-010, AC-018-011

---

## Implementation Order

```
Phase 1 (Parallel - No Dependencies):
T1.1 ⊕ T1.2 ⊕ T1.3 ⊕ T2.1 ⊕ T2.2

Phase 2 (Sequential - After Phase 1):
T3.1 → T3.2 → T3.3
```

---

## Progress Summary

| User Story | Tasks | Completed | Status |
|------------|-------|-----------|--------|
| US-1: List Recent Prompts | 3 | 3 | Complete |
| US-2: View Latest Prompt | 3 | 3 | Complete |
| US-3: Preview Next Prompt | 2 | 2 | Complete |
| **Total** | **8** | **8** | **Complete** |

---

## Verification Checklist

### Pre-Implementation
- [ ] All tests written before code
- [ ] Repository tests cover edge cases (empty, non-existent user)
- [ ] Endpoint tests cover auth, validation, response format

### Post-Implementation
- [ ] All 8 tasks marked complete
- [ ] All acceptance criteria checked
- [ ] All unit tests pass
- [ ] Deploy to Cloud Run
- [ ] Manual verification via curl/Postman

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-18 | Initial task generation |

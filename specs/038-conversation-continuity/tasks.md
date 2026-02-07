# Tasks: Spec 038 - Conversation Continuity & Session Management

## Progress Summary

| Phase | Tasks | Completed | Status |
|-------|-------|-----------|--------|
| Phase 1: Critical Bugs | 2 | 2 | ✅ Complete |
| Phase 2: Session Propagation | 4 | 4 | ✅ Complete |
| Phase 3: Token Budget | 3 | 0 | ⏭️ Skipped (Spec 030) |
| Phase 4: History Processor | 2 | 0 | ⏭️ Deferred (Optional) |
| **Total** | **11** | **6** | **100% (Critical)** |

### E2E Verification: ✅ PASS (2026-01-28)

| Check | Result | Evidence |
|-------|--------|----------|
| Message via Telegram | ✅ | Sent "Testing conversation continuity" |
| Conversation created | ✅ | `7bac745f-a90c-40a7-8806-9093bdff2004` |
| Prompt logged with FK | ✅ | `conversation_id` NOT NULL in generated_prompts |
| LLM response | ✅ | 444 chars, delivered successfully |
| No FK constraint errors | ✅ | Cloud Run logs clean |

---

## Phase 1: Fix Critical Bugs ✅ COMPLETE

### T1.1: Fix Stale Message Snapshot
- **Status**: [x] Complete
- **Priority**: P1 (CRITICAL)
- **File**: `nikita/platforms/telegram/message_handler.py`

**Description**: After `append_message()`, refresh conversation object from database.

**Acceptance Criteria**:
- [x] AC-1.1.1: Add `await self.conversation_repo.session.refresh(conversation)` after append_message
- [x] AC-1.1.2: Test verifies conversation.messages includes just-appended message
- [x] AC-1.1.3: Test verifies agent receives fresh message list

**Implementation**: Line 198 in message_handler.py
```python
await self.conversation_repo.session.refresh(conversation)
```

---

### T1.2: Fix Fragile Type Introspection
- **Status**: [x] Complete
- **Priority**: P1 (HIGH)
- **Files**:
  - `nikita/agents/text/history.py` (lines 147, 164, 197)
  - `nikita/agents/text/agent.py` (line 381)

**Description**: Replace string-based type check with proper isinstance().

**Acceptance Criteria**:
- [x] AC-1.2.1: Import `ModelResponse` from `pydantic_ai.messages`
- [x] AC-1.2.2: Replace `"Response" in msg.__class__.__name__` with `isinstance(msg, ModelResponse)`
- [x] AC-1.2.3: Test verifies detection works with actual ModelResponse objects

**Implementation**:
```python
# history.py:147
elif isinstance(msg, ModelResponse):

# agent.py:381
if isinstance(msg, _ModelResponse)
```

---

## Phase 2: Session Propagation ✅ COMPLETE

### T2.1: Add Session to NikitaDeps
- **Status**: [x] Complete
- **Priority**: P1 (HIGH)
- **File**: `nikita/agents/text/deps.py`

**Description**: Add optional session field to NikitaDeps dataclass.

**Acceptance Criteria**:
- [x] AC-2.1.1: Add `session: AsyncSession | None = None` field to NikitaDeps
- [x] AC-2.1.2: Import AsyncSession from sqlalchemy.ext.asyncio
- [x] AC-2.1.3: Update docstring to document session field

**Implementation**: Line 48 in deps.py
```python
session: "AsyncSession | None" = None  # Spec 038: Session propagation
```

**Tests**: 4 tests in `tests/agents/text/test_deps_session.py`

---

### T2.2: Update build_system_prompt
- **Status**: [x] Complete
- **Priority**: P1 (HIGH)
- **File**: `nikita/agents/text/agent.py`

**Description**: Add session parameter to build_system_prompt with fallback.

**Acceptance Criteria**:
- [x] AC-2.2.1: Add `session: AsyncSession | None = None` parameter
- [x] AC-2.2.2: When session provided, use it directly (no new session creation)
- [x] AC-2.2.3: When session=None, create new session (backwards compat)
- [x] AC-2.2.4: Prompt logged in same transaction as conversation

**Implementation**: Line 199 in agent.py
```python
async def build_system_prompt(
    memory: "NikitaMemory | None",
    user: "User",
    user_message: str,
    conversation_id: "UUID | None" = None,
    session: "AsyncSession | None" = None,  # Spec 038: Session propagation
) -> str:
```

**Tests**: 4 tests in `tests/agents/text/test_session_propagation.py`

---

### T2.3: Wire Session Through Caller Chain
- **Status**: [x] Complete
- **Priority**: P1 (HIGH)
- **Files**:
  - `nikita/agents/text/handler.py` (line 274)
  - `nikita/platforms/telegram/message_handler.py`

**Description**: Pass session through the call chain from MessageHandler to build_system_prompt.

**Acceptance Criteria**:
- [x] AC-2.3.1: TelegramMessageHandler has access to session via repository
- [x] AC-2.3.2: Session is passed to NikitaDeps during initialization
- [x] AC-2.3.3: TextAgentHandler receives session via deps

**Implementation**: Line 274 in handler.py
```python
deps.session = session
```

**Tests**: 3 tests in `tests/pipeline_fixes/test_session_chain.py`

---

### T2.4: Update generate_response
- **Status**: [x] Complete
- **Priority**: P1 (HIGH)
- **File**: `nikita/agents/text/agent.py`

**Description**: Pass deps.session to build_system_prompt.

**Acceptance Criteria**:
- [x] AC-2.4.1: `build_system_prompt()` call includes `session=deps.session`
- [x] AC-2.4.2: Works correctly when deps.session is None (fallback)

**Implementation**: Line 394 in agent.py
```python
deps.memory, deps.user, user_message, deps.conversation_id, deps.session
```

---

## Phase 3: Token Budget Coordination ⏭️ SKIPPED

**Reason**: Already implemented in Spec 030 via `TokenBudgetManager` in `nikita/agents/text/token_budget.py`

### T3.1: Create TokenBudgetConfig
- **Status**: ⏭️ Skipped
- **Reason**: `TokenBudgetManager` already exists with tier allocations

### T3.2: Wire TokenBudgetConfig to HistoryLoader
- **Status**: ⏭️ Skipped
- **Reason**: HistoryLoader already uses token budgeting

### T3.3: Wire TokenBudgetConfig to MetaPromptService
- **Status**: ⏭️ Skipped
- **Reason**: MetaPromptService already has token counting

---

## Phase 4: History Processor ⏭️ DEFERRED

**Reason**: Optional enhancement. Current HistoryLoader handles truncation adequately.

### T4.1: Implement History Processor
- **Status**: ⏭️ Deferred
- **Priority**: P3 (LOW)
- **Reason**: Not blocking MVP, can be added later for cleaner Pydantic AI integration

### T4.2: Wire to Agent Definition
- **Status**: ⏭️ Deferred
- **Priority**: P3 (LOW)
- **Reason**: Depends on T4.1

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-27 | Claude | Initial task breakdown |
| 1.1.0 | 2026-01-28 | Claude | Phase 1+2 complete, E2E verified, Phase 3+4 skipped/deferred |

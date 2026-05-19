# Spec 038: Conversation Continuity & Session Management Refactoring

## Executive Summary

**Objective**: Fix critical session management issues breaking conversation continuity and prompt logging.

**Severity**: CRITICAL - Nikita cannot remember conversations properly

**Root Cause Analysis**:
1. **FK Constraint Violation**: Prompts logged in NEW session before conversation committed
2. **Stale Message Snapshot**: `conversation.messages` not refreshed after `append_message()`
3. **Fragile Type Introspection**: `"Response" in __class__.__name__` will break on Pydantic AI updates
4. **Uncoordinated Token Budgets**: 3 separate budgets (3000 + 4500 + misc) not coordinated

**Good News** (from exploration):
- ✅ HistoryLoader exists and works (Spec 030)
- ✅ `message_history` IS passed to `agent.run()`
- ✅ Token budgeting exists (TokenBudgetManager)
- ✅ Summaries exist (per-conv + daily + context snapshots)
- ✅ Neo4j/Graphiti integration complete
- ✅ 4-tier memory architecture already implemented

---

## User Stories

### US-1: Session Propagation (Fix FK Constraint)

**As a** system operator
**I want** all database operations within a request to use the same session
**So that** FK constraints are respected and transactions are atomic

**Acceptance Criteria**:
- AC-1.1: `NikitaDeps` includes `session: AsyncSession | None` field
- AC-1.2: `build_system_prompt()` uses provided session instead of creating new one
- AC-1.3: `MessageHandler` passes its session through the call chain
- AC-1.4: `generated_prompts.conversation_id` is never NULL due to FK violation
- AC-1.5: All operations within a request use single database transaction

### US-2: Message State Consistency (Fix Stale Snapshot)

**As a** developer
**I want** conversation messages to always reflect the latest database state
**So that** the agent receives accurate conversation history

**Acceptance Criteria**:
- AC-2.1: After `append_message()`, conversation object reflects new message
- AC-2.2: No stale message snapshots passed to agent
- AC-2.3: Either refresh after append OR pass conversation_id only (not messages)

### US-3: Type-Safe Message Detection

**As a** developer
**I want** message type detection to use proper Python typing
**So that** code doesn't break when Pydantic AI updates

**Acceptance Criteria**:
- AC-3.1: Replace `"Response" in msg.__class__.__name__` with `isinstance()`
- AC-3.2: Import correct types from `pydantic_ai.messages`
- AC-3.3: All type checks are forward-compatible

### US-4: Coordinated Token Budget

**As a** system architect
**I want** a single source of truth for token allocation
**So that** context doesn't overflow and allocation is optimal

**Acceptance Criteria**:
- AC-4.1: Single `TokenBudgetConfig` with tier allocations
- AC-4.2: HistoryLoader respects global budget
- AC-4.3: MetaPromptService respects global budget
- AC-4.4: Total context stays under 20K tokens

---

## Non-Functional Requirements

- NFR-1: No database migrations required
- NFR-2: All existing 1248+ tests must continue to pass
- NFR-3: Backwards compatible with session=None fallback
- NFR-4: No new package dependencies required

---

## Out of Scope

- Changes to ElevenLabs voice agent
- Changes to Neo4j/Graphiti memory system
- Portal UI changes
- New conversation storage format

---

## Dependencies

- Pydantic AI >= 0.1.0 (for `ModelResponse`, `history_processors`)
- SQLAlchemy >= 2.0 (for async session refresh)

---

## Success Criteria

- [ ] No FK constraint violations in Cloud Run logs
- [ ] `generated_prompts.conversation_id` never NULL (new rows)
- [ ] No stale message snapshots in agent calls
- [ ] Type checks use `isinstance()` not string matching
- [ ] Single TokenBudgetConfig used across codebase
- [ ] history_processor limits context size
- [ ] All existing tests still pass
- [ ] Nikita remembers information from earlier in conversation

---

## References

- Spec 030: Text Continuity (HistoryLoader, TokenBudgetManager)
- Spec 037: Pipeline Refactoring (PipelineContext)
- Pydantic AI docs: https://docs.pydantic.dev/ai/

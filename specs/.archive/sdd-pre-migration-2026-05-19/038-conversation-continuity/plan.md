# Implementation Plan: Spec 038 - Conversation Continuity & Session Management

## Overview

This plan addresses 4 critical issues in conversation continuity by implementing fixes in 4 phases.

---

## Phase 1: Fix Critical Bugs (P1 Priority)

### T1.1: Fix Stale Message Snapshot (CRITICAL)

**File**: `nikita/platforms/telegram/message_handler.py`

**Problem**: After `append_message()`, `conversation.messages` is stale - doesn't include the just-appended user message.

**Solution**: Refresh conversation object from database after append.

```python
# BEFORE (line ~190-214):
await self.conversation_repo.append_message(conversation.id, "user", text)
# conversation.messages is STALE here!
decision = await self.text_agent_handler.handle(
    conversation_messages=conversation.messages,  # STALE!
)

# AFTER:
await self.conversation_repo.append_message(conversation.id, "user", text)
await self.conversation_repo.session.refresh(conversation)  # Refresh from DB
decision = await self.text_agent_handler.handle(
    conversation_messages=conversation.messages,  # FRESH!
)
```

**Tests**: `tests/platforms/telegram/test_message_handler_refresh.py` (2 tests)

### T1.2: Fix Fragile Type Introspection (HIGH)

**File**: `nikita/agents/text/agent.py`

**Problem**: Line ~360 uses `"Response" in msg.__class__.__name__` which breaks on Pydantic AI updates.

**Solution**: Use proper `isinstance()` check.

```python
# BEFORE (line ~360):
if hasattr(msg, "__class__") and "Response" in msg.__class__.__name__:

# AFTER:
from pydantic_ai.messages import ModelResponse

if isinstance(msg, ModelResponse):
```

**Tests**: `tests/agents/text/test_type_checking.py` (2 tests)

---

## Phase 2: Session Propagation (P1 Priority)

### T2.1: Add Session to NikitaDeps

**File**: `nikita/agents/text/deps.py`

Add optional session field with backwards-compatible default.

```python
from sqlalchemy.ext.asyncio import AsyncSession

@dataclass
class NikitaDeps:
    memory: "NikitaMemory | None"
    user: "User"
    settings: "Settings"
    generated_prompt: str | None = None
    conversation_messages: list[dict[str, Any]] | None = None
    conversation_id: UUID | None = None
    session: AsyncSession | None = None  # NEW: For session propagation
```

**Tests**: `tests/agents/text/test_deps_session.py` (2 tests)

### T2.2: Update build_system_prompt to Accept Session

**File**: `nikita/agents/text/agent.py`

Add session parameter with fallback for backwards compatibility.

```python
async def build_system_prompt(
    memory: "NikitaMemory | None",
    user: "User",
    user_message: str,
    conversation_id: "UUID | None" = None,
    session: "AsyncSession | None" = None,  # NEW
) -> str:
    if session is None:
        # Fallback: create new session (backwards compat)
        session_maker = get_session_maker()
        async with session_maker() as session:
            return await _generate_prompt(session, user, conversation_id)
    else:
        # Use provided session - no FK issues!
        return await _generate_prompt(session, user, conversation_id)
```

**Tests**: `tests/agents/text/test_session_propagation.py` (4 tests)

### T2.3: Wire Session Through Caller Chain

**Files**:
- `nikita/agents/text/handler.py`
- `nikita/platforms/telegram/message_handler.py`

Wire session from TelegramMessageHandler through to build_system_prompt.

**Tests**: `tests/pipeline_fixes/test_session_chain.py` (3 tests)

### T2.4: Update generate_response

**File**: `nikita/agents/text/agent.py`

Pass deps.session to build_system_prompt.

**Tests**: Covered by T2.2 tests

---

## Phase 3: Token Budget Coordination (P2 Priority)

### T3.1: Create TokenBudgetConfig

**File**: `nikita/agents/text/token_config.py` (NEW)

Single source of truth for token allocation across all tiers.

```python
@dataclass
class TokenBudgetConfig:
    """Single source of truth for token allocation."""

    TOTAL_BUDGET: int = 20_000  # 10% of Claude's 200K

    # Tier allocations
    SYSTEM_PROMPT: int = 5_000      # 25%
    MESSAGE_HISTORY: int = 7_000    # 35%
    SESSION_SUMMARIES: int = 2_500  # 12.5%
    USER_FACTS: int = 2_500         # 12.5%
    OUTPUT_RESERVE: int = 3_000     # 15%
```

**Tests**: `tests/agents/text/test_token_config.py` (3 tests)

### T3.2: Wire TokenBudgetConfig to HistoryLoader

**File**: `nikita/agents/text/history.py`

Use shared config instead of hardcoded 3000.

**Tests**: `tests/agents/text/test_token_config.py` (1 test)

### T3.3: Wire TokenBudgetConfig to MetaPromptService

**File**: `nikita/meta_prompts/service.py`

Use shared config for system prompt budget.

**Tests**: `tests/agents/text/test_token_config.py` (1 test)

---

## Phase 4: History Processor (P3 Priority)

### T4.1: Implement Nikita History Processor

**File**: `nikita/agents/text/history_processor.py` (NEW)

Custom history processor for cleaner message truncation.

```python
async def nikita_history_processor(
    ctx: RunContext,
    messages: list[ModelMessage],
) -> list[ModelMessage]:
    """Process message history for Nikita agent."""
    config = TokenBudgetConfig()
    max_tokens = config.MESSAGE_HISTORY

    if len(messages) > 40:
        return messages[-40:]
    return messages
```

**Tests**: `tests/agents/text/test_history_processor.py` (4 tests)

### T4.2: Wire to Agent Definition

**File**: `nikita/agents/text/agent.py`

Add history_processor to agent definition.

**Tests**: Covered by T4.1 tests

---

## File Summary

| File | Action | Phase | Lines Changed |
|------|--------|-------|---------------|
| `nikita/platforms/telegram/message_handler.py` | MODIFY | 1, 2 | ~10 |
| `nikita/agents/text/agent.py` | MODIFY | 1, 2, 4 | ~30 |
| `nikita/agents/text/deps.py` | MODIFY | 2 | ~5 |
| `nikita/agents/text/handler.py` | MODIFY | 2 | ~5 |
| `nikita/agents/text/token_config.py` | CREATE | 3 | ~50 |
| `nikita/agents/text/history_processor.py` | CREATE | 4 | ~40 |
| `nikita/agents/text/history.py` | MODIFY | 3 | ~10 |
| Tests (10 files) | CREATE | All | ~400 |

---

## Rollback Plan

| Component | Rollback Strategy |
|-----------|-------------------|
| Session propagation | `session=None` fallback creates new session |
| Message refresh | Remove `await session.refresh()` call |
| Type checking | Revert to string matching (not recommended) |
| TokenBudgetConfig | Hardcoded values still work |
| history_processor | Empty list in `history_processors` |

---

## Verification

### Unit Tests
```bash
pytest tests/platforms/telegram/test_message_handler_refresh.py -v
pytest tests/agents/text/test_type_checking.py -v
pytest tests/agents/text/test_deps_session.py -v
pytest tests/agents/text/test_session_propagation.py -v
pytest tests/pipeline_fixes/test_session_chain.py -v
pytest tests/agents/text/test_token_config.py -v
pytest tests/agents/text/test_history_processor.py -v
```

### E2E Test
1. Deploy to Cloud Run
2. Send via Telegram: "My name is TestUser and I love hiking"
3. Send follow-up: "What's my name and hobby?"
4. Expected: Nikita responds correctly (proves continuity)
5. Verify: `generated_prompts.conversation_id` not NULL

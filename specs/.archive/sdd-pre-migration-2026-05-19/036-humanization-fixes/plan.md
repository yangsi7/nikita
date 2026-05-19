# Spec 036: Implementation Plan

## Overview

Fix critical humanization layer bugs blocking bot functionality and data generation.

## Architecture

### Current State (Broken)

```
User Message → Webhook → MessageHandler → generate_response()
                                               ↓
                                        build_system_prompt()
                                               ↓
                                        Neo4j queries (61s cold start)
                                               ↓
                                        ⚠️ TIMEOUT (Cloud Run 60s default)
                                               ↓
                                        Request killed, no response
```

### Target State (Fixed)

```
User Message → Webhook → MessageHandler → generate_response()
                                               ↓
                           ┌─────────────────────────────────────┐
                           │ asyncio.wait_for(timeout=120s)     │
                           │ ↓                                   │
                           │ build_system_prompt()               │
                           │ ↓                                   │
                           │ Neo4j queries (pooled, warm <5s)    │
                           │ ↓                                   │
                           │ LLM call                            │
                           └─────────────────────────────────────┘
                                               ↓
                           Response (or graceful timeout message)
```

## Implementation Phases

### Phase 1: P0 Fixes - Bot Functionality Restoration (2 hours)

| Task | Description | Files |
|------|-------------|-------|
| T1.1 | Deploy with Cloud Run timeout 300s | CLI deployment |
| T1.2 | Add LLM timeout wrapper (120s) | `nikita/agents/text/agent.py` |
| T1.3 | Fix narrative arc method signature | `nikita/context/post_processor.py` |

### Phase 2: P1 Fixes - Data Generation (1.5 hours)

| Task | Description | Files |
|------|-------------|-------|
| T2.1 | Propagate social circle errors | `nikita/onboarding/handoff.py` |
| T2.2 | Add Neo4j connection pooling | `nikita/memory/graphiti_client.py` |

### Phase 3: P2 Fixes - Observability (30 min)

| Task | Description | Files |
|------|-------------|-------|
| T3.1 | Add timeout monitoring middleware | `nikita/api/main.py` |

### Phase 4: Verification (1 hour)

| Task | Description | Method |
|------|-------------|--------|
| T4.1 | Run full test suite | pytest |
| T4.2 | E2E via Telegram | Telegram MCP |
| T4.3 | Verify narrative arc generation | Supabase query |

## Critical Code Changes

### T1.2: LLM Timeout Wrapper

**File**: `nikita/agents/text/agent.py`
**Location**: `generate_response()` method (~line 383)

```python
# BEFORE
result = await nikita_agent.run(
    user_prompt=message.content,
    message_history=messages,
    deps=deps,
)

# AFTER
try:
    result = await asyncio.wait_for(
        nikita_agent.run(
            user_prompt=message.content,
            message_history=messages,
            deps=deps,
        ),
        timeout=120.0
    )
except asyncio.TimeoutError:
    logger.error(f"LLM timeout after 120s for user {user_id}")
    # Return graceful fallback
    return "Sorry, I'm having trouble thinking right now. Let me get back to you!"
```

### T1.3: Fix Narrative Arc Method Signature

**File**: `nikita/context/post_processor.py`
**Location**: `_update_narrative_arcs()` method (~line 973)

```python
# BEFORE (WRONG - missing 2 params)
if self.arcs.should_start_new_arc(
    vulnerability_level=vulnerability_level,
    days_since_last=days_since_last_arc,
):

# AFTER (CORRECT - all 4 params)
if self.arcs.should_start_new_arc(
    active_arcs=active_arcs,
    vulnerability_level=vulnerability_level,
    chapter=chapter,
    days_since_last_arc=days_since_last_arc,
):
```

### T2.1: Social Circle Error Propagation

**File**: `nikita/onboarding/handoff.py`
**Location**: `generate_and_store_social_circle()` (~line 245)

```python
# BEFORE (silently fails)
except Exception:
    return False

# AFTER (logs error with traceback)
except Exception as e:
    logger.error(
        f"Social circle generation failed for user {user_id}: {e}",
        exc_info=True
    )
    raise  # Or return False but at least log
```

### T2.2: Neo4j Connection Pooling

**File**: `nikita/memory/graphiti_client.py`
**Approach**: Create singleton driver at module level

```python
# At module level
_driver_instance: Optional[AsyncDriver] = None

async def get_driver() -> AsyncDriver:
    global _driver_instance
    if _driver_instance is None:
        _driver_instance = AsyncGraphDatabase.driver(
            uri=settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )
    return _driver_instance
```

## TDD Test Plan

### Tests to Write BEFORE Implementation

```
tests/
├── agents/text/
│   └── test_llm_timeout.py          # T1.2 tests (4 tests)
├── context/
│   └── test_post_processor_arcs.py  # T1.3 tests (4 tests) - UPDATE
├── onboarding/
│   └── test_handoff_social_circle.py # T2.1 tests (3 tests) - UPDATE
└── memory/
    └── test_neo4j_connection_pooling.py # T2.2 tests (3 tests)
```

## Verification Commands

```bash
# Phase 1 verification - Cloud Run timeout
gcloud run services describe nikita-api --region us-central1 \
  --format="value(spec.template.spec.timeoutSeconds)"
# Expected: 300

# Phase 2 verification - Run Spec 036 tests
pytest tests/agents/text/test_llm_timeout.py \
       tests/context/test_post_processor_arcs.py \
       tests/onboarding/test_handoff_social_circle.py \
       tests/memory/test_neo4j_connection_pooling.py -v

# Phase 4 - Full test suite
pytest tests/ -v --ignore=tests/e2e -x
```

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Neo4j driver singleton creates threading issues | Use asyncio locks for initialization |
| Timeout wrapper breaks error handling | Preserve original exceptions, only catch TimeoutError |
| Social circle error propagation breaks onboarding | Log error but still return False to allow onboarding to continue |

## Rollback Plan

If deployment fails:
1. Revert to previous Cloud Run revision: `gcloud run services update-traffic nikita-api --to-revisions=PREVIOUS=100`
2. All code changes are additive (timeout wrapper, error logging) - can be removed independently

## Dependencies

- Cloud Run CLI (`gcloud`)
- Telegram MCP for E2E testing
- Supabase MCP for verification queries

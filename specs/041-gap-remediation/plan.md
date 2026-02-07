# Spec 041: Gap Remediation - Implementation Plan

**Status**: IN_PROGRESS
**Created**: 2026-01-30

## Overview

This plan addresses 29 gaps identified in the deep audit across security, voice, pipeline, performance, and quality domains.

## Research Findings

### Admin JWT (P0-2)
- Function `get_current_admin_user` already fully implemented at `nikita/api/dependencies/auth.py:118-203`
- Validates Supabase JWT and checks admin email domain
- Only needs wiring to admin routes (10 min fix)

### Error Logging (P0-3)
- Infrastructure 100% complete: `ErrorLog` model, `log_error()` utility, admin endpoint
- Needs global exception handler in `main.py`

### Transcript Extraction (P0-4)
- Current `_extract_facts_via_llm()` is a stub returning empty list
- Implement using Pydantic AI with Claude (consistent with text agent pattern)

### Orchestrator (P1-1)
- All 11 stage classes exist in `nikita/context/stages/`
- 160 tests passing
- Need to refactor `post_processor.py:169-450` to use stage classes

## Technical Approach

### Phase 1: Security + Voice Hardening

**T1.1 Admin JWT Wiring**
```python
# nikita/api/routes/admin.py
from nikita.api.dependencies.auth import get_current_admin_user
get_current_admin_user_id = get_current_admin_user  # Alias for existing routes
```

**T1.2 Error Logging Handler**
```python
# nikita/api/main.py
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    await log_error(session, str(exc), f"nikita.api:{request.url.path}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
```

**T1.4 Transcript LLM Extraction**
```python
# nikita/agents/voice/transcript.py
from pydantic_ai import Agent

class ExtractedFact(BaseModel):
    fact: str
    category: str  # occupation, hobby, relationship, preference, biographical, emotional

extract_agent = Agent("anthropic:claude-sonnet-4-20250514", result_type=FactExtractionResult)
```

### Phase 2: Pipeline + Performance

**T2.1 Orchestrator Refactor**
Target architecture:
```python
async def process_conversation(self, conversation_id):
    stages = [IngestionStage, ExtractionStage, GraphUpdatesStage, ...]
    context = PipelineContext(conversation_id=conversation_id)
    for stage in stages:
        result = await stage(self.session).execute(context, input)
        if result.failure and stage.is_critical:
            break
    return self._build_result(context)
```

### Phase 3: Quality

**T3.1 Test Collection Errors**
- Check for missing dependencies
- Fix import errors in conftest.py
- Verify venv integrity

## Dependencies

```
Phase 1 (Security/Voice)
├── T1.1 Admin JWT → Independent
├── T1.2 Error Logging → Independent
├── T1.3 Voice Logging → Independent (Verified)
├── T1.4 Transcript LLM → Independent
├── T1.5 Onboarding DB → Independent (Verified)
├── T1.6 Meta-prompts → Independent (Verified)
└── T1.7 Thread Loading → Independent (Verified)

Phase 2 (Pipeline)
├── T2.1 Orchestrator → Unblocks T2.2, T2.3, T2.4
├── T2.2 Pipeline Health → Depends on T2.1
├── T2.3 Thread Logging → Depends on T2.1
└── T2.4 Integration Tests → Depends on T2.1

Phase 3 (Quality)
├── T3.1 Test Errors → Independent
├── T3.2 CLAUDE.md → Independent (Verified)
└── T3.4 E2E Automation → After T3.1
```

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Orchestrator regression | MEDIUM | HIGH | 160 existing stage tests, incremental refactor |
| JWT breaks access | LOW | MEDIUM | Auth already implemented, just wiring |
| Test fixes cascade | LOW | MEDIUM | Fix collection errors first |

## Implementation Sequence

1. **Quick Wins (Day 1)**:
   - T1.1: Wire Admin JWT (10 min)
   - T1.2: Wire Error Logging (2-3h)
   - Verify P0-1, P0-5, P0-6, P0-7 are done

2. **Voice (Day 1-2)**:
   - T1.4: Transcript LLM Extraction (4-6h)

3. **Pipeline (Days 3-5)**:
   - T2.1: Orchestrator Refactor (4h)
   - T2.2-T2.4: Dependent tasks

4. **Performance (Days 6-8)**:
   - T2.6-T2.10: UsageLimits, Neo4j batch, caching, integrations

5. **Quality (Days 9-10)**:
   - T3.1: Fix test errors
   - T3.4: E2E automation

## Test Strategy

- Run affected tests after each change
- Full test suite before deployment
- E2E verification via Telegram MCP

## Success Criteria

- All 29 gaps addressed or explicitly deferred
- Spec 037 upgraded to PASS
- 0 test collection errors
- 100% admin routes protected by JWT

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `nikita/api/routes/admin.py` | Modify | Wire JWT |
| `nikita/api/main.py` | Modify | Add error handler |
| `nikita/agents/voice/transcript.py` | Modify | LLM extraction |
| `nikita/context/post_processor.py` | Modify | Orchestrator |
| `tests/agents/voice/test_transcript.py` | Modify | Add tests |

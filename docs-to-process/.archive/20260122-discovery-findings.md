# Admin Monitoring Dashboard - Discovery Findings

**Created**: 2026-01-22
**Status**: Phase 1 Complete - 5 Agents Synthesized

---

## Executive Summary

Discovery revealed a solid foundation with significant enhancement opportunities:
- **21 functional endpoints** in admin_debug.py (specs 016-020 implemented)
- **17 stub endpoints** in admin.py (need activation)
- **8 monitoring-relevant tables** with established repository patterns
- **3 Neo4j graphs** accessible via Graphiti client
- **9-stage pipeline** with JobExecution tracking (Spec 031)

---

## 1. Current Admin State (Agent 1)

### Endpoint Inventory

| Router | Endpoints | Status | Evidence |
|--------|-----------|--------|----------|
| admin.py | 17 | STUB (403 always) | admin.py:1-595 |
| admin_debug.py | 21 | FUNCTIONAL | admin_debug.py:1-1413 |

### Functional Endpoints (admin_debug.py)

| Endpoint | Method | Purpose | Evidence |
|----------|--------|---------|----------|
| /admin/users | GET | List users with pagination | admin_debug.py:45-89 |
| /admin/users/{id} | GET | Single user details | admin_debug.py:91-120 |
| /admin/conversations | GET | Conversation list | admin_debug.py:122-178 |
| /admin/conversations/{id} | GET | Full conversation thread | admin_debug.py:180-230 |
| /admin/prompts/recent | GET | Recent generated prompts | admin_debug.py:232-280 |
| /admin/prompts/{id} | GET | Single prompt details | admin_debug.py:282-320 |
| /admin/jobs | GET | Job execution history | admin_debug.py:322-380 |
| /admin/processing-stats | GET | Pipeline statistics | admin_debug.py:528-580 |
| /admin/voice/sessions | GET | Voice session list | admin_debug.py:582-640 |
| /admin/voice/sessions/{id} | GET | Voice session detail | admin_debug.py:642-700 |

### Authentication Pattern

```python
# nikita/api/dependencies/auth.py:118-203
async def get_current_admin_user(token: str) -> User:
    # Validates JWT + @silent-agents.com domain
    if not user.email.endswith("@silent-agents.com"):
        raise HTTPException(403, "Admin access denied")
```

### UI Components (portal/src/app/admin/)

| Page | Path | Purpose |
|------|------|---------|
| Users | /admin/users | User management |
| Voice | /admin/voice | Voice session monitoring |
| Text | /admin/text | Text conversation monitoring |
| Prompts | /admin/prompts | Generated prompt viewing |
| Jobs | /admin/jobs | Job execution logs |

### Gaps Identified (G1-G5)

| Gap | Description | Priority |
|-----|-------------|----------|
| G1 | admin.py stub auth blocks endpoints | P0 |
| G2 | Missing memory graphs visibility | P0 |
| G3 | No time-series/chart endpoints | P1 |
| G4 | No drill-down navigation helpers | P1 |
| G5 | No export/bulk operations | P2 |

---

## 2. Memory Architecture (Agent 2)

### Generated Prompt Flow

```
User Message
    ↓
MessageHandler.handle_message()
    ↓ (calls MetaPromptService)
_load_context() → queries 3 graphs via NikitaMemory
    ↓
generate_system_prompt() via Haiku
    ↓
Store GeneratedPrompt (token_count, context_snapshot)
    ↓
nikita_agent (text) / ElevenLabs (voice)
    ↓
PostProcessor.process_conversation() [async after 15min]
    ↓
Update Neo4j graphs + daily_summaries + vice_preferences
```

### 9-Stage Post-Processing Pipeline

| Stage | Location | Purpose | Output |
|-------|----------|---------|--------|
| 1. Ingestion | post_processor.py:323-345 | Load conversation | status='processing' |
| 2. Extraction | post_processor.py:347+ | LLM extract facts | ExtractionResult |
| 3. Analysis | post_processor.py:212-222 | Store summary | summary, emotional_tone |
| 4. Threads | post_processor.py:225-230 | Create threads | conversation_threads |
| 5. Thoughts | post_processor.py:234-238 | Create thoughts | nikita_thoughts |
| 6. Graph Updates | post_processor.py:242-246 | Update Neo4j | 3 graphs |
| 7. Rollups | post_processor.py:249-253 | Daily summaries | daily_summaries |
| 7.5. Vice Processing | post_processor.py:257-258 | Detect vices | user_vice_preferences |
| 7.7. Cache Invalidation | post_processor.py:262 | Clear voice cache | User.voice_cache_key |
| 8. Finalization | post_processor.py:266-271 | Mark complete | status='processed' |

### 3-Graph Memory System

| Graph | Purpose | Token Budget | Evidence |
|-------|---------|--------------|----------|
| user_graph | Facts about player | 20-50 facts | graphiti_client.py:83-110 |
| relationship_graph | Shared history | 10-30 episodes | graphiti_client.py:112-149 |
| nikita_graph | Her simulated life | 5-20 events | graphiti_client.py:151-195 |

---

## 3. Database Infrastructure (Agent 3)

### Monitoring-Relevant Tables

| Table | Primary Key | Monitoring Use | Evidence |
|-------|-------------|----------------|----------|
| users | uuid | User state, game progress | user.py:36-199 |
| conversations | uuid | Session tracking | conversation.py:31-155 |
| generated_prompts | uuid | Prompt debugging | generated_prompt.py:19-63 |
| score_history | uuid | Score timeline | game.py:19-65 |
| job_executions | uuid | Pipeline monitoring | job_execution.py:37-82 |
| daily_summaries | uuid | Daily aggregations | game.py:69-128 |
| conversation_threads | uuid | Open thread tracking | context.py:61-120 |
| nikita_thoughts | uuid | Thought lifecycle | context.py:123-191 |

### Entity Relationships

```
User (1)
  ├── Conversations (N) [user_id]
  │     ├── Messages (N) [embedded JSONB]
  │     ├── GeneratedPrompts (N) [conversation_id]
  │     └── ConversationThreads (N) [conversation_id]
  ├── ScoreHistory (N) [user_id]
  ├── DailySummaries (N) [user_id]
  ├── JobExecutions (N) [user_id]
  └── UserVicePreferences (N) [user_id]
```

### Existing Repository Methods

| Method | Location | Purpose |
|--------|----------|---------|
| detect_stuck() | conversation_repository.py:287-313 | Find stuck conversations |
| get_recent_executions() | job_execution_repository.py:44-69 | Recent job history |
| get_recent_by_user_id() | generated_prompt_repository.py:106-129 | User's recent prompts |
| get_daily_stats() | score_history_repository.py:82-133 | Daily score statistics |

---

## 4. Related Specs Patterns (Agent 4)

### Reusable Patterns

| Pattern | Source | Applicability | Evidence |
|---------|--------|---------------|----------|
| Repository Query | detect_stuck() | ✅ High | conversation_repository.py:287 |
| Job Tracking | JobExecution model | ✅ High | job_execution.py:37 |
| Token Monitoring | TokenBudgetManager | ✅ Medium | token_budget.py |
| Multi-Graph Queries | _get_user_facts() | ✅ Medium | service.py:296 |
| Admin Response Schema | ProcessingStatsResponse | ✅ High | admin.py:23 |

### Test Pattern (Spec 031)

```python
# tests/api/routes/test_admin_processing_stats.py:17-40
@pytest.fixture
def app(self, mock_session):
    test_app = FastAPI()
    test_app.include_router(router, prefix="/admin")
    test_app.dependency_overrides[get_current_admin_user_id] = mock_admin_auth
    test_app.dependency_overrides[get_async_session] = mock_get_session
```

---

## 5. External Research (Agent 5)

### Five Monitoring Layers (Portkey + Datadog)

| Layer | Metrics | Implementation |
|-------|---------|----------------|
| Reliability | P95 latency, success rate | FastAPI middleware |
| Quality | Eval pass rate, grounding | LLM-based scoring |
| Safety | Guardrail pass, PII detection | Pre/post filters |
| Cost | Token usage per request | Counter with labels |
| Governance | Trace coverage, audit | Structured logging |

### shadcn/ui Recommendations

- **DataTable** + TanStack Table (sorting, filtering, pagination)
- **Card** for metric summaries
- **Badge** for status indicators
- **Skeleton** for loading states
- **Alert** for warnings/errors

### Error Categorization (Langfuse)

1. Gather 50-100 diverse traces
2. Open coding: Binary pass/fail + descriptions
3. Structure via LLM clustering (6-8 categories)
4. Label and quantify for analytics

---

## 6. Synthesis: Build Plan

### Phase 1: Foundation (Existing Infrastructure)

**Leverage**:
- admin_debug.py endpoints (21 functional)
- Repository methods (detect_stuck, get_recent_executions)
- ProcessingStatsResponse schema pattern
- Auth: @silent-agents.com validation

**Activate**:
- admin.py stub endpoints → route to admin_debug implementations

### Phase 2: New Endpoints Needed

| Endpoint | Method | Purpose | Priority |
|----------|--------|---------|----------|
| /admin/users/{id}/conversations | GET | User's conversation list | P0 |
| /admin/users/{id}/memory | GET | User's 3-graph memory | P0 |
| /admin/users/{id}/scores | GET | Score timeline chart data | P0 |
| /admin/conversations/{id}/prompts | GET | All prompts for conversation | P0 |
| /admin/conversations/{id}/pipeline | GET | 9-stage pipeline status | P1 |
| /admin/metrics/overview | GET | System-wide metrics | P1 |
| /admin/errors | GET | Error log with filters | P1 |

### Phase 3: UI Components

**Dashboard Structure** (Tabbed):
```
/admin/monitoring
├── Overview (summary cards + recent activity)
├── Users (list → user detail → conversations)
├── Conversations (list → thread + prompts + scoring)
├── Prompts (list → prompt detail with layers)
├── Scoring (chart + timeline table)
├── Voice (session list → transcript + scoring)
├── Memory (3-graph visualization per user)
├── Jobs (execution list → detail with trace)
└── Errors (filterable log)
```

### Phase 4: Data Flow

```
Dashboard → API Endpoint → Repository → Database/Neo4j
    ↓
React Query → useSWR/fetch → FastAPI → SQLAlchemy/Graphiti
    ↓
shadcn DataTable → Server-side pagination → Efficient queries
```

---

## 7. Conflicts Resolution

| Conflict | Resolution | Evidence |
|----------|------------|----------|
| admin.py vs admin_debug.py | Use admin_debug.py patterns | admin_debug.py functional |
| Pagination strategy | Server-side (existing pattern) | conversation_repository.py uses offset/limit |
| Chart library | Recharts (portal already uses) | portal/package.json |

---

## 8. Next Steps

1. **Phase 2**: Build Tree-of-Thought dependency visualization
2. **Phase 3**: Create SDD spec via /feature auto-chain
3. **Phase 4**: TDD implementation per user story

---

## Evidence Index

| Finding | Primary Source | Line |
|---------|----------------|------|
| Stub auth | admin.py | 1-595 |
| Functional endpoints | admin_debug.py | 1-1413 |
| Auth validation | auth.py | 118-203 |
| detect_stuck() | conversation_repository.py | 287-313 |
| Pipeline stages | post_processor.py | 158-321 |
| 3-graph memory | graphiti_client.py | 25-286 |
| JobExecution model | job_execution.py | 37-82 |
| TokenBudgetManager | token_budget.py | NEW (Spec 030) |

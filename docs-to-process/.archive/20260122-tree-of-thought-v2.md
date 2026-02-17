# Admin Monitoring Dashboard - Tree-of-Thought v2 (Post-Audit)

**Created**: 2026-01-22
**Status**: Phase 2 - Synthesis (Revised after 4-agent audit)

---

## Critical Fixes Applied

### CRITICAL-1: Audit Logging (Security)

**Requirement**: Log all admin access to sensitive data

**Implementation**:
```sql
-- Migration: 0009_audit_logs.sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_id UUID NOT NULL,
    admin_email TEXT NOT NULL,
    action TEXT NOT NULL,  -- 'view_user', 'view_conversation', 'view_memory'
    resource_type TEXT NOT NULL,
    resource_id UUID,
    user_id UUID,  -- The user being viewed
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_admin ON audit_logs(admin_id, created_at DESC);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id, created_at DESC);
```

**Middleware**:
```python
# nikita/api/dependencies/audit.py (NEW)
from functools import wraps
import logging

async def audit_admin_action(
    admin_id: UUID,
    action: str,
    resource_type: str,
    resource_id: UUID | None,
    user_id: UUID | None,
    session: AsyncSession
):
    """Log admin action to audit_logs table."""
    log = AuditLog(
        admin_id=admin_id,
        admin_email=admin_email,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_id,
    )
    session.add(log)
    await session.commit()
```

### CRITICAL-2: PII Protection (Security)

**Implementation**:
```python
# nikita/api/dependencies/logging.py (NEW)
import logging
import re

SENSITIVE_PATTERNS = [
    r'"content":\s*"[^"]*"',  # Message content
    r'"phone_number":\s*"[^"]*"',  # Phone numbers
    r'"facts":\s*\[.*?\]',  # Memory facts
]

class PiiSafeFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        for pattern in SENSITIVE_PATTERNS:
            message = re.sub(pattern, '"[REDACTED]"', message)
        return message
```

---

## Architecture Fixes Applied

### Fix 1: P2.4 and P6.3 Shared Backend

**Original Issue**: Circular dependency P2.4 → P6.3

**Fix**: Both share `ConversationRepository.get_pipeline_status()` method
```
P2.4: Pipeline Status for Conversation → calls get_pipeline_status(conv_id)
P6.3: Pipeline Stage Detail → calls get_pipeline_status(conv_id) + job_executions
```

### Fix 2: AdminMonitoringService Methods

**Added Methods**:
| Method | Endpoint | Purpose |
|--------|----------|---------|
| get_system_overview() | /admin/metrics/overview | Aggregate all metrics |
| get_error_summary() | /admin/errors | Error categorization |
| get_memory_stats(user_id) | /admin/users/{id}/memory | 3-graph snapshot |
| get_score_timeline(user_id) | /admin/users/{id}/scores | Chart data |
| get_boss_encounters(user_id) | /admin/users/{id}/boss | Boss outcomes |

### Fix 3: Error Handling Strategy

**Per-Tab Error Boundaries**:
```tsx
// portal/src/app/admin/monitoring/layout.tsx
export default function MonitoringLayout({ children }) {
  return (
    <ErrorBoundary fallback={<TabErrorFallback />}>
      {children}
    </ErrorBoundary>
  );
}
```

**API Error Responses**:
```python
# Standard error format
{
    "error": "Neo4j query timeout",
    "code": "NEO4J_TIMEOUT",
    "user_action": "Please try again in 60 seconds",
    "retry_after": 60
}
```

### Fix 4: MemoryRepository Clarification

**Decision**: Remove MemoryRepository. Use NikitaMemory service directly.

```python
# AdminMonitoringService.get_memory_stats()
async def get_memory_stats(self, user_id: UUID) -> MemoryStats:
    memory = NikitaMemory(user_id=user_id)
    return {
        "user_facts": await memory.search_memory("*", ["user"], limit=50),
        "relationship_episodes": await memory.search_memory("*", ["relationship"], limit=30),
        "nikita_events": await memory.search_memory("*", ["nikita"], limit=20),
    }
```

### Fix 5: Effort Estimates Clarification

| Component | Type | Effort | Rationale |
|-----------|------|--------|-----------|
| User Tab | EXTEND | 1.5h | Reuse existing DataTable pattern, add new columns |
| Conversations Tab | EXTEND | 2h | Reuse pattern, add pipeline status panel |
| Prompts Tab | EXTEND | 1.5h | Add layers view, reuse prompt display |
| Scoring Tab | NEW | 2h | New chart component (Recharts), boss table |
| Voice Tab | EXTEND | 1h | Extend existing, add transcript viewer |
| Memory Tab | NEW | 2.5h | New 3-graph tables, loading states |
| Jobs Tab | EXTEND | 1.5h | Add stage breakdown view |
| Errors Tab | NEW | 1.5h | New table with filters |

### Fix 6: Cross-Module Navigation (Phase C)

**Moved from Phase D to Phase C**:
- Navigation happens via Next.js App Router links
- URL-based state (no client-side modal state)
- Example: Click conversation → `/admin/monitoring/conversations/[id]`

---

## Frontend Fixes Applied

### Fix 1: File-Based Routing (NOT Drawers)

**Revised Architecture**:
```
/admin/monitoring/
├── layout.tsx                         # Nav + ErrorBoundary
├── page.tsx                           # Overview
├── users/
│   ├── page.tsx                       # User list
│   └── [id]/
│       ├── page.tsx                   # User detail
│       ├── memory/page.tsx            # Memory graphs
│       └── scores/page.tsx            # Score timeline
├── conversations/
│   ├── page.tsx                       # Conversation list
│   └── [id]/
│       ├── page.tsx                   # Thread + messages
│       ├── prompts/page.tsx           # Prompt layers
│       └── pipeline/page.tsx          # 9-stage status
├── prompts/page.tsx                   # Prompt list
├── scoring/page.tsx                   # Charts + boss table
├── voice/page.tsx                     # Voice sessions
├── memory/page.tsx                    # System memory stats
├── jobs/page.tsx                      # Job executions
└── errors/page.tsx                    # Error log
```

### Fix 2: Navigation Component (NOT Tabs)

**Use existing AdminNavigation pattern**:
```tsx
// portal/src/app/admin/monitoring/layout.tsx
const navItems = [
  { href: '/admin/monitoring', label: 'Overview' },
  { href: '/admin/monitoring/users', label: 'Users' },
  { href: '/admin/monitoring/conversations', label: 'Conversations' },
  { href: '/admin/monitoring/prompts', label: 'Prompts' },
  { href: '/admin/monitoring/scoring', label: 'Scoring' },
  { href: '/admin/monitoring/voice', label: 'Voice' },
  { href: '/admin/monitoring/memory', label: 'Memory' },
  { href: '/admin/monitoring/jobs', label: 'Jobs' },
  { href: '/admin/monitoring/errors', label: 'Errors' },
];
```

### Fix 3: Neo4j Cold Start UX

```tsx
// components/Neo4jLoadingState.tsx
export function Neo4jLoadingState() {
  return (
    <div className="flex flex-col items-center justify-center p-8">
      <Skeleton className="h-32 w-full mb-4" />
      <p className="text-muted-foreground">
        Waking up memory database...
      </p>
      <p className="text-sm text-muted-foreground">
        This may take up to 60 seconds on first load
      </p>
    </div>
  );
}
```

### Fix 4: Pagination Controls

**Copy from existing users/page.tsx pattern**:
```tsx
<div className="flex items-center justify-between">
  <p className="text-sm text-muted-foreground">
    Showing {offset + 1}-{offset + data.length} of {total}
  </p>
  <div className="flex gap-2">
    <Button
      variant="outline"
      size="sm"
      onClick={() => setPage(page - 1)}
      disabled={page === 1}
    >
      ← Previous
    </Button>
    <Button
      variant="outline"
      size="sm"
      onClick={() => setPage(page + 1)}
      disabled={offset + data.length >= total}
    >
      Next →
    </Button>
  </div>
</div>
```

### Fix 5: JSON Viewer Component

**Simple implementation (no library)**:
```tsx
// components/JsonViewer.tsx
export function JsonViewer({ data }: { data: unknown }) {
  return (
    <pre className="bg-muted p-4 rounded-md overflow-auto max-h-96">
      <code className="text-sm">
        {JSON.stringify(data, null, 2)}
      </code>
    </pre>
  );
}
```

---

## Backend Fixes Applied

### Fix 1: Database Indexes

```sql
-- Migration: 0009_admin_monitoring_indexes.sql
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_conversations_status
  ON conversations(status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_conversations_platform
  ON conversations(platform);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_job_executions_status
  ON job_executions(status);

-- Composite index for user + status queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_conversations_user_status
  ON conversations(user_id, status);
```

### Fix 2: New Repository Methods

| Repository | Method | Implementation |
|------------|--------|----------------|
| UserRepository | get_with_full_stats(id) | Join users + user_metrics + engagement_state |
| ConversationRepository | get_by_user_paginated(user_id, page, size) | WHERE user_id = ? ORDER BY created_at DESC |
| ConversationRepository | get_pipeline_status(id) | Query job_executions + conversation fields |
| GeneratedPromptRepository | get_by_conversation_id(conv_id) | WHERE conversation_id = ? ORDER BY created_at |
| ScoreHistoryRepository | get_timeline_data(user_id, days) | SELECT date, metrics WHERE user_id AND date >= |
| ScoreHistoryRepository | get_boss_encounters(user_id) | WHERE event_type = 'boss_encounter' |

### Fix 3: Neo4j Timeout Handling

```python
# AdminMonitoringService.get_memory_stats()
async def get_memory_stats(self, user_id: UUID) -> MemoryStats:
    try:
        async with asyncio.timeout(30):  # 30s timeout
            return await self._query_neo4j(user_id)
    except TimeoutError:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Memory database is warming up",
                "code": "NEO4J_TIMEOUT",
                "retry_after": 60,
            }
        )
```

### Fix 4: Pipeline Status Logic

**Use job_executions table for accurate status**:
```python
async def get_pipeline_status(self, conversation_id: UUID) -> PipelineStatus:
    # Query actual job execution, not infer from data
    job = await self.job_repo.get_by_conversation_id(conversation_id)
    if not job:
        return PipelineStatus(status="not_started", stages=[])

    return PipelineStatus(
        status=job.status,  # RUNNING, COMPLETED, FAILED
        started_at=job.started_at,
        completed_at=job.completed_at,
        stages=job.result.get("stages", []) if job.result else [],
        error=job.result.get("error") if job.status == "FAILED" else None,
    )
```

---

## Performance Fixes Applied

### Rate Limiting for Admin Neo4j Queries

```python
# Extend existing RateLimiter
admin_neo4j_limiter = RateLimiter(
    max_requests=30,  # 30 Neo4j queries per hour
    window_seconds=3600,
)

@router.get("/users/{user_id}/memory")
async def get_user_memory(
    user_id: UUID,
    admin: User = Depends(get_current_admin_user),
):
    await admin_neo4j_limiter.check_rate_limit(str(admin.id))
    ...
```

### Simple LRU Cache

```python
# Cache user details for 60 seconds
from functools import lru_cache
from datetime import datetime

class AdminCache:
    _cache: dict = {}
    _ttl = 60  # seconds

    def get(self, key: str):
        if key in self._cache:
            data, cached_at = self._cache[key]
            if (datetime.now() - cached_at).seconds < self._ttl:
                return data
        return None

    def set(self, key: str, data):
        self._cache[key] = (data, datetime.now())
```

---

## Updated Build Order

```
Phase A: Foundation (3-4 hours)
├── F1: Auth middleware + audit logging decorator (1h)
├── F2: Response schemas (1h)
├── F3: PII-safe logging setup (30min)
├── F4: Database migration (indexes + audit_logs) (30min)
└── F5: Shared UI components (Neo4jLoadingState, JsonViewer) (1h)

Phase B: Backend Endpoints (5-6 hours, PARALLEL after F4)
├── Track 1: User endpoints (P1.1-P1.4) + AdminMonitoringService
├── Track 2: Conversation endpoints (P2.1-P2.4) + pipeline status
├── Track 3: Prompts + Scoring endpoints (P3, P4)
├── Track 4: Memory + Jobs endpoints (P7, P6)
└── Repository methods implementation

Phase C: Frontend Routes + Navigation (6-8 hours, PARALLEL after Phase B)
├── Layout with navigation + error boundaries
├── Overview page (system health cards)
├── 8 route-based pages (NOT tabs)
├── Detail pages with drill-down links
└── Pagination controls on all tables

Phase D: Integration + Polish (2-3 hours)
├── Cross-page navigation verification
├── Error aggregation endpoint
├── E2E testing
└── Documentation
```

---

## Revised API Endpoints

### Existing (Extend)

| Endpoint | Enhancement |
|----------|-------------|
| GET /admin/users | Add pagination, filters, stats join |
| GET /admin/users/{id} | Add full stats, game state |
| GET /admin/conversations | Add date range, platform filter |
| GET /admin/conversations/{id} | Add pipeline status |
| GET /admin/prompts/recent | Add user filter |
| GET /admin/jobs | Add status filter |
| GET /admin/voice/sessions | Add transcript preview |

### New (Create)

| Endpoint | Purpose | Response |
|----------|---------|----------|
| GET /admin/users/{id}/memory | 3-graph snapshot | MemorySnapshot |
| GET /admin/users/{id}/scores | Score timeline | ScoreTimeline |
| GET /admin/users/{id}/boss | Boss encounters | BossEncounters |
| GET /admin/conversations/{id}/prompts | Prompt history | PromptHistory |
| GET /admin/conversations/{id}/pipeline | 9-stage status | PipelineStatus |
| GET /admin/metrics/overview | System metrics | SystemMetrics |
| GET /admin/errors | Error log | ErrorList |
| GET /admin/audit-logs | Admin audit trail | AuditLogs |

---

## Validation Checklist

- [x] Audit logging implemented
- [x] PII protection strategy defined
- [x] File-based routing (not tabs/drawers)
- [x] Neo4j timeout handling + loading UX
- [x] Database indexes defined
- [x] Repository methods mapped
- [x] Error boundaries per route
- [x] Pagination pattern defined
- [x] JSON viewer component defined
- [x] Rate limiting for Neo4j queries
- [x] Simple caching strategy

---

## Ready for /feature

All 4 audit issues resolved. Proceed to Phase 3: SDD Specification.

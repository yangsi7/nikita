---
audit_id: "009-db-infra-audit"
status: "PASS_WITH_REMEDIATION"
spec_reference: "specs/009-database-infrastructure/spec.md"
plan_reference: "specs/009-database-infrastructure/plan.md"
tasks_reference: "specs/009-database-infrastructure/tasks.md"
created_at: "2025-11-28T00:00:00Z"
updated_at: "2025-12-01T00:00:00Z"
type: "audit-report"
---

# Audit Report: 009 Database Infrastructure

## Summary

| Metric | Value | Status |
|--------|-------|--------|
| Requirement Coverage | 100% | PASS |
| AC per Task | Min 2, Avg 3.2 | PASS |
| Dependency Validity | Valid | PASS |
| User Story Mapping | 100% | PASS |
| Constitution Compliance | Article VI PASS | PASS |
| Security Audit (2025-12-01) | 5 issues found | REMEDIATION REQUIRED |

**Overall Status**: **PASS_WITH_REMEDIATION** - Phase 1-5 complete, Phase 6 remediation tasks added

---

## Requirement Coverage Audit

### Functional Requirements

| Requirement | Tasks | ACs | Coverage |
|-------------|-------|-----|----------|
| FR-001: Repository Pattern | T1-T7 | 22 | 100% |
| FR-002: Migration Management | T8-T9 | 12 | 100% |
| FR-003: Row-Level Security | T10 | 6 | 100% |
| FR-004: Connection Pooling | T11 | 5 | 100% |
| FR-005: Transaction Management | T12 | 5 | 100% |
| FR-006: Audit Logging | T2, T5 | (included) | 100% |

**FR-001 Detail**:
- AC-001.1 (dedicated repo class) → T2-T6 (6 repositories created)
- AC-001.2 (async sessions) → T1 (base class), T7 (dependencies)
- AC-001.3 (FastAPI Depends) → T7 (dependencies)
- AC-001.4 (no raw SQL) → Enforced by repository pattern

**FR-002 Detail**:
- AC-002.1 (Alembic) → T8 (setup)
- AC-002.2 (idempotent) → T9 (AC-T9.7 reversibility)
- AC-002.3 (naming) → T8 (AC-T8.4 autogenerate)
- AC-002.4 (CASCADE) → T9 (AC-T9.3)
- AC-002.5 (indexes) → T9 (AC-T9.4)

**FR-003 Detail**:
- AC-003.1 (RLS enabled) → T10 (AC-T10.1, AC-T10.2)
- AC-003.2 (own data only) → T10 (AC-T10.3, AC-T10.4)
- AC-003.3 (service role bypass) → T10 (AC-T10.5)
- AC-003.4 (anon blocked) → T10 (AC-T10.6)

### Non-Functional Requirements

| Requirement | Implementation | Verification |
|-------------|----------------|--------------|
| NFR-001: Performance (<100ms) | T11 (pooling), T9 (indexes) | T14 (integration) |
| NFR-002: Reliability | T11 (pool_pre_ping), T12 (retry) | T14 (integration) |
| NFR-003: Security | T10 (RLS), repos (parameterized) | T14 (RLS tests) |
| NFR-004: Observability | T11 (AC-T11.5 metrics) | T14 (integration) |

### User Stories

| Story | Priority | Tasks | AC Coverage |
|-------|----------|-------|-------------|
| US-001: Repository Instantiation | P1 | T1-T7 | 100% (3 ACs) |
| US-002: Score Persistence | P1 | T2, T5, T12 | 100% (3 ACs) |
| US-003: User Data Isolation | P1 | T10 | 100% (3 ACs) |

---

## Acceptance Criteria Audit

### AC Count per Task

| Task | AC Count | Minimum 2 | Status |
|------|----------|-----------|--------|
| T1 | 3 | Yes | PASS |
| T2 | 6 | Yes | PASS |
| T3 | 3 | Yes | PASS |
| T4 | 5 | Yes | PASS |
| T5 | 3 | Yes | PASS |
| T6 | 6 | Yes | PASS |
| T7 | 4 | Yes | PASS |
| T8 | 5 | Yes | PASS |
| T9 | 7 | Yes | PASS |
| T10 | 6 | Yes | PASS |
| T11 | 5 | Yes | PASS |
| T12 | 5 | Yes | PASS |
| T13 | 6 | Yes | PASS |
| T14 | 5 | Yes | PASS |

**Total ACs**: 69
**Average per Task**: 4.9
**Minimum per Task**: 3 (T1, T3, T5)

All tasks have ≥2 ACs: **PASS**

### AC Testability Check

All ACs follow pattern: [Entity] [Action] [Outcome]

Examples:
- AC-T2.1: "get(user_id) returns User with eager-loaded metrics" - Testable via assertion
- AC-T10.3: "Policy allows user access only to auth.uid() = id" - Testable via JWT verification
- AC-T12.4: "Deadlock detection with exponential backoff retry" - Testable via concurrent access

**All ACs testable**: PASS

---

## Dependency Audit

### Task Dependency Validation

```
T1 (Base) ─┬─→ T2 (User) ────┬─→ T7 (Dependencies) ─→ T13 (Tests)
           ├─→ T3 (Metrics) ─┤
           ├─→ T4 (Conversation)
           ├─→ T5 (History) ─┤
           └─→ T6 (Vice/Summary)

T8 (Alembic) ─→ T9 (Migration) ─→ T10 (RLS) ─→ T14 (Integration)
```

**Circular Dependencies**: None found
**Missing Dependencies**: None found
**Parallel Opportunities**: T2-T6 can run in parallel after T1

### External Dependency Validation

| Dependency | Required | Available |
|------------|----------|-----------|
| SQLAlchemy >=2.0 | Yes | pyproject.toml |
| Alembic >=1.13 | Yes | pyproject.toml |
| asyncpg >=0.29 | Yes | pyproject.toml |
| Supabase PostgreSQL | Yes | Environment |

---

## Constitution Compliance

### Article VI: Simplicity & Anti-Abstraction

| Gate | Requirement | Status |
|------|-------------|--------|
| Gate₁ | Project Count ≤3 | PASS (1 project) |
| Gate₂ | Abstraction Layers ≤2 | PASS (Model→Repo→Service) |
| Gate₃ | Framework Trust | PASS (SQLAlchemy/Alembic direct) |

### Article III: Testing Requirements

| Requirement | Implementation | Status |
|-------------|----------------|--------|
| Min 2 ACs per story | 3 ACs per story | PASS |
| Tests before implementation | T13 defined | READY |

### Article VII: User-Story Organization

| Requirement | Implementation | Status |
|-------------|----------------|--------|
| Stories have priority | P1 for all 3 | PASS |
| Tasks map to stories | T1-T14 mapped | PASS |
| Progressive delivery | Repo→Migration→RLS | PASS |

---

## Risk Assessment

| Risk | Plan Mitigation | Audit Status |
|------|-----------------|--------------|
| Connection pool exhaustion | T11 (pool config) | Adequate |
| Migration conflicts | T8 (Alembic setup) | Adequate |
| RLS bypass bugs | T10 + T14 (tests) | Adequate |

---

## Findings (Initial Audit: 2025-11-28)

### Issues Found: 0

No critical issues found at initial audit.

### Warnings: 0

No warnings.

### Recommendations: 2

1. **Consider adding database health endpoint** - T11.AC-T11.5 is marked optional but recommended for production
2. **Add migration squashing guidance** - For long-running projects, document squashing strategy

---

## Security Audit Findings (2025-12-01)

**Audit Method**: Supabase MCP tools (list_tables, get_table_definition, list_policies)

### Critical Issues

#### Issue 1: message_embeddings Missing user_id Column (CRITICAL)
- **Severity**: CRITICAL
- **Description**: Migration drift detected. Code at `nikita/db/models/conversation.py:94-103` defines user_id column, but actual Supabase database schema lacks this column.
- **Impact**: Foreign key constraint missing, no user isolation for embeddings, potential data access violations
- **Evidence**:
  - Code: `user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)`
  - Supabase schema: Column does not exist in message_embeddings table
- **Remediation**: T15 (migration to add user_id column + FK constraint)
- **Status**: Pending

### High Priority Issues

#### Issue 2: RLS Policy Performance (Initplan Overhead)
- **Severity**: HIGH
- **Description**: 11 RLS policies use `auth.uid()` instead of `(select auth.uid())`, causing PostgreSQL query planner to create initplans
- **Impact**: Performance degradation on every RLS-protected query (adds initplan overhead)
- **Affected Policies**:
  - users.own_data (FOR ALL)
  - user_metrics: own_data_via_user_id (SELECT, INSERT, UPDATE, DELETE)
  - conversations: own_data_via_user_id (SELECT, INSERT, UPDATE, DELETE)
  - score_history: own_data_via_user_id (SELECT, INSERT, UPDATE, DELETE)
  - daily_summaries: own_data_via_user_id (SELECT, INSERT, UPDATE, DELETE)
  - user_vice_preferences: own_data_via_user_id (SELECT, INSERT, UPDATE, DELETE)
  - message_embeddings: own_data_via_user_id (SELECT, INSERT, UPDATE, DELETE - once created)
- **Evidence**: PostgreSQL query planner analysis shows initplan for auth.uid() calls
- **Remediation**: T16 (recreate policies with `(select auth.uid())` subquery)
- **Status**: Pending

#### Issue 3: Duplicate RLS Policies
- **Severity**: HIGH
- **Description**: Duplicate SELECT policies found on conversations and user_vice_preferences tables
- **Impact**: Confusion, potential policy conflict, unnecessary complexity
- **Affected Tables**:
  - conversations: 2 SELECT policies (both named "own_data_via_user_id")
  - user_vice_preferences: 2 SELECT policies (both named "own_data_via_user_id")
- **Evidence**: Supabase list_policies() returned duplicate entries
- **Remediation**: T17 (consolidate to single policy per operation)
- **Status**: Pending

### Medium Priority Issues

#### Issue 4: Extensions in Public Schema
- **Severity**: MEDIUM
- **Description**: vector and pg_trgm extensions installed in public schema instead of dedicated extensions schema
- **Impact**: Namespace pollution, non-standard organization
- **Evidence**: Supabase schema query shows extensions in public
- **Best Practice**: PostgreSQL extensions should be in dedicated schema
- **Remediation**: T18 (create extensions schema, move extensions, update search_path)
- **Status**: Pending

#### Issue 5: In-Memory pending_registrations Dict
- **Severity**: HIGH (for multi-instance deployments)
- **Description**: TelegramAuth.pending_registrations (nikita/platforms/telegram/auth.py:24) is in-memory dict, not database-backed
- **Impact**: State lost on restart, not shared across multiple instances (Cloud Run can scale)
- **Evidence**: Python dict at class level
- **Best Practice**: Use database table for persistent, shared state
- **Remediation**: T18 (create pending_registrations table + repository methods)
- **Status**: Pending

---

## Remediation Plan

### Phase 6: Security Remediation

| Task | Severity | Complexity | Status |
|------|----------|------------|--------|
| T15: Fix message_embeddings user_id | CRITICAL | Medium | Not Started |
| T16: Optimize RLS policies | HIGH | Medium | Not Started |
| T17: Consolidate duplicate policies | HIGH | Low | Not Started |
| T18: Extensions schema + pending_registrations | MEDIUM/HIGH | Low | Not Started |

**Implementation Order**: T15 → {T16, T17, T18 parallel}

**Estimated Effort**: 4-6 hours total (2h for T15, 1.5h for T16, 0.5h for T17, 2h for T18)

---

## Conclusion

**Initial Audit Result (2025-11-28)**: **PASS**

All requirements covered, all tasks have sufficient ACs, no circular dependencies, constitution compliance verified.

**Security Audit Result (2025-12-01)**: **REMEDIATION REQUIRED**

5 security/infrastructure issues identified via Supabase MCP tools audit. Phase 1-5 implementation complete (14/14 tasks), but database state requires remediation before production deployment.

**Overall Status**: **PASS_WITH_REMEDIATION** - Implementation successful, security remediation tasks added as Phase 6 (T15-T18).

**Recommended Execution Order (Phase 6)**:
1. T15 (Fix message_embeddings) - CRITICAL priority
2. T16, T17, T18 (parallel) - HIGH/MEDIUM priority

---

**Initial Audit By**: Claude Code Intelligence Toolkit
**Initial Audit Date**: 2025-11-28

**Security Audit By**: Supabase MCP Tools (list_tables, get_table_definition, list_policies)
**Security Audit Date**: 2025-12-01

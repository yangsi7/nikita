---
plan_id: "009-db-infra-plan"
status: "draft"
owner: "Claude"
created_at: "2025-11-28T00:00:00Z"
updated_at: "2025-11-28T00:00:00Z"
type: "plan"
spec_reference: "specs/009-database-infrastructure/spec.md"
---

# Implementation Plan: Database Infrastructure

## Goal

**Objective:** Implement complete database infrastructure layer including repository pattern, Alembic migrations, RLS policies, connection pooling, and transaction management.

**Success Definition:** All feature specs (002-008) can use database layer via repository pattern with atomic transactions, proper connection pooling, and row-level security.

**Based On:** [specs/009-database-infrastructure/spec.md](spec.md)

---

## Summary

**Overview**: Build production-grade database infrastructure layer following repository pattern. Models already exist; need repositories, Alembic migrations, RLS policies, and connection pooling configuration.

**Tech Stack**:
- **Database**: Supabase PostgreSQL 15+
- **ORM**: SQLAlchemy 2.0 async
- **Migrations**: Alembic
- **Connection**: asyncpg with pooling
- **Security**: Supabase RLS policies

**Deliverables**:
1. 6 repository classes (User, Metrics, Conversation, ScoreHistory, Vice, Summary)
2. Alembic migration environment + initial migration
3. RLS policies for all user data tables
4. Connection pooling configuration (5-20 connections)
5. Transaction management utilities
6. FastAPI dependency injection

---

## Technical Context

### Existing Architecture (Intelligence Evidence)

**Intelligence Queries Executed**:
```bash
# Database files found
fd -t f -e py . nikita/db
# Output: database.py, models/{base,user,conversation,game}.py, repositories/__init__.py

# Repository pattern check
rg -l "class.*Repository" nikita/
# Output: nikita/db/CLAUDE.md (docs only, no implementation)

# AsyncSession usage
rg -l "AsyncSession" nikita/
# Output: nikita/db/database.py (basic setup)
```

**Patterns Discovered** (CoD^Σ Evidence):
- **Pattern 1**: Async session dependency @ `nikita/db/database.py:32-41`
  - Usage: `get_async_session()` yields session with auto-commit/rollback
  - Applicability: Repositories will receive sessions via this dependency
- **Pattern 2**: Model structure @ `nikita/db/models/user.py:19-110`
  - Usage: SQLAlchemy 2.0 declarative with mapped_column
  - Applicability: Repositories query these models
- **Pattern 3**: Relationship loading @ `nikita/db/models/user.py:74-100`
  - Usage: Cascade delete, back_populates for bidirectional
  - Applicability: Repositories must handle eager/lazy loading

**Current State**:
- Models: COMPLETE (User, UserMetrics, UserVicePreference, Conversation, ScoreHistory, DailySummary)
- Repositories: NOT IMPLEMENTED (empty __init__.py)
- Migrations: NOT IMPLEMENTED (empty migrations/)
- Connection pooling: PARTIAL (missing pool config)
- RLS: NOT IMPLEMENTED

**CoD^Σ Evidence Chain**:
```
spec_FR001 ∘ intel[nikita/db/database.py:32] → repository_pattern
spec_FR002 ∘ intel[nikita/db/migrations/] → alembic_setup
spec_FR003 ∘ intel[no_RLS_found] → rls_implementation
```

---

## Constitution Check (Article VI)

### Pre-Design Gates

```
Gate₁: Project Count (≤3)
  Status: PASS ✓
  Count: 1 project (nikita)
  Decision: PROCEED

Gate₂: Abstraction Layers (≤2 per concept)
  Status: PASS ✓
  Details: Model → Repository → Service (2 layers for data access)
  Decision: PROCEED

Gate₃: Framework Trust (use directly)
  Status: PASS ✓
  Details: Using SQLAlchemy/Alembic directly, no wrappers
  Decision: PROCEED
```

**Overall Pre-Design Gate**: PASS ✓

---

## Architecture (CoD^Σ)

### Component Breakdown

**System Flow**:
```
FastAPI Route → Depends(get_*_repo) → Repository → AsyncSession → Database
      ↓                ↓                  ↓            ↓            ↓
  Endpoint         Injection          Business      Transaction   PostgreSQL
```

**Dependencies** (CoD^Σ Notation):
```
Repository ⇐ AsyncSession ⇐ async_sessionmaker ⇐ create_async_engine
UserRepo ⊥ ConversationRepo (independent)
ScoreHistoryRepo ⇐ UserRepo (score updates logged atomically)
```

**Data Flow**:
```
Request ≫ Validation ≫ Repository → Transaction → Commit/Rollback
   ↓          ↓            ↓            ↓              ↓
FastAPI   Pydantic     Domain       SQLAlchemy     Database
```

**Modules**:
1. **nikita/db/repositories/**: Repository classes
   - Purpose: Encapsulate all database queries
   - Exports: 6 repository classes + dependencies
   - Imports: models, AsyncSession

2. **nikita/db/migrations/**: Alembic environment
   - Purpose: Schema version control
   - Exports: Migration scripts
   - Imports: models (for autogenerate)

---

## User Story Implementation Plan

### US-001: Repository Instantiation (Priority: P1)

**Goal**: Repositories injected via FastAPI dependencies

**Acceptance Criteria** (from spec.md):
- AC-US001.1: `get_user_repo()` dependency returns UserRepository
- AC-US001.2: Repositories receive AsyncSession from connection pool
- AC-US001.3: Test fixtures can inject mock repositories

**Implementation Approach**:
1. Create base repository class with session injection
2. Create 6 repository implementations
3. Create FastAPI Depends() for each repository
4. Write pytest fixtures for mock injection

**Evidence**: Pattern at `nikita/db/database.py:32-41`

---

### US-002: Score Persistence (Priority: P1)

**Goal**: Score updates persisted atomically with history

**Acceptance Criteria** (from spec.md):
- AC-US002.1: `update_score()` writes to users AND score_history
- AC-US002.2: Failed history insert rolls back score change
- AC-US002.3: Score history includes event_type and event_details

**Implementation Approach**:
1. UserRepository.update_score() in single transaction
2. Transaction rollback on any failure
3. event_type enum validation

**Evidence**: ScoreHistory model at `nikita/db/models/game.py:18-55`

---

### US-003: User Data Isolation (Priority: P1)

**Goal**: RLS enforces user data isolation

**Acceptance Criteria** (from spec.md):
- AC-US003.1: Portal queries return only authenticated user's data
- AC-US003.2: Direct table access blocked without valid JWT
- AC-US003.3: Service role operations work for backend tasks

**Implementation Approach**:
1. Create RLS policies via migration
2. Enable RLS on all user data tables
3. Test with anon vs service role

**Evidence**: Supabase auth integration required

---

## Tasks

### Phase 1: Repository Pattern (FR-001)

#### T1: Create Base Repository Class
- **ID:** T1
- **User Story**: US-001 - Repository Instantiation
- **Owner:** executor-agent
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): None (foundation)
- **Estimated Complexity:** Low

**Acceptance Criteria**:
- [ ] AC-T1.1: BaseRepository class accepts AsyncSession in __init__
- [ ] AC-T1.2: BaseRepository exposes session property for subclasses
- [ ] AC-T1.3: BaseRepository has generic CRUD methods (get, create, update, delete)

**Implementation Notes:**
- **File**: `nikita/db/repositories/base.py`
- **Pattern Evidence**: Based on `nikita/db/database.py:32` session pattern
- **Testing**: Unit tests with mock session

---

#### T2: Create UserRepository
- **ID:** T2
- **User Story**: US-001, US-002
- **Owner:** executor-agent
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T1 → T2
- **Estimated Complexity:** Medium

**Acceptance Criteria**:
- [ ] AC-T2.1: get(user_id) returns User with eager-loaded metrics
- [ ] AC-T2.2: get_by_telegram_id(telegram_id) returns User or None
- [ ] AC-T2.3: create(user_data) creates User + UserMetrics atomically
- [ ] AC-T2.4: update_score(user_id, delta, event_type, event_details) updates users AND score_history in transaction
- [ ] AC-T2.5: apply_decay(user_id, decay_amount) applies decay and logs to score_history
- [ ] AC-T2.6: advance_chapter(user_id) increments chapter and logs event

**Implementation Notes:**
- **File**: `nikita/db/repositories/user_repository.py`
- **Pattern Evidence**: Models at `nikita/db/models/user.py:19-110`
- **Testing**: Integration tests with test database

---

#### T3: Create UserMetricsRepository
- **ID:** T3
- **User Story**: US-001, US-002
- **Owner:** executor-agent
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T1 → T3 (T2 ⊥ T3)
- **Estimated Complexity:** Low

**Acceptance Criteria**:
- [ ] AC-T3.1: get(user_id) returns UserMetrics for user
- [ ] AC-T3.2: update_metrics(user_id, intimacy_delta, passion_delta, ...) updates metrics atomically
- [ ] AC-T3.3: calculate_composite(user_id) returns calculated composite score

**Implementation Notes:**
- **File**: `nikita/db/repositories/metrics_repository.py`
- **Pattern Evidence**: Model at `nikita/db/models/user.py:112-167`
- **Testing**: Unit tests for composite calculation

---

#### T4: Create ConversationRepository
- **ID:** T4
- **User Story**: US-001
- **Owner:** executor-agent
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T1 → T4 (T4 ⊥ T2, T3)
- **Estimated Complexity:** Medium

**Acceptance Criteria**:
- [ ] AC-T4.1: create(user_id, platform, started_at) creates new conversation
- [ ] AC-T4.2: append_message(conv_id, role, content, analysis) adds message to JSONB
- [ ] AC-T4.3: get_recent(user_id, limit=10) returns last N conversations
- [ ] AC-T4.4: search(user_id, query) performs full-text search on search_vector
- [ ] AC-T4.5: close_conversation(conv_id, score_delta) sets ended_at and score_delta

**Implementation Notes:**
- **File**: `nikita/db/repositories/conversation_repository.py`
- **Pattern Evidence**: Model at `nikita/db/models/conversation.py:27-85`
- **Testing**: Test JSONB append and full-text search

---

#### T5: Create ScoreHistoryRepository
- **ID:** T5
- **User Story**: US-002
- **Owner:** executor-agent
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T1 → T5 (T5 ⊥ T2-T4)
- **Estimated Complexity:** Low

**Acceptance Criteria**:
- [ ] AC-T5.1: log_event(user_id, score, chapter, event_type, event_details) creates history record
- [ ] AC-T5.2: get_history(user_id, limit=50) returns score timeline descending
- [ ] AC-T5.3: get_daily_stats(user_id, date) returns aggregated stats for date

**Implementation Notes:**
- **File**: `nikita/db/repositories/score_history_repository.py`
- **Pattern Evidence**: Model at `nikita/db/models/game.py:18-55`
- **Testing**: Unit tests with mock data

---

#### T6: Create VicePreferenceRepository and DailySummaryRepository
- **ID:** T6
- **User Story**: US-001
- **Owner:** executor-agent
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T1 → T6 (T6 ⊥ T2-T5)
- **Estimated Complexity:** Low

**Acceptance Criteria**:
- [ ] AC-T6.1: VicePreferenceRepository.get_active(user_id) returns active preferences
- [ ] AC-T6.2: VicePreferenceRepository.update_intensity(pref_id, delta) updates intensity_level
- [ ] AC-T6.3: VicePreferenceRepository.discover(user_id, category) creates new preference
- [ ] AC-T6.4: DailySummaryRepository.create(user_id, date, data) creates summary
- [ ] AC-T6.5: DailySummaryRepository.get_by_date(user_id, date) returns summary
- [ ] AC-T6.6: DailySummaryRepository.get_range(user_id, start, end) returns summaries in range

**Implementation Notes:**
- **File**: `nikita/db/repositories/vice_repository.py`, `nikita/db/repositories/summary_repository.py`
- **Pattern Evidence**: Models at `nikita/db/models/user.py:169-207`, `nikita/db/models/game.py:68-115`
- **Testing**: Unit tests with date range queries

---

#### T7: Create Repository Dependencies
- **ID:** T7
- **User Story**: US-001
- **Owner:** executor-agent
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T2-T6 → T7
- **Estimated Complexity:** Low

**Acceptance Criteria**:
- [ ] AC-T7.1: get_user_repo() FastAPI Depends returns UserRepository
- [ ] AC-T7.2: get_conversation_repo() returns ConversationRepository
- [ ] AC-T7.3: All 6 repos have corresponding get_*_repo() dependencies
- [ ] AC-T7.4: Dependencies compose with AsyncSession dependency

**Implementation Notes:**
- **File**: `nikita/db/repositories/__init__.py` (exports), `nikita/db/dependencies.py` (new)
- **Pattern Evidence**: Based on `nikita/db/database.py:32-41`
- **Testing**: Integration test with FastAPI test client

---

### Phase 2: Migrations (FR-002)

#### T8: Setup Alembic Environment
- **ID:** T8
- **User Story**: US-001 (infrastructure)
- **Owner:** executor-agent
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T1 ⊥ T8 (independent foundation)
- **Estimated Complexity:** Medium

**Acceptance Criteria**:
- [ ] AC-T8.1: alembic.ini at project root with Supabase connection
- [ ] AC-T8.2: migrations/env.py configured for async SQLAlchemy
- [ ] AC-T8.3: migrations/versions/ directory exists
- [ ] AC-T8.4: `alembic revision --autogenerate` works
- [ ] AC-T8.5: `alembic upgrade head` applies migrations

**Implementation Notes:**
- **File**: `alembic.ini`, `nikita/db/migrations/env.py`
- **Pattern Evidence**: Existing empty `nikita/db/migrations/`
- **Testing**: Run migration against test database

---

#### T9: Create Initial Migration
- **ID:** T9
- **User Story**: US-001 (infrastructure)
- **Owner:** executor-agent
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T8 → T9
- **Estimated Complexity:** Medium

**Acceptance Criteria**:
- [ ] AC-T9.1: Migration creates all 6 tables (users, user_metrics, user_vice_preferences, conversations, score_history, daily_summaries)
- [ ] AC-T9.2: Migration creates message_embeddings table with pgvector
- [ ] AC-T9.3: All foreign keys with ON DELETE CASCADE
- [ ] AC-T9.4: Performance indexes created (telegram_id, game_status, user_started, etc.)
- [ ] AC-T9.5: Check constraints for chapter (1-5), boss_attempts (0-3), intensity_level (1-5)
- [ ] AC-T9.6: Full-text search index on conversations.search_vector
- [ ] AC-T9.7: Migration is reversible (downgrade works)

**Implementation Notes:**
- **File**: `nikita/db/migrations/versions/{timestamp}_initial_schema.py`
- **Pattern Evidence**: Models at `nikita/db/models/*.py`
- **Testing**: Up and down migration test

---

### Phase 3: Row-Level Security (FR-003)

#### T10: Create RLS Policies Migration
- **ID:** T10
- **User Story**: US-003 - User Data Isolation
- **Owner:** executor-agent
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T9 → T10
- **Estimated Complexity:** Medium

**Acceptance Criteria**:
- [ ] AC-T10.1: RLS enabled on users, user_metrics, user_vice_preferences
- [ ] AC-T10.2: RLS enabled on conversations, score_history, daily_summaries
- [ ] AC-T10.3: Policy "own_data" allows user access only to auth.uid() = id (users)
- [ ] AC-T10.4: Policy "own_data_via_user_id" allows access where user_id matches (related tables)
- [ ] AC-T10.5: Service role bypasses RLS (no policy restrictions)
- [ ] AC-T10.6: Anon role has no access (SELECT/INSERT/UPDATE/DELETE blocked)

**Implementation Notes:**
- **File**: `nikita/db/migrations/versions/{timestamp}_rls_policies.py`
- **Pattern Evidence**: Spec `spec.md:64-72` RLS template
- **Testing**: Test with anon key vs service key

---

### Phase 4: Connection & Transaction (FR-004, FR-005)

#### T11: Configure Connection Pooling
- **ID:** T11
- **User Story**: US-001 (infrastructure)
- **Owner:** executor-agent
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T8 ⊥ T11 (independent)
- **Estimated Complexity:** Low

**Acceptance Criteria**:
- [ ] AC-T11.1: pool_size=5, max_overflow=15 (total max 20)
- [ ] AC-T11.2: pool_timeout=30 seconds
- [ ] AC-T11.3: pool_recycle=1800 seconds
- [ ] AC-T11.4: pool_pre_ping=True (validate connections)
- [ ] AC-T11.5: Connection pool metrics exposed (optional health endpoint)

**Implementation Notes:**
- **File**: `nikita/db/database.py` (update get_async_engine)
- **Pattern Evidence**: Existing basic config at `nikita/db/database.py:12-19`
- **Testing**: Load test with concurrent connections

---

#### T12: Create Transaction Utilities
- **ID:** T12
- **User Story**: US-002 - Score Persistence
- **Owner:** executor-agent
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T1 → T12 (T11 ⊥ T12)
- **Estimated Complexity:** Medium

**Acceptance Criteria**:
- [ ] AC-T12.1: `@atomic` decorator wraps function in transaction
- [ ] AC-T12.2: Nested transactions use SAVEPOINTs
- [ ] AC-T12.3: Failed transactions rollback completely
- [ ] AC-T12.4: Deadlock detection with exponential backoff retry (3 attempts)
- [ ] AC-T12.5: Transaction isolation level configurable (default: READ COMMITTED)

**Implementation Notes:**
- **File**: `nikita/db/transactions.py` (new)
- **Pattern Evidence**: Based on `nikita/db/database.py:38-41` rollback pattern
- **Testing**: Test concurrent updates with deadlock simulation

---

### Phase 5: Testing & Integration

#### T13: Repository Unit Tests
- **ID:** T13
- **User Story**: US-001, US-002
- **Owner:** executor-agent
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T2-T6 → T13
- **Estimated Complexity:** Medium

**Acceptance Criteria**:
- [ ] AC-T13.1: Each repository has test file in tests/db/repositories/
- [ ] AC-T13.2: Test fixtures provide mock AsyncSession
- [ ] AC-T13.3: UserRepository tests cover all 6 methods
- [ ] AC-T13.4: ConversationRepository tests cover JSONB operations
- [ ] AC-T13.5: Test coverage > 80% for repository layer
- [ ] AC-T13.6: Tests run in isolation (no database dependency for unit tests)

**Implementation Notes:**
- **Files**: `tests/db/repositories/test_*.py`
- **Pattern Evidence**: Based on existing test patterns
- **Testing**: pytest with mock session

---

#### T14: Integration Tests
- **ID:** T14
- **User Story**: US-001, US-002, US-003
- **Owner:** executor-agent
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T13 → T14, T9 → T14, T10 → T14
- **Estimated Complexity:** High

**Acceptance Criteria**:
- [ ] AC-T14.1: Integration tests use test Supabase project
- [ ] AC-T14.2: RLS tests verify user isolation with anon JWT
- [ ] AC-T14.3: Transaction tests verify atomic operations
- [ ] AC-T14.4: Migration tests verify up/down reversibility
- [ ] AC-T14.5: Full-text search test verifies query results

**Implementation Notes:**
- **Files**: `tests/db/integration/test_*.py`
- **Pattern Evidence**: Spec `spec.md:299-307` risks mention integration tests
- **Testing**: pytest with test database fixture

---

### Phase 6: Security Remediation (Audit Findings - 2025-12-01)

#### T15: Fix message_embeddings Schema Drift
- **ID:** T15
- **User Story**: US-004 - Security Remediation
- **Owner:** executor-agent
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T9 → T15
- **Estimated Complexity:** Medium

**Acceptance Criteria**:
- [ ] AC-T15.1: Migration adds user_id UUID NOT NULL column to message_embeddings
- [ ] AC-T15.2: Foreign key constraint message_embeddings.user_id → users.id with ON DELETE CASCADE
- [ ] AC-T15.3: Index created on message_embeddings(user_id) for performance
- [ ] AC-T15.4: Migration updates existing rows (if any) with user_id from conversations table
- [ ] AC-T15.5: Migration is reversible (downgrade drops column)

**Implementation Notes:**
- **File**: `nikita/db/migrations/versions/{timestamp}_fix_message_embeddings_user_id.py`
- **Pattern Evidence**: Migration drift detected via Supabase MCP audit
- **Testing**: Integration test verifying user_id constraint

**Context**: Code at models/conversation.py:94-103 expects user_id column, but actual DB schema missing it (migration not applied).

---

#### T16: Fix RLS Policy Performance (Initplan Issue)
- **ID:** T16
- **User Story**: US-004 - Security Remediation
- **Owner:** executor-agent
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T10 → T16
- **Estimated Complexity:** Medium

**Acceptance Criteria**:
- [ ] AC-T16.1: Recreate 11 RLS policies using `(select auth.uid())` instead of `auth.uid()` for better performance
- [ ] AC-T16.2: Affected policies: users (own_data), user_metrics, conversations, score_history, daily_summaries, user_vice_preferences, message_embeddings SELECT/INSERT/UPDATE/DELETE
- [ ] AC-T16.3: Verify query plans show no initplan after fix (`EXPLAIN ANALYZE` tests)
- [ ] AC-T16.4: Existing policy behavior unchanged (only performance improved)

**Implementation Notes:**
- **File**: `nikita/db/migrations/versions/{timestamp}_optimize_rls_policies.py`
- **Pattern Evidence**: PostgreSQL initplan overhead detected in audit
- **Testing**: Query plan analysis tests

**Context**: `auth.uid()` creates initplan in PostgreSQL, causing performance overhead. Using `(select auth.uid())` allows optimizer to cache result.

---

#### T17: Consolidate Duplicate RLS Policies
- **ID:** T17
- **User Story**: US-004 - Security Remediation
- **Owner:** executor-agent
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T10 → T17 (T16 ⊥ T17)
- **Estimated Complexity:** Low

**Acceptance Criteria**:
- [ ] AC-T17.1: Remove duplicate SELECT policy on conversations table (keep single "own_data_via_user_id")
- [ ] AC-T17.2: Remove duplicate SELECT policy on user_vice_preferences table (keep single "own_data_via_user_id")
- [ ] AC-T17.3: Verify no functionality change (integration tests pass)

**Implementation Notes:**
- **File**: `nikita/db/migrations/versions/{timestamp}_consolidate_duplicate_policies.py`
- **Pattern Evidence**: Supabase audit found duplicate SELECT policies
- **Testing**: Existing RLS integration tests should pass

---

#### T18: Improve Extension Organization
- **ID:** T18
- **User Story**: US-004 - Security Remediation
- **Owner:** executor-agent
- **Status:** [ ] Not Started
- **Dependencies** (CoD^Σ): T9 → T18 (T15-T17 ⊥ T18)
- **Estimated Complexity:** Low

**Acceptance Criteria**:
- [ ] AC-T18.1: Create dedicated "extensions" schema for vector and pg_trgm extensions
- [ ] AC-T18.2: Move vector and pg_trgm from public schema to extensions schema
- [ ] AC-T18.3: Update search_path in database.py to include extensions schema
- [ ] AC-T18.4: Create pending_registrations table (id UUID PK, telegram_id BIGINT UNIQUE, phone_number VARCHAR(20), verification_code VARCHAR(6), expires_at TIMESTAMPTZ, created_at TIMESTAMPTZ)
- [ ] AC-T18.5: Add index on pending_registrations(telegram_id) and pending_registrations(expires_at)
- [ ] AC-T18.6: Create TelegramAuthRepository.store_pending_registration() and get_pending_registration() methods

**Implementation Notes:**
- **Files**: `nikita/db/migrations/versions/{timestamp}_reorganize_extensions.py`, `nikita/db/repositories/telegram_auth_repository.py`
- **Pattern Evidence**: Extensions in public schema pollute namespace (Supabase audit finding)
- **Testing**: Extension usage tests, pending_registrations repository tests

**Context**: Moving extensions to dedicated schema is PostgreSQL best practice. In-memory pending_registrations dict (nikita/platforms/telegram/auth.py:24) is not multi-instance safe - needs database persistence.

---

## Dependencies

### Task Dependency Graph (CoD^Σ)

```
T1 (Base) ──┬──→ T2 (User) ──┬──→ T7 (Dependencies) ──→ T13 (Unit Tests) ──→ T14 (Integration)
            │                 │
            ├──→ T3 (Metrics) ┤
            │                 │
            ├──→ T4 (Conversation)
            │                 │
            ├──→ T5 (History) ┤
            │                 │
            └──→ T6 (Vice/Summary)

T8 (Alembic) ──→ T9 (Initial Migration) ──→ T10 (RLS) ──→ T14
                         │                      │
                         ├──────────────────────┼──→ T15 (Fix message_embeddings)
                         └──────────────────────┼──→ T16 (Optimize RLS) ⊥ T17 (Consolidate)
                                                └──→ T18 (Extensions + pending_registrations)

T11 (Pool) ⊥ T1-T10 (independent)
T12 (Transactions) ⇐ T1 (needs BaseRepository)
T15-T18 ⊥ each other (parallel remediation)
```

**Critical Path**: T1 → T2 → T7 → T13 → T14 → {T15-T18}
**Parallelizable**: {T2, T3, T4, T5, T6} ⊥ each other after T1
**Parallelizable**: {T8, T11} ⊥ T1-T7
**Parallelizable**: {T15, T16, T17, T18} ⊥ each other after T10, T14

### External Dependencies
- **Library**: sqlalchemy[asyncio]>=2.0 - Source: `pyproject.toml`
- **Library**: alembic>=1.13 - Source: `pyproject.toml`
- **Library**: asyncpg>=0.29 - Source: `pyproject.toml`
- **Service**: Supabase PostgreSQL - Availability: Required

### File Dependencies (CoD^Σ Evidence)
```
nikita/db/models/*.py → nikita/db/repositories/*.py (repositories import models)
nikita/db/database.py → nikita/db/repositories/*.py (session injection)
nikita/db/models/*.py → nikita/db/migrations/env.py (autogenerate target)
```

---

## Risks (CoD^Σ)

### Risk 1: Connection Pool Exhaustion
- **Likelihood (p):** Medium (0.5)
- **Impact:** High (8)
- **Risk Score:** r = 4.0
- **Mitigation Chain**:
  ```
  high_load → pool_exhausted → timeout_errors → user_impact
  Detection: pool metrics monitoring
  Response: increase pool size, add connection timeout
  Resolution: auto-scaling or queue overflow
  ```
- **Mitigation:**
  - **Reduce p**: Connection timeouts, pool recycling
  - **Reduce impact**: Graceful degradation, retry logic

### Risk 2: Migration Conflicts
- **Likelihood (p):** Low (0.2)
- **Impact:** Medium (5)
- **Risk Score:** r = 1.0
- **Mitigation Chain**:
  ```
  concurrent_migrations → conflict → broken_schema → rollback
  ```
- **Mitigation:**
  - **Prevention**: Single migration at a time, feature branches
  - **Containment**: Migration squashing, clear naming

### Risk 3: RLS Bypass Bugs
- **Likelihood (p):** Low (0.3)
- **Impact:** High (9)
- **Risk Score:** r = 2.7
- **Mitigation Chain**:
  ```
  policy_bug → data_leak → user_sees_other_data → critical
  ```
- **Mitigation:**
  - **Prevention**: Integration tests with different JWT roles
  - **Containment**: Audit logging, policy review

---

## Verification (CoD^Σ)

### Test Strategy (CoD^Σ Composition)
```
Unit → Integration → E2E
  ↓         ↓          ↓
Fast     Medium     Slow

Coverage: ∑(AC_tested) / ∑(AC_total) ≥ 0.95
```

- **Unit Tests**: `tests/db/repositories/*.test.py`
  - Coverage: All repository methods
  - Execution: <10ms per test (mocked)

- **Integration Tests**: `tests/db/integration/*.test.py`
  - Coverage: RLS, transactions, migrations
  - Dependencies: Test Supabase instance

### AC Coverage Map (CoD^Σ Traceability)

| AC | Test File | Status |
|----|-----------|--------|
| AC-T1.1 | tests/db/repositories/test_base.py | Pending |
| AC-T2.1-T2.6 | tests/db/repositories/test_user_repository.py | Pending |
| AC-T3.1-T3.3 | tests/db/repositories/test_metrics_repository.py | Pending |
| AC-T4.1-T4.5 | tests/db/repositories/test_conversation_repository.py | Pending |
| AC-T5.1-T5.3 | tests/db/repositories/test_score_history_repository.py | Pending |
| AC-T6.1-T6.6 | tests/db/repositories/test_vice_repository.py, test_summary_repository.py | Pending |
| AC-T7.1-T7.4 | tests/db/test_dependencies.py | Pending |
| AC-T8.1-T8.5 | tests/db/migrations/test_alembic_setup.py | Pending |
| AC-T9.1-T9.7 | tests/db/migrations/test_initial_migration.py | Pending |
| AC-T10.1-T10.6 | tests/db/integration/test_rls_policies.py | Pending |
| AC-T11.1-T11.5 | tests/db/test_connection_pool.py | Pending |
| AC-T12.1-T12.5 | tests/db/test_transactions.py | Pending |

```
Coverage := ∑(mapped_ACs) / ∑(total_ACs) = 45/45 (100%)
```

### Verification Command
```bash
# Verification pipeline
pytest tests/db/ -v --cov=nikita.db --cov-report=term-missing

# Run migrations test
alembic upgrade head && alembic downgrade base && alembic upgrade head
```

---

## Progress Tracking (CoD^Σ)

**Completion Metrics**:
```
Total Tasks (N):     ∑(tasks) = 18
Completed (X):       |{t ∈ T : status=complete}| = 14
In Progress (Y):     |{t ∈ T : status=in_progress}| = 0
Blocked (Z):         |{t ∈ T : status=blocked}| = 0

Progress Ratio:      X/N = 14/18 (78%)
```

**Status Distribution**:
```
Completed: ████████░░ [14/18]
Progress:  ░░░░░░░░░░ [0/18]
Blocked:   ░░░░░░░░░░ [0/18]
```

**Last Updated:** 2025-12-01
**Next Review:** After T15-T18 (Security Remediation complete)

---

## Handover Points (CoD^Σ Delegation)

### Handover 1: Repository Layer Complete (After T7)
```
[Plan Agent] → [Executor Agent]
  ↓              ↓
Context      Implementation
```

- **From:** Planner
- **To:** Executor
- **Trigger:** T1-T7.status = complete
- **Context Transfer**:
  - **Outputs**: 6 repositories + dependencies
  - **State**: Repository pattern established
  - **Evidence**: plan.md + spec.md

### Handover 2: Infrastructure Complete (After T14)
```
[Executor] → [Feature Teams]
  ↓            ↓
DB Layer    Feature Implementation
```

- **From:** DB Infra Executor
- **To:** Feature spec executors (002-008)
- **Trigger:** All tests passing
- **Context Transfer**:
  - **Outputs**: Full DB layer operational
  - **Dependencies Unblocked**: All feature specs

---

## Notes (CoD^Σ Evidence)

**Deviations from Spec**:
- None currently

**Lessons Learned**:
- TBD (update as plan executes)

**Optimizations**:
- TBD (track token/time savings)

# Spec 036: Humanization Layer Critical Fixes

## Overview

Fix critical bugs blocking the humanization layer from functioning properly. The bot is currently non-functional due to LLM timeout issues, and several humanization tables remain empty due to code bugs.

## Problem Statement

Gap analysis (2026-01-26) revealed:
1. **LLM Timeout (CRITICAL)**: Neo4j cold start (61.33s) exceeds Cloud Run default timeout (60s), causing bot to be non-functional
2. **Narrative Arcs Empty**: Method signature mismatch in `post_processor.py` prevents arc creation
3. **Social Circles Empty**: Exceptions silently swallowed during onboarding
4. **Neo4j Cold Start**: No connection pooling causes repeated slow startup

## Functional Requirements

| ID | Requirement | Priority | Issue |
|----|-------------|----------|-------|
| FR-001 | Cloud Run timeout increased to 300s | P0 | #21 |
| FR-002 | Add explicit LLM timeout wrapper (120s) with graceful fallback | P0 | #21 |
| FR-003 | Fix narrative arc `should_start_new_arc()` method signature mismatch | P0 | #23 |
| FR-004 | Propagate social circle generation errors (don't silently fail) | P1 | #22 |
| FR-005 | Add Neo4j connection pooling for warm starts | P1 | #24 |
| FR-006 | Add timeout monitoring middleware for observability | P2 | #21 |

## Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-001 | Message response time < 30s (after warm-up) | < 30s |
| NFR-002 | Neo4j warm start time < 5s | < 5s |
| NFR-003 | All existing tests pass | 100% |
| NFR-004 | No regression in text agent behavior | 0 regressions |

## User Stories

### US-1: Bot Functionality Restoration (P0)
**As a** player
**I want** the Telegram bot to respond to my messages
**So that** I can play the game

**Acceptance Criteria:**
- AC-1.1: Bot responds within 30s to messages (after warm-up)
- AC-1.2: LLM timeout errors are gracefully handled with user-friendly message
- AC-1.3: Cloud Run doesn't kill requests during Neo4j cold start

### US-2: Narrative Arc Generation (P0)
**As a** player
**I want** narrative arcs to be generated during conversations
**So that** the game has story progression

**Acceptance Criteria:**
- AC-2.1: `should_start_new_arc()` called with correct 4-parameter signature
- AC-2.2: Narrative arcs are created after eligible conversations
- AC-2.3: Post-processor doesn't silently fail on arc generation

### US-3: Social Circle Generation (P1)
**As a** player
**I want** social circles to be generated during onboarding
**So that** Nikita can reference friends and family

**Acceptance Criteria:**
- AC-3.1: Social circle generation errors are logged with full traceback
- AC-3.2: Errors are propagated (not silently swallowed)
- AC-3.3: Successful generation still works as before

### US-4: Neo4j Performance (P1)
**As a** system
**I want** Neo4j connections to be pooled
**So that** warm queries are fast

**Acceptance Criteria:**
- AC-4.1: Singleton driver instance created at startup
- AC-4.2: Second query to Neo4j < 5s (proves warm connection)
- AC-4.3: Connection reused across queries

### US-5: Observability (P2)
**As an** operator
**I want** slow requests to be logged
**So that** I can monitor performance issues

**Acceptance Criteria:**
- AC-5.1: Requests > 45s are logged with duration
- AC-5.2: Middleware doesn't affect request processing
- AC-5.3: Logs include request path and method

## Out of Scope

- Complete rewrite of Neo4j client (only add pooling)
- Background job for social circle retry
- Automatic arc recovery for past conversations

## Dependencies

- GitHub Issues: #21, #22, #23, #24
- Cloud Run CLI access for timeout configuration
- Supabase access for verification queries

## Success Criteria

1. **Bot Responds**: Telegram messages get responses within 30s
2. **Narrative Arcs Generated**: `user_narrative_arcs` table has records after conversation
3. **Social Circle Errors Visible**: Generation failures logged with full traceback
4. **Tests Pass**: Full test suite passes (100%)
5. **Performance**: Neo4j warm queries < 5s

## References

- Gap Analysis: `docs-to-process/20260126-analysis-humanization-layer-gaps.md`
- GitHub Issues: #21 (LLM timeout), #22 (social circles), #23 (narrative arcs), #24 (Neo4j cold start)

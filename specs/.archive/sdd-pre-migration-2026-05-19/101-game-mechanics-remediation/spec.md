# Spec 101: Game Mechanics Remediation

## Overview

Fixes 5 game mechanic bugs/gaps identified in the system intelligence audit: boss PARTIAL cooldown not persisted, days_played dead column, Ch1 decay imbalance, EXPLOSIVE conflict escape, and semantic repetition penalty.

## Scope

| ID | Issue | Type | Severity |
|----|-------|------|----------|
| B1/G2 | Boss PARTIAL `cool_down_until` not persisted on User model | Bug | HIGH |
| G1 | `days_played` column never incremented | Gap | MEDIUM |
| G4 | Ch1 decay rate too harsh (0.8/hr, only 8h grace) | Gap | MEDIUM |
| G11 | EXPLOSIVE conflict has no timeout escape | Gap | HIGH |
| G14/I9 | No semantic repetition penalty in skip logic | Improvement | MEDIUM |

## Functional Requirements

### FR-001: Boss PARTIAL Cooldown Persistence (B1/G2)

**Problem**: `process_partial()` returns `cool_down_until` in response dict but never persists it. `should_trigger_boss()` has no cooldown check.

**Solution**:
1. Add `cool_down_until: datetime | None` column on `users` table
2. `process_partial()` persists `cool_down_until` via `user_repository.set_cool_down()`
3. `should_trigger_boss()` checks `cool_down_until > now()` → block trigger

**Files**: `nikita/db/models/user.py`, `nikita/engine/chapters/boss.py`, Supabase migration

**AC**:
- AC-1.1: `cool_down_until` column exists on `users` table (nullable DateTime)
- AC-1.2: `process_partial()` calls `user_repository.set_cool_down(user_id, cool_down_until)`
- AC-1.3: `should_trigger_boss()` accepts optional `cool_down_until` param, returns False if `cool_down_until > now()`
- AC-1.4: 24h cooldown enforced — boss cannot retrigger within 24h of PARTIAL

### FR-002: days_played Column Resolution (G1)

**Problem**: `days_played` column exists but is never incremented. Either implement or drop.

**Solution**: Increment `days_played` in the decay job (runs every hour). If `last_interaction_at` is from a different calendar day than the last decay run, increment. This is a lightweight addition to the existing decay flow.

**Files**: `nikita/api/routes/tasks.py`, `nikita/db/repositories/user_repository.py`

**AC**:
- AC-2.1: Decay job increments `days_played` for each user whose `last_interaction_at` changed to a new day since last check
- AC-2.2: `days_played` only increments once per calendar day (idempotent)
- AC-2.3: New users start with `days_played = 0`, incremented to 1 on first interaction day

### FR-003: Ch1 Decay Rebalancing (G4)

**Problem**: Ch1 has the shortest grace period (8h) AND highest decay rate (0.8/hr). New players get punished hardest. Should be inverted: longest grace early, shortest late.

**Solution**: Swap grace periods so Ch1 has longest grace (72h) and Ch5 shortest (8h). Keep decay rates as-is (higher rate but more time before it kicks in).

**Files**: `nikita/engine/constants.py`

**AC**:
- AC-3.1: Grace periods inverted: Ch1=72h, Ch2=48h, Ch3=24h, Ch4=16h, Ch5=8h
- AC-3.2: Decay rates unchanged (0.8, 0.6, 0.4, 0.3, 0.2)
- AC-3.3: All existing decay tests updated to reflect new grace periods
- AC-3.4: Game balance: new players get 3 full days before any decay starts

### FR-004: EXPLOSIVE Conflict Timeout Escape (G11)

**Problem**: EXPLOSIVE conflict state has no timeout. Once reached, requires specific emotional conditions to de-escalate. Player could be stuck indefinitely.

**Solution**: Add timeout-based de-escalation. After N hours in EXPLOSIVE, auto-transition to COLD.

**Files**: `nikita/emotional_state/conflict.py`

**AC**:
- AC-4.1: `EXPLOSIVE_TIMEOUT_HOURS = 6` constant added
- AC-4.2: `check_de_escalation()` checks if conflict has been EXPLOSIVE for > 6 hours
- AC-4.3: Auto-transition: EXPLOSIVE → COLD after timeout, with trigger "timeout_de_escalation"
- AC-4.4: Timeout uses `conflict_started_at` from EmotionalStateModel metadata

### FR-005: Semantic Repetition Penalty (G14/I9)

**Problem**: Skip logic is purely random. No penalty for sending repetitive messages. Player could spam identical messages.

**Solution**: Add optional `recent_messages` parameter to `SkipDecision.should_skip()`. If last N messages have high semantic similarity (simple string comparison), increase skip probability.

**Files**: `nikita/agents/text/skip.py`

**AC**:
- AC-5.1: `should_skip()` accepts optional `recent_messages: list[str]` parameter
- AC-5.2: If any pair of recent messages have >80% character overlap (SequenceMatcher), skip probability increases by 2x
- AC-5.3: Repetition penalty stacks with consecutive skip reduction
- AC-5.4: Default behavior unchanged when `recent_messages` not provided

## Non-Functional Requirements

- All changes backward-compatible with existing game state
- No data migration needed for existing users (nullable columns, safe defaults)
- Performance: no additional DB queries per message (cooldown loaded with user)

## Dependencies

- Spec 100 (decay idempotency must be fixed first) — DONE
- Supabase MCP for migration

## Test Strategy

- Unit tests for each FR
- Update existing boss tests for cooldown logic
- Update existing decay tests for new grace periods
- Integration test for EXPLOSIVE timeout

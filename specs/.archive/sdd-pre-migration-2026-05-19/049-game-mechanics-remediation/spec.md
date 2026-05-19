# Spec 049: Game Mechanics Remediation

**Status**: DRAFT | **Priority**: HIGH | **Source**: Deep Audit 2026-02-14

## Problem Statement

Deep audit identified 5 game mechanics gaps causing 3/10 user journey failures:
1. Boss fight timeout: AFK users stuck in boss_fight forever (decay skips them)
2. BreakupManager dead code: ConflictStage detects conflicts but never triggers breakup/game_over
3. Won state: Pipeline runs full processing on won users (wasted resources)
4. Decay notification: No Telegram message when decay triggers game_over
5. Pipeline filtering: All game_status values processed equally

## User Stories

### US-1: Boss Fight Timeout (HIGH)
As a player stuck in boss_fight, I want the system to auto-resolve my state after 24h so I can continue playing.

**Acceptance Criteria:**
- AC-1.1: Task endpoint `/tasks/boss-timeout` resolves boss_fight states older than 24h
- AC-1.2: Resolution sets game_status back to "active" and increments boss_attempts
- AC-1.3: pg_cron calls the endpoint every 6 hours
- AC-1.4: Resolved users receive a Telegram message explaining what happened
- AC-1.5: Unit tests cover timeout logic (>=3 tests)

### US-2: BreakupManager Wiring (HIGH)
As a game designer, I want ConflictStage to check breakup thresholds so the conflict→game_over path works.

**Acceptance Criteria:**
- AC-2.1: ConflictStage calls `BreakupManager.check_threshold()` after conflict detection
- AC-2.2: If breakup threshold met, pipeline sets `ctx.game_over_triggered = True`
- AC-2.3: Post-pipeline handler in message_handler detects game_over from pipeline and persists it
- AC-2.4: Unit tests for ConflictStage with breakup wiring (>=3 tests)
- AC-2.5: Integration test: conflict score below threshold → game_over triggered

### US-3: Pipeline Game Status Filtering (MEDIUM)
As a system, I want to skip pipeline processing for game_over/won users to save resources.

**Acceptance Criteria:**
- AC-3.1: PipelineOrchestrator.process() returns early if game_status in ("game_over", "won")
- AC-3.2: Early return includes reason in result dict
- AC-3.3: Unit test verifies early return for game_over
- AC-3.4: Unit test verifies early return for won

### US-4: Decay Game-Over Notification (MEDIUM)
As a player, I want to receive a Telegram notification when decay triggers game_over.

**Acceptance Criteria:**
- AC-4.1: DecayProcessor._handle_game_over() sends Telegram message to user
- AC-4.2: Message includes explanation of what happened
- AC-4.3: Uses existing bot.send_message() pattern
- AC-4.4: Unit test with mocked bot verifies message sent

### US-5: Won State Content (LOW)
As a player who won the game, I want varied responses (not a single canned message).

**Acceptance Criteria:**
- AC-5.1: Won users get one of 3+ varied congratulation messages
- AC-5.2: Messages rotate (not always the same)
- AC-5.3: Unit test verifies message variety

## Non-Functional Requirements

- NFR-1: Boss timeout check completes in <5s for all users
- NFR-2: Pipeline early return adds <1ms overhead
- NFR-3: No database schema changes required (uses existing columns)

## Out of Scope

- Game restart mechanics (already working per journey #7)
- Voice agent game status handling (separate spec)
- Portal game status display (Spec 050)

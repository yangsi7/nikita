# Plan: Spec 101 — Game Mechanics Remediation

## Implementation Order

Stories ordered by dependency: cooldown persistence first (blocks nothing), then days_played (uses decay job), then decay rebalance (constants change), then conflict timeout, then repetition penalty.

## Story 1: Boss PARTIAL Cooldown Persistence (FR-001)

### T1.1: Add `cool_down_until` column to User model
- Add `cool_down_until: Mapped[datetime | None]` to `nikita/db/models/user.py`
- Apply Supabase migration: `ALTER TABLE users ADD COLUMN cool_down_until TIMESTAMPTZ`

### T1.2: Add `set_cool_down()` to UserRepository
- Add method: `async def set_cool_down(self, user_id, cool_down_until) -> None`
- Updates `users.cool_down_until` for the given user

### T1.3: Wire cooldown into `process_partial()`
- Edit `nikita/engine/chapters/boss.py` `process_partial()`:
  - Accept `user_repository` (already does)
  - Call `user_repository.set_cool_down(user_id, cool_down_until)` before return
- Ensures 24h cooldown is persisted in DB

### T1.4: Add cooldown check to `should_trigger_boss()`
- Add `cool_down_until: datetime | None = None` parameter
- If `cool_down_until is not None and cool_down_until > datetime.now(UTC)`: return False
- Callers updated to pass `user.cool_down_until`

### T1.5: Write tests
- `tests/engine/chapters/test_boss_cooldown.py`:
  - Test cooldown blocks boss trigger
  - Test expired cooldown allows trigger
  - Test process_partial persists cooldown
  - Test None cooldown allows trigger (default)

## Story 2: days_played Increment (FR-002)

### T2.1: Add `increment_days_played()` to UserRepository
- Method: `async def increment_days_played(self, user_id) -> None`
- Increments `days_played` by 1

### T2.2: Wire into decay job
- Edit `nikita/api/routes/tasks.py` decay endpoint
- After decay processing, for each active user:
  - Check if `last_interaction_at.date() > (last_decay_check or created_at).date()`
  - If so, call `increment_days_played(user_id)`
- Use simple date comparison: if user interacted today and `days_played` hasn't been incremented today

### T2.3: Write tests
- `tests/db/test_days_played.py`:
  - Test increment_days_played
  - Test idempotency (no double increment same day)

## Story 3: Ch1 Decay Rebalancing (FR-003)

### T3.1: Swap grace periods in constants.py
- Edit `nikita/engine/constants.py` `GRACE_PERIODS`:
  - Ch1: 72h (was 8h), Ch2: 48h (was 16h), Ch3: 24h (unchanged), Ch4: 16h (was 48h), Ch5: 8h (was 72h)

### T3.2: Update existing decay tests
- `tests/engine/decay/` — update all grace period assertions
- `tests/engine/decay/test_calculator.py` — update expected thresholds

### T3.3: Write balance verification test
- Test: Ch1 user with 70h inactivity is NOT overdue (within 72h grace)
- Test: Ch5 user with 9h inactivity IS overdue (past 8h grace)

## Story 4: EXPLOSIVE Conflict Timeout (FR-004)

### T4.1: Add `EXPLOSIVE_TIMEOUT_HOURS` constant
- Add to `nikita/emotional_state/conflict.py`: `EXPLOSIVE_TIMEOUT_HOURS = 6`

### T4.2: Add timeout check to `check_de_escalation()`
- In `ConflictDetector.check_de_escalation()`:
  - If `current == ConflictState.EXPLOSIVE`:
    - Check `state.conflict_started_at` (or metadata timestamp)
    - If `now - conflict_started_at > EXPLOSIVE_TIMEOUT_HOURS`: return (True, COLD, "timeout_de_escalation")
  - Timeout check runs BEFORE existing valence/interaction checks

### T4.3: Write tests
- `tests/emotional_state/test_explosive_timeout.py`:
  - Test timeout triggers de-escalation after 6h
  - Test no de-escalation before 6h
  - Test de-escalation target is COLD
  - Test timeout trigger reason string

## Story 5: Semantic Repetition Penalty (FR-005)

### T5.1: Add repetition detection to SkipDecision
- Edit `nikita/agents/text/skip.py`:
  - Add `should_skip(self, chapter, recent_messages=None)` parameter
  - If recent_messages provided, compute max pairwise similarity using `difflib.SequenceMatcher`
  - If similarity > 0.8: multiply skip_probability by 2.0

### T5.2: Write tests
- `tests/agents/text/test_skip_repetition.py`:
  - Test identical messages → 2x penalty
  - Test different messages → no penalty
  - Test 81% similarity → penalty applies
  - Test 79% similarity → no penalty
  - Test None recent_messages → default behavior

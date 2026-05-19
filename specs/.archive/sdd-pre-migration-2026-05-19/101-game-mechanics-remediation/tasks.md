# Tasks: Spec 101 — Game Mechanics Remediation

## Story 1: Boss PARTIAL Cooldown Persistence

### T1.1: Add `cool_down_until` column to User model [S]
- [ ] Add `cool_down_until: Mapped[datetime | None]` to User model in `nikita/db/models/user.py`
- [ ] Apply Supabase migration: `ALTER TABLE users ADD COLUMN cool_down_until TIMESTAMPTZ`
- **AC**: Column exists, nullable, datetime type

### T1.2: Add `set_cool_down()` to UserRepository [S]
- [ ] Add `async def set_cool_down(self, user_id: UUID, cool_down_until: datetime) -> None`
- [ ] Updates `user.cool_down_until` and flushes
- **AC**: Method exists, updates user record

### T1.3: Wire cooldown into `process_partial()` [M]
- [ ] Edit `boss.py` `process_partial()` to call `user_repository.set_cool_down()`
- [ ] Pass `cool_down_until` (24h from now) to the method
- **AC**: Cooldown persisted in DB after PARTIAL outcome

### T1.4: Add cooldown check to `should_trigger_boss()` [M]
- [ ] Add `cool_down_until: datetime | None = None` parameter
- [ ] Return False if `cool_down_until > datetime.now(UTC)`
- **AC**: Boss blocked during active cooldown, allowed when expired/None

### T1.5: Write cooldown tests [M]
- [ ] `tests/engine/chapters/test_boss_cooldown.py`
  - `test_cooldown_blocks_boss_trigger`
  - `test_expired_cooldown_allows_trigger`
  - `test_process_partial_persists_cooldown`
  - `test_none_cooldown_allows_trigger`
- **AC**: 4 tests pass

## Story 2: days_played Increment

### T2.1: Add `increment_days_played()` to UserRepository [S]
- [ ] Add `async def increment_days_played(self, user_id: UUID) -> None`
- [ ] Increments `user.days_played += 1` and flushes
- **AC**: Method exists, increments correctly

### T2.2: Wire into decay job [M]
- [ ] Edit decay endpoint in `tasks.py`
- [ ] After decay processing, check each active user
- [ ] Increment days_played if user interacted on a new calendar day
- **AC**: days_played incremented correctly during decay job

### T2.3: Write days_played tests [S]
- [ ] `tests/db/test_days_played.py`
  - `test_increment_days_played`
  - `test_no_double_increment_same_day`
- **AC**: 2 tests pass

## Story 3: Ch1 Decay Rebalancing

### T3.1: Swap grace periods in constants.py [S]
- [ ] Edit `GRACE_PERIODS` in `nikita/engine/constants.py`
  - Ch1: 72h, Ch2: 48h, Ch3: 24h, Ch4: 16h, Ch5: 8h
- **AC**: Grace periods inverted

### T3.2: Update existing decay tests [M]
- [ ] Update `tests/engine/decay/test_calculator.py` assertions
- [ ] Update any other tests that hardcode grace periods
- **AC**: All existing tests pass with new values

### T3.3: Write balance verification test [S]
- [ ] `tests/engine/decay/test_grace_balance.py`
  - `test_ch1_user_safe_at_70h` (within 72h grace)
  - `test_ch5_user_overdue_at_9h` (past 8h grace)
- **AC**: 2 tests pass

## Story 4: EXPLOSIVE Conflict Timeout

### T4.1: Add timeout constant [S]
- [ ] Add `EXPLOSIVE_TIMEOUT_HOURS = 6` to `nikita/emotional_state/conflict.py`
- **AC**: Constant defined

### T4.2: Add timeout check to `check_de_escalation()` [M]
- [ ] In EXPLOSIVE branch of `check_de_escalation()`:
  - Check metadata for `conflict_started_at` timestamp
  - If `now - started_at > 6h`: return (True, COLD, "timeout_de_escalation")
  - Timeout check runs before existing conditions
- **AC**: Auto de-escalation after 6h

### T4.3: Write timeout tests [M]
- [ ] `tests/emotional_state/test_explosive_timeout.py`
  - `test_timeout_triggers_de_escalation_after_6h`
  - `test_no_de_escalation_before_6h`
  - `test_de_escalation_target_is_cold`
  - `test_timeout_trigger_reason`
- **AC**: 4 tests pass

## Story 5: Semantic Repetition Penalty

### T5.1: Add repetition detection to SkipDecision [M]
- [ ] Add `recent_messages: list[str] | None = None` param to `should_skip()`
- [ ] Import `difflib.SequenceMatcher`
- [ ] Compute max pairwise similarity
- [ ] If >0.8: multiply skip_probability by 2.0
- **AC**: Repetitive messages penalized

### T5.2: Write repetition tests [M]
- [ ] `tests/agents/text/test_skip_repetition.py`
  - `test_identical_messages_increase_skip`
  - `test_different_messages_no_penalty`
  - `test_high_similarity_triggers_penalty`
  - `test_low_similarity_no_penalty`
  - `test_none_messages_default_behavior`
- **AC**: 5 tests pass

---

## Summary

| Story | Tasks | Size | Tests |
|-------|-------|------|-------|
| S1: Boss Cooldown | T1.1-T1.5 | M | 4 |
| S2: days_played | T2.1-T2.3 | S | 2 |
| S3: Decay Rebalance | T3.1-T3.3 | M | 2+ |
| S4: EXPLOSIVE Timeout | T4.1-T4.3 | M | 4 |
| S5: Repetition Penalty | T5.1-T5.2 | S | 5 |
| **Total** | **15 tasks** | | **17+ tests** |

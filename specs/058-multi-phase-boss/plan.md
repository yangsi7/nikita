# Plan: Spec 058 — Multi-Phase Boss + Warmth

**Spec**: `specs/058-multi-phase-boss/spec.md`
**Wave**: B (parallel with 056)
**Depends on**: Spec 057 (COMPLETE — conflict_details JSONB, ConflictDetails model)
**Feature Flag**: `multi_phase_boss_enabled` (default: OFF)
**Risk**: HIGH — Touches boss flow, scoring pipeline, message handler, LLM judgment

---

## 1. Summary

This plan transforms the single-turn binary boss encounter into a 2-phase (OPENING -> RESOLUTION) multi-turn system with a new PARTIAL outcome. Phase state is persisted in the existing `conflict_details` JSONB column (Spec 057 infrastructure). The scoring pipeline gains vulnerability exchange detection (new behavior tag in the analyzer prompt) and a warmth bonus (+2/+1/+0 trust with diminishing returns per conversation). All changes are gated behind `multi_phase_boss_enabled` (default OFF), ensuring zero regression on the existing single-turn boss path.

---

## 2. Implementation Phases

### Phase A: Feature Flag + Models (Foundation)

#### T-A1: Add `multi_phase_boss_enabled` feature flag
- **Files**: `nikita/config/settings.py`
- **Description**: Add `multi_phase_boss_enabled: bool = Field(default=False, ...)` following the `conflict_temperature_enabled` pattern at line ~148. Add convenience function in `nikita/engine/chapters/__init__.py`.
- **Signature**:
  ```python
  # settings.py (after conflict_temperature_enabled)
  multi_phase_boss_enabled: bool = Field(
      default=False,
      description="Enable 2-phase boss encounters with PARTIAL outcome. Rollback: MULTI_PHASE_BOSS_ENABLED=false",
  )

  # chapters/__init__.py
  def is_multi_phase_boss_enabled() -> bool:
      from nikita.config.settings import get_settings
      return get_settings().multi_phase_boss_enabled
  ```
- **AC refs**: AC-8.1, AC-8.2
- **Effort**: XS (15 min)
- **Depends on**: None

#### T-A2: Add `BossPhase` enum + `BossPhaseState` model
- **Files**: `nikita/engine/chapters/boss.py` (new models at top)
- **Description**: Add `BossPhase(str, Enum)` with OPENING/RESOLUTION values and `BossPhaseState(BaseModel)` with phase, chapter, started_at, turn_count, conversation_history fields. These are pure data models with no DB dependency.
- **Signature**:
  ```python
  class BossPhase(str, Enum):
      OPENING = "opening"
      RESOLUTION = "resolution"

  class BossPhaseState(BaseModel):
      phase: BossPhase
      chapter: int
      started_at: datetime
      turn_count: int = 0
      conversation_history: list[dict[str, str]] = []
  ```
- **AC refs**: AC-2.1
- **Effort**: XS (15 min)
- **Depends on**: None

#### T-A3: Extend `BossResult` enum with PARTIAL
- **Files**: `nikita/engine/chapters/judgment.py`
- **Description**: Add `PARTIAL = "PARTIAL"` to the existing `BossResult` enum. Update `JudgmentResult.outcome` type hint comment to include PARTIAL. Must be backward-compatible (PASS/FAIL still work).
- **AC refs**: AC-3.1
- **Effort**: XS (10 min)
- **Depends on**: None

#### T-A4: Add `boss_phase` field to `ConflictDetails` model
- **Files**: `nikita/conflicts/models.py`
- **Description**: Add `boss_phase: dict[str, Any] | None = Field(default=None)` to `ConflictDetails` (line ~394). This stores `BossPhaseState.model_dump()` as nested JSONB. When None, no boss is active.
- **AC refs**: AC-2.2, AC-2.5
- **Effort**: XS (15 min)
- **Depends on**: T-A2

#### T-A5: DB migration — add `vulnerability_exchanges` to `user_metrics`
- **Files**: Supabase migration (via MCP)
- **Description**: `ALTER TABLE user_metrics ADD COLUMN vulnerability_exchanges INT DEFAULT 0;` No ORM model change needed (tracked in JSONB or raw query).
- **AC refs**: AC-6.3
- **Effort**: XS (10 min)
- **Depends on**: None

**Phase A tests**: 8 unit tests — BossPhase enum, BossPhaseState serialization/deserialization, BossResult.PARTIAL existence, ConflictDetails.boss_phase round-trip, feature flag default OFF.

---

### Phase B: Phase Manager (Core State Machine)

#### T-B1: Create `phase_manager.py` with `BossPhaseManager` class
- **Files**: `nikita/engine/chapters/phase_manager.py` (NEW)
- **Description**: Central class for boss phase lifecycle. Methods:
  - `start_boss(chapter: int) -> BossPhaseState` — creates OPENING state
  - `advance_phase(state: BossPhaseState, user_message: str, nikita_response: str) -> BossPhaseState` — OPENING->RESOLUTION, appends to conversation_history
  - `is_resolution_complete(state: BossPhaseState) -> bool` — True when phase=RESOLUTION and turn_count >= 2
  - `get_phase_prompt(state: BossPhaseState) -> BossPrompt` — dispatches to phase-specific prompt
  - `clear_boss_phase() -> None` — returns None (for writing back to conflict_details)
- **Signature**:
  ```python
  class BossPhaseManager:
      def start_boss(self, chapter: int) -> BossPhaseState: ...
      def advance_phase(self, state: BossPhaseState, user_message: str, nikita_response: str) -> BossPhaseState: ...
      def is_resolution_complete(self, state: BossPhaseState) -> bool: ...
      def get_phase_prompt(self, state: BossPhaseState) -> dict[str, str]: ...
  ```
- **AC refs**: AC-1.1, AC-1.2, AC-1.3, AC-2.3, AC-2.4
- **Effort**: M (1.5 hr)
- **Depends on**: T-A2, T-A4

#### T-B2: Persistence helpers — read/write boss_phase in conflict_details
- **Files**: `nikita/engine/chapters/phase_manager.py`
- **Description**: Add static methods:
  - `persist_phase(conflict_details: dict | None, state: BossPhaseState) -> dict` — writes `state.model_dump(mode="json")` into `conflict_details["boss_phase"]`, returns updated dict
  - `load_phase(conflict_details: dict | None) -> BossPhaseState | None` — reads and parses `conflict_details.get("boss_phase")`, returns None if absent
  Uses `ConflictDetails.from_jsonb()` pattern from Spec 057.
- **AC refs**: AC-1.4, AC-2.2, AC-2.3
- **Effort**: S (30 min)
- **Depends on**: T-B1

#### T-B3: Boss timeout logic (24h auto-FAIL)
- **Files**: `nikita/engine/chapters/phase_manager.py`
- **Description**: Add `is_timed_out(state: BossPhaseState, now: datetime | None = None) -> bool` that checks `(now - state.started_at) > timedelta(hours=24)`. Called in message handler before advancing phase.
- **AC refs**: AC-1.6
- **Effort**: XS (15 min)
- **Depends on**: T-B1

**Phase B tests**: 15 unit tests — start_boss returns OPENING, advance_phase transitions to RESOLUTION, advance_phase appends history, is_resolution_complete returns True after 2 turns, persist_phase round-trip through ConflictDetails, load_phase returns None for empty, timeout at 24h, timeout before 24h, interrupted boss preserves state, clear_boss_phase.

---

### Phase C: Phase-Prompt Variants (10 Prompts)

#### T-C1: Create phase-aware prompt structure
- **Files**: `nikita/engine/chapters/prompts.py`
- **Description**: Add `BOSS_PHASE_PROMPTS: dict[int, dict[str, BossPrompt]]` — 2 phases x 5 chapters = 10 prompts. Structure: `{1: {"opening": BossPrompt(...), "resolution": BossPrompt(...)}, ...}`. OPENING prompts reuse existing `BOSS_PROMPTS[ch]` content. RESOLUTION prompts are new (guide toward judgment).
- **AC refs**: AC-4.1, AC-4.2, AC-4.3, AC-4.4, AC-4.5
- **Effort**: M (1.5 hr — writing 5 new RESOLUTION prompts)
- **Depends on**: T-A2

#### T-C2: Add `get_boss_phase_prompt()` function
- **Files**: `nikita/engine/chapters/prompts.py`
- **Description**: `get_boss_phase_prompt(chapter: int, phase: str) -> BossPrompt` — retrieves phase-specific prompt. Falls back to `get_boss_prompt(chapter)` if phase not found. Validates chapter 1-5 and phase opening/resolution.
- **Signature**:
  ```python
  def get_boss_phase_prompt(chapter: int, phase: str) -> BossPrompt:
      if chapter not in BOSS_PHASE_PROMPTS:
          raise KeyError(f"Invalid chapter {chapter}. Must be 1-5.")
      prompts = BOSS_PHASE_PROMPTS[chapter]
      if phase not in prompts:
          raise KeyError(f"Invalid phase {phase}. Must be opening/resolution.")
      return prompts[phase]
  ```
- **AC refs**: AC-4.4, AC-4.6
- **Effort**: S (20 min)
- **Depends on**: T-C1

**Phase C tests**: 12 tests — all 10 prompts exist and have required keys (challenge_context, success_criteria, in_character_opening), get_boss_phase_prompt invalid chapter, invalid phase, Ch1 opening matches existing BOSS_PROMPTS[1].

---

### Phase D: Multi-Turn Judgment

#### T-D1: Update `BossJudgment` for multi-turn context
- **Files**: `nikita/engine/chapters/judgment.py`
- **Description**: Add `judge_multi_phase_outcome()` method that receives `phase_state: BossPhaseState` with full conversation history from both phases. Build judgment prompt that evaluates OPENING response quality + RESOLUTION response quality. Include PARTIAL criteria: "acknowledged issue but didn't resolve."
- **Signature**:
  ```python
  async def judge_multi_phase_outcome(
      self,
      phase_state: BossPhaseState,
      chapter: int,
      boss_prompt: dict[str, Any],
  ) -> JudgmentResult:
  ```
- **AC refs**: AC-5.1, AC-5.2, AC-5.3, AC-5.4
- **Effort**: M (1 hr)
- **Depends on**: T-A2, T-A3

#### T-D2: Confidence-based PARTIAL threshold
- **Files**: `nikita/engine/chapters/judgment.py`
- **Description**: Update the judgment system prompt to instruct the LLM to return confidence (0.0-1.0). Add post-processing: if confidence < 0.7 AND outcome is PASS or FAIL, override to PARTIAL. This ensures ambiguous responses get the truce outcome.
- **AC refs**: AC-5.5
- **Effort**: S (30 min)
- **Depends on**: T-D1

**Phase D tests**: 10 tests — multi-phase judgment with PASS/PARTIAL/FAIL, confidence override to PARTIAL, full conversation history passed, both phases evaluated, error handling (LLM failure -> FAIL).

---

### Phase E: Boss State Machine + Message Handler Integration

#### T-E1: Add `process_partial()` to `BossStateMachine`
- **Files**: `nikita/engine/chapters/boss.py`
- **Description**: New method following `process_pass`/`process_fail` pattern. PARTIAL: does NOT increment boss_attempts, does NOT advance chapter, sets status back to "active", records cool-down timestamp for 24h delay.
- **Signature**:
  ```python
  async def process_partial(
      self,
      user_id: UUID,
      user_repository: UserRepository | None = None,
  ) -> dict[str, Any]:
      # Returns: {"attempts": int, "game_status": "active", "cool_down_until": datetime}
  ```
- **AC refs**: AC-3.2, AC-3.3, AC-3.4, AC-3.5
- **Effort**: S (30 min)
- **Depends on**: T-A3

#### T-E2: Update `process_outcome()` for three-way dispatch
- **Files**: `nikita/engine/chapters/boss.py`
- **Description**: Modify `process_outcome` to accept `outcome: str` (PASS/FAIL/PARTIAL) instead of `passed: bool`. When flag is OFF, preserve `passed: bool` signature via overload or default. Dispatch to `process_pass`, `process_fail`, or `process_partial`.
- **AC refs**: AC-3.1, AC-8.2, AC-8.3
- **Effort**: S (30 min)
- **Depends on**: T-E1

#### T-E3: Rewrite `_handle_boss_response` for multi-phase flow
- **Files**: `nikita/platforms/telegram/message_handler.py` (~line 794-886)
- **Description**: The most critical integration point. When flag ON:
  1. Load `BossPhaseState` from `user.conflict_details` via `BossPhaseManager.load_phase()`
  2. If phase=OPENING: advance to RESOLUTION, persist state, send RESOLUTION prompt (no judgment yet)
  3. If phase=RESOLUTION: run `judge_multi_phase_outcome()`, process outcome (3-way), clear phase
  4. Handle timeout (24h auto-FAIL)
  When flag OFF: preserve existing single-turn flow exactly.
- **Pattern**: Branch at top of method based on `is_multi_phase_boss_enabled()`, delegate to `_handle_multi_phase_boss()` (new private method) vs existing code.
- **AC refs**: AC-1.1 through AC-1.6, AC-8.2, AC-8.3
- **Effort**: L (2 hr)
- **Depends on**: T-B1, T-B2, T-B3, T-D1, T-E2

#### T-E4: Boss initiation for multi-phase
- **Files**: `nikita/engine/chapters/boss.py`, `nikita/platforms/telegram/message_handler.py`
- **Description**: When boss triggers and flag ON, `initiate_boss()` creates `BossPhaseState(phase=OPENING)`, persists to conflict_details, sends OPENING prompt. Update `initiate_boss()` to accept optional `conflict_details` parameter and return updated details.
- **AC refs**: AC-1.1, AC-2.2
- **Effort**: S (30 min)
- **Depends on**: T-B1, T-B2

#### T-E5: PARTIAL response messaging
- **Files**: `nikita/platforms/telegram/message_handler.py`
- **Description**: Add `_send_boss_partial_message(chat_id, chapter)` following the pattern of `_send_boss_pass_message`/`_send_boss_fail_message`. Message: empathetic truce tone, hint at cool-down period.
- **AC refs**: AC-3.5
- **Effort**: XS (15 min)
- **Depends on**: T-E3

**Phase E tests**: 18 tests — multi-phase boss full flow (OPENING->RESOLUTION->PASS), OPENING->RESOLUTION->PARTIAL, OPENING->RESOLUTION->FAIL, timeout auto-FAIL, interrupted boss (non-boss message between phases), flag OFF preserves single-turn, process_partial no increment, process_partial no advance, cool-down delay, boss initiation persists state, PARTIAL messaging.

---

### Phase F: Vulnerability Exchange Detection + Warmth Bonus

#### T-F1: Add vulnerability exchange detection to analyzer prompt
- **Files**: `nikita/engine/scoring/analyzer.py`
- **Description**: Append vulnerability exchange section to `ANALYSIS_SYSTEM_PROMPT` (~line 80). Define detection criteria: Nikita shares something vulnerable + player responds with empathy/matching depth. Add behavior tag `"vulnerability_exchange"` to `behaviors_identified`.
- **Prompt addition**:
  ```
  ## Vulnerability Exchange Detection
  Detect if a vulnerability exchange occurred in this interaction:
  - Nikita shared something vulnerable (fear, insecurity, personal struggle)
  - Player responded with empathy, matching vulnerability, or genuine understanding
  If both conditions are met, include "vulnerability_exchange" in behaviors_identified.
  Only tag genuine mutual vulnerability — one-sided sharing is NOT an exchange.
  ```
- **AC refs**: AC-6.1, AC-6.2, AC-6.4
- **Effort**: S (30 min)
- **Depends on**: None

#### T-F2: Warmth bonus in `ScoreCalculator`
- **Files**: `nikita/engine/scoring/calculator.py`
- **Description**: Add `apply_warmth_bonus(deltas: MetricDeltas, v_exchange_count: int) -> MetricDeltas` method. Bonus logic: count=0 -> +2 trust, count=1 -> +1 trust, count>=2 -> +0. Called in `calculate()` after engagement multiplier, only when `"vulnerability_exchange"` in analysis.behaviors_identified. Pass `v_exchange_count` from conversation-scoped counter.
- **Signature**:
  ```python
  def apply_warmth_bonus(
      self,
      deltas: MetricDeltas,
      v_exchange_count: int,
  ) -> MetricDeltas:
      bonus = {0: Decimal("2"), 1: Decimal("1")}.get(v_exchange_count, Decimal("0"))
      if bonus > 0:
          new_trust = min(deltas.trust + bonus, Decimal("10"))
          return deltas.model_copy(update={"trust": new_trust})
      return deltas
  ```
- **AC refs**: AC-7.1, AC-7.2, AC-7.3, AC-7.4
- **Effort**: S (30 min)
- **Depends on**: T-F1

#### T-F3: Conversation-scoped V-exchange counter
- **Files**: `nikita/engine/scoring/service.py`
- **Description**: Add `v_exchange_count: int = 0` parameter to `score_interaction()`. When `"vulnerability_exchange"` detected in analysis, pass count to `calculator.apply_warmth_bonus()`. Caller (orchestrator/message handler) tracks count per conversation and increments after each detection.
- **AC refs**: AC-7.5
- **Effort**: S (30 min)
- **Depends on**: T-F2

**Phase F tests**: 12 tests — vulnerability_exchange tag detection, warmth bonus +2 first exchange, +1 second, +0 third, trust capped at 10, counter reset per conversation, no bonus when no exchange detected, bonus applied after multiplier, interaction with flag OFF (no bonus).

---

### Phase G: Integration + Backward Compatibility

#### T-G1: Update `chapters/__init__.py` exports
- **Files**: `nikita/engine/chapters/__init__.py`
- **Description**: Export `BossPhase`, `BossPhaseState`, `BossPhaseManager`, `is_multi_phase_boss_enabled`, `get_boss_phase_prompt`.
- **AC refs**: AC-8.1
- **Effort**: XS (10 min)
- **Depends on**: T-B1, T-C2

#### T-G2: Backward compatibility test suite
- **Files**: `tests/engine/chapters/test_boss_backward_compat.py` (NEW)
- **Description**: Run ALL existing boss tests with flag OFF. Verify: single-turn PASS/FAIL flow unchanged, BossResult still has PASS/FAIL, process_outcome with `passed=True/False` still works, no PARTIAL behavior when flag OFF.
- **AC refs**: AC-8.2, AC-8.4
- **Effort**: M (1 hr)
- **Depends on**: T-E2

#### T-G3: Multi-phase integration test suite
- **Files**: `tests/engine/chapters/test_boss_multi_phase.py` (NEW)
- **Description**: End-to-end tests with flag ON: full 2-phase flow, PARTIAL outcome, timeout, interrupted boss, persistence round-trip, vulnerability exchange + warmth bonus during boss.
- **AC refs**: AC-8.5
- **Effort**: M (1.5 hr)
- **Depends on**: All T-E tasks

#### T-G4: Adversarial tests
- **Files**: `tests/engine/chapters/test_boss_adversarial.py` (NEW)
- **Description**: Edge cases: rapid phase transitions, concurrent boss + conflict temperature, boss during game_over/won status, corrupt conflict_details JSONB, phase state with missing fields, boss_phase present but flag OFF (should ignore).
- **Effort**: M (1 hr)
- **Depends on**: T-G2, T-G3

---

## 3. Dependency Graph

```
T-A1 (flag) ──────────────────────────────────────────────┐
T-A2 (models) ─────┬──── T-B1 (phase_manager) ──┬─ T-B2 ─┤
                    │          │                  │        │
T-A3 (PARTIAL enum) ┤    T-B3 (timeout)          │        │
                    │                             │        │
T-A4 (CD field) ────┘                             │        │
                                                  │        │
T-A5 (migration) ─────────────────────────────────┤        │
                                                  │        │
T-C1 (prompts) ── T-C2 (get fn) ─────────────────┤        │
                                                  │        │
T-D1 (multi judge) ── T-D2 (confidence) ──────────┤        │
                                                  │        │
T-E1 (partial) ── T-E2 (3-way) ───────────────────┤        │
                                                  │        │
                    T-E3 (msg handler) ── T-E4 ── T-E5 ───┤
                                                           │
T-F1 (vuln detect) ── T-F2 (warmth) ── T-F3 (counter) ───┤
                                                           │
                    T-G1 (exports) ── T-G2 ── T-G3 ── T-G4
```

**Critical path**: T-A2 -> T-B1 -> T-B2 -> T-E3 -> T-G3

---

## 4. Risk Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Multi-phase boss breaks existing single-turn flow | HIGH | Feature flag (OFF by default). T-G2 backward compat suite runs all existing tests with flag OFF. Branch at top of `_handle_boss_response`. |
| Phase state corruption in conflict_details JSONB | HIGH | `BossPhaseState` validated by Pydantic. `load_phase()` returns None on parse error (graceful degradation to single-turn). |
| Boss timeout race condition (24h boundary) | MEDIUM | Use `started_at` from persisted state (not in-memory). Always check timeout before advancing phase. |
| PARTIAL outcome gaming (players intentionally get PARTIAL to avoid FAIL) | LOW | PARTIAL has 24h cool-down. Net effect: delays boss, doesn't help player advance. |
| Vulnerability detection false positives | MEDIUM | Behavior tag only (no separate LLM call). Warmth bonus is small (+2 max) and diminishing. False positives have minimal game impact. |
| conflict_details JSONB size growth | LOW | boss_phase stores max 4 messages (2 phases x 2 turns). Cleared on completion. Temperature data already in same JSONB. |

---

## 5. Effort Summary

| Phase | Tasks | Effort |
|-------|-------|--------|
| A: Foundation | T-A1..A5 (5 tasks) | 1 hr |
| B: Phase Manager | T-B1..B3 (3 tasks) | 2.25 hr |
| C: Prompts | T-C1..C2 (2 tasks) | 2 hr |
| D: Judgment | T-D1..D2 (2 tasks) | 1.5 hr |
| E: Integration | T-E1..E5 (5 tasks) | 3.75 hr |
| F: Warmth | T-F1..F3 (3 tasks) | 1.5 hr |
| G: Compat + Tests | T-G1..G4 (4 tasks) | 3.5 hr |
| **Total** | **24 tasks** | **~15.5 hr** |

Test budget: ~75 tests across phases (8 + 15 + 12 + 10 + 18 + 12 = 75, plus G-suite).

---

## 6. Files Changed Summary

| File | Action | Phase |
|------|--------|-------|
| `nikita/config/settings.py` | MODIFY — add feature flag | A |
| `nikita/engine/chapters/__init__.py` | MODIFY — exports + helper fn | A, G |
| `nikita/engine/chapters/boss.py` | MODIFY — models, process_partial, 3-way dispatch | A, E |
| `nikita/engine/chapters/judgment.py` | MODIFY — PARTIAL enum, multi-phase judgment | A, D |
| `nikita/engine/chapters/prompts.py` | MODIFY — 10 phase-prompt variants | C |
| `nikita/engine/chapters/phase_manager.py` | CREATE — phase state machine | B |
| `nikita/engine/scoring/analyzer.py` | MODIFY — vulnerability exchange prompt | F |
| `nikita/engine/scoring/calculator.py` | MODIFY — warmth bonus | F |
| `nikita/engine/scoring/service.py` | MODIFY — v_exchange_count param | F |
| `nikita/conflicts/models.py` | MODIFY — boss_phase field | A |
| `nikita/platforms/telegram/message_handler.py` | MODIFY — multi-phase boss | E |
| Supabase migration | CREATE — vulnerability_exchanges column | A |
| `tests/engine/chapters/test_boss_*.py` (3 files) | CREATE | G |

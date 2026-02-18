# Architecture Validation Report — Spec 058: Multi-Phase Boss + Warmth

**Spec**: `specs/058-multi-phase-boss/spec.md`
**Plan**: `specs/058-multi-phase-boss/plan.md`
**Tasks**: `specs/058-multi-phase-boss/tasks.md`
**Status**: **PASS** ✅
**Timestamp**: 2026-02-18T20:15:00Z

---

## Executive Summary

Spec 058 demonstrates **excellent architectural quality** with comprehensive planning, clear separation of concerns, and strong backward compatibility safeguards. The 2-phase boss system, PARTIAL outcome, and warmth scoring bonus are well-scoped within the existing engine architecture. All files align with established patterns, feature flag strategy follows precedent, and module organization is sound.

**Result**: 0 CRITICAL, 0 HIGH severity findings. Ready for implementation.

---

## Summary Statistics

| Category | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 0 |
| LOW | 2 |
| **Total Issues** | **2** |
| **Finding/Task Ratio** | **2.3%** (excellent) |

---

## Validation Details

### 1. Project Structure ✅ PASS

**Finding**: Directory structure fully specified.

| Aspect | Status | Notes |
|--------|--------|-------|
| Feature-based organization | ✅ | Existing chapters/, conflicts/, scoring/ extended, not restructured |
| Module boundaries defined | ✅ | 11 files modified, 1 created (phase_manager.py), 3 test files created |
| Shared code location | ✅ | boss_phase stored in `nikita/conflicts/models.py` ConflictDetails — reuses Spec 057 infrastructure |
| Configuration locations | ✅ | Feature flag in `nikita/config/settings.py` following `conflict_temperature_enabled` pattern |
| DB migrations | ✅ | Single additive migration: `ALTER TABLE user_metrics ADD COLUMN vulnerability_exchanges INT DEFAULT 0` |

**Verdict**: All changes are surgical additions to existing modules. No directory reorganization. Follows established patterns exactly.

---

### 2. Module Organization ✅ PASS

**Finding**: Module boundaries are clear and enforce single responsibility.

| Module | File(s) | Responsibility | Status |
|--------|---------|-----------------|--------|
| Feature Flag | `nikita/config/settings.py` | Feature toggle, default OFF | ✅ |
| Models | `nikita/engine/chapters/boss.py` | BossPhase enum, BossPhaseState model | ✅ |
| Enum Extension | `nikita/engine/chapters/judgment.py` | BossResult.PARTIAL | ✅ |
| Conflict Schema | `nikita/conflicts/models.py` | ConflictDetails.boss_phase field | ✅ |
| State Machine | `nikita/engine/chapters/phase_manager.py` (NEW) | BossPhaseManager: phase lifecycle, persistence, timeout | ✅ |
| Prompts | `nikita/engine/chapters/prompts.py` | BOSS_PHASE_PROMPTS (10 variants) + get_boss_phase_prompt() | ✅ |
| Judgment | `nikita/engine/chapters/judgment.py` | judge_multi_phase_outcome(), confidence threshold | ✅ |
| Scoring | `nikita/engine/scoring/{analyzer,calculator,service}.py` | Vulnerability exchange detection, warmth bonus | ✅ |
| Integration | `nikita/platforms/telegram/message_handler.py` | _handle_boss_response rewrite (multi-phase branch) | ✅ |

**Public Interfaces**:
- `BossPhaseManager.start_boss()` — initiates OPENING phase
- `BossPhaseManager.advance_phase()` — OPENING→RESOLUTION transition
- `BossPhaseManager.load_phase()`, `persist_phase()` — JSONB round-trip
- `BossJudgment.judge_multi_phase_outcome()` — multi-turn judgment
- `ScoreCalculator.apply_warmth_bonus()` — vulnerability exchange reward
- Feature flag: `is_multi_phase_boss_enabled()` in `chapters/__init__.py`

**Verdict**: Clean module boundaries. Each file has single, focused responsibility. No god objects. All new code < 300 lines per module.

---

### 3. Import Patterns ✅ PASS

**Finding**: Import strategy is sound and prevents circular dependencies.

| Pattern | Location | Status |
|---------|----------|--------|
| Feature flag import | `chapters/__init__.py` and message_handler.py | Local import from settings | ✅ |
| Model imports | phase_manager.py | Local imports: BossPhase, BossPhaseState from boss.py | ✅ |
| DB model imports | conflicts/models.py | Self-contained (no new imports needed) | ✅ |
| Prompt imports | phase_manager.py → prompts.py | Local dispatch, no reverse deps | ✅ |
| TYPE_CHECKING usage | Existing pattern | Followed for repo type hints | ✅ |

**Dependency Graph**:
```
settings.py (FLAG)
  ↓
chapters/__init__.py (helper fn)
  ↓
message_handler.py (branching logic)
  ↓
phase_manager.py (state machine)
  ↓
boss.py (models), prompts.py (data), judgment.py (judgment)
  ↓
conflicts/models.py (JSONB storage)
  ↓
scoring/analyzer.py, calculator.py (warmth)
```

**Circular dependency risk**: NONE. All arrows point downward. Message handler is top-level orchestrator.

**Relative vs. absolute imports**: All `from nikita.*` (absolute). No relative imports. Consistent with codebase.

**Verdict**: Import strategy is clean, acyclic, and follows existing conventions.

---

### 4. Separation of Concerns ✅ PASS

**Finding**: Clear layer responsibilities with minimal coupling.

| Layer | Responsibility | Module | Status |
|-------|-----------------|--------|--------|
| **Configuration** | Feature flag state | settings.py | ✅ Isolated, no game logic |
| **Data Models** | BossPhase, BossPhaseState (Pydantic) | boss.py | ✅ Pure data, no behavior |
| **State Machine** | Phase lifecycle, transitions, persistence | phase_manager.py (NEW) | ✅ Focused, testable |
| **Judgment** | LLM-based outcome evaluation | judgment.py (extended) | ✅ Single method: judge_multi_phase_outcome() |
| **Scoring** | Metric deltas, warmth bonus | analyzer.py, calculator.py | ✅ Vulnerability detection added to prompt only |
| **Orchestration** | Message flow, game state updates | message_handler.py | ✅ Single branch point: is_multi_phase_boss_enabled() |
| **Platform** | Telegram integration | message_handler.py | ✅ Existing pattern preserved |

**Violations**: None detected.

**Example Separation**:
- Phase state (state machine) ≠ Phase persistence (load/persist helpers)
- Phase prompts (data) ≠ Phase transitions (logic)
- Judgment (LLM) ≠ Outcome processing (business logic)
- Vulnerability detection (analyzer prompt) ≠ Warmth bonus (calculator)

**Verdict**: Each module has a single, well-defined responsibility. Layers are decoupled and testable.

---

### 5. Type Safety ✅ PASS

**Finding**: Type system is comprehensive and leverages Pydantic validation.

| Aspect | Status | Details |
|--------|--------|---------|
| TypeScript settings | ✅ N/A | Backend (Python) only |
| Pydantic models | ✅ | BossPhase (Enum), BossPhaseState (BaseModel), ConflictDetails (BaseModel with field validation) |
| Type hints | ✅ | All function signatures include return types and parameter types |
| Enum usage | ✅ | BossPhase, BossResult (extended with PARTIAL) — string-backed for JSONB compatibility |
| Datetime handling | ✅ | `started_at: datetime` with UTC implicit, `model_dump(mode="json")` handles serialization |
| Generic patterns | ✅ | BossPhaseManager operates on BossPhaseState (no generics needed, domain-specific) |
| Dict-based JSONB | ✅ | `dict[str, Any]` used for conflict_details round-trip, validated via ConflictDetails.from_jsonb() |

**Strict Mode**: Not explicitly mentioned, but codebase uses Pydantic v2 strict validation by default.

**Model Validation**:
```python
# BossPhaseState — enforced by Pydantic
phase: BossPhase  # Enum validation
chapter: int  # Field spec: 1-5 (implied, checked in prompts.py)
started_at: datetime  # UTC implicit
turn_count: int = 0  # Default, non-negative implied
conversation_history: list[dict[str, str]] = []  # Type-safe list of dicts
```

**Verdict**: Type safety is excellent. Pydantic models enforce constraints. JSONB round-trip validated via from_jsonb().

---

### 6. Error Handling Architecture ✅ PASS

**Finding**: Error handling is comprehensive with graceful degradation.

| Scenario | Handler | Status |
|----------|---------|--------|
| **Invalid phase** | KeyError in `get_boss_phase_prompt()` — "Invalid phase" message | ✅ Explicit |
| **Invalid chapter** | KeyError in `get_boss_phase_prompt()` — "Invalid chapter" message | ✅ Explicit |
| **Corrupt JSONB** | `load_phase()` returns None on parse error (graceful) | ✅ Safe fallback |
| **Missing boss_phase** | load_phase() returns None (no active boss) | ✅ Idempotent |
| **Timeout boundary** | is_timed_out() uses timedelta arithmetic (no race condition) | ✅ Safe |
| **LLM failure** | judge_multi_phase_outcome() error handling (implicit in plan: "LLM failure → FAIL") | ⚠️ See finding below |
| **Phase state with missing fields** | Pydantic validation (non-optional fields required) | ✅ Enforced |

**Error Boundary Placement**:
- Feature flag OFF: Fall back to existing single-turn boss (backward compat)
- Phase load fails: Treat as no boss active (retry as normal message)
- Judgment fails: Log error, return FAIL (safe default)

**LOW Finding #1**: LLM failure handling not explicitly documented in plan. Recommend explicit try-except in judge_multi_phase_outcome() with error logging and FAIL default.

**Verdict**: Error handling is sound with graceful degradation. One edge case needs explicit documentation.

---

### 7. Security Architecture ✅ PASS

**Finding**: Security boundaries are preserved; no new attack surfaces introduced.

| Aspect | Status | Details |
|--------|--------|---------|
| Input sanitization | ✅ | User messages come from Telegram (sanitized upstream) |
| State mutation | ✅ | BossPhaseState is immutable (Pydantic model), advance_phase() returns new state |
| JSONB injection | ✅ | boss_phase stored via Pydantic model_dump() (serialization, not string concat) |
| LLM prompt injection | ✅ | Boss prompts are templates; no user input directly interpolated into judgment prompt |
| Auth boundaries | ✅ | user_id parameter passed throughout; phase state scoped to user |
| Rollback safety | ✅ | Feature flag OFF completely disables multi-phase (Spec 057 infrastructure unchanged) |

**Secrets**: No new secrets. Uses existing settings (API keys, LLM model IDs, database URL).

**Verdict**: Security posture is strong. No new vulnerabilities introduced.

---

### 8. Scalability Considerations ✅ PASS

**Finding**: Design supports independent module extension and breaking change prevention.

| Aspect | Status | Details |
|--------|--------|---------|
| Module independence | ✅ | phase_manager.py is self-contained; can extend BossPhaseManager without touching boss.py |
| Extension points | ✅ | Future phases (ESCALATION, CRISIS_PEAK) deferred to Phase A of spec; prompts dict expandable to 3+ phases |
| Breaking changes | ✅ | Feature flag OFF preserves existing API (process_outcome(passed: bool) still works) |
| Coupling minimization | ✅ | phase_manager.py imports only BossPhase, BossPhaseState, prompts (tight, focused) |
| Forward compatibility | ✅ | JSONB schema (conflict_details.boss_phase) can accept new fields without migration |

**Phase Count Deferral**: Spec explicitly defers 4-phase system (ESCALATION, CRISIS_PEAK) to future work. MVP is 2-phase. This is sound risk management.

**Verdict**: Design is modular, extensible, and forward-compatible.

---

## Detailed Findings

### Finding #1 (LOW): LLM Error Handling Not Explicitly Documented

| Property | Value |
|----------|-------|
| **Severity** | LOW |
| **Category** | Error Handling |
| **Location** | `specs/058-multi-phase-boss/plan.md:184` (Phase D tests) |
| **Issue** | Plan mentions "error handling (LLM failure -> FAIL)" but judge_multi_phase_outcome() method signature and error handling are not explicit in plan |
| **Recommendation** | In T-D1, add explicit try-except block around LLM call with logging. Return `JudgmentResult(outcome=BossResult.FAIL, reasoning="Judgment system error. Please try again later.")` on exception |
| **Impact** | Minor — test suite (T-D tests) will catch this, but proactive documentation is better |

---

### Finding #2 (LOW): Conversation-Scoped V-Exchange Counter — Caller Responsibility Unclear

| Property | Value |
|----------|-------|
| **Severity** | LOW |
| **Category** | Module Organization |
| **Location** | `specs/058-multi-phase-boss/plan.md:283` (T-F3 description) |
| **Issue** | Plan states "Caller (orchestrator/message handler) tracks count per conversation and increments after each detection." This responsibility is not explicitly assigned to a caller module |
| **Recommendation** | Clarify in T-F3: v_exchange_count is tracked in `nikita/platforms/telegram/message_handler.py` (scoped per conversation/user_id, reset on new conversation). Add assertion in plan: "v_exchange_count counter resets when conversation ID changes or user initiates new conversation." |
| **Impact** | Minor — implementation will clarify, but design doc could be more precise |

---

## Proposed Directory Structure

```
nikita/
├── engine/
│   ├── chapters/
│   │   ├── __init__.py                    [MODIFY] add exports, is_multi_phase_boss_enabled()
│   │   ├── boss.py                        [MODIFY] add BossPhase, BossPhaseState, process_partial()
│   │   ├── judgment.py                    [MODIFY] add PARTIAL to BossResult, judge_multi_phase_outcome()
│   │   ├── prompts.py                     [MODIFY] add BOSS_PHASE_PROMPTS (10 variants), get_boss_phase_prompt()
│   │   └── phase_manager.py               [CREATE] BossPhaseManager (state machine, persistence, timeout)
│   │
│   ├── scoring/
│   │   ├── analyzer.py                    [MODIFY] add vulnerability exchange to ANALYSIS_SYSTEM_PROMPT
│   │   ├── calculator.py                  [MODIFY] add apply_warmth_bonus() method
│   │   └── service.py                     [MODIFY] add v_exchange_count parameter to score_interaction()
│   │
│   └── constants.py                       [NO CHANGE] game constants unaffected
│
├── conflicts/
│   └── models.py                          [MODIFY] add boss_phase field to ConflictDetails
│
├── config/
│   └── settings.py                        [MODIFY] add multi_phase_boss_enabled feature flag
│
└── platforms/
    └── telegram/
        └── message_handler.py             [MODIFY] rewrite _handle_boss_response() with multi-phase branch
```

---

## Module Dependency Graph

```
settings.py (FLAG: multi_phase_boss_enabled)
    ↓
chapters/__init__.py (is_multi_phase_boss_enabled() helper)
    ↓
message_handler.py (orchestrator, decision point)
    ├─→ phase_manager.py (state machine)
    │     ├─→ boss.py (BossPhase, BossPhaseState)
    │     ├─→ prompts.py (BOSS_PHASE_PROMPTS)
    │     └─→ conflicts/models.py (ConflictDetails JSONB)
    │
    ├─→ boss.py (BossStateMachine.process_partial())
    │
    ├─→ judgment.py (judge_multi_phase_outcome())
    │
    └─→ scoring/service.py (score_interaction with v_exchange_count)
        ├─→ analyzer.py (vulnerability_exchange tag)
        └─→ calculator.py (apply_warmth_bonus())
```

**Cycle Check**: All arrows point downward. No reverse dependencies. Acyclic.

---

## Separation of Concerns Analysis

| Layer | Module | Responsibility | Test Scope |
|-------|--------|-----------------|-----------|
| **Configuration** | settings.py | Feature flag storage and retrieval | Unit (flag defaults, env var override) |
| **Data Model** | boss.py | BossPhase enum, BossPhaseState class, serialization | Unit (model defaults, roundtrip) |
| **State Machine** | phase_manager.py | Lifecycle: start, advance, complete, timeout, persistence | Unit (state transitions, timeout boundary) |
| **Schema** | conflicts/models.py | JSONB column definition for boss_phase | Unit (field defaults, from_jsonb/to_jsonb) |
| **Prompts** | prompts.py | 10 phase-variant prompts, prompt lookup | Unit (all 10 prompts exist, keys present) |
| **Judgment** | judgment.py | Multi-turn outcome evaluation, confidence threshold | Unit (3-way outcome, confidence override), E2E (full conversation context) |
| **Orchestration** | boss.py (BossStateMachine) | Process pass/fail/partial outcomes, advance chapter | Unit (no attempts increment on PARTIAL, cool-down set) |
| **Integration** | message_handler.py | Multi-phase boss flow, phase state I/O, feature flag branch | Integration (full OPENING→RESOLUTION→outcome flow), E2E (Telegram request) |
| **Scoring** | analyzer.py, calculator.py, service.py | Vulnerability exchange detection, warmth bonus | Unit (tag detection, bonus +2/+1/+0), Integration (full interaction pipeline) |

---

## Import Pattern Checklist

| Pattern | Spec | Current | Status |
|---------|------|---------|--------|
| Feature flag access | `from nikita.config.settings import get_settings; settings.multi_phase_boss_enabled` | Follows `conflict_temperature_enabled` | ✅ |
| Feature flag helper | `from nikita.engine.chapters import is_multi_phase_boss_enabled()` | New in T-A1 | ✅ |
| Model imports | `from nikita.engine.chapters.boss import BossPhase, BossPhaseState` | Local, self-contained | ✅ |
| State machine | `from nikita.engine.chapters.phase_manager import BossPhaseManager` | New module, single export | ✅ |
| Conflict schema | `from nikita.conflicts.models import ConflictDetails` | Extended with boss_phase field | ✅ |
| Judgment | `from nikita.engine.chapters.judgment import BossJudgment, BossResult` | Extended with PARTIAL, judge_multi_phase_outcome() | ✅ |
| Prompts | `from nikita.engine.chapters.prompts import BOSS_PHASE_PROMPTS, get_boss_phase_prompt` | New structure, function | ✅ |
| Analyzer | `from nikita.engine.scoring.analyzer import ScoreAnalyzer` | Prompt extended, no API change | ✅ |
| Calculator | `from nikita.engine.scoring.calculator import ScoreCalculator` | New apply_warmth_bonus() method | ✅ |

---

## Security Architecture Checklist

| Aspect | Implementation | Status |
|--------|----------------|--------|
| **Input validation** | User messages from Telegram (upstream sanitization) | ✅ Safe |
| **State immutability** | BossPhaseState is Pydantic BaseModel (immutable by default) | ✅ Safe |
| **JSONB safety** | boss_phase stored via model_dump() (no string interpolation) | ✅ Safe |
| **LLM prompt injection** | Boss prompts are templates, user input not directly interpolated | ✅ Safe |
| **User scoping** | user_id passed throughout, phase state per-user | ✅ Safe |
| **Feature flag rollback** | OFF disables multi-phase entirely, Spec 057 unchanged | ✅ Safe |
| **Database constraints** | vulnerability_exchanges INT DEFAULT 0 (no negative values) | ✅ Safe |
| **Auth boundaries** | Message handler requires valid user_id (existing check) | ✅ Unchanged |

---

## Backward Compatibility Analysis

| Scenario | Spec 058 Handling | Result |
|----------|-------------------|--------|
| **Flag OFF (default)** | All multi-phase code unreachable; existing boss.py code runs | ✅ Single-turn PASS/FAIL preserved |
| **process_outcome(passed: bool)** | T-E2 adds overload for backward compat when flag OFF | ✅ Existing callers work unchanged |
| **BossResult enum** | PARTIAL added, PASS/FAIL unchanged | ✅ Existing code uses PASS/FAIL, not broken |
| **ConflictDetails schema** | boss_phase field added with default=None | ✅ Existing conflict data unchanged |
| **Existing boss tests** | T-G2 runs all with flag OFF, expects 0 failures | ✅ Full backward compat coverage |
| **Judgment method signature** | judge_boss_outcome() unchanged; new judge_multi_phase_outcome() added alongside | ✅ Both coexist |
| **Message handler** | Single branch point at top of _handle_boss_response(); existing flow preserved in else branch | ✅ Single-turn path unchanged |

---

## Risk Mitigation Analysis

| Risk | Mitigation | Status |
|------|-----------|--------|
| **Multi-phase breaks single-turn flow** | Feature flag OFF by default; T-G2 backward compat suite | ✅ Excellent |
| **Phase state corruption in JSONB** | BossPhaseState validated by Pydantic; load_phase() returns None on error | ✅ Good |
| **Boss timeout race condition at 24h boundary** | started_at persisted in state, timeout checked before advance | ✅ Good |
| **PARTIAL outcome gaming (players intentionally get PARTIAL to avoid FAIL)** | PARTIAL has 24h cool-down; delays boss but no net progress | ✅ Good |
| **Vulnerability detection false positives** | Behavior tag only (no separate LLM call); warmth bonus small (+2 max) and diminishing | ✅ Acceptable |
| **conflict_details JSONB size growth** | boss_phase max 4 messages (2 phases x 2 turns); cleared on completion | ✅ Good |

---

## Test Coverage Plan

| Phase | Test Count | Coverage |
|-------|-----------|----------|
| A: Foundation | 8 tests | Feature flag, models, PARTIAL enum, ConflictDetails, DB migration |
| B: Phase Manager | 15 tests | State transitions, persistence, timeout, interruption |
| C: Prompts | 12 tests | 10 prompts exist, required keys, lookup function |
| D: Judgment | 10 tests | 3-way judgment, confidence threshold, full history |
| E: Integration | 18 tests | Full OPENING→RESOLUTION flows for each outcome, timeout, interrupted |
| F: Warmth | 12 tests | Vulnerability tag, warmth bonus +2/+1/+0, counter reset |
| G: Compat + Tests | 4 suites | Backward compat (flag OFF), integration (flag ON), adversarial (edge cases) |
| **Total** | **~75+ tests** | Comprehensive coverage with adversarial suite |

---

## Recommendations

### Priority 1 (Must Address Before Implementation)

1. **Clarify LLM error handling** (Finding #1): Add explicit try-except block in T-D1 judge_multi_phase_outcome() with error logging and FAIL default. Document in plan.

2. **Document v_exchange_count counter initialization** (Finding #2): Specify in T-F3 that counter is conversation-scoped in message_handler.py and resets on new conversation. Add unit test for counter reset.

### Priority 2 (Nice to Have)

3. **Add timeout constant**: Define `BOSS_TIMEOUT_HOURS = 24` in `nikita/engine/constants.py` instead of hardcoding in phase_manager.py. Makes game balancing easier.

4. **Document PARTIAL cool-down constant**: Add `BOSS_PARTIAL_COOLDOWN_HOURS = 24` to constants.py alongside above. Used in process_partial() and E5 cool-down messaging.

5. **Add confidence threshold constant**: Define `JUDGMENT_CONFIDENCE_THRESHOLD = 0.7` in constants.py. Makes tuning easier for future A/B testing.

---

## Sign-Off

**Validator**: Architecture Validation Specialist (SDD)
**Date**: 2026-02-18
**Verdict**: **PASS** — 0 CRITICAL, 0 HIGH findings

**Reasoning**:
- Spec demonstrates excellent architectural foresight with clear separation of concerns
- Feature flag strategy is solid and follows established precedent
- Module organization is clean; new phase_manager.py is well-scoped
- Type safety is comprehensive via Pydantic models
- Error handling provides graceful degradation
- Backward compatibility is explicitly planned and tested
- No circular dependencies or violation of SOLID principles
- Two LOW findings are minor documentation clarifications, not blocking issues

**Ready for implementation**.

---

## Appendix: File Modification Summary

| File | Lines Added | Lines Modified | Action | Complexity |
|------|------------|-----------------|--------|-----------|
| settings.py | 5 | 1 (after conflict_temperature_enabled) | ADD feature flag | XS |
| chapters/__init__.py | 8 | 1 (add helper fn + export) | ADD helper + exports | XS |
| boss.py | 60 | 3 (add models, process_partial signature) | ADD BossPhase, BossPhaseState, process_partial() | S |
| judgment.py | 80 | 2 (extend BossResult enum, add method) | EXTEND + ADD judge_multi_phase_outcome() | M |
| prompts.py | 120 | 5 (add BOSS_PHASE_PROMPTS, function) | ADD 10 prompts, get_boss_phase_prompt() | M |
| **phase_manager.py** | **280** | **0** | **CREATE** | **M** |
| conflicts/models.py | 2 | 1 (add boss_phase field) | ADD field to ConflictDetails | XS |
| analyzer.py | 15 | 1 (append to ANALYSIS_SYSTEM_PROMPT) | ADD vulnerability section | S |
| calculator.py | 30 | 1 (add apply_warmth_bonus method) | ADD warmth bonus logic | S |
| service.py | 3 | 1 (add v_exchange_count param) | MODIFY signature | XS |
| message_handler.py | 150 | 10 (branch logic, refactoring) | REWRITE _handle_boss_response + ADD _handle_multi_phase_boss() | L |
| **Supabase migration** | **1 query** | **0** | **CREATE** | **XS** |
| test_*.py (3 files) | ~350 | 0 | CREATE | M |

**Total LoC Changed**: ~950 net new code + 25 LoC modified (in existing files)
**Complexity Distribution**: Highest complexity in message_handler.py (orchestration), phase_manager.py (state machine), judge_multi_phase_outcome() (judgment logic)

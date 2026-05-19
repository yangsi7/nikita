# Audit Report — Spec 116 Extraction Checkpoint (MP-004)

**Status: PASS**
**Date: 2026-03-14**
**Validators: 6/6 run**

---

## Validator Results

| Validator | Status | Findings |
|-----------|--------|----------|
| Frontend | PASS | No frontend scope — backend pipeline reorder only |
| Architecture | PASS (after fix) | HIGH: stage count "11" in spec → fixed to "10 on master"; MEDIUM×2 out of scope; LOW: CLAUDE.md pos 3 → fixed to pos 2 |
| Data Layer | PASS | No schema changes; confirmed PersistenceStage and MemoryUpdateStage write to independent DB tables |
| Auth | PASS | No auth surface affected |
| Testing | PASS (after fix) | CRITICAL: test_all_11_stages_present → replaced with set-based check; HIGH: regression verification → added to tasks; MEDIUM: dual-failure test added |
| API | PASS (after fix) | HIGH: same stage count issue → fixed in spec; commit-on-failure confirmed at tasks.py line 770 |

---

## Key Architectural Finding (CONFIRMED SAFE)

Architecture validator confirmed:
- Each stage runs in a SQLAlchemy `begin_nested()` SAVEPOINT
- On success, SAVEPOINT is RELEASED (writes staged in outer transaction)
- `tasks.py:770` calls `conv_session.commit()` unconditionally (success or failure)
- Therefore: PersistenceStage writes survive a subsequent MemoryUpdateStage failure

---

## Changes Made During Validation

| Fix | Location |
|-----|----------|
| spec.md FR-004: "11" → "10 on master" | `specs/116-extraction-checkpoint/spec.md` |
| pipeline/CLAUDE.md: "pos 3" → "pos 2" | `nikita/pipeline/CLAUDE.md` |
| test: `== 11` → set-based stage presence check | `tests/pipeline/test_extraction_checkpoint.py` |
| test: added dual-failure integration test | `tests/pipeline/test_extraction_checkpoint.py` |

---

## Test Results

- New tests: 9/9 PASS
- Pipeline suite: 273/273 PASS (0 regressions)

---

## Implementation Summary

**Files modified:**
- `nikita/pipeline/orchestrator.py`: swapped `persistence` (index 2→1) and `memory_update` (index 1→2) in `STAGE_DEFINITIONS`
- `nikita/pipeline/stages/persistence.py`: docstring updated to "Runs after extraction, before memory_update"
- `nikita/pipeline/CLAUDE.md`: pos 3 → pos 2

**Files created:**
- `tests/pipeline/test_extraction_checkpoint.py`: 9 tests (7 ordering + 2 integration)

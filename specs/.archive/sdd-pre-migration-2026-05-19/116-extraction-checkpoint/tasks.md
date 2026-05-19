# Tasks — Spec 116 Extraction Checkpoint (MP-004)

## Story 1: Stage Order Tests (RED)

- [ ] Create `tests/pipeline/test_extraction_checkpoint.py`
- [ ] Write `TestExtractionCheckpointStageOrder` (7 assertions, all RED)
- [ ] Write `TestPersistenceSurvivesMemoryUpdateFailure` (1 integration test, RED)
- [ ] Verify RED: `pytest tests/pipeline/test_extraction_checkpoint.py -v` → FAIL

## Story 2: Implementation (GREEN)

- [ ] Swap `persistence` and `memory_update` in `STAGE_DEFINITIONS` (orchestrator.py lines 46-48)
- [ ] Update `PersistenceStage` docstring (persistence.py line 4)
- [ ] Verify GREEN: `pytest tests/pipeline/test_extraction_checkpoint.py -v` → PASS
- [ ] Verify no regressions: `pytest tests/pipeline/ -v --tb=short` → all pass

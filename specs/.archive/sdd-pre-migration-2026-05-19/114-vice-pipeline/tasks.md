# Tasks — Spec 114: Vice Pipeline Activation

## Story 1: ViceStage + feature flag

- [ ] T1: Write failing tests
  - `tests/pipeline/stages/test_vice_stage.py` — AC-001 through AC-005
  - `tests/config/test_vice_setting.py` — AC-006
- [ ] T2: Implement
  - `nikita/config/settings.py` — add `vice_pipeline_enabled: bool = False`
  - `nikita/pipeline/stages/vice.py` — `ViceStage` class + `_extract_last_exchange()` helper
  - `nikita/pipeline/orchestrator.py` — insert `("vice", "...ViceStage", False)` after `emotional`
- [ ] T3: Run Story 1 tests — all pass

## Commit Sequence

1. `test(pipeline): Spec 114 — ViceStage + flag tests (RED)`
2. `feat(pipeline): Spec 114 — ViceStage + vice_pipeline_enabled flag (GREEN)`

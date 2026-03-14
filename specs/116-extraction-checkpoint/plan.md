# Plan — Spec 116 Extraction Checkpoint (MP-004)

## Approach

Minimal stage reorder: swap `persistence` and `memory_update` in `STAGE_DEFINITIONS`.
No new code paths, no schema changes. 2 files modified.

TDD: write failing tests first (RED), then implement (GREEN).

---

## T1 — Tests (RED phase)

### T1.1 — Stage order assertions

**File**: `tests/pipeline/test_extraction_checkpoint.py` (NEW)

```python
class TestExtractionCheckpointStageOrder:
    """AC-001/AC-002: persistence precedes memory_update in STAGE_DEFINITIONS."""

    def test_persistence_before_memory_update(self):
        """AC-001/AC-002: persistence at index 1, memory_update at index 2."""
        names = [name for name, _, _ in PipelineOrchestrator.STAGE_DEFINITIONS]
        persistence_idx = names.index("persistence")
        memory_update_idx = names.index("memory_update")
        assert persistence_idx < memory_update_idx, (
            f"persistence (idx {persistence_idx}) must precede "
            f"memory_update (idx {memory_update_idx})"
        )

    def test_persistence_at_index_1(self):
        """AC-001: persistence is immediately after extraction."""
        assert PipelineOrchestrator.STAGE_DEFINITIONS[1][0] == "persistence"

    def test_memory_update_at_index_2(self):
        """AC-002: memory_update follows persistence."""
        assert PipelineOrchestrator.STAGE_DEFINITIONS[2][0] == "memory_update"

    def test_extraction_still_at_index_0(self):
        """extraction must remain the first stage (CRITICAL)."""
        assert PipelineOrchestrator.STAGE_DEFINITIONS[0][0] == "extraction"

    def test_all_11_stages_present(self):
        """AC-004: all 11 stages remain in STAGE_DEFINITIONS."""
        assert len(PipelineOrchestrator.STAGE_DEFINITIONS) == 11

    def test_persistence_is_non_critical(self):
        """Persistence must remain non-critical so memory_update can still run on persistence failure."""
        entry = next(e for e in PipelineOrchestrator.STAGE_DEFINITIONS if e[0] == "persistence")
        assert entry[2] is False, "persistence must be non-critical"

    def test_memory_update_is_critical(self):
        """memory_update must remain critical."""
        entry = next(e for e in PipelineOrchestrator.STAGE_DEFINITIONS if e[0] == "memory_update")
        assert entry[2] is True, "memory_update must be critical"
```

### T1.2 — Integration: persistence survives memory_update failure

**File**: `tests/pipeline/test_extraction_checkpoint.py` (same file, new class)

```python
class TestPersistenceSurvivesMemoryUpdateFailure:
    """Verify pipeline behavior when memory_update fails after persistence runs."""

    @pytest.mark.asyncio
    async def test_persistence_runs_before_critical_failure(self, mock_session):
        """When memory_update (critical) fails, persistence has already run."""
        persistence_called = []

        class FakePersistence(BaseStage):
            name = "persistence"
            is_critical = False
            timeout_seconds = 5.0
            async def _run(self, ctx):
                persistence_called.append(True)
                return {"thoughts_persisted": 1}

        class FakeMemoryFail(BaseStage):
            name = "memory_update"
            is_critical = True
            timeout_seconds = 5.0
            async def _run(self, ctx):
                raise Exception("OpenAI outage")

        stages = [
            ("extraction",    FakeOkStage(session=mock_session),    True),
            ("persistence",   FakePersistence(session=mock_session), False),
            ("memory_update", FakeMemoryFail(session=mock_session),  True),
        ]
        orchestrator = PipelineOrchestrator(session=mock_session, stages=stages)
        result = await orchestrator.process(uuid4(), uuid4(), "text")

        assert result.success is False
        assert result.error_stage == "memory_update"
        assert len(persistence_called) == 1, "persistence must have run before memory_update failed"
```

---

## T2 — Implementation (GREEN phase)

### T2.1 — Swap stages in orchestrator.py

**File**: `nikita/pipeline/orchestrator.py`

Change `STAGE_DEFINITIONS` list order. Swap items at index 1 and 2:

```python
# Before
("extraction",    "nikita.pipeline.stages.extraction.ExtractionStage", True),
("memory_update", "nikita.pipeline.stages.memory_update.MemoryUpdateStage", True),
("persistence",   "nikita.pipeline.stages.persistence.PersistenceStage", False),

# After
("extraction",    "nikita.pipeline.stages.extraction.ExtractionStage", True),
("persistence",   "nikita.pipeline.stages.persistence.PersistenceStage", False),
("memory_update", "nikita.pipeline.stages.memory_update.MemoryUpdateStage", True),
```

All other stages remain unchanged.

### T2.2 — Update PersistenceStage docstring

**File**: `nikita/pipeline/stages/persistence.py`

Line 4: change `"Runs after memory_update, before life_sim."` →
`"Runs after extraction, before memory_update."`

---

## Files Modified

| File | Change |
|------|--------|
| `nikita/pipeline/orchestrator.py` | Swap persistence↔memory_update in STAGE_DEFINITIONS (lines 46-55) |
| `nikita/pipeline/stages/persistence.py` | Update docstring line 4 |
| `tests/pipeline/test_extraction_checkpoint.py` | NEW — 8 tests (7 ordering + 1 integration) |

---

## Verification

```bash
pytest tests/pipeline/test_extraction_checkpoint.py -v
pytest tests/pipeline/ -v --tb=short
```

All pipeline tests must pass. Stage count remains 11.

# Plan — Spec 117 ConfigLoader Migration (GE-001/GE-007)

## Approach

Targeted refactor: migrate 4 production files from direct constant imports to `get_config()`.
Add one new ConfigLoader method. Clean `__init__.py` and `__all__`.

TDD: write failing tests → implement → all pass.

---

## T1 — Tests (RED phase)

**File**: `tests/config/test_configloader_metric_weights.py` (NEW)
**File**: `tests/engine/test_configloader_migration.py` (NEW)

### T1.1 — ConfigLoader.get_metric_weights()

```python
class TestGetMetricWeights:
    def test_returns_dict_of_decimal(self):
        """AC-001: get_metric_weights returns {str: Decimal}."""
        from nikita.config import get_config
        weights = get_config().get_metric_weights()
        assert isinstance(weights, dict)
        assert set(weights.keys()) == {"intimacy", "passion", "trust", "secureness"}
        from decimal import Decimal
        assert all(isinstance(v, Decimal) for v in weights.values())

    def test_weights_sum_to_one(self):
        """Metric weights sum to 1.0."""
        from nikita.config import get_config
        from decimal import Decimal
        weights = get_config().get_metric_weights()
        total = sum(weights.values())
        assert abs(total - Decimal("1.0")) < Decimal("0.01")

    def test_matches_scoring_yaml_values(self):
        """Values match scoring.yaml configuration."""
        from nikita.config import get_config
        from decimal import Decimal
        weights = get_config().get_metric_weights()
        assert weights["intimacy"] == Decimal("0.30")
        assert weights["passion"] == Decimal("0.25")
        assert weights["trust"] == Decimal("0.25")
        assert weights["secureness"] == Decimal("0.20")
```

### T1.2 — engine/__init__.py cleanup (AC-006)

```python
class TestEngineInitCleanup:
    def test_engine_init_does_not_export_deprecated_constants(self):
        """AC-006: nikita.engine no longer exports deprecated constants."""
        import nikita.engine as engine
        for name in ["CHAPTER_NAMES", "CHAPTER_BEHAVIORS", "DECAY_RATES",
                     "GRACE_PERIODS", "BOSS_THRESHOLDS"]:
            assert not hasattr(engine, name), (
                f"nikita.engine.{name} should be removed (DC-008)"
            )
```

### T1.3 — constants.__all__ cleanup (AC-007)

```python
class TestConstantsAllCleanup:
    def test_deprecated_names_removed_from_all(self):
        """AC-007: BOSS_ENCOUNTERS, GAME_STATUSES, CHAPTER_DAY_RANGES not in __all__."""
        from nikita.engine import constants
        for name in ["BOSS_ENCOUNTERS", "GAME_STATUSES", "CHAPTER_DAY_RANGES"]:
            assert name not in constants.__all__, (
                f"{name} must be removed from __all__ (dead code DC-005/006/007)"
            )
```

### T1.4 — Module-level import cleanup assertions

```python
class TestProductionImportMigration:
    def test_scoring_calculator_no_module_level_constant_import(self):
        """AC-002: scoring/calculator.py no longer imports METRIC_WEIGHTS at module level."""
        import inspect
        import nikita.engine.scoring.calculator as mod
        src = inspect.getsource(mod)
        # Module-level import (top of file) should not reference METRIC_WEIGHTS
        # Check that METRIC_WEIGHTS doesn't appear in top-10 lines
        top_lines = '\n'.join(src.split('\n')[:20])
        assert "METRIC_WEIGHTS" not in top_lines

    def test_decay_calculator_no_module_level_constant_import(self):
        """AC-003: decay/calculator.py no longer imports DECAY_RATES at module level."""
        import inspect
        import nikita.engine.decay.calculator as mod
        src = inspect.getsource(mod)
        top_lines = '\n'.join(src.split('\n')[:20])
        assert "DECAY_RATES" not in top_lines
        assert "GRACE_PERIODS" not in top_lines
```

---

## T2 — Implementation (GREEN phase)

### T2.1 — Add get_metric_weights() to ConfigLoader

**File**: `nikita/config/loader.py`

Add after `get_daily_cap()` (around line 165):

```python
def get_metric_weights(self) -> dict[str, Decimal]:
    """Return metric weights as {name: Decimal} for RelationshipScoreCalculator.

    Reads from scoring.yaml metrics.weights.
    """
    w = self.scoring.metrics.weights
    return {
        "intimacy":   Decimal(str(w.intimacy)),
        "passion":    Decimal(str(w.passion)),
        "trust":      Decimal(str(w.trust)),
        "secureness": Decimal(str(w.secureness)),
    }
```

### T2.2 — scoring/calculator.py

Replace module-level imports, update `__init__` and `_detect_threshold_events`:

```python
# Remove: from nikita.engine.constants import BOSS_THRESHOLDS, METRIC_WEIGHTS
# Add:
from nikita.config import get_config

# __init__:
self.weights = get_config().get_metric_weights()

# _detect_threshold_events:
try:
    boss_threshold = get_config().get_boss_threshold(chapter)
except Exception:
    boss_threshold = Decimal("55")
```

### T2.3 — chapters/boss.py

Remove `BOSS_ENCOUNTERS` from import:
```python
# Before: from nikita.engine.constants import BOSS_ENCOUNTERS, BOSS_THRESHOLDS
# After:  from nikita.engine.constants import BOSS_THRESHOLDS
```

### T2.4 — decay/calculator.py

Replace module-level imports with lazy `get_config()` at usage:

```python
# Remove: from nikita.engine.constants import DECAY_RATES, GRACE_PERIODS
# Add at top:
from nikita.config import get_config

# Replace GRACE_PERIODS[user.chapter]:
grace_period = get_config().get_grace_period(user.chapter)

# Replace DECAY_RATES[user.chapter]:
decay_rate = get_config().get_decay_rate(user.chapter)
```

### T2.5 — pipeline/stages/game_state.py

Replace lazy constant imports:

```python
# In _check_boss_threshold():
# Before: from nikita.engine.constants import BOSS_THRESHOLDS
#         threshold = BOSS_THRESHOLDS.get(ctx.chapter, Decimal("75"))
# After:
from nikita.config import get_config
try:
    threshold = get_config().get_boss_threshold(ctx.chapter)
except Exception:
    threshold = Decimal("75")

# In _validate_chapter():
# Before: from nikita.engine.constants import CHAPTER_NAMES
#         if ctx.chapter not in CHAPTER_NAMES:
#             valid_chapters=list(CHAPTER_NAMES.keys()),
# After:
from nikita.config import get_config
cfg = get_config()
valid_chapters = list(cfg.chapters.keys())
if ctx.chapter not in valid_chapters:
    ...
    valid_chapters=valid_chapters,
```

### T2.6 — engine/__init__.py

Replace entire contents:
```python
"""Game engine module for Nikita."""
```

### T2.7 — engine/constants.py __all__

Remove `"BOSS_ENCOUNTERS"`, `"GAME_STATUSES"`, `"CHAPTER_DAY_RANGES"` from `__all__` list.

---

## Files Modified

| File | Change |
|------|--------|
| `nikita/config/loader.py` | Add `get_metric_weights()` |
| `nikita/engine/scoring/calculator.py` | Migrate METRIC_WEIGHTS + BOSS_THRESHOLDS |
| `nikita/engine/chapters/boss.py` | Remove BOSS_ENCOUNTERS from import |
| `nikita/engine/decay/calculator.py` | Migrate DECAY_RATES + GRACE_PERIODS |
| `nikita/pipeline/stages/game_state.py` | Migrate BOSS_THRESHOLDS + CHAPTER_NAMES |
| `nikita/engine/__init__.py` | Remove all re-exports |
| `nikita/engine/constants.py` | Remove 3 names from __all__ |
| `tests/config/test_configloader_metric_weights.py` | NEW: 3 tests for get_metric_weights |
| `tests/engine/test_configloader_migration.py` | NEW: 4 tests for cleanup assertions |

---

## Verification

```bash
pytest tests/config/test_configloader_metric_weights.py tests/engine/test_configloader_migration.py -v
pytest tests/engine/ tests/pipeline/ -q --tb=short   # regression
pytest tests/ -x -q --ignore=tests/e2e --ignore=tests/integration --ignore=tests/db  # full suite
```

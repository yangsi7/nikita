# Spec 117 — ConfigLoader Migration + Engine Constants Cleanup (GE-001/GE-007)

## Problem

`nikita.engine.constants` has a `DEPRECATED` section (line 98+) declaring 6 constants that
should be read from `ConfigLoader` (the YAML-backed configuration system). However:

1. **Zero ConfigLoader callers in production**: `get_config()` from `nikita.config` has no
   callers in the engine or pipeline packages. All production code imports DEPRECATED constants
   directly, silently bypassing the intended config system.

2. **Dead `__init__.py` re-exports**: `nikita/engine/__init__.py` re-exports
   `CHAPTER_NAMES`, `CHAPTER_BEHAVIORS`, `DECAY_RATES`, `GRACE_PERIODS`, `BOSS_THRESHOLDS`
   from `constants.py`. Nobody imports from `nikita.engine` directly (grep confirms zero callers),
   making these re-exports dead code (DC-008).

3. **Dead constants in `__all__`**: `BOSS_ENCOUNTERS`, `GAME_STATUSES`, and `CHAPTER_DAY_RANGES`
   appear in `engine/constants.py:__all__` but are deprecated (DC-005, DC-006, DC-007).
   `BOSS_ENCOUNTERS` is imported but unused in `chapters/boss.py`.

4. **Missing ConfigLoader method**: `get_metric_weights()` does not exist on `ConfigLoader`.
   `METRIC_WEIGHTS` (used in `scoring/calculator.py`) has no ConfigLoader equivalent.

---

## Approach

1. Add `get_metric_weights() -> dict[str, Decimal]` to `ConfigLoader` (new method).
2. Migrate 4 production call sites from direct constant imports to `get_config()`.
3. Clean `engine/__init__.py`: remove deprecated re-exports (DC-008).
4. Clean `engine/constants.py:__all__`: remove `BOSS_ENCOUNTERS`, `GAME_STATUSES`,
   `CHAPTER_DAY_RANGES` (DC-005, DC-006, DC-007). Constants themselves stay (backward compat).
5. Remove unused `BOSS_ENCOUNTERS` import from `chapters/boss.py` (DC-005).

---

## Functional Requirements

### FR-001 — ConfigLoader.get_metric_weights()

Add method to `nikita/config/loader.py`:

```python
def get_metric_weights(self) -> dict[str, Decimal]:
    """Return metric weights as {name: Decimal} dict.

    Maps scoring.yaml metrics.weights to the format expected by RelationshipScoreCalculator.
    """
    w = self.scoring.metrics.weights
    return {
        "intimacy":   Decimal(str(w.intimacy)),
        "passion":    Decimal(str(w.passion)),
        "trust":      Decimal(str(w.trust)),
        "secureness": Decimal(str(w.secureness)),
    }
```

### FR-002 — scoring/calculator.py migration

Replace module-level imports with `get_config()` calls:

**Before:**
```python
from nikita.engine.constants import BOSS_THRESHOLDS, METRIC_WEIGHTS
...
self.weights = dict(METRIC_WEIGHTS)  # line 68
...
boss_threshold = BOSS_THRESHOLDS.get(chapter, Decimal("55"))  # line 239
```

**After:**
```python
from nikita.config import get_config
...
self.weights = get_config().get_metric_weights()
...
boss_threshold = get_config().get_boss_threshold(chapter)
```

Note: `get_boss_threshold()` raises `ConfigurationError` if chapter unknown. Add fallback:
```python
try:
    boss_threshold = get_config().get_boss_threshold(chapter)
except Exception:
    boss_threshold = Decimal("55")
```

### FR-003 — chapters/boss.py cleanup

Remove unused `BOSS_ENCOUNTERS` from import (line 22). `BOSS_THRESHOLDS` stays (used elsewhere in file).

**Before:**
```python
from nikita.engine.constants import BOSS_ENCOUNTERS, BOSS_THRESHOLDS
```

**After:**
```python
from nikita.engine.constants import BOSS_THRESHOLDS
```

Note: `BOSS_THRESHOLDS` is still used in `boss.py`. This spec migrates only the dead import.
Full boss.py ConfigLoader migration is deferred (out of scope — boss.py has complex chapter-
specific logic; BOSS_THRESHOLDS is non-deprecated).

### FR-004 — decay/calculator.py migration

Replace module-level constant imports with `get_config()` calls at usage sites:

**Before:**
```python
from nikita.engine.constants import DECAY_RATES, GRACE_PERIODS
...
grace_period = GRACE_PERIODS[user.chapter]  # line 66, 87
decay_rate = DECAY_RATES[user.chapter]      # line 88
```

**After:**
```python
from nikita.config import get_config
...
grace_period = get_config().get_grace_period(user.chapter)
decay_rate = get_config().get_decay_rate(user.chapter)
```

### FR-005 — pipeline/stages/game_state.py migration

Replace lazy constant imports with `get_config()` calls:

**Before (line 56):**
```python
from nikita.engine.constants import BOSS_THRESHOLDS
threshold = BOSS_THRESHOLDS.get(ctx.chapter, Decimal("75"))
```

**After:**
```python
from nikita.config import get_config
try:
    threshold = get_config().get_boss_threshold(ctx.chapter)
except Exception:
    threshold = Decimal("75")
```

**Before (line 84):**
```python
from nikita.engine.constants import CHAPTER_NAMES
if ctx.chapter not in CHAPTER_NAMES:
    ...
    valid_chapters=list(CHAPTER_NAMES.keys()),
```

**After:**
```python
from nikita.config import get_config
cfg = get_config()
valid_chapters = list(cfg.chapters.keys())
if ctx.chapter not in valid_chapters:
    ...
    valid_chapters=valid_chapters,
```

### FR-006 — engine/__init__.py cleanup (DC-008)

Remove all re-exports. The file becomes a minimal docstring only:

```python
"""Game engine module for Nikita."""
```

### FR-007 — engine/constants.py __all__ cleanup (DC-005, DC-006, DC-007)

Remove `BOSS_ENCOUNTERS`, `GAME_STATUSES`, and `CHAPTER_DAY_RANGES` from `__all__`.
The constant definitions themselves remain (backward compatibility for any external callers).

---

## Acceptance Criteria

| ID | Criterion |
|----|-----------|
| AC-001 | `ConfigLoader.get_metric_weights()` returns `{"intimacy": Decimal("0.30"), ...}` |
| AC-002 | `scoring/calculator.py` no longer imports `METRIC_WEIGHTS` or `BOSS_THRESHOLDS` at module level |
| AC-003 | `decay/calculator.py` no longer imports `DECAY_RATES` or `GRACE_PERIODS` at module level |
| AC-004 | `game_state.py` no longer imports from `engine.constants` |
| AC-005 | `chapters/boss.py` no longer imports `BOSS_ENCOUNTERS` |
| AC-006 | `engine/__init__.py` contains only the module docstring (no imports) |
| AC-007 | `BOSS_ENCOUNTERS`, `GAME_STATUSES`, `CHAPTER_DAY_RANGES` absent from `constants.__all__` |
| AC-008 | All existing tests pass (`pytest tests/ -x -q`) |

---

## Files to Modify

| File | Change |
|------|--------|
| `nikita/config/loader.py` | Add `get_metric_weights()` method |
| `nikita/engine/scoring/calculator.py` | Migrate `METRIC_WEIGHTS`, `BOSS_THRESHOLDS` → ConfigLoader |
| `nikita/engine/chapters/boss.py` | Remove `BOSS_ENCOUNTERS` from import |
| `nikita/engine/decay/calculator.py` | Migrate `DECAY_RATES`, `GRACE_PERIODS` → ConfigLoader |
| `nikita/pipeline/stages/game_state.py` | Migrate `BOSS_THRESHOLDS`, `CHAPTER_NAMES` → ConfigLoader |
| `nikita/engine/__init__.py` | Remove all re-exports (DC-008) |
| `nikita/engine/constants.py` | Remove 3 names from `__all__` (DC-005/006/007) |

---

## Data Design

No schema changes. No DB migrations. No new API endpoints.

`get_metric_weights()` reads from already-loaded `ConfigLoader.scoring.metrics.weights`
(populated at startup from `scoring.yaml`). No new YAML files needed.

---

## Error Handling

`ConfigLoader.get_boss_threshold(n)` raises `ConfigurationError` for unknown chapters.
Call sites in `scoring/calculator.py` and `game_state.py` add `try/except` fallback to
their existing default values (`Decimal("55")` and `Decimal("75")` respectively) —
matching the `.get(chapter, default)` pattern they currently use.

`ConfigLoader.get_decay_rate(n)` and `get_grace_period(n)` raise `ConfigurationError`
for unknown chapters. These replace direct dict lookups which would `KeyError`. The
`DecayCalculator` already guards against invalid chapters; the new `ConfigurationError`
is semantically equivalent.

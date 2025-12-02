# 013 - Configuration System Tasks

**Generated**: 2025-12-02
**Plan Version**: 1.0
**Total Tasks**: 23

---

## User Story Organization

| User Story | Priority | Tasks | Status |
|------------|----------|-------|--------|
| US-1: Base Configuration Loading | P1 | T1.1-T1.3 | Pending |
| US-2: Pydantic Schema Validation | P1 | T2.1-T2.6 | Pending |
| US-3: ConfigLoader Singleton | P1 | T3.1-T3.4 | Pending |
| US-4: Prompt File System | P2 | T4.1-T4.5 | Pending |
| US-5: Experiment Overlays | P2 | T5.1-T5.4 | Pending |
| US-6: Migration from constants.py | P1 | T6.1-T6.4 | Pending |

---

## US-1: Base Configuration Loading (P1)

### T1.1: Create Directory Structure
- **Status**: [ ] Pending
- **Estimate**: 15 min
- **Dependencies**: None

**Acceptance Criteria**:
- [ ] AC-1.1.1: `nikita/config_data/` directory exists
- [ ] AC-1.1.2: `nikita/config_data/experiments/` subdirectory exists
- [ ] AC-1.1.3: `nikita/prompts/` directory with `persona/`, `chapters/`, `bosses/` subdirs
- [ ] AC-1.1.4: `nikita/config/__init__.py` exports `get_config`, `ConfigLoader`

### T1.2: Create game.yaml
- **Status**: [ ] Pending
- **Estimate**: 20 min
- **Dependencies**: T1.1

**Acceptance Criteria**:
- [ ] AC-1.2.1: Contains `starting_score: 50.0`
- [ ] AC-1.2.2: Contains `max_boss_attempts: 3`
- [ ] AC-1.2.3: Contains `game_duration_days: 21` (compressed game)
- [ ] AC-1.2.4: Contains `score_range: {min: 0, max: 100}`
- [ ] AC-1.2.5: YAML validates with `pyyaml`

### T1.3: Create chapters.yaml
- **Status**: [ ] Pending
- **Estimate**: 30 min
- **Dependencies**: T1.1

**Acceptance Criteria**:
- [ ] AC-1.3.1: Contains 5 chapter definitions (1-5)
- [ ] AC-1.3.2: Each chapter has `name`, `day_range`, `boss_threshold`
- [ ] AC-1.3.3: Boss thresholds match spec: 55/60/65/70/75%
- [ ] AC-1.3.4: Day ranges defined (1-3, 4-7, 8-11, 12-16, 17-21)
- [ ] AC-1.3.5: YAML validates with `pyyaml`

---

## US-2: Pydantic Schema Validation (P1)

### T2.1: Create GameConfig Schema
- **Status**: [ ] Pending
- **Estimate**: 20 min
- **Dependencies**: T1.2

**Acceptance Criteria**:
- [ ] AC-2.1.1: `GameConfig` Pydantic model validates game.yaml
- [ ] AC-2.1.2: `starting_score` validated as float 0-100
- [ ] AC-2.1.3: `max_boss_attempts` validated as int > 0
- [ ] AC-2.1.4: Invalid values raise `ValidationError`

### T2.2: Create ChaptersConfig Schema
- **Status**: [ ] Pending
- **Estimate**: 25 min
- **Dependencies**: T1.3

**Acceptance Criteria**:
- [ ] AC-2.2.1: `ChaptersConfig` validates chapters.yaml
- [ ] AC-2.2.2: Validates exactly 5 chapters exist
- [ ] AC-2.2.3: Validates boss thresholds are monotonically increasing
- [ ] AC-2.2.4: Validates day ranges don't overlap
- [ ] AC-2.2.5: Cross-field validation via `model_validator`

### T2.3: Create EngagementConfig Schema
- **Status**: [ ] Pending
- **Estimate**: 25 min
- **Dependencies**: T1.1

**Acceptance Criteria**:
- [ ] AC-2.3.1: `EngagementConfig` validates engagement.yaml
- [ ] AC-2.3.2: Validates 6 engagement states defined
- [ ] AC-2.3.3: Validates transition rules reference valid states
- [ ] AC-2.3.4: Validates calibration multipliers sum logic

### T2.4: Create ScoringConfig Schema
- **Status**: [ ] Pending
- **Estimate**: 20 min
- **Dependencies**: T1.1

**Acceptance Criteria**:
- [ ] AC-2.4.1: `ScoringConfig` validates scoring.yaml
- [ ] AC-2.4.2: Validates 4 metric weights (intimacy, passion, trust, secureness)
- [ ] AC-2.4.3: Validates weights sum to 1.0 (±0.001 tolerance)
- [ ] AC-2.4.4: Validates delta ranges are valid

### T2.5: Create DecayConfig Schema
- **Status**: [ ] Pending
- **Estimate**: 20 min
- **Dependencies**: T1.1

**Acceptance Criteria**:
- [ ] AC-2.5.1: `DecayConfig` validates decay.yaml
- [ ] AC-2.5.2: Validates 5 grace periods (8/16/24/48/72h)
- [ ] AC-2.5.3: Validates decay rates decrease per chapter (0.8→0.2)
- [ ] AC-2.5.4: Validates daily_cap exists per chapter

### T2.6: Create VicesConfig Schema
- **Status**: [ ] Pending
- **Estimate**: 20 min
- **Dependencies**: T1.1

**Acceptance Criteria**:
- [ ] AC-2.6.1: `VicesConfig` validates vices.yaml
- [ ] AC-2.6.2: Validates 8 vice categories defined
- [ ] AC-2.6.3: Validates intensity levels (low/medium/high)
- [ ] AC-2.6.4: Validates prompt_modifiers exist per category

---

## US-3: ConfigLoader Singleton (P1)

### T3.1: Implement ConfigLoader Class
- **Status**: [ ] Pending
- **Estimate**: 30 min
- **Dependencies**: T2.1-T2.6

**Acceptance Criteria**:
- [ ] AC-3.1.1: `ConfigLoader` class exists in `loader.py`
- [ ] AC-3.1.2: Implements singleton pattern (`__new__` or module-level)
- [ ] AC-3.1.3: `_load_yaml()` method loads YAML files
- [ ] AC-3.1.4: `_validate_configs()` method applies Pydantic schemas

### T3.2: Implement get_config() Function
- **Status**: [ ] Pending
- **Estimate**: 15 min
- **Dependencies**: T3.1

**Acceptance Criteria**:
- [ ] AC-3.2.1: `get_config()` returns cached `ConfigLoader` instance
- [ ] AC-3.2.2: Multiple calls return same instance
- [ ] AC-3.2.3: Thread-safe via `@lru_cache` or `threading.Lock`

### T3.3: Implement Convenience Accessors
- **Status**: [ ] Pending
- **Estimate**: 20 min
- **Dependencies**: T3.2

**Acceptance Criteria**:
- [ ] AC-3.3.1: `get_chapter(n)` returns chapter config
- [ ] AC-3.3.2: `get_decay_rate(chapter)` returns Decimal rate
- [ ] AC-3.3.3: `get_grace_period(chapter)` returns timedelta
- [ ] AC-3.3.4: `get_boss_threshold(chapter)` returns Decimal

### T3.4: Verify Load Performance
- **Status**: [ ] Pending
- **Estimate**: 15 min
- **Dependencies**: T3.2

**Acceptance Criteria**:
- [ ] AC-3.4.1: Config load time < 100ms measured
- [ ] AC-3.4.2: Subsequent calls < 1ms (cached)
- [ ] AC-3.4.3: Performance test exists in test suite

---

## US-4: Prompt File System (P2)

### T4.1: Implement PromptLoader Class
- **Status**: [ ] Pending
- **Estimate**: 25 min
- **Dependencies**: T1.1

**Acceptance Criteria**:
- [ ] AC-4.1.1: `PromptLoader` class exists in `prompt_loader.py`
- [ ] AC-4.1.2: `load(path)` method reads `.prompt` files
- [ ] AC-4.1.3: Returns string content

### T4.2: Implement Variable Substitution
- **Status**: [ ] Pending
- **Estimate**: 20 min
- **Dependencies**: T4.1

**Acceptance Criteria**:
- [ ] AC-4.2.1: `{{variable}}` syntax replaced with values
- [ ] AC-4.2.2: `render(path, **kwargs)` method accepts variables
- [ ] AC-4.2.3: Nested variables work `{{user.name}}`

### T4.3: Implement Missing Variable Error
- **Status**: [ ] Pending
- **Estimate**: 10 min
- **Dependencies**: T4.2

**Acceptance Criteria**:
- [ ] AC-4.3.1: `MissingVariableError` exception defined
- [ ] AC-4.3.2: Raised when template has unreplaced `{{var}}`
- [ ] AC-4.3.3: Error message includes missing variable name

### T4.4: Implement Prompt Caching
- **Status**: [ ] Pending
- **Estimate**: 15 min
- **Dependencies**: T4.1

**Acceptance Criteria**:
- [ ] AC-4.4.1: Prompts cached after first load
- [ ] AC-4.4.2: `@lru_cache` or dict-based cache
- [ ] AC-4.4.3: Subsequent loads < 1ms

### T4.5: Implement cache_clear()
- **Status**: [ ] Pending
- **Estimate**: 10 min
- **Dependencies**: T4.4

**Acceptance Criteria**:
- [ ] AC-4.5.1: `cache_clear()` method exists
- [ ] AC-4.5.2: Clears all cached prompts
- [ ] AC-4.5.3: Next load reads from disk

---

## US-5: Experiment Overlays (P2)

### T5.1: Implement NIKITA_EXPERIMENT Detection
- **Status**: [ ] Pending
- **Estimate**: 15 min
- **Dependencies**: T3.1

**Acceptance Criteria**:
- [ ] AC-5.1.1: Reads `NIKITA_EXPERIMENT` env var at startup
- [ ] AC-5.1.2: If set, loads `experiments/{name}.yaml`
- [ ] AC-5.1.3: If not set, uses base config only

### T5.2: Implement Deep Merge Logic
- **Status**: [ ] Pending
- **Estimate**: 20 min
- **Dependencies**: T5.1

**Acceptance Criteria**:
- [ ] AC-5.2.1: Experiment YAML overlays base config
- [ ] AC-5.2.2: Nested dicts merged recursively
- [ ] AC-5.2.3: Lists replaced (not appended)
- [ ] AC-5.2.4: Scalars overwritten

### T5.3: Implement Experiment Inheritance
- **Status**: [ ] Pending
- **Estimate**: 15 min
- **Dependencies**: T5.2

**Acceptance Criteria**:
- [ ] AC-5.3.1: `extends: "parent_experiment"` syntax works
- [ ] AC-5.3.2: Parent loaded first, then child overlay
- [ ] AC-5.3.3: Circular inheritance detected and raises error

### T5.4: Implement Invalid Experiment Error
- **Status**: [ ] Pending
- **Estimate**: 10 min
- **Dependencies**: T5.1

**Acceptance Criteria**:
- [ ] AC-5.4.1: `ConfigurationError` raised for unknown experiment
- [ ] AC-5.4.2: Error message lists available experiments
- [ ] AC-5.4.3: Fails fast at startup, not runtime

---

## US-6: Migration from constants.py (P1)

### T6.1: Create enums.py
- **Status**: [ ] Pending
- **Estimate**: 20 min
- **Dependencies**: None

**Acceptance Criteria**:
- [ ] AC-6.1.1: `nikita/config/enums.py` created
- [ ] AC-6.1.2: Contains `Chapter` enum (1-5)
- [ ] AC-6.1.3: Contains `GameStatus` enum
- [ ] AC-6.1.4: Contains `EngagementState` enum (6 states)
- [ ] AC-6.1.5: Contains `Mood`, `TimeOfDay`, `Availability` enums

### T6.2: Extract Numeric Values to YAML
- **Status**: [ ] Pending
- **Estimate**: 30 min
- **Dependencies**: T1.2, T1.3, T6.1

**Acceptance Criteria**:
- [ ] AC-6.2.1: All `Decimal` values moved to YAML
- [ ] AC-6.2.2: All `timedelta` values moved to YAML
- [ ] AC-6.2.3: `METRIC_WEIGHTS` in scoring.yaml
- [ ] AC-6.2.4: `BOSS_THRESHOLDS` in chapters.yaml
- [ ] AC-6.2.5: `GRACE_PERIODS`, `DECAY_RATES` in decay.yaml

### T6.3: Update constants.py
- **Status**: [ ] Pending
- **Estimate**: 20 min
- **Dependencies**: T6.2

**Acceptance Criteria**:
- [ ] AC-6.3.1: `constants.py` contains only enum re-exports
- [ ] AC-6.3.2: Deprecation warnings added for old imports
- [ ] AC-6.3.3: `CHAPTER_BEHAVIORS` moved to prompts/

### T6.4: Update Imports Across Codebase
- **Status**: [ ] Pending
- **Estimate**: 45 min
- **Dependencies**: T3.2, T6.3

**Acceptance Criteria**:
- [ ] AC-6.4.1: All `from nikita.engine.constants import` updated
- [ ] AC-6.4.2: Replace with `from nikita.config import get_config`
- [ ] AC-6.4.3: All accessor patterns updated (e.g., `get_config().get_chapter(1)`)
- [ ] AC-6.4.4: `rg "from nikita.engine.constants" nikita/` returns only enum imports

---

## Testing Tasks

### T7.1: Unit Tests for ConfigLoader
- **Status**: [ ] Pending
- **Estimate**: 30 min
- **Dependencies**: T3.2

**Acceptance Criteria**:
- [ ] AC-7.1.1: Test config loads correctly from YAML
- [ ] AC-7.1.2: Test validation catches invalid values
- [ ] AC-7.1.3: Test singleton pattern (same instance)
- [ ] AC-7.1.4: Test convenience accessors return correct values

### T7.2: Unit Tests for PromptLoader
- **Status**: [ ] Pending
- **Estimate**: 25 min
- **Dependencies**: T4.5

**Acceptance Criteria**:
- [ ] AC-7.2.1: Test prompt loads from file
- [ ] AC-7.2.2: Test `{{variable}}` substitution
- [ ] AC-7.2.3: Test `MissingVariableError` raised
- [ ] AC-7.2.4: Test caching (second load is fast)

### T7.3: Unit Tests for Experiments
- **Status**: [ ] Pending
- **Estimate**: 20 min
- **Dependencies**: T5.4

**Acceptance Criteria**:
- [ ] AC-7.3.1: Test experiment activation via env var
- [ ] AC-7.3.2: Test deep merge overlay
- [ ] AC-7.3.3: Test experiment inheritance
- [ ] AC-7.3.4: Test invalid experiment error

### T7.4: Integration Tests
- **Status**: [ ] Pending
- **Estimate**: 30 min
- **Dependencies**: T6.4

**Acceptance Criteria**:
- [ ] AC-7.4.1: Test full startup with all configs
- [ ] AC-7.4.2: Test migration preserved all values
- [ ] AC-7.4.3: Test performance < 100ms load time
- [ ] AC-7.4.4: Test no old constant imports remain

---

## Progress Summary

| Phase | Tasks | Completed | Status |
|-------|-------|-----------|--------|
| Phase 1: Foundation | T1.1-T1.3 | 0 | Pending |
| Phase 2: Schemas | T2.1-T2.6 | 0 | Pending |
| Phase 3: ConfigLoader | T3.1-T3.4 | 0 | Pending |
| Phase 4: PromptLoader | T4.1-T4.5 | 0 | Pending |
| Phase 5: Experiments | T5.1-T5.4 | 0 | Pending |
| Phase 6: Migration | T6.1-T6.4 | 0 | Pending |
| Phase 7: Testing | T7.1-T7.4 | 0 | Pending |
| **TOTAL** | **27** | **0** | **0%** |

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-02 | Claude | Initial task breakdown |

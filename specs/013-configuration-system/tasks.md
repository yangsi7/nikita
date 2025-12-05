# 013 - Configuration System Tasks

**Generated**: 2025-12-02
**Plan Version**: 1.0
**Total Tasks**: 23

---

## User Story Organization

| User Story | Priority | Tasks | Status |
|------------|----------|-------|--------|
| US-1: Base Configuration Loading | P1 | T1.1-T1.3 | ✅ Complete |
| US-2: Pydantic Schema Validation | P1 | T2.1-T2.6 | ✅ Complete |
| US-3: ConfigLoader Singleton | P1 | T3.1-T3.4 | ✅ Complete |
| US-4: Prompt File System | P2 | T4.1-T4.5 | ✅ Complete |
| US-5: Experiment Overlays | P2 | T5.1-T5.4 | ✅ Complete |
| US-6: Migration from constants.py | P1 | T6.1-T6.4 | ⚠️ Partial (T6.1 done) |

---

## US-1: Base Configuration Loading (P1)

### T1.1: Create Directory Structure
- **Status**: [x] Complete
- **Estimate**: 15 min
- **Dependencies**: None

**Acceptance Criteria**:
- [x] AC-1.1.1: `nikita/config_data/` directory exists
- [x] AC-1.1.2: `nikita/config_data/experiments/` subdirectory exists
- [x] AC-1.1.3: `nikita/prompts/` directory with `persona/`, `chapters/`, `bosses/` subdirs
- [x] AC-1.1.4: `nikita/config/__init__.py` exports `get_config`, `ConfigLoader`

### T1.2: Create game.yaml
- **Status**: [x] Complete
- **Estimate**: 20 min
- **Dependencies**: T1.1

**Acceptance Criteria**:
- [x] AC-1.2.1: Contains `starting_score: 50.0`
- [x] AC-1.2.2: Contains `max_boss_attempts: 3`
- [x] AC-1.2.3: Contains `game_duration_days: 21` (compressed game)
- [x] AC-1.2.4: Contains `score_range: {min: 0, max: 100}`
- [x] AC-1.2.5: YAML validates with `pyyaml`

### T1.3: Create chapters.yaml (+ scoring, decay, engagement, vices, schedule)
- **Status**: [x] Complete
- **Estimate**: 30 min
- **Dependencies**: T1.1

**Acceptance Criteria**:
- [x] AC-1.3.1: Contains 5 chapter definitions (1-5)
- [x] AC-1.3.2: Each chapter has `name`, `day_range`, `boss_threshold`
- [x] AC-1.3.3: Boss thresholds match spec: 55/60/65/70/75%
- [x] AC-1.3.4: Day ranges defined (1-3, 4-7, 8-11, 12-16, 17-21)
- [x] AC-1.3.5: YAML validates with `pyyaml`
- [x] AC-1.3.6: 7 YAML files created (game, chapters, scoring, decay, engagement, vices, schedule)

---

## US-2: Pydantic Schema Validation (P1)

### T2.1: Create GameConfig Schema
- **Status**: [x] Complete
- **Estimate**: 20 min
- **Dependencies**: T1.2

**Acceptance Criteria**:
- [x] AC-2.1.1: `GameConfig` Pydantic model validates game.yaml
- [x] AC-2.1.2: `starting_score` validated as float 0-100
- [x] AC-2.1.3: `max_boss_attempts` validated as int > 0
- [x] AC-2.1.4: Invalid values raise `ValidationError`

### T2.2: Create ChaptersConfig Schema
- **Status**: [x] Complete
- **Estimate**: 25 min
- **Dependencies**: T1.3

**Acceptance Criteria**:
- [x] AC-2.2.1: `ChaptersConfig` validates chapters.yaml
- [x] AC-2.2.2: Validates exactly 5 chapters exist
- [x] AC-2.2.3: Validates boss thresholds are monotonically increasing
- [x] AC-2.2.4: Validates day ranges don't overlap
- [x] AC-2.2.5: Cross-field validation via `model_validator`

### T2.3: Create EngagementConfig Schema
- **Status**: [x] Complete
- **Estimate**: 25 min
- **Dependencies**: T1.1

**Acceptance Criteria**:
- [x] AC-2.3.1: `EngagementConfig` validates engagement.yaml
- [x] AC-2.3.2: Validates 6 engagement states defined
- [x] AC-2.3.3: Validates transition rules reference valid states
- [x] AC-2.3.4: Validates calibration multipliers sum logic

### T2.4: Create ScoringConfig Schema
- **Status**: [x] Complete
- **Estimate**: 20 min
- **Dependencies**: T1.1

**Acceptance Criteria**:
- [x] AC-2.4.1: `ScoringConfig` validates scoring.yaml
- [x] AC-2.4.2: Validates 4 metric weights (intimacy, passion, trust, secureness)
- [x] AC-2.4.3: Validates weights sum to 1.0 (±0.001 tolerance)
- [x] AC-2.4.4: Validates delta ranges are valid

### T2.5: Create DecayConfig Schema
- **Status**: [x] Complete
- **Estimate**: 20 min
- **Dependencies**: T1.1

**Acceptance Criteria**:
- [x] AC-2.5.1: `DecayConfig` validates decay.yaml
- [x] AC-2.5.2: Validates 5 grace periods (8/16/24/48/72h)
- [x] AC-2.5.3: Validates decay rates decrease per chapter (0.8→0.2)
- [x] AC-2.5.4: Validates daily_cap exists per chapter

### T2.6: Create VicesConfig Schema
- **Status**: [x] Complete
- **Estimate**: 20 min
- **Dependencies**: T1.1

**Acceptance Criteria**:
- [x] AC-2.6.1: `VicesConfig` validates vices.yaml
- [x] AC-2.6.2: Validates 8 vice categories defined
- [x] AC-2.6.3: Validates intensity levels (low/medium/high)
- [x] AC-2.6.4: Validates prompt_modifiers exist per category

---

## US-3: ConfigLoader Singleton (P1)

### T3.1: Implement ConfigLoader Class
- **Status**: [x] Complete
- **Estimate**: 30 min
- **Dependencies**: T2.1-T2.6

**Acceptance Criteria**:
- [x] AC-3.1.1: `ConfigLoader` class exists in `loader.py`
- [x] AC-3.1.2: Implements singleton pattern (`__new__` or module-level)
- [x] AC-3.1.3: `_load_yaml()` method loads YAML files
- [x] AC-3.1.4: `_validate_configs()` method applies Pydantic schemas

### T3.2: Implement get_config() Function
- **Status**: [x] Complete
- **Estimate**: 15 min
- **Dependencies**: T3.1

**Acceptance Criteria**:
- [x] AC-3.2.1: `get_config()` returns cached `ConfigLoader` instance
- [x] AC-3.2.2: Multiple calls return same instance
- [x] AC-3.2.3: Thread-safe via `@lru_cache` or `threading.Lock`

### T3.3: Implement Convenience Accessors
- **Status**: [x] Complete
- **Estimate**: 20 min
- **Dependencies**: T3.2

**Acceptance Criteria**:
- [x] AC-3.3.1: `get_chapter(n)` returns chapter config
- [x] AC-3.3.2: `get_decay_rate(chapter)` returns Decimal rate
- [x] AC-3.3.3: `get_grace_period(chapter)` returns timedelta
- [x] AC-3.3.4: `get_boss_threshold(chapter)` returns Decimal

### T3.4: Verify Load Performance
- **Status**: [x] Complete
- **Estimate**: 15 min
- **Dependencies**: T3.2

**Acceptance Criteria**:
- [x] AC-3.4.1: Config load time < 100ms measured
- [x] AC-3.4.2: Subsequent calls < 1ms (cached)
- [x] AC-3.4.3: Performance test exists in test suite

---

## US-4: Prompt File System (P2)

### T4.1: Implement PromptLoader Class
- **Status**: [x] Complete
- **Estimate**: 25 min
- **Dependencies**: T1.1

**Acceptance Criteria**:
- [x] AC-4.1.1: `PromptLoader` class exists in `prompt_loader.py`
- [x] AC-4.1.2: `load(path)` method reads `.prompt` files
- [x] AC-4.1.3: Returns string content

### T4.2: Implement Variable Substitution
- **Status**: [x] Complete
- **Estimate**: 20 min
- **Dependencies**: T4.1

**Acceptance Criteria**:
- [x] AC-4.2.1: `{{variable}}` syntax replaced with values
- [x] AC-4.2.2: `render(path, **kwargs)` method accepts variables
- [x] AC-4.2.3: Nested variables work `{{user.name}}`

### T4.3: Implement Missing Variable Error
- **Status**: [x] Complete
- **Estimate**: 10 min
- **Dependencies**: T4.2

**Acceptance Criteria**:
- [x] AC-4.3.1: `MissingVariableError` exception defined
- [x] AC-4.3.2: Raised when template has unreplaced `{{var}}`
- [x] AC-4.3.3: Error message includes missing variable name

### T4.4: Implement Prompt Caching
- **Status**: [x] Complete
- **Estimate**: 15 min
- **Dependencies**: T4.1

**Acceptance Criteria**:
- [x] AC-4.4.1: Prompts cached after first load
- [x] AC-4.4.2: `@lru_cache` or dict-based cache
- [x] AC-4.4.3: Subsequent loads < 1ms

### T4.5: Implement cache_clear()
- **Status**: [x] Complete
- **Estimate**: 10 min
- **Dependencies**: T4.4

**Acceptance Criteria**:
- [x] AC-4.5.1: `cache_clear()` method exists
- [x] AC-4.5.2: Clears all cached prompts
- [x] AC-4.5.3: Next load reads from disk

---

## US-5: Experiment Overlays (P2)

### T5.1: Implement NIKITA_EXPERIMENT Detection
- **Status**: [x] Complete
- **Estimate**: 15 min
- **Dependencies**: T3.1

**Acceptance Criteria**:
- [x] AC-5.1.1: Reads `NIKITA_EXPERIMENT` env var at startup
- [x] AC-5.1.2: If set, loads `experiments/{name}.yaml`
- [x] AC-5.1.3: If not set, uses base config only

### T5.2: Implement Deep Merge Logic
- **Status**: [x] Complete
- **Estimate**: 20 min
- **Dependencies**: T5.1

**Acceptance Criteria**:
- [x] AC-5.2.1: Experiment YAML overlays base config
- [x] AC-5.2.2: Nested dicts merged recursively
- [x] AC-5.2.3: Lists replaced (not appended)
- [x] AC-5.2.4: Scalars overwritten

### T5.3: Implement Experiment Inheritance
- **Status**: [x] Complete
- **Estimate**: 15 min
- **Dependencies**: T5.2

**Acceptance Criteria**:
- [x] AC-5.3.1: `extends: "parent_experiment"` syntax works
- [x] AC-5.3.2: Parent loaded first, then child overlay
- [x] AC-5.3.3: Circular inheritance detected and raises error

### T5.4: Implement Invalid Experiment Error
- **Status**: [x] Complete
- **Estimate**: 10 min
- **Dependencies**: T5.1

**Acceptance Criteria**:
- [x] AC-5.4.1: `ConfigurationError` raised for unknown experiment
- [x] AC-5.4.2: Error message lists available experiments
- [x] AC-5.4.3: Fails fast at startup, not runtime

---

## US-6: Migration from constants.py (P1)

### T6.1: Create enums.py
- **Status**: [x] Complete
- **Estimate**: 20 min
- **Dependencies**: None

**Acceptance Criteria**:
- [x] AC-6.1.1: `nikita/config/enums.py` created
- [x] AC-6.1.2: Contains `Chapter` enum (1-5)
- [x] AC-6.1.3: Contains `GameStatus` enum
- [x] AC-6.1.4: Contains `EngagementState` enum (6 states)
- [x] AC-6.1.5: Contains `Mood`, `TimeOfDay`, `ViceCategory`, `ViceIntensity`, `Metric` enums (9 total)

### T6.2: Extract Numeric Values to YAML
- **Status**: [x] Complete
- **Estimate**: 30 min
- **Dependencies**: T1.2, T1.3, T6.1

**Acceptance Criteria**:
- [x] AC-6.2.1: All `Decimal` values moved to YAML
- [x] AC-6.2.2: All `timedelta` values moved to YAML (as hours in decay.yaml)
- [x] AC-6.2.3: `METRIC_WEIGHTS` in scoring.yaml
- [x] AC-6.2.4: `BOSS_THRESHOLDS` in chapters.yaml
- [x] AC-6.2.5: `GRACE_PERIODS`, `DECAY_RATES` in decay.yaml

### T6.3: Update constants.py
- **Status**: [x] Complete
- **Estimate**: 20 min
- **Dependencies**: T6.2

**Acceptance Criteria**:
- [x] AC-6.3.1: `constants.py` re-exports enums from nikita.config.enums
- [x] AC-6.3.2: Deprecation warnings added for old imports (in docstring + comments)
- [x] AC-6.3.3: `CHAPTER_BEHAVIORS` moved to prompts/chapters/*.prompt (lazy-loaded)

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
- **Status**: [x] Complete
- **Estimate**: 30 min
- **Dependencies**: T3.2

**Acceptance Criteria**:
- [x] AC-7.1.1: Test config loads correctly from YAML (test_loader.py)
- [x] AC-7.1.2: Test validation catches invalid values (test_schemas.py)
- [x] AC-7.1.3: Test singleton pattern (same instance)
- [x] AC-7.1.4: Test convenience accessors return correct values
- [x] AC-7.1.5: 52 tests total: 19 enum, 12 schema, 21 loader

### T7.2: Unit Tests for PromptLoader
- **Status**: [x] Complete
- **Estimate**: 25 min
- **Dependencies**: T4.5

**Acceptance Criteria**:
- [x] AC-7.2.1: Test prompt loads from file
- [x] AC-7.2.2: Test `{{variable}}` substitution
- [x] AC-7.2.3: Test `MissingVariableError` raised
- [x] AC-7.2.4: Test caching (second load is fast)

### T7.3: Unit Tests for Experiments
- **Status**: [x] Complete
- **Estimate**: 20 min
- **Dependencies**: T5.4

**Acceptance Criteria**:
- [x] AC-7.3.1: Test experiment activation via env var
- [x] AC-7.3.2: Test deep merge overlay
- [x] AC-7.3.3: Test experiment inheritance
- [x] AC-7.3.4: Test invalid experiment error

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
| Phase 1: Foundation | T1.1-T1.3 | 3/3 | ✅ Complete |
| Phase 2: Schemas | T2.1-T2.6 | 6/6 | ✅ Complete |
| Phase 3: ConfigLoader | T3.1-T3.4 | 4/4 | ✅ Complete |
| Phase 4: PromptLoader | T4.1-T4.5 | 5/5 | ✅ Complete |
| Phase 5: Experiments | T5.1-T5.4 | 4/4 | ✅ Complete |
| Phase 6: Migration | T6.1-T6.4 | 3/4 | ⚠️ T6.4 deferred (backward compat OK) |
| Phase 7: Testing | T7.1-T7.4 | 3/4 | ⚠️ T7.4 pending |
| **TOTAL** | **30** | **28** | **93%** |

**TDD Status**: 89 tests passing (test_enums.py: 19, test_schemas.py: 12, test_loader.py: 21, test_prompt_loader.py: 20, test_experiments.py: 17)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-02 | Claude | Initial task breakdown |
| 1.1 | 2025-12-04 | Claude | Updated to reflect TDD progress (56% complete, 52 tests) |
| 1.2 | 2025-12-04 | Claude | PromptLoader (US-4), Experiments (US-5), Migration (T6.2-T6.3) complete. 93%, 89 tests |

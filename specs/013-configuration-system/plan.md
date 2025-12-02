# 013 - Configuration System Implementation Plan

**Generated**: 2025-12-02
**Spec Version**: 1.0
**Estimated Effort**: 4-6 hours

---

## Executive Summary

Implement a hybrid layered configuration system that extracts all magic numbers from code into YAML files and all prompts into `.prompt` files. This is foundational for specs 012, 003-006.

---

## User Stories

### US-1: Base Configuration Loading (P1)

**As a** developer
**I want** all game parameters loaded from YAML files
**So that** I can change behavior without code changes

**Acceptance Criteria**:
- AC-1.1: game.yaml loads with all game-wide parameters
- AC-1.2: chapters.yaml loads with per-chapter configs
- AC-1.3: engagement.yaml loads with calibration parameters
- AC-1.4: scoring.yaml loads with weights and multipliers
- AC-1.5: decay.yaml loads with rates and grace periods
- AC-1.6: vices.yaml loads with category definitions

### US-2: Pydantic Schema Validation (P1)

**As a** developer
**I want** all configs validated at startup
**So that** invalid configs fail fast, not at runtime

**Acceptance Criteria**:
- AC-2.1: GameConfig validates game.yaml
- AC-2.2: ChaptersConfig validates chapters.yaml with constraint checks
- AC-2.3: EngagementConfig validates engagement.yaml
- AC-2.4: ScoringConfig validates scoring.yaml with weight sum check
- AC-2.5: DecayConfig validates decay.yaml with monotonicity check
- AC-2.6: VicesConfig validates vices.yaml

### US-3: ConfigLoader Singleton (P1)

**As a** developer
**I want** a singleton ConfigLoader
**So that** configs are loaded once and cached

**Acceptance Criteria**:
- AC-3.1: ConfigLoader implements singleton pattern
- AC-3.2: get_config() returns cached instance
- AC-3.3: Convenience accessors work (get_chapter, get_decay_rate, etc.)
- AC-3.4: Config load time < 100ms

### US-4: Prompt File System (P2)

**As a** developer
**I want** prompts stored in .prompt files
**So that** prompts can be edited without code changes

**Acceptance Criteria**:
- AC-4.1: PromptLoader loads .prompt files
- AC-4.2: Variable substitution works ({{variable}} syntax)
- AC-4.3: Missing variables raise MissingVariableError
- AC-4.4: Prompt files cached after first load
- AC-4.5: cache_clear() works for dev hot reload

### US-5: Experiment Overlays (P2)

**As a** game designer
**I want** experiment overlays
**So that** I can A/B test game variants

**Acceptance Criteria**:
- AC-5.1: NIKITA_EXPERIMENT env var activates experiment
- AC-5.2: Experiment YAML overrides base config
- AC-5.3: Experiment inheritance works (extends: "parent")
- AC-5.4: Invalid experiment name raises ConfigurationError

### US-6: Migration from constants.py (P1)

**As a** developer
**I want** to migrate from constants.py
**So that** no magic numbers remain in code

**Acceptance Criteria**:
- AC-6.1: All numeric values extracted to YAML
- AC-6.2: constants.py contains only enums
- AC-6.3: All imports updated to use get_config()
- AC-6.4: Tests verify migration preserved values

---

## Technical Architecture

### Directory Structure

```
nikita/
├── config/
│   ├── __init__.py          # Exports get_config, ConfigLoader
│   ├── loader.py            # ConfigLoader class
│   ├── prompt_loader.py     # PromptLoader class
│   ├── schemas.py           # Pydantic models
│   └── enums.py             # Enums only (from constants.py)
│
├── config_data/             # NEW - YAML configs
│   ├── game.yaml
│   ├── chapters.yaml
│   ├── engagement.yaml
│   ├── scoring.yaml
│   ├── decay.yaml
│   ├── schedule.yaml
│   ├── vices.yaml
│   └── experiments/
│       └── fast_game.yaml
│
└── prompts/                 # NEW - Prompt files
    ├── persona/
    │   ├── core_identity.prompt
    │   ├── voice_style.prompt
    │   └── boundaries.prompt
    ├── chapters/
    │   ├── chapter_1.prompt
    │   ├── chapter_2.prompt
    │   ├── chapter_3.prompt
    │   ├── chapter_4.prompt
    │   └── chapter_5.prompt
    └── bosses/
        └── boss_*.prompt
```

### Data Flow

```
Application Startup
       │
       ▼
┌─────────────────────────────────────────┐
│ 1. Load base YAML files                 │
│    config_data/*.yaml                   │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ 2. Check NIKITA_EXPERIMENT env var      │
│    If set, load experiments/*.yaml      │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ 3. Deep merge overlay onto base         │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ 4. Validate with Pydantic schemas       │
│    - Type validation                    │
│    - Constraint checks                  │
│    - Cross-field validation             │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ 5. Initialize PromptLoader              │
│    Load and cache prompts on-demand     │
└────────────────┬────────────────────────┘
                 │
                 ▼
         ConfigLoader singleton
              (cached)
```

---

## Implementation Tasks

### Phase 1: Foundation (2 hours)

#### T1.1: Create Directory Structure
- Create `config_data/` directory
- Create `config_data/experiments/` directory
- Create `prompts/` directory structure
- Create `nikita/config/` module files

#### T1.2: Implement Pydantic Schemas
- Create `schemas.py` with all config models
- GameConfig, ChaptersConfig, EngagementConfig
- ScoringConfig, DecayConfig, VicesConfig
- Add field validators for constraints

#### T1.3: Implement ConfigLoader
- Create `loader.py` with singleton pattern
- Implement `_load_yaml()` method
- Implement `_load_base_configs()` method
- Implement `_validate_configs()` cross-validation
- Add convenience accessors

### Phase 2: YAML Files (1.5 hours)

#### T2.1: Create game.yaml
- Extract values from constants.py
- Add all game-wide parameters
- Match spec Section 3.1

#### T2.2: Create chapters.yaml
- Extract CHAPTER_NAMES, BOSS_THRESHOLDS
- Extract DECAY_RATES, GRACE_PERIODS
- Add behavior configs per chapter
- Match spec Section 3.2 (55/60/65/70/75% thresholds)

#### T2.3: Create engagement.yaml
- Create state machine definition
- Add transition rules
- Add calibration scoring params
- Add recovery mechanics
- Match spec Section 3.3

#### T2.4: Create scoring.yaml
- Extract METRIC_WEIGHTS
- Add delta ranges
- Add calibration multipliers
- Add boss scoring
- Match spec Section 3.4

#### T2.5: Create decay.yaml
- Extract GRACE_PERIODS (8/16/24/48/72h)
- Extract DECAY_RATES (0.8/0.6/0.4/0.3/0.2)
- Add daily caps
- Add protection rules
- Match spec Section 3.5

#### T2.6: Create vices.yaml
- Define 8 vice categories
- Add intensity levels
- Add prompt modifiers
- Add defaults
- Match spec Section 3.7

### Phase 3: Prompt System (1 hour)

#### T3.1: Implement PromptLoader
- Create `prompt_loader.py`
- Implement variable substitution
- Implement caching
- Add error handling for missing variables

#### T3.2: Create Persona Prompts
- Create `prompts/persona/core_identity.prompt`
- Create `prompts/persona/voice_style.prompt`
- Create `prompts/persona/boundaries.prompt`

#### T3.3: Create Chapter Prompts
- Create `prompts/chapters/chapter_1.prompt` through `chapter_5.prompt`
- Include behavior hints and calibration guidance
- Include engagement style guidance

### Phase 4: Experiment System (30 min)

#### T4.1: Implement Experiment Overlays
- Add `_apply_experiment()` method to ConfigLoader
- Implement deep merge logic
- Implement experiment inheritance

#### T4.2: Create fast_game.yaml Experiment
- Create compressed 7-day game variant
- Override boss thresholds
- Override grace periods

### Phase 5: Migration (1 hour)

#### T5.1: Create enums.py
- Move enums from constants.py
- Chapter, GameStatus, EngagementState
- Mood, TimeOfDay, Availability, etc.

#### T5.2: Update constants.py
- Remove all numeric values
- Keep only backward-compat imports
- Add deprecation warnings

#### T5.3: Update Imports Across Codebase
- Find all `from nikita.engine.constants import ...`
- Update to `from nikita.config.loader import get_config`
- Update accessor patterns

### Phase 6: Testing (1 hour)

#### T6.1: Unit Tests for ConfigLoader
- Test config loads correctly
- Test validation catches errors
- Test singleton pattern
- Test convenience accessors

#### T6.2: Unit Tests for PromptLoader
- Test prompt loads
- Test variable substitution
- Test missing variable error
- Test caching

#### T6.3: Unit Tests for Experiment System
- Test experiment activation
- Test override merging
- Test inheritance

#### T6.4: Integration Tests
- Test full startup with configs
- Test migration compatibility
- Test performance (< 100ms load)

---

## Dependencies

### External
- pyyaml (YAML parsing)
- pydantic (schema validation)

### Internal
- None (foundational system)

### Blocked By
- None

### Blocks
- 012-context-engineering
- 014-engagement-model
- 003-scoring-engine
- 004-chapter-boss-system
- 005-decay-system
- 006-vice-personalization

---

## Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| YAML syntax errors | High | Medium | Add YAML linting to CI |
| Schema too strict | Medium | Low | Start permissive, tighten later |
| Import update missed | High | Medium | grep for old imports in CI |
| Performance regression | Medium | Low | Benchmark config load time |

---

## Success Metrics

- [ ] All 7 YAML files created and loading
- [ ] All Pydantic schemas validating
- [ ] ConfigLoader singleton working
- [ ] PromptLoader with variable substitution working
- [ ] constants.py contains only enums
- [ ] All imports updated
- [ ] Config load time < 100ms
- [ ] 100% test coverage for config module

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-02 | Claude | Initial plan |

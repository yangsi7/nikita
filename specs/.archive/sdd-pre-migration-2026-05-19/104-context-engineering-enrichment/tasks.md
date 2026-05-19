# Tasks: Spec 104 — Context Engineering Enrichment

## Story 1: Onboarding → Vice Seeding

### T1.1: Create vice seeder module [S]
- **Red**: Test `seed_vices_from_profile()` exists and returns vice list
- **Green**: Create `nikita/engine/vice/seeder.py` with mapping logic
- **File**: `nikita/engine/vice/seeder.py`

### T1.2: Map darkness_level to vice weights [S]
- **Red**: Test level 4 → dark_humor+emotional_intensity at 0.6, level 2 → vulnerability+intellectual at 0.4
- **Green**: Implement 3-tier mapping in seeder
- **File**: `nikita/engine/vice/seeder.py`

### T1.3: Wire into complete_onboarding [S]
- **Red**: Test that complete_onboarding calls seed_vices_from_profile
- **Green**: Add call in `nikita/onboarding/server_tools.py`
- **File**: `nikita/onboarding/server_tools.py`

### T1.4: Tests [S]
- **File**: `tests/engine/vice/test_seeder.py`
- 4 tests: level 1-2, level 3, level 4-5, missing profile graceful

## Story 2: Narrative Arc Refs in Summaries

### T2.1: ThoughtRepository.get_active_arcs [S]
- **Red**: Test returns list of arc strings for user
- **Green**: SQL query `WHERE thought_type='arc' AND status='active'`
- **File**: `nikita/db/repositories/thought_repository.py`

### T2.2: SummaryStage accepts active_arcs [S]
- **Red**: Test LLM prompt includes "Active storylines" when arcs present
- **Green**: Add arcs to prompt string in `_summarize_with_llm()`
- **File**: `nikita/pipeline/stages/summary.py`

### T2.3: Wire arc loading [S]
- **Red**: Test `SummaryStage._run()` loads arcs from thought repo
- **Green**: Add try/except arc loading block
- **File**: `nikita/pipeline/stages/summary.py`

### T2.4: Tests [S]
- **File**: `tests/pipeline/test_summary_arcs.py`
- 3 tests: with arcs, without arcs, repo error graceful

## Story 3: Thought Auto-Resolution

### T3.1: resolve_matching_thoughts [M]
- **Red**: Test matching thoughts marked `status='used'`
- **Green**: SequenceMatcher loop over active thoughts vs facts, threshold 0.6
- **File**: `nikita/db/repositories/thought_repository.py`

### T3.2: Wire into PersistenceStage [S]
- **Red**: Test PersistenceStage calls resolve_matching_thoughts
- **Green**: Add call after fact storage
- **File**: `nikita/pipeline/stages/persistence.py`

### T3.3: Tests [S]
- **File**: `tests/pipeline/test_thought_resolution.py`
- 4 tests: exact match, similar match, no match, empty facts

## Story 4: Thought-Driven Openers

### T4.1: get_active_openers [S]
- **Red**: Test returns max 3 wants_to_share thoughts
- **Green**: SQL query with limit
- **File**: `nikita/db/repositories/thought_repository.py`

### T4.2: Wire into prompt builder [S]
- **Red**: Test ctx.conversation_openers populated
- **Green**: Load in `_enrich_context()`
- **File**: `nikita/pipeline/stages/prompt_builder.py`

### T4.3: Tests [S]
- **File**: `tests/pipeline/test_thought_openers.py`
- 3 tests: with openers, empty, repo error graceful

## Story 5: Boss Judgment Context

### T5.1: Add params to judge_boss_outcome [S]
- **Red**: Test accepts vice_profile and engagement_state params
- **Green**: Add optional kwargs to method signature
- **File**: `nikita/engine/chapters/judgment.py`

### T5.2: Modify LLM prompt [S]
- **Red**: Test prompt includes "Player personality" when vices passed
- **Green**: Append context sections to prompt
- **File**: `nikita/engine/chapters/judgment.py`

### T5.3: Tests [S]
- **File**: `tests/engine/chapters/test_boss_judgment_context.py`
- 3 tests: with context, without context (backward compat), partial context

## Story 6: Backstory-Aware Conflict

### T6.1: Add attachment_style param [S]
- **Red**: Test detect_conflict_state accepts attachment_style
- **Green**: Add optional param with default None
- **File**: `nikita/emotional_state/conflict.py`

### T6.2: Threshold adjustments [S]
- **Red**: Test anxious → lower EXPLOSIVE threshold, avoidant → raise COLD threshold
- **Green**: Implement threshold modifiers
- **File**: `nikita/emotional_state/conflict.py`

### T6.3: Tests [S]
- **File**: `tests/emotional_state/test_attachment_conflict.py`
- 4 tests: anxious, avoidant, secure (no change), disorganized (no change)

---

**Total**: 18 tasks, 21 tests, 6 source files modified, 6 test files created

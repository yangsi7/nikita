# Plan: Spec 104 — Context Engineering Enrichment

## Stories (6 stories, 18 tasks)

### Story 1: Onboarding → Vice Seeding (FR-001)
**Goal**: When user completes onboarding, seed initial vice weights from profile.

- T1.1: Create `nikita/engine/vice/seeder.py` with `seed_vices_from_profile(user_id, profile)` [S]
- T1.2: Map darkness_level → vice category weights (3 tiers) [S]
- T1.3: Wire into `complete_onboarding()` server tool [S]
- T1.4: Tests in `tests/engine/vice/test_seeder.py` — 4 tests [S]

### Story 2: Narrative Arc Refs in Summaries (FR-002)
**Goal**: SummaryStage includes active arcs in LLM prompt.

- T2.1: Add `ThoughtRepository.get_active_arcs(user_id)` method [S]
- T2.2: Modify `SummaryStage._summarize_with_llm()` to accept and use `active_arcs` [S]
- T2.3: Wire arc loading in `SummaryStage._run()` [S]
- T2.4: Tests — 3 tests [S]

### Story 3: Thought Auto-Resolution (FR-003)
**Goal**: Cross-ref facts vs. thoughts, auto-resolve matches.

- T3.1: Add `ThoughtRepository.resolve_matching_thoughts(user_id, facts)` [M]
- T3.2: Wire into PersistenceStage after fact extraction [S]
- T3.3: Tests — 4 tests [S]

### Story 4: Thought-Driven Conversation Openers (FR-004)
**Goal**: Load active `wants_to_share` thoughts into prompt builder.

- T4.1: Add `ThoughtRepository.get_active_openers(user_id, limit=3)` method [S]
- T4.2: Wire into `PromptBuilderStage._enrich_context()` [S]
- T4.3: Tests — 3 tests [S]

### Story 5: Boss Judgment Context (FR-005)
**Goal**: Inject vice profile + engagement state into judge prompt.

- T5.1: Add optional params to `judge_boss_outcome()` [S]
- T5.2: Modify LLM prompt template to include player context [S]
- T5.3: Tests — 3 tests [S]

### Story 6: Backstory-Aware Conflict (FR-006)
**Goal**: Attachment style affects conflict thresholds.

- T6.1: Add optional `attachment_style` param to `detect_conflict_state()` [S]
- T6.2: Implement threshold adjustments for anxious/avoidant [S]
- T6.3: Tests — 4 tests [S]

## Dependencies
- Spec 100 (pipeline tracking) — done
- Spec 103 (touchpoint enrichment) — done

## Risk Mitigation
- All enrichment is non-critical (try/except guards)
- Backward compatible — all new params are optional with defaults

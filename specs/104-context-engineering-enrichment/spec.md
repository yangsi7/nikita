# Spec 104: Context Engineering Enrichment

## Overview
Enrich pipeline context with deeper intelligence from onboarding profile, narrative arcs, thoughts, and vice profiles to produce more contextually aware Nikita responses.

## Functional Requirements

### FR-001: Onboarding Profile → Vice Seeding
Map `darkness_level` + `conversation_style` from onboarding profile to initial vice weights. When a user completes onboarding, seed their `user_vice_preferences` with weighted categories.

**Acceptance Criteria:**
- AC-1.1: `seed_vices_from_profile(user_id, profile)` function exists in `nikita/engine/vice/seeder.py`
- AC-1.2: `darkness_level >= 4` seeds `dark_humor`, `emotional_intensity` at weight 0.6
- AC-1.3: `darkness_level <= 2` seeds `vulnerability`, `intellectual_dominance` at weight 0.4
- AC-1.4: `darkness_level == 3` (default) seeds all categories at weight 0.3
- AC-1.5: Called from `complete_onboarding()` server tool after profile is stored

### FR-002: Narrative Arc Refs in Daily Summaries
Inject active narrative arcs (from `nikita_thoughts` where `thought_type='arc'` and `status='active'`) into the SummaryStage LLM prompt so summaries reference ongoing storylines.

**Acceptance Criteria:**
- AC-2.1: `SummaryStage._summarize_with_llm()` accepts `active_arcs: list[str]` parameter
- AC-2.2: Active arcs loaded from `ThoughtRepository.get_active_arcs(user_id)` (new method)
- AC-2.3: When arcs present, summary prompt includes "Active storylines: {arcs}" section
- AC-2.4: When no arcs, prompt unchanged (backward compatible)

### FR-003: Thought Auto-Resolution
Cross-reference extracted facts against active thoughts. When a `nikita_thoughts` entry of type `wants_to_share` has its topic appear in `extracted_facts`, mark it `status='used'`.

**Acceptance Criteria:**
- AC-3.1: `ThoughtRepository.resolve_matching_thoughts(user_id, facts: list[str])` method
- AC-3.2: Uses SequenceMatcher (threshold 0.6) to compare thought content vs. facts
- AC-3.3: Called after ExtractionStage completes, within PersistenceStage
- AC-3.4: Resolved thoughts get `status='used'`, `resolved_at=now()`

### FR-004: Thought-Driven Conversation Openers
Load active `wants_to_share` thoughts into prompt builder so Nikita references them as conversation openers.

**Acceptance Criteria:**
- AC-4.1: `PromptBuilderStage._enrich_context()` loads active thoughts via `ThoughtRepository.get_active_openers(user_id)`
- AC-4.2: Stored in `ctx.conversation_openers: list[str]`
- AC-4.3: Template section renders openers as "Things on Nikita's mind: ..."
- AC-4.4: Max 3 openers loaded (most recent first)

### FR-005: Boss Judgment Context Enrichment
Inject vice profile + engagement state into boss judge prompt so judgment considers the player's personality.

**Acceptance Criteria:**
- AC-5.1: `BossJudgment.judge_boss_outcome()` accepts optional `vice_profile: list[str]`, `engagement_state: str`
- AC-5.2: Vice categories appended to judge prompt as "Player personality: {categories}"
- AC-5.3: Engagement state appended as "Current engagement: {state}"
- AC-5.4: Backward compatible — omitting params doesn't change behavior

### FR-006: Backstory-Aware Conflict Detection
Load `attachment_style` from PsycheState into temperature calculation for conflict detection.

**Acceptance Criteria:**
- AC-6.1: `ConflictDetector.detect_conflict_state()` accepts optional `attachment_style: str`
- AC-6.2: `anxious` attachment lowers EXPLOSIVE threshold by 0.1 (more sensitive)
- AC-6.3: `avoidant` attachment raises COLD threshold by 0.1 (easier to go cold)
- AC-6.4: `secure` and `disorganized` use default thresholds

## Non-Functional Requirements
- All enrichment is non-critical (try/except, graceful degradation)
- No additional LLM calls — use data already in DB
- Tests: 25+ new tests across 6 stories

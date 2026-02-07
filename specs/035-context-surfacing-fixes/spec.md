# Spec 035: Context Surfacing Fixes

**Status**: Draft
**Priority**: P1 (Core Feature)
**Estimated Effort**: 14-20 hours
**Dependencies**: Spec 028 (Voice Onboarding), Spec 029 (Context Comprehensive)

---

## 1. Overview

### 1.1 Problem Statement

The Nikita deep humanization system is 95% complete with 8 humanization modules (021-028) wired and working. However, 4 critical gaps prevent full context surfacing:

1. **Social Circle Module Not Wired**: `social_generator.py` (536 LOC) exists but is never called during onboarding. Users get no personalized social world.

2. **Narrative Arcs Module Not Wired**: `arcs.py` (527 LOC) exists but is never called during conversation processing. No multi-conversation storylines occur.

3. **Voice Prompt Logging Missing**: Text agent logs all prompts to `generated_prompts` table; voice agent does not. Admin cannot debug voice prompt issues.

4. **Test Coverage Gap**: `social_generator.py` and `arcs.py` have 0 tests while similar modules (`psychology_mapper.py`, `relationship_analyzer.py`) have 56+ tests.

### 1.2 Goal

Wire existing social circle and narrative arc modules into the production pipeline, add voice prompt observability, and ensure comprehensive test coverage.

### 1.3 Success Metrics

- Social circle generated for 100% of new users completing onboarding
- Narrative arcs created/progressed after eligible conversations
- Voice prompts visible in admin dashboard
- 35+ new tests for social_generator + arcs modules

---

## 2. User Stories

### US-1: Social Circle Integration (GAP-1)
**As a** user completing voice onboarding,
**I want** Nikita to have a personalized social circle adapted to my profile,
**So that** she can reference named friends, family, and colleagues authentically in our conversations.

**Priority**: P1
**Acceptance Criteria**:
- AC-1.1: `generate_social_circle_for_user()` called in `handoff.py` after profile creation
- AC-1.2: 5-8 FriendCharacter objects created per user based on location, hobbies, job, meeting_context
- AC-1.3: Social circle stored in `user_social_circles` database table
- AC-1.4: Social circle loaded in `MetaPromptService._load_context()` TIER 5
- AC-1.5: Social circle section rendered in `system_prompt.meta.md` template
- AC-1.6: Token budget maintained (≤500 tokens for social circle)

### US-2: Narrative Arc Integration (GAP-2)
**As a** user having ongoing conversations with Nikita,
**I want** multi-conversation storylines to develop naturally,
**So that** our relationship feels dynamic with meaningful plot progression.

**Priority**: P1
**Acceptance Criteria**:
- AC-2.1: Arc selection logic added to `PostProcessor` after `_analyze_psychology()`
- AC-2.2: Template selection based on vulnerability_level and conversation topics
- AC-2.3: Max 2 active arcs per user enforced
- AC-2.4: Arc stage progression (setup → rising → climax → falling → resolved)
- AC-2.5: Active arcs stored in `user_narrative_arcs` database table
- AC-2.6: Arc context loaded in `MetaPromptService._load_context()`
- AC-2.7: Arc section rendered in `system_prompt.meta.md` template

### US-3: Voice Prompt Logging (GAP-3)
**As an** admin debugging voice conversations,
**I want** voice prompts logged to the same `generated_prompts` table as text,
**So that** I can inspect what prompt the voice agent received.

**Priority**: P2
**Acceptance Criteria**:
- AC-3.1: `generated_prompt` committed to database in `ConversationConfigBuilder.build_config()`
- AC-3.2: `platform` field added to `generated_prompts` table (text/voice)
- AC-3.3: Voice prompts visible at `/admin/prompts` with platform filter
- AC-3.4: Admin voice monitoring page links to prompt detail

### US-4: Test Coverage (GAP-4)
**As a** developer maintaining the humanization system,
**I want** comprehensive test coverage for social_generator and arcs modules,
**So that** regressions are caught before deployment.

**Priority**: P2
**Acceptance Criteria**:
- AC-4.1: `test_social_generator.py` with 15+ tests covering character generation, adaptation logic
- AC-4.2: `test_arcs.py` with 20+ tests covering template selection, stage progression, resolution
- AC-4.3: All new tests passing in CI
- AC-4.4: Integration test verifying social circle + arcs in generated prompt

---

## 3. Functional Requirements

### FR-001: Social Circle Database Schema
The system SHALL create a `user_social_circles` table with:
- `id` (UUID, PK)
- `user_id` (UUID, FK to users)
- `friend_name` (TEXT)
- `friend_role` (TEXT: best_friend, ex, work_colleague, party_friend, family, therapist)
- `age` (INTEGER)
- `occupation` (TEXT)
- `personality` (TEXT)
- `relationship_to_nikita` (TEXT)
- `storyline_potential` (JSONB)
- `trigger_conditions` (JSONB)
- `adapted_traits` (JSONB)
- `is_active` (BOOLEAN, default true)
- `created_at`, `updated_at` (TIMESTAMPTZ)

### FR-002: Narrative Arc Database Schema
The system SHALL create a `user_narrative_arcs` table with:
- `id` (UUID, PK)
- `user_id` (UUID, FK to users)
- `template_name` (TEXT)
- `category` (TEXT: career, social, personal, relationship, family)
- `current_stage` (TEXT: setup, rising, climax, falling, resolved)
- `stage_progress` (INTEGER, 0-100)
- `conversations_in_arc` (INTEGER)
- `max_conversations` (INTEGER)
- `current_description` (TEXT)
- `involved_characters` (JSONB)
- `emotional_impact` (JSONB)
- `is_active` (BOOLEAN)
- `started_at`, `resolved_at` (TIMESTAMPTZ)

### FR-003: Social Circle Repository
The system SHALL provide `SocialCircleRepository` with:
- `create_circle_for_user(user_id, friends: list[FriendCharacter])` → stores all friends
- `get_circle(user_id)` → returns list of UserSocialCircle
- `get_active_friends(user_id)` → returns active friends only

### FR-004: Narrative Arc Repository
The system SHALL provide `NarrativeArcRepository` with:
- `create_arc(user_id, template: ArcTemplate)` → creates new arc
- `get_active_arcs(user_id)` → returns active arcs (max 2)
- `advance_arc(arc_id, new_stage)` → progresses stage
- `resolve_arc(arc_id)` → marks completed
- `increment_conversation_count(arc_id)` → tracks conversation count

### FR-005: Onboarding Handoff Integration
The system SHALL call `generate_social_circle_for_user()` in `handoff.py`:
- After successful profile creation in `complete_handoff()` or `store_profile()`
- Using profile fields: location, hobbies, job/occupation, meeting_context
- Storing result via `SocialCircleRepository`

### FR-006: PostProcessor Arc Stage
The system SHALL add `_update_narrative_arcs()` to PostProcessor:
- Called after `_analyze_psychology()` stage
- Checks if new arc should start (max 2 active)
- Progresses existing arcs based on conversation dynamics
- Stores arc updates via `NarrativeArcRepository`

### FR-007: Context Loading Enhancement
The system SHALL load social circle and arcs in `MetaPromptService._load_context()`:
- Social circle in TIER 5 (Personalization) section
- Active arcs in TIER 5 section
- Format for template injection

### FR-008: Template Enhancement
The system SHALL add sections to `system_prompt.meta.md`:
- `## NIKITA'S SOCIAL WORLD` with friend list
- `## ONGOING STORYLINES` with active arc context
- Jinja2 template syntax for dynamic rendering

### FR-009: Voice Prompt Logging
The system SHALL log voice prompts:
- In `ConversationConfigBuilder.build_config()` after `generate_system_prompt()`
- Commit to `generated_prompts` table with `platform='voice'`
- Store `generated_prompt_id` in voice conversation record

### FR-010: Generated Prompts Platform Field
The system SHALL add `platform` column to `generated_prompts`:
- Type: VARCHAR(10)
- Values: 'text', 'voice'
- Default: 'text'
- Migration for existing data

---

## 4. Non-Functional Requirements

### NFR-001: Performance
- Social circle loading: <50ms (cached after first load)
- Arc update processing: <100ms per conversation
- No regression in context loading (<500ms total)

### NFR-002: Token Budget
- Social circle section: ≤500 tokens
- Arc context section: ≤300 tokens
- Total prompt remains ≤15K tokens

### NFR-003: Test Coverage
- New modules: ≥80% line coverage
- All edge cases tested (empty profile, max arcs, resolved arcs)

### NFR-004: Data Integrity
- Social circle immutable after creation (no mid-game changes)
- Arc progression atomic (no partial stage updates)
- Foreign key constraints enforced

---

## 5. Technical Design

### 5.1 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      ONBOARDING FLOW                             │
│                                                                  │
│  Voice Onboarding → complete_handoff() → generate_social_circle │
│                                        → store in DB             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CONVERSATION FLOW                             │
│                                                                  │
│  Message → PostProcessor → _analyze_psychology()                 │
│                         → _update_narrative_arcs() [NEW]         │
│                         → store arc updates                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CONTEXT LOADING                               │
│                                                                  │
│  MetaPromptService._load_context() → TIER 5: social_circle       │
│                                   → TIER 5: narrative_arcs       │
│                                   → system_prompt.meta.md        │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 File Changes

**New Files**:
- `nikita/db/models/social_circle.py` - UserSocialCircle SQLAlchemy model
- `nikita/db/models/narrative_arc.py` - UserNarrativeArc SQLAlchemy model
- `nikita/db/repositories/social_circle_repository.py` - Repository class
- `nikita/db/repositories/narrative_arc_repository.py` - Repository class
- `tests/life_simulation/test_social_generator.py` - 15+ tests
- `tests/life_simulation/test_arcs.py` - 20+ tests

**Modified Files**:
- `nikita/onboarding/handoff.py` - Wire social circle generation
- `nikita/context/post_processor.py` - Add `_update_narrative_arcs()` stage
- `nikita/meta_prompts/service.py` - Load social circle + arcs in context
- `nikita/meta_prompts/templates/system_prompt.meta.md` - Add template sections
- `nikita/agents/voice/context.py` - Add prompt logging
- `nikita/db/models/__init__.py` - Export new models
- `nikita/db/models/generated_prompt.py` - Add platform field

### 5.3 Database Migrations

Two migrations required:
1. `0015_social_circles.sql` - Create user_social_circles table + indexes
2. `0016_narrative_arcs.sql` - Create user_narrative_arcs table + indexes
3. `0017_generated_prompts_platform.sql` - Add platform column

---

## 6. Test Plan

### 6.1 Unit Tests

**test_social_generator.py** (15+ tests):
- `test_generates_core_characters` - Lena, Viktor, Max, etc.
- `test_adapts_to_berlin_location` - Tech hub friends
- `test_adapts_to_small_city_location` - Local scene friends
- `test_adapts_to_tech_hobbies` - Hacker/security friends
- `test_adapts_to_creative_hobbies` - Artist friends
- `test_adapts_to_finance_job` - Finance network friends
- `test_adapts_to_creative_job` - Creative network friends
- `test_meeting_context_party` - Party host friend
- `test_meeting_context_app` - Mutual connection friend
- `test_meeting_context_work` - Professional contact friend
- `test_5_to_8_characters_generated` - Count validation
- `test_character_roles_covered` - All roles present
- `test_storyline_potential_populated` - Each character has storylines
- `test_trigger_conditions_populated` - Each character has triggers
- `test_to_dict_serialization` - Storage format correct

**test_arcs.py** (20+ tests):
- `test_arc_system_singleton` - get_arc_system() returns same instance
- `test_template_selection_vulnerability_0` - Surface templates only
- `test_template_selection_vulnerability_3` - Mid-level templates
- `test_template_selection_vulnerability_5` - Deep templates
- `test_template_selection_by_topic_work` - Career arcs
- `test_template_selection_by_topic_friend` - Social arcs
- `test_template_selection_by_topic_family` - Family arcs
- `test_arc_stage_progression_setup_to_rising` - First advance
- `test_arc_stage_progression_full_cycle` - All 5 stages
- `test_arc_should_advance_by_conversation_count` - Count-based
- `test_arc_max_duration_enforcement` - Auto-resolve
- `test_arc_resolution_sets_resolved_at` - Timestamp set
- `test_max_2_active_arcs` - Limit enforcement
- `test_arc_context_formatting` - Prompt injection format
- `test_arc_to_dict_serialization` - Storage format
- `test_arc_category_filtering` - Category-based selection
- `test_involved_characters_in_arc` - Character references
- `test_emotional_impact_values` - Impact scores
- `test_arc_creation_from_template` - Template instantiation
- `test_arc_inactive_after_resolution` - is_active=False

### 6.2 Integration Tests

- `test_handoff_creates_social_circle` - End-to-end onboarding
- `test_post_processor_updates_arcs` - Full conversation flow
- `test_social_circle_in_prompt` - Verify in generated prompt
- `test_arcs_in_prompt` - Verify in generated prompt
- `test_voice_prompt_logged` - Verify in generated_prompts table

---

## 7. Rollout Plan

### Phase 1: Database + Models (2h)
1. Create migrations via Supabase MCP
2. Create SQLAlchemy models
3. Create repository classes
4. Run migrations in staging

### Phase 2: Social Circle Integration (3h)
1. Wire to handoff.py
2. Add to MetaPromptService._load_context()
3. Update system_prompt.meta.md template
4. Write tests

### Phase 3: Narrative Arc Integration (4h)
1. Add _update_narrative_arcs() to PostProcessor
2. Add to MetaPromptService._load_context()
3. Update system_prompt.meta.md template
4. Write tests

### Phase 4: Voice Logging + Final Tests (3h)
1. Add prompt logging to voice context.py
2. Add platform field migration
3. Write remaining tests
4. Run full test suite

### Phase 5: E2E Verification (2h)
1. Deploy to Cloud Run
2. Create test user via voice onboarding
3. Verify social circle created
4. Have conversations to trigger arcs
5. Verify arcs progress
6. Check admin dashboards

---

## 8. Open Questions

None - all requirements clarified in discovery phase.

---

## 9. References

- Discovery artifacts: `docs-to-process/discovery-035/`
- GAP-ANALYSIS.md: Risk scores and detailed gap descriptions
- IMPLEMENTATION-PLAN.md: Phase breakdown with code snippets
- SYSTEM-UNDERSTANDING.md: Full context engineering diagram

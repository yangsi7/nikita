---
feature: 017-enhanced-onboarding
created: 2025-12-15
updated: 2026-01-21
status: superseded
superseded_by: 028-voice-onboarding
total_tasks: 23
completed: 18
remaining_na: 5
---

# Tasks: Enhanced Onboarding with Personalization Guide

> **SUPERSEDED BY SPEC 028 (Voice Onboarding)**
>
> Remaining tasks (5) marked as N/A - functionality delivered via voice onboarding.
> See [Spec 028 tasks.md](../028-voice-onboarding/tasks.md) for complete implementation.

**Source**: [plan.md](plan.md) | **Spec**: [spec.md](spec.md)

---

## Progress Summary (Final - 2026-01-21)

| User Story | Tasks | Completed | Status |
|------------|-------|-----------|--------|
| US-1: Basic Profile Collection | 6 | 6 | ✅ Complete |
| US-2: Venue Research & Scenarios | 8 | 5 | ⏭️ N/A - Voice pivot |
| US-3: Nikita Persona Integration | 4 | 4 | ✅ Complete |
| US-7: Memory Integration | 3 | 3 | ✅ Complete |
| Testing | 4 | 2 | ⏭️ N/A - Voice pivot |
| **Total** | **23** | **18** | **Superseded** |

**Note**: 5 remaining tasks (US-2 remaining + testing) not implemented in text path.
Voice onboarding (Spec 028) provides equivalent functionality with superior UX.

### Recent Changes (2025-12-22)

- FR-008: Added `_send_first_nikita_message()` to OnboardingHandler
- FR-013: Added `_load_memory_context()` to MetaPromptService (Graphiti memory loading)
- FR-014: Added conversation summaries loading (today/week)
- FR-015: Verified per-conversation prompt generation working
- Added 4 first Nikita message tests + 3 memory context tests (34 total new tests)

---

## User Story 1: Basic Profile Collection (Priority: P1)

### T1.1: Create UserProfile Model
- **Status**: [ ] Not Started
- **Estimate**: 2 hours
- **Dependencies**: None

**Acceptance Criteria**:
- [ ] AC-T1.1-001: UserProfile model with fields: location_city, location_country, life_stage, social_scene, primary_interest, drug_tolerance (1-5)
- [ ] AC-T1.1-002: SQLAlchemy model inherits from Base, has UUID primary key referencing users.id
- [ ] AC-T1.1-003: Migration script creates user_profiles table with proper constraints

**Files to Create/Modify**:
- `nikita/db/models/profile.py` (NEW)
- `migrations/versions/00XX_add_user_profiles.py` (NEW)
- `nikita/db/models/__init__.py` (ADD export)

---

### T1.2: Create UserBackstory Model
- **Status**: [ ] Not Started
- **Estimate**: 2 hours
- **Dependencies**: T1.1

**Acceptance Criteria**:
- [ ] AC-T1.2-001: UserBackstory model with fields: venue_name, venue_city, scenario_type, how_we_met, the_moment, unresolved_hook, nikita_persona_overrides (JSONB)
- [ ] AC-T1.2-002: One-to-one relationship with User (UNIQUE constraint on user_id)
- [ ] AC-T1.2-003: Migration script creates backstories table

**Files to Create/Modify**:
- `nikita/db/models/profile.py` (ADD)
- `migrations/versions/00XX_add_backstories.py` (NEW)

---

### T1.4: Create OnboardingState Model
- **Status**: [ ] Not Started
- **Estimate**: 2 hours
- **Dependencies**: None (parallel with T1.1)

**Acceptance Criteria**:
- [ ] AC-T1.4-001: OnboardingState model with fields: telegram_id, current_step (enum), collected_answers (JSONB), started_at, updated_at
- [ ] AC-T1.4-002: Steps enum: LOCATION, LIFE_STAGE, SCENE, INTEREST, DRUG_TOLERANCE, VENUE_RESEARCH, SCENARIO_SELECTION, COMPLETE
- [ ] AC-T1.4-003: Delete on completion (transient state like PendingRegistration)

**Files to Create/Modify**:
- `nikita/db/models/profile.py` (ADD)
- `migrations/versions/00XX_add_onboarding_state.py` (NEW)

---

### T1.5: Create Repository Classes
- **Status**: [ ] Not Started
- **Estimate**: 3 hours
- **Dependencies**: T1.1, T1.2, T1.4

**Acceptance Criteria**:
- [ ] AC-T1.5-001: ProfileRepository with create_profile(), get_by_user_id(), update()
- [ ] AC-T1.5-002: BackstoryRepository with create(), get_by_user_id(), update()
- [ ] AC-T1.5-003: OnboardingStateRepository with get_or_create(), update_step(), delete()
- [ ] AC-T1.5-004: All repositories inherit from BaseRepository[ModelT]

**Files to Create/Modify**:
- `nikita/db/repositories/profile_repository.py` (NEW)
- `nikita/db/repositories/__init__.py` (ADD exports)

---

### T2.1: Create OnboardingHandler Class
- **Status**: [ ] Not Started
- **Estimate**: 4 hours
- **Dependencies**: T1.4, T1.5

**Acceptance Criteria**:
- [ ] AC-T2.1-001: OnboardingHandler class with handle() method routing by current_step
- [ ] AC-T2.1-002: Step handlers for each profile field with appropriate prompts
- [ ] AC-T2.1-003: Mysterious intro message: "Before we connect you... I need to know a bit about you."
- [ ] AC-T2.1-004: State saved after each step (resume capability)
- [ ] AC-T2.1-005: Validation for each field type (location, life_stage enum, scene enum, freeform text, 1-5 scale)

**Files to Create/Modify**:
- `nikita/platforms/telegram/onboarding/__init__.py` (NEW)
- `nikita/platforms/telegram/onboarding/handler.py` (NEW)

---

### T2.3: Resume Logic for Abandoned Onboarding
- **Status**: [ ] Not Started
- **Estimate**: 2 hours
- **Dependencies**: T2.1

**Acceptance Criteria**:
- [ ] AC-T2.3-001: On new message, check OnboardingState for telegram_id
- [ ] AC-T2.3-002: If incomplete onboarding exists, prompt to continue from last step
- [ ] AC-T2.3-003: "skip" or "I don't want to" detection → apply generic backstory
- [ ] AC-T2.3-004: Progress preserved for 24+ hours (no auto-expiry)

**Files to Create/Modify**:
- `nikita/platforms/telegram/onboarding/handler.py` (MODIFY)

---

## User Story 2: Venue Research & Scenario Generation (Priority: P1)

### T1.3: Create VenueCache Model
- **Status**: [ ] Not Started
- **Estimate**: 1 hour
- **Dependencies**: None (parallel with T1.1)

**Acceptance Criteria**:
- [ ] AC-T1.3-001: VenueCache model with fields: city, scene, venues (JSONB array), fetched_at, expires_at
- [ ] AC-T1.3-002: Composite unique constraint on (city, scene)
- [ ] AC-T1.3-003: Migration script creates venue_cache table with 30-day expiry default

**Files to Create/Modify**:
- `nikita/db/models/profile.py` (ADD)
- `migrations/versions/00XX_add_venue_cache.py` (NEW)

---

### T2.2: Integrate with OTP Handler
- **Status**: [ ] Not Started
- **Estimate**: 2 hours
- **Dependencies**: T2.1

**Acceptance Criteria**:
- [ ] AC-T2.2-001: After OTP verification success, check if user has profile
- [ ] AC-T2.2-002: If no profile, route to OnboardingHandler instead of welcome message
- [ ] AC-T2.2-003: If profile exists, send normal welcome message
- [ ] AC-T2.2-004: Modify webhook routing to detect ongoing onboarding state

**Files to Create/Modify**:
- `nikita/platforms/telegram/otp_handler.py` (MODIFY)
- `nikita/api/routes/telegram.py` (MODIFY)

---

### T3.1: Create VenueResearchService
- **Status**: [ ] Not Started
- **Estimate**: 4 hours
- **Dependencies**: T1.3, T1.5

**Acceptance Criteria**:
- [ ] AC-T3.1-001: VenueResearchService class with research_venues(city, scene) method
- [ ] AC-T3.1-002: Uses Firecrawl MCP firecrawl_search for "{city} best {scene} venues"
- [ ] AC-T3.1-003: Parses results to extract venue names, descriptions, vibes
- [ ] AC-T3.1-004: Caches results in VenueCache for 30 days
- [ ] AC-T3.1-005: Returns structured list of venues with name, description, vibe

**Files to Create/Modify**:
- `nikita/services/venue_research.py` (NEW)
- `nikita/services/__init__.py` (ADD export)

---

### T3.2: Implement Venue Research Fallback
- **Status**: [ ] Not Started
- **Estimate**: 2 hours
- **Dependencies**: T3.1

**Acceptance Criteria**:
- [ ] AC-T3.2-001: On Firecrawl timeout/error, fallback to user prompt within 2 seconds
- [ ] AC-T3.2-002: Prompt: "What's your favorite spot in {city}?"
- [ ] AC-T3.2-003: Accept user-provided venue and use for scenarios
- [ ] AC-T3.2-004: Log fallback usage for monitoring

**Files to Create/Modify**:
- `nikita/services/venue_research.py` (MODIFY)

---

### T3.3: Integrate Venue Cache
- **Status**: [ ] Not Started
- **Estimate**: 1 hour
- **Dependencies**: T3.1

**Acceptance Criteria**:
- [ ] AC-T3.3-001: Check cache before calling Firecrawl
- [ ] AC-T3.3-002: If cache hit and not expired, return cached venues
- [ ] AC-T3.3-003: If cache miss or expired, fetch and update cache
- [ ] AC-T3.3-004: Cache key: (city.lower(), scene.lower())

**Files to Create/Modify**:
- `nikita/services/venue_research.py` (MODIFY)

---

### T4.1: Create BackstoryGeneratorService
- **Status**: [ ] Not Started
- **Estimate**: 4 hours
- **Dependencies**: T3.1

**Acceptance Criteria**:
- [ ] AC-T4.1-001: BackstoryGeneratorService class with generate_scenarios(profile, venues) method
- [ ] AC-T4.1-002: Uses Claude LLM to generate 3 distinct scenarios
- [ ] AC-T4.1-003: Each scenario has: venue, context (Nikita's reason there), the_moment, unresolved_hook
- [ ] AC-T4.1-004: Scenarios vary by tone: romantic, intellectual, chaotic
- [ ] AC-T4.1-005: Template prompt includes user profile for personalization

**Files to Create/Modify**:
- `nikita/services/backstory_generator.py` (NEW)
- `nikita/services/__init__.py` (ADD export)

---

### T4.2: Custom Backstory Validation
- **Status**: [ ] Not Started
- **Estimate**: 2 hours
- **Dependencies**: T4.1

**Acceptance Criteria**:
- [ ] AC-T4.2-001: Accept freeform text for custom backstory
- [ ] AC-T4.2-002: Use LLM to extract: venue, the_moment, hook from user text
- [ ] AC-T4.2-003: Enhance user text with Nikita-style details
- [ ] AC-T4.2-004: Validate minimum content (venue or location mentioned)

**Files to Create/Modify**:
- `nikita/services/backstory_generator.py` (MODIFY)

---

### T4.3: Scenario Presentation in Onboarding
- **Status**: [ ] Not Started
- **Estimate**: 3 hours
- **Dependencies**: T4.1, T2.1

**Acceptance Criteria**:
- [ ] AC-T4.3-001: Present 3 scenarios + custom option in Telegram message
- [ ] AC-T4.3-002: Use numbered options (1, 2, 3, 4) for selection
- [ ] AC-T4.3-003: Parse user selection and store in OnboardingState
- [ ] AC-T4.3-004: On "4" (custom), prompt for freeform text

**Files to Create/Modify**:
- `nikita/platforms/telegram/onboarding/handler.py` (MODIFY)

---

## User Story 3: Nikita Persona Integration (Priority: P1)

### T5.1: Create BackstoryContext Dataclass
- **Status**: [ ] Not Started
- **Estimate**: 1 hour
- **Dependencies**: T1.2

**Acceptance Criteria**:
- [ ] AC-T5.1-001: BackstoryContext dataclass with fields from UserBackstory model
- [ ] AC-T5.1-002: Include persona_overrides for adaptive traits
- [ ] AC-T5.1-003: Factory method from_model(UserBackstory) for conversion

**Files to Create/Modify**:
- `nikita/meta_prompts/models.py` (ADD)

---

### T5.2: Add Backstory to MetaPromptContext
- **Status**: [ ] Not Started
- **Estimate**: 2 hours
- **Dependencies**: T5.1

**Acceptance Criteria**:
- [ ] AC-T5.2-001: Add backstory: BackstoryContext | None field to MetaPromptContext
- [ ] AC-T5.2-002: Load backstory in context builder when user has backstory
- [ ] AC-T5.2-003: Default to None for users without backstory (existing users)

**Files to Create/Modify**:
- `nikita/meta_prompts/models.py` (MODIFY)
- `nikita/meta_prompts/service.py` (MODIFY)

---

### T5.3: Update System Prompt Template
- **Status**: [ ] Not Started
- **Estimate**: 2 hours
- **Dependencies**: T5.2

**Acceptance Criteria**:
- [ ] AC-T5.3-001: Add BACKSTORY section to system_prompt.meta.md
- [ ] AC-T5.3-002: Include: venue, how_we_met, the_moment, unresolved_hook
- [ ] AC-T5.3-003: Conditional rendering: only if backstory exists
- [ ] AC-T5.3-004: First message instruction: reference venue and hook

**Files to Create/Modify**:
- `nikita/meta_prompts/templates/system_prompt.meta.md` (MODIFY)

---

### T5.4: Persona Adaptation Logic
- **Status**: [ ] Not Started
- **Estimate**: 2 hours
- **Dependencies**: T5.2

**Acceptance Criteria**:
- [ ] AC-T5.4-001: Map life_stage to Nikita occupation (tech→hacker, artist→digital artist, etc.)
- [ ] AC-T5.4-002: Map social_scene to Nikita interests (techno→DJ hobby, art→gallery hopper)
- [ ] AC-T5.4-003: Map drug_tolerance to vice_profile intensity
- [ ] AC-T5.4-004: Store persona_overrides in UserBackstory.nikita_persona_overrides

**Files to Create/Modify**:
- `nikita/services/backstory_generator.py` (ADD)

---

## Testing

### T6.1: Database Model Tests
- **Status**: [ ] Not Started
- **Estimate**: 3 hours
- **Dependencies**: T1.1-T1.5

**Acceptance Criteria**:
- [ ] AC-T6.1-001: Unit tests for UserProfile, UserBackstory, VenueCache, OnboardingState models
- [ ] AC-T6.1-002: Repository tests for CRUD operations
- [ ] AC-T6.1-003: Test data fixtures for profile scenarios
- [ ] AC-T6.1-004: 90%+ coverage for new models

**Files to Create/Modify**:
- `tests/db/models/test_profile.py` (NEW)
- `tests/db/repositories/test_profile_repository.py` (NEW)

---

### T6.2: Onboarding Handler Tests
- **Status**: [ ] Not Started
- **Estimate**: 4 hours
- **Dependencies**: T2.1-T2.3

**Acceptance Criteria**:
- [ ] AC-T6.2-001: Test each step of onboarding flow
- [ ] AC-T6.2-002: Test resume from abandoned state
- [ ] AC-T6.2-003: Test skip/opt-out detection
- [ ] AC-T6.2-004: Test existing user bypass
- [ ] AC-T6.2-005: 85%+ coverage for handler

**Files to Create/Modify**:
- `tests/platforms/telegram/onboarding/test_handler.py` (NEW)

---

### T6.3: Service Integration Tests
- **Status**: [ ] Not Started
- **Estimate**: 4 hours
- **Dependencies**: T3.1-T4.1

**Acceptance Criteria**:
- [ ] AC-T6.3-001: Test VenueResearchService with mock Firecrawl
- [ ] AC-T6.3-002: Test fallback when Firecrawl fails
- [ ] AC-T6.3-003: Test BackstoryGeneratorService with mock LLM
- [ ] AC-T6.3-004: Test cache hit/miss scenarios
- [ ] AC-T6.3-005: 80%+ coverage for services

**Files to Create/Modify**:
- `tests/services/test_venue_research.py` (NEW)
- `tests/services/test_backstory_generator.py` (NEW)

---

### T6.4: E2E Onboarding Test
- **Status**: [ ] Not Started
- **Estimate**: 3 hours
- **Dependencies**: All P1 tasks

**Acceptance Criteria**:
- [ ] AC-T6.4-001: E2E test: OTP → profile → venues → scenarios → selection → first message
- [ ] AC-T6.4-002: Verify Nikita's first message contains venue and hook
- [ ] AC-T6.4-003: Verify profile persists across sessions
- [ ] AC-T6.4-004: Test with real Firecrawl (optional, can mock)

**Files to Create/Modify**:
- `tests/e2e/test_onboarding_flow.py` (NEW)

---

## Dependency Graph

```
Phase 1 (Database - Parallel):
┌─────────────────────────────────────┐
│ T1.1 ───┐                           │
│ T1.3 ───┼──→ T1.5 (repos)           │
│ T1.4 ───┘        │                  │
│         T1.2 ────┘                  │
└─────────────────────────────────────┘
              │
              ▼
Phase 2 (Handler):
┌─────────────────────────────────────┐
│ T2.1 (handler) → T2.2 (otp routing) │
│        └──────→ T2.3 (resume)       │
└─────────────────────────────────────┘
              │
              ▼
Phase 3 (Venue Research):
┌─────────────────────────────────────┐
│ T3.1 (research) → T3.2 (fallback)   │
│        └───────→ T3.3 (cache)       │
└─────────────────────────────────────┘
              │
              ▼
Phase 4 (Backstory):
┌─────────────────────────────────────┐
│ T4.1 (generator) → T4.2 (custom)    │
│        └───────→ T4.3 (present)     │
└─────────────────────────────────────┘
              │
              ▼
Phase 5 (MetaPrompt):
┌─────────────────────────────────────┐
│ T5.1 → T5.2 → T5.3                  │
│         └──→ T5.4                   │
└─────────────────────────────────────┘
              │
              ▼
Phase 6 (Testing):
┌─────────────────────────────────────┐
│ T6.1, T6.2, T6.3, T6.4              │
└─────────────────────────────────────┘
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-15 | Initial task breakdown from plan.md |
| 1.1 | 2025-12-15 | Added missing tasks T2.3, T3.3, T4.2 (audit fix G1) |

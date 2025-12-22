---
plan_id: "017-enhanced-onboarding"
status: "draft"
owner: "Claude"
created_at: "2025-12-15"
updated_at: "2025-12-15"
type: "plan"
---

# Implementation Plan: Enhanced Onboarding with Personalization Guide

## Goal

**Objective**: Implement personalization flow for new Telegram users that collects profile info, researches venues, generates backstory scenarios, and adapts Nikita's persona.

**Success Definition**: New users complete onboarding, select backstory, and receive immersive first message from Nikita referencing their shared history.

**Based On**: [specs/017-enhanced-onboarding/spec.md](spec.md)

---

## Summary

**Overview**: After OTP verification, route new users to a personalization guide that collects 5 profile fields (location, life_stage, scene, interest, drug_tolerance), uses Firecrawl MCP to research real venues, generates 3 "how we met" scenarios via LLM, lets user select or write custom backstory, then injects context into Nikita's persona for immersive first interaction.

**Tech Stack**:
- **Backend**: Python 3.12 + FastAPI + Pydantic AI
- **Database**: Supabase PostgreSQL + SQLAlchemy
- **External APIs**: Firecrawl MCP (venue research), Claude (scenario generation)
- **Testing**: pytest + pytest-asyncio
- **Deployment**: Google Cloud Run

**Deliverables**:
1. **Database Models**: UserProfile, UserBackstory, VenueCache tables
2. **Onboarding Handler**: Telegram message handler for profile collection
3. **Venue Research Service**: Firecrawl integration with fallback
4. **Backstory Generator**: LLM-based scenario generation
5. **MetaPrompt Integration**: Backstory injection into Nikita's context

---

## Technical Context

### Existing Architecture (Intelligence Evidence)

**Intelligence Queries Executed**:
```bash
# Repository pattern
Grep "class.*Repository" nikita/db/repositories/
# Found: BaseRepository[ModelT] pattern at base.py:18

# MetaPromptContext structure
Grep "class MetaPromptContext" nikita/meta_prompts/
# Found: models.py:79

# DB models
Glob "nikita/db/models/*.py"
# Found: 11 model files including user.py, engagement.py
```

**Patterns Discovered** (CoD^Σ Evidence):
- **Repository Pattern** @ `nikita/db/repositories/base.py:18`
  - Usage: `class UserRepository(BaseRepository[User])`
  - Applicability: Create ProfileRepository, BackstoryRepository, VenueCacheRepository

- **Handler Pattern** @ `nikita/platforms/telegram/otp_handler.py`
  - Usage: Specialized handlers for telegram message flows
  - Applicability: Create OnboardingHandler for profile collection

- **Service Pattern** @ `nikita/meta_prompts/service.py`
  - Usage: MetaPromptService wraps LLM calls with templates
  - Applicability: Create BackstoryGeneratorService for scenario generation

**CoD^Σ Evidence Chain**:
```
spec_requirements ∘ codebase_patterns → implementation_tasks
Evidence: spec.md + nikita/db/repositories/base.py:18 + nikita/platforms/telegram/*_handler.py → plan.md
```

---

## Constitution Check (Article VI)

**Constitutional Authority**: Article VI (Simplicity & Anti-Abstraction)

### Pre-Design Gates

```
Gate₁: Project Count (≤3)
  Status: PASS ✓
  Count: 1 project (Nikita)
  Decision: PROCEED

Gate₂: Abstraction Layers (≤2 per concept)
  Status: PASS ✓
  Details: Handler → Service → Repository (3 layers, but consistent with existing patterns)
  Decision: PROCEED

Gate₃: Framework Trust (use directly)
  Status: PASS ✓
  Details: Using existing FastAPI, SQLAlchemy, Pydantic patterns
  Decision: PROCEED
```

**Overall Pre-Design Gate**: PASS ✓

---

## Architecture (CoD^Σ)

### Component Breakdown

**System Flow**:
```
OTP_Success → OnboardingHandler → ProfileCollection → VenueResearch → ScenarioGeneration → Selection → MetaPromptInjection
      ↓              ↓                    ↓                  ↓                 ↓              ↓              ↓
   User_Created   Questions          UserProfile       VenueCache       3_Scenarios    Backstory    Nikita_Context
```

**Dependencies** (CoD^Σ Notation):
```
OnboardingHandler ⇐ ProfileRepository ⇐ UserProfile (model)
VenueResearchService ⇐ Firecrawl_MCP ⊕ UserFallback
BackstoryGenerator ⇐ Claude_LLM ⇐ MetaPromptService
MetaPromptContext ⇐ BackstoryContext (new field)
```

**Data Flow**:
```
TelegramMessage ≫ OnboardingState ≫ ProfileData → VenueData → Scenarios → Selection → Backstory
       ↓                 ↓              ↓            ↓            ↓           ↓          ↓
   Raw_Input        Step_Track      Validated    Research     Generated   User_Choice  Persisted
```

**Modules**:
1. **nikita/platforms/telegram/onboarding/**: OnboardingHandler, ProfileCollector
2. **nikita/services/venue_research.py**: FirecrawlService, VenueCacheService
3. **nikita/services/backstory_generator.py**: BackstoryGeneratorService
4. **nikita/db/models/profile.py**: UserProfile, UserBackstory, VenueCache
5. **nikita/db/repositories/profile_repository.py**: ProfileRepository, BackstoryRepository

---

## User Story Implementation Plan

### User Story P1: Basic Profile Collection (Priority: Must-Have)

**Goal**: New users complete profile questions and receive backstory options

**Acceptance Criteria** (from spec.md):
- AC-FR001-001: Mysterious tone intro after OTP
- AC-FR002-001: 4 essential fields collected → profile saved
- AC-FR003-001: Direct 1-5 drug tolerance scale
- AC-FR009-001: Resume from last question if abandoned
- AC-FR010-001: Existing users bypass onboarding

**Implementation Approach**:
1. Create OnboardingHandler with step-based state machine
2. Create UserProfile model with 5 fields
3. Modify otp_handler.py to route to onboarding
4. Create ProfileRepository for CRUD operations

**Evidence**: Based on handler pattern at `nikita/platforms/telegram/otp_handler.py`

---

### User Story P1: Venue Research & Scenario Generation (Priority: Must-Have)

**Goal**: System researches venues and generates 3 personalized scenarios

**Acceptance Criteria** (from spec.md):
- AC-FR004-001: Firecrawl searches for real venues
- AC-FR004-002: Fallback asks user for favorite spot
- AC-FR005-001: 3 distinct scenarios with venue, context, moment, hook
- AC-FR006-001: Custom backstory option accepted

**Implementation Approach**:
1. Create VenueResearchService using Firecrawl MCP
2. Create VenueCache model for caching results
3. Create BackstoryGeneratorService using Claude LLM
4. Integrate with OnboardingHandler for scenario presentation

**Evidence**: Firecrawl MCP available in .mcp.json

---

### User Story P1: Nikita Persona Integration (Priority: Must-Have)

**Goal**: Nikita's first message references shared history

**Acceptance Criteria** (from spec.md):
- AC-FR007-001: Nikita's persona adapts to user profile
- AC-FR008-001: First message references venue and hook
- AC-FR008-002/003: Drug tolerance affects language

**Implementation Approach**:
1. Create BackstoryContext dataclass
2. Add backstory field to MetaPromptContext
3. Modify system_prompt.meta.md to inject backstory
4. Create UserBackstory model for persistence

**Evidence**: Based on MetaPromptContext at `nikita/meta_prompts/models.py:79`

---

## Tasks

**Organization**: Tasks map to user stories [US1], [US2], [US3] for SDD progressive delivery

### Phase 1: Database Layer (US-1)

#### T1.1: Create UserProfile Model
- **ID**: T1.1
- **User Story**: US-1 - Basic Profile Collection
- **Owner**: executor-agent
- **Status**: [ ] Not Started
- **Dependencies** (CoD^Σ): None
- **Estimated Complexity**: Low

**Acceptance Criteria**:
- [ ] AC-T1.1-001: UserProfile model with fields: location_city, location_country, life_stage, social_scene, primary_interest, drug_tolerance (1-5)
- [ ] AC-T1.1-002: SQLAlchemy model inherits from Base, has UUID primary key referencing users.id
- [ ] AC-T1.1-003: Migration script creates user_profiles table with proper constraints

**Implementation Notes**:
- **Pattern Evidence**: Based on `nikita/db/models/user.py` structure
- **File**: `nikita/db/models/profile.py`
- **Migration**: `migrations/versions/00XX_add_user_profiles.py`

---

#### T1.2: Create UserBackstory Model
- **ID**: T1.2
- **User Story**: US-1, US-3 - Profile + Persona Integration
- **Owner**: executor-agent
- **Status**: [ ] Not Started
- **Dependencies** (CoD^Σ): T1.1 (UserProfile must exist)
- **Estimated Complexity**: Low

**Acceptance Criteria**:
- [ ] AC-T1.2-001: UserBackstory model with fields: venue_name, venue_city, scenario_type, how_we_met, the_moment, unresolved_hook, nikita_persona_overrides (JSONB)
- [ ] AC-T1.2-002: One-to-one relationship with User (UNIQUE constraint on user_id)
- [ ] AC-T1.2-003: Migration script creates backstories table

**Implementation Notes**:
- **Pattern Evidence**: Based on `nikita/db/models/engagement.py` for JSONB fields
- **File**: `nikita/db/models/profile.py` (same file as T1.1)

---

#### T1.3: Create VenueCache Model
- **ID**: T1.3
- **User Story**: US-5 - Venue Cache & Optimization
- **Owner**: executor-agent
- **Status**: [ ] Not Started
- **Dependencies** (CoD^Σ): None (independent)
- **Estimated Complexity**: Low

**Acceptance Criteria**:
- [ ] AC-T1.3-001: VenueCache model with fields: city, scene, venues (JSONB array), fetched_at, expires_at
- [ ] AC-T1.3-002: Composite unique constraint on (city, scene)
- [ ] AC-T1.3-003: Migration script creates venue_cache table with 30-day expiry default

**Implementation Notes**:
- **Pattern Evidence**: Based on `nikita/db/models/context.py` for JSONB
- **File**: `nikita/db/models/profile.py`

---

#### T1.4: Create OnboardingState Model
- **ID**: T1.4
- **User Story**: US-1, US-4 - Profile Collection + Resilience
- **Owner**: executor-agent
- **Status**: [ ] Not Started
- **Dependencies** (CoD^Σ): T1.1 ⊥ T1.4 (independent but logically related)
- **Estimated Complexity**: Low

**Acceptance Criteria**:
- [ ] AC-T1.4-001: OnboardingState model with fields: telegram_id, current_step (enum), collected_answers (JSONB), started_at, updated_at
- [ ] AC-T1.4-002: Steps enum: LOCATION, LIFE_STAGE, SCENE, INTEREST, DRUG_TOLERANCE, VENUE_RESEARCH, SCENARIO_SELECTION, COMPLETE
- [ ] AC-T1.4-003: Delete on completion (transient state like PendingRegistration)

**Implementation Notes**:
- **Pattern Evidence**: Based on `nikita/db/models/pending_registration.py` transient pattern
- **File**: `nikita/db/models/profile.py`

---

#### T1.5: Create Repository Classes
- **ID**: T1.5
- **User Story**: US-1, US-2, US-5
- **Owner**: executor-agent
- **Status**: [ ] Not Started
- **Dependencies** (CoD^Σ): T1.1 → T1.5, T1.2 → T1.5, T1.3 → T1.5, T1.4 → T1.5
- **Estimated Complexity**: Medium

**Acceptance Criteria**:
- [ ] AC-T1.5-001: ProfileRepository with create_profile(), get_by_user_id(), update()
- [ ] AC-T1.5-002: BackstoryRepository with create(), get_by_user_id(), update()
- [ ] AC-T1.5-003: VenueCacheRepository with get_by_city_scene(), create_or_update(), is_expired()
- [ ] AC-T1.5-004: OnboardingStateRepository with get_or_create(), update_step(), delete()
- [ ] AC-T1.5-005: All repositories inherit from BaseRepository[ModelT]

**Implementation Notes**:
- **Pattern Evidence**: Based on `nikita/db/repositories/base.py:18`
- **File**: `nikita/db/repositories/profile_repository.py`

---

### Phase 2: Onboarding Handler (US-1)

#### T2.1: Create OnboardingHandler Class
- **ID**: T2.1
- **User Story**: US-1 - Basic Profile Collection
- **Owner**: executor-agent
- **Status**: [ ] Not Started
- **Dependencies** (CoD^Σ): T1.4 → T2.1, T1.5 → T2.1
- **Estimated Complexity**: High

**Acceptance Criteria**:
- [ ] AC-T2.1-001: OnboardingHandler class with handle() method routing by current_step
- [ ] AC-T2.1-002: Step handlers for each profile field with appropriate prompts
- [ ] AC-T2.1-003: Mysterious intro message: "Before we connect you... I need to know a bit about you."
- [ ] AC-T2.1-004: State saved after each step (resume capability)
- [ ] AC-T2.1-005: Validation for each field type (location, life_stage enum, scene enum, freeform text, 1-5 scale)

**Implementation Notes**:
- **Pattern Evidence**: Based on `nikita/platforms/telegram/otp_handler.py`
- **File**: `nikita/platforms/telegram/onboarding/handler.py`

---

#### T2.2: Integrate with OTP Handler
- **ID**: T2.2
- **User Story**: US-1 - Basic Profile Collection
- **Owner**: executor-agent
- **Status**: [ ] Not Started
- **Dependencies** (CoD^Σ): T2.1 → T2.2
- **Estimated Complexity**: Medium

**Acceptance Criteria**:
- [ ] AC-T2.2-001: After OTP verification success, check if user has profile
- [ ] AC-T2.2-002: If no profile, route to OnboardingHandler instead of welcome message
- [ ] AC-T2.2-003: If profile exists, send normal welcome message
- [ ] AC-T2.2-004: Modify webhook routing to detect ongoing onboarding state

**Implementation Notes**:
- **Pattern Evidence**: Modify `nikita/platforms/telegram/otp_handler.py:76-82`
- **Files**: `otp_handler.py`, `nikita/api/routes/telegram.py`

---

#### T2.3: Resume Logic for Abandoned Onboarding
- **ID**: T2.3
- **User Story**: US-1, US-4 - Resilience
- **Owner**: executor-agent
- **Status**: [ ] Not Started
- **Dependencies** (CoD^Σ): T2.1 → T2.3
- **Estimated Complexity**: Medium

**Acceptance Criteria**:
- [ ] AC-T2.3-001: On new message, check OnboardingState for telegram_id
- [ ] AC-T2.3-002: If incomplete onboarding exists, prompt to continue from last step
- [ ] AC-T2.3-003: "skip" or "I don't want to" detection → apply generic backstory
- [ ] AC-T2.3-004: Progress preserved for 24+ hours (no auto-expiry)

**Implementation Notes**:
- **Pattern Evidence**: Similar to PendingRegistration but no expiry
- **File**: `nikita/platforms/telegram/onboarding/handler.py`

---

### Phase 3: Venue Research (US-2)

#### T3.1: Create VenueResearchService
- **ID**: T3.1
- **User Story**: US-2 - Venue Research & Scenario Generation
- **Owner**: executor-agent
- **Status**: [ ] Not Started
- **Dependencies** (CoD^Σ): T1.3 → T3.1, T1.5 → T3.1
- **Estimated Complexity**: High

**Acceptance Criteria**:
- [ ] AC-T3.1-001: VenueResearchService class with research_venues(city, scene) method
- [ ] AC-T3.1-002: Uses Firecrawl MCP firecrawl_search for "{city} best {scene} venues"
- [ ] AC-T3.1-003: Parses results to extract venue names, descriptions, vibes
- [ ] AC-T3.1-004: Caches results in VenueCache for 30 days
- [ ] AC-T3.1-005: Returns structured list of venues with name, description, vibe

**Implementation Notes**:
- **Pattern Evidence**: Firecrawl MCP available in .mcp.json
- **File**: `nikita/services/venue_research.py`

---

#### T3.2: Implement Venue Research Fallback
- **ID**: T3.2
- **User Story**: US-2, US-4 - Resilience
- **Owner**: executor-agent
- **Status**: [ ] Not Started
- **Dependencies** (CoD^Σ): T3.1 → T3.2
- **Estimated Complexity**: Medium

**Acceptance Criteria**:
- [ ] AC-T3.2-001: On Firecrawl timeout/error, fallback to user prompt within 2 seconds
- [ ] AC-T3.2-002: Prompt: "What's your favorite spot in {city}?"
- [ ] AC-T3.2-003: Accept user-provided venue and use for scenarios
- [ ] AC-T3.2-004: Log fallback usage for monitoring

**Implementation Notes**:
- **File**: `nikita/services/venue_research.py`

---

#### T3.3: Integrate Venue Cache
- **ID**: T3.3
- **User Story**: US-5 - Venue Cache & Optimization
- **Owner**: executor-agent
- **Status**: [ ] Not Started
- **Dependencies** (CoD^Σ): T3.1 → T3.3
- **Estimated Complexity**: Low

**Acceptance Criteria**:
- [ ] AC-T3.3-001: Check cache before calling Firecrawl
- [ ] AC-T3.3-002: If cache hit and not expired, return cached venues
- [ ] AC-T3.3-003: If cache miss or expired, fetch and update cache
- [ ] AC-T3.3-004: Cache key: (city.lower(), scene.lower())

**Implementation Notes**:
- **File**: `nikita/services/venue_research.py`

---

### Phase 4: Backstory Generation (US-2, US-3)

#### T4.1: Create BackstoryGeneratorService
- **ID**: T4.1
- **User Story**: US-2 - Scenario Generation
- **Owner**: executor-agent
- **Status**: [ ] Not Started
- **Dependencies** (CoD^Σ): T3.1 → T4.1 (needs venues)
- **Estimated Complexity**: High

**Acceptance Criteria**:
- [ ] AC-T4.1-001: BackstoryGeneratorService class with generate_scenarios(profile, venues) method
- [ ] AC-T4.1-002: Uses Claude LLM to generate 3 distinct scenarios
- [ ] AC-T4.1-003: Each scenario has: venue, context (Nikita's reason there), the_moment, unresolved_hook
- [ ] AC-T4.1-004: Scenarios vary by tone: romantic, intellectual, chaotic
- [ ] AC-T4.1-005: Template prompt includes user profile for personalization

**Implementation Notes**:
- **Pattern Evidence**: Based on `nikita/meta_prompts/service.py` LLM pattern
- **File**: `nikita/services/backstory_generator.py`

---

#### T4.2: Custom Backstory Validation
- **ID**: T4.2
- **User Story**: US-2 - Custom Backstory Option
- **Owner**: executor-agent
- **Status**: [ ] Not Started
- **Dependencies** (CoD^Σ): T4.1 → T4.2
- **Estimated Complexity**: Medium

**Acceptance Criteria**:
- [ ] AC-T4.2-001: Accept freeform text for custom backstory
- [ ] AC-T4.2-002: Use LLM to extract: venue, the_moment, hook from user text
- [ ] AC-T4.2-003: Enhance user text with Nikita-style details
- [ ] AC-T4.2-004: Validate minimum content (venue or location mentioned)

**Implementation Notes**:
- **File**: `nikita/services/backstory_generator.py`

---

#### T4.3: Scenario Presentation in Onboarding
- **ID**: T4.3
- **User Story**: US-2 - Scenario Selection
- **Owner**: executor-agent
- **Status**: [ ] Not Started
- **Dependencies** (CoD^Σ): T4.1 → T4.3, T2.1 → T4.3
- **Estimated Complexity**: Medium

**Acceptance Criteria**:
- [ ] AC-T4.3-001: Present 3 scenarios + custom option in Telegram message
- [ ] AC-T4.3-002: Use numbered options (1, 2, 3, 4) for selection
- [ ] AC-T4.3-003: Parse user selection and store in OnboardingState
- [ ] AC-T4.3-004: On "4" (custom), prompt for freeform text

**Implementation Notes**:
- **File**: `nikita/platforms/telegram/onboarding/handler.py`

---

### Phase 5: MetaPrompt Integration (US-3)

#### T5.1: Create BackstoryContext Dataclass
- **ID**: T5.1
- **User Story**: US-3 - Nikita Persona Integration
- **Owner**: executor-agent
- **Status**: [ ] Not Started
- **Dependencies** (CoD^Σ): T1.2 (BackstoryModel)
- **Estimated Complexity**: Low

**Acceptance Criteria**:
- [ ] AC-T5.1-001: BackstoryContext dataclass with fields from UserBackstory model
- [ ] AC-T5.1-002: Include persona_overrides for adaptive traits
- [ ] AC-T5.1-003: Factory method from_model(UserBackstory) for conversion

**Implementation Notes**:
- **Pattern Evidence**: Based on `nikita/meta_prompts/models.py:79` MetaPromptContext
- **File**: `nikita/meta_prompts/models.py`

---

#### T5.2: Add Backstory to MetaPromptContext
- **ID**: T5.2
- **User Story**: US-3 - Nikita Persona Integration
- **Owner**: executor-agent
- **Status**: [ ] Not Started
- **Dependencies** (CoD^Σ): T5.1 → T5.2
- **Estimated Complexity**: Medium

**Acceptance Criteria**:
- [ ] AC-T5.2-001: Add backstory: BackstoryContext | None field to MetaPromptContext
- [ ] AC-T5.2-002: Load backstory in context builder when user has backstory
- [ ] AC-T5.2-003: Default to None for users without backstory (existing users)

**Implementation Notes**:
- **File**: `nikita/meta_prompts/models.py`

---

#### T5.3: Update System Prompt Template
- **ID**: T5.3
- **User Story**: US-3 - Backstory Injection
- **Owner**: executor-agent
- **Status**: [ ] Not Started
- **Dependencies** (CoD^Σ): T5.2 → T5.3
- **Estimated Complexity**: Medium

**Acceptance Criteria**:
- [ ] AC-T5.3-001: Add BACKSTORY section to system_prompt.meta.md
- [ ] AC-T5.3-002: Include: venue, how_we_met, the_moment, unresolved_hook
- [ ] AC-T5.3-003: Conditional rendering: only if backstory exists
- [ ] AC-T5.3-004: First message instruction: reference venue and hook

**Implementation Notes**:
- **File**: `nikita/meta_prompts/templates/system_prompt.meta.md`

---

#### T5.4: Persona Adaptation Logic
- **ID**: T5.4
- **User Story**: US-3 - Persona Adaptation
- **Owner**: executor-agent
- **Status**: [ ] Not Started
- **Dependencies** (CoD^Σ): T5.2 → T5.4
- **Estimated Complexity**: Medium

**Acceptance Criteria**:
- [ ] AC-T5.4-001: Map life_stage to Nikita occupation (tech→hacker, artist→digital artist, etc.)
- [ ] AC-T5.4-002: Map social_scene to Nikita interests (techno→DJ hobby, art→gallery hopper)
- [ ] AC-T5.4-003: Map drug_tolerance to vice_profile intensity
- [ ] AC-T5.4-004: Store persona_overrides in UserBackstory.nikita_persona_overrides

**Implementation Notes**:
- **File**: `nikita/services/backstory_generator.py`

---

### Phase 6: Testing (All US)

#### T6.1: Database Model Tests
- **ID**: T6.1
- **User Story**: US-1, US-2, US-5
- **Owner**: executor-agent
- **Status**: [ ] Not Started
- **Dependencies** (CoD^Σ): T1.1-T1.5 (all models)
- **Estimated Complexity**: Medium

**Acceptance Criteria**:
- [ ] AC-T6.1-001: Unit tests for UserProfile, UserBackstory, VenueCache, OnboardingState models
- [ ] AC-T6.1-002: Repository tests for CRUD operations
- [ ] AC-T6.1-003: Test data fixtures for profile scenarios
- [ ] AC-T6.1-004: 90%+ coverage for new models

**Implementation Notes**:
- **Files**: `tests/db/models/test_profile.py`, `tests/db/repositories/test_profile_repository.py`

---

#### T6.2: Onboarding Handler Tests
- **ID**: T6.2
- **User Story**: US-1, US-4
- **Owner**: executor-agent
- **Status**: [ ] Not Started
- **Dependencies** (CoD^Σ): T2.1-T2.3 (handler complete)
- **Estimated Complexity**: High

**Acceptance Criteria**:
- [ ] AC-T6.2-001: Test each step of onboarding flow
- [ ] AC-T6.2-002: Test resume from abandoned state
- [ ] AC-T6.2-003: Test skip/opt-out detection
- [ ] AC-T6.2-004: Test existing user bypass
- [ ] AC-T6.2-005: 85%+ coverage for handler

**Implementation Notes**:
- **File**: `tests/platforms/telegram/onboarding/test_handler.py`

---

#### T6.3: Service Integration Tests
- **ID**: T6.3
- **User Story**: US-2, US-3
- **Owner**: executor-agent
- **Status**: [ ] Not Started
- **Dependencies** (CoD^Σ): T3.1-T3.3, T4.1-T4.3 (services complete)
- **Estimated Complexity**: High

**Acceptance Criteria**:
- [ ] AC-T6.3-001: Test VenueResearchService with mock Firecrawl
- [ ] AC-T6.3-002: Test fallback when Firecrawl fails
- [ ] AC-T6.3-003: Test BackstoryGeneratorService with mock LLM
- [ ] AC-T6.3-004: Test cache hit/miss scenarios
- [ ] AC-T6.3-005: 80%+ coverage for services

**Implementation Notes**:
- **Files**: `tests/services/test_venue_research.py`, `tests/services/test_backstory_generator.py`

---

#### T6.4: E2E Onboarding Test
- **ID**: T6.4
- **User Story**: US-1, US-2, US-3
- **Owner**: executor-agent
- **Status**: [ ] Not Started
- **Dependencies** (CoD^Σ): All P1 tasks complete
- **Estimated Complexity**: High

**Acceptance Criteria**:
- [ ] AC-T6.4-001: E2E test: OTP → profile → venues → scenarios → selection → first message
- [ ] AC-T6.4-002: Verify Nikita's first message contains venue and hook
- [ ] AC-T6.4-003: Verify profile persists across sessions
- [ ] AC-T6.4-004: Test with real Firecrawl (optional, can mock)

**Implementation Notes**:
- **File**: `tests/e2e/test_onboarding_flow.py`

---

## Dependencies

### Task Dependency Graph (CoD^Σ)
```
Phase 1 (Database):
T1.1 ⊥ T1.3 ⊥ T1.4        (independent, parallel)
T1.1 → T1.2               (backstory needs profile)
{T1.1, T1.2, T1.3, T1.4} → T1.5  (repos need models)

Phase 2 (Handler):
T1.5 → T2.1 → T2.2        (sequential)
T2.1 → T2.3               (resume needs handler)

Phase 3 (Venue Research):
T1.5 → T3.1 → T3.2        (sequential)
T3.1 → T3.3               (cache after research)

Phase 4 (Backstory):
T3.1 → T4.1 → T4.2        (sequential)
{T4.1, T2.1} → T4.3       (presentation needs both)

Phase 5 (MetaPrompt):
T1.2 → T5.1 → T5.2 → T5.3 (sequential chain)
T5.2 → T5.4               (adaptation needs context)

Phase 6 (Testing):
All implementation → T6.x  (tests after code)
```

**Critical Path**: T1.1 → T1.5 → T2.1 → T4.3 → T5.3 → T6.4

**Parallelizable**: {T1.1, T1.3, T1.4} can run in parallel

### External Dependencies
- **Firecrawl MCP**: Available in .mcp.json - venue research
- **Claude LLM**: Available via Anthropic API - scenario generation
- **Supabase**: Database migrations via Supabase MCP

---

## Risks (CoD^Σ)

### Risk 1: Firecrawl Rate Limiting
- **Likelihood (p)**: 0.3 (Medium-Low)
- **Impact**: 4 (Medium)
- **Risk Score**: r = 1.2
- **Mitigation**:
  - Venue cache reduces API calls
  - User fallback ensures flow continues
  - Rate limiting on our end if needed

### Risk 2: LLM Scenario Quality Variance
- **Likelihood (p)**: 0.25 (Low)
- **Impact**: 5 (Medium)
- **Risk Score**: r = 1.25
- **Mitigation**:
  - Template prompt with strict structure
  - Validation of scenario components
  - Custom option as fallback

### Risk 3: Complex State Machine in Handler
- **Likelihood (p)**: 0.35 (Medium)
- **Impact**: 4 (Medium)
- **Risk Score**: r = 1.4
- **Mitigation**:
  - Clear step enum with transitions
  - Comprehensive unit tests per step
  - Logging for debugging

---

## Verification (CoD^Σ)

### Test Strategy
```
Unit → Integration → E2E  (test pyramid)
  ↓         ↓          ↓
Fast     Medium     Slow

Coverage: ∑(AC_tested) / ∑(AC_total) ≥ 0.85
```

### AC Coverage Map
```
AC-FR001-001 → test_handler.py:test_mysterious_intro ✓
AC-FR002-001 → test_handler.py:test_profile_completion ✓
AC-FR003-001 → test_handler.py:test_drug_tolerance_scale ✓
AC-FR004-001 → test_venue_research.py:test_firecrawl_search ✓
AC-FR004-002 → test_venue_research.py:test_fallback ✓
AC-FR005-001 → test_backstory_generator.py:test_scenario_generation ✓
AC-FR006-001 → test_backstory_generator.py:test_custom_backstory ✓
AC-FR007-001 → test_backstory_generator.py:test_persona_adaptation ✓
AC-FR008-001 → test_meta_prompts.py:test_backstory_injection ✓
AC-FR009-001 → test_handler.py:test_resume_flow ✓
AC-FR010-001 → test_handler.py:test_existing_user_bypass ✓
```

### Verification Command
```bash
# Run all tests
pytest tests/ -v --cov=nikita --cov-report=term-missing

# Specific feature tests
pytest tests/platforms/telegram/onboarding/ tests/services/ -v
```

---

## Progress Tracking (CoD^Σ)

**Completion Metrics**:
```
Total Tasks (N):     17
Completed (X):       0
In Progress (Y):     0
Blocked (Z):         0

Progress Ratio:      0/17 = 0%
```

**Last Updated**: 2025-12-15
**Next Review**: After Phase 1 complete

---

## Notes

**Key Design Decisions**:
1. **Personalization Guide (not persona)**: Per user clarification, mysterious wizard tone, not a character
2. **Direct 1-5 Scale**: Explicit drug tolerance question per user preference
3. **Firecrawl MCP**: Already available, no new API key needed
4. **Resume Flow**: State persisted, no auto-expiry

**Dependencies on Existing Code**:
- Modify `otp_handler.py` to route to onboarding
- Extend `MetaPromptContext` with backstory
- Follow existing handler, repository, service patterns

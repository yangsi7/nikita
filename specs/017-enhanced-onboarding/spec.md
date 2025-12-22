---
feature: 017-enhanced-onboarding
created: 2025-12-15
status: Draft
priority: P1
technology_agnostic: true
constitutional_compliance:
  article_iv: specification_first
---

# Feature Specification: Enhanced Onboarding with Personalization Guide

**IMPORTANT**: This specification is TECHNOLOGY-AGNOSTIC. Focus on WHAT and WHY, not HOW.

---

## Summary

After OTP verification, new Telegram users currently enter chat with Nikita who has zero context about them. This breaks immersion - users should feel like they're resuming contact with someone they met once before, not starting from scratch.

This feature introduces a **personalization flow** that collects user profile information, researches real venues in their city, generates "how we met" backstory scenarios, and adapts Nikita's persona to match the user's profile.

**Problem Statement**: New users experience an immersion-breaking start where Nikita has no context about who they are, their location, interests, or how they "met."

**Value Proposition**: Users feel immediately engaged with a personalized Nikita who references their shared history, location, and interests - creating the illusion of a pre-existing relationship.

### CoD^Σ Overview

**System Model**:
```
User → Personalization → Backstory → Nikita_Context
  ↓         ↓              ↓            ↓
Profile  Scenarios    Selection    Immersion

Requirements: R := {FR_i} ⊕ {NFR_j}
Flow: OTP_success → Profile_collection → Venue_research → Scenario_gen → Selection → Chat_init
```

**Value Chain**:
```
Problem ≫ Solution ≫ Implementation → Value_Delivered
  ↓         ↓            ↓               ↓
No_context  Personalize  Profile+Backstory  Immersive_start
```

---

## Functional Requirements

**Current [NEEDS CLARIFICATION] Count**: 0 / 3

### FR-001: Personalization Guide Flow
System MUST present a personalization guide to new users after OTP verification.

**Rationale**: Collects user information to generate personalized backstory without breaking Nikita's character.
**Priority**: Must Have

**Details**:
- Guide uses mysterious, teasing tone: "Before we connect you... I need to know a bit about you."
- NOT a character persona (no name like "Cupid") - a welcoming wizard experience
- Frame: Personalization, not matchmaking

### FR-002: Essential Profile Collection
System MUST collect essential profile fields through structured prompts.

**Rationale**: Minimum data required to generate meaningful backstory scenarios.
**Priority**: Must Have

**Fields**:
- `location`: City and country
- `life_stage`: Student | Working | Creative | Other
- `social_scene`: Techno/Club | Art/Gallery | Music/Concert | Startup/Work | Academic | Casual
- `primary_interest`: Freeform text (one main passion)

### FR-003: Drug Tolerance Collection
System MUST collect drug tolerance using a direct 1-5 scale.

**Rationale**: Affects Nikita's edge level - how explicit she is about party culture, substances, all-nighters.
**Priority**: Must Have

**Scale**:
- 1: Mild alcohol references only
- 3: Moderate party culture references
- 5: Full vice integration (party drugs, all-nighters, explicit edge)

### FR-004: Venue Research Integration
System MUST research real venues in the user's city and social scene.

**Rationale**: Authentic venue names create believable "how we met" scenarios.
**Priority**: Must Have

**Details**:
- Primary: Web search for "{city} {scene} venues"
- Fallback: Ask user directly: "What's your favorite spot in {city}?"
- Cache results to avoid repeated lookups

### FR-005: Scenario Generation
System MUST generate 3 distinct "how we met" backstory scenarios.

**Rationale**: Gives users choice while ensuring quality personalization.
**Priority**: Must Have

**Each scenario includes**:
- Venue: Specific real place (or plausible description)
- Context: Why Nikita was there (adapted occupation/interest)
- The Moment: 1-2 memorable details (conversation topic, shared drink, funny incident)
- Hook: Something unresolved that can be referenced later

### FR-006: Custom Backstory Option
System MUST allow users to write their own backstory.

**Rationale**: Power users may want full control over the narrative.
**Priority**: Must Have

**Details**:
- Fourth option alongside 3 generated scenarios
- System validates and enhances user-provided backstory
- Extracts key details for Nikita's context

### FR-007: Nikita Persona Adaptation
System MUST adapt Nikita's surface traits to match user profile.

**Rationale**: Creates coherent shared history and relatable connection points.
**Priority**: Must Have

**Constant Traits** (never change):
- ADHD-adjacent cognition (tangential, multi-threaded)
- Creative intelligence (pattern recognition, artistic sensibility)
- Edgy authenticity (dark humor, boundary-testing)
- Slight chaos (disorganized, double-books, impulsive)

**Adaptive Traits**:
| User Profile | Nikita Adaptation |
|--------------|-------------------|
| Tech worker | Security researcher / hacker |
| Artist | Digital artist / NFT creator |
| Student | Grad student (comp sci, philosophy) |
| Techno scene | DJ hobby, knows local clubs |
| Art scene | Gallery hopper, knows curators |
| Drug tolerance 1 | Mild references only |
| Drug tolerance 5 | Full vice integration |

### FR-008: Backstory Context Injection
System MUST inject backstory details into Nikita's first message and subsequent context.

**Rationale**: Creates illusion of pre-existing relationship.
**Priority**: Must Have

**Details**:
- Nikita's first message references: venue, shared moment, unresolved hook
- Example: "Hey you. Still thinking about that conversation we had at Hive... you said something about [extracted detail]. What was that about?"

### FR-009: Onboarding State Persistence
System MUST save onboarding progress and resume where user left off.

**Rationale**: Users may abandon mid-flow; don't make them restart.
**Priority**: Must Have

**Details**:
- Save after each question answered
- On next message, detect incomplete onboarding and prompt to continue
- Track: current step, collected answers, timestamp

### FR-010: Existing User Bypass
System MUST bypass onboarding for users who already have a profile and backstory.

**Rationale**: Don't re-onboard existing users.
**Priority**: Must Have

### FR-011: Mandatory Completion (No Skip)
System MUST NOT allow users to skip or bypass onboarding. Personalization is required for the product to function.

**Rationale**: Without profile and backstory data, MetaPromptService cannot generate personalized system prompts. Users would receive generic, immersion-breaking responses that defeat the core product value.
**Priority**: Must Have

**Details**:
- Skip phrases ("skip", "later", "no thanks") trigger encouragement, not bypass
- Same question is re-presented after skip attempt
- Step-specific encouraging messages maintain engagement
- Profile gate in MessageHandler redirects incomplete users back to onboarding

### FR-012: Profile Gate Check
System MUST check for complete profile and backstory before allowing text agent conversations.

**Rationale**: Prevents users who somehow bypassed onboarding from getting generic responses.
**Priority**: Must Have

**Details**:
- MessageHandler checks profile_repository and backstory_repository
- If either is missing, redirect to OnboardingHandler
- Existing users with data proceed directly to text agent

### FR-013: Graphiti Memory Loading
System MUST load user facts, threads, and thoughts from Graphiti knowledge graph into prompt context.

**Rationale**: Without memory integration, Nikita cannot reference past conversations, facts learned about the user, or ongoing conversation threads - breaking immersion and personalization.
**Priority**: Must Have

**Details**:
- MetaPromptService._load_context() MUST call Graphiti to load:
  - `user_facts`: Facts about the user extracted from past conversations (e.g., "works in finance", "has a cat named Luna")
  - `open_threads`: Active conversation threads awaiting resolution (e.g., "user mentioned job interview next week")
  - `active_thoughts`: Nikita's simulated thoughts from between conversations
- Memory search should be relevant to current user message
- Graceful degradation if Graphiti unavailable (empty lists, not failure)

### FR-014: Conversation Summaries Integration
System MUST load daily and weekly conversation summaries into prompt context.

**Rationale**: Summaries provide compressed historical context enabling Nikita to reference past conversations without loading full transcripts.
**Priority**: Must Have

**Details**:
- Load from `daily_summaries` table in Supabase
- `today_summaries`: Summaries from current day's conversations
- `week_summaries`: Summaries from past 7 days
- Format for prompt injection: concise bullet points

### FR-015: Per-Conversation Prompt Generation
System MUST generate fresh personalized prompts for each conversation turn using current memory context.

**Rationale**: Prompts must reflect latest facts, threads, and user state - stale prompts lead to inconsistent Nikita behavior.
**Priority**: Must Have

**Details**:
- No prompt caching (initial implementation)
- Each message triggers: context load → memory query → prompt generation
- Generated prompts logged to `generated_prompts` table with token count
- Target latency: <350ms total (context: 100ms, Graphiti: 100ms, prompt gen: 150ms)

---

## Non-Functional Requirements

### Performance
- Profile collection flow completes in ≤5 messages
- Venue research completes in <5 seconds
- Scenario generation completes in <10 seconds

### Security
- Profile data stored securely (encrypted at rest)
- No PII exposed in logs
- Drug tolerance treated as sensitive data

### Scalability
- Venue cache prevents redundant API calls
- Support concurrent onboarding for multiple users

### Availability
- Fallback to user-provided venues if web search fails
- Graceful degradation if scenario generation fails (use generic template)

---

## User Stories (CoD^Σ)

**Priority Model**:
```
P1 ⇒ MVP (core onboarding flow)
P2 ⇒ P1.enhance (research + rich scenarios)
P3 ⇒ future (conversational enrichment, Portal)

Independence: ∀S_i, S_j ∈ Stories : S_i ⊥ S_j
```

---

### US-1: Basic Profile Collection (Priority: P1 - Must-Have)
```
New user → complete profile questions → receive personalized backstory options
```
**Why P1**: Core MVP functionality - system unusable without profile collection

**Acceptance Criteria**:
- **AC-FR001-001**: Given new user after OTP verification, When onboarding starts, Then personalization guide presents first question with mysterious tone
- **AC-FR002-001**: Given user in onboarding, When all 4 essential fields collected, Then profile is saved and flow proceeds to scenario selection
- **AC-FR003-001**: Given user in onboarding, When drug tolerance question presented, Then scale is explicit 1-5 with clear descriptions
- **AC-FR009-001**: Given user abandons after 2 questions, When they return, Then flow resumes from question 3 (not restart)
- **AC-FR010-001**: Given existing user with profile, When they message, Then onboarding is bypassed entirely

**Independent Test**: Complete onboarding flow end-to-end, verify profile persists across sessions
**Dependencies**: None

---

### US-2: Venue Research & Scenario Generation (Priority: P1 - Must-Have)
```
User with profile → system researches venues → 3 personalized scenarios presented
```
**Why P1**: Core value proposition - scenarios with real venues create immersion

**Acceptance Criteria**:
- **AC-FR004-001**: Given user profile with location+scene, When profile complete, Then system searches for real venues in their city
- **AC-FR004-002**: Given venue search fails, When user prompted for favorite spot, Then their input is used for scenarios
- **AC-FR005-001**: Given venue research complete, When scenarios generated, Then 3 distinct options presented with venue, context, moment, hook
- **AC-FR006-001**: Given 3 scenarios presented, When user selects "custom", Then freeform text input accepted and validated

**Independent Test**: Provide profile with "Zurich" + "Techno", verify real Zurich club names appear in scenarios
**Dependencies**: US-1 complete

---

### US-3: Nikita Persona Integration (Priority: P1 - Must-Have)
```
User selects backstory → Nikita's first message references shared history
```
**Why P1**: Payoff of entire onboarding - immersive first interaction

**Acceptance Criteria**:
- **AC-FR007-001**: Given user is tech worker, When backstory selected, Then Nikita's adapted persona reflects compatible occupation
- **AC-FR008-001**: Given backstory with venue "Hive" and hook "unfinished debate", When Nikita sends first message, Then message references both elements
- **AC-FR008-002**: Given drug tolerance = 1, When Nikita references partying, Then language is mild (no explicit drug references)
- **AC-FR008-003**: Given drug tolerance = 5, When Nikita references partying, Then full vice language permitted

**Independent Test**: Complete onboarding, verify Nikita's first message contains backstory venue name and hook
**Dependencies**: US-1 and US-2 complete

---

### US-4: Onboarding Resilience (Priority: P2 - Important)
```
User experiences errors or abandonment → system handles gracefully
```
**Why P2**: Improves P1 reliability but not blocking for MVP demo

**Acceptance Criteria**:
- **AC-FR004-003**: Given venue search timeout, When fallback triggered, Then user asked for favorite venue within 2 seconds
- **AC-FR009-002**: Given user returns after 24 hours, When onboarding incomplete, Then progress still preserved
- **AC-FR009-003**: Given user explicitly says "skip" or "I don't want to", When detected, Then encouraging message sent and same question re-asked (personalization is mandatory)

**Independent Test**: Simulate network failure during venue search, verify fallback works
**Dependencies**: US-1 complete

---

### US-5: Venue Cache & Optimization (Priority: P2 - Important)
```
Multiple users in same city/scene → venue research cached
```
**Why P2**: Reduces API costs and latency, not blocking MVP

**Acceptance Criteria**:
- **AC-FR004-004**: Given user A researched "Zurich Techno" yesterday, When user B has same profile, Then cached venues used (no new API call)
- **AC-FR004-005**: Given venue cache expired (30 days), When new user triggers research, Then fresh results fetched and cached

**Independent Test**: Two users with "Berlin Techno", second user gets instant venue results
**Dependencies**: US-2 complete

---

### US-6: Portal Onboarding (Priority: P3 - Future)
```
Portal user → web-based personalization flow
```
**Why P3**: Future channel - Telegram is priority

**Acceptance Criteria**:
- **AC-FR001-002**: Given Portal user, When onboarding initiated, Then web UI presents same questions as Telegram

**Independent Test**: Complete onboarding via Portal web interface
**Dependencies**: US-1, US-2, US-3 complete

---

### US-7: Memory Integration for Personalized Prompts (Priority: P1 - Must-Have)
```
User sends message → system loads memory → generates personalized prompt → Nikita responds with context
```
**Why P1**: Core value proposition - Nikita must remember past conversations and facts about the user

**Acceptance Criteria**:
- **AC-FR013-001**: Given user has past conversations with extracted facts, When new message received, Then MetaPromptService loads user_facts from Graphiti into prompt context
- **AC-FR013-002**: Given user has open conversation threads, When prompt generated, Then open_threads are included in context (e.g., "job interview next week")
- **AC-FR013-003**: Given Graphiti is unavailable, When prompt generation attempted, Then system degrades gracefully (empty memory, not failure)
- **AC-FR014-001**: Given user has daily summaries, When prompt generated, Then today_summaries and week_summaries loaded from Supabase
- **AC-FR015-001**: Given any user message, When processed by text agent, Then fresh prompt generated (no caching)
- **AC-FR015-002**: Given prompt generated, When logged to generated_prompts table, Then token_count > 0 and includes memory context

**Independent Test**:
1. Have multi-turn conversation with new facts extracted
2. Verify facts appear in next conversation's prompt context
3. Check generated_prompts table shows increasing context

**Dependencies**: US-1, US-2, US-3 complete (user must have profile/backstory)

---

## Intelligence Evidence

**Constitutional Requirement**: Article II (Evidence-Based Reasoning)

### Queries Executed

```bash
# Existing registration flow
project-intel.mjs --search "registration|otp|onboarding" --type py --json

# Meta-prompt context structure
project-intel.mjs --symbols nikita/meta_prompts/models.py --json

# User model structure
project-intel.mjs --symbols nikita/db/models/user.py --json
```

### Findings

**Related Features**:
- `nikita/platforms/telegram/otp_handler.py:76-82` - Current post-OTP welcome message (extension point)
- `nikita/meta_prompts/models.py:78-189` - MetaPromptContext (add BackstoryContext)
- `nikita/db/models/user.py:32-148` - User model (add profile relationship)

**Existing Patterns**:
- Repository pattern: `nikita/db/repositories/*.py` (follow for ProfileRepository)
- Handler pattern: `nikita/platforms/telegram/*_handler.py` (follow for OnboardingHandler)
- Service pattern: Settings-driven config for external APIs

### CoD^Σ Trace

```
Discovery_plan ≫ user_clarifications ∘ codebase_exploration → requirements
Evidence: plans/017-enhanced-onboarding-discovery.md, nikita/platforms/telegram/otp_handler.py:76
```

---

## Scope

### In-Scope Features
- Telegram-based personalization flow for new users
- Essential profile collection (4 fields) + drug tolerance (1-5 scale)
- Web-based venue research with user fallback
- 3 scenario generation + custom option
- Nikita persona adaptation based on profile
- Backstory injection into first message and ongoing context
- Onboarding state persistence (resume where left off)

### Out-of-Scope
- Portal onboarding (future P3)
- Retroactive onboarding for existing users
- Voice messages + transcription (separate feature)
- Complete personality theory implementation
- Conversational enrichment phase (future enhancement)

### Future Phases
- **Phase 2**: Conversational enrichment (optional deeper profiling)
- **Phase 3**: Portal web onboarding
- **Phase 4**: Retroactive opt-in onboarding for existing users

---

## Constraints

### Business Constraints
- Telegram-first (primary platform)
- New users only (existing users unaffected)
- Must integrate with existing OTP flow

### User Constraints
- Mobile Telegram users (UI must work in chat)
- Non-technical users (simple language, no jargon)
- International users (support any city)

### Regulatory Constraints
- Drug tolerance is sensitive data (treat accordingly)
- Location data stored securely
- Personalization is mandatory - no skip/opt-out option (core product requirement)

---

## Risks & Mitigations (CoD^Σ)

**Risk Model**:
```
r := p × impact
p ∈ [0,1], impact ∈ [1,10]
```

### Risk 1: Venue Research Fails
**Likelihood (p)**: 0.3 (Medium-Low)
**Impact**: 5 (Medium)
**Risk Score**: r = 1.5
**Mitigation**:
```
Risk → Detect(timeout/error) → Fallback(ask user) → Resolve(user-provided venues)
```
- Ask user: "What's your favorite spot in {city}?"
- Graceful degradation maintains flow

### Risk 2: Scenario Generation Produces Low-Quality Content
**Likelihood (p)**: 0.2 (Low)
**Impact**: 6 (Medium-High)
**Risk Score**: r = 1.2
**Mitigation**:
```
Risk → Detect(validation) → Fallback(template) → Resolve(generic + venue)
```
- Fallback to template-based scenarios with user's venue
- Always include one "custom" option

### Risk 3: User Abandons Onboarding
**Likelihood (p)**: 0.4 (Medium)
**Impact**: 3 (Low)
**Risk Score**: r = 1.2
**Mitigation**:
```
Risk → Detect(incomplete state) → Resume(next message) → Resolve(continue flow)
```
- Persist state after each question
- Resume on next message

### Risk 4: Drug Tolerance Question Offends User
**Likelihood (p)**: 0.15 (Low)
**Impact**: 4 (Medium)
**Risk Score**: r = 0.6
**Mitigation**:
```
Risk → Prevent(framing) → Encourage_continue → Rephrase_if_needed
```
- Frame as "edge level" or "party comfort"
- Send encouraging message if user hesitates (personalization is mandatory)
- Rephrase question with softer framing if needed

---

## Success Metrics

### User-Centric Metrics
- 80%+ of new users complete onboarding (don't abandon)
- User satisfaction with Nikita's first message > 4/5
- Users report feeling "like they already know Nikita"

### Technical Metrics
- Profile collection completes in ≤5 messages
- Venue research success rate > 90% (with fallback)
- Scenario generation latency < 10 seconds

### Business Metrics
- Increased engagement in first 24 hours (vs. non-personalized)
- Higher retention at Day 7 for personalized users
- Reduced "confused first message" support tickets

---

## Open Questions

All questions resolved via user clarification:

- [x] **Q1**: Onboarding persona vs. guide
  - **Answer**: Personalization guide/wizard (NOT a character persona)

- [x] **Q2**: Drug tolerance question explicitness
  - **Answer**: Direct 1-5 scale

- [x] **Q3**: Intro tone
  - **Answer**: Mysterious tease: "Before we connect you..."

- [x] **Q4**: Abandonment handling
  - **Answer**: Resume where left off

---

## Stakeholders

**Owner**: Product (Simon)
**Created By**: Claude (SDD workflow)
**Reviewers**: Engineering, Product
**Informed**: Design

---

## Approvals

- [ ] **Product Owner**: Simon - [pending]
- [ ] **Engineering Lead**: [pending]

---

## Specification Checklist

**Before Planning**:
- [x] All [NEEDS CLARIFICATION] resolved (0/3)
- [x] All user stories have ≥2 acceptance criteria
- [x] All user stories have priority (P1, P2, P3)
- [x] All user stories have independent test criteria
- [x] P1 stories define MVP scope (US-1, US-2, US-3)
- [x] No technology implementation details in spec
- [x] Intelligence evidence provided (CoD^Σ traces)
- [ ] Stakeholder approvals obtained

**Status**: Draft - Ready for Review

---

**Version**: 1.2
**Last Updated**: 2025-12-22
**Changes in 1.2**: Added FR-013 (Graphiti Memory Loading), FR-014 (Conversation Summaries), FR-015 (Per-Conversation Prompt Generation); Added US-7 (Memory Integration) with 6 acceptance criteria
**Changes in 1.1**: Added FR-011 (Mandatory Completion) and FR-012 (Profile Gate Check); Updated AC-FR009-003 to reflect soft-skip behavior; Updated constraints and risk mitigations
**Next Step**: Run `/plan specs/017-enhanced-onboarding/spec.md` to create implementation plan

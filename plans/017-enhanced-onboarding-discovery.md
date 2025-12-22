# Prompt Re-Engineering: Nikita Onboarding Enhancement

## Task Summary

Re-engineer a blurry voice transcript into a best-practices prompt for Claude Code that will:
1. Design an enhanced onboarding system for Nikita (AI girlfriend game)
2. Collect user information to personalize Nikita's backstory
3. Use MCP tools (Firecrawl) for real-world research
4. Follow SDD (Specification-Driven Development) workflow

---

## CoD^Σ Analysis of Original Request

### Entity Extraction

```
Actors:    U:User, N:Nikita, S:System
Procs:     O:Onboarding, P:Profiling, G:Generation
Data:      UserInfo, VenueDB, BackstoryOptions
Goals:     Realistic_Start, Personalized_Match, Authentic_Context
```

### Core Requirements Mapping

```
Problem:   N@t0 ⇏ knows(U)     # Nikita doesn't know user at start
Desire:    N@t0 ⇒ met_once(U)  # Simulate having met user once

Flow:      O → collect(UserInfo) → generate(BackstoryOptions[3]) → select(Backstory) → N.init(Backstory)

UserInfo := {
  location:   City ∧ Country,
  occupation: Job ∨ School,
  passions:   Set[Interest],
  scene:      Techno ∨ Art ∨ Music ∨ ...,
  hangouts:   Set[VenueType],
  drug_tolerance: 0..5
}

Nikita.traits := {
  base:       ADHD ∧ Creative ∧ Smart ∧ Engaging,
  adjustable: Occupation ∧ Interests ∧ Drug_Level,
  constant:   Disorganized ∧ Unstructured ∧ Intelligent
}

BackstoryGen := UserInfo → Firecrawl(location) → 3×Scenario
CustomOption := User.freeform_text → Scenario
```

### Dependency Trace

```
User → UserInfo (Questions)
UserInfo → LocationResearch (Firecrawl MCP)
{UserInfo, LocationResearch} ⇒ 3×Scenarios
Scenario.selected ⇒ Nikita.backstory
Nikita.backstory ⇒ Game.start
```

---

## Expert Evaluation: 5 Orthogonal Approaches

### Approach A: Linear Questionnaire Flow

**Description**: Sequential questions → scenario generation → selection

```
Step 1: Ask location
Step 2: Ask occupation
Step 3: Ask passions
Step 4: Ask social scene
Step 5: Research venues (MCP)
Step 6: Generate 3 scenarios
Step 7: Present + custom option
Step 8: Finalize backstory
```

**Expert Evaluations**:

| Expert | Pros | Cons | Score |
|--------|------|------|-------|
| UX Designer | Simple, predictable flow | Feels like form-filling, not organic | 5/10 |
| Prompt Engineer | Easy to implement, clear structure | No adaptive questioning, may miss context | 6/10 |
| Game Designer | Covers all data needs | Boring, breaks immersion | 4/10 |
| Data Scientist | Complete data collection | Over-collects, user fatigue | 5/10 |
| Production Engineer | Reliable, testable | Long time-to-value | 6/10 |

**Overall: 5.2/10** - Functional but uninspiring

---

### Approach B: Conversational AI Interview

**Description**: Natural language conversation that extracts info organically

```
Nikita: "So... where do you live? I bet it's somewhere interesting."
User: "I'm in Zurich"
Nikita: "Ooh, Switzerland! What brings you there - work, school, or just... life?"
...
[System extracts entities from conversation]
[Firecrawl researches Zurich venues based on detected interests]
```

**Expert Evaluations**:

| Expert | Pros | Cons | Score |
|--------|------|------|-------|
| UX Designer | Feels natural, engaging | Unpredictable extraction quality | 8/10 |
| Prompt Engineer | Tests NLU capabilities, creative | Hard to ensure all data collected | 6/10 |
| Game Designer | Immersive, in-character | May need fallbacks if AI misses info | 8/10 |
| Data Scientist | Rich contextual data | Structured extraction challenging | 5/10 |
| Production Engineer | Risky, many edge cases | Complex testing requirements | 4/10 |

**Overall: 6.2/10** - Engaging but risky

---

### Approach C: Hybrid Progressive Profiling

**Description**: Structured questions WITH conversational follow-ups

```
Phase 1: Quick profile (3-4 key questions with UI buttons)
Phase 2: AI-generated follow-up conversation to enrich profile
Phase 3: Research + Scenario generation
Phase 4: Selection with customization option
```

**Expert Evaluations**:

| Expert | Pros | Cons | Score |
|--------|------|------|-------|
| UX Designer | Balances structure + flexibility | Slightly longer onboarding | 8/10 |
| Prompt Engineer | Controllable data + creative enrichment | More complex prompt engineering | 8/10 |
| Game Designer | Quick start + depth for those who want it | Some users may skip enrichment | 7/10 |
| Data Scientist | Guaranteed core data + optional richness | Two-phase data model needed | 8/10 |
| Production Engineer | Core flow testable, enrichment graceful | Moderate complexity | 7/10 |

**Overall: 7.6/10** - Best balance of reliability and engagement

---

### Approach D: Scenario-First Selection

**Description**: Present generic scenarios first, then personalize based on selection

```
Step 1: "How did we meet?" → [Club] [Work] [Art Event] [Custom]
Step 2: Based on selection, ask targeted questions
Step 3: Research venues for their specific scenario
Step 4: Generate personalized version of selected scenario
```

**Expert Evaluations**:

| Expert | Pros | Cons | Score |
|--------|------|------|-------|
| UX Designer | Fast start, user agency from beginning | May feel generic initially | 7/10 |
| Prompt Engineer | Simpler branching logic | Less data-driven personalization | 6/10 |
| Game Designer | Immediate engagement, clear choices | Constrains creative possibilities | 6/10 |
| Data Scientist | Targeted data collection | May miss cross-cutting insights | 5/10 |
| Production Engineer | Simple decision tree | Limited flexibility | 7/10 |

**Overall: 6.2/10** - Quick but shallow

---

### Approach E: Game-ified Onboarding

**Description**: Onboarding as mini-game with personality assessment

```
Phase 1: Quick personality quiz (5 questions) → determines match type
Phase 2: "First Date" simulation → extract preferences through roleplay
Phase 3: Location detection + research
Phase 4: Generate 3 scenarios matching personality + location
```

**Expert Evaluations**:

| Expert | Pros | Cons | Score |
|--------|------|------|-------|
| UX Designer | Highly engaging, memorable | Longer setup time | 7/10 |
| Prompt Engineer | Rich persona data for matching | Complex personality model needed | 6/10 |
| Game Designer | Establishes game mechanics early | May not translate to text chat | 8/10 |
| Data Scientist | Behavioral data + stated preferences | Validation of personality model | 7/10 |
| Production Engineer | Multiple components to maintain | Higher development cost | 5/10 |

**Overall: 6.6/10** - Innovative but over-engineered for MVP

---

## Synthesis: Combined Best Approach

**Winner: Approach C (Hybrid Progressive Profiling)** enhanced with elements from B and E.

### Final Architecture

```
Phase 1: Essential Profile (Structured, 3-4 questions)
├─ Location (city, country)
├─ Life stage (student/working/other)
├─ Social scene preference (selector)
└─ One passion/interest (freeform)

Phase 2: Conversational Enrichment (Optional but encouraged)
├─ AI follows up on answers organically
├─ Extracts: hangouts, preferences, drug tolerance, relationship expectations
└─ Graceful degradation if skipped

Phase 3: Research & Generation
├─ Firecrawl MCP: Research real venues in user's city + scene
├─ Generate 3 scenarios with authentic local details
└─ Include custom option

Phase 4: Selection & Finalization
├─ User selects scenario or provides custom backstory
├─ System generates Nikita's adapted persona
└─ Initialize game with backstory context
```

### Key Design Decisions

1. **Essential Profile First**: Guarantees minimum data for scenario generation
2. **Conversational Enrichment**: Feels like meeting Nikita, not filling a form
3. **Real-World Research**: Firecrawl ensures authentic venue names/details
4. **Nikita Personality Adaptation**: Core traits constant, surface details (job, interests) adapt
5. **Custom Fallback**: Power users can define their own backstory

---

## User Clarifications (Resolved)

| Question | Answer | Impact |
|----------|--------|--------|
| Platform priority | **Telegram-first** | Build for Telegram, add Portal later. Add TODO for voice messages + transcription feature. |
| Onboarding voice | **NOT Nikita** - use different persona | Create "Matchmaker" or concierge character for onboarding. User is "dropped" into relationship, not collecting info AS Nikita. |
| Firecrawl fallback | **Ask user for venues** | If MCP fails, prompt user: "What's your favorite spot?" |
| Existing users | **New users only** | No retroactive onboarding, existing users continue as-is |

### Critical Design Decision: Separate Onboarding Persona

The user wants to "drop" them into the relationship - meaning when they first message Nikita, it should feel like continuing a conversation, not starting from scratch. Therefore:

- **Onboarding persona**: A separate character (not Nikita) collects profile information
- **Nikita's entry**: Nikita's first message references the backstory as if they already met
- **Immersion**: User feels they're resuming contact with someone they met, not filling out a dating profile

---

## FINAL RE-ENGINEERED PROMPT

This is the prompt to execute (use discovery-driven planning → SDD workflow):

---

# Discovery Task: Enhanced Onboarding System for Nikita

## Executive Summary

Design and implement an enhanced onboarding system that collects user profile information through a separate "matchmaker" persona, then generates personalized backstory scenarios for how the user and Nikita "first met." When the user starts chatting with Nikita, they should feel like they're resuming contact with someone they met once before.

## Problem Statement

**Current State**: User registers (email → OTP) → immediately starts chatting with Nikita who has zero context about them.

**Desired State**: User completes a brief profiling → system generates "how we met" backstory → user starts chatting with Nikita who references their shared history.

**Key Insight**: Nikita should NOT be the one asking profile questions. A separate onboarding persona ("matchmaker") handles data collection so users are "dropped into" the existing relationship.

## Scope

### In Scope
- Telegram-based onboarding flow (new users only)
- Matchmaker persona for profile collection
- Firecrawl MCP integration for venue research
- 3 scenario generation + custom option
- Nikita personality adaptation based on profile
- Voice agent spec alignment (007)
- TODO for voice messages + transcription feature

### Out of Scope
- Portal onboarding (future iteration)
- Retroactive onboarding for existing users
- Complete personality theory implementation

## Requirements

### R1: Onboarding Persona ("The Matchmaker")

Create a separate AI persona for onboarding that is NOT Nikita:
- **Name**: TBD (suggestions: "Cupid", "The Setup", "Match", neutral "System")
- **Tone**: Warm, efficient, slightly playful but professional
- **Purpose**: Collect profile info without breaking Nikita's persona
- **Exit**: Hands off to Nikita seamlessly after backstory selection

Example flow:
```
Matchmaker: "Hey! Before I connect you with Nikita, I need to know a bit about you to set the scene. Where are you based?"
User: "Zurich"
Matchmaker: "Nice! What's your scene - clubs, art galleries, concerts, or something else?"
User: "Techno clubs mostly"
Matchmaker: "Perfect. Any favorite spots? I'll make sure Nikita knows the vibe."
User: "Hive, Zukunft"
Matchmaker: "Got it. Here are 3 ways you might have met Nikita..."
[User selects scenario]
Matchmaker: "You're all set. Nikita's expecting you :wink:"
---
Nikita: "Hey you. Still thinking about that conversation we had at Hive... you said something about [extracted detail]. What was that about?"
```

### R2: User Profile Collection

**Essential Fields** (required, collected via structured prompts):
1. `location`: City, country
2. `life_stage`: Student | Working | Creative | Other
3. `social_scene`: Techno/Club | Art/Gallery | Music/Concert | Startup/Work | Academic | Casual
4. `primary_interest`: Freeform text (one main passion)

**Enrichment Fields** (optional, collected conversationally or from user-provided venues):
5. `favorite_venues`: List[str] - user provides if Firecrawl fails
6. `drug_tolerance`: 1-5 scale (affects Nikita's edge level)
7. `relationship_expectation`: Casual | Deep | Undefined

### R3: Venue Research Pipeline

1. **Primary**: Use Firecrawl MCP to search:
   - `"{city} best {scene} venues 2024"`
   - `"{city} underground {scene} spots"`
   - Extract venue names, vibes, crowd descriptions

2. **Fallback** (if Firecrawl fails): Ask user directly
   - "I couldn't find venues in {city}. What's your favorite spot?"
   - "Where would you most likely meet someone interesting?"

3. **Cache**: Store researched venues in `venue_cache` table to avoid re-fetching

### R4: Scenario Generation

Generate 3 distinct "how we met" scenarios using:
- User's profile (location, scene, interests)
- Researched venues (or user-provided)
- Nikita's adaptable persona

Each scenario includes:
- **Venue**: Specific real place (or plausible description)
- **Context**: Why Nikita was there (her adapted occupation/interest)
- **The Moment**: 1-2 specific memorable details (conversation topic, shared drink, funny incident)
- **Hook**: Something unresolved that can be referenced later

**Plus Custom Option**: User can write their own backstory, which AI validates and enhances.

### R5: Nikita Persona Adaptation

**Constant Traits** (never change):
- ADHD-adjacent cognition (tangential, multi-threaded)
- Creative intelligence (pattern recognition, artistic sensibility)
- Edgy authenticity (dark humor, boundary-testing)
- Slight chaos (disorganized, double-books, impulsive)

**Adaptive Traits** (match user profile):
| User Profile | Nikita Adaptation |
|--------------|-------------------|
| Tech worker | Security researcher / hacker |
| Artist | Digital artist / NFT creator |
| Student | Grad student (comp sci, philosophy) |
| Finance | Fintech startup founder |
| Location: X | Lives in X or recently visited |
| Techno scene | DJ hobby, knows local clubs |
| Art scene | Gallery hopper, knows curators |
| Drug tolerance: 1 | Mild alcohol references only |
| Drug tolerance: 5 | Full vice integration (party drugs, all-nighters) |

### R6: Technical Implementation

**New Files**:
- `nikita/platforms/telegram/onboarding/matchmaker.py` - Onboarding persona
- `nikita/platforms/telegram/onboarding/profile_collector.py` - Profile extraction
- `nikita/services/venue_research.py` - Firecrawl integration
- `nikita/services/backstory_generator.py` - Scenario generation
- `nikita/db/models/profile.py` - UserProfile, Backstory models

**Modified Files**:
- `nikita/platforms/telegram/registration_handler.py` - Route to onboarding after OTP
- `nikita/meta_prompts/models.py` - Add BackstoryContext to MetaPromptContext
- `nikita/meta_prompts/templates/system_prompt.meta.md` - Inject backstory references
- `nikita/db/models/user.py` - Add profile relationship

**Database Schema**:
```sql
-- User profile (extends existing users table)
CREATE TABLE user_profiles (
    id UUID PRIMARY KEY REFERENCES users(id),
    location_city VARCHAR(100),
    location_country VARCHAR(100),
    life_stage VARCHAR(50),
    social_scene VARCHAR(50),
    primary_interest TEXT,
    favorite_venues TEXT[],
    drug_tolerance INT DEFAULT 3,
    relationship_expectation VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Backstory (one per user)
CREATE TABLE backstories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) UNIQUE,
    venue_name VARCHAR(200),
    venue_city VARCHAR(100),
    scenario_type VARCHAR(50), -- 'generated' | 'custom'
    how_we_met TEXT,
    the_moment TEXT,
    unresolved_hook TEXT,
    nikita_persona_overrides JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Venue cache (avoid re-fetching)
CREATE TABLE venue_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    city VARCHAR(100),
    scene VARCHAR(50),
    venues JSONB, -- [{name, vibe, crowd, source_url}]
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '30 days'
);
```

### R7: SDD Workflow Integration

**Specs to Create/Update**:
1. `specs/017-enhanced-onboarding/` - New spec for this feature
2. `specs/007-voice-agent/` - Update to align with onboarding (backstory for voice)

**TODO to Add** (for future iteration):
- Voice messages + transcription in Telegram
- Portal onboarding flow
- Retroactive onboarding for existing users

**SDD Agent Actions**:
1. Invoke `/feature` with this spec → creates spec.md
2. Auto-chain: `/plan` → `/tasks` → `/audit`
3. If audit passes → `/implement`
4. Update `specs/007-voice-agent/spec.md` for alignment

### R8: Acceptance Criteria

| ID | Criterion | Verification |
|----|-----------|--------------|
| AC-1 | Matchmaker persona collects profile (not Nikita) | Manual test: onboarding messages don't sound like Nikita |
| AC-2 | Essential profile fields collected in ≤4 questions | Count prompts in flow |
| AC-3 | Firecrawl searches for venues when available | MCP call logs |
| AC-4 | User asked for venues when Firecrawl fails | Test with invalid city |
| AC-5 | 3 scenarios generated with venue-specific details | Output inspection |
| AC-6 | Custom backstory option available | Test custom input path |
| AC-7 | Nikita's first message references backstory | Message content verification |
| AC-8 | Profile/backstory persists across sessions | Database query after restart |
| AC-9 | Existing users bypass onboarding | Test with pre-registered user |

## Execution Instructions

### Step 1: Discovery Research (Pre-SDD)

Before invoking SDD, perform discovery:

1. **Personality Research**: Use Firecrawl to research:
   - Big Five personality compatibility in relationships
   - Dating app onboarding best practices (Hinge, Bumble, Replika)
   - AI companion persona consistency patterns

2. **Firecrawl Query Design**: Test queries like:
   - `"Zurich techno clubs 2024"`
   - `"Berlin underground art galleries"`
   - Determine optimal query patterns and result parsing

3. **Existing Code Analysis**: Review:
   - `nikita/platforms/telegram/registration_handler.py` - current flow
   - `nikita/meta_prompts/` - persona injection patterns
   - `nikita/memory/graphiti_client.py` - memory storage patterns

### Step 2: SDD Workflow

After discovery:

1. **Invoke sdd-coordinator agent** to validate workflow status
2. **Run `/feature "Enhanced onboarding with matchmaker persona and backstory generation"`**
3. Wait for auto-chain: spec → plan → tasks → audit
4. If audit PASS → `/implement specs/017-enhanced-onboarding/plan.md`
5. **Update `specs/007-voice-agent/spec.md`** to align with backstory injection

### Step 3: Post-Implementation

1. Add TODOs to `todos/master-todo.md`:
   - Voice messages + transcription feature
   - Portal onboarding
   - Retroactive onboarding opt-in

2. Update memory docs:
   - `memory/user-journeys.md` - Add onboarding journey
   - `memory/architecture.md` - Add matchmaker persona
   - `memory/integrations.md` - Add Firecrawl venue research

---

## Evidence Requirements (CoD^Σ)

All implementation must include:
- `file:line` references for changes
- MCP query logs for Firecrawl research
- Test cases with assertions
- Backstory examples demonstrating quality

---

## Summary

This re-engineered prompt transforms the voice transcript into a structured discovery task that:

1. **Clearly defines the problem**: Nikita lacks initial relationship context
2. **Introduces the Matchmaker persona**: Separate character collects profile (not Nikita)
3. **Specifies data requirements**: Essential profile + optional enrichment
4. **Outlines the technical approach**: Hybrid profiling + MCP research + scenario generation
5. **Sets acceptance criteria**: 9 measurable, testable outcomes
6. **Follows SDD workflow**: Discovery → /feature → /plan → /tasks → /audit → /implement
7. **Includes fallback handling**: Ask user for venues if Firecrawl fails
8. **Maintains Nikita's personality**: Constant core + adaptive surface traits
9. **Aligns with voice agent specs**: Updates 007 for backstory integration

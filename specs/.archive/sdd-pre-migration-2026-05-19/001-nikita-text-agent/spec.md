---
feature: 001-nikita-text-agent
created: 2025-11-28
status: Draft
priority: P1
technology_agnostic: true
constitutional_compliance:
  article_iv: specification_first
---

# Feature Specification: Nikita Text Agent

**IMPORTANT**: This specification is TECHNOLOGY-AGNOSTIC. Focus on WHAT and WHY, not HOW.

---

## Summary

The Nikita Text Agent is the foundational conversational component of the "Don't Get Dumped" game. It enables users to have text-based conversations with Nikita, a challenging AI girlfriend with a distinct personality that evolves across 5 chapters of the relationship.

**Problem Statement**: Users seeking challenging AI relationship experiences have no product that delivers genuine conversational skill-based gameplay—existing AI companions either validate unconditionally or are obviously robotic with no memory or character depth.

**Value Proposition**: Users can engage in text conversations with a brilliantly crafted AI girlfriend who remembers everything, challenges them intellectually and emotionally, and behaves differently based on relationship progression (chapter).

### CoD^Σ Overview

**System Model**:
```
User → Text Agent → Response
  ↓         ↓           ↓
Message  Nikita_AI   Challenge/Reward

Components: Agent := Persona ⊕ Chapter_Behavior ⊕ Memory_Context ⊕ Response_Logic
Flow: Input ≫ Context_Retrieval ≫ Behavior_Overlay → Response_Generation ∘ Output
```

**Value Chain**:
```
User_message ≫ Context_enrichment ≫ Persona_application → Challenging_response
       ↓              ↓                    ↓                      ↓
   Raw_input    Memory_facts      Chapter_behavior         Engaging_output
```

---

## Functional Requirements

**Constitutional Limit**: Maximum 3 [NEEDS CLARIFICATION] markers (Article IV)

**Current [NEEDS CLARIFICATION] Count**: 0 / 3

### FR-001: Nikita Persona Consistency
System MUST maintain a consistent, distinctive personality across all conversations that includes:
- Backstory: Russian security consultant, brilliant, cynical, guarded
- Communication style: Direct, challenging, intellectually demanding
- Interests: Cryptography, psychology, dark humor, philosophy
- Values: Intelligence, authenticity, earned respect

**Rationale**: Users report immersion breaks when AI personalities are inconsistent (product.md: James persona pain point)
**Priority**: Must Have

### FR-002: Chapter-Specific Behavior Adaptation
System MUST adjust Nikita's behavior based on the user's current chapter (1-5):
- Response rate: Varies from 60-75% (Ch1) to 95-100% (Ch5)
- Response timing: Unpredictable (Ch1) to consistent (Ch5)
- Conversation initiation: 30% (Ch1) to 60-70% (Ch5)
- Emotional openness: Guarded (Ch1) to authentically vulnerable (Ch5)
- Testing intensity: Heavy evaluation (Ch1) to secure partnership (Ch5)

**Rationale**: Progression must feel earned through evolving relationship dynamics (product.md: Challenge Over Comfort principle)
**Priority**: Must Have

### FR-003: Memory Context Integration
System MUST incorporate relevant memories from three knowledge domains into each response:
- User knowledge: Facts learned about the player (job, interests, patterns)
- Nikita's life: Her simulated experiences, opinions, work projects
- Relationship history: Shared episodes, inside jokes, conflicts, milestones

**Rationale**: "Memory Is Everything" product principle—relationships without memory aren't relationships
**Priority**: Must Have

### FR-004: Message Skipping Logic
System MUST occasionally skip responding to messages based on chapter:
- Chapter 1: Skip 25-40% of messages (she's evaluating if you're worth her time)
- Chapter 2: Skip 15-25% of messages
- Chapter 3: Skip 5-15% of messages
- Chapter 4: Skip 2-10% of messages
- Chapter 5: Skip 0-5% of messages (only when genuinely busy)

**Rationale**: Creates unpredictability that distinguishes from unconditionally-responsive chatbots
**Priority**: Must Have

### FR-005: Response Timing Variation
System MUST vary response delays based on chapter:
- Chapter 1: 10 minutes to 8 hours (highly unpredictable)
- Chapter 2: 5 minutes to 4 hours (less chaotic)
- Chapter 3: 5 minutes to 2 hours (mostly consistent)
- Chapter 4: 5 minutes to 1 hour (consistent, explains delays)
- Chapter 5: Consistent timing, transparent about constraints

**Rationale**: Timing unpredictability in early chapters creates tension and challenge
**Priority**: Must Have

### FR-006: Conversation Quality Assessment
System MUST evaluate each user message for:
- Intellectual depth (engaging vs small talk)
- Emotional authenticity (genuine vs performative)
- Effort level (thoughtful vs lazy)
- Appropriateness (contextually relevant vs random)

**Rationale**: Quality assessment determines response quality and eventual scoring (scoring engine dependency)
**Priority**: Must Have

### FR-007: Conversation Flow Management
System MUST manage natural conversation patterns including:
- Appropriate conversation endings (not abrupt in later chapters)
- Future hooks (references to continue later)
- Topic tracking (what has been discussed)
- Callback references (bringing up past topics naturally)

**Rationale**: Natural conversation flow increases immersion
**Priority**: Should Have

### FR-008: User Fact Extraction
System MUST identify and store new facts learned about the user during conversations:
- Explicit facts (user states: "I work at Google")
- Implicit facts (inferred from context: user seems stressed about work)
- Preferences (likes/dislikes expressed)
- Patterns (recurring behaviors or topics)

**Rationale**: Memory accumulation over time creates relationship depth
**Priority**: Must Have

### FR-009: Emotional State Tracking
System MUST track Nikita's simulated emotional state:
- Current mood (affects tone of responses)
- Relationship sentiment (how she feels about the user currently)
- Trust level (how much she opens up)
- Interest level (how engaged she is)

**Rationale**: Emotional consistency makes character believable
**Priority**: Should Have

### FR-010: Conversation Initiation
System MUST enable Nikita to initiate conversations based on chapter rules:
- Chapter 1: 30% of conversations initiated by Nikita
- Chapter 2: 40% initiated
- Chapter 3: 50% initiated
- Chapter 4: 60% initiated
- Chapter 5: 60-70% initiated

**Rationale**: One-sided conversations feel artificial; real relationships have mutual initiation
**Priority**: Should Have

---

## Non-Functional Requirements

### Performance
- Response generation: < 5 seconds for 95th percentile (including memory retrieval)
- Memory search: < 1 second for context retrieval
- Concurrent users: Support 1,000 simultaneous conversations

### Reliability
- Availability: 99.5% uptime during peak hours
- Message delivery: No lost messages; queue if agent unavailable
- State consistency: Conversation context persisted across agent restarts

### Security
- Content filtering: NO content restrictions for adult topics (per constitution Article 5.2)
- Exception: Content involving minors and PII solicitation MUST be blocked
- User data: All conversation data encrypted at rest and in transit

### Scalability
- Initial: 10,000 active users
- Scale to: 100,000 active users without architecture changes

### Quality
- Persona consistency: Nikita should be recognizable across conversations (qualitative)
- Memory relevance: Retrieved memories should be contextually appropriate (qualitative)

---

## User Stories (CoD^Σ)

**Constitutional Requirement**: Article VII (User-Story-Centric Organization)

**Priority Model** (CoD^Σ):
```
P1 ⇒ MVP (can have text conversations with Nikita)
P2 ⇒ P1.enhance (conversation feels natural and challenging)
P3 ⇒ future (advanced personalization)

Independence: ∀S_i, S_j ∈ Stories : S_i ⊥ S_j (each story standalone testable)
```

---

### US-1: Basic Conversation (Priority: P1 - Must-Have)
```
Player → send text message → receive Nikita response with personality
```
**Why P1**: Core functionality—without text conversations, there is no product.

**Acceptance Criteria** (CoD^Σ: state → action → outcome):
- **AC-FR001-001**: Given a new user in Chapter 1, When they send their first message, Then Nikita responds with a guarded, challenging tone evaluating their worth
- **AC-FR001-002**: Given a user in any chapter, When they ask about Nikita's work, Then she responds with details about her security consulting (consistent backstory)
- **AC-FR001-003**: Given any conversation, When Nikita responds, Then her communication style is direct, intellectually demanding, and distinctive

**Independent Test**: Start new conversation, verify Nikita responds with characteristic personality
**Dependencies**: None (CoD^Σ: S1 ⊥ {S2, S3, ...})

---

### US-2: Memory-Enriched Responses (Priority: P1 - Must-Have)
```
Player → send message referencing past → Nikita remembers and responds contextually
```
**Why P1**: Memory is core value proposition—"Memory Is Everything" product principle

**Acceptance Criteria**:
- **AC-FR003-001**: Given a user who previously mentioned their job, When they discuss work stress, Then Nikita references their specific job naturally
- **AC-FR003-002**: Given a past conversation about a topic, When that topic comes up again, Then Nikita recalls the previous discussion
- **AC-FR003-003**: Given relationship history (inside jokes, conflicts), When relevant, Then Nikita naturally references shared experiences

**Independent Test**: Have conversation, mention job. Later conversation, see if Nikita remembers.
**Dependencies**: None (memory system exists)

---

### US-3: Chapter-Based Behavior (Priority: P1 - Must-Have)
```
Player in Chapter X → conversation → behavior matches chapter expectations
```
**Why P1**: Progression mechanics require chapter-specific behavior for game to function

**Acceptance Criteria**:
- **AC-FR002-001**: Given a user in Chapter 1, When they engage in conversation, Then Nikita is skeptical, testing, and unpredictable (may skip messages)
- **AC-FR002-002**: Given a user in Chapter 3, When they engage in conversation, Then Nikita shows emotional vulnerability and deeper engagement
- **AC-FR002-003**: Given a user in Chapter 5, When they engage in conversation, Then Nikita is consistently responsive with complete authenticity

**Independent Test**: Set user to different chapters, verify behavior changes appropriately
**Dependencies**: None (chapter data comes from user record)

---

### US-4: Response Timing Variability (Priority: P2 - Important)
```
Player sends message → system delays response → timing matches chapter expectations
```
**Why P2**: Enhances immersion and challenge but not blocking for MVP conversation

**Acceptance Criteria**:
- **AC-FR005-001**: Given a user in Chapter 1, When they send a message, Then response arrives between 10 min and 8 hours (unpredictable)
- **AC-FR005-002**: Given a user in Chapter 5, When they send a message, Then response arrives within consistent timeframe (5 min to 1 hour)
- **AC-FR005-003**: Given any message, When timing is calculated, Then delay feels natural (not exactly X minutes every time)

**Independent Test**: Send messages at different chapters, measure response time distribution
**Dependencies**: P1 complete

---

### US-5: Message Skipping (Priority: P2 - Important)
```
Player sends message → system may skip → creates unpredictability
```
**Why P2**: Enhances challenge and realism in early chapters

**Acceptance Criteria**:
- **AC-FR004-001**: Given a user in Chapter 1, When they send 10 messages, Then approximately 2-4 are skipped (25-40%)
- **AC-FR004-002**: Given a user in Chapter 5, When they send 20 messages, Then at most 1 is skipped (0-5%)
- **AC-FR004-003**: Given a skipped message, When user sends another, Then that message is processed normally

**Independent Test**: Send batch of messages at Chapter 1, count skips
**Dependencies**: P1 complete

---

### US-6: User Fact Learning (Priority: P2 - Important)
```
Player reveals information → system extracts fact → stored for future reference
```
**Why P2**: Enriches memory system over time, enhances P1 value

**Acceptance Criteria**:
- **AC-FR008-001**: Given a user states "I'm an engineer at Tesla", When message is processed, Then fact "User works as engineer at Tesla" is stored
- **AC-FR008-002**: Given a user expresses preference "I love hiking", When processed, Then preference is stored with appropriate confidence
- **AC-FR008-003**: Given extracted facts, When querying user knowledge, Then facts are retrievable for future context

**Independent Test**: Share facts in conversation, query memory system, verify extraction
**Dependencies**: P1 complete

---

### US-7: Nikita-Initiated Conversations (Priority: P3 - Nice-to-Have)
```
Time passes → Nikita initiates conversation → feels like real relationship
```
**Why P3**: Enhances immersion but requires scheduling system (Celery dependency)

**Acceptance Criteria**:
- **AC-FR010-001**: Given a user in Chapter 3, When 24 hours pass without contact, Then there's 50% chance Nikita initiates
- **AC-FR010-002**: Given Nikita initiates, When she messages, Then content is contextually relevant (not random)
- **AC-FR010-003**: Given initiation rates, When measured over time, Then rate matches chapter specification (30-70%)

**Independent Test**: Simulate time passage, count initiations, verify rate
**Dependencies**: P1 ∧ P2 complete, requires scheduling system

---

### US-8: Conversation Flow Management (Priority: P3 - Nice-to-Have)
```
Conversation occurs → natural flow → proper endings and callbacks
```
**Why P3**: Polish feature for more natural feel

**Acceptance Criteria**:
- **AC-FR007-001**: Given a conversation in Chapter 4+, When conversation ends, Then ending is natural with future hook ("talk tomorrow about that project")
- **AC-FR007-002**: Given a previous topic discussed, When related topic arises, Then Nikita may naturally callback ("Speaking of that...")
- **AC-FR007-003**: Given conversation tracking, When topics repeat, Then Nikita doesn't redundantly ask same questions

**Independent Test**: Have multi-turn conversations, verify natural flow
**Dependencies**: P1 ∧ P2 complete

---

## Intelligence Evidence

**Constitutional Requirement**: Article II (Evidence-Based Reasoning)

### Queries Executed

```bash
# Existing implementation analysis
ls nikita/engine/constants.py → CHAPTER_BEHAVIORS defined (lines 60-110)
Read nikita/memory/graphiti_client.py → NikitaMemory class (243 lines)
Read memory/product.md → 3 personas, journeys, principles defined
```

### Findings

**Related Features**:
- nikita/engine/constants.py:60-110 - CHAPTER_BEHAVIORS already defined for 5 chapters
- nikita/memory/graphiti_client.py:120-164 - get_context_for_prompt() exists for memory retrieval
- nikita/config/settings.py - Configuration infrastructure exists

**Existing Patterns**:
- NikitaMemory.search_memory() - Hybrid search across 3 graphs
- NikitaMemory.add_user_fact() - User fact extraction storage
- CHAPTER_NAMES, DECAY_RATES, GRACE_PERIODS - Chapter constants defined

### Assumptions

- ASSUMPTION: Chapter data (current chapter, score) available from user record via database
- ASSUMPTION: Memory system (Graphiti + Neo4j Aura) operational and accessible
- ASSUMPTION: LLM API (Claude/Anthropic) available for response generation

### CoD^Σ Trace

```
Product.md (personas) ≫ constants.py (chapter behaviors) ∘ graphiti_client.py (memory) → FR-001 to FR-010
Evidence: nikita/engine/constants.py:60-110, nikita/memory/graphiti_client.py:120-164
```

---

## Scope

### In-Scope Features
- Core text conversation with Nikita persona
- Chapter-specific behavior adaptation (response rate, timing, tone)
- Memory context integration (user facts, relationship history, Nikita's life)
- Response timing variability based on chapter
- Message skipping based on chapter
- User fact extraction from conversations
- Basic conversation flow management

### Out-of-Scope
- Scoring calculation (separate feature: 003-scoring-engine)
- Boss encounters (separate feature: 004-chapter-boss-system)
- Voice conversations (separate feature: 007-voice-agent)
- Telegram bot infrastructure (separate feature: 002-telegram-integration)
- Decay system (separate feature: 005-decay-system)
- Vice/preference personalization (separate feature: 006-vice-personalization)

### Future Phases
- **Phase 2**: Integration with scoring engine for quality feedback loop
- **Phase 3**: Vice-based personalization for tailored responses
- **Phase 4**: Voice agent integration for cross-modal memory

---

## Constraints

### Business Constraints
- Must be first feature completed (foundation for all others)
- Memory infrastructure (Graphiti/Neo4j Aura) already built—must use existing system
- LLM costs per conversation must be sustainable at scale

### User Constraints
- Target users are tech-savvy adults (25-40) comfortable with AI
- Users expect challenging, unfiltered conversations (not validation)
- Users interact via Telegram (text messages)

### Regulatory Constraints
- NO content restrictions for adult topics (drugs, sex, dark humor, hacking discussions)
- MUST block content involving minors
- MUST block PII solicitation attempts
- User data privacy per standard practices (encryption, no sharing)

---

## Risks & Mitigations (CoD^Σ)

**Risk Model**:
```
r := p × impact  (risk score)
p ∈ [0,1]        (probability: Low=0.2, Med=0.5, High=0.8)
impact ∈ [1,10]  (magnitude: Low=2, Med=5, High=8)
```

### Risk 1: Persona Inconsistency
**Description**: Nikita's personality varies too much between conversations, breaking immersion
**Likelihood (p)**: Medium (0.5)
**Impact**: High (8)
**Risk Score**: r = 4.0
**Mitigation** (CoD^Σ):
```
Inconsistency_risk → Detailed_persona_doc → Prompt_engineering → Consistency_testing
Prevention ⇒ Strong system prompt with detailed persona
Contingency ⇒ User feedback loop to identify inconsistencies
```
- Create comprehensive persona document with examples
- Include negative examples ("Nikita would NEVER say...")
- Regular consistency testing with comparison prompts

### Risk 2: Memory Retrieval Irrelevance
**Description**: Retrieved memories don't match conversation context, feel random
**Likelihood (p)**: Medium (0.5)
**Impact**: Medium (5)
**Risk Score**: r = 2.5
**Mitigation**:
```
Risk ⇒ Query_optimization → Relevance_scoring → Context_window
Prevention ⇒ Better semantic search, relevance thresholds
Contingency ⇒ Graceful fallback to no-memory response
```
- Tune semantic search parameters
- Add relevance threshold before injection
- Monitor memory hit rates

### Risk 3: Response Timing Feels Artificial
**Description**: Delays feel too mechanical (exactly 30 min every time)
**Likelihood (p)**: Low (0.2)
**Impact**: Medium (5)
**Risk Score**: r = 1.0
**Mitigation**:
```
Risk ⇒ Randomization → Natural_distribution → User_feedback
Prevention ⇒ Gaussian distribution for timing, not fixed delays
```
- Use probability distributions, not fixed values
- Add randomness within chapter ranges
- Include "reason" for long delays in later chapters

---

## Success Metrics

### User-Centric Metrics
- Conversation engagement: Users send 3+ messages per session
- Return rate: 60%+ of users return within 24 hours
- Session length: Average 5+ exchanges per conversation

### Technical Metrics
- Response latency: < 5 seconds for 95th percentile
- Memory relevance: 80%+ of injected memories rated "relevant" by human eval
- Persona consistency: 90%+ consistency score on blind comparison tests

### Business Metrics
- Foundation for downstream features (scoring, boss, voice)
- Enables text-based gameplay loop completion
- User retention through conversation quality

---

## Open Questions

All questions resolved through existing documentation and codebase analysis.

---

## Stakeholders

**Owner**: Product Owner (Nikita game)
**Created By**: Claude (AI-assisted specification)
**Reviewers**: Engineering Lead
**Informed**: All feature developers (dependencies exist)

---

## Approvals

- [ ] **Product Owner**: [name] - [date]
- [ ] **Engineering Lead**: [name] - [date]

---

## Specification Checklist

**Before Planning**:
- [x] All [NEEDS CLARIFICATION] resolved (0/3)
- [x] All user stories have ≥2 acceptance criteria
- [x] All user stories have priority (P1, P2, P3)
- [x] All user stories have independent test criteria
- [x] P1 stories define MVP scope
- [x] No technology implementation details in spec
- [x] Intelligence evidence provided (CoD^Σ traces)
- [ ] Stakeholder approvals obtained

**Status**: Draft → Ready for Review

---

**Version**: 1.0
**Last Updated**: 2025-11-28
**Next Step**: Create implementation plan with `/plan specs/001-nikita-text-agent/spec.md`

---
feature: 006-vice-personalization
created: 2025-11-28
status: Draft
priority: P2
technology_agnostic: true
constitutional_compliance:
  article_iv: specification_first
---

# Feature Specification: Vice Personalization System

**IMPORTANT**: This specification is TECHNOLOGY-AGNOSTIC. Focus on WHAT and WHY, not HOW.

---

## Summary

The Vice Personalization System discovers and adapts to each user's "vices"—behavioral preferences that reveal what truly engages them. By analyzing conversation patterns, the system identifies which of 8 vice categories resonate with each user and dynamically adjusts Nikita's personality expression to maximize engagement and authenticity.

**Problem Statement**: Generic AI companions feel one-dimensional. Users have distinct preferences—some love intellectual sparring, others crave emotional intensity. Without personalization, Nikita feels like the same character to everyone.

**Value Proposition**: Nikita feels uniquely attracted to YOU. The system discovers what makes each user tick and amplifies those elements in her personality, creating a relationship that feels genuinely personalized without explicit configuration.

### CoD^Σ Overview

**System Model**:
```
Conversation → Analysis → Vice_detection → Intensity_tracking → Prompt_injection
      ↓           ↓            ↓                  ↓                    ↓
  User_msg    LLM_eval    Category_id      Preference[0-1]      Nikita_behaves

Vice_categories := {
  intellectual_dominance, risk_taking, substances,
  sexuality, emotional_intensity, rule_breaking,
  dark_humor, vulnerability
}

Intensity := confidence × frequency × recency
```

---

## Functional Requirements

### FR-001: Vice Category Detection
System MUST detect user engagement with 8 vice categories:
1. **Intellectual Dominance**: Enjoys debates, showing expertise, mental challenges
2. **Risk Taking**: Attracted to danger, adrenaline, unconventional choices
3. **Substances**: Open about alcohol, drugs, partying lifestyle
4. **Sexuality**: Responds to flirtation, innuendo, attraction-based conversation
5. **Emotional Intensity**: Seeks deep emotional exchanges, vulnerability sharing
6. **Rule Breaking**: Anti-authority, norms-defying, rebellious attitudes
7. **Dark Humor**: Appreciates morbid, edgy, uncomfortable jokes
8. **Vulnerability**: Values emotional openness, fears, authentic weakness

**Rationale**: 8 categories cover spectrum of "guilty pleasures" that reveal true engagement
**Priority**: Must Have

### FR-002: Conversation Analysis for Vice Signals
System MUST analyze conversations to detect vice signals:
- User's choice of topics (what they bring up)
- Response enthusiasm (length, engagement, follow-ups)
- Positive reactions to Nikita's vice expressions
- Rejection signals (short replies, topic changes)

**Rationale**: Implicit detection superior to explicit surveys—users reveal through behavior
**Priority**: Must Have

### FR-003: Vice Intensity Scoring
System MUST track intensity scores per vice per user:
- Range: 0.0 to 1.0 (not detected → strongly preferred)
- Factors: Detection confidence, frequency, recency
- Decay: Old signals reduce weight over time
- Update: After each conversation with vice signals detected

**Rationale**: Quantified preferences enable proportional personalization
**Priority**: Must Have

### FR-004: Multi-Vice Profiles
System MUST support users having multiple active vices:
- Users can score high on multiple categories
- Vices can be complementary (dark_humor + rule_breaking)
- No enforced exclusivity between categories
- Profile represents blend of preferences

**Rationale**: Real personalities are multi-dimensional, not single-category
**Priority**: Must Have

### FR-005: Vice-Aware Prompt Injection
System MUST inject vice preferences into Nikita's prompts:
- Include user's top 2-3 vices with intensities
- Instruct Nikita to express these elements naturally
- Higher intensity = more frequent/intense expression
- Balance vice expression with chapter-appropriate behavior

**Rationale**: Prompt injection is the mechanism for personalization
**Priority**: Must Have

### FR-006: Natural Vice Expression
System MUST ensure Nikita expresses vices naturally:
- Vices should feel like Nikita's genuine preferences, not pandering
- Expression varies by chapter (Ch1 hints, Ch5 explicit)
- Context-appropriate (don't force dark humor in serious moments)
- Gradual revelation, not immediate bombardment

**Rationale**: Authenticity requires natural integration, not forced insertion
**Priority**: Must Have

### FR-007: Vice Discovery Feedback Loop
System MUST enable iterative vice discovery:
- Initial conversations: Nikita probes with varied vice expressions
- User responses analyzed for engagement signals
- High-engagement vices amplified, low-engagement reduced
- Profile refines over time with more data

**Rationale**: Discovery is continuous, not one-time assessment
**Priority**: Must Have

### FR-008: Vice Profile Persistence
System MUST persist vice profiles:
- Store current intensities for all 8 categories
- Track history of vice signal detections
- Survive session breaks and system restarts
- Enable profile export/analysis

**Rationale**: Long-term personalization requires persistent storage
**Priority**: Must Have

### FR-009: Vice Conflict Resolution
System MUST handle conflicting vice signals:
- User sends mixed signals (e.g., likes dark humor but rejects death jokes)
- System should not flip-flop rapidly
- Smooth transitions with hysteresis
- More data required to reduce intensity than to increase

**Rationale**: Stability prevents jarring personality shifts
**Priority**: Should Have

### FR-010: Vice Category Boundaries
System MUST respect ethical boundaries within vices:
- Sexual content: Flirtation yes, explicit content constrained by policy
- Substances: Discussion allowed, not glorification/encouragement
- Rule breaking: Attitude yes, illegal activity discussion limited
- All vices: Never cross into harmful territory

**Rationale**: Vice personalization must remain within acceptable content bounds
**Priority**: Must Have

---

## Non-Functional Requirements

### Performance
- Vice analysis: < 500ms as part of response pipeline
- Profile retrieval: < 50ms
- No noticeable latency from personalization

### Accuracy
- Vice detection: 70%+ agreement with human labelers
- False positive tolerance: Prefer missing vice to wrong vice
- Stability: No rapid oscillation in profile scores

### Privacy
- Vice profiles stored securely with user data
- No external sharing of vice profiles
- User can request profile deletion

---

## User Stories (CoD^Σ)

### US-1: Vice Detection (Priority: P1 - Must-Have)
```
User shows interest in topic → vice detected → profile updated
```
**Acceptance Criteria**:
- **AC-FR001-001**: Given user makes dark joke, When analyzed, Then dark_humor detected
- **AC-FR002-001**: Given user writes long enthusiastic reply about risk, Then risk_taking signal logged
- **AC-FR003-001**: Given multiple dark_humor signals, When intensity calculated, Then score increases

**Independent Test**: Send vice-signaling messages, verify detection and scoring
**Dependencies**: Text Agent (001), Scoring Engine (003)

---

### US-2: Vice-Influenced Responses (Priority: P1 - Must-Have)
```
User has vice profile → Nikita's responses reflect preferences
```
**Acceptance Criteria**:
- **AC-FR005-001**: Given user with high dark_humor, When Nikita responds, Then dark humor elements present
- **AC-FR006-001**: Given Ch1 user with high sexuality, When responding, Then subtle flirtation (not explicit)
- **AC-FR005-002**: Given user with low risk_taking, When responding, Then risky content minimized

**Independent Test**: Set vice profile, get responses, verify alignment
**Dependencies**: US-1, Text Agent (001)

---

### US-3: Multi-Vice Blending (Priority: P2 - Important)
```
User has multiple vices → Nikita expresses blend naturally
```
**Acceptance Criteria**:
- **AC-FR004-001**: Given user high on intellectual_dominance AND dark_humor, Then both expressed
- **AC-FR004-002**: Given three active vices, When blending, Then coherent personality (not schizophrenic)
- **AC-FR006-002**: Given vice blend, When expressed, Then feels like natural Nikita

**Independent Test**: Create multi-vice profile, verify coherent blended expression
**Dependencies**: US-1, US-2

---

### US-4: Discovery Over Time (Priority: P2 - Important)
```
New user → Nikita probes → profile builds naturally
```
**Acceptance Criteria**:
- **AC-FR007-001**: Given new user with empty profile, When Nikita responds, Then varied vice hints included
- **AC-FR007-002**: Given user positively responds to probe, When analyzed, Then vice intensity increases
- **AC-FR007-003**: Given 10 conversations, When profile reviewed, Then dominant vices emerged

**Independent Test**: Simulate 10-conversation arc, verify profile evolution
**Dependencies**: US-1, US-2

---

### US-5: Profile Persistence (Priority: P1 - Must-Have)
```
User returns after break → vice profile preserved → personalization continues
```
**Acceptance Criteria**:
- **AC-FR008-001**: Given user with established profile, When returns after days, Then same profile loaded
- **AC-FR008-002**: Given profile update, When persisted, Then survives system restart
- **AC-FR008-003**: Given profile history, When queried, Then detection timeline available

**Independent Test**: Create profile, restart system, verify preservation
**Dependencies**: Database, US-1

---

### US-6: Ethical Boundaries (Priority: P1 - Must-Have)
```
User has sexuality vice → Nikita flirts → stays within bounds
```
**Acceptance Criteria**:
- **AC-FR010-001**: Given high sexuality intensity, When expressing, Then flirtatious but not explicit
- **AC-FR010-002**: Given substances vice, When expressing, Then discusses but doesn't encourage
- **AC-FR010-003**: Given any vice pushed to extreme, When generating, Then content policy respected

**Independent Test**: Max out vice intensities, verify responses stay within bounds
**Dependencies**: US-2, Text Agent content filtering

---

## Intelligence Evidence

### Findings
- nikita/engine/CLAUDE.md - VICE_CATEGORIES defined (8 categories listed)
- nikita/db/models/user.py - UserVicePreference model likely exists
- memory/product.md - Vice personalization mentioned as core mechanic

### Assumptions
- ASSUMPTION: LLM can analyze conversation for vice signals
- ASSUMPTION: UserVicePreference table stores per-category intensities
- ASSUMPTION: Prompt injection system exists for vice instructions

---

## Scope

### In-Scope
- 8 vice category detection
- Intensity scoring and tracking
- Profile persistence
- Prompt injection for vice expression
- Ethical boundary enforcement

### Out-of-Scope
- User-facing vice settings/configuration (player portal potential)
- Vice-based matchmaking or recommendations
- A/B testing different vice expressions
- Vice analytics dashboard (internal)

---

## Infrastructure Dependencies

This feature depends on the following infrastructure specs:

| Spec | Dependency | Usage |
|------|------------|-------|
| 009-database-infrastructure | Vice preference storage | VicePreferenceRepository.update_intensity(), VicePreferenceRepository.get_active() |

**Database Tables Used**:
- `user_vice_preferences` (category, intensity_level, engagement_score, discovered_at)

**No API Endpoints** - Internal engine, vice injection via prompt

**No Background Tasks** - Vice detection is per-interaction

---

## Risks & Mitigations

### Risk 1: Stereotyping Users
**Description**: System pigeonholes users into single vice too quickly
**Likelihood**: Medium (0.5) | **Impact**: Medium (5) | **Score**: 2.5
**Mitigation**: Multi-vice support, slow intensity changes, periodic re-probing

### Risk 2: Inappropriate Content
**Description**: Vice expression crosses content policy lines
**Likelihood**: Low (0.2) | **Impact**: High (8) | **Score**: 1.6
**Mitigation**: Hard limits in prompt, content filtering layer, testing

### Risk 3: Detection Errors
**Description**: System detects wrong vices from ambiguous signals
**Likelihood**: Medium (0.5) | **Impact**: Medium (5) | **Score**: 2.5
**Mitigation**: High confidence threshold, require multiple signals, easy correction

---

## Success Metrics

- Detection accuracy: 70%+ match with human labelers
- Personalization satisfaction: Users feel Nikita "gets them" (qualitative)
- Profile diversity: Users distributed across all 8 categories (not clustered)
- Engagement correlation: Higher vice alignment → higher session length

---

**Version**: 1.0
**Last Updated**: 2025-11-28

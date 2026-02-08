> **SUPERSEDED**: This spec has been replaced by Spec 042. See specs/042-unified-pipeline/spec.md for current requirements.

# Spec 039: Unified Context Engine & Intelligent Prompt Generation

## Status: IMPLEMENTATION COMPLETE (90%)

| Attribute | Value |
|-----------|-------|
| **Version** | 1.0.0 |
| **Created** | 2026-01-28 |
| **Status** | Phase 5 (Cleanup) Pending |
| **Dependencies** | Specs 021-028 (Humanization), Spec 030 (Text Continuity) |

---

## 1. Problem Statement

**Current State**: System prompt generation produces only ~424 tokens via mechanical template substitution across 12+ scattered modules (meta_prompts/, context/, life_simulation/, emotional_state/, prompts/, etc.).

**Desired State**: Unified 2-layer architecture producing 6K-15K token rich, narrative, human-feeling prompts with intelligent agentic generation.

**Business Impact**:
- Current prompts lack depth for engaging AI girlfriend experience
- Scattered architecture increases maintenance burden
- No past-prompt continuity or time-awareness
- Voice/text parity at only 70%

---

## 2. User Requirements

### FR-001: Intelligent Agentic Generation
The system SHALL use an LLM (Claude Sonnet 4.5) to GENERATE prompts dynamically, not mechanical template substitution.

### FR-002: Past Prompt Continuity
The system SHALL reference previous prompts (last 3-5) to maintain narrative coherence.

### FR-003: Time-Awareness
The system SHALL adapt based on hours/days since last contact (recency interpretation: "just talked", "been a while", "worried").

### FR-004: Comprehensive Memory Queries
The system SHALL query all 3 Graphiti graphs (user, relationship, nikita) for context.

### FR-005: Social Circle Context
The system SHALL surface friends with backstories in prompts.

### FR-006: Knowledge Base Access
The system SHALL load static persona files (base_personality.yaml, chapter configs).

### FR-007: Unified Architecture
The system SHALL consolidate scattered modules into single `nikita/context_engine/` module.

### FR-008: Voice/Text Parity
The system SHALL use the same ContextPackage for both voice and text modalities.

### FR-009: Adaptive Token Budget
The system SHALL produce 6K-10K tokens typically, up to 15K for complex situations.

---

## 3. Non-Functional Requirements

### NFR-001: Token Budget Compliance
- Input context: ~10K tokens
- Output target: 6K-15K tokens (adaptive)
- Core persona: Always included (2000 tokens)

### NFR-002: Latency
- Context collection: <500ms
- Prompt generation: <5000ms total
- Graceful degradation on collector failures

### NFR-003: Caching
- Static content (persona, chapter rules): Cache 1h
- Dynamic content (mood, threads): Fresh each request
- Expected cost reduction: 85-90%

---

## 4. Architecture

### 4.1 Two-Layer Design

```
┌─────────────────────────────────────────────────────────────┐
│              LAYER 1: ContextEngine                         │
│  8 typed collectors → ContextPackage (~5K tokens)           │
└─────────────────────┬───────────────────────────────────────┘
                      │ RunContext[ContextPackage]
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              LAYER 2: PromptGenerator                       │
│  Claude Sonnet 4.5 → PromptBundle (6K-15K tokens)           │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              PromptAssembler                                │
│  Static persona + chapter rules + generated blocks          │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Module Structure

```
nikita/context_engine/
├── __init__.py          # Exports
├── models.py            # ContextPackage, PromptBundle
├── engine.py            # ContextEngine (Layer 1)
├── generator.py         # PromptGenerator (Layer 2)
├── assembler.py         # PromptAssembler
├── router.py            # V1/V2 feature-flagged routing
├── collectors/          # 8 typed collectors
│   ├── base.py          # BaseCollector
│   ├── database.py      # Users, metrics, vices
│   ├── graphiti.py      # 3 knowledge graphs
│   ├── humanization.py  # Specs 022-028
│   ├── history.py       # Threads, thoughts, summaries
│   ├── knowledge.py     # Static YAML files
│   ├── temporal.py      # Time calculations
│   ├── social.py        # Social circle
│   └── continuity.py    # Past prompts
└── validators/          # Output validators
    ├── coverage.py      # Required sections
    ├── guardrails.py    # No stage directions
    └── speakability.py  # Voice-safe
```

---

## 5. User Stories

### US-1: Context Collection
**As a** system prompt generator
**I want** unified context from all sources
**So that** prompts have comprehensive, accurate information

**Acceptance Criteria**:
- AC-1.1: 8 collectors implemented (database, graphiti, humanization, history, knowledge, temporal, social, continuity)
- AC-1.2: Parallel collection with <500ms timeout per collector
- AC-1.3: Graceful degradation if any collector fails
- AC-1.4: ContextPackage model with all typed fields

### US-2: Prompt Generation
**As a** Nikita agent
**I want** intelligent LLM-generated prompts
**So that** responses feel natural and human

**Acceptance Criteria**:
- AC-2.1: PromptGenerator uses Claude Sonnet 4.5
- AC-2.2: Text prompts: 6K-15K tokens
- AC-2.3: Voice prompts: 800-1500 tokens (speakable)
- AC-2.4: Past prompt continuity reference
- AC-2.5: Output validators pass (coverage, guardrails, speakability)

### US-3: Migration & Integration
**As a** developer
**I want** feature-flagged routing between old and new engines
**So that** migration is safe and reversible

**Acceptance Criteria**:
- AC-3.1: Router supports DISABLED, SHADOW, CANARY_*, ENABLED, ROLLBACK flags
- AC-3.2: Instant rollback via environment variable
- AC-3.3: Shadow mode runs both engines and compares
- AC-3.4: Fallback prompts on any v2 failure

---

## 6. Data Models

### ContextPackage (Layer 1 Output)

| Field | Type | Description |
|-------|------|-------------|
| user_id | UUID | User identifier |
| conversation_id | UUID | None | Current conversation |
| local_time | datetime | User's local time |
| hours_since_last_contact | float | Time since last message |
| recency_interpretation | str | "just talked", "been a while", etc. |
| chapter | int | Current chapter (1-5) |
| relationship_score | float | Score 0-100 |
| engagement_state | str | Engagement state (6 states) |
| user_facts | list[str] | Top 50 from user graph |
| relationship_episodes | list[str] | Top 50 from relationship graph |
| nikita_events | list[str] | Top 50 from nikita graph |
| social_circle | list[dict] | Friends with backstories |
| nikita_mood_4d | dict | Arousal, valence, dominance, intimacy |
| open_threads | list[dict] | Active conversation threads |
| past_prompts | list[dict] | Last 3-5 prompts |
| persona_canon | str | Base personality YAML |
| vice_profile | dict | User's vice preferences |

### PromptBundle (Layer 2 Output)

| Field | Type | Description |
|-------|------|-------------|
| text_system_prompt_block | str | Text prompt (6K-12K tokens) |
| voice_system_prompt_block | str | Voice prompt (800-1500 tokens) |
| coverage_notes | str | None | What was included |

---

## 7. Validators

### Coverage Validator
Required sections for text prompts:
1. DO NOT REVEAL
2. TEXTING STYLE RULES
3. PRIVATE CONTEXT — CURRENT STATE
4. PRIVATE CONTEXT — WHAT'S ON MY MIND
5. PRIVATE CONTEXT — MY LIFE LATELY
6. PRIVATE CONTEXT — WHERE WE STAND
7. PRIVATE CONTEXT — MY WORLD
8. PRIVATE CONTEXT — FOLLOW UPS
9. PRIVATE CONTEXT — WHAT I'M REALLY FEELING
10. RESPONSE PLAYBOOK

### Guardrails Validator
Banned patterns:
- Stage directions: `*smiles*`
- Actions: `(laughs)`
- Meta brackets: `[action]`
- Meta terms: "system prompt", "tokens", "LLM"

### Speakability Validator (Voice)
- No emojis
- Max 2000 characters
- No special formatting

---

## 8. Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| Prompt tokens | ~424 | 6,000-15,000 |
| Past prompt reference | 0% | 100% |
| Time-awareness | 0% | 100% |
| Voice/text parity | 70% | 100% |
| Coverage validation | 0% | 100% |
| Guardrail pass rate | Unknown | >99% |

---

## 9. Test Requirements

- **Unit Tests**: 231 tests (models, collectors, engine, generator, validators, assembler, router)
- **Integration Tests**: End-to-end context collection and prompt generation
- **Regression Tests**: Ensure old functionality still works via router

---

## 10. Migration Strategy

| Phase | Traffic | Description |
|-------|---------|-------------|
| DISABLED | 100% v1 | Default (current) |
| SHADOW | Both (return v1) | A/B comparison |
| CANARY_5 | 5% v2 | Initial rollout |
| CANARY_25 | 25% v2 | Moderate rollout |
| CANARY_50 | 50% v2 | Half traffic |
| ENABLED | 100% v2 | Full migration |
| ROLLBACK | 100% v1 | Emergency |

---

## 11. Deprecation Plan

| Module | Action | Timeline |
|--------|--------|----------|
| nikita/prompts/ | DELETE | Phase 5 |
| nikita/meta_prompts/ | DEPRECATE | After 100% v2 |
| nikita/context/template_generator.py | DEPRECATE | After 100% v2 |

---

## 12. Related Specifications

- **Spec 029**: Context Comprehensive (superseded by this spec)
- **Spec 030**: Text Continuity (integrated via HistoryCollector)
- **Specs 021-028**: Humanization (consumed by HumanizationCollector)
- **Spec 040**: Canon Alignment (future - persona consistency)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-28 | Initial specification (extracted from plan.md) |

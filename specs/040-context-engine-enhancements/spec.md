# Feature Specification: Context Engine Enhancements

**Spec ID**: 040-context-engine-enhancements
**Created**: 2026-01-29
**Status**: Approved
**Priority**: P1

---

## Summary

Enhance the unified context engine (Spec 039) to fully utilize available backstory data and track onboarding state for improved personalization.

**Problem Statement**: The context engine currently uses only 2 of 5 backstory fields (`venue`, `the_moment`), missing rich narrative context from `how_we_met`, `unresolved_hook`, and `tone`. Additionally, onboarding state fields (`onboarding_status`, `onboarded_at`, `onboarding_profile`) exist in the database but are not exposed in `ContextPackage`, preventing differentiated experiences for new vs returning users.

**Value Proposition**: Full backstory narratives enable more immersive, personalized conversations. Onboarding awareness allows Nikita to reference early relationship moments and adapt behavior appropriately for user relationship age.

### CoD^Σ Overview

**System Model**:
```
User → Context Engine → ContextPackage → PromptGenerator → Personalized Prompt
  ↓         ↓               ↓                  ↓                    ↓
Profile  8 Collectors   Structured Data    Sonnet 4.5         Rich Narrative

Gap Analysis: BackstoryContext uses 2/5 fields@models.py:134-147
              ContextPackage missing onboarding fields@models.py:164-241
              _format_backstory is 1-line@generator.py:187
```

**Value Chain**:
```
Full Backstory (5 fields) → Richer prompts → More immersive conversations
Onboarding State         → Relationship age awareness → Adaptive behavior
```

---

## Functional Requirements

### FR-001: Full Backstory Narrative Expansion
**Priority**: Must Have
**Description**: System MUST format all 5 backstory fields (`venue`, `how_we_met`, `the_moment`, `unresolved_hook`, `tone`) into a rich narrative section in the generated prompt.
**Rationale**: Backstory fields are collected during onboarding but only 2/5 are used, wasting valuable personalization data.

### FR-002: Onboarding State Tracking
**Priority**: Must Have
**Description**: System MUST expose onboarding state in ContextPackage with fields: `is_new_user` (boolean), `days_since_onboarding` (int), `onboarding_profile_summary` (string).
**Rationale**: Enables differentiated experiences based on relationship maturity.

### FR-003: Bullet Point Formatting
**Priority**: Should Have
**Description**: System SHOULD format backstory as bullet points rather than prose for 62% token efficiency improvement (per research findings).
**Rationale**: Bullet points are more token-efficient and easier for LLM to parse.

### FR-004: Progressive Disclosure
**Priority**: Should Have
**Description**: System SHOULD include backstory detail proportional to relationship age (full detail for new users, condensed for established relationships).
**Rationale**: Prevents context bloat while maintaining personalization.

### FR-005: Token Budget Adjustment
**Priority**: Should Have
**Description**: System SHOULD increase token budget from 10K to 11K to accommodate new sections without cutting existing context.
**Rationale**: New backstory and onboarding sections add ~200-300 tokens.

---

## Non-Functional Requirements

### NFR-001: Performance
- Backstory formatting adds <5ms to prompt generation
- No additional database queries (uses existing collector data)

### NFR-002: Backwards Compatibility
- Users without backstory get graceful fallback ("Standard meeting story")
- Users without onboarding data get sensible defaults (`is_new_user=True`, `days_since_onboarding=0`)

### NFR-003: Token Efficiency
- Bullet point format saves 62% tokens vs prose (research-backed)
- Total backstory section: ≤300 tokens

---

## User Stories

### US-1: Backstory Narrative Expansion (Priority: P1 - Must-Have)
```
Nikita system → full backstory in prompts → immersive conversations
```
**Why P1**: Core personalization - backstory data is already collected but underutilized.

**Acceptance Criteria**:
- **AC-040-001**: Given a user with complete backstory (5 fields), When prompt is generated, Then all 5 fields appear in backstory section
- **AC-040-002**: Given a user with partial backstory (2 fields), When prompt is generated, Then only available fields appear (no placeholders)
- **AC-040-003**: Given a user with no backstory, When prompt is generated, Then default text "Standard meeting story" appears
- **AC-040-004**: Given any backstory, When formatted, Then bullet points are used (not prose)

**Independent Test**: Generate prompt for test user with full backstory, verify 5 bullet points in output.
**Dependencies**: None (S1 ⊥ {S2, S3})

### US-2: Onboarding State Tracking (Priority: P1 - Must-Have)
```
Nikita system → onboarding awareness → relationship-age-appropriate behavior
```
**Why P1**: Enables progressive relationship dynamics and prevents treating 3-month users like first-time users.

**Acceptance Criteria**:
- **AC-040-005**: Given a user onboarded today, When ContextPackage is built, Then `is_new_user=True` and `days_since_onboarding=0`
- **AC-040-006**: Given a user onboarded 30 days ago, When ContextPackage is built, Then `is_new_user=False` and `days_since_onboarding=30`
- **AC-040-007**: Given a user with `onboarding_profile` JSONB data, When ContextPackage is built, Then `onboarding_profile_summary` contains key preferences
- **AC-040-008**: Given a user without onboarding data, When ContextPackage is built, Then defaults apply (`is_new_user=True`, `days_since_onboarding=0`, empty summary)

**Independent Test**: Query ContextPackage for users with different onboarding dates, verify field values.
**Dependencies**: None (S2 ⊥ {S1, S3})

### US-3: Token Budget & Documentation (Priority: P2 - Important)
```
Developer → updated token budget → accommodate new context sections
```
**Why P2**: Supports US-1 and US-2 by ensuring new sections don't cause truncation.

**Acceptance Criteria**:
- **AC-040-009**: Given new sections added, When token budget is checked, Then limit is 11,000 tokens (was 10,000)
- **AC-040-010**: Given documentation files, When reviewed, Then memory/memory-system-architecture.md reflects new fields
- **AC-040-011**: Given nikita/context_engine/CLAUDE.md, When reviewed, Then backstory and onboarding fields are documented

**Independent Test**: Run token estimation on full ContextPackage with new fields, verify within budget.
**Dependencies**: P1 complete (documentation references implemented features)

---

## Intelligence Evidence

### Queries Executed

```bash
# Backstory model analysis
rg "class BackstoryContext" nikita/context_engine/models.py -A 20
# Result: 5 fields defined (venue, how_we_met, the_moment, unresolved_hook, tone)

# Current formatting
rg "_format_backstory|backstory" nikita/context_engine/generator.py
# Result: Line 187 uses only venue + the_moment

# Onboarding fields in DB
rg "onboarding_status|onboarded_at|onboarding_profile" nikita/db/models/user.py
# Result: 3 fields exist in User model
```

### Findings

**Related Features**:
- `models.py:134-147` - BackstoryContext model with 5 fields
- `generator.py:187` - 1-line format using 2/5 fields
- `collectors/database.py` - DatabaseCollector already loads user data

**Existing Patterns**:
- `models.py:164-241` - ContextPackage structure for adding new fields
- Bullet point formatting used elsewhere for token efficiency

### Assumptions

- ASSUMPTION: All 5 backstory fields are populated during onboarding (validated against onboarding flow)
- ASSUMPTION: Token budget increase to 11K is acceptable (minimal cost impact)

### CoD^Σ Trace

```
Plan (Section 16) ≫ code-analysis → requirements
Evidence: models.py:134-147, generator.py:187, prompt-researcher findings
GAP-002 (backstory) + GAP-003 (onboarding) from orchestration synthesis
```

---

## Scope

### In-Scope Features
- Expand `_format_backstory()` to use all 5 BackstoryContext fields
- Add `is_new_user`, `days_since_onboarding`, `onboarding_profile_summary` to ContextPackage
- Update DatabaseCollector to extract onboarding data
- Update PromptGenerator template to include expanded backstory
- Increase token budget from 10K to 11K
- Update documentation

### Out-of-Scope
- Social circle integration (Spec 041)
- Voice onboarding dynamic context (Spec 041)
- Changes to onboarding flow itself
- New database migrations (use existing fields)

### Future Phases
- **Spec 041**: Social circle field fix + voice onboarding dynamic context

---

## Constraints

### Technical Constraints
- Must not add database queries (performance budget)
- Must maintain backwards compatibility with v1 fallback
- Must work with existing ContextPackage structure

### Business Constraints
- Implementation budget: 8 hours
- Must deploy to production within same day

---

## Risks & Mitigations

### Risk 1: Token Budget Overflow
**Likelihood (p)**: Low (0.2)
**Impact**: Medium (5)
**Risk Score**: r = 1.0
**Mitigation**:
- Bullet points save 62% tokens vs prose
- Progressive disclosure reduces detail for established users
- 1K buffer (10K → 11K) accommodates growth

### Risk 2: Missing Backstory Data
**Likelihood (p)**: Medium (0.5)
**Impact**: Low (2)
**Risk Score**: r = 1.0
**Mitigation**:
- Graceful fallback to "Standard meeting story"
- Partial data handled (show only available fields)
- Tests cover all edge cases

---

## Success Metrics

### User-Centric Metrics
- Backstory mentioned in 100% of prompts for users with backstory data
- New vs returning user differentiation visible in prompt context

### Technical Metrics
- All 17 tests pass
- Token usage within 11K budget
- No performance regression (prompt generation <100ms)

### Business Metrics
- Improved conversation immersion (qualitative)
- Foundation for Spec 041 enhancements

---

## Open Questions

None - all clarified during orchestration planning session.

---

## Stakeholders

**Owner**: Development team
**Created By**: Claude (SDD automation)
**Reviewers**: User (plan approval)

---

## Approvals

- [x] User: Approved via plan mode (2026-01-29)

---

## Specification Checklist

**Before Planning**:
- [x] All [NEEDS CLARIFICATION] resolved (0 of 3)
- [x] All user stories have ≥2 acceptance criteria
- [x] All user stories have priority (P1, P1, P2)
- [x] All user stories have independent test criteria
- [x] P1 stories define MVP scope
- [x] No technology implementation details in spec
- [x] Intelligence evidence provided (CoD^Σ traces)
- [x] Stakeholder approvals obtained

**Status**: Approved - Ready for Planning

---

**Version**: 1.0
**Last Updated**: 2026-01-29
**Next Step**: Auto-chain to /plan (Phase 5)

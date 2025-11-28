---
description: "Requirements quality validation template - 'Unit tests for English' across 9 quality dimensions"
---

# Requirements Quality Checklist

**Feature**: [feature-id]
**Artifact**: [spec.md / plan.md / tasks.md]
**Evaluated**: [YYYY-MM-DD]
**Evaluator**: [Skill/Command that performed validation]

---

## Purpose: "Unit Tests for English"

This checklist validates the **QUALITY OF REQUIREMENTS** themselves, not implementation correctness.

**Testing Requirements, Not Implementation**:
- ✅ "Are performance requirements quantified with specific metrics?"
- ✅ "Is 'fast loading' defined with measurable criteria?"
- ✅ "Are error handling requirements complete for all failure modes?"
- ❌ NOT "Verify the page loads quickly"
- ❌ NOT "Test error handling works correctly"
- ❌ NOT "Confirm the API returns expected data"

**Metaphor**: If your spec is code written in English, this checklist is its unit test suite.

---

## Quality Scoring System

Each dimension scored 0-10:
- **0-3**: Critical gaps, unusable for implementation
- **4-6**: Significant issues, needs work before implementation
- **7-8**: Good quality, minor improvements recommended
- **9-10**: Excellent quality, ready for implementation

**Overall Quality** = Average of all dimension scores
**Implementation Ready**: Overall score ≥ 7.0

---

## Quality Assessment Workflow (CoD^Σ)
<!-- Document how 9-dimensional quality assessment composes into readiness determination -->

**Assessment Pipeline:**
```
Step 1: ∥ DimensionEvaluation (parallel)
  ↳ D1: Requirement Completeness [0-10]
  ↳ D2: Requirement Clarity [0-10]
  ↳ D3: Requirement Consistency [0-10]
  ↳ D4: Acceptance Criteria Quality [0-10]
  ↳ D5: Scenario Coverage [0-10]
  ↳ D6: Edge Case Coverage [0-10]
  ↳ D7: Non-Functional Requirements [0-10]
  ↳ D8: Dependencies & Assumptions [0-10]
  ↳ D9: Ambiguities & Conflicts [0-10]
  ↳ Output: [dimension_scores[1-9]]

Step 2: ⊕ ScoreAggregation
  ↳ Formula: overall_score = Σ(dimension_scores) / 9
  ↳ Output: [overall_score]

Step 3: ∘ ReadinessClassification
  ↳ Logic: if overall_score ≥ 7.0 → "READY"
  ↳ Logic: else if overall_score ≥ 5.0 → "READY WITH RISKS"
  ↳ Logic: else → "NOT READY"
  ↳ Output: [readiness_status]

Step 4: → ActionRecommendation
  ↳ Input: [readiness_status, critical_issues]
  ↳ Mapping: status → next_actions
  ↳ Output: [actionable_guidance]
```

**Composition Formula:**
```
DimensionEvaluations ∥ [D1-D9] ⊕ ScoreAggregation ∘ ReadinessClassification → ActionRecommendation
```

**Decision Flow:**
```
Overall Score?
├─ ≥ 7.0 → ✅ READY
│   └─ Action: Proceed to /implement
│
├─ 5.0-6.9 → ⚠️ READY WITH RISKS
│   └─ Action: Document risks, proceed with caution
│
└─ < 5.0 → ❌ NOT READY
    └─ Action: Refine spec → clarify → re-validate

Critical Issues?
├─ YES (any dimension) → ⚠️ Blocks implementation even if score ≥ 7.0
└─ NO → Proceed based on overall score
```

**Quality Gate Formula:**
```
Implementation_Ready := (overall_score ≥ 7.0) ∧ (critical_issues = 0)
```

---

## Dimension 1: Requirement Completeness (0-10)

**Score**: [X/10]

**Definition**: Are all necessary requirements present and documented?

### Checklist Items

#### Functional Requirements
- [ ] Are all user-facing features identified and documented?
- [ ] Are all system behaviors explicitly specified?
- [ ] Are all API endpoints/interfaces defined?
- [ ] Are all data entities and their relationships documented?
- [ ] Are all business rules and validation logic specified?

#### Non-Functional Requirements (NFRs)
- [ ] Are performance requirements defined (latency, throughput)?
- [ ] Are security requirements specified (auth, encryption, audit)?
- [ ] Are scalability requirements documented (load, concurrency)?
- [ ] Are availability requirements defined (uptime, failover)?
- [ ] Are accessibility requirements specified (WCAG, keyboard nav)?
- [ ] Are usability requirements defined (UX, responsiveness)?
- [ ] Are maintainability requirements documented?

#### Edge Cases & Scenarios
- [ ] Are error scenarios documented for all operations?
- [ ] Are boundary conditions specified (min/max, empty states)?
- [ ] Are concurrent operation scenarios addressed?
- [ ] Are recovery scenarios defined for failures?
- [ ] Are partial success/failure scenarios documented?

#### Dependencies & Integration
- [ ] Are external system dependencies documented?
- [ ] Are integration requirements specified?
- [ ] Are data migration requirements defined (if applicable)?
- [ ] Are backward compatibility requirements specified?

**Critical Gaps Identified**:
- [List any critical missing requirements]

---

## Dimension 2: Requirement Clarity (0-10)

**Score**: [X/10]

**Definition**: Are requirements specific, unambiguous, and measurable?

### Checklist Items

#### Quantification
- [ ] Are vague adjectives replaced with measurable criteria?
  - "Fast" → "< 200ms p95 latency"
  - "Scalable" → "Support 10K concurrent users"
  - "Secure" → "HTTPS with TLS 1.3, OAuth 2.0 authentication"
- [ ] Are all performance metrics quantified?
- [ ] Are all size/limit constraints specified with numbers?
- [ ] Are all timing requirements defined precisely?

#### Terminology
- [ ] Is domain-specific terminology clearly defined?
- [ ] Are acronyms and abbreviations explained?
- [ ] Is technical jargon minimized or explained?
- [ ] Are all terms used consistently throughout?

#### Specificity
- [ ] Are user actions described with specific verbs?
- [ ] Are UI elements described with specific attributes?
- [ ] Are data formats explicitly specified (JSON, XML, CSV)?
- [ ] Are validation rules precisely defined?
- [ ] Are error messages specified (not just "show error")?

#### Avoiding Ambiguity
- [ ] Are all "should", "may", "can" replaced with "MUST", "MUST NOT", "MAY" (RFC 2119)?
- [ ] Are all conditional statements clearly defined (if/then)?
- [ ] Are all "etc.", "and so on" replaced with exhaustive lists?
- [ ] Are all pronouns replaced with explicit references?

**Vague Language Detected**:
- spec.md:L[X] - "[vague term]" needs quantification: [suggested specific criteria]
- spec.md:L[X] - "[ambiguous statement]" needs clarification: [suggested precise wording]

---

## Dimension 3: Requirement Consistency (0-10)

**Score**: [X/10]

**Definition**: Do requirements align without conflicts or contradictions?

### Checklist Items

#### Internal Consistency
- [ ] Are terminology and naming conventions consistent throughout?
- [ ] Do requirements align across different sections?
- [ ] Are data entity definitions consistent everywhere mentioned?
- [ ] Are validation rules consistent for similar inputs?
- [ ] Are error handling patterns consistent across operations?

#### Cross-Artifact Consistency
- [ ] Does plan.md align with spec.md requirements?
- [ ] Do tasks.md items map to spec.md user stories?
- [ ] Are data models in plan.md consistent with spec.md entities?
- [ ] Are API contracts in plan.md consistent with spec.md interfaces?

#### Terminology Drift
- [ ] Is the same concept named identically everywhere?
  - Example: "user profile" vs "account settings" vs "user account"
- [ ] Are verbs consistent for similar actions?
  - Example: "upload" vs "import" vs "transfer"

#### Constraint Consistency
- [ ] Are size/limit constraints consistent across related operations?
- [ ] Are timeout values consistent for similar operations?
- [ ] Are validation rules consistent for similar data types?

**Inconsistencies Detected**:
- spec.md:L[X] vs plan.md:L[Y] - [term A] vs [term B]: [recommendation]
- spec.md:L[X] vs spec.md:L[Y] - Conflicting requirements: [explanation]

---

## Dimension 4: Acceptance Criteria Quality (0-10)

**Score**: [X/10]

**Definition**: Are success criteria measurable, testable, and complete?

### Checklist Items

#### Testability
- [ ] Are all acceptance criteria objectively verifiable?
- [ ] Can success/failure be determined without subjective judgment?
- [ ] Are all criteria automated-test-friendly (no manual interpretation)?
- [ ] Are all criteria independent (can be tested separately)?

#### Completeness (Article III: ≥2 ACs per task)
- [ ] Does each requirement have ≥2 testable acceptance criteria?
- [ ] Does each user story have ≥2 testable acceptance criteria?
- [ ] Does each task have ≥2 testable acceptance criteria?
- [ ] Are acceptance criteria sufficient to verify requirement satisfaction?

#### Measurability
- [ ] Are all "user-friendly" criteria replaced with measurable UX metrics?
- [ ] Are all "fast" criteria replaced with specific timing thresholds?
- [ ] Are all "secure" criteria replaced with specific security measures?
- [ ] Are all visual criteria replaced with measurable properties?

#### Coverage
- [ ] Are acceptance criteria defined for happy path?
- [ ] Are acceptance criteria defined for error scenarios?
- [ ] Are acceptance criteria defined for edge cases?
- [ ] Are acceptance criteria defined for non-functional requirements?

**Acceptance Criteria Issues**:
- Task T[X] - Only [N] ACs (needs ≥2): [recommendation]
- Requirement R[X] - AC[X] not objectively verifiable: [how to make testable]
- User Story P[X] - Missing AC for [scenario]: [suggested AC]

---

## Dimension 5: Scenario Coverage (0-10)

**Score**: [X/10]

**Definition**: Are all user journeys, flows, and scenarios addressed?

### Checklist Items

#### Primary Scenarios (Happy Path)
- [ ] Are all primary user journeys documented?
- [ ] Are all core workflows specified end-to-end?
- [ ] Are all main success paths defined?
- [ ] Are all expected inputs and outputs specified?

#### Alternate Scenarios
- [ ] Are all alternative paths documented?
- [ ] Are all optional features and their conditions specified?
- [ ] Are all user choice points and their consequences defined?
- [ ] Are all variation scenarios addressed?

#### Exception/Error Scenarios
- [ ] Are all error conditions documented?
- [ ] Are all validation failures specified?
- [ ] Are all timeout scenarios addressed?
- [ ] Are all network failure scenarios defined?
- [ ] Are all external system failure scenarios documented?

#### Recovery Scenarios
- [ ] Are all retry/rollback requirements specified?
- [ ] Are all partial failure recovery paths defined?
- [ ] Are all data consistency recovery scenarios addressed?
- [ ] Are all system restart/resume scenarios documented?

#### Concurrent/Race Conditions
- [ ] Are all concurrent user interaction scenarios addressed?
- [ ] Are all race condition scenarios documented?
- [ ] Are all locking/synchronization requirements specified?

**Scenario Gaps Identified**:
- Missing [scenario type]: [description] - [recommendation]
- Incomplete [scenario type] at spec.md:L[X]: [what needs to be added]

---

## Dimension 6: Edge Case Coverage (0-10)

**Score**: [X/10]

**Definition**: Are boundary conditions and edge cases defined?

### Checklist Items

#### Data Boundaries
- [ ] Are minimum/maximum value requirements specified?
- [ ] Are empty/null/zero scenarios documented?
- [ ] Are overflow/underflow scenarios addressed?
- [ ] Are string length limits defined?
- [ ] Are array/list size limits specified?

#### State Boundaries
- [ ] Are first-time user scenarios documented?
- [ ] Are no-data/empty-state scenarios specified?
- [ ] Are maximum capacity scenarios addressed?
- [ ] Are transition state requirements defined?

#### Time Boundaries
- [ ] Are timeout scenarios documented?
- [ ] Are retry limit scenarios specified?
- [ ] Are expiration scenarios addressed?
- [ ] Are time zone edge cases documented?

#### Permission Boundaries
- [ ] Are unauthorized access scenarios specified?
- [ ] Are insufficient permission scenarios documented?
- [ ] Are permission change mid-operation scenarios addressed?

#### Resource Limits
- [ ] Are out-of-memory scenarios documented?
- [ ] Are disk-full scenarios specified?
- [ ] Are rate-limit scenarios addressed?
- [ ] Are quota-exceeded scenarios defined?

**Edge Cases Missing**:
- [Edge case category]: [specific scenario] - [where to document]

---

## Dimension 7: Non-Functional Requirements (0-10)

**Score**: [X/10]

**Definition**: Are quality attributes adequately specified?

### Checklist Items

#### Performance
- [ ] Are response time requirements quantified?
- [ ] Are throughput requirements specified (requests/second)?
- [ ] Are load/stress test criteria defined?
- [ ] Are resource utilization limits specified (CPU, memory)?

#### Security
- [ ] Are authentication requirements specified?
- [ ] Are authorization requirements defined?
- [ ] Are encryption requirements documented (at-rest, in-transit)?
- [ ] Are audit/logging requirements specified?
- [ ] Are data privacy requirements defined (GDPR, CCPA)?

#### Scalability
- [ ] Are user load requirements quantified?
- [ ] Are data growth requirements specified?
- [ ] Are horizontal scaling requirements defined?

#### Reliability
- [ ] Are availability requirements specified (uptime %)?
- [ ] Are error rate thresholds defined?
- [ ] Are recovery time objectives (RTO) specified?
- [ ] Are recovery point objectives (RPO) specified?

#### Accessibility
- [ ] Are WCAG compliance levels specified?
- [ ] Are keyboard navigation requirements defined?
- [ ] Are screen reader requirements documented?
- [ ] Are color contrast requirements specified?

#### Usability
- [ ] Are user experience requirements measurable?
- [ ] Are responsive design requirements specified?
- [ ] Are loading state requirements defined?
- [ ] Are error message requirements specified?

#### Maintainability
- [ ] Are code quality requirements defined?
- [ ] Are documentation requirements specified?
- [ ] Are testing requirements documented?

**NFR Gaps Identified**:
- [NFR category]: [what is missing] - [priority: CRITICAL/HIGH/MEDIUM/LOW]

---

## Dimension 8: Dependencies & Assumptions (0-10)

**Score**: [X/10]

**Definition**: Are dependencies documented and assumptions validated?

### Checklist Items

#### External Dependencies
- [ ] Are all external systems/APIs documented?
- [ ] Are all third-party services identified?
- [ ] Are all external data sources specified?
- [ ] Are dependency version requirements defined?
- [ ] Are dependency availability requirements specified?

#### Internal Dependencies
- [ ] Are all prerequisite features identified?
- [ ] Are all shared components documented?
- [ ] Are all database schema requirements specified?
- [ ] Are all infrastructure requirements defined?

#### Assumptions
- [ ] Are all technical assumptions explicitly stated?
- [ ] Are all business assumptions documented?
- [ ] Are all user behavior assumptions identified?
- [ ] Are assumptions validated or marked for validation?
- [ ] Are risks associated with assumptions documented?

#### Integration Points
- [ ] Are all integration requirements specified?
- [ ] Are all data exchange formats documented?
- [ ] Are all API contracts defined?
- [ ] Are all authentication mechanisms specified?

**Dependency/Assumption Issues**:
- Undocumented dependency: [what] - [where it should be documented]
- Unvalidated assumption: [what] - [how to validate]
- Missing integration spec: [what] - [what needs to be defined]

---

## Dimension 9: Ambiguities & Conflicts (0-10)

**Score**: [X/10]

**Definition**: Are ambiguities resolved and conflicts identified?

### Checklist Items

#### Unresolved Placeholders
- [ ] Are all TODO markers resolved?
- [ ] Are all TBD items specified?
- [ ] Are all ??? placeholders replaced?
- [ ] Are all FIXME items addressed?
- [ ] Are all [NEEDS CLARIFICATION] markers resolved?

#### Vague Language
- [ ] Are all "approximately" replaced with specific ranges?
- [ ] Are all "about" replaced with exact values?
- [ ] Are all "typically" replaced with precise conditions?
- [ ] Are all "usually" replaced with explicit rules?

#### Undefined References
- [ ] Are all "the system" references made explicit?
- [ ] Are all "the user" references specified (which user role)?
- [ ] Are all "this feature" references unambiguous?
- [ ] Are all "similar to" references precise?

#### Conflicting Requirements
- [ ] Are there contradictory statements in spec?
- [ ] Are there conflicts between spec and plan?
- [ ] Are there conflicts between requirements?
- [ ] Are priority conflicts resolved?

#### Missing Definitions
- [ ] Are all custom terms defined?
- [ ] Are all business concepts explained?
- [ ] Are all technical terms clarified?
- [ ] Are all acronyms expanded on first use?

**Clarification Needed**:
- spec.md:L[X] - [NEEDS CLARIFICATION]: "[ambiguous text]"
  - **Issue**: [why ambiguous]
  - **Suggestion**: [how to clarify]
  - **Priority**: [CRITICAL/HIGH/MEDIUM/LOW]

**Conflicts Detected**:
- spec.md:L[X] vs spec.md:L[Y] - [description of conflict]
- spec.md:L[X] vs plan.md:L[Y] - [description of conflict]

---

## Overall Assessment

### Quality Score Summary

| Dimension | Score | Status | Critical Issues |
|-----------|-------|--------|----------------|
| 1. Completeness | [X/10] | [PASS/FAIL] | [X] |
| 2. Clarity | [X/10] | [PASS/FAIL] | [X] |
| 3. Consistency | [X/10] | [PASS/FAIL] | [X] |
| 4. Acceptance Criteria | [X/10] | [PASS/FAIL] | [X] |
| 5. Scenario Coverage | [X/10] | [PASS/FAIL] | [X] |
| 6. Edge Cases | [X/10] | [PASS/FAIL] | [X] |
| 7. Non-Functional Reqs | [X/10] | [PASS/FAIL] | [X] |
| 8. Dependencies & Assumptions | [X/10] | [PASS/FAIL] | [X] |
| 9. Ambiguities & Conflicts | [X/10] | [PASS/FAIL] | [X] |
| **OVERALL** | **[X/10]** | **[PASS/FAIL]** | **[X]** |

**Scoring Legend**:
- **PASS**: Score ≥ 7.0
- **FAIL**: Score < 7.0

### Implementation Readiness

**Status**: [Choose one]

✅ **READY** (Overall score ≥ 7.0)
- Requirements quality is sufficient for implementation
- Minor improvements can be addressed during development
- All critical issues resolved

⚠️ **READY WITH RISKS** (Overall score 5.0-6.9)
- Significant quality issues present
- Implementation can proceed but with documented risks
- Address high-priority issues during or after implementation

❌ **NOT READY** (Overall score < 5.0)
- Critical quality issues block implementation
- Requirements need substantial revision before proceeding
- Must address issues and re-validate

### Critical Issues Summary

**CRITICAL** (blocks implementation):
- [Issue 1]: [brief description] - [where]
- [Issue 2]: [brief description] - [where]

**HIGH** (significant risk):
- [Issue 1]: [brief description] - [where]
- [Issue 2]: [brief description] - [where]

**MEDIUM** (quality concerns):
- [Issue 1]: [brief description] - [where]

**LOW** (improvements):
- [Issue 1]: [brief description] - [where]

---

## Recommendations

### Immediate Actions (CRITICAL/HIGH)

1. **[Issue Category]**: [Specific action required]
   - **Location**: [file:line]
   - **Current**: [what exists now]
   - **Required**: [what should exist]
   - **Command**: [skill or command to use]

2. **[Issue Category]**: [Specific action required]
   - **Location**: [file:line]
   - **Current**: [what exists now]
   - **Required**: [what should exist]
   - **Command**: [skill or command to use]

### Recommended Improvements (MEDIUM)

- [Improvement 1]: [brief description]
- [Improvement 2]: [brief description]

### Optional Enhancements (LOW)

- [Enhancement 1]: [brief description]
- [Enhancement 2]: [brief description]

---

## Traceability

**Requirement Coverage**: [X]% of requirements have traceable acceptance criteria

**Mapping Status**:
- Requirements with AC mapping: [X]
- Requirements without AC mapping: [X]
- Orphaned ACs (no requirement): [X]

**ID Scheme**: [Does spec have consistent requirement IDs? YES/NO]

**Recommendation**: [If NO, suggest implementing REQ-### or FR-### / NFR-### system]

---

## Next Steps

### If READY
1. Proceed to implementation: `/implement plan.md`
2. Address MEDIUM/LOW issues during development
3. Use this checklist for future requirements validation

### If READY WITH RISKS
1. Document accepted risks
2. Prioritize HIGH issues for early resolution
3. Proceed to implementation with caution
4. Regular validation checkpoints during development

### If NOT READY
1. **Refine specification**: Use specify-feature skill or /feature command
2. **Resolve ambiguities**: Use clarify-specification skill
3. **Regenerate plan**: After spec fixes, run /plan command
4. **Regenerate tasks**: After plan fixes, use generate-tasks skill
5. **Re-validate**: Run quality check again before implementation

---

## Related Templates

- **@.claude/templates/feature-spec.md** - Specification structure
- **@.claude/templates/clarification-checklist.md** - Ambiguity detection
- **@.claude/templates/audit-report.md** - Cross-artifact consistency
- **@.claude/shared-imports/constitution.md** - Quality principles (Article V)

---

**Checklist Generated**: [YYYY-MM-DD HH:MM]
**Review Method**: [Automated/Manual/Hybrid]
**Next Review**: [After addressing CRITICAL/HIGH issues]

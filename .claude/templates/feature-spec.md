---
feature: ###-feature-name
created: YYYY-MM-DD
status: Draft
priority: P1
technology_agnostic: true  # IMPORTANT: No tech stack in spec
constitutional_compliance:
  article_iv: specification_first  # Article IV enforcement
---

# Feature Specification: [Name]

**IMPORTANT**: This specification is TECHNOLOGY-AGNOSTIC. Do not include:
- Tech stack choices (React, Python, etc.)
- Architecture decisions (microservices, monolith, etc.)
- Implementation details ("use REST API", "create database table")

Focus on WHAT and WHY, not HOW.

---

## Summary

[1-2 paragraph overview of what this feature is and why it matters]

**Problem Statement**: [What problem does this solve?]
**Value Proposition**: [What value does this deliver to users?]

### CoD^Σ Overview

**System Model**:
```
User → Feature → Value
  ↓       ↓         ↓
Need  Capability Result

Requirements: R := {FR_i} ⊕ {NFR_j}  (functional ⊕ non-functional)
Priorities: P1 ⇒ MVP, P2 ⇒ enhance, P3 ⇒ future
Stories: ∑(S_i) → Implementation, ∀S_i ⊥ S_j (independent stories)
```

**Value Chain**:
```
Problem ≫ Solution ≫ Implementation → Value_Delivered
  ↓         ↓            ↓               ↓
User_pain  Feature    Tech_plan      User_benefit
```

---

## Functional Requirements

**Constitutional Limit**: Maximum 3 [NEEDS CLARIFICATION] markers (Article IV)

**Guidelines**:
- Use sparingly (clarify most through user dialogue first)
- Be specific ("auth method not specified" not "unclear")
- Include context (why this matters)
- Prioritize resolution (scope > security > UX > technical)

**Format**:
- **FR-001**: System MUST [specific capability, e.g., "allow users to create accounts"]
- **FR-002**: System MUST [NEEDS CLARIFICATION: What is the password complexity requirement? Options: A) 8+ chars, B) 8+ chars + number, C) 8+ chars + number + special]

**Current [NEEDS CLARIFICATION] Count**: 0 / 3

### FR-001: [Requirement Title]
System MUST [specific, testable capability]

**Rationale**: [Why this is required]
**Priority**: [Must Have | Should Have | Nice to Have]

### FR-002: [Requirement Title]
System MUST [capability]

**Rationale**: [Why]
**Priority**:

### FR-003: [Requirement Title]
System MUST [capability]

**Rationale**: [Why]
**Priority**:

---

## Non-Functional Requirements

### Performance
- [e.g., "Response time < 200ms for 95th percentile"]
- [e.g., "Support 1,000 concurrent users"]

### Security
- [e.g., "All data encrypted at rest and in transit"]
- [e.g., "Role-based access control required"]

### Scalability
- [e.g., "Handle 10,000 records initially, scale to 100,000"]

### Availability
- [e.g., "99.9% uptime during business hours"]

### Accessibility
- [e.g., "WCAG 2.1 AA compliant"]

---

## User Stories (CoD^Σ)

**Constitutional Requirement**: Article VII (User-Story-Centric Organization)

**Priority Model** (CoD^Σ):
```
P1 ⇒ MVP (core_value ∧ required)
P2 ⇒ P1.enhance (improves_P1 ∧ ¬blocking)
P3 ⇒ future (nice_to_have)

Independence: ∀S_i, S_j ∈ Stories : S_i ⊥ S_j (each story standalone testable)
```

---

### Story Template (Compact CoD^Σ Format)

**US-[N]**: [Title] **(Priority: P[1|2|3])**
```
Role → Want → Value
[user-type] → [capability] → [benefit]

Why P[N]: [rationale - core MVP | enhances P1 | future nice-to-have]
```

**Acceptance Criteria** (CoD^Σ: state → action → outcome):
- **AC-REQ#-00N**: Given [state], When [action], Then [outcome]
- **AC-REQ#-00M**: Given [state], When [action], Then [outcome]

**Independent Test**: [standalone validation method without other stories]
**Dependencies**: [None | P1 complete | P1 ∧ P2 complete] (CoD^Σ: dep ⇐ this_story)

---

### US-1: [P1 Title] (Priority: P1 - Must-Have)
```
[user] → [core-capability] → [essential-value]
```
**Why P1**: [Core MVP functionality - system unusable without this]

**Acceptance Criteria**:
- **AC-REQ#-001**: Given [initial-state], When [core-action], Then [essential-outcome]
- **AC-REQ#-002**: Given [error-condition], When [action], Then [error-handling]

**Independent Test**: [How to demo P1 works standalone]
**Dependencies**: None (CoD^Σ: S1 ⊥ {S2, S3, ...})

---

### US-2: [P2 Title] (Priority: P2 - Important)
```
[user] → [enhancement-capability] → [improved-value]
```
**Why P2**: [Enhances P1 by [specific-improvement]]

**Acceptance Criteria**:
- **AC-REQ#-003**: Given [state], When [action], Then [enhanced-outcome]
- **AC-REQ#-004**: Given [state], When [action], Then [outcome]

**Independent Test**: [How to demo P2 works standalone (or with P1 as base)]
**Dependencies**: [None | P1 complete] (CoD^Σ: P1 → P2 or P2 ⊥ P1)

---

### US-3: [P3 Title] (Priority: P3 - Nice-to-Have)
```
[user] → [nice-to-have-capability] → [additional-value]
```
**Why P3**: [Future enhancement - not blocking MVP/P2]

**Acceptance Criteria**:
- **AC-REQ#-005**: Given [state], When [action], Then [outcome]
- **AC-REQ#-006**: Given [state], When [action], Then [outcome]

**Independent Test**: [Standalone validation]
**Dependencies**: [None | P1/P2 complete] (CoD^Σ: dependencies → P3)

---

## Intelligence Evidence

**Constitutional Requirement**: Article II (Evidence-Based Reasoning)

### Queries Executed

```bash
# Feature analysis queries
project-intel.mjs --search "<keywords>" --type md --json
# Output: /tmp/spec_intel_patterns.json

project-intel.mjs --overview --json
# Output: /tmp/spec_intel_overview.json
```

### Findings

**Related Features**:
- [file:line] - Description of related feature
- [file:line] - Description of pattern found

**Existing Patterns**:
- [file:line] - How this pattern informs requirements

### Assumptions

- [ASSUMPTION: rationale based on intelligence findings]

### CoD^Σ Trace

```
User description ≫ intel-query ∘ pattern-analysis → requirements
Evidence: /tmp/spec_intel_patterns.json, src/features/*.tsx:23
```

---

## Scope

### In-Scope Features
- [Specific feature/capability 1]
- [Specific feature/capability 2]
- [Specific feature/capability 3]

### Out-of-Scope
- [Thing that might seem related but isn't included]
- [Future enhancement that's separate]
- [Edge case we're explicitly not handling]

### Future Phases
- **Phase 2**: [Features deferred to next phase]
- **Phase 3**: [Features deferred to later]

---

## Constraints

### Business Constraints
- [e.g., "Must launch by Q2"]
- [e.g., "Budget: $X"]
- [e.g., "Must integrate with existing system Y"]

### User Constraints
- [e.g., "Target users are non-technical"]
- [e.g., "Must work on mobile devices"]
- [e.g., "Accessible to users with disabilities"]

### Regulatory Constraints
- [e.g., "GDPR compliance required"]
- [e.g., "HIPAA compliance required"]
- [e.g., "SOC 2 Type II certification required"]

---

## Risks & Mitigations (CoD^Σ)

**Risk Model**:
```
r := p × impact  (risk score)
p ∈ [0,1]        (probability: Low=0.2, Med=0.5, High=0.8)
impact ∈ [1,10]  (magnitude: Low=2, Med=5, High=8)
```

### Risk 1: [Description]
**Likelihood (p)**: [Low:0.2 | Medium:0.5 | High:0.8]
**Impact**: [Low:2 | Medium:5 | High:8]
**Risk Score**: r = [p × impact]
**Mitigation** (CoD^Σ):
```
Risk → Detect → Respond → Resolve
Prevention ⇒ p↓ | Contingency ⇒ impact↓
```
- [Specific mitigation actions]

### Risk 2: [Description]
**Likelihood (p)**: [Low | Medium | High]
**Impact**: [Low | Medium | High]
**Risk Score**: r = [calculated]
**Mitigation**: Risk ⇒ [early-warning] → [fallback] → [recovery]

---

## Success Metrics

### User-Centric Metrics
- [e.g., "User engagement increases by 20%"]
- [e.g., "Task completion time decreases by 30%"]
- [e.g., "User satisfaction score > 4.5/5"]

### Technical Metrics
- [e.g., "Error rate < 1%"]
- [e.g., "API response time < 200ms"]
- [e.g., "Test coverage > 80%"]

### Business Metrics
- [e.g., "Conversion rate increases by 15%"]
- [e.g., "Support tickets decrease by 25%"]
- [e.g., "Time-to-value < 5 minutes"]

---

## Open Questions

- [ ] **Q1**: [Question that needs answering]
  - **Priority**: [Scope | Security | UX | Technical]
  - **Impact**: [What depends on this]
  - **Answer**: [TBD | answer once known]

- [ ] **Q2**: [Question]
  - **Priority**:
  - **Impact**:
  - **Answer**:

---

## Stakeholders

**Owner**: [product owner]
**Created By**: [who wrote this spec]
**Reviewers**: [who needs to approve]
**Informed**: [who needs to know about progress]

---

## Approvals

- [ ] **Product Owner**: [name] - [date]
- [ ] **Engineering Lead**: [name] - [date]
- [ ] **Design Lead**: [name] - [date] (if UI changes)
- [ ] **Security**: [name] - [date] (if security-sensitive)

---

## Specification Checklist

**Before Planning**:
- [ ] All [NEEDS CLARIFICATION] resolved (max 3)
- [ ] All user stories have ≥2 acceptance criteria
- [ ] All user stories have priority (P1, P2, P3)
- [ ] All user stories have independent test criteria
- [ ] P1 stories define MVP scope
- [ ] No technology implementation details in spec
- [ ] Intelligence evidence provided (CoD^Σ traces)
- [ ] Stakeholder approvals obtained

**Status**: [Draft | In Review | Approved | Ready for Planning]

---

**Version**: 1.0
**Last Updated**: [YYYY-MM-DD]
**Next Step**: Use clarify-specification skill to resolve ambiguities, then create-implementation-plan skill

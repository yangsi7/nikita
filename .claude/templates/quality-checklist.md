# Quality Checklist

**Feature**: ###-feature-name
**Created**: YYYY-MM-DD
**Specification**: specs/###-feature-name/spec.md

---

## Purpose

Pre-planning validation to ensure specification quality before technical design.

**Constitutional Authority**: Article V (Template-Driven Quality)

---

## Content Quality

**Check**: Specification is technology-agnostic (no implementation details)

- [ ] No tech stack mentioned (React, Python, etc.)
- [ ] No architecture details (REST API, microservices, etc.)
- [ ] No implementation specifics ("create database table", "use OAuth")
- [ ] Focus is on WHAT and WHY, not HOW

**Status**: [ ] Pass | [ ] Fail

**Violations** (if any):
- [List specific instances of tech details in spec]

---

## Requirement Completeness

**Check**: All requirements are testable, measurable, and bounded

### Testability
- [ ] Each requirement has clear pass/fail criteria
- [ ] Acceptance scenarios use Given/When/Then format
- [ ] No vague language ("fast", "good", "user-friendly")

### Measurability
- [ ] Performance targets are specific (< 200ms, not "fast")
- [ ] Scale is quantified (1000 users, not "many")
- [ ] Success criteria are measurable

### Bounded
- [ ] Scope is clearly defined
- [ ] Out-of-scope items are explicit
- [ ] Edge cases are documented

**Status**: [ ] Pass | [ ] Fail

**Issues** (if any):
- [List specific incomplete requirements]

---

## Evidence Quality

**Check**: Specification includes evidence-based reasoning (Article II)

### Intelligence Evidence Section
- [ ] "Intelligence Evidence" section present in specification
- [ ] Queries executed with commands and output paths documented
- [ ] Findings include file:line references (e.g., "src/auth/login.tsx:45")
- [ ] CoD^Σ trace present with composition operators (≫, ∘, →)
- [ ] Evidence sources cited (project-intel.mjs output, MCP queries, etc.)

### Assumptions Documented
- [ ] All assumptions explicitly marked with [ASSUMPTION: rationale]
- [ ] Assumptions based on intelligence findings or domain knowledge
- [ ] No unsupported claims without evidence

### Evidence Examples

**✓ GOOD Evidence**:
```markdown
## Intelligence Evidence

### Queries Executed
```bash
project-intel.mjs --search "auth" --type tsx --json
# Output: /tmp/spec_intel_auth.json
```

### Findings
- src/auth/session.ts:23 - Existing session management with JWT
- src/auth/login.tsx:45 - Current login flow uses email/password

### CoD^Σ Trace
```
User requirement ≫ intel-query ∘ pattern-analysis → specification
Evidence: /tmp/spec_intel_auth.json, src/auth/*.tsx
```
```

**✗ BAD Evidence** (missing):
```markdown
## Intelligence Evidence
N/A - new feature

### Assumptions
- Users want OAuth login
```

**Status**: [ ] Pass | [ ] Fail

**Issues** (if any):
- [List evidence gaps: missing section, no file:line refs, no CoD^Σ trace, etc.]

---

## Feature Readiness

**Check**: Feature has all artifacts needed for planning

### Acceptance Criteria
- [ ] All user stories have ≥2 acceptance criteria
- [ ] All ACs are in Given/When/Then format
- [ ] All ACs are testable and specific

**AC Count**: [total] ([P1 count], [P2 count], [P3 count])

### User Story Quality
- [ ] All stories have priority (P1, P2, P3)
- [ ] All stories have independent test criteria
- [ ] P1 stories define MVP scope

### Clarity
- [ ] [NEEDS CLARIFICATION] count ≤ 3
- [ ] All ambiguities are documented
- [ ] Clarification questions are specific

**[NEEDS CLARIFICATION] Count**: 0 / 3 (max)

**Status**: [ ] Pass | [ ] Fail

**Issues** (if any):
- [List specific readiness gaps]

---

## Overall Assessment

**Content Quality**: [ ] Pass | [ ] Fail
**Requirement Completeness**: [ ] Pass | [ ] Fail
**Evidence Quality**: [ ] Pass | [ ] Fail
**Feature Readiness**: [ ] Pass | [ ] Fail

---

## Decision

**Ready for Planning**: [ ] Yes | [ ] No

**If No, Required Actions**:
1. [Specific fix needed]
2. [Specific fix needed]

**If Yes, Next Step**: Create implementation plan with create-implementation-plan skill

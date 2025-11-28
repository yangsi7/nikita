---
description: "Cross-artifact consistency analysis template for pre-implementation quality gate"
---

# Specification Audit Report

**Feature**: [feature-id]
**Date**: [YYYY-MM-DD HH:MM]
**Audited Artifacts**: spec.md, plan.md, tasks.md
**Constitution Version**: 1.0.0
**Auditor**: /audit command via Claude Code Intelligence Toolkit

---

## Executive Summary

- **Total Findings**: [X]
- **Critical**: [X] | **High**: [X] | **Medium**: [X] | **Low**: [X]
- **Implementation Ready**: [YES/NO]
- **Constitution Compliance**: [PASS/FAIL]
- **Quality Score**: [X/10] (based on severity-weighted findings)

**Overall Assessment**:
[Brief paragraph summary of audit results. Example: "Feature is ready for implementation with minor improvements recommended. All critical gates pass. Constitution compliance achieved."]

**Key Issues**:
- [Most important issue #1]
- [Most important issue #2]
- [Most important issue #3]

---

## Findings

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| C1 | Constitution | CRITICAL | spec.md:L45 | [Article violated]: [description] | [Specific fix] |
| A1 | Ambiguity | HIGH | spec.md:L120 | [What is ambiguous] | [How to clarify] |
| D1 | Duplication | MEDIUM | spec.md:L85, L134 | [What is duplicated] | [How to consolidate] |
| U1 | Underspecification | MEDIUM | plan.md:L67 | [What is underspecified] | [What detail is missing] |
| G1 | Gap | HIGH | tasks.md | [Missing coverage] | [What needs to be added] |
| I1 | Inconsistency | HIGH | spec.md:L45, plan.md:L23 | [Terminology conflict] | [Standardize to X term] |

**Finding ID Convention**:
- **C**: Constitution violation
- **A**: Ambiguity
- **D**: Duplication
- **U**: Underspecification
- **G**: Coverage gap
- **I**: Inconsistency

**Note**: Limited to 50 highest-priority findings. If total findings exceed 50, remaining are summarized in overflow section below.

### Overflow Summary (if > 50 findings)

**Additional Findings**: [X] findings not shown in main table

**Breakdown by Category**:
- LOW severity: [X] findings
- Style/formatting: [X] findings
- Documentation improvements: [X] findings

**Summary**: [Brief description of patterns in overflow findings]

---

## Coverage Analysis

### Requirements → Tasks Mapping

| Requirement Key | Has Task? | Task IDs | Priority | Acceptance Criteria | Notes |
|-----------------|-----------|----------|----------|-------------------|-------|
| [slug-from-requirement] | ✓ | T012, T015 | P1 | AC-001-001, AC-001-002 | Covered |
| [another-requirement-slug] | ✗ | - | P1 | AC-002-001 | **MISSING COVERAGE** |
| [optional-requirement-slug] | ✓ | T045 | P3 | AC-005-003 | Covered (optional) |

**Coverage Metrics**:
- **Total Requirements**: [X]
  - Functional: [X]
  - Non-Functional: [X]
- **Covered Requirements**: [X] ([Y]%)
- **Uncovered Requirements**: [X] ([Y]%)
- **P1 Coverage**: [X]% (must be ≥95% for implementation readiness)
- **P2 Coverage**: [X]%
- **P3 Coverage**: [X]%

**Critical Uncovered Requirements** (blocks MVP):
1. [requirement-slug] (P1) - [brief description] - Missing task coverage
2. [requirement-slug] (P1) - [brief description] - No AC verification path

### Tasks → Requirements Mapping

| Task ID | Mapped To | User Story | Priority | Test Coverage | Notes |
|---------|-----------|------------|----------|---------------|-------|
| T001 | setup-infrastructure | - | Setup | - | Foundational |
| T012 | [requirement-slug] | P1 Story | P1 | AC-001-001, AC-001-002 | Covered |
| T045 | *(orphaned)* | - | P2 | - | **NO REQUIREMENT MAPPING** |
| T067 | [requirement-slug] | P3 Story | P3 | AC-005-001 | Covered |

**Orphaned Tasks**: [X] tasks with no mapped requirement or user story
- T045: [description] (severity: MEDIUM - verify this task is necessary)
- T078: [description] (severity: LOW - documentation task)

**Task Verification Gaps**: [X] tasks missing acceptance criteria
- T023: [description] - No testable ACs defined

---

## Constitution Alignment

### Article Compliance Matrix

| Article | Status | Violations | Notes |
|---------|--------|------------|-------|
| **I: Intelligence-First Principle** | [✓ PASS / ✗ FAIL / ⚠ WARNING] | [X] | [Evidence or violation details] |
| **II: Evidence-Based Reasoning (CoD^Σ)** | [✓ PASS / ✗ FAIL / ⚠ WARNING] | [X] | [Evidence or violation details] |
| **III: Test-First Imperative (TDD)** | [✓ PASS / ✗ FAIL / ⚠ WARNING] | [X] | [Evidence or violation details] |
| **IV: Specification-First Development** | [✓ PASS / ✗ FAIL / ⚠ WARNING] | [X] | [Evidence or violation details] |
| **V: Template-Driven Quality** | [✓ PASS / ✗ FAIL / ⚠ WARNING] | [X] | [Evidence or violation details] |
| **VI: Simplicity & Anti-Abstraction** | [✓ PASS / ✗ FAIL / ⚠ WARNING] | [X] | [Evidence or violation details] |
| **VII: User-Story-Centric Organization** | [✓ PASS / ✗ FAIL / ⚠ WARNING] | [X] | [Evidence or violation details] |

### Critical Constitution Violations

[If any FAIL status above, list here with file:line references and required fixes]

**Example**:
- **Article IV Violation** (spec.md:L120-125):
  - **Issue**: Specification contains implementation details ("using JWT tokens", "Redis cache")
  - **Why Critical**: Violates technology-agnostic requirement of spec.md
  - **Fix**: Remove HOW (implementation), keep only WHAT (secure authentication) and WHY (user privacy)
  - **Evidence**: Constitution Article IV: "Specifications MUST be technology-agnostic"

[If no violations, state: "No constitution violations detected. All 7 articles compliant."]

### Detailed Article Checks

#### Article I: Intelligence-First Principle

**Requirements**:
- [ ] Plan.md references project-intel.mjs queries
- [ ] Tasks require intel queries before file reads
- [ ] 80%+ token efficiency target documented

**Findings**:
- [Specific checks with PASS/FAIL and evidence]

#### Article II: Evidence-Based Reasoning (CoD^Σ)

**Requirements**:
- [ ] Spec.md includes file:line evidence for existing patterns
- [ ] Plan.md has CoD^Σ traces for architectural decisions
- [ ] All claims have traceable evidence

**Findings**:
- [Specific checks with PASS/FAIL and evidence]

#### Article III: Test-First Imperative (TDD)

**Requirements**:
- [ ] Each implementation task has ≥2 testable acceptance criteria
- [ ] Tests written BEFORE implementation in task order
- [ ] Test coverage targets defined

**Findings**:
- [Specific checks with PASS/FAIL and evidence]
- **Tasks with insufficient ACs**: T023 (only 1 AC), T045 (0 ACs)

#### Article IV: Specification-First Development

**Requirements**:
- [ ] Spec exists and is complete (no [NEEDS CLARIFICATION] markers)
- [ ] Spec is technology-agnostic (WHAT/WHY only, no HOW)
- [ ] Plan created AFTER spec
- [ ] Tasks created AFTER plan

**Findings**:
- [Specific checks with PASS/FAIL and evidence]
- **[NEEDS CLARIFICATION] markers**: [X] found at spec.md:L45, L78, L120

#### Article V: Template-Driven Quality

**Requirements**:
- [ ] Spec follows @.claude/templates/feature-spec.md
- [ ] Plan follows @.claude/templates/plan.md
- [ ] Tasks follow @.claude/templates/tasks.md
- [ ] Quality checklists completed

**Findings**:
- [Specific checks with PASS/FAIL and evidence]

#### Article VI: Simplicity & Anti-Abstraction

**Requirements**:
- [ ] No over-engineering in plan
- [ ] Max 3 architectural patterns justified
- [ ] Framework used directly (no unnecessary abstractions)
- [ ] Pre/post-design gates documented

**Findings**:
- [Specific checks with PASS/FAIL and evidence]
- **Abstraction concern**: plan.md introduces custom [X] layer - verify necessity

#### Article VII: User-Story-Centric Organization

**Requirements**:
- [ ] Tasks grouped by user story (P1, P2, P3)
- [ ] Each story has independent test criteria
- [ ] MVP-first delivery order (P1 → P2 → P3)
- [ ] Stories are independently completable

**Findings**:
- [Specific checks with PASS/FAIL and evidence]
- **Story independence**: P2 story T045-T048 depends on P1 story - verify if blocking

---

## Quality Dimensions Analysis

### Ambiguity Score: [X/10]

**Vague Language Detected**:
- spec.md:L45 - "fast response time" (no threshold defined)
- spec.md:L78 - "user-friendly interface" (subjective, no criteria)
- spec.md:L120 - "scalable architecture" (no metrics provided)

**Unresolved Placeholders**:
- plan.md:L67 - TODO: define API endpoint
- tasks.md:T023 - TBD: determine test strategy

**Recommendation**: Clarify vague attributes with measurable criteria. Run clarify-specification skill if needed.

### Duplication Score: [X/10]

**Near-Duplicate Requirements**:
- R-001 "User can upload file" vs R-005 "User uploads document" (85% overlap)
- R-012 "System validates input" vs R-023 "Input validation performed" (100% overlap)

**Duplicate Tasks**:
- T045 "Create user model" vs T067 "Implement User entity" (same action)

**Recommendation**: Consolidate duplicates, keep higher-quality phrasing.

### Consistency Score: [X/10]

**Terminology Drift**:
- "user profile" (spec.md:L45) vs "account settings" (plan.md:L23) vs "user account" (tasks.md:T045)
- "upload" (spec.md) vs "import" (plan.md) vs "transfer" (tasks.md)

**Data Entity Conflicts**:
- Entity "UserProfile" in plan.md not defined in spec.md
- Entity "Session" in spec.md not modeled in plan.md data-model.md

**Recommendation**: Standardize terminology, align entity models across artifacts.

### Completeness Score: [X/10]

**Missing Sections**:
- spec.md: Edge cases section missing
- plan.md: API contracts/ directory not created
- tasks.md: Polish phase incomplete

**Missing Mappings**:
- [X] requirements with no task coverage
- [X] tasks with no requirement mapping
- [X] user stories with no AC alignment

**Recommendation**: Fill gaps before proceeding to implementation.

---

## Implementation Readiness

### Pre-Implementation Checklist

**Critical Requirements**:
- [ ] All CRITICAL findings resolved
- [ ] Constitution compliance achieved (all 7 articles PASS)
- [ ] No [NEEDS CLARIFICATION] markers remain in spec
- [ ] Coverage ≥ 95% for P1 requirements
- [ ] All P1 user stories have independent test criteria
- [ ] No orphaned tasks in P1 phase

**Quality Requirements**:
- [ ] All HIGH findings addressed or accepted risk documented
- [ ] Terminology standardized across artifacts
- [ ] Ambiguous requirements clarified with measurable criteria
- [ ] Duplicate requirements consolidated
- [ ] Task ordering validated (no circular dependencies)

**Test-First Requirements** (Article III):
- [ ] All implementation tasks have ≥2 testable ACs
- [ ] Tests ordered BEFORE implementation in task list
- [ ] Test coverage targets defined

**Readiness Status**: [Choose one]

✓ **READY TO PROCEED**
- Only LOW/MEDIUM issues remain
- Constitution compliance achieved
- P1 coverage ≥ 95%
- All critical quality gates pass
- **Next step**: `/implement plan.md` (begin progressive implementation)

✗ **NOT READY - BLOCKERS PRESENT**
- [X] CRITICAL issues must be resolved first
- [X] HIGH issues require addressing
- Constitution violations block implementation
- **Next step**: Resolve issues listed in "Next Actions" below, then re-audit

⚠ **READY WITH RISKS**
- MEDIUM/LOW issues present but acceptable
- Document accepted risks before proceeding
- **Next step**: User decision - proceed or address issues first

---

## Next Actions

### Immediate Actions Required

**To resolve CRITICAL findings** ([X] total):

1. **[Finding ID]**: [Specific action]
   - **Command**: `/feature` (re-run specify-feature skill)
   - **Focus**: [What to fix]
   - **Evidence**: [Why this is critical]

2. **[Finding ID]**: [Specific action]
   - **Command**: `/plan specs/[feature-id]/spec.md`
   - **Focus**: [What to adjust]
   - **Evidence**: [Constitution article reference]

**To address HIGH findings** ([X] total):

1. **[Finding ID]**: [Specific action]
   - **Manual edit**: [File:line with suggested change]
   - **Rationale**: [Why this improves quality]

2. **[Finding ID]**: [Specific action]
   - **Clarification needed**: Run clarify-specification skill
   - **Questions**: [List key ambiguities]

**Optional improvements** (MEDIUM/LOW, [X] total):
- [Grouped by type with brief suggestions]
- Can be addressed during implementation or post-MVP

### Recommended Commands

```bash
# If spec needs refinement (CRITICAL issues in spec)
/feature

# If plan needs adjustment (CRITICAL issues in plan)
/plan specs/[feature-id]/spec.md

# If tasks need regeneration (after fixing spec/plan)
# Manually invoke generate-tasks skill

# If ambiguities detected (HIGH priority clarification)
# Manually invoke clarify-specification skill

# After fixes, re-audit to verify
/audit [feature-id]

# When audit passes, proceed to implementation
/implement specs/[feature-id]/plan.md
```

### Workflow Sequence

```
Current State: Audit Complete
                ↓
        [BLOCKERS?]
         ↙      ↘
       YES      NO
        ↓        ↓
    Fix Issues  Ready
        ↓        ↓
    Re-Audit    /implement
        ↓
    [PASS?] → YES → /implement
```

---

## Remediation Offer

**Would you like me to:**

1. **Suggest specific edits** for top [X] CRITICAL/HIGH issues?
   - Provides exact text replacements with file:line references
   - Explains reasoning based on constitution/templates
   - You approve before any edits are made

2. **Generate remediation plan** for all issues?
   - Organizes fixes by priority and effort
   - Provides step-by-step action plan
   - Estimates time for each fix

3. **Proceed with current state** (if NO or READY WITH RISKS)?
   - Acknowledges accepted risks
   - Documents deferred improvements
   - Proceeds to /implement

**Note**: This audit is READ-ONLY. All edits require explicit user approval.

---

## Metadata

**Analysis Duration**: [X] seconds
**Tokens Used**: [X] (intelligence-first approach)
**Files Read**: spec.md ([X] KB), plan.md ([X] KB), tasks.md ([X] KB), constitution.md ([X] KB)
**Intelligence Queries**: [X] project-intel.mjs queries performed

**Reproducibility**: Re-running audit on unchanged artifacts produces identical finding IDs and recommendations.

**Related Commands**:
- `/verify` - Post-implementation AC verification
- `/feature` - Refine specification
- `/plan` - Regenerate implementation plan
- Invoke clarify-specification skill - Resolve ambiguities
- Invoke generate-tasks skill - Regenerate task list

---

**Audit Report Generated**: [YYYY-MM-DD HH:MM]
**Next Scheduled Audit**: After CRITICAL/HIGH issue resolution
**Audit Trail**: This report saved to `docs/sessions/[session-id]/audit/[timestamp]-audit-[feature-id].md`

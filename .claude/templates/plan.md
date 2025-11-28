---
plan_id: ""
status: "draft"
owner: ""
created_at: ""
updated_at: ""
type: "plan"
naming_pattern: "YYYYMMDD-HHMM-plan-{id}.md"
---

# Implementation Plan: [Title]

## Goal
<!-- What are we building/fixing/refactoring? -->

**Objective:**
**Success Definition:**
**Based On:** [link to feature-spec.md or bug-report.md]

---

## Summary

**Overview**: [One-paragraph description of implementation approach]

**Tech Stack**:
- **Frontend**: [framework/library]
- **Backend**: [framework/language]
- **Database**: [database + ORM if applicable]
- **Testing**: [framework]
- **Deployment**: [platform]

**Deliverables**:
1. [Deliverable 1] - [brief description]
2. [Deliverable 2] - [brief description]
3. [Deliverable 3] - [brief description]

---

## Technical Context

### Existing Architecture (Intelligence Evidence)

**Intelligence Queries Executed**:
```bash
# Project overview
project-intel.mjs --overview --json
# Output: [summary of project structure]

# Existing patterns
project-intel.mjs --search "[relevant-keyword]" --type tsx --json
# Output: Found [N] patterns at [file1:line], [file2:line]

# Dependencies
project-intel.mjs --dependencies [relevant-file] --direction both --json
# Output: Upstream: [N], Downstream: [M]
```

**Patterns Discovered** (CoD^Σ Evidence):
- **Pattern 1**: [pattern-name] @ `[file:line]`
  - Usage: [how it's used in codebase]
  - Applicability: [how we'll use it]
- **Pattern 2**: [pattern-name] @ `[file:line]`
  - Usage: [how it's used]
  - Applicability: [how we'll use it]

**External Research** (MCP Queries):
- **Library**: [library-name]
  - Source: [MCP query or documentation URL]
  - Rationale: [why chosen based on evidence]

**CoD^Σ Evidence Chain**:
```
spec_requirements ∘ intel_patterns → tech_decisions
Evidence: spec.md + intel[file:line] + mcp[library-docs] → plan.md
```

---

## Constitution Check (Article VI)

**Constitutional Authority**: Article VI (Simplicity & Anti-Abstraction)

### Pre-Design Gates

```
Gate₁: Project Count (≤3)
  Status: [PASS ✓ | CONDITIONAL ⚠ | BLOCKED ✗]
  Count: [X] projects
  Details: [list projects identified]
  Decision: [PROCEED | NEEDS JUSTIFICATION]

Gate₂: Abstraction Layers (≤2 per concept)
  Status: [PASS ✓ | CONDITIONAL ⚠ | BLOCKED ✗]
  Details: [abstraction analysis]
  Decision: [PROCEED | NEEDS JUSTIFICATION]

Gate₃: Framework Trust (use directly)
  Status: [PASS ✓ | CONDITIONAL ⚠ | BLOCKED ✗]
  Details: [framework usage analysis]
  Decision: [PROCEED | NEEDS JUSTIFICATION]
```

**Overall Pre-Design Gate**: [PASS ✓ | CONDITIONAL ⚠ | BLOCKED ✗]

**Justification** (if CONDITIONAL or BLOCKED):
| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [Gate] | [Rationale] | [Why simpler won't work] |

---

## Architecture (CoD^Σ)

### Component Breakdown

**System Flow**:
```
User → Frontend → API → Service → Database
  ↓      ↓         ↓       ↓         ↓
Input  Validate  Route   Logic    Persist
```

**Dependencies** (CoD^Σ Notation):
```
Auth ⇐ Session ⇐ User
Service ⊥ Storage (independent)
Frontend → API → [Service₁, Service₂] (fanout)
[Service₁, Service₂] ⇒ Database (fanin)
```

**Data Flow**:
```
Input ≫ Validation ≫ Transform → Business_Logic → Persistence
  ↓           ↓            ↓            ↓              ↓
Schema    Rules        DTO          Domain         Entity
```

**Modules**:
1. **[Module 1]**: `[directory/]`
   - Purpose: [what it does]
   - Exports: [what it provides]
   - Imports: [what it depends on]

2. **[Module 2]**: `[directory/]`
   - Purpose: [what it does]
   - Exports: [what it provides]
   - Imports: [what it depends on]

**Integration Points**:
- **External**: [system/API] via [protocol]
- **Internal**: [module1] ⇔ [module2] via [interface]

---

## User Story Implementation Plan

**From spec.md User Stories**:

### User Story P1: [Title] (Priority: Must-Have)

**Goal**: [Brief description from spec.md]

**Acceptance Criteria** (from spec.md):
- AC-REQ#-001: [Criterion 1]
- AC-REQ#-002: [Criterion 2]

**Implementation Approach**:
1. [Component to build]
2. [Integration point]
3. [Testing approach]

**Evidence**: Based on pattern at `[file:line]` (via intel query)

---

### User Story P2: [Title] (Priority: Important)

**Goal**: [Brief description from spec.md]

**Acceptance Criteria** (from spec.md):
- AC-REQ#-001: [Criterion 1]
- AC-REQ#-002: [Criterion 2]

**Implementation Approach**:
1. [Component to build]
2. [Integration with P1]
3. [Testing approach]

**Evidence**: Based on pattern at `[file:line]`

---

### User Story P3: [Title] (Priority: Nice-to-Have)

**Goal**: [Brief description from spec.md]

**Acceptance Criteria** (from spec.md):
- AC-REQ#-001: [Criterion 1]
- AC-REQ#-002: [Criterion 2]

**Implementation Approach**:
1. [Component to build]
2. [Integration with P1/P2]
3. [Testing approach]

**Evidence**: Based on pattern at `[file:line]`

---

## Tasks

**Organization**: Tasks map to user stories [US1], [US2], [US3] for SDD progressive delivery

**CoD^Σ Dependencies**: Task dependencies use → (sequential), ⊥ (independent), ⇒ (causal)

### Task 1: [US1] [Task Description]
- **ID:** T1
- **User Story**: P1 - [User story title from spec.md]
- **Owner:** [agent or human]
- **Status:** [ ] Not Started | [ ] In Progress | [ ] Blocked | [x] Complete
- **Dependencies** (CoD^Σ): [None | T1 → T2 (sequential) | T1 ⊥ T3 (independent)]
- **Estimated Complexity:** [Low | Medium | High]

**Acceptance Criteria** (from spec.md):
- [ ] AC-REQ#-001: [Testable criterion with verification method]
- [ ] AC-REQ#-002: [Testable criterion with verification method]
- [ ] AC-REQ#-003: [Optional third criterion]

**Implementation Notes:**
- **Pattern Evidence**: Based on `[file:line]` (via project-intel.mjs query)
- **Integration**: [How this integrates with other components]
- **Testing**: [Test files that verify this task]

---

### Task 2: [US1] [Task Description]
- **ID:** T2
- **User Story**: P1 - [User story title from spec.md]
- **Owner:**
- **Status:** [ ] Not Started | [ ] In Progress | [ ] Blocked | [ ] Complete
- **Dependencies** (CoD^Σ): T1 → T2 (T2 requires T1 complete)
- **Estimated Complexity:** [Low | Medium | High]

**Acceptance Criteria** (from spec.md):
- [ ] AC-REQ#-004: [Testable criterion]
- [ ] AC-REQ#-005: [Testable criterion]

**Implementation Notes:**
- **Pattern Evidence**: Based on `[file:line]` (via project-intel.mjs query)
- **Integration**: [How this integrates with T1 and other components]
- **Testing**: [Test files that verify this task]

---

<!-- Add more tasks as needed -->

---

## Dependencies

### Task Dependency Graph (CoD^Σ)
```
T1 → T2 → T4         (sequential execution)
  ↘ T3 ↗             (T3 depends on T1, feeds into T4)

T5 ∥ T6              (parallel, no dependencies)

Completion: T1 ⇒ T2  (T1 must complete before T2 starts)
Integration: T3 ∘ T4 (T3 output feeds T4 input)
```

**Critical Path**: T1 → T2 → T4 (longest path, determines minimum duration)
**Parallelizable**: {T3, T5, T6} ⊥ T2 (can run while T2 executes)

### External Dependencies (CoD^Σ Evidence)
- **Library**: [name@version] - Source: `package.json:L[line]`
- **API**: [endpoint] - Availability: [SLA | status]
- **Service**: [name] - Dependency: [upstream-service] ⇐ [this-service]
- **Unreleased**: [feature-name] - Blocks: [T1, T2] ⇒ Δt_delay

### File Dependencies (CoD^Σ Evidence)
<!-- Evidence from: project-intel.mjs --dependencies [file] --json -->
```
file1.ts → file2.ts → file3.ts  (modification chain)
  ↓
file4.ts ⇐ file1.ts              (file4 depends on file1)

utils.ts ∥ api.ts                (independent, no cross-imports)
```

**Modification Rules**:
- `file1` must be modified ≫ `file2` (transformation pipeline)
- `file3` imports `file4`, changes propagate: file4.change ⇒ file3.retest

---

## Risks (CoD^Σ)

### Risk Notation
```
r := p × impact     (risk = probability × impact magnitude)
p ∈ [0,1]           (probability: 0=impossible, 1=certain)
impact ∈ [1,10]     (impact: 1=trivial, 10=critical)
```

### Risk 1: [Description]
- **Likelihood (p):** [Low:0.2 | Medium:0.5 | High:0.8]
- **Impact:** [Low:2 | Medium:5 | High:8]
- **Risk Score:** r = [p × impact] (e.g., 0.5 × 5 = 2.5)
- **Mitigation Chain** (CoD^Σ):
  ```
  Risk → Detection → Response → Resolution
    ↓        ↓           ↓           ↓
  [event] [monitor] [action]  [outcome]
  ```
- **Mitigation:** [Specific actions to reduce p or impact]
  - **Reduce p**: [preventive measures] ⇒ p↓
  - **Reduce impact**: [contingency plans] ⇒ impact↓

### Risk 2: [Description]
- **Likelihood (p):** [Low | Medium | High]
- **Impact:** [Low | Medium | High]
- **Risk Score:** r = [calculated]
- **Mitigation Chain**:
  ```
  [Risk event] → [Early warning] → [Fallback plan] → [Recovery]
  ```
- **Mitigation:** [How to prevent/handle]
  - **Prevention**: [actions] ⇒ ¬risk
  - **Containment**: [if risk occurs] ⇒ impact_limited

---

## Verification (CoD^Σ)

### Test Strategy (CoD^Σ Composition)
```
Unit → Integration → E2E  (test pyramid, sequential)
  ↓         ↓          ↓
Fast     Medium     Slow

Coverage: ∑(AC_tested) / ∑(AC_total) ≥ 0.95  (95% minimum)
```

- **Unit Tests**: `[files/functions]` → `tests/unit/*.test.ts`
  - Coverage: functions ∈ [module] → test_coverage ≥ 80%
  - Execution: Fast (<100ms per test)

- **Integration Tests**: `[workflows]` → `tests/integration/*.test.ts`
  - Coverage: module₁ ∘ module₂ → integration_test
  - Dependencies: DB ∥ API (mock or real)

- **E2E Tests**: `[user flows]` → `tests/e2e/*.test.ts`
  - Coverage: User → UI → API → DB → Response
  - Verification: flow_complete ⇒ AC_satisfied

### AC Coverage Map (CoD^Σ Traceability)
<!-- Every AC ⇒ test (mandatory mapping) -->
```
AC-REQ#-001 → test/file.test.ts:L42 ✓
AC-REQ#-002 → test/file.test.ts:L57 ✓
AC-REQ#-003 → test/other.test.ts:L18 ✓

Coverage := ∑(mapped_ACs) / ∑(total_ACs) = [N/M] ([percentage]%)
```

**Traceability Rules**:
- ∀ AC ∈ spec.md, ∃ test ∈ tests/ : AC → test (every AC must have a test)
- ∀ test.pass ⇒ AC.verified (passing test verifies AC)
- ¬∃ test ⇒ AC.blocked (missing test blocks AC verification)

### Verification Command
```bash
# Verification pipeline (sequential with fail-fast)
npm test && npm run lint && npm run build

# CoD^Σ representation:
# Test ∘ Lint ∘ Build → Verified
# ∀ stage.fail ⇒ pipeline.halt
```

---

## Progress Tracking (CoD^Σ)

**Completion Metrics**:
```
Total Tasks (N):     ∑(tasks) = [N]
Completed (X):       |{t ∈ T : status=complete}| = [X]
In Progress (Y):     |{t ∈ T : status=in_progress}| = [Y]
Blocked (Z):         |{t ∈ T : status=blocked}| = [Z]

Progress Ratio:      X/N = [X/N] ([percentage]%)
Velocity:            Δtasks/Δtime = [tasks per day/week]
Estimated Complete:  (N - X) / velocity = [days/weeks remaining]
```

**Status Distribution**:
```
Completed: ████████░░ [X/N]
Progress:  ██░░░░░░░░ [Y/N]
Blocked:   █░░░░░░░░░ [Z/N]

Health: (X + Y) / N ≥ 0.8 ⇒ on_track | < 0.8 ⇒ at_risk
```

**Last Updated:** [YYYY-MM-DD HH:MM] (timestamp)
**Next Review:** [YYYY-MM-DD] (scheduled milestone)

---

## Handover Points (CoD^Σ Delegation)

**Delegation Notation**:
```
Agent₁ → Agent₂  (context transfer)
Context: C₁ ≫ C₂  (context transformation/filtering)
Decision: D₁ ∘ D₂ (decision composition)
```

### Handover 1: [Milestone] (After T2 Complete)
```
[Agent₁] → [Agent₂]  (delegation)
  ↓         ↓
Context  Action
```

- **From:** [Agent₁ - role/responsibility]
- **To:** [Agent₂ - role/responsibility]
- **Trigger:** T2.status = complete ⇒ handover_initiated
- **Context Transfer**:
  - **Outputs**: [T1, T2 deliverables] → Agent₂.input
  - **State**: [current-state] ≫ [next-state]
  - **Evidence**: spec.md + plan.md + [T1,T2].outputs
- **Handover File:** @[YYYYMMDD-HHMM-handover-agent1-to-agent2.md]

### Handover 2: [Milestone] (After T4 Complete)
```
[Agent₂] → [Agent₃]
  ↓         ↓
Results   Next
```

- **From:** [Agent₂ - role]
- **To:** [Agent₃ - role]
- **Trigger:** T4.status = complete ∧ verification.pass ⇒ handover
- **Context Transfer**:
  - **Outputs**: [T3, T4 deliverables] → Agent₃.input
  - **Dependencies**: T4.complete ⇒ T5.ready
  - **Evidence**: plan.md + verification-report.md
- **Handover File:** @[YYYYMMDD-HHMM-handover-agent2-to-agent3.md]

---

## Notes (CoD^Σ Evidence)

**Deviations from Spec** (CoD^Σ Traceability):
- **Change**: [what changed]
- **Reason**: [why changed] (CoD^Σ: requirement_conflict ⇒ spec_update)
- **Evidence**: spec.md:L[old-line] → plan.md:L[new-approach]
- **Impact**: [affected tasks/stories] → [mitigation]

**Lessons Learned** (Update as plan executes):
- **Lesson**: [insight discovered]
- **Context**: [where/when discovered] @ [file:line or task-id]
- **Pattern**: [generalizable pattern] (CoD^Σ: A → B observed)
- **Application**: [how to apply in future] ⇒ [improvement]

**Optimizations** (CoD^Σ Improvements):
- **Optimization**: [improvement made]
- **Baseline**: [original approach] → [time/tokens/complexity: X]
- **Improved**: [new approach] → [time/tokens/complexity: Y]
- **Gain**: Δ_improvement = (X - Y) / X = [percentage]% faster/smaller/simpler
- **Evidence**: [file:line or benchmark results]

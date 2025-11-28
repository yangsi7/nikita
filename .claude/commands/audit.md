---
description: Perform cross-artifact consistency and quality analysis across spec.md, plan.md, and tasks.md to verify constitution compliance and implementation readiness (project)
allowed-tools: Read, Grep, Glob
argument-hint: [feature-id] [focus-area]
---

## User Input

```text
$ARGUMENTS
```

**Argument Patterns:**

1. **Single argument (feature-id):**
   ```
   /audit 001-user-authentication
   ```
   Audits the specified feature.

2. **Two arguments (feature-id + focus-area):**
   ```
   /audit 001-user-authentication "focus on security requirements"
   /audit 002-oauth-flow "check Article III compliance"
   ```
   Audits with emphasis on specified area. Focus-area is provided as context to prioritize findings.

3. **No arguments (auto-detect):**
   ```
   /audit
   ```
   Detects feature from current git branch or SPECIFY_FEATURE environment variable.

**Processing:**
- First argument: feature-id (required or auto-detected)
- Remaining arguments: focus-area (optional context for analysis)
- If auto-detection fails, abort with clear error

You **MUST** consider the user input before proceeding (if not empty).

---

## Goal

Identify inconsistencies, duplications, ambiguities, underspecified items, and constitution violations across the three core artifacts (`spec.md`, `plan.md`, `tasks.md`) before implementation begins. This command runs **after** task generation to ensure implementation readiness.

---

## Operating Constraints

### STRICTLY READ-ONLY

- **DO NOT modify any files**
- Output a structured analysis report only
- Offer optional remediation recommendations (user must explicitly approve any edits)

### Constitution Authority

The project constitution (`.claude/shared-imports/constitution.md`) is **non-negotiable**. Constitution violations are **automatically CRITICAL** and require adjustment of spec, plan, or tasks—not dilution or reinterpretation of principles.

If a constitutional principle itself needs changing, that requires a separate, explicit constitution amendment process outside this command.

---

## Execution Steps

### 1. Initialize Analysis Context

**Detect Feature:**

Parse `$ARGUMENTS` to extract feature-id:

1. **If `$ARGUMENTS` is not empty**:
   - Feature ID is the first word of `$ARGUMENTS`
   - Remaining words are focus-area (optional)

2. **If `$ARGUMENTS` is empty** (auto-detect):
   - **Try option A**: Read `.git/HEAD` file
     - If contains `ref: refs/heads/###-name` pattern, extract branch name
     - Example: `ref: refs/heads/002-constitution-command` → feature = `002-constitution-command`
   - **Try option B**: Check for environment variable (not directly accessible, will fail gracefully)
   - **If both fail**: Abort with error

**Feature Detection Logic**:

```
Extract first word from $ARGUMENTS using string split:
  If $ARGUMENTS = "002-constitution-command check Article IV":
    feature_id = "002-constitution-command"
    focus_area = "check Article IV"

  If $ARGUMENTS is empty:
    Read .git/HEAD
    Extract pattern after "refs/heads/"
    If matches ###-* pattern:
      feature_id = extracted value
    Else:
      ERROR: "No feature detected. Provide feature-id or use git branch with ###-name pattern"
```

**Locate Artifacts:**

Once feature-id is determined, construct paths:

```bash
FEATURE="<detected-feature-id>"  # e.g., "001-user-authentication"
FEATURE_DIR="specs/${FEATURE}"
SPEC="${FEATURE_DIR}/spec.md"
PLAN="${FEATURE_DIR}/plan.md"
TASKS="${FEATURE_DIR}/tasks.md"
CONSTITUTION=".claude/shared-imports/constitution.md"
```

**Verify Prerequisites Using Read Tool:**

Attempt to read each required file:

1. Try to Read `specs/${feature_id}/spec.md`
   - If fails: Report "Missing spec.md → Run specify-feature skill or /feature command"

2. Try to Read `specs/${feature_id}/plan.md`
   - If fails: Report "Missing plan.md → Run create-implementation-plan skill or /plan command"

3. Try to Read `specs/${feature_id}/tasks.md`
   - If fails: Report "Missing tasks.md → Run generate-tasks skill"

4. Try to Read `.claude/shared-imports/constitution.md`
   - If fails: Report "Missing constitution.md in .claude/shared-imports/"

**Abort if any required file is missing with clear instructions.**

---

### 2. Load Artifacts (Progressive Disclosure)

Load only minimal necessary context from each artifact using intelligence-first approach:

**From spec.md:**
- Overview/Context section
- Functional Requirements
- Non-Functional Requirements (NFRs)
- User Stories with priorities (P1, P2, P3)
- Edge Cases (if present)
- [NEEDS CLARIFICATION] markers (should be zero for complete spec)

**From plan.md:**
- Architecture/Stack section
- Data Model
- Implementation Phases
- Technical Constraints
- Research decisions
- API Contracts (if present)

**From tasks.md:**
- Task IDs and descriptions
- Phase groupings (Setup, Foundational, User Story P1, P2, P3, Polish)
- Parallel markers [P]
- Referenced file paths
- User story mappings

**From constitution.md:**
- All 7 Articles with MUST/SHOULD statements
- Quality gates
- Enforcement rules

---

### 3. Build Semantic Models

Create internal representations for analysis (do NOT dump raw artifacts in output):

**Requirements Inventory:**
- Each functional requirement with stable key (slug from imperative phrase)
- Example: "User can upload file" → `user-can-upload-file`
- Track testable acceptance criteria

**User Story/Action Inventory:**
- Discrete user actions with priorities (P1, P2, P3)
- Independent test criteria per story (Article VII requirement)
- Acceptance criteria alignment

**Task Coverage Mapping:**
- Map each task to one or more requirements/stories
- Use keyword matching + explicit ID references
- Track task → requirement → story lineage

**Constitution Rule Set:**
- Extract all MUST/SHOULD normative statements
- Build checklist for automated compliance verification

---

### 4. Detection Passes (High-Signal Analysis)

Focus on actionable findings. **Limit to 50 findings total**; aggregate remainder in overflow summary.

#### A. Constitution Alignment (CRITICAL Priority)

Check each article for compliance:

**Article I: Intelligence-First Principle**
- ✓ Does plan.md reference project-intel.mjs queries?
- ✓ Are file reads preceded by intelligence queries in tasks?

**Article II: Evidence-Based Reasoning (CoD^Σ)**
- ✓ Does spec.md include file:line evidence for existing patterns?
- ✓ Does plan.md have CoD^Σ traces for architectural decisions?

**Article III: Test-First Imperative (TDD)**
- ✓ Each task has ≥2 testable acceptance criteria?
- ✓ Tests written BEFORE implementation in task order?

**Article IV: Specification-First Development**
- ✓ Spec exists and is complete (no [NEEDS CLARIFICATION])?
- ✓ Plan created AFTER spec?
- ✓ Tasks created AFTER plan?
- ✓ Spec is technology-agnostic (no HOW, only WHAT/WHY)?

**Article V: Template-Driven Quality**
- ✓ Spec follows feature-spec.md template?
- ✓ Plan follows plan.md template?
- ✓ Tasks follow tasks.md template?
- ✓ Quality checklists validated?

**Article VI: Simplicity & Anti-Abstraction**
- ✓ No over-engineering in plan?
- ✓ Max 3 architectural patterns justified?
- ✓ Framework used directly (no unnecessary abstractions)?

**Article VII: User-Story-Centric Organization**
- ✓ Tasks grouped by user story (P1, P2, P3)?
- ✓ Each story has independent test criteria?
- ✓ MVP-first delivery order (P1 → P2 → P3)?

#### B. Duplication Detection

- Identify near-duplicate requirements (similar phrasing, overlapping scope)
- Flag duplicate tasks (same action, different wording)
- Mark lower-quality phrasing for consolidation

#### C. Ambiguity Detection

- **Vague adjectives lacking measurable criteria:**
  - "fast", "scalable", "secure", "intuitive", "robust", "user-friendly"
  - Missing quantifiable thresholds (e.g., "< 200ms response time")

- **Unresolved placeholders:**
  - TODO, TKTK, ???, `<placeholder>`, TBD, FIXME

- **Missing acceptance criteria:**
  - User stories without testable ACs
  - NFRs without measurement criteria

#### D. Underspecification

- **Requirements with verbs but missing:**
  - Object (what is acted upon?)
  - Measurable outcome (how to verify?)

- **User stories missing:**
  - Acceptance criteria alignment
  - Priority assignment (P1/P2/P3)

- **Tasks referencing undefined entities:**
  - Files not in plan.md data model
  - Components not in plan.md architecture
  - APIs not in plan.md contracts

#### E. Coverage Gaps

- **Requirements with zero associated tasks**
- **Tasks with no mapped requirement/story** (orphaned tasks)
- **Non-functional requirements (NFRs) not reflected in tasks:**
  - Performance requirements
  - Security requirements
  - Scalability requirements
  - Accessibility requirements

#### F. Inconsistency Detection

- **Terminology drift:**
  - Same concept named differently across files
  - Example: "user profile" vs "account settings" vs "user account"

- **Data entity conflicts:**
  - Entities in plan.md absent from spec.md
  - Entities in spec.md not modeled in plan.md

- **Task ordering contradictions:**
  - Integration tasks before foundational setup (without dependency note)
  - P2 story tasks before P1 story complete
  - Missing [P] markers for parallelizable tasks

- **Architectural conflicts:**
  - Spec implies one tech stack, plan uses different stack
  - Example: Spec says "mobile app", plan uses web-only framework

---

### 5. Severity Assignment

Use this heuristic to prioritize findings:

**CRITICAL** (blocks implementation):
- Violates constitution MUST statement
- Missing core artifact (spec/plan/tasks)
- Requirement with zero coverage that blocks baseline functionality
- [NEEDS CLARIFICATION] markers remain in spec

**HIGH** (significant risk):
- Duplicate or conflicting requirements
- Ambiguous security/performance attributes
- Untestable acceptance criteria
- NFR with no implementation tasks

**MEDIUM** (quality concerns):
- Terminology drift across artifacts
- Missing non-functional task coverage
- Underspecified edge case
- Task ordering issues

**LOW** (improvements):
- Style/wording inconsistencies
- Minor redundancy not affecting execution
- Documentation gaps

---

### 6. Produce Compact Analysis Report

Generate Markdown report following our naming convention:
`YYYYMMDD-HHMM-audit-[feature-id].md`

**Report Structure:**

```markdown
# Specification Audit Report

**Feature**: [feature-id]
**Date**: [YYYY-MM-DD HH:MM]
**Audited Artifacts**: spec.md, plan.md, tasks.md
**Constitution Version**: 1.0.0

---

## Executive Summary

- **Total Findings**: X
- **Critical**: X | **High**: X | **Medium**: X | **Low**: X
- **Implementation Ready**: YES/NO
- **Constitution Compliance**: PASS/FAIL

---

## Findings

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| C1 | Constitution | CRITICAL | spec.md:L45 | Article IV violated: spec contains implementation details | Remove HOW, keep only WHAT/WHY |
| A1 | Ambiguity | HIGH | spec.md:L120 | NFR "fast response" lacks criteria | Specify "< 200ms p95 latency" |
| D1 | Duplication | MEDIUM | spec.md:L85,L134 | Two similar requirements for file upload | Merge, keep clearer version |

*(Generate stable IDs: C=Constitution, A=Ambiguity, D=Duplication, U=Underspecification, G=Gap, I=Inconsistency)*

---

## Coverage Analysis

### Requirements → Tasks Mapping

| Requirement Key | Has Task? | Task IDs | Priority | Notes |
|-----------------|-----------|----------|----------|-------|
| user-can-upload-file | ✓ | T1.3, T2.5 | P1 | Covered |
| system-validates-input | ✗ | - | P1 | **MISSING COVERAGE** |

**Coverage Metrics:**
- Total Requirements: X
- Covered Requirements: X (Y%)
- Uncovered Requirements: X (Y%)

### Tasks → Requirements Mapping

| Task ID | Mapped To | User Story | Priority | Notes |
|---------|-----------|------------|----------|-------|
| T1.1 | setup-database | - | Setup | Foundational |
| T2.3 | user-can-upload-file | P1 Story | P1 | Covered |
| T4.7 | *(orphaned)* | - | P2 | **NO REQUIREMENT** |

**Orphaned Tasks**: X

---

## Constitution Alignment

### Article Compliance Matrix

| Article | Status | Violations | Notes |
|---------|--------|------------|-------|
| I: Intelligence-First | ✓ PASS | 0 | project-intel.mjs referenced in plan |
| II: Evidence-Based Reasoning | ✗ FAIL | 2 | Missing CoD^Σ traces in spec.md:L45, L78 |
| III: Test-First Imperative | ✓ PASS | 0 | All tasks have ≥2 ACs |
| IV: Specification-First | ✗ FAIL | 1 | Spec contains implementation details (spec.md:L120) |
| V: Template-Driven Quality | ✓ PASS | 0 | All artifacts follow templates |
| VI: Simplicity & Anti-Abstraction | ⚠ WARNING | 1 | Plan introduces custom abstraction layer |
| VII: User-Story-Centric | ✓ PASS | 0 | Tasks properly grouped by story |

**Critical Constitution Violations**: [List with file:line references]

---

## Implementation Readiness

### Pre-Implementation Checklist

- [ ] All CRITICAL findings resolved
- [ ] Constitution compliance achieved
- [ ] No [NEEDS CLARIFICATION] markers remain
- [ ] Coverage ≥ 95% for P1 requirements
- [ ] All P1 user stories have independent test criteria
- [ ] No orphaned tasks in P1 phase

**Recommendation**:
- ✗ NOT READY (resolve X CRITICAL issues first)
- ✓ READY TO PROCEED (only LOW/MEDIUM issues remain)

---

## Next Actions

### Immediate Actions Required

1. **Resolve CRITICAL findings** (X total):
   - [Specific action with command suggestion]
   - Example: "Run clarify-specification skill to resolve ambiguities"

2. **Address HIGH findings** (X total):
   - [Specific action]

3. **Optional improvements** (MEDIUM/LOW):
   - [Suggestions]

### Recommended Commands

```bash
# If spec needs refinement
/feature  # Re-run specify-feature skill

# If plan needs adjustment
/plan specs/[feature-id]/spec.md

# If tasks need regeneration
# (After fixing spec/plan)
# Manually invoke generate-tasks skill

# After fixes, re-audit
/audit [feature-id]
```

---

## Remediation Offer

**Would you like me to suggest concrete remediation edits for the top N CRITICAL/HIGH issues?**

*(DO NOT apply automatically - user must explicitly approve)*
```

---

### 7. Offer Remediation (Optional)

After generating report, ask:

> "I've identified X CRITICAL and Y HIGH priority issues. Would you like me to:
> 1. Suggest specific edits to resolve CRITICAL issues?
> 2. Generate a remediation plan for all issues?
> 3. Proceed with current state (acknowledging risks)?"

**If user approves remediation:**
- Generate specific edit instructions with file:line references
- Provide exact text replacements or additions
- Explain reasoning based on constitution/templates
- User must execute edits manually or delegate to implementation

---

## Operating Principles

### Context Efficiency

- **High-signal tokens only**: Focus on actionable findings, not exhaustive dumps
- **Progressive disclosure**: Load artifacts incrementally via Read tool
- **Token-efficient output**: Limit findings table to 50 rows; summarize overflow
- **Deterministic results**: Rerunning unchanged artifacts produces consistent IDs

### Analysis Guidelines

- **NEVER modify files** (this is read-only analysis)
- **NEVER hallucinate missing sections** (report absences accurately)
- **Prioritize constitution violations** (always CRITICAL severity)
- **Use examples over patterns** (cite specific instances with file:line)
- **Report zero issues gracefully** (emit clean bill of health with metrics)

---

## Related Commands

### Command Comparison Matrix

| Command | Phase | Purpose | Input | Output | Modifies Files? |
|---------|-------|---------|-------|--------|----------------|
| **/feature** | 1. Specification | Create technology-agnostic spec | User requirements | spec.md | ✅ Yes (creates) |
| **/plan** | 2. Planning | Generate implementation plan | spec.md | plan.md | ✅ Yes (creates) |
| **generate-tasks** | 3. Task Generation | Create task list | spec.md + plan.md | tasks.md | ✅ Yes (creates) |
| **→ /audit** | **4. Quality Gate** | **Verify consistency** | **spec + plan + tasks** | **audit report** | **❌ No (read-only)** |
| **/implement** | 5. Implementation | Execute tasks with TDD | plan.md + tasks.md | Code changes | ✅ Yes (writes code) |
| **/verify** | 6. Verification | Check ACs met | spec.md + code | verification report | ❌ No (validation) |
| **/validate** | 6. Validation | Validate against requirements | spec.md + code | validation report | ❌ No (validation) |

### Key Distinctions

**`/audit` vs `/verify`:**
- **Audit**: Pre-implementation (checks artifacts for consistency)
- **Verify**: Post-implementation (checks code meets acceptance criteria)
- **Timing**: Audit BEFORE /implement, Verify AFTER /implement

**`/audit` vs `/validate`:**
- **Audit**: Checks spec/plan/tasks against constitution
- **Validate**: Checks implementation against spec requirements
- **Focus**: Audit = artifact consistency, Validate = code correctness

**`/audit` vs `/plan`:**
- **Audit**: Read-only verification of existing plan
- **Plan**: Creates or updates implementation plan
- **When**: Run /plan first, then /audit to verify

### Workflow Position

```
Specification → Planning → Task Generation
                                ↓
                          → /audit ← YOU ARE HERE
                                ↓
                    (If audit passes)
                                ↓
                    Implementation → Verification
```

**Critical Rule:** Never skip `/audit` between task generation and implementation. It's your quality gate that prevents costly rework.

---

**Note**: This command checks artifacts BEFORE implementation. Use `/validate` or `/verify` AFTER implementation to check actual code against requirements.

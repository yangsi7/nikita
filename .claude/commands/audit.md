---
description: Cross-artifact consistency audit for implementation readiness - SDD Phase 7
allowed-tools: Read, Grep, Glob
argument-hint: [feature-id] [focus-area]
---

# Specification Audit - SDD Phase 7

Perform cross-artifact consistency and quality analysis to verify implementation readiness.

## Unified Skill Routing

This command routes to **SDD Phase 7: Audit** via the unified skill at @.claude/skills/sdd/SKILL.md.

**Phase 7 Workflow:** @.claude/skills/sdd/workflows/07-audit.md

---

## User Input

```text
$ARGUMENTS
```

**Argument Patterns:**

1. **Feature ID provided:** `/audit 001-user-authentication`
2. **With focus area:** `/audit 001-user-authentication "focus on security"`
3. **Auto-detect:** `/audit` (uses git branch or spec directory)

---

## Phase 7 Process

Follow the **sdd skill Phase 7** workflow:

### 1. Locate Artifacts

```
FEATURE_DIR = specs/${feature_id}/
├── spec.md      (Phase 3 output)
├── plan.md      (Phase 5 output)
└── tasks.md     (Phase 6 output)
```

### 2. Load Constitution

Read `.claude/shared-imports/constitution.md` for compliance checking.

### 3. Detection Passes

**A. Constitution Alignment (CRITICAL)**
- Article I: Intelligence-First
- Article II: Evidence-Based (CoD^Σ)
- Article III: Test-First (TDD)
- Article IV: Specification-First
- Article V: Template-Driven
- Article VI: Simplicity
- Article VII: User-Story-Centric

**B. Duplication Detection**
- Near-duplicate requirements
- Duplicate tasks

**C. Ambiguity Detection**
- Vague adjectives without metrics
- Unresolved placeholders (TODO, TBD, ???)
- Missing acceptance criteria

**D. Coverage Gaps**
- Requirements with zero tasks
- Orphaned tasks (no mapped requirement)
- NFRs without implementation tasks

**E. Inconsistency Detection**
- Terminology drift
- Data entity conflicts
- Task ordering contradictions

---

## Severity Levels

| Level | Description | Action |
|-------|-------------|--------|
| **CRITICAL** | Blocks implementation | Must fix before /implement |
| **HIGH** | Significant risk | Should fix before /implement |
| **MEDIUM** | Quality concern | Can proceed with caution |
| **LOW** | Improvement | Optional enhancement |

---

## Output

**File:** `specs/${feature_id}/audit-report.md`

**Structure:**
```markdown
# Specification Audit Report

**Feature**: [feature-id]
**Date**: [timestamp]
**Result**: PASS | FAIL

## Executive Summary
- Total Findings: X
- Critical: X | High: X | Medium: X | Low: X

## Findings Table
| ID | Category | Severity | Location | Summary | Fix |
...

## Coverage Analysis
## Constitution Compliance
## Implementation Readiness
```

---

## Quality Gate

**Implementation requires:**
- ✓ Zero CRITICAL findings
- ✓ Constitution compliance PASS
- ✓ No [NEEDS CLARIFICATION] markers
- ✓ Coverage ≥ 95% for P1 requirements
- ✓ All P1 stories have independent test criteria

---

## Operating Constraints

### STRICTLY READ-ONLY

- **DO NOT modify any files**
- Output analysis report only
- Offer remediation suggestions (user must approve edits)

### Constitution Authority

Constitution violations are **automatically CRITICAL**. The constitution is non-negotiable; spec/plan/tasks must adjust, not the constitution.

---

## Post-Audit Flow

**If PASS:**
→ Ready for Phase 8 (/implement)

**If FAIL:**
→ Fix CRITICAL issues
→ Re-run /audit
→ Repeat until PASS

---

## Related Commands

| Command | Phase | When to Use |
|---------|-------|-------------|
| /feature | 3 | Create/update spec |
| /plan | 5 | Create/update plan |
| /audit | **7** | **Verify readiness** |
| /implement | 8 | Execute (after audit PASS) |

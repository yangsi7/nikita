# Phase 5: Quality Gate Enforcement (Article V)

**Purpose**: Automatic validation before implementation using /audit command to ensure cross-artifact consistency and constitutional compliance.

**Constitutional Mandate**: Template-Driven Quality requires automatic validation before implementation.

---

## Step 5.1: Invoke /audit Command Automatically

After tasks.md is successfully created, **automatically** trigger the quality gate.

**DO NOT ask user to run /audit manually** - this is automatic enforcement.

**Instruct Claude**:

"Now that tasks.md is complete, run the **quality gate validation** to verify cross-artifact consistency:

`/audit $FEATURE_ID`

This command will:
1. Validate Article IV compliance (spec → plan → tasks sequence)
2. Verify Article VII compliance (user-story-centric organization)
3. Check Article III compliance (≥2 ACs per user story)
4. Detect constitution violations (CRITICAL priority)
5. Identify missing requirement coverage
6. Find ambiguities and underspecification

**If audit finds CRITICAL issues**:
- Implementation is BLOCKED until issues resolved
- Report violations to user
- Provide remediation guidance

**If audit passes all checks**:
- Report 'Ready for implementation'
- User can proceed with `/implement plan.md`

The audit report will be saved as: `YYYYMMDD-HHMM-audit-$FEATURE_ID.md`"

---

## Step 5.2: Handle Audit Results

### On CRITICAL Failures

**Report Format**:
```
⚠ Quality Gate FAILED - Implementation BLOCKED

Critical Issues Found:
- [List of CRITICAL findings from audit]

Next Actions:
1. Fix CRITICAL issues in spec.md, plan.md, or tasks.md
2. Re-run /tasks to regenerate tasks.md
3. Audit will re-validate automatically

Implementation cannot proceed until audit passes.
```

**Common CRITICAL Issues**:
- Constitution violations (Article VI limits exceeded without justification)
- Missing user stories from spec not covered in tasks
- Acceptance criteria without corresponding tests
- User stories with <2 ACs (Article III violation)
- Tasks organized by layer instead of story (Article VII violation)

### On Successful Audit

**Report Format**:
```
✓ Quality Gate PASSED - Ready for Implementation

All validation checks passed:
- Constitution compliance: ✓
- Requirements coverage: 100%
- User story organization: ✓
- Acceptance criteria: ≥2 per story ✓

Next Step: Run /implement plan.md to begin implementation
```

**Validation Summary**:
- All user stories from spec.md have corresponding task phases
- All ACs from plan.md have test tasks
- Task organization follows Article VII (story-centric)
- Test tasks come before implementation (Article III)
- Constitution gates documented and justified

---

## Step 5.3: Record Audit Invocation

Log in tasks.md that audit was run:

```markdown
## Quality Gate

**Status**: Audit ran automatically on task generation
**Report**: YYYYMMDD-HHMM-audit-$FEATURE_ID.md
**Result**: [PASS/FAIL]
**Date**: [YYYY-MM-DD HH:MM]
```

This provides audit trail for when quality gate was executed.

---

## Quality Gate Validation Checks

The /audit command performs these validations:

### Check 1: Article IV Compliance (Specification-First)

**Validates**:
- spec.md exists and contains user stories
- plan.md exists and contains ACs
- tasks.md references both spec and plan

**CRITICAL if**: Missing spec or plan, or tasks.md doesn't reference them

### Check 2: Article VII Compliance (User-Story-Centric)

**Validates**:
- Tasks organized by user story phases
- Each phase corresponds to one user story
- No "all models" or "all services" phases

**CRITICAL if**: Layer-based organization detected

### Check 3: Article III Compliance (Test-First)

**Validates**:
- Every user story has ≥2 acceptance criteria
- Every AC has ≥1 test task
- Test tasks come before implementation tasks

**CRITICAL if**: Story with <2 ACs, or AC without test

### Check 4: Requirement Coverage

**Validates**:
- Every user story from spec has task phase
- Every component from plan has implementation task
- Every AC from plan has verification task

**WARNING if**: Partial coverage, **CRITICAL if**: Major gaps

### Check 5: Constitution Violations

**Validates**:
- Project count ≤3 (or justified)
- Abstraction layers ≤2 per concept (or justified)
- No unnecessary framework wrappers

**CRITICAL if**: Violations without justification

### Check 6: Task Consistency

**Validates**:
- Sequential task IDs (no gaps)
- All tasks labeled with [US#]
- Parallel markers [P] used appropriately
- Verification tasks for each story

**WARNING if**: Inconsistencies, **CRITICAL if**: Breaks workflow

---

## Automatic Workflow Pattern

```
generate-tasks skill executes
    ↓
tasks.md created successfully
    ↓ (automatic - NO user action)
invoke /audit $FEATURE_ID
    ↓
/audit validates cross-artifact consistency
    ↓
       PASS                    FAIL
        ↓                       ↓
Ready for /implement    Fix CRITICAL issues → Re-run /tasks
```

**Key Point**: User never manually runs /audit in the SDD workflow. It's automatically invoked by generate-tasks skill.

---

## Remediation Guidance

If audit fails with CRITICAL issues, provide specific remediation:

**Issue**: User story missing from tasks.md
**Fix**: Add new phase for missing story with tests, implementation, verification

**Issue**: AC without test task
**Fix**: Add test task for AC in appropriate story phase (before implementation)

**Issue**: Layer-based organization
**Fix**: Reorganize tasks by user story (one phase per story)

**Issue**: Story with <2 ACs
**Fix**: Return to plan.md, add more ACs to meet Article III requirement

**Issue**: Constitution violation (>3 projects)
**Fix**: Add justification to plan.md Complexity Justification Table, or simplify

---

## Success Criteria

Quality gate passes when:

- ✓ All articles validated (III, IV, VI, VII)
- ✓ 100% requirement coverage (spec → plan → tasks)
- ✓ No CRITICAL issues found
- ✓ Audit report saved with PASS status
- ✓ Ready for implementation message displayed

# Phase 0: Quality Gate Validation

**MANDATORY**: Check quality checklists before implementation.

**Constitutional Authority**: Article V (Template-Driven Quality)

## Step 0.1: Load Quality Checklist

Read `.claude/templates/quality-checklist.md`

## Step 0.2: Validate Feature Readiness

Check:
- [ ] All [NEEDS CLARIFICATION] markers resolved (max 0)
- [ ] All user stories have ≥2 acceptance criteria
- [ ] All ACs are testable and measurable
- [ ] Technical plan exists with constitution check
- [ ] Tasks organized by user story

**Example Validation**:
```markdown
Feature: 003-user-authentication

✓ Content Quality: PASS (no tech details in spec.md)
✓ Requirement Completeness: PASS (all ACs in Given/When/Then format)
✗ Feature Readiness: FAIL
  - User Story P2 has only 1 AC (need ≥2)
  - 2 [NEEDS CLARIFICATION] markers in spec.md
```

## Step 0.3: Audit Validation (MANDATORY)

**CRITICAL**: Verify /audit has been run and PASSED before implementation.

**Constitutional Authority**: Article V (Template-Driven Quality) - Quality gates enforce minimum standards

### Check 1: Audit Report Exists

```bash
# Check for audit report in feature directory
if [ -f "specs/###-feature-name/audit-report.md" ]; then
    echo "✓ Audit report found"
else
    echo "✗ Audit report NOT FOUND"
fi
```

**If audit report missing**:
```markdown
# ❌ Quality Gate Blocked: Audit Required

**Missing**: audit-report.md

**Why Blocked**: Article V requires /audit validation before implementation.

The /audit command validates:
- Cross-artifact consistency (spec.md ↔ plan.md ↔ tasks.md)
- Constitution compliance (Articles I-VII)
- Requirement coverage and traceability
- Missing or duplicate requirements
- Terminology drift across artifacts

**Required Action**:
1. Run: `/audit ###-feature-name`
2. Review audit report for CRITICAL issues
3. Fix any CRITICAL issues
4. Re-run /audit until PASS
5. Then re-run /implement

**Status**: ❌ BLOCKED - Cannot proceed without audit validation
```

**BLOCK implementation** - Do not proceed to Phase 1.

### Check 2: Audit Result Status

Read `audit-report.md` and extract overall result:
- **PASS**: ✓ Proceed to implementation
- **PASS WITH WARNINGS**: ✓ Proceed (address warnings during development)
- **FAIL**: ❌ BLOCK implementation

**Example audit-report.md check**:
```markdown
## Overall Assessment

**Status**: [PASS | PASS WITH WARNINGS | FAIL]
**Overall Score**: X.X / 10.0
**Critical Issues**: [X]
```

**If Status = FAIL**:
```markdown
# ❌ Quality Gate Blocked: Audit Failed

**Audit Status**: FAIL
**Overall Score**: X.X / 10.0
**Critical Issues**: [X]

**Why Blocked**: /audit identified CRITICAL issues that must be fixed before implementation:

[List critical issues from audit report]

**Required Actions**:
1. Fix CRITICAL issues in [artifact(s)]
2. Re-run /audit to validate fixes
3. Ensure audit status = PASS or PASS WITH WARNINGS
4. Then re-run /implement

**Status**: ❌ BLOCKED - Cannot implement with failing audit
```

**BLOCK implementation** - Do not proceed to Phase 1.

### Check 3: Critical Issue Count

Extract from audit report:
```markdown
**Critical Issues**: [X]
```

**If Critical Issues > 0**:
```markdown
# ❌ Quality Gate Blocked: Critical Issues Present

**Critical Issue Count**: [X]

Critical issues identified by audit:
[List each critical issue with location and description]

**Why Blocked**: Critical issues represent:
- Constitution violations (blocking)
- Missing requirement coverage
- Contradictory requirements
- Ambiguities preventing implementation

**Required Actions**:
1. Address each CRITICAL issue:
   - [Issue 1]: [Fix action]
   - [Issue 2]: [Fix action]
2. Re-run /audit to validate fixes
3. Ensure Critical Issues = 0
4. Then re-run /implement

**Status**: ❌ BLOCKED - Cannot implement with unresolved critical issues
```

**BLOCK implementation** - Do not proceed to Phase 1.

### Success Criteria

**PROCEED to Phase 1 only if**:
- ✓ audit-report.md exists
- ✓ Audit Status = PASS or PASS WITH WARNINGS
- ✓ Critical Issues = 0

**Example PASS**:
```markdown
# ✅ Audit Validation: PASSED

**Audit Report**: specs/003-user-authentication/audit-report.md
**Status**: PASS WITH WARNINGS
**Overall Score**: 8.5 / 10.0
**Critical Issues**: 0
**Warnings**: 2 (non-blocking)

Quality gate cleared. Proceeding to implementation...
```

## Step 0.4: User Override Option

**NOTE**: User override is NOT AVAILABLE for audit validation. Audit PASS is mandatory (Article V).

For other quality checks (non-audit):

If validation fails:
```
⚠ Quality checklist incomplete:
- User Story P2 has only 1 AC (need ≥2)

Proceed anyway? (yes/no)
```

**If no**: Block implementation, suggest fixes
**If yes**: Log override, continue with warning

**Enforcement**:
- [ ] Quality checklist loaded
- [ ] All gates checked
- [ ] Audit validation MANDATORY (no override)
- [ ] User override logged if bypassed (non-audit checks only)

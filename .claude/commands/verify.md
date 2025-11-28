---
description: Verify implementation satisfies all acceptance criteria from plan using implement-and-verify skill in verification mode (project)
allowed-tools: Bash(npm:*), Bash(test:*), Bash(project-intel.mjs:*), Bash(git:*), Read, Write, Grep
argument-hint: <plan-file> [--story <story-id>]
---

## Pre-Execution

<!-- Bash pre-validation removed - $1 not available in !`` context. Claude will validate file existence when reading. -->

# Verification Command

Verify implementation against acceptance criteria using the **implement-and-verify skill** in verification mode.

**Usage**:
- `/verify plan.md` - Verify ALL acceptance criteria (final verification)
- `/verify plan.md --story P1` - Verify specific user story independently
- `/verify plan.md --story P2` - Verify P2 story
- `/verify` - Auto-detect plan from git branch, verify all

**Input Plan:** `$1` (validated to exist)
**Story Scope:** `$STORY_ID` (if provided)

---

## Your Task

### Story-Level Verification (if --story provided)

Verify that the specified user story:
- Has all tests passing independently
- Can be demoed standalone
- Has no dependencies on incomplete stories
- Meets all story-specific acceptance criteria

**Instruct Claude**:

"Use the **implement-and-verify skill** in **story verification mode**:

**Plan**: $PLAN_FILE
**Story**: $STORY_ID

**Verify**:
1. Load all ACs for story $STORY_ID from plan.md
2. Run tests for story $STORY_ID tasks
3. Verify story works independently (no dependencies on incomplete stories)
4. Generate verification report: `YYYYMMDD-HHMM-verification-story-$STORY_ID.md`

**Success Criteria** (Article VII - Progressive Delivery):
- All story $STORY_ID tests pass: 100%
- Story can be demoed standalone: Yes
- No blocking dependencies: Confirmed
- Independent test criteria met: Yes

**Report Format**: Use @.claude/templates/verification-report.md

This validates that story $STORY_ID is **independently shippable** (Article VII mandate)."

---

### Full Verification (if no --story)

Verify that the entire implementation:
- Passes ALL acceptance criteria (100% coverage)
- All tests pass (unit + integration)
- Lint and build succeed
- No regressions introduced

**Instruct Claude**:

"Use the **implement-and-verify skill** in **full verification mode**:

**Plan**: $PLAN_FILE

**Verify**:
1. Load ALL acceptance criteria from plan.md
2. Run complete test suite (unit + integration)
3. Run lint checks
4. Run type checks (if TypeScript)
5. Run build process
6. Generate final verification report: `YYYYMMDD-HHMM-verification-final.md`

**Success Criteria** (Article III - Test-First Imperative):
- ALL acceptance criteria pass: 100%
- All tests pass: 100%
- Lint: Pass
- Build: Success
- No regressions: Confirmed

**Report Format**: Use @.claude/templates/verification-report.md

This validates that the **complete implementation** meets all requirements."

---

## Process Overview

For each task in the plan marked as "completed":

1. **Load Plan**
   - Read the plan file: `$1`
   - If --story provided: filter to story-specific tasks
   - If no --story: verify all completed tasks
   - Extract ACs for each task

2. **AC Verification**
   - For each task, verify ALL ACs:
     - Run tests corresponding to each AC
     - Check test results (must be PASS)
     - Document evidence (test output)

3. **Additional Checks**
   - Run full test suite (`npm test`)
   - Run lint checks (`npm run lint`)
   - Run type checks (if TypeScript: `npm run type-check`)
   - Run build (`npm run build`)
   - Verify no regressions

4. **Generate Report**
   - Use @.claude/templates/verification-report.md
   - Document results for each task
   - Include AC coverage percentage
   - Note any failures
   - Save as: `YYYYMMDD-HHMM-verification-{scope}.md`

---

## Templates Reference

**Input Templates:**
- @.claude/templates/plan.md - Implementation plans (input)

**Output Templates:**
- @.claude/templates/verification-report.md - Verification report (required)

---

## Verification Report Format

**Generated File**: `YYYYMMDD-HHMM-verification-{scope}.md`

**Scope values**:
- `story-P1` - Story-level verification for P1
- `story-P2` - Story-level verification for P2
- `final` - Complete implementation verification

**Report Structure**:

```markdown
---
plan_id: "<plan-file-name>"
scope: "story-P1" | "story-P2" | "final"
status: "pass" | "fail"
verified_by: "implement-and-verify-skill"
timestamp: "YYYY-MM-DDTHH:MM:SSZ"
---

# Verification Report: {Scope}

## Test Summary
- Total ACs: X
- Passed: X (XX%)
- Failed: X
- Coverage: XX%

## AC Coverage
[Detailed results for each AC]

## Recommendations
[Next steps or issues to address]
```

---

## Progressive Delivery Workflow (Article VII)

**Recommended usage pattern**:

```bash
# After implementing P1 story
/verify plan.md --story P1
# → Ensures P1 is shippable independently

# After implementing P2 story
/verify plan.md --story P2
# → Ensures P2 works standalone

# After all stories complete
/verify plan.md
# → Final verification of complete implementation
```

**Benefits**:
- Catch story-specific issues early
- Ensure each story is independently demostrable
- Enable progressive shipment (P1 → P2 → P3)
- Validate Article VII compliance

---

## Expected Outcomes

### Story-Level Success

```
✓ Story P1 Verification PASSED

Tests: 8/8 passing (100%)
ACs: 4/4 verified (100%)
Independent Test: PASS (story works standalone)
Can Ship: YES

Next: Implement P2 story or ship P1 as MVP
```

### Story-Level Failure

```
✗ Story P1 Verification FAILED

Tests: 6/8 passing (75%)
ACs: 3/4 verified (75%)
Failures:
- AC-P1-003: Weak password validation failing

Action:
1. Fix failing tests using debug-issues skill
2. Re-run /verify plan.md --story P1
3. Only proceed to P2 after P1 passes
```

### Full Verification Success

```
✓ Complete Implementation Verification PASSED

Total ACs: 12
Passed: 12 (100%)
Tests: All passing
Lint: Pass
Build: Success

Implementation is complete and ready for deployment.
```

### Full Verification Failure

```
✗ Complete Implementation Verification FAILED

Total ACs: 12
Passed: 10 (83%)
Failed: 2

Failures:
- AC-P2-002: Session persistence not working
- AC-P3-001: OAuth callback error

Action:
1. Address failing ACs
2. Re-run /verify plan.md
3. Do NOT deploy until 100% pass
```

---

## Constitutional Compliance

This command enforces:
- **Article III**: Test-First Imperative (verify all ACs)
- **Article VII**: User-Story-Centric Organization (story-level verification)
- **Article V**: Template-Driven Quality (use verification-report template)

---

## Related Commands

- **/feature** - Creates specification
- **/plan** - Creates implementation plan
- **/tasks** - Creates task breakdown
- **/audit** - Validates consistency (runs automatically)
- **/implement** - Executes tasks with TDD
- **→ /verify** - Validates ACs ← YOU ARE HERE

---

**Note**: This command is often invoked automatically by the implement-and-verify skill after each story completion. Can also be run manually.

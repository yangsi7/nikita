---
plan_id: ""
status: "pending"
verified_by: ""
timestamp: ""
type: "verification-report"
naming_pattern: "YYYYMMDD-HHMM-verification-{plan-id}.md"
---

# Verification Report: [Plan Title]

## Test Summary

**Plan:** [link to plan.md]
**Verification Date:** [timestamp]
**Verified By:** [agent or human]

**Results:**
- **Total ACs:** [N]
- **Passed:** [X] ✓
- **Failed:** [Y] ✗
- **Untested:** [Z] ⚠
- **Coverage:** [X/N = percentage]%

**Overall Status:** [ ] PASS | [ ] FAIL | [ ] PARTIAL

---

## AC Coverage

### Task 1: [Task Name] (ID: T1)

#### T1-AC1: [Acceptance Criterion]
- **Status:** [✓ PASS | ✗ FAIL | ⚠ UNTESTED]
- **Test:** `[test-file]:[line]` or `[manual test description]`
- **Result:** [pass/fail details]
- **Evidence:** [link to test output or screenshot]

#### T1-AC2: [Acceptance Criterion]
- **Status:** [✓ PASS | ✗ FAIL | ⚠ UNTESTED]
- **Test:** `[test-file]:[line]`
- **Result:** [pass/fail details]
- **Evidence:** [link to test output]

---

### Task 2: [Task Name] (ID: T2)

#### T2-AC1: [Acceptance Criterion]
- **Status:**
- **Test:**
- **Result:**
- **Evidence:**

<!-- Continue for all tasks -->

---

## Failures

### Failure 1: T1-AC2 Failed
**AC:** [Full acceptance criterion text]

**Error:**
```
[Full error message/stack trace]
```

**Location:** `[file]:[line]`

**Root Cause:** [CoD^Σ trace to root cause]
```
Step 1: → IntelQuery
  ↳ Source: [file:line]
  ↳ Data: [finding]

Step 2: ∘ Analysis
  ↳ Logic: [reasoning]

Step 3: → Conclusion
  ↳ Result: [root cause with evidence]
```

**Fix Required:** [Specific action to fix]

---

### Failure 2: [AC ID] Failed
**AC:** [criterion]
**Error:** [error details]
**Root Cause:** [analysis]
**Fix Required:** [action]

---

## Untested ACs

### T3-AC1: [Criterion]
**Reason Untested:** [why this AC wasn't tested]
**Action Required:** [what needs to happen]
**Priority:** [Low | Medium | High]

---

## Evidence Links

### Test Output Files
- `./test-results/[timestamp].log` - Full test execution log
- `./coverage/index.html` - Code coverage report
- `./screenshots/[test-name].png` - E2E test screenshot

### Manual Test Results
- [Link to manual test documentation]
- [Link to screenshots/recordings]

### Intel Queries Used
- `/tmp/verify_deps_[timestamp].json` - Dependency check
- `/tmp/verify_symbols_[timestamp].json` - Symbol validation

---

## Test Execution Commands

### Commands Run
```bash
# Unit tests
npm test -- --coverage

# Integration tests
npm run test:integration

# E2E tests
npm run test:e2e

# Lint
npm run lint

# Build
npm run build
```

### Execution Time
- **Unit Tests:** [X]s
- **Integration Tests:** [Y]s
- **E2E Tests:** [Z]s
- **Total:** [Total]s

---

## Recommendations

### Immediate Actions
1. [Fix for Failure 1 with task assignment]
2. [Fix for Failure 2 with task assignment]

### Coverage Improvements
1. [Test to add for untested AC1]
2. [Test to add for untested AC2]

### Next Steps
- [ ] Fix all failures
- [ ] Add missing tests
- [ ] Re-run verification
- [ ] Update plan.md status

---

## Sign-Off

**Verified:** [yes/no]
**Approved for Deployment:** [yes/no]
**Blockers:** [any blockers to deployment]

**Signature:** [agent or human name]
**Date:** [timestamp]

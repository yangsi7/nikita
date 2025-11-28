# Enforcement Rules & Failure Modes

## Enforcement Rules

### Rule 1: No Completion Without Passing ACs

**❌ Violation:**
```markdown
Task: Add login feature
Status: ✓ Complete
Test Results: 2 passed, 1 failed
```

**✓ Correct:**
```markdown
Task: Add login feature
Status: BLOCKED
Test Results: 2 passed, 1 failed
Action:
1. Debug failing test
2. Fix implementation
3. Re-run tests
4. Mark complete ONLY when all pass
```

### Rule 2: Test-First Mandatory

**❌ Violation:**
```
1. Implement feature
2. Write tests after
3. Tests pass (but might not be testing the right thing)
```

**✓ Correct:**
```
1. Write tests from ACs (tests FAIL)
2. Implement feature
3. Tests PASS (proves implementation works)
```

### Rule 3: 100% AC Coverage

**❌ Violation:**
```markdown
Total ACs: 3
Tested ACs: 2
Coverage: 67%  # Not acceptable!
```

**✓ Correct:**
```markdown
Total ACs: 3
Tested ACs: 3
Coverage: 100% ✓
```

## Common Pitfalls

| Pitfall | Impact | Solution |
|---------|--------|----------|
| Implementing before tests | Can't verify correctness | Write tests FIRST always |
| Skipping lint/build | Broken code deployed | Run full verification suite |
| Marking complete with failures | Incomplete implementation | Block until 100% pass |
| No verification report | Can't track progress | Generate report every time |

## Failure Modes

### Common Failures & Solutions

**1. Quality gates not validated before implementation**
- **Symptom**: Starting implementation without checking quality-checklist.md
- **Solution**: Run Phase 0 quality gate validation (Article V)
- **Prevention**: Skill enforces quality-checklist.md check at start

**2. Tests written after implementation (Article III violation)**
- **Symptom**: Code exists, then tests written (tests might not catch issues)
- **Solution**: Delete code, write tests first, watch them FAIL, then implement
- **Enforcement**: Tests must FAIL initially to prove they're valid

**3. Acceptance criteria coverage < 100%**
- **Symptom**: Some ACs not tested, verification incomplete
- **Solution**: Create test for EVERY AC (1:1 mapping)
- **Requirement**: No task marked complete unless all ACs have passing tests

**4. Tests passing without implementation (false positives)**
- **Symptom**: Tests pass immediately when written (before code exists)
- **Solution**: Tests are broken (not testing anything); rewrite tests to FAIL first
- **Prevention**: Always verify tests FAIL before implementing

**5. Story verification skipped**
- **Symptom**: Moving to P2 without verifying P1 independently
- **Solution**: MUST run /verify plan.md --story P1 before continuing to P2
- **Enforcement**: Article VII requires each story verified standalone

**6. Story depends on incomplete stories (violates independence)**
- **Symptom**: P2 tests fail because P3 not implemented yet
- **Solution**: Refactor P2 to be independent; update spec.md if dependency is valid
- **Requirement**: Each story must pass "Independent Test" criteria

**7. Marking tasks complete with failing tests**
- **Symptom**: Task status = "completed" but tests show failures
- **Solution**: NEVER mark task complete with failures; status MUST be "blocked"
- **Enforcement**: 100% AC pass rate required before completion

**8. Skipping lint, type-check, or build verification**
- **Symptom**: Tests pass but lint errors or build fails
- **Solution**: Run full verification suite (lint, type-check, build, tests)
- **Requirement**: ALL checks must pass, not just AC tests

**9. Over-engineering implementation (YAGNI violation)**
- **Symptom**: Code implements features not in ACs, unnecessary abstractions
- **Solution**: Write minimal code to pass tests, nothing more
- **Prevention**: Follow YAGNI (You Aren't Gonna Need It) principle

**10. No handover created for blocked tasks**
- **Symptom**: Task blocked but no documentation of blocker
- **Solution**: Create handover.md (≤600 tokens) with blocker details
- **Pattern**: Use debug-issues skill if technical block, handover to appropriate agent

**11. Progressive delivery not followed (implementing all stories at once)**
- **Symptom**: Implementing P1, P2, P3 together instead of verifying P1 first
- **Solution**: Complete P1 → verify → decide to ship or continue (Article VII)
- **Benefit**: MVP can ship after P1 passes, faster time-to-value

---
description: Perform systematic bug diagnosis using intelligence-first approach to trace from symptom to root cause with debug-issues skill (project)
allowed-tools: Bash(project-intel.mjs:*), Bash(sed:*), Bash(jq:*), Bash(cp:*), Bash(test:*), Read, Grep, Glob, Edit, Write
---

## Pre-Execution

!`if [ -f "error.log" ]; then cp error.log /tmp/bug_error.log && echo "Captured error.log to /tmp/bug_error.log"; else echo "No error.log found"; fi`

# Bug Command - Systematic Bug Diagnosis with Root Cause Analysis

You are now executing the `/bug` command. This command performs systematic bug diagnosis using intelligence-first approach to trace from symptom to root cause with complete CoD^Σ reasoning.

## Your Task

Diagnose the bug or error using the **debug-issues skill** (@.claude/skills/debug-issues/SKILL.md).

**Error Log:** `/tmp/bug_error.log` (if error.log was present)

## Process Overview

Follow the debug-issues skill workflow:

1. **Capture Symptom** (Phase 1)
   - Document complete error message
   - Record reproduction steps
   - Note frequency and environment
   - User impact assessment
   - Example:
     ```
     Error: TypeError: Cannot read property 'discount' of undefined
     at calculateTotal (src/pricing/calculator.ts:67)

     Reproduction:
     1. Add items to cart
     2. Apply discount code "SAVE20"
     3. Click "Checkout"
     4. ERROR: 500 response

     Frequency: 15% of checkout attempts
     Environment: Production
     Impact: High (blocks checkout)
     ```

2. **Parse Error** (Phase 2)
   - Extract error type (TypeError, ReferenceError, etc.)
   - Extract root location (file:line)
   - Parse stack trace to identify call chain
   - Identify entry point for investigation
   - Example parsing:
     ```json
     {
       "error_type": "TypeError",
       "message": "Cannot read property 'discount' of undefined",
       "root_location": "src/pricing/calculator.ts:67",
       "root_function": "calculateTotal",
       "call_chain": [
         "src/api/routes.ts:45",
         "src/checkout/checkout.ts:123",
         "src/pricing/calculator.ts:67"
       ]
     }
     ```

3. **Intel Trace** (Phase 3)
   - **CRITICAL:** Use project-intel.mjs to trace from error to cause
   - Use @.claude/shared-imports/project-intel-mjs-guide.md
   - Query sequence:
     ```bash
     # 1. Locate function with error
     project-intel.mjs --search "calculateTotal" --type ts --json

     # 2. Analyze symbols in file
     project-intel.mjs --symbols src/pricing/calculator.ts --json

     # 3. Trace dependencies
     project-intel.mjs --dependencies src/pricing/calculator.ts --direction upstream --json

     # 4. Check return types of dependencies
     project-intel.mjs --symbols src/pricing/discountService.ts --json
     ```
   - Read ONLY targeted lines identified by intel
   - **Token Savings:** 90%+ vs reading full files

4. **Identify Root Cause** (Phase 4)
   - Analyze code at error location
   - Trace data flow to find undefined source
   - Use MCP verification for library behavior
   - Document complete CoD^Σ trace
   - Example:
     ```
     Root Cause: src/pricing/calculator.ts:67
     Issue: Missing null check before accessing .discount property

     Why It Fails:
     - getDiscount() returns Discount | undefined
     - When discount code invalid, returns undefined
     - Code attempts undefined.discount → TypeError
     ```

5. **Generate Bug Report** (Phase 5)
   - Use @.claude/templates/bug-report.md
   - Include complete symptom
   - Include complete CoD^Σ trace
   - Specify root cause with file:line
   - Propose specific fix
   - Include verification plan
   - Save as: `YYYYMMDD-HHMM-bug-{id}.md`

## Templates Reference

**Output Templates:**
- @.claude/templates/bug-report.md - Complete bug report with fix (required)
- @.claude/templates/mcp-query.md - MCP verification results (if used)

## Intelligence-First Enforcement

**NEVER read full files before intel queries.**

Example workflow for React infinite render bug:
```bash
# 1. Search for component
project-intel.mjs --search "LoginForm" --type tsx --json

# 2. Analyze symbols to find useEffect
project-intel.mjs --symbols src/components/LoginForm.tsx --json
# Result: useEffect at line 45

# 3. Read ONLY useEffect lines
sed -n '40,55p' src/components/LoginForm.tsx

# 4. Verify with React docs
# Use Ref MCP: "React useEffect dependencies best practices"

# Total tokens: ~400 vs ~3000 for reading full file (87% savings)
```

## CoD^Σ Reasoning

Use @.claude/shared-imports/CoD_Σ.md for debugging trace:

```
Step 1: → ParseError
  ↳ Source: Error log /tmp/bug_error.log
  ↳ Data: TypeError at src/pricing/calculator.ts:67

Step 2: ⇄ IntelQuery("locate function")
  ↳ Query: project-intel.mjs --search "calculateTotal"
  ↳ Data: Found in src/pricing/calculator.ts at line 62

Step 3: ⇄ IntelQuery("analyze symbols")
  ↳ Query: project-intel.mjs --symbols calculator.ts
  ↳ Data: calculateTotal at line 62, error at line 67 (5 lines in)

Step 4: → TargetedRead(lines 62-75)
  ↳ Source: sed -n '62,75p' calculator.ts
  ↳ Data: Line 67 calls getDiscount(code).discount without null check

Step 5: ⇄ IntelQuery("check getDiscount")
  ↳ Query: project-intel.mjs --symbols discountService.ts
  ↳ Data: getDiscount returns Discount | undefined

Step 6: ⊕ MCPVerify("TypeScript best practices")
  ↳ Tool: Ref MCP
  ↳ Query: "TypeScript optional chaining undefined handling"
  ↳ Data: Use ?. operator for potentially undefined values

Step 7: ∘ Conclusion
  ↳ Logic: getDiscount returns undefined → accessing .discount throws TypeError
  ↳ Root Cause: src/pricing/calculator.ts:67 - missing null check
  ↳ Fix: Use optional chaining: getDiscount(code)?.discount ?? 0
```

## Common Bug Patterns

The debug-issues skill includes patterns for:
- **React infinite re-render** - useEffect dependency issues
- **N+1 query problem** - Database queries in loops
- **Memory leaks** - Missing cleanup functions
- **Async race conditions** - Improper promise handling

## Bug Report Format

Use @.claude/templates/bug-report.md with these sections:

```markdown
---
bug_id: "checkout-discount-500"
severity: "critical|high|medium|low"
status: "open|investigating|fixed"
assigned_to: "executor-agent|planner|..."
---

# Bug Report: [Title]

## Symptom
[Complete error with reproduction steps from Phase 1]

## CoD^Σ Trace
[Complete reasoning trace from Phase 4]

## Root Cause
**Location:** file:line
**Issue:** [Specific problem]
**Why It Fails:** [Explanation]

## Fix Specification
**Approach:** [How to fix]
**Changes Required:** [Specific code changes]
**Reason:** [Why this fix works]

## Verification
**Test Plan:** [How to verify fix]
**Acceptance Criteria:**
- [ ] AC1: [Specific testable criterion]
- [ ] AC2: [Specific testable criterion]
```

## Expected Output

**Generated file:** `YYYYMMDD-HHMM-bug-{id}.md`

Must include:
1. **Symptom** - Complete error with repro steps
2. **CoD^Σ Trace** - Full reasoning chain with evidence
3. **Root Cause** - Specific file:line with explanation
4. **Fix Specification** - Concrete fix proposal
5. **Verification** - Test plan and ACs

## Success Criteria

Before completing, verify:
- [ ] Complete symptom captured
- [ ] Error parsed and structured
- [ ] Intel queries executed before file reads
- [ ] Complete CoD^Σ trace documented
- [ ] Root cause identified with file:line
- [ ] Specific fix proposed
- [ ] Verification plan provided
- [ ] Bug report uses template
- [ ] Token usage 80%+ less than direct reading

## User Input

If the user hasn't provided enough information, ask:

- **What error are you seeing?** (Exact error message)
- **How can I reproduce it?** (Step-by-step)
- **How often does it happen?** (Always, sometimes, specific conditions)
- **What's the impact?** (Blocks users, performance issue, cosmetic)

## Start Now

Begin by capturing the symptom. If an error log was found, it's available at `/tmp/bug_error.log`.

Then proceed with the debug-issues skill workflow to trace from symptom to root cause.

**Remember:** Intel FIRST, read SECOND, every claim needs evidence (file:line or MCP).

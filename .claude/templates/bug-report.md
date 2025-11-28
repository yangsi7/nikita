---
bug_id: ""
severity: "medium"
status: "open"
assigned_to: ""
created_at: ""
type: "bug-report"
naming_pattern: "YYYYMMDD-HHMM-bug-{id}.md"
---

# Bug Report: [Bug Title]

## Symptom

**Summary:** [One-line description]

**Error Message:**
```
[Full error message if applicable]
```

**Reproduction Steps:**
1. [Step 1]
2. [Step 2]
3. [Step 3]
4. **Expected:** [What should happen]
5. **Actual:** [What actually happens]

**Frequency:** [Always | Sometimes | Rare]
**Environment:** [Production | Staging | Development]

---

## CoD^Σ Trace

### Investigation Process

```
Step 1: → ParseError
  ↳ Source: error.log or stack trace
  ↳ Data: Error type: [type], Location: [file:line]

Step 2: ⇄ IntelQuery (Locate Context)
  ↳ Query: project-intel.mjs --symbols [file]
  ↳ Data: Function [name] at line [N]

Step 3: ⇄ IntelQuery (Trace Dependencies)
  ↳ Query: project-intel.mjs --dependencies [file]
  ↳ Data: Imports [dependencies]

Step 4: → IntelQuery (Find Root Cause)
  ↳ Query: project-intel.mjs --search "[pattern]"
  ↳ Data: Found issue in [file:line]

Step 5: ⊕ MCP Verification
  ↳ Tool: [Ref MCP | Supabase MCP]
  ↳ Query: [verify library behavior or DB schema]
  ↳ Data: [authoritative source confirms/contradicts]

Step 6: ∘ Conclusion
  ↳ Logic: [reasoning from evidence to root cause]
  ↳ Result: Root cause identified at [file:line]
```

---

## Root Cause

**Location:** `[file]:[line]`

**Issue:**
```typescript
// Problematic code
[code snippet showing the bug]
```

**Why It Fails:**
[Explanation of the mechanism of failure]

**Contributing Factors:**
- [Factor 1]
- [Factor 2]

---

## Fix Specification

### Proposed Solution

**Approach:** [Description of fix strategy]

**Changes Required:**
1. **File:** `[file]:[line]`
   **Change:**
   ```typescript
   // Before
   [buggy code]

   // After
   [fixed code]
   ```
   **Reason:** [why this fixes the issue]

2. **File:** `[file]:[line]` (if additional changes needed)
   **Change:** [change details]

### Alternative Solutions Considered
- **Option 1:** [alternative approach]
  - **Pros:** [pros]
  - **Cons:** [cons]
  - **Rejected because:** [reason]

---

## Verification

### Test Plan

**Unit Tests:**
```typescript
describe('[Component/Function]', () => {
  it('should [expected behavior]', () => {
    // Test that reproduces bug
    expect([buggy scenario]).to[fail/throw]

    // Test that verifies fix
    expect([fixed scenario]).to[pass]
  })
})
```

**Integration Tests:**
- [Test case to verify fix in integration]

**Manual Verification:**
1. [Step to manually verify fix]
2. [Step to ensure no regression]

### Acceptance Criteria
- [ ] Bug reproduction test fails on buggy code
- [ ] Bug reproduction test passes on fixed code
- [ ] No regression in related functionality
- [ ] All existing tests still pass
- [ ] Code review approved

---

## Impact Analysis

### Affected Components
<!-- From project-intel.mjs --dependencies -->
- `[component1]` - [how it's affected]
- `[component2]` - [how it's affected]

### Users Affected
**Scope:** [All users | Subset | Edge case]
**User Impact:** [High | Medium | Low]

### Data Impact
**Data at Risk:** [yes/no]
**Data Loss Possible:** [yes/no]
**Mitigation:** [if yes, how to prevent]

---

## Intel Queries Used

### Query 1: Symbol Location
```bash
project-intel.mjs --search "[error function]" --json
```
**Result:** [summary]
**Output:** `/tmp/bug_query_1.json`

### Query 2: Dependencies
```bash
project-intel.mjs --dependencies [file] --json
```
**Result:** [summary]
**Output:** `/tmp/bug_query_2.json`

### Query 3: [Additional Query]
```bash
[command]
```
**Result:** [summary]

---

## Related Issues

**Similar Bugs:** [links to related bug reports]
**Related Features:** [links to feature specs that might be affected]
**Documentation:** [links to relevant docs]

---

## Timeline

**Reported:** [timestamp]
**Investigated:** [timestamp]
**Root Cause Found:** [timestamp]
**Fix Proposed:** [timestamp]
**Fix Implemented:** [timestamp]
**Verified:** [timestamp]
**Deployed:** [timestamp]

---

## Metadata

**Severity:** [Critical | High | Medium | Low]
**Priority:** [P0 | P1 | P2 | P3]
**Category:** [Bug Type: Logic | Performance | Security | UI | etc]
**Assigned To:** [agent or developer]
**Labels:** [tags for categorization]

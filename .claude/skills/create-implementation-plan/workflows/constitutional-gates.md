# Constitutional Gates Validation

**Purpose**: Enforce Article VI (Simplicity & Anti-Abstraction) limits BEFORE and AFTER design.

**Article VI Summary**:
- Maximum 3 projects (deployable units)
- Maximum 2 abstraction layers per concept
- Trust framework features (no unnecessary wrappers)

---

## Phase 0: Pre-Design Constitutional Gates

**MANDATORY**: Check Article VI limits BEFORE design.

### Step 0.1: Validate Specification Exists

PreToolUse hook will block plan.md creation without spec.md, but verify explicitly:

```bash
FEATURE=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "${SPECIFY_FEATURE:-}")
if [[ ! -f "specs/$FEATURE/spec.md" ]]; then
    echo "ERROR: Cannot create plan without specification (Article IV violation)"
    echo "Next: Run specify-feature skill or use /feature command"
    exit 1
fi
```

### Step 0.2: Constitution Check (Article VI)

Read specification and assess complexity against Article VI gates.

**Gate 1: Project Count (MAX 3)**
- **Rule**: Maximum 3 projects for initial implementation
- **Check**: Count distinct deployable units implied by spec
- **If > 3**: Violation detected → require justification

**Gate 2: Abstraction Layers (MAX 2 per concept)**
- **Rule**: Maximum 2 abstraction layers per concept
- **Check**: No repository/service/facade patterns unless documented
- **If > 2**: Violation detected → require justification

**Gate 3: Framework Trust (Use directly)**
- **Rule**: Use framework features directly (no custom wrappers)
- **Check**: No reinvention of framework capabilities
- **If wrappers present**: Violation detected → require justification

#### Gate Decision Process

**For each gate**, assess and report:

```markdown
## Pre-Design Constitutional Gates

### Gate 1: Project Count
**Status**: [PASS ✓ | NEEDS JUSTIFICATION ⚠ | VIOLATION ✗]
**Count**: [X] projects
**Details**: [List projects identified from spec]
**Decision**: [PROCEED | NEEDS JUSTIFICATION]

### Gate 2: Abstraction Layers
**Status**: [PASS ✓ | NEEDS JUSTIFICATION ⚠ | VIOLATION ✗]
**Details**: [Abstraction analysis]
**Decision**: [PROCEED | NEEDS JUSTIFICATION]

### Gate 3: Framework Trust
**Status**: [PASS ✓ | NEEDS JUSTIFICATION ⚠ | VIOLATION ✗]
**Details**: [Framework usage analysis]
**Decision**: [PROCEED | NEEDS JUSTIFICATION]

---

**Overall Pre-Design Gate**: [PASS ✓ | CONDITIONAL ⚠ | BLOCKED ✗]
```

#### Violation Handling

**IF any gate = VIOLATION (no justification)**:

```markdown
# ❌ Constitutional Gate BLOCKED

**Violations Detected**: [X]

**Gate [N]**: [Gate Name] - VIOLATION
- **Issue**: [What violates the constitution]
- **Specification**: [Where in spec.md this comes from]
- **Article VI Limit**: [What the limit is]
- **Detected Count**: [What the actual count is]

**Required Action**:
1. Provide justification in Complexity Justification Table
2. Document why simpler alternative won't work
3. Get approval for complexity increase

**Complexity Justification Table**:

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [Gate violated] | [Specific reason] | [Why 3 projects insufficient, etc.] |

**Status**: ⚠ Conditional proceed with documented justification
```

**IF all gates = PASS**:

```markdown
# ✅ Pre-Design Constitutional Gates: PASSED

All Article VI gates cleared:
- ✓ Gate 1: Project Count ≤ 3
- ✓ Gate 2: Abstraction Layers ≤ 2 per concept
- ✓ Gate 3: Framework Trust maintained (no unnecessary wrappers)

Proceeding to intelligence-first context gathering...
```

---

## Phase 4: Post-Design Constitutional Re-Check

**Article VI Mandate**: Verify gates still pass AFTER design decisions.

**Purpose**: Ensure technical design didn't introduce constitutional violations.

### Step 4.1: Re-validate All Three Gates

Re-check each Article VI gate against the completed design:

**Gate 1: Project Count Re-Check**
- **Question**: Did component breakdown create a 4th project?
- **Check**: Count deployable units in architecture (from Phase 2.2)
- **Status**: [PASS ✓ | NEW VIOLATION ⚠]

**Gate 2: Abstraction Layers Re-Check**
- **Question**: Did architecture add unnecessary abstraction layers?
- **Check**: Count layers per concept (Model → Service → API → Controller?)
- **Examples to Check**:
  - Data access: Database → [Repository?] → Service → Controller
  - State management: State → [Store?] → [Actions?] → Component
- **Status**: [PASS ✓ | NEW VIOLATION ⚠]

**Gate 3: Framework Trust Re-Check**
- **Question**: Did design create wrappers around framework features?
- **Examples to Check**:
  - Authentication: Using Supabase Auth directly OR custom AuthWrapper?
  - Database: Using Supabase client directly OR custom DB abstraction?
  - State management: Using React state/hooks OR custom state abstraction?
- **Status**: [PASS ✓ | NEW VIOLATION ⚠]

### Step 4.2: Post-Design Gate Report

Generate comprehensive post-design gate assessment:

```markdown
## Post-Design Constitutional Gates

### Gate 1: Project Count (Re-Check)
**Pre-Design Status**: [PASS/CONDITIONAL]
**Post-Design Status**: [PASS ✓ | NEW VIOLATION ⚠]
**Project Count**: [X] deployable units
**Details**: [List all projects identified in architecture]
**Decision**: [GATES HOLD | NEEDS JUSTIFICATION | VIOLATION]

### Gate 2: Abstraction Layers (Re-Check)
**Pre-Design Status**: [PASS/CONDITIONAL]
**Post-Design Status**: [PASS ✓ | NEW VIOLATION ⚠]
**Analysis**:
- [Concept 1]: [X] layers ([list layers])
- [Concept 2]: [X] layers ([list layers])
**Decision**: [GATES HOLD | NEEDS JUSTIFICATION | VIOLATION]

### Gate 3: Framework Trust (Re-Check)
**Pre-Design Status**: [PASS/CONDITIONAL]
**Post-Design Status**: [PASS ✓ | NEW VIOLATION ⚠]
**Framework Usage**:
- Authentication: [Using Supabase Auth directly ✓ | Custom wrapper ⚠]
- Database: [Using Supabase client ✓ | Custom ORM/wrapper ⚠]
- State: [Using framework state ✓ | Custom abstraction ⚠]
**Decision**: [GATES HOLD | NEEDS JUSTIFICATION | VIOLATION]

---

**Overall Post-Design Assessment**: [PASS ✓ | CONDITIONAL ⚠ | BLOCKED ✗]
```

### Step 4.3: Handle New Violations

**IF new violations detected in Post-Design**:

```markdown
# ⚠ Post-Design Violations Detected

**New Violations**: [X]

**What Changed**:
Pre-Design: [Gate status before design]
Post-Design: [Gate status after design]

**Violations**:

**1. [Gate Name] - NEW VIOLATION**
- **Pre-Design**: [PASS]
- **Post-Design**: [VIOLATION - X projects/layers/wrappers]
- **Cause**: [What design decision introduced this]
- **Location**: [Where in plan.md/architecture]

**Required Actions**:
1. Update Complexity Justification Table with new violations
2. Document why design requires this complexity
3. Consider simpler alternatives:
   - [Alternative 1]: [Why rejected]
   - [Alternative 2]: [Why rejected]

**Updated Complexity Justification Table**:

| Violation | Why Needed | Simpler Alternative Rejected Because | Added In Phase |
|-----------|------------|-------------------------------------|----------------|
| [Gate] | [Design rationale] | [Why simpler won't work] | Post-Design |

**Status**: ⚠ Conditional proceed with documented justification
```

**IF all gates still PASS**:

```markdown
# ✅ Post-Design Constitutional Gates: PASSED

All Article VI gates maintained through design:
- ✓ Gate 1: Project Count ≤ 3 (Pre: X, Post: X)
- ✓ Gate 2: Abstraction Layers ≤ 2 per concept (maintained)
- ✓ Gate 3: Framework Trust maintained (no wrappers added)

Design respects constitutional limits. Proceeding to plan generation...
```

---

## Key Patterns

**Pattern 1: Gate Before and After**
```
Pre-Design Check → Design → Post-Design Re-Check → Confirm limits maintained
```

**Pattern 2: Violation Escalation**
```
Violation Detected → Document in Complexity Table → Justify why needed → Proceed conditionally
```

**Pattern 3: Framework Trust Verification**
```
Check authentication → Check database → Check state → Check routing → Confirm no wrappers
```

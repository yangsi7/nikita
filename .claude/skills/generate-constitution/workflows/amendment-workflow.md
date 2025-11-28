# Amendment Workflow: Update Constitution

**Purpose**: Keep constitution.md aligned with product.md changes through version-controlled amendments.

---

## When to Amend

**Trigger**: product.md changes → constitution.md MUST update

**Examples**:
- New persona pain points added
- "Our Thing" differentiation changed
- North Star metric updated
- User journey steps modified

---

## Version Semantics

Follow semantic versioning for constitution.md:

- **MAJOR (X.0.0)**: Article added or removed (architectural shift)
  - Example: Adding new Article VIII for AI principles
  - Impact: Significant architectural direction change

- **MINOR (1.X.0)**: Article modified (principle change within existing category)
  - Example: Changing performance threshold from <2s to <1s
  - Impact: Tightening or loosening existing constraints

- **PATCH (1.0.X)**: Formatting, typos, clarifications (no principle change)
  - Example: Clarifying wording without changing requirement
  - Impact: Documentation improvement only

---

## Amendment Process

### Step 1: Identify Changed User Needs

Compare product.md versions:
```bash
# If using version control
git diff product.md

# Otherwise review changes manually
```

Note which sections changed:
- Persona pain points
- "Our Thing" differentiator
- North Star metric
- User journey requirements

### Step 2: Update Affected Articles

For each changed user need:

1. **Locate corresponding Article** in constitution.md
2. **Update derivation chain** if logic changed
3. **Modify principle** if constraint changed
4. **Update verification** if monitoring changed

**Example**:
```markdown
# Before (v1.0.0)
## Article III: Performance Standards (NON-NEGOTIABLE)
Dashboard MUST load in <2 seconds

# After (v1.1.0)
## Article III: Performance Standards (NON-NEGOTIABLE)
Dashboard MUST load in <2 seconds
Reports MUST generate in <10 seconds
```

### Step 3: Bump Version Number

Update version in frontmatter:
```markdown
---
version: 1.1.0  # Was 1.0.0
ratified: 2025-10-24  # Update date
derived_from: product.md (v1.1)  # Update if versioned
---
```

### Step 4: Update Ratified Date

Set to current date when amendment is approved.

### Step 5: Update Derivation Map

Add or modify rows in Appendix:
```markdown
## Appendix: Constitution Derivation Map

| Article | Product.md Source | User Need | Technical Principle |
|---------|-------------------|-----------|---------------------|
| Article III | NorthStar:15 | "Report generation <10s" | <10s report performance |  <!-- NEW ROW -->
```

### Step 6: Add Amendment History Entry

Append to Amendment History section:

```markdown
## Amendment History

### Version 1.1.0 - 2025-10-24

**Changed**: Article III (Performance Standards)

**Reason**: Product.md updated North Star to include report generation performance

**Before**: Dashboard <2s only

**After**: Dashboard <2s AND reports <10s

**Evidence**: Product.md:NorthStar:line:15

**Impact**: Requires optimization of report generation queries and caching strategy
```

---

## Amendment Entry Template

```markdown
### Version X.Y.Z - YYYY-MM-DD

**Changed**: [Article name and number]

**Reason**: [Why this amendment is needed, referencing product.md change]

**Before**: [Previous principle or constraint]

**After**: [New principle or constraint]

**Evidence**: Product.md:[section]:[line]

**Impact**: [How this affects implementation, if significant]
```

---

## Validation After Amendment

Run validation checks:
- [ ] All changed Articles have updated derivation chains
- [ ] Version number bumped correctly (MAJOR/MINOR/PATCH)
- [ ] Ratified date updated
- [ ] Derivation map includes new/modified rows
- [ ] Amendment history entry added
- [ ] No orphaned principles (all still trace to product.md)

---

## Review Process

Before finalizing amendment:

1. **Verify user need evidence** - Ensure product.md reference is correct
2. **Check NON-NEGOTIABLE classification** - "Our Thing" items stay NON-NEGOTIABLE
3. **Test derivation chain** - User Need ≫ Capability → Technical Approach ≫ Constraint
4. **Review impact** - Identify affected features/plans
5. **Communicate changes** - Notify team of new constraints

---

## Outputs Modified

- `constitution.md` - Amended with version bump
- Version number incremented
- Derivation map updated
- Amendment history entry added
- Ratified date updated

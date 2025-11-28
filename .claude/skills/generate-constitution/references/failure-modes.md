# Failure Modes: Common Constitution Issues

**Purpose**: Diagnose and fix the 12 most common constitution generation failures.

---

## Failure 1: Constitution Created Without product.md

**Symptom**: Technical principles with no user need evidence

**Impact**: Arbitrary tech preferences, not user-driven principles

**Solution**: STOP. Create product.md with define-product skill first

**Enforcement**: This skill MUST NOT run without product.md existing

**Prevention**: Skill checks for product.md in Step 1, exits if missing

---

## Failure 2: Technical Preferences Without CoD^Σ Derivation

**Symptom**: "Use React" without user need justification

**Impact**: Tech bias instead of evidence-based decisions

**Solution**: Add full derivation chain:
```
User Need ≫ Capability → Technical Approach ≫ Constraint
```

**Article II**: Evidence-Based Reasoning requires CoD^Σ traces

**Prevention**: Every Article MUST have "Technical Derivation (CoD^Σ)" section

---

## Failure 3: Orphaned Principles (No product.md Trace)

**Symptom**: Article exists but derivation map has no product.md reference

**Impact**: Unjustified tech decisions, scope creep

**Solution**: Either add evidence FROM product.md OR delete the principle

**Validation**: Run "Can I trace this to a specific user pain?" test

**Prevention**: Derivation map MUST be complete (no gaps)

**Example Fix**:
```markdown
❌ Before:
## Article VI: Code Quality
Use TypeScript (no evidence)

✓ After:
## Article VI: Maintainability (SHOULD)

### User Need Evidence
From product.md:Constraint:Time:45
- "Team of 3 developers, need to move fast"

### Technical Derivation (CoD^Σ)
Small team velocity (product.md:Constraint:Time:45)
  ≫ Catch errors early, reduce debugging time
  → Static type checking
  ≫ TypeScript for compile-time safety

### Principle
SHOULD use TypeScript to reduce debugging cycles and enable faster development
```

---

## Failure 4: "Our Thing" Not Marked NON-NEGOTIABLE

**Symptom**: Key differentiator has "SHOULD" classification

**Impact**: Core promise might be compromised

**Solution**: Upgrade to NON-NEGOTIABLE (breaks user promise if violated)

**Test**: "Can I delete this without breaking a user promise?" → NO = NON-NEGOTIABLE

**Prevention**: All "Our Thing" items from product.md become NON-NEGOTIABLE

**Example Fix**:
```markdown
❌ Before:
## Article III: Performance (SHOULD)
Dashboard should load quickly

✓ After:
## Article III: Performance (NON-NEGOTIABLE)

### User Need Evidence
From product.md:OurThing:42
- "Instant cross-platform visibility"

### Principle
Dashboard MUST load in <2 seconds (p95)
```

---

## Failure 5: Over-Constraining Tech Stack

**Symptom**: "MUST use PostgreSQL exclusively" when requirement is "ACID transactions"

**Impact**: Locks into specific product without flexibility

**Solution**: Constrain by capability, not specific technology

**Pattern**: "Data storage MUST provide ACID. Preferred: PostgreSQL. Acceptable: MySQL."

**Prevention**: Ask "Does this constrain HOW or WHAT?" (WHAT = correct)

**Example Fix**:
```markdown
❌ Before:
## Article II: Database (NON-NEGOTIABLE)
MUST use PostgreSQL

✓ After:
## Article II: Data Consistency (NON-NEGOTIABLE)

### User Need Evidence
From product.md:Persona1:Pain2:25
- "Executives distrust inconsistent data"

### Principle
Data storage MUST provide ACID transactions

**Preferred**: PostgreSQL (team expertise, proven)
**Acceptable**: MySQL with InnoDB
**Not Acceptable**: MongoDB, DynamoDB (eventual consistency)
```

---

## Failure 6: Missing Verification Methods

**Symptom**: Principle defined but no way to validate compliance

**Impact**: Unenforceable principles, drift over time

**Solution**: Add "Verification" section with specific checks

**Example**: "Monitor data staleness: alert if any source >15min stale"

**Prevention**: Every Article MUST have "Verification" section

**Example Fix**:
```markdown
❌ Before:
## Article III: Security
All data must be encrypted

✓ After:
## Article III: Data Encryption (NON-NEGOTIABLE)

### Principle
1. All data in transit MUST use TLS 1.3
2. All data at rest MUST use AES-256
3. Keys MUST rotate every 90 days

### Verification
**Automated**:
- CI/CD fails if non-HTTPS endpoints
- Database audit logs encryption daily
- Security scanner checks TLS weekly

**Monitoring**:
- Alert if key rotation >90 days
- Dashboard shows last-rotated per service
```

---

## Failure 7: Amendment Without Version Bump

**Symptom**: Constitution changed but version still 1.0.0

**Impact**: No change tracking, confusion about what's current

**Solution**: Follow semantic versioning (MAJOR.MINOR.PATCH)

**Pattern**:
- Article added/removed = MAJOR
- Article modified = MINOR
- Formatting only = PATCH

**Prevention**: Amendment workflow Step 2 (bump version)

**Example Fix**:
```markdown
❌ Before:
---
version: 1.0.0  # Not bumped!
---
## Article III: Performance (modified)

✓ After:
---
version: 1.1.0  # Bumped MINOR for modification
ratified: 2025-10-24  # Updated date
---
## Article III: Performance (modified)

## Amendment History
### Version 1.1.0 - 2025-10-24
**Changed**: Article III (Performance)
```

---

## Failure 8: Derivation Map Incomplete or Stale

**Symptom**: Articles exist but not in derivation map

**Impact**: Can't trace principles back to user needs

**Solution**: Update derivation map table with ALL Articles

**Validation**: Every Article row MUST appear in map

**Prevention**: Generate map as Step 5 in Derivation Workflow

**Example Fix**:
```markdown
❌ Before:
## Appendix: Constitution Derivation Map
| Article | Product.md Source | User Need | Technical Principle |
|---------|-------------------|-----------|---------------------|
| Article II | Persona1:Pain1:118 | Manual copying | <15min sync |
<!-- Article III missing! -->

✓ After:
## Appendix: Constitution Derivation Map
| Article | Product.md Source | User Need | Technical Principle |
|---------|-------------------|-----------|---------------------|
| Article II | Persona1:Pain1:118 | Manual copying | <15min sync latency |
| Article III | OurThing:42 | Instant visibility | <2s dashboard load |  <!-- ADDED -->
```

---

## Failure 9: User Needs from product.md Not Addressed

**Symptom**: Key pain point in product.md has no corresponding Article

**Impact**: User need ignored, constitutional gap

**Solution**: Add Article with derivation chain for that pain

**Validation**: All "Our Thing", North Star, and top 3 pains per persona MUST have Articles

**Prevention**: Bidirectional validation (Product → Constitution complete)

**Example Fix**:
```markdown
product.md has:
- Persona1:Pain1: Manual data copying (2hr/week waste)
- Persona1:Pain2: Executives distrust inconsistent data
- Persona1:Pain3: Reports take 30 minutes to generate  <!-- MISSING! -->

Constitution.md MUST add:
## Article V: Report Performance (NON-NEGOTIABLE)

### User Need Evidence
From product.md:Persona1:Pain3:87
- "Reports take 30 minutes to generate, slowing decisions"

### Technical Derivation (CoD^Σ)
Decision speed (product.md:Persona1:Pain3:87)
  ≫ Fast report generation required
  → Optimized queries + caching
  ≫ <10 second report generation

### Principle
Reports MUST generate in <10 seconds (p95)
```

---

## Failure 10: Classification Incorrect (NON-NEGOTIABLE vs SHOULD)

**Symptom**: Nice-to-have marked NON-NEGOTIABLE OR core promise marked SHOULD

**Impact**: Wrong prioritization, broken promises or over-constraining

**Solution**: Run 3 quick tests (see Validation Checks section)

**Tests**:
1. "Can I delete without breaking user promise?" NO = NON-NEGOTIABLE
2. "Can I trace to specific user pain?" YES = keep, NO = remove
3. "Does this enable Our Thing?" YES = NON-NEGOTIABLE

**Prevention**: Review classification after drafting each Article

**Example Fix**:
```markdown
❌ Before:
## Article IV: Code Style (NON-NEGOTIABLE)
Use Prettier for formatting

✓ After:
## Article IV: Code Consistency (SHOULD)
SHOULD use Prettier for formatting consistency

Rationale: Nice to have but not user-facing, downgrade to SHOULD

--- OR ---

❌ Before:
## Article III: Performance (SHOULD)
Dashboard should load quickly

✓ After:
## Article III: Performance (NON-NEGOTIABLE)
Dashboard MUST load in <2 seconds

Rationale: Enables "instant visibility" promise (Our Thing), upgrade to NON-NEGOTIABLE
```

---

## Failure 11: No Amendment History

**Symptom**: Constitution changed but no record of what/why

**Impact**: Can't understand evolution, lost context

**Solution**: Add amendment entry with before/after comparison

**Pattern**: Version X.Y.Z - Date, Changed, Reason, Before, After, Evidence

**Prevention**: Amendment workflow Step 6 (add history entry)

**Example Fix**:
```markdown
❌ Before:
Constitution modified but no history section

✓ After:
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

## Failure 12: Technical Jargon in Evidence Quotes

**Symptom**: Quoting technical terms from product.md (which shouldn't have them)

**Impact**: product.md boundary violation (it should be user-centric only)

**Solution**: If product.md has technical terms, fix THAT first (it's wrong)

**Enforcement**: product.md boundary violation check

**Prevention**: define-product skill enforces user-centric language only

**Example**:
```markdown
❌ Bad product.md quote:
"Users need PostgreSQL database for ACID transactions"
<!-- Technical terms! product.md shouldn't have these -->

✓ Good product.md quote:
"Executives distrust reports with inconsistent data"
<!-- User-centric language, no tech terms -->

Then constitution.md derives:
Distrust of inconsistent data ≫ Strong consistency → ACID → PostgreSQL
```

---

## Diagnostic Workflow

When constitution.md has issues:

1. **Check Prerequisites** (Failure 1)
   - Does product.md exist?
   - Does it have personas, pain points, "Our Thing"?

2. **Check Derivations** (Failures 2, 3)
   - Does every Article have CoD^Σ derivation?
   - Does every Article trace to product.md?

3. **Check Classification** (Failures 4, 10)
   - Are "Our Thing" items NON-NEGOTIABLE?
   - Are tech preferences correctly classified?

4. **Check Specificity** (Failure 5)
   - Constrained by capability, not product?
   - Appropriate flexibility allowed?

5. **Check Verification** (Failure 6)
   - Does every Article have verification method?
   - Are checks specific and measurable?

6. **Check Versioning** (Failures 7, 11)
   - Is version number current?
   - Is amendment history complete?

7. **Check Completeness** (Failures 8, 9)
   - Is derivation map complete?
   - Are all user needs addressed?

8. **Check Boundaries** (Failure 12)
   - Are evidence quotes user-centric?
   - No technical jargon in product.md?

---

## Quick Fixes

**For each failure mode**:
1. Identify symptom (what looks wrong?)
2. Apply solution (specific fix)
3. Re-validate (check passes now?)
4. Document learning (update process)

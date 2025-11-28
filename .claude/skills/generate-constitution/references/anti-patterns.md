# Anti-Patterns: Common Constitution Mistakes

**Purpose**: Learn from common mistakes to avoid creating weak or unjustified technical principles.

---

## Anti-Pattern 1: Tech Preferences Without User Justification

**Problem**: Technical decisions made without tracing back to user needs.

### ❌ Bad Example

```markdown
## Article I: Technology Stack (NON-NEGOTIABLE)

### Principle
Use React because it's popular
```

**Why Bad**:
- No product.md reference
- No user need quoted
- "Popular" is not a user need
- Tech preference masquerading as principle

### ✓ Good Example

```markdown
## Article V: Responsive UI Updates (NON-NEGOTIABLE)

### User Need Evidence
From product.md:OurThing:42
- "Real-time updates without page refresh"

### Technical Derivation (CoD^Σ)
Real-time visibility (product.md:OurThing:42)
  ≫ <100ms UI updates required
  → Reactive framework for state management
  ≫ React with optimized re-rendering

### Principle
Frontend MUST use React for <100ms UI reactivity to enable real-time updates

### Rationale
React's virtual DOM and efficient diffing algorithm enables sub-100ms UI updates required for "real-time visibility" promise. Alternative frameworks (Vue, Angular) can meet requirement but team expertise is strongest in React.
```

**Why Good**:
- Traces to specific user need (product.md:OurThing:42)
- User need quoted verbatim
- CoD^Σ derivation chain shows reasoning
- Principle is specific (React) with justification (<100ms)
- Rationale explains the connection

---

## Anti-Pattern 2: Over-Constraining Without Evidence

**Problem**: Locking into specific technology when the requirement is broader.

### ❌ Bad Example

```markdown
## Article III: Data Storage (NON-NEGOTIABLE)

### Principle
MUST use PostgreSQL exclusively
```

**Why Bad**:
- No user need evidence
- No flexibility (what if PostgreSQL doesn't meet needs?)
- Constrains "HOW" not "WHAT" is needed

### ✓ Good Example

```markdown
## Article III: Data Integrity (NON-NEGOTIABLE)

### User Need Evidence
From product.md:Persona1:Pain2:25
- "Executives distrust reports with inconsistent data across tools"

### Technical Derivation (CoD^Σ)
Executive trust requires data consistency (product.md:Persona1:Pain2:25)
  ≫ Strong consistency guarantees required
  → ACID transaction support
  ≫ Relational database with strict schema

### Principle
Data storage MUST provide ACID transactions with strict schema enforcement.

**Preferred**: PostgreSQL (team expertise, proven at scale)
**Acceptable**: MySQL with InnoDB (meets ACID requirements)
**Not Acceptable**: MongoDB, DynamoDB (eventual consistency)

### Rationale
ACID transactions ensure data consistency that executives require for trust. PostgreSQL preferred due to team expertise, but MySQL acceptable as it meets core ACID requirement.
```

**Why Good**:
- Focuses on capability (ACID) not specific product (PostgreSQL)
- Provides flexibility with acceptable alternatives
- Clear exclusion criteria (eventual consistency fails requirement)
- Traces to user need (executive trust)

---

## Anti-Pattern 3: Vague Principles

**Problem**: Unmeasurable principles that can't be verified.

### ❌ Bad Examples

```markdown
System should be performant
Code should follow best practices
UI should look modern
Architecture should be scalable
```

**Why Bad**:
- "Performant", "best practices", "modern", "scalable" are subjective
- No measurable criteria
- Can't verify compliance
- Different people interpret differently

### ✓ Good Examples

```markdown
Dashboard MUST load in <2 seconds (p95)
All code MUST pass TypeScript strict mode type checks
Buttons MUST have minimum 44x44px touch targets (WCAG AAA)
System MUST handle 10,000 concurrent users without degradation
```

**Why Good**:
- Specific measurable criteria
- Objective pass/fail
- Can be monitored and verified
- No ambiguity in interpretation

---

## Anti-Pattern 4: Missing Derivation Chains

**Problem**: Principles stated without showing how they connect to user needs.

### ❌ Bad Example

```markdown
## Article II: Performance (NON-NEGOTIABLE)

### Principle
API responses MUST be <200ms
```

**Why Bad**:
- No user need evidence
- No reasoning why 200ms specifically
- Can't trace back to product.md

### ✓ Good Example

```markdown
## Article II: API Performance (NON-NEGOTIABLE)

### User Need Evidence
From product.md:NorthStar:15
- "Users complete tasks 50% faster than competitors"

### Technical Derivation (CoD^Σ)
Task completion speed (product.md:NorthStar:15)
  ⊕ Dashboard real-time updates (product.md:OurThing:42)
  ≫ Perceived instant feedback required (<250ms human perception threshold)
  → API responses <200ms
  ≫ 50ms buffer for UI rendering

### Principle
All API endpoints MUST respond in <200ms (p95) to enable perceived instant feedback

### Rationale
Research shows <250ms feels "instant" to humans. 200ms API + 50ms UI rendering = 250ms total, enabling "50% faster" promise while maintaining instant-feel perception.

### Verification
Monitor API response times. Alert if any endpoint p95 exceeds 200ms.
```

**Why Good**:
- Full derivation chain with CoD^Σ operators
- Traces to specific North Star metric
- Explains the 200ms choice (250ms threshold - 50ms buffer)
- Verification method defined

---

## Anti-Pattern 5: No Verification Method

**Problem**: Principle defined but no way to validate compliance.

### ❌ Bad Example

```markdown
## Article III: Security (NON-NEGOTIABLE)

### Principle
All data MUST be encrypted
```

**Why Bad**:
- How do you check compliance?
- What counts as "encrypted"?
- Who verifies?

### ✓ Good Example

```markdown
## Article IV: Data Encryption (NON-NEGOTIABLE)

### User Need Evidence
From product.md:Persona2:Pain3:87
- "Healthcare customers require HIPAA compliance"

### Technical Derivation (CoD^Σ)
HIPAA compliance (product.md:Persona2:Pain3:87)
  ≫ Data encryption at rest and in transit required
  → TLS 1.3 for transit, AES-256 for rest
  ≫ Key rotation every 90 days

### Principle
1. All data in transit MUST use TLS 1.3
2. All data at rest MUST use AES-256 encryption
3. Encryption keys MUST rotate every 90 days

### Verification
**Automated Checks**:
- CI/CD fails if non-HTTPS endpoints detected
- Database audit logs encryption status daily
- Security scanner checks TLS version weekly

**Manual Audits**:
- Quarterly penetration testing
- Annual HIPAA compliance audit

**Monitoring**:
- Alert if key rotation exceeds 90-day threshold
- Dashboard shows last-rotated date per service
```

**Why Good**:
- Specific verification methods (automated, manual, monitoring)
- Clear criteria for each check
- Responsibility assigned (CI/CD, security team, auditors)

---

## Anti-Pattern 6: Orphaned Principles

**Problem**: Technical decision with no connection to product.md.

### ❌ Bad Example

```markdown
## Article VI: Code Quality (SHOULD)

### Principle
Code coverage should be >80%
```

**Why Bad**:
- No user need evidence
- Internal quality metric without user justification
- "80%" is arbitrary
- Doesn't trace to product.md

### ✓ Two Approaches

**Approach 1: Derive from user need**
```markdown
## Article VI: Reliability (NON-NEGOTIABLE)

### User Need Evidence
From product.md:Persona1:Pain4:102
- "System crashes during demos lose executive trust"

### Technical Derivation (CoD^Σ)
Demo reliability (product.md:Persona1:Pain4:102)
  ≫ Zero critical failures in production
  → Comprehensive testing required
  ≫ >80% code coverage on critical paths

### Principle
All user-facing critical paths MUST have >80% test coverage

### Rationale
Prevents demo-breaking crashes that damage executive trust. Focus on critical paths (not internal utils) ensures user-facing reliability.
```

**Approach 2: Remove if no user need**
If no user need exists for code coverage, consider:
- Is this really needed?
- Should it be in developer guidelines instead of constitution?
- Maybe it's a "nice to have" not a constitutional principle

---

## Key Lessons

1. **Always start with user need** - No user need = no constitutional principle
2. **Show your work** - CoD^Σ derivation chain required
3. **Be specific** - Measurable criteria, not vague aspirations
4. **Constrain capability, not technology** - "ACID transactions" not "PostgreSQL only"
5. **Define verification** - How will you know if this is followed?
6. **Check for orphans** - Every principle MUST trace to product.md

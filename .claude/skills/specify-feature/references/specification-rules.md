# Specification Rules and Anti-Patterns

**Purpose**: Best practices for creating technology-agnostic feature specifications and common mistakes to avoid.

---

## Core Rules

### Rule 1: Technology-Agnostic (Article IV)

**MUST**: Focus on WHAT and WHY, never HOW

**Good Examples** (WHAT/WHY):
- "Users need to see order status in real-time"
- "System must update status within 5 minutes of change"
- "Guest users can access their orders without login"

**Bad Examples** (HOW):
- "Create a React component that polls the API every 5 seconds"
- "Store data in PostgreSQL with indexed queries on order_id"
- "Use WebSocket connection for real-time updates"

**Enforcement**:
- ❌ NEVER mention: frameworks, databases, APIs, libraries, cloud providers
- ❌ NEVER specify: architecture patterns, data structures, algorithms
- ❌ NEVER describe: technical implementations, code organization

### Rule 2: User-Centric (Article VII)

**MUST**: Start from user needs, not system capabilities

**Good Examples**:
- "As a customer, I want to track my order so that I know when it arrives"
- "Users need confidence their payment information is secure"
- "First-time visitors should understand the value proposition in 10 seconds"

**Bad Examples**:
- "The system should have a tracking module"
- "Implement SSL encryption for the database"
- "Create a marketing homepage component"

**Enforcement**:
- ✓ Every requirement answers "Why does the user care?"
- ✓ User stories follow "As a [user], I want [capability], so that [value]" format
- ✓ Success metrics focus on user outcomes, not technical metrics

### Rule 3: Testably Specific

**MUST**: Requirements must be measurable and verifiable

**Good Examples**:
- "Page load time < 2 seconds"
- "Support < 10 order status inquiries per week"
- "90% of users complete checkout in under 3 minutes"

**Bad Examples**:
- "System should be fast"
- "Users should be happy"
- "Interface should be intuitive"

**Enforcement**:
- ✓ Every success criterion has a number
- ✓ Every acceptance scenario has "Given/When/Then"
- ✓ Every user story is independently verifiable

### Rule 4: Evidence-Based (Article II)

**MUST**: Include CoD^Σ trace with intelligence evidence

**Required Evidence**:
- Intelligence queries executed (project-intel.mjs commands)
- Findings with file:line references
- Assumptions explicitly marked with `[ASSUMPTION: rationale]`
- Clarifications marked with `[NEEDS CLARIFICATION: question]` (max 3)

**Example**:
```markdown
## CoD^Σ Evidence Trace

Intelligence Queries:
- project-intel.mjs --search "checkout" --json → /tmp/spec_intel_patterns.json
  Findings: specs/003-checkout/spec.md:45 (existing payment flow)

Assumptions:
- [ASSUMPTION: Social login will reuse existing OAuth infrastructure per specs/002-auth/]

Clarifications Needed:
- [NEEDS CLARIFICATION: Should guest checkout support saved addresses?]
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Premature Technical Decisions

**Problem**: Including implementation details in specification

**Examples**:
- ❌ "Use React hooks for state management"
- ❌ "Store data in MongoDB collections"
- ❌ "Create REST API endpoints"
- ❌ "Deploy on AWS Lambda"

**Why Bad**: Locks in technical choices before evaluating options

**Fix**: Describe capabilities, not implementation
- ✓ "Users can save their preferences"
- ✓ "System persists data reliably"
- ✓ "Application communicates with backend"

### Anti-Pattern 2: Vague Requirements

**Problem**: Requirements that can't be tested or verified

**Examples**:
- ❌ "System should be fast"
- ❌ "Interface should be user-friendly"
- ❌ "App should scale well"
- ❌ "Feature should be secure"

**Why Bad**: Impossible to verify completion, no acceptance criteria

**Fix**: Make requirements specific and measurable
- ✓ "Page load time < 2 seconds for 95% of requests"
- ✓ "Users complete checkout in 3 steps or fewer"
- ✓ "System handles 10,000 concurrent users"
- ✓ "Data encrypted in transit and at rest"

### Anti-Pattern 3: Too Many Clarifications

**Problem**: Specification with >3 [NEEDS CLARIFICATION] markers

**Examples**:
- ❌ Spec with 8 clarification questions
- ❌ Every requirement has "[NEEDS CLARIFICATION]"
- ❌ Ambiguous scope in multiple sections

**Why Bad**: Indicates user description was too vague for specification

**Fix**: Resolve most ambiguities through dialogue BEFORE creating spec
- ✓ Max 3 [NEEDS CLARIFICATION] markers
- ✓ Use clarify-specification skill to resolve before planning
- ✓ If >3 markers, quality gate should have blocked (score < 7.0)

### Anti-Pattern 4: Solution-Driven Requirements

**Problem**: Starting with solution instead of problem

**Examples**:
- ❌ "Add a dashboard with charts"
- ❌ "Implement search with filters"
- ❌ "Create a notification system"

**Why Bad**: Solution may not address the actual problem

**Fix**: Start with problem, derive solution
- ✓ Problem: "Users can't find past orders easily"
  - Solution (in plan): Dashboard with order history
- ✓ Problem: "Users need to track shipments without calling"
  - Solution (in plan): Real-time tracking page

### Anti-Pattern 5: Missing Edge Cases

**Problem**: Only describing happy path scenarios

**Examples**:
- ❌ Only "user logs in successfully" scenario
- ❌ No error handling requirements
- ❌ No boundary condition documentation

**Why Bad**: Leads to brittle implementation that fails unexpectedly

**Fix**: Document edge cases and error scenarios
- ✓ "User enters invalid email: show format error"
- ✓ "Payment fails: preserve cart and retry"
- ✓ "Session expires: redirect to login with return URL"

### Anti-Pattern 6: System-Centric Language

**Problem**: Describing what system does instead of what users get

**Examples**:
- ❌ "System processes payments"
- ❌ "Database stores user preferences"
- ❌ "API returns order status"

**Why Bad**: Loses focus on user value

**Fix**: Rephrase from user perspective
- ✓ "Users complete purchases securely"
- ✓ "Users see their saved preferences on return"
- ✓ "Users know where their order is"

---

## Quality Checklist

Before finalizing specification, verify:

**Technology-Agnostic**:
- [ ] No framework names (React, Vue, Angular, etc.)
- [ ] No database choices (PostgreSQL, MongoDB, etc.)
- [ ] No architecture patterns (REST, GraphQL, microservices, etc.)
- [ ] No cloud providers (AWS, Azure, GCP, etc.)
- [ ] No specific libraries or packages

**User-Centric**:
- [ ] Every requirement explains user value
- [ ] User stories follow "As a/I want/So that" format
- [ ] Success criteria focus on user outcomes
- [ ] Edge cases consider user experience

**Testably Specific**:
- [ ] Success metrics have numbers
- [ ] Acceptance scenarios use "Given/When/Then"
- [ ] Requirements are verifiable
- [ ] No vague terms ("fast", "intuitive", "better")

**Evidence-Based**:
- [ ] Intelligence queries documented
- [ ] Findings with file:line references
- [ ] Assumptions marked explicitly
- [ ] Clarifications marked (max 3)

**Complete**:
- [ ] Problem statement clear
- [ ] User stories prioritized (P1/P2/P3)
- [ ] Functional requirements defined
- [ ] Success criteria measurable
- [ ] Edge cases documented

---

## Common Traps

**Trap 1: "Just add X to the spec"**
- Adding technical details to move forward
- Solution: Keep spec pure, add details to plan.md later

**Trap 2: "We already know the tech stack"**
- Assuming implementation approach upfront
- Solution: Defer tech decisions to planning phase

**Trap 3: "This is too simple to document"**
- Skipping specification for "obvious" features
- Solution: Every feature needs specification for audit trail

**Trap 4: "The user didn't provide enough detail"**
- Creating vague spec from vague input
- Solution: Quality gate should block (score < 7.0), request more detail

---

## Related Rules

**See Also**:
- @.claude/shared-imports/constitution.md - Article IV (Specification-First Development)
- @.claude/templates/feature-spec.md - Required specification structure
- @.claude/skills/clarify-specification/SKILL.md - Resolving ambiguities

**Constitutional Articles**:
- **Article I**: Intelligence-First (query before writing)
- **Article II**: Evidence-Based Reasoning (CoD^Σ traces)
- **Article IV**: Specification-First (WHAT/WHY before HOW)
- **Article VII**: User-Story-Centric (organize by user value)

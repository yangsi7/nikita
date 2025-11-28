# Clarification Workflow: Resolve Specification Ambiguities

**Purpose**: Systematically eliminate ambiguity from specifications through structured questioning (max 5 questions per iteration).

**Constitutional Authority**: Article IV (Specification-First Development), Article V (Template-Driven Quality)

---

## Phase 1: Load Specification and Detect Ambiguities

### Step 1.1: Read Current Specification

Identify current feature from SessionStart hook context or user input.

```bash
Read specs/<feature-number>-<name>/spec.md
```

### Step 1.2: Scan Against Ambiguity Categories

Use `@.claude/templates/clarification-checklist.md` categories:

**10+ Ambiguity Categories**:
1. **Functional Scope & Behavior**: What exactly does "process" mean? Which actions are in/out of scope?
2. **Domain & Data Model**: What entities exist? What are their relationships and cardinality?
3. **Interaction & UX Flow**: How do users navigate? What's the exact sequence of screens/actions?
4. **Non-Functional Requirements**: Performance targets? Scale expectations? Security requirements?
5. **Integration & Dependencies**: Which external systems? What data flows in/out?
6. **Edge Cases & Failure Scenarios**: What happens when X fails? How to handle boundary conditions?
7. **Constraints & Tradeoffs**: Budget limits? Technology restrictions? Compliance requirements?
8. **Terminology & Definitions**: What does "active user" mean? How is "completion" defined?
9. **Permissions & Access Control**: Who can do what? What are the authorization rules?
10. **State & Lifecycle**: What states can entities be in? What triggers transitions?

### Step 1.3: Identify Gaps and Mark Coverage

For each category, assess coverage:
- **Clear**: Well-defined, no ambiguity
- **Partial**: Some aspects defined, others unclear
- **Missing**: Not addressed in specification

**Output**: Coverage matrix showing which categories need clarification

---

## Phase 2: Prioritize Clarification Questions

### Step 2.1: Extract [NEEDS CLARIFICATION] Markers

Count existing markers in specification (Article IV limit: max 3).

### Step 2.2: Prioritize by Impact

**Priority Order** (Article IV, Section 4.2):
1. **Scope** (highest impact) - Affects what gets built
2. **Security** - Affects risk and compliance
3. **UX Flow** - Affects user experience
4. **Technical** (lowest impact) - Implementation details

**Maximum 5 Questions Per Iteration** (Article IV requirement)

### Step 2.3: Generate Questions with Recommendations

Each question MUST include:
- **Context**: Why this matters
- **Question**: Specific, focused inquiry
- **Options**: 2-3 recommendations based on common patterns
- **Impact**: What depends on this answer

**Example**:
```
**Question 1: Authentication Method** (Priority: Security)

Context: Specification mentions "user login" but doesn't specify authentication approach.

Question: How should users authenticate?

Options:
A) Email/password (simplest, industry standard)
B) Social login only (Google, GitHub - reduces friction)
C) Both email/password + social (maximum flexibility)

Recommendation: Option C provides flexibility while maintaining control.

Impact: Affects data model (user table schema), security requirements (password hashing, OAuth), and UX flow (login screens).

Intelligence Evidence:
- project-intel.mjs found: src/auth/login.tsx:12 (existing email/password flow)
- Recommendation aligns with existing pattern
```

---

## Phase 3: Interactive Clarification

### Step 3.1: Present Questions Sequentially

**ONE QUESTION AT A TIME** for complex topics (Article IV requirement).

Present question with:
- Numbered options
- Recommendation highlighted
- Impact analysis
- Evidence from intelligence queries (if available)

### Step 3.2: Capture User Response

Record answer with rationale:
```
**Answer to Q1**: Option C (both methods)

**Rationale**: Need to support existing email users while enabling social login for new users.

**Additional Context**: Google and GitHub OAuth only (not Facebook).
```

### Step 3.3: Update Specification Incrementally

**After EACH answer**:
1. Edit specification to incorporate answer
2. Remove or resolve [NEEDS CLARIFICATION] marker
3. Add functional requirement with answer
4. Verify no contradictions introduced

**Example Update**:
```markdown
## Functional Requirements

- **FR-001**: System MUST support email/password authentication
- **FR-002**: System MUST support OAuth2 social login (Google, GitHub)
- **FR-003**: Users MUST be able to link multiple auth methods to one account
```

**Remove**:
```markdown
- **FR-XXX**: System MUST authenticate users via [NEEDS CLARIFICATION: auth method not specified]
```

---

## Phase 4: Validation and Completion

### Step 4.1: Verify Consistency

**Check for contradictions**:
- Do new requirements conflict with existing ones?
- Are priorities consistent?
- Do user stories align with clarifications?

### Step 4.2: Update Clarification Checklist

Mark categories as **Clear** after resolution:

```markdown
## Clarification Status

| Category | Status | Notes |
|----------|--------|-------|
| Functional Scope | Clear | All features defined |
| Domain Model | Clear | User/Auth entities specified |
| UX Flow | Clear | Login/register flows documented |
| Non-Functional | Partial | Need performance targets |
| Integration | Clear | Google/GitHub OAuth |
...
```

### Step 4.3: Report Completion

**Output**:
```
✓ Clarification complete: <N> questions resolved

Resolved:
- Q1: Authentication method → Email/password + Social (Google, GitHub)
- Q2: User roles → Admin, User, Guest with specified permissions
- Q3: Data retention → 90 days for inactive accounts

Updated Specification:
- Added FR-001 through FR-008 (authentication requirements)
- Updated User Stories with auth flow details
- Removed all [NEEDS CLARIFICATION] markers

Remaining Ambiguities: 0 (ready for planning)

Next Step: Use create-implementation-plan skill to define HOW
```

---

## Question Generation Guidelines

### Always Include Intelligence Evidence

Before generating recommendations, query project-intel.mjs:

```bash
# Find similar features
project-intel.mjs --search "auth" --type ts --json

# Get symbols from relevant files
project-intel.mjs --symbols src/auth/login.tsx --json
```

Include findings in recommendation rationale:
```
Intelligence Evidence:
- Found existing pattern at src/auth/login.tsx:12 (email/password)
- Found OAuth integration at src/auth/oauth.ts:45 (Google)
- Recommendation: Extend existing patterns for consistency
```

### Structure Each Question

```markdown
**Question N: [Topic]** (Priority: [Scope|Security|UX|Technical])

Context: [Why this matters, what's unclear]

Question: [Specific inquiry]

Options:
A) [Option 1] ([trade-off])
B) [Option 2] ([trade-off])
C) [Option 3] ([trade-off])

Recommendation: [Which option and why]

Impact: [What depends on this decision]

Intelligence Evidence: [Findings from project-intel.mjs or MCP queries]
```

---

## Output Files

- `specs/$FEATURE/spec.md` - Updated incrementally with clarifications
- Removed [NEEDS CLARIFICATION] markers
- Added functional requirements with clarified details

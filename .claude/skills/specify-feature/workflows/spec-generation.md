# Phase 3: Generate Specification with CoD^Σ Evidence

**Purpose**: Create technology-agnostic specification document with intelligence evidence.

**Template**: @.claude/templates/feature-spec.md

---

## Step 3.1: Create Feature Directory Structure

**Derive feature name from user description**:

```bash
# Example: "user authentication" → "user-authentication"
FEATURE_NAME=$(echo "<user-description>" | sed 's/[^a-zA-Z0-9]/-/g' | tr '[:upper:]' '[:lower:]' | sed 's/--*/-/g' | sed 's/^-//;s/-$//')
```

**Create directory**:

```bash
NEXT_NUM=$(printf "%03d" $(($(fd --type d --max-depth 1 '^[0-9]{3}-' specs/ 2>/dev/null | wc -l) + 1)))
FEATURE_NAME="<derived-from-user-description>"

mkdir -p specs/$NEXT_NUM-$FEATURE_NAME
```

**Directory naming convention**:
- Format: `###-<domain>-<capability>`
- Example: `004-auth-social-login`
- Use kebab-case (lowercase with hyphens)

---

## Step 3.2: Create Git Branch

**For feature isolation**:

```bash
if git rev-parse --git-dir >/dev/null 2>&1; then
    BRANCH_NAME="$NEXT_NUM-$FEATURE_NAME"
    git checkout -b "$BRANCH_NAME"
fi
```

**Branch naming matches directory**:
- Example: `004-auth-social-login`
- Consistent with directory for easy tracking

---

## Step 3.3: Generate Specification Content

**Use template structure from @.claude/templates/feature-spec.md**:

```markdown
---
feature: <number>-<name>
created: <YYYY-MM-DD>
status: Draft
priority: P1
---

# Feature Specification: <Feature Title>

## Problem Statement
[From Phase 2, Step 2.1]

## User Stories
[From Phase 2, Step 2.2 - all stories with priorities]

## Functional Requirements
[From Phase 2, Step 2.3]

## Success Criteria
[From Phase 2, Step 2.4]

## CoD^Σ Evidence Trace

Intelligence Queries:
- project-intel.mjs --search "<keywords>" → /tmp/spec_intel_patterns.json
  Findings: [file:line references to similar features]
- project-intel.mjs --overview → /tmp/spec_intel_overview.json
  Context: [existing architecture patterns]

Assumptions:
- [ASSUMPTION: rationale based on intelligence findings]

Clarifications Needed:
- [NEEDS CLARIFICATION: specific question] (max 3)

## Edge Cases
[From Phase 2, Step 2.4]
```

**YAML Frontmatter Fields**:
- `feature`: Feature identifier (e.g., "004-auth-social-login")
- `created`: Current date (YYYY-MM-DD format)
- `status`: Always "Draft" initially
- `priority`: Primary priority level (P1 for MVP features)

**CoD^Σ Evidence Trace Requirements**:
1. **Intelligence Queries**: Document all project-intel.mjs queries executed
   - Query command
   - Output file path (/tmp/*.json)
   - Key findings with file:line references

2. **Assumptions**: Explicit assumptions based on intelligence findings
   - Format: `[ASSUMPTION: rationale]`
   - Based on evidence, not guesses
   - Example: `[ASSUMPTION: Authentication follows existing src/auth/ patterns per intel query]`

3. **Clarifications Needed**: Unknown or ambiguous requirements
   - Format: `[NEEDS CLARIFICATION: specific question]`
   - Max 3 markers (resolve most through dialogue first)
   - Example: `[NEEDS CLARIFICATION: Should social login support GitHub, Google, or both?]`

**Example CoD^Σ Trace**:
```markdown
## CoD^Σ Evidence Trace

Intelligence Queries:
- project-intel.mjs --search "auth login" --type tsx --json → /tmp/spec_intel_patterns.json
  Findings:
  - src/components/Login.tsx:12-45 (existing email/password login form)
  - src/utils/auth.ts:23-67 (JWT token management)
  - src/services/authService.ts:15 (login API integration)

- project-intel.mjs --overview --json → /tmp/spec_intel_overview.json
  Context:
  - Authentication features in src/auth/ directory
  - API services in src/services/
  - Shared utilities in src/utils/

Assumptions:
- [ASSUMPTION: Social login will integrate with existing JWT auth system (src/utils/auth.ts:23)]
- [ASSUMPTION: Social providers will return user email for account matching]

Clarifications Needed:
- [NEEDS CLARIFICATION: Should users be able to link multiple social accounts to one email?]
```

---

## Step 3.4: Save Specification

```bash
Write specs/$NEXT_NUM-$FEATURE_NAME/spec.md
```

**File naming**:
- Always `spec.md` (standardized name)
- Located in feature directory
- Example: `specs/004-auth-social-login/spec.md`

---

## Verification Checklist

Before proceeding to Phase 4, verify specification includes:

- [ ] YAML frontmatter with all required fields
- [ ] Problem statement (what, why, who, current situation)
- [ ] User stories with P1/P2/P3 priorities
- [ ] Functional requirements (technology-agnostic)
- [ ] Success criteria (measurable outcomes)
- [ ] CoD^Σ Evidence Trace:
  - [ ] Intelligence queries documented
  - [ ] Findings with file:line references
  - [ ] Assumptions explicitly marked
  - [ ] Clarifications marked (max 3)
- [ ] Edge cases documented
- [ ] NO technical implementation details

**Constitutional Compliance**:
- ✓ Article I: Intelligence queries executed before file operations
- ✓ Article II: CoD^Σ trace with evidence saved to /tmp/*.json
- ✓ Article IV: Specification is technology-agnostic (WHAT/WHY only)
- ✓ Article VII: User stories are independently testable with priorities

---

## Directory Structure After Completion

```
specs/
└── ###-<feature-name>/
    └── spec.md          # Technology-agnostic specification (this phase)
    └── plan.md          # Implementation plan (next: /plan command)
    └── tasks.md         # Task breakdown (next: generate-tasks)
    └── research.md      # Technical research (next: create-implementation-plan)
    └── data-model.md    # Data schemas (next: create-implementation-plan)
```

**Note**: Only spec.md is created in this phase. Other files are created automatically by subsequent workflow steps.

**Next Phase**: Proceed to Report to User (Phase 4)

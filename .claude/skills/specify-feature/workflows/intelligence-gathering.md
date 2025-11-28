# Phase 1: Intelligence-First Context Gathering

**Purpose**: Query project intelligence BEFORE creating specification to discover existing patterns, related features, and architectural context.

**Article I Compliance**: MUST query project-intel.mjs before reading any files or creating specification.

---

## Step 1.1: Auto-Number Next Feature

**Determine the next sequential feature number:**

```bash
!`fd --type d --max-depth 1 '^[0-9]{3}-' specs/ 2>/dev/null | sort | tail -1`
```

**Parse Result**:
```bash
# Example output: specs/003-reporting
# Next feature number: 004

NEXT_NUM=$(printf "%03d" $(($(fd --type d --max-depth 1 '^[0-9]{3}-' specs/ 2>/dev/null | wc -l) + 1)))
```

**If specs/ directory doesn't exist**:
```bash
mkdir -p specs/
NEXT_NUM="001"
```

---

## Step 1.2: Query Existing Patterns

**Search for related features and patterns:**

```bash
!`project-intel.mjs --search "<user-keywords>" --type md --json > /tmp/spec_intel_patterns.json`
```

**Extract Insights**:
```bash
# Parse JSON to find:
# - Similar feature specifications
# - Related implementation patterns
# - Naming conventions used
# - Priority patterns (P1/P2/P3 distribution)

# Example insights:
# - Found 3 specs with authentication patterns
# - Naming: ###-<domain>-<capability> (e.g., 002-auth-oauth)
# - Priority: MVP features consistently use P1, enhancements P2/P3
```

**Save Evidence**:
```
Intelligence Evidence:
- Query: project-intel.mjs --search "auth login" --type md
- Findings:
  - specs/002-auth-basic/spec.md:15-42 (email/password pattern)
  - specs/003-user-management/spec.md:28 (user model reference)
- Pattern: Authentication features use security-first approach
```

---

## Step 1.3: Understand Project Architecture

**Get project overview to understand existing structure:**

```bash
!`project-intel.mjs --overview --json > /tmp/spec_intel_overview.json`
```

**Architecture Insights**:
```bash
# Parse JSON to identify:
# - Main directories and their purposes
# - Key technologies detected (language, frameworks)
# - Code organization patterns
# - Existing feature domains

# Example insights:
# - Frontend: src/components/, src/pages/
# - Backend: api/, services/
# - Shared: lib/, utils/
# - Features organized by domain (auth/, checkout/, etc.)
```

**Document Context**:
```
Project Context:
- Architecture: Frontend + Backend (detected from overview)
- Domains: auth, checkout, reporting, user-management
- Conventions: Feature directories in src/<domain>/
```

---

## Intelligence Evidence Format

**Include in specification's CoD^Σ Evidence Trace**:

```markdown
## CoD^Σ Evidence Trace

Intelligence Queries:
- project-intel.mjs --search "<keywords>" → /tmp/spec_intel_patterns.json
  Findings: [file:line references to similar features]
- project-intel.mjs --overview → /tmp/spec_intel_overview.json
  Context: [existing architecture patterns]

Assumptions:
- [ASSUMPTION: rationale based on intelligence findings]

Clarifications Needed:
- [NEEDS CLARIFICATION: specific question]
```

---

## Token Efficiency

**Comparison**:
- **Without intelligence**: Read 10+ spec files (~5,000 tokens) to find patterns
- **With intelligence**: 2 queries (~350 tokens) + targeted reads (~500 tokens)
- **Savings**: ~85%

---

## Enforcement Checklist

Before proceeding to Phase 2, verify:

- [ ] Feature number determined (auto-numbered or manual)
- [ ] Pattern search executed (even if no results)
- [ ] Project overview captured
- [ ] Evidence saved to /tmp/*.json files
- [ ] Insights documented for specification

**Next Phase**: Proceed to Extract User Requirements (Phase 2)

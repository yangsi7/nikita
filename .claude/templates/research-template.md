---
description: "Research findings template for implementation planning with intelligence-first evidence"
---

# Research: [Feature Name]

**Feature**: [feature-id]
**Created**: [YYYY-MM-DD]
**Purpose**: Document architectural decisions, patterns, and external knowledge for implementation plan
**Intelligence Source**: project-intel.mjs queries + MCP tools + external documentation

---

## Executive Summary

**Key Findings**:
1. [Finding 1 - brief summary]
2. [Finding 2 - brief summary]
3. [Finding 3 - brief summary]

**Recommended Approach**: [One-sentence recommendation based on research]

---

## 1. Existing Patterns Analysis

**Intelligence Queries Used**:
```bash
# Pattern discovery
project-intel.mjs --search "[keyword]" --type tsx --json
project-intel.mjs --symbols [relevant-file] --json
project-intel.mjs --dependencies [relevant-file] --json
```

### Pattern 1: [Pattern Name]

**Location**: `[file:line]` (found via intel query)

**Description**: [What this pattern does]

**Implementation**:
```[language]
// Code example or pseudocode from existing codebase
[relevant code snippet]
```

**Pros**:
- [Advantage 1]
- [Advantage 2]

**Cons**:
- [Limitation 1]
- [Limitation 2]

**Applicability**: [How this applies to current feature]

**CoD^Σ Evidence**:
- Pattern exists at `[file:line]`
- Used by [X] components: `[file1]`, `[file2]`, `[file3]`
- Dependency analysis: [upstream/downstream usage]

---

### Pattern 2: [Alternative Pattern Name]

**Location**: `[file:line]` (found via intel query)

**Description**: [What this pattern does]

**Implementation**:
```[language]
// Code example or pseudocode
[relevant code snippet]
```

**Pros**:
- [Advantage 1]
- [Advantage 2]

**Cons**:
- [Limitation 1]
- [Limitation 2]

**Applicability**: [How this applies to current feature]

**CoD^Σ Evidence**:
- Pattern exists at `[file:line]`
- Usage context: [description]

---

[Add more patterns as needed]

---

## 2. External Library/Framework Research

### Library 1: [Library Name]

**Source**: [MCP tool query / official documentation URL]

**Version**: [X.Y.Z]

**Purpose**: [Why we're considering this library]

**Key Features**:
- [Feature 1]: [Brief description]
- [Feature 2]: [Brief description]
- [Feature 3]: [Brief description]

**API Examples**:
```[language]
// Usage example
[code example from documentation]
```

**Pros**:
- [Advantage 1]
- [Advantage 2]
- [Advantage 3]

**Cons**:
- [Limitation 1]
- [Limitation 2]

**License**: [License type]

**Community Health**:
- GitHub stars: [X]
- Last updated: [date]
- Active maintainers: [X]
- Open issues: [X]

**Compatibility**:
- Works with: [existing tech stack components]
- Conflicts with: [any known conflicts]

**Evidence**:
- Documentation: [URL]
- MCP query: [query used]
- Community reputation: [Stack Overflow, Reddit, etc.]

---

### Library 2: [Alternative Library Name]

[Same structure as Library 1]

---

[Add more libraries as needed]

---

## 3. Architectural Decision Records (ADRs)

### ADR-001: [Decision Title]

**Status**: [Proposed / Accepted / Superseded]

**Context**: [What is the situation requiring a decision?]

**Decision**: [What is the change that we're proposing/have agreed to?]

**Consequences**: [What becomes easier or more difficult after this decision?]

**Pros**:
- [Benefit 1]
- [Benefit 2]

**Cons**:
- [Trade-off 1]
- [Trade-off 2]

**Alternatives Considered**:
1. [Alternative 1]: [Why rejected/chosen]
2. [Alternative 2]: [Why rejected/chosen]

**CoD^Σ Reasoning**:
- Evidence for decision: [file:line references, benchmark data, documentation]
- Dependency analysis: [what depends on this decision]
- Risk assessment: [what could go wrong]

---

### ADR-002: [Decision Title]

[Same structure as ADR-001]

---

[Add more ADRs as needed]

---

## 4. Technical Constraints & Considerations

### Performance Considerations

**Requirements** (from spec.md):
- [Requirement 1]: [specific performance target]
- [Requirement 2]: [specific performance target]

**Findings**:
- [Finding 1]: [Evidence from benchmarks, documentation, or existing code]
- [Finding 2]: [Evidence]

**Recommendations**:
- [Recommendation 1]: [Specific action to meet performance requirements]
- [Recommendation 2]: [Specific action]

**Evidence**:
- Benchmark results: [data or reference]
- Existing performance at `[file:line]`: [metrics]

---

### Security Considerations

**Requirements** (from spec.md):
- [Security requirement 1]
- [Security requirement 2]

**Findings**:
- [Security concern 1]: [Evidence]
- [Security concern 2]: [Evidence]

**Recommendations**:
- [Security measure 1]: [How to implement]
- [Security measure 2]: [How to implement]

**Best Practices** (from MCP/documentation):
- [Practice 1]: [Reference]
- [Practice 2]: [Reference]

---

### Scalability Considerations

**Requirements** (from spec.md):
- [Scalability requirement 1]
- [Scalability requirement 2]

**Findings**:
- [Scalability pattern 1]: [Evidence from codebase at file:line]
- [Scalability pattern 2]: [Evidence]

**Recommendations**:
- [Approach 1]: [How to implement]
- [Approach 2]: [How to implement]

---

### Compatibility Considerations

**Requirements**:
- Browser support: [requirements from spec]
- Platform support: [requirements from spec]
- Backward compatibility: [requirements from spec]

**Findings**:
- [Compatibility issue 1]: [Evidence]
- [Compatibility issue 2]: [Evidence]

**Recommendations**:
- [Solution 1]: [How to handle]
- [Solution 2]: [How to handle]

---

## 5. Integration Points Analysis

### Integration 1: [System/Service Name]

**Type**: [Internal service / External API / Database / Message queue]

**Purpose**: [Why we need to integrate]

**Requirements** (from spec.md):
- [Integration requirement 1]
- [Integration requirement 2]

**Existing Integration Patterns**:
- Pattern found at: `[file:line]` (via project-intel.mjs)
- Authentication: [method used]
- Data format: [format used]
- Error handling: [approach used]

**Recommendations**:
- Follow existing pattern at `[file:line]`
- Modifications needed: [list any adaptations]

**CoD^Σ Evidence**:
- Integration pattern: `[file:line]`
- Dependency analysis: [related integrations]
- Success criteria: [how to verify integration works]

---

### Integration 2: [System/Service Name]

[Same structure as Integration 1]

---

[Add more integrations as needed]

---

## 6. Data Flow Analysis

**Overview**: [High-level description of data flow]

**Flow Diagram** (text-based):
```
[User] → [Frontend Component] → [API Endpoint] → [Service Layer] → [Database]
  ↓           ↓                      ↓                 ↓               ↓
[Input]   [Validation]          [Business Logic]  [Data Transform] [Persistence]
```

**Key Data Transformations**:
1. **Input → Validated Data**: [transformation description]
   - Location: `[file:line]` (existing pattern)
   - Validation rules: [rules]

2. **API → Service**: [transformation description]
   - Location: `[file:line]` (existing pattern)
   - Transformation logic: [description]

3. **Service → Database**: [transformation description]
   - Location: `[file:line]` (existing pattern)
   - Mapping: [description]

**Error Handling Points**:
- Point 1: [where errors are caught, how they're handled]
- Point 2: [where errors are caught, how they're handled]

---

## 7. Testing Strategy Research

### Existing Test Patterns

**Unit Test Pattern**:
- Location: `[test-file:line]` (found via project-intel.mjs)
- Framework: [Jest / Vitest / Mocha / etc.]
- Example structure:
```[language]
// Example from existing tests
[test code snippet]
```

**Integration Test Pattern**:
- Location: `[test-file:line]`
- Approach: [description]
- Example structure:
```[language]
[test code snippet]
```

**E2E Test Pattern** (if applicable):
- Location: `[test-file:line]`
- Tool: [Playwright / Cypress / etc.]
- Approach: [description]

**Recommendations**:
- Follow existing patterns at `[file:line]`
- Adaptations needed: [list]

---

## 8. Dependencies & Prerequisites

### Required Dependencies

| Dependency | Version | Purpose | Source |
|------------|---------|---------|--------|
| [package-name] | [X.Y.Z] | [why needed] | [npm / MCP query result] |
| [package-name] | [X.Y.Z] | [why needed] | [npm / MCP query result] |

### Dev Dependencies

| Dependency | Version | Purpose | Source |
|------------|---------|---------|--------|
| [package-name] | [X.Y.Z] | [why needed] | [npm / MCP query result] |

### Infrastructure Requirements

- [Requirement 1]: [description]
- [Requirement 2]: [description]

### Prerequisite Features

- [Feature 1]: Must be implemented first because [reason]
- [Feature 2]: Must exist because [reason]

---

## 9. Risk Assessment

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| [Risk 1] | [High/Medium/Low] | [High/Medium/Low] | [Mitigation strategy] |
| [Risk 2] | [High/Medium/Low] | [High/Medium/Low] | [Mitigation strategy] |

### Dependency Risks

| Dependency | Risk | Mitigation |
|------------|------|------------|
| [Library/service] | [Description of risk] | [How to mitigate] |

### Integration Risks

| Integration Point | Risk | Mitigation |
|-------------------|------|------------|
| [System name] | [Description of risk] | [How to mitigate] |

---

## 10. Implementation Recommendations

### Recommended Approach

**Primary Recommendation**: [Approach name]

**Rationale**:
1. [Reason 1 with evidence]
2. [Reason 2 with evidence]
3. [Reason 3 with evidence]

**Implementation Steps**:
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Expected Effort**: [Time estimate based on similar implementations]

**CoD^Σ Chain**:
```
Requirements (spec.md)
  → Existing Pattern ([file:line])
  → Library Choice ([library-name] via MCP)
  → Integration Approach ([file:line])
  → Test Strategy ([test-file:line])
  → Implementation Plan (plan.md)
```

---

### Alternative Approaches (if applicable)

**Alternative 1**: [Approach name]

**Pros**:
- [Advantage 1]
- [Advantage 2]

**Cons**:
- [Limitation 1]
- [Limitation 2]

**Why Not Recommended**: [Reasoning]

---

## 11. Open Questions

**Questions Requiring Clarification**:
1. [Question 1]: [Why this needs clarification]
   - **Impact**: [High/Medium/Low]
   - **Blocking**: [Yes/No]

2. [Question 2]: [Why this needs clarification]
   - **Impact**: [High/Medium/Low]
   - **Blocking**: [Yes/No]

**Assumptions** (need validation):
1. [Assumption 1]: [What we're assuming and why]
2. [Assumption 2]: [What we're assuming and why]

---

## 12. Constitution Compliance Check

### Article I: Intelligence-First Principle
- ✓ All patterns discovered via project-intel.mjs queries
- ✓ Evidence includes file:line references
- ✓ MCP tools used for external documentation

### Article II: Evidence-Based Reasoning (CoD^Σ)
- ✓ All recommendations backed by evidence
- ✓ CoD^Σ chains documented for key decisions
- ✓ File:line references provided throughout

### Article VI: Simplicity & Anti-Abstraction
- ✓ Recommendations prefer existing patterns over new abstractions
- ✓ New patterns justified with clear evidence
- ✓ Complexity limited to necessary minimum

---

## References

### Internal References (via project-intel.mjs)
- `[file:line]` - [brief description]
- `[file:line]` - [brief description]

### External References (via MCP tools)
- [Library documentation URL]
- [Framework guide URL]
- [Best practices article URL]

### Additional Resources
- [Resource 1]: [URL or reference]
- [Resource 2]: [URL or reference]

---

**Research Completed**: [YYYY-MM-DD]
**Next Step**: Incorporate findings into plan.md implementation plan
**Confidence Level**: [High/Medium/Low] based on evidence quality and completeness

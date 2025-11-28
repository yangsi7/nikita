# Skill Template

**Purpose**: Use this template to create new skills for Claude Code Intelligence Toolkit

**Location**: `.claude/skills/[skill-name]/SKILL.md`

---

## YAML Frontmatter (Required)

```yaml
---
name: [skill-name]
description: [One sentence describing when to use this skill. Include trigger keywords that will auto-invoke the skill.]
license: MIT
version: 1.0.0
allowed-tools: [Optional comma-separated list of tools this skill can use]
---
```

**Guidelines**:
- `name`: kebab-case, matches folder name
- `description`: Clear, actionable trigger keywords (e.g., "Use when debugging bugs...", "Use when creating specifications...")
- `allowed-tools`: Only specify if skill needs restricted tools; omit for full access
- `version`: Semantic versioning (MAJOR.MINOR.PATCH)

---

## Skill Structure

```markdown
# [Skill Name]

## Overview

[2-3 sentences describing what this skill does and when to use it]

**Outcomes**:
- [Expected outcome 1]
- [Expected outcome 2]
- [Expected outcome 3]

---

## Prerequisites

<prerequisites>

[Optional: List global skills, MCP tools, or other dependencies this skill leverages]

**Global Skills** (if applicable):
- [skill-name]: [What knowledge it provides]

**MCP Tools** (if applicable):
- [mcp-tool]: [What it's used for]

**Usage Pattern**:
```
Workflow := reference_prerequisites ∘ execute_workflow ∘ output_results
```

</prerequisites>

---

## Workflow

<workflow>

**Pattern**: [Describe overall workflow pattern using CoD^Σ notation]

### Phase 1: [Phase Name]

**Purpose**: [What this phase accomplishes]

**Steps**:
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Outputs**:
- [Output 1]
- [Output 2]

### Phase 2: [Phase Name]

[Repeat for each phase]

</workflow>

---

## Quality Standards

<quality_standards>

### Token Efficiency
- Target token budget: [X tokens]
- Progressive disclosure levels:
  1. Metadata (this SKILL.md): [X tokens]
  2. Phase docs (if needed): [X tokens each]
  3. Templates: [X tokens each]

### Validation Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

### Success Metrics
- [Metric 1]: [Target value]
- [Metric 2]: [Target value]

</quality_standards>

---

## Anti-Patterns (Do NOT Do)

<anti_patterns>

❌ [Anti-pattern 1 - why it's wrong]
❌ [Anti-pattern 2 - why it's wrong]
❌ [Anti-pattern 3 - why it's wrong]

✅ [Correct pattern 1]
✅ [Correct pattern 2]

</anti_patterns>

---

## Examples

<examples>

### Example 1: [Use Case Name]

**Input**: [What user provides]

**Process**:
```
[CoD^Σ workflow trace]
```

**Output**: [What skill produces]

### Example 2: [Use Case Name]

[Repeat for 2-3 examples showing different use cases]

</examples>

---

## References

<references>

### Related Skills
- [skill-name]: [When to use instead/in combination]

### Documentation
- @docs/[doc-name].md: [What it contains]
- @templates/[template-name].md: [What it's for]

### External Resources
- [Resource name]: [URL or description]

</references>

---

## Implementation Notes

**Progressive Disclosure**:
- This SKILL.md should be ≤ [X] lines
- Complex workflows should reference @docs/[skill-name]/phase-*.md
- Templates should be referenced via @templates/, not inlined

**Token Budget**:
- Skill metadata + core instructions: [X tokens]
- Phase docs (if needed): [X tokens each]
- Total target: ≤ [X tokens]

**Testing**:
- Test that skill auto-invokes based on description keywords
- Validate outputs match quality standards
- Ensure CoD^Σ traces are present and accurate

---

**Remember**: Skills are auto-invoked by Claude Code based on the description field. Make it clear and specific about when to use this skill.

# Agent Template

**Purpose**: Use this template to create new subagents for Claude Code Intelligence Toolkit

**Location**: `.claude/agents/[agent-name].md`

---

## YAML Frontmatter (Required)

```yaml
---
name: [agent-name]
description: [One sentence describing what this agent does and when to invoke it]
model: inherit  # ALWAYS use inherit to match main conversation tier
tools: [comma-separated list of allowed tools]
---
```

**Guidelines**:
- `name`: kebab-case, descriptive of agent's purpose
- `description`: Clear, specific about agent's responsibility
- `model`: ALWAYS set to `inherit` (matches main conversation model tier)
- `tools`: Specify only tools agent needs (principle of least privilege)

**Common Tool Patterns**:
- Research agents: `Read, Glob, Grep, Write, mcp__*`
- Implementation agents: `Read, Write, Edit, Bash, mcp__*`
- QA agents: `Read, Bash, Grep, Glob`
- Documentation agents: `Read, Write, Edit, Grep, Glob`

---

## Agent Structure

```markdown
# [Agent Name]

**Purpose**: [1-2 sentences describing agent's role and responsibilities]

**Token Budget**: ≤ [X] tokens per execution

**Output**: [output-file-name-pattern].md

---

## Core Responsibilities

1. [Responsibility 1]
2. [Responsibility 2]
3. [Responsibility 3]
4. [Responsibility 4]
5. [Responsibility 5]

---

## Prerequisites (Global Skills Reference)

<prerequisites>

[Optional: Reference global skills this agent should leverage]

**Global Skills to Reference**:
- [skill-name]: [What knowledge to use]

**MCP Tools Available**:
- [mcp-tool]: [What it provides]

**Usage Pattern**:
```
Reference_Global_Skills ∘ Execute_Task ∘ Generate_Report
```

</prerequisites>

---

## Workflow (CoD^Σ)

### Phase 1: [Phase Name]

**Purpose**: [What this phase accomplishes]

**Steps**:
1. [Step 1 with CoD^Σ notation if applicable]
2. [Step 2]
3. [Step 3]

**Validation**:
- [Check 1]
- [Check 2]

### Phase 2: [Phase Name]

[Repeat for each phase]

### Phase N: Report Generation

**Report Structure** (≤ [X] tokens):
```markdown
# [Report Title]
**Generated**: [ISO 8601 timestamp]
**Agent**: [agent-name]

---

## Summary (2-3 sentences)
[Key findings or recommendations]

---

## Findings/Results

### Finding 1
[Details]

### Finding 2
[Details]

---

## Recommendations
[Actionable recommendations]

---

## Evidence (CoD^Σ)
[File:line references, MCP query results, traced reasoning]
```

---

## Quality Standards

<quality_standards>

### Token Efficiency
- Report target: ≤ [X] tokens
- Concise summaries: 2-3 sentences max
- Evidence-based claims only

### Evidence Requirements (Constitution Article II)
- All claims MUST have file:line references
- MCP query results MUST be cited
- CoD^Σ traces required for all reasoning

### Validation Checklist
- [ ] Report ≤ [X] tokens
- [ ] All claims have evidence
- [ ] CoD^Σ traces present
- [ ] Actionable recommendations provided
- [ ] Output saved to specified location

</quality_standards>

---

## Anti-Patterns (Do NOT Do)

<anti_patterns>

❌ Reading files without intelligence queries first
❌ Claims without file:line or MCP evidence
❌ Reports exceeding token budget
❌ Bloating main context with research details
❌ Using tools not listed in frontmatter

✅ Query intelligence sources BEFORE reading files
✅ Cite all claims with file:line references
✅ Keep reports concise and actionable
✅ Write report to file, return only summary to main agent

</anti_patterns>

---

## Handover Protocol

<handover>

### Invocation Pattern

**From Main Agent**:
```
Task: [Clear task description]
Output: [Exact file path for report]
Token Budget: [X tokens]
Context: [Minimal context needed]

Dispatch: @.claude/agents/[agent-name].md
```

**From This Agent**:
```
Execution :=
  Parse_Task
    ∘ Reference_Prerequisites
    ∘ Execute_Workflow
    ∘ Generate_Report
    ∘ Write_To_File([output-path])
    ∘ Signal_Completion
```

### Report Delivery

1. Execute task in isolated context
2. Generate concise report (≤ [X] tokens)
3. Write report to specified file path
4. Return only: "Report complete: [file-path]" to main agent
5. Main agent reads report (not full execution context)

</handover>

---

## Success Criteria

<success_criteria>

- [ ] Task completed as specified
- [ ] Report generated within token budget
- [ ] All evidence cited (file:line or MCP sources)
- [ ] CoD^Σ reasoning traces included
- [ ] Output file created at specified location
- [ ] Recommendations are actionable
- [ ] No tool usage outside allowed list
- [ ] No violations of anti-patterns

</success_criteria>

---

## References

<references>

### Related Agents
- [agent-name]: [When to use instead/in combination]

### Skills
- [skill-name]: [What it provides to this agent]

### Templates
- @.claude/templates/[template-name].md: [What it's for]

</references>

---

## Implementation Notes

**Token Management**:
- Agent execution can be verbose (sub-agents have separate context)
- Report MUST be ≤ [X] tokens (what main agent reads)
- Main agent NEVER sees execution details, only final report

**Isolation Benefit**:
- Fresh context for each invocation
- Prevents context pollution in main conversation
- Enables parallel execution of multiple agents

**Testing**:
- Test agent invocation via Task tool
- Validate report structure and token count
- Verify evidence requirements met
- Check output file creation

---

**Remember**: Agents operate in isolated contexts. Keep reports concise - main agent only reads the report file, not the execution details.

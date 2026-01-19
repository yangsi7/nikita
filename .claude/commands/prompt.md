---
description: Best-practice prompt engineering with research-backed patterns - transform, debug, or create production-ready prompts
allowed-tools: Task, Read, Write, Edit, Glob, Grep, WebSearch, mcp__Ref__*, mcp__mcp-server-firecrawl__*
argument-hint: ["prompt text or file path"] [mode: transform|debug|create]
---

# Prompt Engineering

Engineer production-ready prompts using research-backed patterns with mandatory external research.

## Unified Skill Routing

This command invokes the **prompt-engineer skill** at @.claude/skills/prompt-engineer/SKILL.md.

---

## User Input

```text
$ARGUMENTS
```

**Argument Patterns:**

1. **Transform mode** (default): `/prompt "your rough prompt here"`
2. **Debug mode**: `/prompt debug "failing prompt"`
3. **Create mode**: `/prompt create "requirements for new prompt"`
4. **File input**: `/prompt path/to/prompt.md`

---

## Modes

### Transform Mode (Default)

Take a rough, informal prompt and transform it into production-ready format.

**Input:** Rough prompt with informal instructions
**Output:** Optimized prompt with XML structure, examples, constraints

### Debug Mode

Analyze a failing or underperforming prompt, diagnose issues, and fix them.

**Input:** Prompt + description of failures
**Output:** Root cause analysis + fixed prompt

### Create Mode

Generate an optimal prompt from scratch based on requirements.

**Input:** Task requirements, domain context
**Output:** Complete prompt designed for the task

---

## Process Overview

### 1. Mode Detection

Analyze input to determine mode:
- Contains existing prompt → Transform or Debug
- Contains "not working", "failing", "wrong" → Debug
- Requirements without prompt → Create

### 2. Analysis

**Transform:** Identify structure issues, missing sections, vague instructions
**Debug:** Root cause analysis - ambiguity, examples, constraints
**Create:** Requirements extraction, domain identification

### 3. Research (ALWAYS - via Subagent)

**CRITICAL:** Research always runs via subagent to keep main context clean.

Research targets:
- Domain-specific patterns (MCP Ref tool)
- Latest prompt engineering techniques (Firecrawl)
- Similar working prompts (local examples)

```
Task → prompt-researcher subagent
  ↳ mcp__Ref__ref_search_documentation
  ↳ mcp__mcp-server-firecrawl__firecrawl_search
  ↳ Local pattern matching
  ↳ Returns: Condensed findings (~500 tokens)
```

### 4. Design

Select pattern based on task:

| Task Type | Pattern | When to Use |
|-----------|---------|-------------|
| Multi-expert | Meta-Prompting | Need diverse perspectives |
| Tool use | ReAct | External APIs, search |
| Quality-critical | Self-Refine | Iterative improvement |
| Simple task | Direct | Single-step completion |

Apply Claude-specific optimizations:
- XML structure (`<role>`, `<context>`, `<instructions>`)
- Thinking blocks (if reasoning needed)
- Prefill (for format control)

### 5. Validate (via Subagent)

Run parallel validation tests:
- Happy path: Standard use case
- Edge case: Boundary conditions
- Adversarial: Attempts to break prompt
- Format: Output structure compliance

**Target:** ≥80% pass rate

### 6. Iterate

If validation fails:
- Apply self-refine loop (max 3 iterations)
- Address specific failure modes
- Re-validate after each iteration

### 7. Output

Deliver production-ready prompt with:
- Complete structured prompt
- Usage notes
- Test results
- Pattern rationale

---

## Quality Standards

### Structure Requirements

Every production prompt must have:
- [ ] Role definition (who the model is)
- [ ] Context (background information)
- [ ] Instructions (step-by-step process)
- [ ] Format (expected output structure)
- [ ] Examples (1-2 minimum)
- [ ] Constraints (do's and don'ts)

### Claude-Specific Optimizations

- **XML Tags:** Use `<role>`, `<context>`, `<instructions>`, `<format>`, `<examples>`, `<constraints>`
- **Thinking Blocks:** Add `<thinking>` for complex reasoning
- **Prefill:** Start assistant response to guide format
- **Progressive Disclosure:** Load details on-demand

---

## Pattern Library

### Meta-Prompting (Conductor-Expert)

Best for: Multi-perspective analysis, complex decisions
@.claude/skills/prompt-engineer/patterns/meta-prompting.md

### ReAct (Reasoning + Acting)

Best for: Tool use, information gathering, verification loops
@.claude/skills/prompt-engineer/patterns/react-pattern.md

### Self-Refine

Best for: Quality-critical outputs, iterative improvement
@.claude/skills/prompt-engineer/patterns/self-refine.md

---

## Template Library

### System Prompts
@.claude/skills/prompt-engineer/templates/system-prompt.md

### Subagent Prompts
@.claude/skills/prompt-engineer/templates/agent-prompt.md

### Task-Specific Prompts
@.claude/skills/prompt-engineer/templates/task-prompt.md

---

## Workflows Reference

| Workflow | Purpose |
|----------|---------|
| @.claude/skills/prompt-engineer/workflows/analyze.md | Input analysis |
| @.claude/skills/prompt-engineer/workflows/research.md | External research |
| @.claude/skills/prompt-engineer/workflows/design.md | Prompt architecture |
| @.claude/skills/prompt-engineer/workflows/validate.md | Testing |
| @.claude/skills/prompt-engineer/workflows/iterate.md | Refinement |

---

## Examples

### Transform Example

**Input:**
```
/prompt "Write me a blog post about AI"
```

**Output:** Structured prompt with role (tech writer), context (audience, tone), instructions (research, outline, write), format (markdown with headers), examples, and constraints.

### Debug Example

**Input:**
```
/prompt debug "My summarization prompt keeps returning bullet points instead of paragraphs"
```

**Output:** Root cause (format section unclear), fixed prompt with explicit paragraph requirement and anti-pattern example.

### Create Example

**Input:**
```
/prompt create "I need a prompt for code review that catches security issues"
```

**Output:** Complete code review prompt with security focus, OWASP patterns, severity classification, and example findings.

---

## Start Now

Analyze the input and determine mode:

1. **If prompt provided:** Start with analysis (structure, issues, improvements)
2. **If requirements provided:** Start with requirements extraction
3. **Then:** Research → Design → Validate → Output

Always research via subagent before designing the prompt.

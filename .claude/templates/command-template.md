# Command Template

**Purpose**: Use this template to create new slash commands for Claude Code Intelligence Toolkit

**Location**: `.claude/commands/[command-name].md`

---

## YAML Frontmatter (Required)

```yaml
---
description: [One sentence describing what this command does - REQUIRED for SlashCommand tool integration]
allowed-tools: [Optional comma-separated list of tools this command can use]
---
```

**Guidelines**:
- `description`: Required for SlashCommand tool - enables skills to invoke this command
- `allowed-tools`: Specify to restrict tool usage; omit for full access
- File name becomes command (e.g., `analyze.md` → `/analyze`)

**Example**:
```yaml
---
description: Perform intelligence-first code analysis using analyze-code skill to understand bugs, architecture, dependencies, performance, or security concerns
allowed-tools: Task, Read, Bash, Grep, Glob, SlashCommand, mcp__*
---
```

---

## Command Structure

```markdown
# /[command-name] - [Short Description]

**Purpose**: [1-2 sentences describing what this command does]

**Usage**: `/[command-name] [optional-args]`

**When to Use**:
- [Use case 1]
- [Use case 2]
- [Use case 3]

---

## Command Execution

<execution>

### Step 1: [Parse Arguments/Validate Input]

[How to handle command arguments if applicable]

**Arguments**:
- `[arg1]`: [Description, optional/required]
- `[arg2]`: [Description, optional/required]

### Step 2: [Invoke Skill or Execute Workflow]

**Primary Pattern**: Invoke skill via auto-trigger or Task tool

```
Workflow :=
  Parse_Args
    ∘ Validate_Input
    ∘ Invoke_Skill([skill-name])
    ∘ Monitor_Progress
    ∘ Report_Results
```

**Skills Invoked**:
- [skill-name]: [What it does in this workflow]

**Alternative**: Direct execution (if no skill exists)

[Describe workflow steps if not using a skill]

### Step 3: [Output Results]

**Expected Outputs**:
- [Output file 1]: [What it contains]
- [Output file 2]: [What it contains]

</execution>

---

## Workflow Example

<example>

**User Input**:
```
/[command-name] [example-args]
```

**Execution Trace** (CoD^Σ):
```
User_Command
  → Parse_Args([args])
  → Invoke_Skill([skill-name])
    ∘ [skill-phase-1]
    ∘ [skill-phase-2]
    ∘ [skill-phase-3]
  → Generate_Report
  → Present_To_User
```

**Output**:
```
[Example output or report summary]
```

</example>

---

## Integration Patterns

<integration>

### Pattern 1: Skill Auto-Invocation

**Best when**: Skill exists that naturally handles this workflow

```markdown
[command-name] command invoked → Skill auto-triggers based on description match → Workflow executes
```

**Implementation**:
```
1. User types: /[command-name]
2. Command expands to prompt
3. Prompt triggers [skill-name] skill automatically
4. Skill executes workflow
5. Results presented to user
```

### Pattern 2: Direct Skill Invocation via Skill Tool

**Best when**: Need explicit skill invocation control

```markdown
Use Skill tool to invoke [skill-name] skill directly
```

**Implementation**:
```markdown
Execute the [skill-name] skill to [accomplish task].

[Provide context and parameters for skill]
```

### Pattern 3: Agent Delegation via Task Tool

**Best when**: Complex task requiring sub-agent isolation

```markdown
Use Task tool to delegate to [agent-name] agent
```

**Implementation**:
```markdown
Launch the [agent-name] agent with the following task:

Task: [Clear task description]
Output: [File path for results]
Context: [Minimal necessary context]
```

### Pattern 4: Direct Execution

**Best when**: Simple operations not requiring skills/agents

```markdown
Execute [operation] directly using available tools
```

**Implementation**:
[Describe direct workflow steps]

</integration>

---

## Quality Standards

<quality_standards>

### Token Efficiency
- Command file: Keep concise, reference skills for complex workflows
- Avoid duplicating logic that exists in skills

### Usability
- Clear usage instructions
- Helpful examples
- Error handling guidance

### Integration
- Prefer skill invocation over reinventing workflows
- Use Task tool for agent delegation when appropriate
- Reference templates via @ syntax

</quality_standards>

---

## Anti-Patterns (Do NOT Do)

<anti_patterns>

❌ Duplicating entire skill logic in command file
❌ Not specifying description in YAML frontmatter
❌ Executing complex workflows without skills/agents
❌ Missing usage examples
❌ Unclear argument handling

✅ Invoke existing skills to handle workflows
✅ Include clear description for SlashCommand tool
✅ Delegate complex tasks to agents
✅ Provide clear usage examples
✅ Document all arguments and their validation

</anti_patterns>

---

## Invocation Methods

<invocation>

### Method 1: User Types Command

```
User: /[command-name] [args]
→ Command file expands to full prompt
→ Workflow executes
```

### Method 2: Skill Invokes Command (SlashCommand Tool)

```
Skill workflow includes:
SlashCommand(command: "/[command-name] [args]")
→ Command expands and executes
→ Results available to skill
```

**Requirements**:
- description field MUST be present in YAML frontmatter
- SlashCommand tool MUST be in skill's allowed-tools

### Method 3: Agent Invokes Command

```
Agent uses SlashCommand tool:
SlashCommand(command: "/[command-name] [args]")
→ Command expands in agent context
→ Results available to agent
```

</invocation>

---

## Testing

<testing>

### Test Checklist

- [ ] Command file has description in YAML frontmatter
- [ ] Usage examples are clear and accurate
- [ ] Skill invocation works (if applicable)
- [ ] Arguments are parsed and validated correctly
- [ ] Expected outputs are generated
- [ ] Error cases are handled
- [ ] Documentation is complete

### Test Cases

**Test 1: Basic Invocation**
```
Input: /[command-name]
Expected: [Expected behavior]
```

**Test 2: With Arguments**
```
Input: /[command-name] [args]
Expected: [Expected behavior]
```

**Test 3: Error Handling**
```
Input: /[command-name] [invalid-args]
Expected: [Error message or graceful handling]
```

</testing>

---

## Examples

<examples>

### Example 1: Analysis Command

```yaml
---
description: Perform code analysis using analyze-code skill
allowed-tools: Task, Read, Bash, SlashCommand
---

# /analyze - Code Analysis

Invoke the analyze-code skill to perform intelligence-first analysis.

[Additional context and parameters]
```

### Example 2: Planning Command

```yaml
---
description: Create implementation plan from specification
allowed-tools: Task, Read, Write, SlashCommand
---

# /plan - Implementation Planning

Execute the create-implementation-plan skill to generate plan.md from spec.md.

[Workflow details]
```

</examples>

---

## References

<references>

### Related Commands
- /[related-command]: [When to use instead]

### Related Skills
- [skill-name]: [Invoked by this command]

### Related Agents
- [agent-name]: [Delegated to by this command]

### Templates
- @.claude/templates/[template].md: [Used for output]

</references>

---

## Implementation Notes

**Command Expansion**:
- When user types `/[command-name]`, the entire file content expands as the prompt
- Keep commands concise by invoking skills instead of inlining complex logic

**SlashCommand Tool Integration**:
- The `description` field enables skills and agents to invoke this command
- Commands without `description` cannot be invoked programmatically

**Progressive Disclosure**:
- Command file should be high-level
- Complex workflows should live in skills
- Agent delegation for isolated execution

---

**Remember**: Commands are user-facing triggers. They should invoke skills for workflows and delegate to agents for complex isolated tasks. Keep the command file concise and focused.

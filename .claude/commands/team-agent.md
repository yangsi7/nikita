---
description: Orchestrate multi-agent team workflows for complex collaboration tasks
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Task
  - TeamCreate
  - SendMessage
  - TaskCreate
  - TaskUpdate
  - TaskList
  - TeamDelete
  - Skill
  - SlashCommand
argument-hint: "<task-description> [--preset audit|implement|review|research]"
---

# `/team-agent` — Multi-Agent Team Orchestration

Orchestrate persistent agent teams with bidirectional messaging for complex collaboration tasks that require agents to share findings and build on each other's work.

**Arguments**: `$ARGUMENTS`

---

## When to Use Teams vs Subagents

| Criteria | Subagents (Task tool) | Agent Teams (this command) |
|----------|----------------------|---------------------------|
| Communication | One-way (result only) | Bidirectional messaging |
| Lifetime | Single invocation | Persistent until shutdown |
| Cost | 1x | 3-5x more expensive |
| Task list | None | Shared task list |
| Use when | Independent research, validation, analysis | Agents must communicate, debate, review each other's work |

**Default to subagents.** Use teams ONLY when:
- Agents need to share intermediate findings and react to each other
- Work requires iterative review cycles (implement → review → fix → re-review)
- Multi-module changes need coordinated integration testing
- Debate/synthesis across multiple perspectives improves quality

**Do NOT use teams for:**
- SDD phases → use `/feature`, `/plan`, `/implement`, `/audit`
- Simple research → use Explore subagent
- Parallel validation → use parallel Task tool calls (SDD validators)
- Single-file changes → just do it directly

---

## Presets

### `audit` — Spec vs Implementation Analysis
| Role | Agent Type | Purpose |
|------|-----------|---------|
| lead | (you) | Coordinate, synthesize, write report |
| analyzer-1 | code-analyzer | Analyze implementation against spec requirements |
| analyzer-2 | code-analyzer | Analyze test coverage against acceptance criteria |
| synthesizer | general-purpose | Cross-reference findings, identify gaps and conflicts |

**Use for**: Deep audits requiring cross-referencing between spec artifacts and code.

### `implement` — TDD Implementation with Review
| Role | Agent Type | Purpose |
|------|-----------|---------|
| lead | (you) | Coordinate, assign tasks, resolve conflicts |
| planner | Plan | Break down work, identify dependencies |
| implementor | implementor | Write code following TDD cycle |
| reviewer | code-analyzer | Review implementor's code, flag issues |

**Use for**: Complex multi-file features where implementation quality benefits from real-time review.

### `review` — Architecture/Security Review
| Role | Agent Type | Purpose |
|------|-----------|---------|
| lead | (you) | Coordinate, write final review report |
| reviewer-1 | code-analyzer | Architecture patterns, dependency analysis |
| reviewer-2 | code-analyzer | Security analysis, error handling, edge cases |

**Use for**: Pre-merge reviews, security audits, architecture assessments.

### `research` — Multi-Source Research & Synthesis
| Role | Agent Type | Purpose |
|------|-----------|---------|
| lead | (you) | Coordinate, synthesize, write summary |
| explorer-1 | Explore | Codebase exploration (patterns, structure) |
| explorer-2 | Explore | Codebase exploration (dependencies, data flow) |
| researcher | prompt-researcher | External docs, best practices, alternatives |

**Use for**: Understanding unfamiliar codebases, evaluating technology choices, migration planning.

### `auto` — Infer from Task Description
If no preset specified, infer from keywords:
- "audit", "verify", "check spec" → `audit`
- "implement", "build", "create", "add feature" → `implement`
- "review", "security", "architecture" → `review`
- "research", "explore", "understand", "compare" → `research`

---

## Phase 0: Setup

1. **Parse arguments**:
   - Extract task description from `$ARGUMENTS`
   - Detect preset: `--preset <name>` or infer from keywords (see `auto` above)
   - If no task description provided, ask user with AskUserQuestion

2. **Create team**:
   ```
   TeamCreate(
     team_name: "nikita-{preset}-{YYYYMMDD-HHMM}",
     description: "{task description}"
   )
   ```

3. **Create tasks** in the shared task list:
   - Break the task description into 3-6 discrete work items
   - Use TaskCreate for each, with clear subjects and descriptions
   - Set dependencies via TaskUpdate(addBlockedBy) where order matters
   - Example for audit preset:
     ```
     T1: "Analyze spec requirements and extract acceptance criteria" (no deps)
     T2: "Analyze implementation code against spec FRs" (no deps)
     T3: "Analyze test coverage against ACs" (no deps)
     T4: "Cross-reference findings and identify gaps" (blocked by T1, T2, T3)
     T5: "Write unified audit report" (blocked by T4)
     ```

---

## Phase 1: Spawn Teammates (PARALLEL)

Spawn all teammates in a single message with parallel Task tool calls:

```
Task(
  team_name: "nikita-{preset}-...",
  name: "{role-name}",
  subagent_type: "{agent-type}",
  prompt: "You are {role} on team {team_name}. Your job: {role description}.
    Check TaskList for your assigned tasks. When done, mark tasks completed
    via TaskUpdate and send findings to the lead via SendMessage.
    Task context: {task description}",
  mode: "bypassPermissions"
)
```

**Important**:
- Launch ALL teammates in parallel (single message, multiple Task calls)
- Each teammate gets the full task context in their prompt
- Teammates should check TaskList on startup to find their work
- Use `mode: "bypassPermissions"` so teammates can work autonomously

---

## Phase 2: Coordinate

1. **Assign tasks** to teammates:
   ```
   TaskUpdate(taskId: "T1", owner: "analyzer-1")
   TaskUpdate(taskId: "T2", owner: "analyzer-2")
   ```

2. **Monitor progress**:
   - Teammates send messages automatically when they complete tasks
   - These arrive as conversation turns — no polling needed
   - Check TaskList periodically to see overall status

3. **Share context** between teammates when needed:
   ```
   SendMessage(
     type: "message",
     recipient: "synthesizer",
     content: "analyzer-1 found these gaps: {summary}. Factor into your cross-reference.",
     summary: "Sharing analyzer-1 findings"
   )
   ```

4. **Unblock dependencies**:
   - When blocking tasks complete, downstream tasks become available
   - Teammates check TaskList and pick up newly unblocked work
   - Reassign if a teammate is stuck or idle

5. **Handle failures**:
   - If a teammate is unresponsive after 2 messages, note it and redistribute work
   - If a teammate reports being blocked, help unblock or reassign
   - If token budget is a concern, shut down expensive agents early

---

## Phase 3: Aggregate & Cleanup

1. **Collect findings**:
   - Review all teammate messages received during Phase 2
   - Check TaskList to confirm all tasks are completed
   - If tasks remain incomplete, either finish them yourself or note gaps

2. **Synthesize report**:
   - Combine findings into a unified output appropriate for the preset:
     - `audit`: Gap analysis with severity ratings
     - `implement`: Implementation summary with test results
     - `review`: Review report with findings and recommendations
     - `research`: Research summary with key insights and sources
   - Write report to `docs-to-process/{YYYYMMDD}-team-{preset}-{4char-id}.md`

3. **Shutdown teammates**:
   ```
   SendMessage(type: "shutdown_request", recipient: "analyzer-1", content: "Work complete")
   SendMessage(type: "shutdown_request", recipient: "analyzer-2", content: "Work complete")
   SendMessage(type: "shutdown_request", recipient: "synthesizer", content: "Work complete")
   ```
   Wait for shutdown responses before proceeding.

4. **Delete team**:
   ```
   TeamDelete()
   ```

5. **Log event**:
   - Add entry to event-stream.md: `[timestamp] TEAM: {preset} team completed — {summary}`

---

## Error Handling

| Scenario | Action |
|----------|--------|
| TeamCreate fails | Fall back to parallel subagents (Task tool without team_name) |
| Teammate unresponsive | Send 2 follow-up messages, then redistribute work |
| Teammate reports error | Check error, help unblock, or reassign task |
| Token budget exceeded | Shutdown expensive agents, finish remaining work as lead |
| All tasks blocked | Check dependency chain, manually unblock or reassign |
| Shutdown rejected | Send context about why shutdown is needed, retry once |

### Fallback to Subagents

If TeamCreate is unavailable or fails, degrade gracefully:

```
# Instead of team workflow, run parallel subagents:
Task(subagent_type: "code-analyzer", prompt: "Analyze spec requirements...")
Task(subagent_type: "code-analyzer", prompt: "Analyze test coverage...")
Task(subagent_type: "general-purpose", prompt: "Cross-reference findings...")
```

Results won't benefit from bidirectional communication but work completes.

---

## Integration with Existing Commands

| Command | When to Use Instead |
|---------|-------------------|
| `/deep-audit` | Quick spec-vs-code audit (uses subagents, cheaper) |
| `/implement` | Standard TDD implementation (single agent, sufficient for most features) |
| `/audit` | SDD Phase 7 audit (structured, follows SDD workflow) |
| `/analyze` | Single-focus code analysis (one agent is enough) |
| `/e2e-test` | End-to-end testing (specialized MCP tools, not a team task) |
| `/team-agent` | When agents genuinely need to communicate and iterate on each other's work |

---

## Examples

### Audit a spec
```
/team-agent "Audit spec 042 unified pipeline — verify all 45 tasks implemented correctly" --preset audit
```

### Implement with review
```
/team-agent "Implement user settings page with real-time review" --preset implement
```

### Architecture review
```
/team-agent "Review authentication flow for security vulnerabilities" --preset review
```

### Research
```
/team-agent "Research alternatives to Neo4j for temporal knowledge graphs" --preset research
```

### Auto-detect preset
```
/team-agent "Understand how the context engine collects and assembles prompts"
→ Detected: research preset
```

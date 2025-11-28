# Event Stream Log (CoD^Σ)

**Format**: `[YYYY-MM-DD HH:MM:SS] [session-id] EventType - Description`

**Event Types** (CoD^Σ):
```
E := {msg, tool, research, decision, plan, observation, understanding}
msg := User ⇔ Claude
tool := {Read, Write, Edit, Bash, Task, SlashCommand, Skill}
research := docs ∨ external
understanding := system_analysis ∧ entity_mapping
```

**Session ID**: Captured via `.claude/settings.json` hooks (SessionStart event)

---

## Instructions for Use

This file tracks all significant events during development sessions in chronological order. It serves as an audit trail and helps maintain context across sessions.

### When to Log

Log the following events:
- **msg** - User requests and Claude responses (brief summaries)
- **tool** - Tool invocations (Read, Write, Edit, Bash, Task, Skill)
- **research** - Information gathering (docs, MCP queries, web searches)
- **decision** - Key decisions made during development
- **plan** - Planning activities and plan updates
- **observation** - Important discoveries or insights
- **understanding** - System analysis and entity mapping results

### Format Guidelines

Each entry should be:
1. **Timestamped**: `[YYYY-MM-DD HH:MM:SS]`
2. **Session-tagged**: `[session-id]` (from .session-id file)
3. **Event-typed**: One of the event types above
4. **Descriptive**: Brief but clear description of what happened

### Example Entries

```
[2025-10-24 14:30:00] [abc123-session] msg → User requested authentication feature
[2025-10-24 14:31:15] [abc123-session] tool[Skill] → Invoked specify-feature skill
[2025-10-24 14:32:30] [abc123-session] research-docs → Queried project-intel.mjs for auth patterns
[2025-10-24 14:35:00] [abc123-session] understanding → Analyzed auth system (OAuth2, JWT, session types)
[2025-10-24 14:40:00] [abc123-session] decision → Selected JWT-based approach with refresh tokens
[2025-10-24 14:42:00] [abc123-session] plan → Created spec.md, plan.md, tasks.md via SDD workflow
[2025-10-24 14:45:00] [abc123-session] observation → Existing user model needs email_verified field
[2025-10-24 14:50:00] [abc123-session] tool[Write] → Created specs/003-auth-feature/spec.md
```

### CoD^Σ Compressed Format

For complex workflows, use CoD^Σ operators to compress event sequences:

```
[14:30-14:50] tool[Skill] → specify-feature ≫ /plan ≫ generate-tasks ≫ /audit
[14:50-15:20] research → project-intel.mjs ⊕ mcp__ref ⊕ existing_docs
[15:20-16:00] tool[Edit] → ∑(files:5) auth_implementation
```

**Operators**:
- `≫` Transformation pipeline
- `⊕` Parallel composition
- `∑` Aggregation
- `→` Sequential flow

---

## Log Entries

### Session [session-id]: [Brief Description]

```
[YYYY-MM-DD HH:MM:SS] [session-id] msg → [Description]
[YYYY-MM-DD HH:MM:SS] [session-id] tool[ToolName] → [Description]
[YYYY-MM-DD HH:MM:SS] [session-id] research-docs → [Description]
[YYYY-MM-DD HH:MM:SS] [session-id] decision → [Description]
[YYYY-MM-DD HH:MM:SS] [session-id] observation → [Description]
```

---

## Session History

Keep a brief summary of completed sessions:

### Completed Sessions

**Session [session-id-1]** (YYYY-MM-DD):
- Brief summary of what was accomplished
- Key decisions made
- Files created/modified

**Session [session-id-2]** (YYYY-MM-DD):
- Brief summary of what was accomplished
- Key decisions made
- Files created/modified

---

## Notes

- Keep entries concise but informative
- Use CoD^Σ compression for long sequences
- Reference file paths with line numbers when relevant
- Include evidence sources (file:line, MCP queries, etc.)
- Archive old sessions periodically to keep file manageable

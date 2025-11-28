# Project Bootstrap Guide

Quick guide for starting a new project with the Intelligence Toolkit templates.

---

## Quick Start (5 minutes)

### 1. Copy Bootstrap Templates

```bash
# Navigate to your new project directory
cd /path/to/your/new/project

# Copy the four bootstrap templates
cp path/to/skill-builder/.claude/templates/planning-template.md planning.md
cp path/to/skill-builder/.claude/templates/todo-template.md todo.md
cp path/to/skill-builder/.claude/templates/event-stream-template.md event-stream.md
cp path/to/skill-builder/.claude/templates/workbook-template.md workbook.md
```

### 2. Initialize Planning

Open `planning.md` and fill in:
- Project name and overview
- Problem statement
- Core innovation
- Success criteria
- Technology stack

### 3. Create Initial Tasks

Open `todo.md` and:
- Add Phase 1 tasks (setup and foundation)
- Define acceptance criteria for each task
- Mark current task as in-progress

### 4. Start Event Logging

Open `event-stream.md` and:
- Log session start event
- Log key decisions as you make them
- Track tool invocations

### 5. Use Workbook for Active Work

Open `workbook.md` and:
- Note current context
- Track patterns and antipatterns
- Make quick drafts
- Keep under 300 lines

---

## Full Setup (30 minutes)

### Step 1: Clone Intelligence Toolkit

```bash
# Clone the toolkit repository
git clone https://github.com/yangsi7/skill-builder.git toolkit

# Or copy .claude directory to your project
cp -r toolkit/.claude your-project/.claude
```

### Step 2: Copy Project Intelligence Tool

```bash
# Copy project-intel.mjs for intelligence-first queries
cp toolkit/project-intel.mjs your-project/project-intel.mjs
chmod +x your-project/project-intel.mjs
```

### Step 3: Set Up Configuration Files

```bash
# Copy example MCP config
cp toolkit/.mcp.example.json your-project/.mcp.json
# Edit .mcp.json with your MCP server configurations

# Copy .gitignore
cp toolkit/.gitignore your-project/.gitignore

# Copy CLAUDE.md
cp toolkit/CLAUDE.md your-project/CLAUDE.md
# Edit CLAUDE.md to match your project
```

### Step 4: Bootstrap Project Files

```bash
# Copy all four bootstrap templates
cp toolkit/.claude/templates/planning-template.md your-project/planning.md
cp toolkit/.claude/templates/todo-template.md your-project/todo.md
cp toolkit/.claude/templates/event-stream-template.md your-project/event-stream.md
cp toolkit/.claude/templates/workbook-template.md your-project/workbook.md
```

### Step 5: Customize Planning

Edit `planning.md`:

1. **Project Overview**
   - Name your project
   - Describe the problem
   - Define your innovation
   - Set success criteria

2. **Architecture**
   - Map out components (CoD^Σ)
   - Define data flow
   - List dependencies

3. **Technology Stack**
   - Frontend choices
   - Backend choices
   - Infrastructure choices

4. **File Structure**
   - Adapt to your project layout

5. **Phases and Milestones**
   - Define your phases
   - Set milestones
   - Plan deliverables

### Step 6: Create Initial Tasks

Edit `todo.md`:

1. **Phase 1: Foundation**
   - [ ] Set up development environment
   - [ ] Initialize project structure
   - [ ] Configure tools
   - [ ] Create initial documentation

2. **Define Acceptance Criteria**
   - Each task needs ≥ 2 testable ACs
   - Specify how to verify completion

3. **Mark First Task**
   - Set first task to in-progress
   - Begin work

### Step 7: Initialize Event Stream

Edit `event-stream.md`:

```markdown
## Session [your-first-session-id]: Project Bootstrap

[YYYY-MM-DD HH:MM:SS] [session-id] msg → Started new project: [Your Project Name]
[YYYY-MM-DD HH:MM:SS] [session-id] decision → Using Intelligence Toolkit for development
[YYYY-MM-DD HH:MM:SS] [session-id] tool[Write] → Created planning.md, todo.md, workbook.md
```

### Step 8: Set Up Workbook

Edit `workbook.md`:

1. **Current Session Context**
   - Session ID
   - Focus: Project bootstrap
   - Next action: [Your first task]

2. **Key Context**
   - Project state
   - Important decisions
   - Resources needed

3. **Quick Reference**
   - Update with your project specifics

---

## Using the SDD Workflow

Once bootstrap is complete, use the Specification-Driven Development workflow:

### 1. Specify Feature
```bash
/feature "Your feature description"
```

This automatically:
- Creates `specs/###-feature-name/spec.md`
- Runs clarification if needed
- Invokes `/plan` automatically
- Generates tasks via `generate-tasks` skill
- Runs `/audit` for quality validation

### 2. Implement
```bash
/implement specs/###-feature-name/plan.md
```

This automatically:
- Implements each user story (P1, P2, P3...)
- Runs `/verify --story P1` after each story
- Progressive delivery with independent validation

### 3. Verify (if manual check needed)
```bash
/verify plan.md --story P1
```

---

## Intelligence-First Workflow

Always query intelligence BEFORE reading files:

```bash
# 1. Project overview (always first)
project-intel.mjs --overview --json

# 2. Search for relevant files
project-intel.mjs --search "auth" --type tsx --json

# 3. Get symbols from files
project-intel.mjs --symbols src/auth/login.tsx --json

# 4. Trace dependencies
project-intel.mjs --dependencies src/auth/login.tsx --json

# 5. NOW read targeted files
Read src/auth/login.tsx
```

**Token Savings**: 80%+ vs reading files directly

---

## Project Maintenance

### Daily
- [ ] Update `workbook.md` with current context
- [ ] Mark completed tasks in `todo.md`
- [ ] Log key events in `event-stream.md`

### Weekly
- [ ] Review and update `planning.md`
- [ ] Clean up `workbook.md` (keep under 300 lines)
- [ ] Archive completed tasks in `todo.md`
- [ ] Review event stream for insights

### Monthly
- [ ] Review success metrics
- [ ] Update risk management
- [ ] Refine architecture if needed
- [ ] Archive old session content

---

## File Organization

```
your-project/
├── planning.md              # Master plan (bootstrap template)
├── todo.md                  # Task tracking (bootstrap template)
├── event-stream.md          # Event log (bootstrap template)
├── workbook.md              # Active notepad (bootstrap template)
├── CLAUDE.md                # Claude Code guidance
├── .gitignore               # Git exclusions
├── .mcp.json                # MCP server config
├── project-intel.mjs        # Intelligence query tool
├── .claude/                 # Intelligence Toolkit
│   ├── agents/              # Subagents
│   ├── skills/              # Auto-invoked workflows
│   ├── commands/            # Slash commands
│   ├── templates/           # Templates (18 total)
│   ├── shared-imports/      # Core frameworks
│   └── settings.json        # Hooks configuration
├── specs/                   # Feature specifications
│   └── ###-feature-name/
│       ├── spec.md
│       ├── plan.md
│       └── tasks.md
└── docs/                    # Documentation
    ├── architecture/
    ├── guides/
    └── reference/
```

---

## Customization Tips

### Planning.md
- Adapt phases to your project timeline
- Add project-specific sections
- Update technology stack
- Define your own metrics

### Todo.md
- Create custom task templates
- Add project-specific phases
- Define your AC standards

### Event-stream.md
- Use CoD^Σ compression for complex workflows
- Archive old sessions to keep file manageable

### Workbook.md
- **Critical**: Keep under 300 lines
- Archive frequently
- Focus on current work only

---

## Common Workflows

### Starting a New Feature
1. `/feature "description"` (creates spec, plan, tasks)
2. Review generated artifacts
3. `/implement plan.md` (execute with TDD)

### Debugging
1. `/bug` (systematic diagnosis)
2. Implement fix
3. Verify with tests

### Code Analysis
1. `/analyze` (intel-first investigation)
2. Review findings
3. Create tasks for improvements

### Cross-Artifact Validation
1. `/audit [feature-id]` (consistency check)
2. Fix any CRITICAL issues
3. Address WARNINGS
4. Proceed with implementation

---

## Getting Help

### Documentation
- **Templates Guide**: `.claude/templates/README.md`
- **System Overview**: `docs/architecture/system-overview.md`
- **Skills Guide**: `docs/guides/developing-agent-skills.md`
- **Constitution**: `.claude/shared-imports/constitution.md`

### Commands
- `/help` - Claude Code help
- `/agents` - Manage subagents
- `/memory` - Edit CLAUDE.md files

### Intelligence Toolkit
- Use skills for automated workflows
- Use agents for specialized tasks
- Use slash commands for quick access

---

## Success Checklist

After bootstrap, verify:

- [ ] `planning.md` has project overview and architecture
- [ ] `todo.md` has Phase 1 tasks with ACs
- [ ] `event-stream.md` has initial session log
- [ ] `workbook.md` has current context
- [ ] `CLAUDE.md` is customized for your project
- [ ] `.mcp.json` configured with your MCP servers
- [ ] `project-intel.mjs` is executable
- [ ] `.claude/` directory is complete
- [ ] Git repository initialized (if using git)
- [ ] First task is marked in-progress

---

**You're ready to start development with intelligence-first workflows!**

Use `/feature` for your first feature and let the SDD workflow guide you.

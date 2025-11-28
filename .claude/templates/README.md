# Templates Directory

This directory contains structured templates for consistent project documentation and workflow management.

---

## Project Bootstrap Templates

These templates help you quickly set up project management files for a new project:

### 1. event-stream-template.md
**Purpose**: Chronological event logging for audit trails and context preservation

**Use When**: Starting a new project or session that needs event tracking

**Creates**: `event-stream.md` in project root

**Key Features**:
- Timestamped event logging with session IDs
- CoD^Σ compressed format for complex workflows
- Event types: msg, tool, research, decision, plan, observation, understanding
- Session history tracking

**Usage**:
```bash
cp .claude/templates/event-stream-template.md event-stream.md
# Edit to add your first session events
```

### 2. todo-template.md
**Purpose**: Task tracking and progress management

**Use When**: Need to organize and track actionable tasks

**Creates**: `todo.md` in project root

**Key Features**:
- Phase-based task organization
- Acceptance criteria for each task
- Backlog management
- Blocked tasks tracking
- Task templates for different types (feature, bug, research)
- CoD^Σ progress tracking

**Usage**:
```bash
cp .claude/templates/todo-template.md todo.md
# Update with your project tasks
```

### 3. planning-template.md
**Purpose**: Master plan with architecture, components, and roadmap

**Use When**: Starting a new project or major feature

**Creates**: `planning.md` in project root

**Key Features**:
- System architecture (CoD^Σ notation)
- Component breakdown (must-have vs optional)
- Technology stack documentation
- Development workflow (SDD)
- Phases and milestones
- Success metrics
- Risk management
- Decision log

**Usage**:
```bash
cp .claude/templates/planning-template.md planning.md
# Fill in your project details
```

### 4. workbook-template.md
**Purpose**: Personal context-engineered notepad for current session

**Use When**: Need a scratchpad for active development work

**Creates**: `workbook.md` in project root

**Key Features**:
- Current session context
- Chain of drafts for brainstorming
- Antipatterns and effective patterns
- Quick reference (commands, file locations)
- Recent completions tracking
- Upcoming work preview
- **Must stay under 300 lines** (archive old content)

**Usage**:
```bash
cp .claude/templates/workbook-template.md workbook.md
# Use as your active working notepad
```

---

## Feature Specification Templates

### feature-spec.md
**Purpose**: Technology-agnostic feature specification

**Use When**: Starting a new feature or user story

**Key Features**:
- Problem statement and objectives
- User stories with priorities
- Functional requirements
- Success criteria
- CoD^Σ overview (system model, value chain)
- Risk quantification

**Usage**: Automatically used by `specify-feature` skill when running `/feature`

### plan.md
**Purpose**: Implementation plan with tech stack and architecture

**Use When**: After specification is complete and clarified

**Key Features**:
- Technical context and tech stack decisions
- Constitution compliance checks
- Architecture design (CoD^Σ)
- User stories with acceptance criteria
- Dependencies and integration points
- Risks and mitigation strategies
- Verification plan

**Usage**: Automatically used by `create-implementation-plan` skill when running `/plan`

### tasks.md
**Purpose**: User-story-organized task breakdown

**Use When**: After implementation plan is complete

**Key Features**:
- Foundational tasks
- User story phases (P1, P2, P3...)
- Cross-cutting concerns
- Independent test criteria per story
- Constitutional compliance

**Usage**: Automatically used by `generate-tasks` skill when invoked from `/plan`

---

## Workflow and Analysis Templates

### audit-report.md
**Purpose**: Cross-artifact consistency and quality analysis

**Use When**: Before implementation to validate readiness

**Key Features**:
- Constitution compliance check (7 articles)
- Requirement coverage analysis
- Ambiguity detection
- Consistency validation
- Terminology drift detection

**Usage**: Automatically used by `/audit` command

### verification-report.md
**Purpose**: Acceptance criteria verification results

**Use When**: After implementing a user story

**Key Features**:
- Story-level AC verification
- Test execution results
- Independent demo validation
- Dependency checks
- Overall verdict

**Usage**: Automatically used by `/verify` command

### bug-report.md
**Purpose**: Systematic bug diagnosis from symptom to fix

**Use When**: Debugging issues or errors

**Key Features**:
- Symptom description
- Evidence gathering
- Root cause analysis (CoD^Σ)
- Fix recommendation
- Verification steps

**Usage**: Automatically used by `debug-issues` skill when running `/bug`

### analysis-spec.md
**Purpose**: Define scope and objectives for code analysis

**Use When**: Starting a code analysis or investigation

**Key Features**:
- Analysis goals
- Scope definition
- Expected outputs
- Success criteria

**Usage**: Used by `analyze-code` skill when running `/analyze`

### report.md
**Purpose**: Code analysis results with CoD^Σ traces

**Use When**: Reporting code analysis findings

**Key Features**:
- Summary findings
- Detailed analysis
- Evidence (file:line references)
- Recommendations

**Usage**: Generated by `analyze-code` skill

---

## Specialized Templates

### clarification-checklist.md
**Purpose**: Systematic ambiguity scanning and resolution

**Key Features**:
- 10+ ambiguity categories
- CoD^Σ scoring model
- Coverage formula
- Readiness gate

**Usage**: Used by `clarify-specification` skill

### quality-checklist.md
**Purpose**: Pre-implementation quality validation

**Key Features**:
- Content quality checks
- Requirement completeness
- Feature readiness
- Constitutional compliance

**Usage**: Used by `specify-feature` skill

### handover.md
**Purpose**: Agent-to-agent context delegation (600 token limit)

**Key Features**:
- Brief context summary
- Specific request
- Success criteria
- Intelligence queries executed
- Constraints

**Usage**: Used by agents when delegating to other agents

### mcp-query.md
**Purpose**: External knowledge query documentation

**Key Features**:
- Query context
- Tool used
- Results summary
- Evidence extracted

**Usage**: Used when querying MCP tools (Ref, Supabase, etc.)

### data-model-template.md
**Purpose**: Database schema and data model documentation

**Key Features**:
- Entity definitions
- Relationships
- Constraints
- Indexes
- Sample queries

**Usage**: Used by `create-implementation-plan` skill

### research-template.md
**Purpose**: Research findings and recommendations

**Key Features**:
- Research scope
- Findings summary
- Options analysis
- Recommendation with rationale

**Usage**: Used by `create-implementation-plan` skill

---

## Product Definition Templates

### product.md
**Purpose**: User-centric product definition

**Use When**: Defining product strategy and user needs

**Key Features**:
- Problem statement
- User personas
- Pain points
- User journeys
- Success metrics

**Usage**: Used by `define-product` skill

### product-constitution.md
**Purpose**: Technical principles derived FROM user needs

**Use When**: After product.md is complete

**Key Features**:
- Architecture decisions
- Tech stack choices
- Development constraints
- All traced to user needs (CoD^Σ)

**Usage**: Used by `generate-constitution` skill

---

## Template Usage Patterns

### Quick Start Pattern
For new projects, copy these four templates to bootstrap:
```bash
cp .claude/templates/planning-template.md planning.md
cp .claude/templates/todo-template.md todo.md
cp .claude/templates/event-stream-template.md event-stream.md
cp .claude/templates/workbook-template.md workbook.md
```

### SDD Workflow Pattern
The SDD workflow automatically uses these templates:
1. `/feature` → `feature-spec.md`
2. `/plan` (auto) → `plan.md`, `data-model-template.md`, `research-template.md`
3. `/tasks` (auto) → `tasks.md`
4. `/audit` (auto) → `audit-report.md`
5. `/implement` → creates implementations
6. `/verify --story X` (auto) → `verification-report.md`

### Analysis Pattern
For code investigation:
1. `/analyze` → `analysis-spec.md`, `report.md`
2. `/bug` → `bug-report.md`

---

## Template Conventions

### Naming
- **Bootstrap templates**: `*-template.md` (user copies manually)
- **Workflow templates**: `*.md` (used automatically by skills)

### Structure
All templates follow this structure:
1. **Title and metadata**
2. **Instructions for use** (how and when to use)
3. **Template content** (structured sections)
4. **Examples** (where helpful)
5. **Related documents** (cross-references)

### CoD^Σ Integration
Most templates include CoD^Σ notation for:
- System modeling
- Evidence tracing
- Workflow composition
- Progress tracking

---

## Maintenance

### Adding New Templates
1. Create template file in `.claude/templates/`
2. Add YAML frontmatter if used by skills
3. Include usage instructions in template
4. Update this README
5. Consider whether it needs @ import in CLAUDE.md

### Template Evolution
- Templates evolve based on usage patterns
- Keep templates concise and actionable
- Archive old versions when making major changes
- Test templates with real projects before committing

---

## Related Documentation

- **Template System**: @docs/architecture/system-overview.md
- **SDD Workflow**: @.claude/shared-imports/constitution.md (Article IV)
- **Skills Using Templates**: @.claude/skills/*/SKILL.md
- **Commands Using Templates**: @.claude/commands/*.md

---

**Total Templates**: 18
**Bootstrap Templates**: 4 (event-stream, todo, planning, workbook)
**Workflow Templates**: 14 (automated usage)

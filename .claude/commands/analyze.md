---
description: Perform intelligence-first code analysis using analyze-code skill to understand bugs, architecture, dependencies, performance, or security concerns (project)
allowed-tools: Bash(project-intel.mjs:*), Bash(sed:*), Bash(jq:*), Read, Grep, Glob
---

## Pre-Execution

!`project-intel.mjs stats --json > /tmp/project_overview.json`

# Analyze Command - Intelligence-First Code Analysis

You are now executing the `/analyze` command. This command performs comprehensive code analysis using the **intelligence-first approach** to understand bugs, architecture, dependencies, performance issues, or security concerns.

## Your Task

Analyze this codebase or specific issue using the **analyze-code skill** (@.claude/skills/analyze-code/SKILL.md).

## Analysis Modes

The analyze-code skill supports **three specialized modes** optimized for different use cases:

### Mode 1: Overview (General Repository Context)

**Purpose**: Create comprehensive repository map for reference

**When to Use**:
- New to the codebase
- Need general understanding of structure
- Creating documentation
- Onboarding new team members

**Output**: `refs/overview.md` (repository map, component inventory, architecture patterns)

**Token Budget**: ~2K (vs 50K+ reading all files) = **96% savings**

**Example Usage**:
```
User: "I'm new to this project, show me the structure"
Mode: overview (auto-detected)
```

---

### Mode 2: Feature (Specific Domain Context)

**Purpose**: Deep dive into specific feature/domain for development

**When to Use**:
- Understanding how a feature works
- Planning modifications
- Creating feature documentation
- Investigating feature-specific issues

**Output**: `refs/design.md` (feature boundary, dependency graphs, data flow, integration points)

**Token Budget**: ~8K (vs 40K+ reading feature files) = **80% savings**

**Example Usage**:
```
User: "How does the booking system work?"
Mode: feature (auto-detected, target="booking")
```

---

### Mode 3: Architecture (System Structure Analysis)

**Purpose**: Analyze system layers, boundaries, and architectural patterns

**When to Use**:
- Reviewing architecture decisions
- Finding circular dependencies
- Evaluating code organization
- Planning major refactoring

**Output**: `report.md` (layer analysis, boundary violations, coupling metrics, refactoring recommendations)

**Token Budget**: ~5K (vs 30K+ reading system) = **83% savings**

**Example Usage**:
```
User: "Review the architecture for circular dependencies"
Mode: architecture (auto-detected)
```

---

### Mode Selection (Automatic)

**The skill auto-detects mode from your message context:**

| Your Message Contains | Detected Mode | Output |
|----------------------|---------------|---------|
| "codebase", "structure", "overview" | **overview** | refs/overview.md |
| "how does [X] work", specific feature name | **feature** (target=[X]) | refs/design.md |
| "architecture", "layers", "cycles" | **architecture** | report.md |

**Manual Mode Specification** (optional):
```
/analyze mode=overview
/analyze mode=feature target=authentication
/analyze mode=architecture
```

If the mode is ambiguous, the skill will ask you to clarify.

## Process Overview

Follow the analyze-code skill workflow:

1. **Define Scope** (Phase 1)
   - Create @.claude/templates/analysis-spec.md
   - Define objective, scope (in/out), and success criteria
   - Save as: `YYYYMMDD-HHMM-analysis-spec-{id}.md`

2. **Execute Intel Queries** (Phase 2)
   - **CRITICAL:** Query project-intel.mjs BEFORE reading ANY files
   - Use @.claude/shared-imports/project-intel-mjs-guide.md for query syntax
   - Execute all 4 query types:
     - Overview (already done: /tmp/project_overview.json)
     - Search for relevant files
     - Symbol analysis for each file
     - Dependency tracing
   - Save intel results to /tmp/analysis_*.json for evidence

3. **MCP Verification** (Phase 3)
   - Verify findings with authoritative sources
   - Use Ref MCP for library behavior
   - Use Supabase MCP for database schema
   - Document all MCP queries using @.claude/templates/mcp-query.md

4. **Generate Report** (Phase 4)
   - Use @.claude/templates/report.md
   - Include complete CoD^Σ trace with evidence
   - Every claim must have file:line or MCP source
   - Save as: `YYYYMMDD-HHMM-report-{id}.md`

## Intelligence-First Enforcement

**NEVER read full files before intel queries.**

Example workflow:
```bash
# 1. Search for relevant files
project-intel.mjs --search "pattern" --type tsx --json > /tmp/analysis_search.json

# 2. Analyze symbols
project-intel.mjs --symbols src/file.tsx --json > /tmp/analysis_symbols.json

# 3. Trace dependencies
project-intel.mjs --dependencies src/file.tsx --direction upstream --json > /tmp/analysis_deps.json

# 4. NOW read targeted lines only
sed -n '40,60p' src/file.tsx  # Read only 20 lines, not entire file
```

## Token Budget

Your target: **1500-3000 tokens** for complete analysis (vs 15000-30000 without intel-first)

Breakdown:
- Intel queries: ~500 tokens
- MCP verification: ~300 tokens
- Targeted reads: ~500 tokens
- Report generation: ~1500 tokens

## Reasoning Framework

Use **@.claude/shared-imports/CoD_Σ.md** for all reasoning traces.

Every step in your analysis must use CoD^Σ notation:
- `→` for intel queries
- `⇄` for dependency queries
- `⊕` for MCP verification
- `∘` for conclusions

## Expected Outputs

1. **analysis-spec.md** - Scope definition (Phase 1)
2. **report.md** - Final analysis with CoD^Σ trace (Phase 4)
3. *Optional:* **mcp-query.md** - MCP verification results (Phase 3)

## Success Criteria

Before completing, verify:
- [ ] All intel queries executed before file reads
- [ ] Complete CoD^Σ trace documented
- [ ] Every claim has evidence (file:line or MCP)
- [ ] Report uses template structure
- [ ] Token usage 80%+ less than direct reading

## Start Now

Begin by defining the analysis scope using @.claude/templates/analysis-spec.md. If the user hasn't specified what to analyze, ask them:

- What specific issue are you investigating?
- Which components/files should be in scope?
- What does success look like (what question should be answered)?

Then proceed with the analyze-code skill workflow.

---
description: Deep audit specs vs implementation with parallel agents
slash_command: deep-audit
allowed-tools:
  - Bash
    filters:
      - source .venv/bin/activate && python -m pytest
      - git status
      - git log --oneline -5
      - wc -l
      - fd --type f
      - rg --count
  - Read
  - Glob
  - Grep
  - Task
  - Skill
model: claude-sonnet-4-5
argument-hint: "[scope] - Optional scope: 'full' (all specs), 'spec-NNN' (single spec), or feature name"
---

# Deep Audit Command

**Purpose**: Systematically audit specifications against implementation, identify divergence, gaps, and generate remediation plans using intelligence-first parallel agent orchestration.

**Scope**: General-purpose for any codebase with PROJECT_INDEX.json and standard SDD structure.

---

## Arguments

- `$ARGUMENTS` (optional): Audit scope
  - `full` - Audit all specs in specs/ directory
  - `spec-NNN` - Audit single spec (e.g., `spec-039`)
  - `feature-name` - Audit by feature name (e.g., `context-engine`)
  - (empty) - Interactive mode: detect critical areas from PROJECT_INDEX.json

---

## Workflow Overview

```
Phase 0: Intelligence Gathering (PARALLEL)
  ├─> code-analyzer: PROJECT_INDEX analysis
  ├─> tree-of-thought: Architecture understanding
  └─> Explore: Spec coverage detection
       ↓
Phase 1: Multi-Source Verification (PARALLEL)
  ├─> code-analyzer: Spec vs implementation alignment
  ├─> firecrawl-research: Best practices for detected patterns
  ├─> Ref MCP: Latest library docs for dependencies
  └─> Explore: Error logs, test failures, TODO/FIXME
       ↓
Phase 2: Synthesis & Gap Analysis (SEQUENTIAL)
  ├─> tree-of-thought: Synthesize findings → gap report
  └─> Prioritize gaps (P0/P1/P2)
       ↓
Phase 3: Remediation Planning (CONDITIONAL)
  ├─> /feature (if new spec needed)
  ├─> /plan (if existing spec needs update)
  └─> Generate tracking issues
       ↓
Phase 4: Documentation Sync
  └─> /streamline-docs → Consolidate findings
```

---

## Phase 0: Intelligence Gathering (Token Budget: 5-10%)

### Step 0.1: Determine Audit Scope

```bash
# Check for PROJECT_INDEX.json
if [ -f "PROJECT_INDEX.json" ]; then
  echo "✓ PROJECT_INDEX.json found"
else
  echo "✗ PROJECT_INDEX.json missing - run /index first"
  exit 1
fi

# Validate scope argument
SCOPE="$ARGUMENTS"
if [ -z "$SCOPE" ]; then
  SCOPE="interactive"
fi
```

### Step 0.2: Launch Parallel Intelligence Agents (CRITICAL)

**Execute 3 agents concurrently using Task tool:**

**Agent 1: code-analyzer - Project Structure Analysis**
```
Analyze PROJECT_INDEX.json and determine:
1. Total specs in specs/ directory (count + list)
2. Implementation coverage (files per spec)
3. Test coverage (test files per spec)
4. Critical paths (high-dependency modules)
5. Recent changes (git log last 30 days on spec dirs)

Output: JSON summary with:
- total_specs: int
- specs: [{id, name, files_count, test_count, last_modified}]
- critical_modules: [module names with >5 dependencies]
- recent_activity: [{spec, commit_count, days_ago}]
```

**Agent 2: tree-of-thought - Architecture Understanding**
```
Using PROJECT_INDEX.json, build a mental model of:
1. System architecture (layers, boundaries, data flow)
2. Key abstractions (core classes, interfaces, patterns)
3. Integration points (external APIs, databases, message queues)
4. Potential architectural debt (coupling hotspots, circular deps)

Output: Architecture summary with:
- layers: [layer names + responsibilities]
- key_abstractions: [{name, role, dependencies}]
- integration_points: [{service, protocol, criticality}]
- debt_indicators: [{pattern, files, severity}]
```

**Agent 3: Explore - Spec Coverage Detection**
```
Search codebase for:
1. All specs in specs/ directory (fd "spec.md" specs/)
2. Completed specs (grep "Status: Complete" or similar)
3. In-progress specs (grep "Status: In Progress")
4. Orphaned specs (specs with no matching code in src/)
5. Undocumented features (code in src/ with no matching spec)

Output: Coverage report with:
- total_specs: int
- completed: [spec IDs]
- in_progress: [spec IDs]
- orphaned: [spec IDs + reason]
- undocumented: [feature names detected in code]
```

**Wait for all 3 agents to complete before proceeding.**

### Step 0.3: Scope Refinement

Based on agent outputs:

**If $ARGUMENTS is "full":**
- Audit all specs from Agent 3 output

**If $ARGUMENTS is "spec-NNN" or feature name:**
- Validate scope exists in Agent 3 output
- Filter Agent 1/2 outputs to this scope

**If $ARGUMENTS is "interactive":**
- Present findings from all 3 agents
- Recommend audit targets:
  - P0: Specs with >10 files and <50% test coverage
  - P1: Specs modified in last 7 days
  - P2: Specs in "In Progress" status >30 days
- Ask user to confirm scope or select manually

---

## Phase 1: Multi-Source Verification (Token Budget: 10-15%)

**Execute 4 verification streams in PARALLEL using Task tool:**

### Stream 1: Spec-Implementation Alignment (code-analyzer agent)

**For each spec in scope:**
```
Given spec at specs/$SPEC_ID/spec.md, analyze:

1. Requirements Traceability:
   - Extract all requirements (FR-NNN, NFR-NNN) from spec
   - Search codebase for implementation references (grep, rg)
   - Identify implemented vs missing requirements

2. API Contract Validation:
   - Extract API contracts from spec (endpoints, methods, schemas)
   - Find actual implementations (FastAPI routes, GraphQL resolvers)
   - Compare signatures (params, return types, status codes)

3. Data Model Alignment:
   - Extract data models from spec (tables, fields, relationships)
   - Find actual models (ORM classes, migrations, schemas)
   - Compare schemas (field types, constraints, indexes)

4. Test Coverage Validation:
   - Extract acceptance criteria from spec (AC-NNN)
   - Find test files matching spec (test_$feature_*.py)
   - Map tests to ACs (via naming, docstrings, comments)

Output per spec:
{
  "spec_id": "NNN",
  "requirements": {
    "total": int,
    "implemented": [req_ids],
    "missing": [req_ids],
    "diverged": [{req_id, spec_version, code_version, diff}]
  },
  "api_contracts": {
    "total": int,
    "aligned": [endpoint_paths],
    "misaligned": [{path, spec_sig, code_sig, diff}]
  },
  "data_models": {
    "total": int,
    "aligned": [model_names],
    "misaligned": [{model, spec_schema, code_schema, diff}]
  },
  "test_coverage": {
    "total_acs": int,
    "tested_acs": [ac_ids],
    "untested_acs": [ac_ids],
    "coverage_pct": float
  }
}
```

### Stream 2: Best Practices Research (firecrawl-research skill)

**For detected patterns from Phase 0 Agent 2 (architecture understanding):**

```
For each integration point and key abstraction, research:

1. External API Integration Patterns:
   - Search: "{service_name} best practices 2026"
   - Search: "{service_name} production patterns"
   - Limit: 5 results per service
   - Focus: Authentication, rate limiting, error handling, retry logic

2. Architectural Pattern Validation:
   - Search: "{pattern_name} anti-patterns"
   - Search: "{pattern_name} common mistakes"
   - Limit: 3 results per pattern
   - Focus: Coupling, testability, performance, maintainability

3. Technology Stack Currency:
   - Search: "{framework_name} {version} migration guide"
   - Search: "{framework_name} deprecated features"
   - Limit: 3 results per framework
   - Focus: Breaking changes, security advisories, best practices

Output:
{
  "api_integration": [{
    "service": str,
    "best_practices": [str],
    "anti_patterns": [str],
    "sources": [urls]
  }],
  "architecture": [{
    "pattern": str,
    "best_practices": [str],
    "anti_patterns": [str],
    "sources": [urls]
  }],
  "tech_stack": [{
    "framework": str,
    "current_version": str,
    "recommendations": [str],
    "migration_notes": [str],
    "sources": [urls]
  }]
}
```

**CRITICAL**: Use two-step Firecrawl workflow:
1. `firecrawl_search(query, limit=5)` → Get URLs only
2. `firecrawl_scrape(url, formats=["markdown"], onlyMainContent=true)` → Get content from top 2 URLs

**Never use `scrapeOptions` with `firecrawl_search`** (causes token overflow).

### Stream 3: Library Documentation Verification (Ref MCP)

**For each external dependency from PROJECT_INDEX.json:**

```
Query Ref MCP for latest documentation:

1. Critical Dependencies (databases, ORMs, web frameworks):
   - ref_search_documentation("{library_name} {feature} 2026")
   - ref_read_url(top_result_url)
   - Extract: API signatures, breaking changes, deprecations

2. Integration Libraries (payment, auth, email):
   - ref_search_documentation("{library_name} production guide")
   - ref_read_url(top_result_url)
   - Extract: Security best practices, rate limits, error codes

3. Testing Frameworks:
   - ref_search_documentation("{framework_name} fixtures")
   - ref_read_url(top_result_url)
   - Extract: Setup patterns, mocking strategies, async testing

Output per dependency:
{
  "library": str,
  "version_used": str,
  "latest_version": str,
  "api_changes": [{
    "feature": str,
    "old_signature": str,
    "new_signature": str,
    "migration_notes": str
  }],
  "deprecations": [{
    "feature": str,
    "deprecated_in": str,
    "removed_in": str,
    "replacement": str
  }],
  "security_notes": [str],
  "source_url": str
}
```

### Stream 4: Error & Context Gathering (Explore agent)

**Search codebase for issues and alternate approaches:**

```
1. Error Indicators:
   - Search: TODO comments (rg "TODO|FIXME|XXX|HACK" --type py)
   - Search: Logged errors (rg "logger.error|logger.exception" --type py)
   - Search: Exception handling (rg "except.*:" --type py -A 2)
   - Search: Test failures (pytest output if available)

2. Code Smells:
   - Search: Long functions (rg "^def " --type py | count lines >100)
   - Search: High cyclomatic complexity (nested if/for >4 levels)
   - Search: Duplicate code (similar function signatures)
   - Search: Magic numbers (hardcoded constants)

3. Alternate Approaches:
   - Search: Multiple implementations (rg "class.*Client" --type py)
   - Search: Unused code (rg "def " --type py | cross-ref with callers)
   - Search: Deprecated patterns (rg "DEPRECATED|@deprecated")

Output:
{
  "error_indicators": {
    "todos": [{file, line, text}],
    "logged_errors": [{file, line, message}],
    "exception_handlers": [{file, line, exception_type}],
    "test_failures": [{test_name, error, file}]
  },
  "code_smells": {
    "long_functions": [{file, function, lines}],
    "complex_functions": [{file, function, complexity}],
    "duplicates": [{pattern, files}],
    "magic_numbers": [{file, line, value}]
  },
  "alternate_approaches": {
    "multiple_impls": [{pattern, files, recommendation}],
    "unused_code": [{file, function, reason}],
    "deprecated": [{file, line, replacement}]
  }
}
```

**Wait for all 4 streams to complete before proceeding.**

---

## Phase 2: Synthesis & Gap Analysis (Token Budget: 5-10%)

### Step 2.1: Launch tree-of-thought Synthesis Agent

**Provide ALL outputs from Phase 1 (4 streams) as context:**

```
You are synthesizing audit findings from 4 verification streams:
1. Spec-Implementation Alignment (code-analyzer output)
2. Best Practices Research (firecrawl-research output)
3. Library Documentation (Ref MCP output)
4. Error & Context (Explore output)

Task: Create a comprehensive gap analysis report with:

1. **Critical Gaps (P0)** - Production blockers:
   - Missing requirements (from Stream 1)
   - API contract violations (from Stream 1)
   - Security issues (from Stream 2 + 3)
   - Data corruption risks (from Stream 1 + 4)

2. **Important Gaps (P1)** - Quality issues:
   - Test coverage gaps (from Stream 1)
   - Code smells (from Stream 4)
   - Architectural debt (from Phase 0 Agent 2 + Stream 2)
   - Deprecated API usage (from Stream 3)

3. **Optional Improvements (P2)** - Nice-to-haves:
   - Performance optimizations (from Stream 2 + 4)
   - Code cleanup (from Stream 4)
   - Documentation updates (from Stream 1)

4. **Divergence Analysis**:
   - Specs ahead of implementation (requirements in spec, not in code)
   - Implementation ahead of specs (features in code, not in spec)
   - Conflicting information (spec says X, code does Y)

5. **Recommended Actions**:
   - Immediate fixes (P0 gaps)
   - Short-term improvements (P1 gaps)
   - Long-term refactors (P2 gaps)
   - Spec updates needed (divergence)

Output format: Structured markdown with:
- Executive summary (5 bullet points)
- Gap tables (Priority | Gap | Evidence | Recommendation)
- Traceability matrix (Spec → Code → Tests)
- Action plan (prioritized tasks with effort estimates)
```

**Wait for synthesis agent to complete.**

### Step 2.2: Generate Gap Report Artifact

Create `docs-to-process/{YYYYMMDD}-audit-{scope}-{4char}.md` with tree-of-thought output.

**Format:**
```markdown
# Deep Audit Report: {scope}
**Date**: {YYYY-MM-DD}
**Scope**: {full|spec-NNN|feature-name}
**Auditor**: Claude Code + Deep Audit Command

## Executive Summary
- {5 key findings}

## Critical Gaps (P0) - {count}
| ID | Gap | Evidence | Recommendation | Effort |
|----|-----|----------|----------------|--------|
| P0-1 | ... | file:line | ... | {hours} |

## Important Gaps (P1) - {count}
| ID | Gap | Evidence | Recommendation | Effort |
|----|-----|----------|----------------|--------|
| P1-1 | ... | file:line | ... | {hours} |

## Optional Improvements (P2) - {count}
{list}

## Divergence Analysis
### Specs Ahead of Implementation
{table}

### Implementation Ahead of Specs
{table}

### Conflicting Information
{table}

## Traceability Matrix
| Spec | Requirement | Implementation | Tests | Status |
|------|-------------|----------------|-------|--------|
| {id} | {FR-NNN} | {file:line} | {test file} | {✓|✗|⚠️} |

## Action Plan
### Immediate (P0) - Est. {hours}h
- [ ] {task 1}
- [ ] {task 2}

### Short-term (P1) - Est. {hours}h
- [ ] {task 1}

### Long-term (P2) - Est. {hours}h
- [ ] {task 1}

## Appendices
### A. Best Practices Summary
{from Stream 2}

### B. Library Updates Needed
{from Stream 3}

### C. Code Smells Inventory
{from Stream 4}
```

---

## Phase 3: Remediation Planning (Token Budget: 10-15%)

### Step 3.1: Generate Specs for Missing Features

**For each "Implementation Ahead of Specs" item from Phase 2:**

```bash
# Invoke /feature for undocumented features
# Example: If audit found "payment processing" code without spec

# Prompt SDD skill to create retroactive spec
echo "Invoking SDD skill to generate spec for: {feature_name}"
```

**Use Skill tool:**
```
Skill: sdd
Args: "feature {feature_name} - Retroactive specification for existing implementation"
```

**This will auto-chain:**
- Phase 3: Create specs/{NNN}-{feature}/spec.md
- Phase 5: Create plan.md + research.md
- Phase 6: Create tasks.md
- Phase 7: Audit → PASS (implementation already exists)

### Step 3.2: Generate Plans for Incomplete Specs

**For each "Specs Ahead of Implementation" item from Phase 2:**

```bash
# Check if spec has plan.md
if [ ! -f "specs/$SPEC_ID/plan.md" ]; then
  echo "Invoking /plan for spec $SPEC_ID"
fi
```

**Use Skill tool:**
```
Skill: sdd
Args: "plan specs/{spec_id}/spec.md"
```

**This will auto-chain:**
- Phase 5: Create/update plan.md
- Phase 6: Create/update tasks.md
- Phase 7: Audit → ready for /implement

### Step 3.3: Create GitHub Issues for Quick Wins

**For P0 and P1 gaps with <4h effort estimates:**

```markdown
# Issue Template (create via GitHub CLI or manual)

Title: [AUDIT-{ID}] {gap description}
Labels: audit, priority-{p0|p1}, effort-{small|medium}

## Gap Description
{from Phase 2 gap table}

## Evidence
- File: {file path}
- Line: {line number}
- Context: {code snippet or spec excerpt}

## Recommendation
{from Phase 2 gap table}

## Acceptance Criteria
- [ ] {derived from recommendation}
- [ ] Tests pass
- [ ] Documentation updated

## Effort Estimate
{hours} hours

## Related Spec
specs/{spec_id}/spec.md (if applicable)
```

### Step 3.4: Update Master Todo

**Add audit findings to todos/master-todo.md:**

```markdown
## Deep Audit Findings ({date})

### P0 - Critical ({count})
- [ ] [AUDIT-P0-1] {gap} (Est: {h}h) - Issue #{num}
- [ ] [AUDIT-P0-2] {gap} (Est: {h}h) - Issue #{num}

### P1 - Important ({count})
- [ ] [AUDIT-P1-1] {gap} (Est: {h}h) - Issue #{num}

### Specs to Generate ({count})
- [ ] Spec for {feature_name} (retroactive)

### Plans to Update ({count})
- [ ] Update plan for spec-{NNN}
```

---

## Phase 4: Documentation Sync (Token Budget: 5%)

### Step 4.1: Consolidate Audit Artifacts

**Use Skill tool to invoke streamline-docs:**

```
Skill: streamline-docs
```

**This will:**
1. Scan docs-to-process/ for audit reports
2. Extract high-impact findings → CLAUDE.md
3. Update docs/decisions/ with architecture decisions
4. Update docs/patterns/ with detected patterns
5. Log changes in docs/CHANGELOG.md
6. Delete processed files from docs-to-process/

### Step 4.2: Update Project State Files

**If significant changes detected:**

```bash
# Update event-stream.md
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] AUDIT_COMPLETE: Deep audit found {p0_count} P0, {p1_count} P1 gaps - {spec_count} specs need updates" >> event-stream.md

# Update workbook.md
cat >> workbook.md << EOF

## Deep Audit Session: $(date +%Y-%m-%d)

**Scope**: {scope}
**Gaps Found**: {p0_count} P0, {p1_count} P1, {p2_count} P2

**Critical Actions**:
- {P0 item 1}
- {P0 item 2}

**Next Steps**:
- {action from Phase 3}
EOF

# Prune if exceeding limits
wc -l event-stream.md workbook.md
```

---

## Quality Gates

**Phase 0 Gate**: All 3 intelligence agents must complete successfully
- If any agent fails → STOP and diagnose
- Required outputs: Project structure, architecture model, spec coverage

**Phase 1 Gate**: All 4 verification streams must complete
- Stream 1 (alignment): ≥1 spec analyzed
- Stream 2 (research): ≥1 best practice found
- Stream 3 (docs): ≥1 library checked
- Stream 4 (errors): ≥1 context type gathered

**Phase 2 Gate**: Synthesis agent produces valid gap report
- Must have ≥1 gap identified (any priority)
- Must have traceability matrix
- Must have action plan

**Phase 3 Gate**: Remediation artifacts created
- If specs missing → /feature invoked
- If plans missing → /plan invoked
- If issues needed → GitHub issues created
- todos/master-todo.md updated

---

## Output Summary

**Console Output:**
```
🔍 Deep Audit Complete - {scope}

📊 Findings:
- P0 Critical: {count} gaps
- P1 Important: {count} gaps
- P2 Optional: {count} improvements

📄 Artifacts Generated:
- Gap Report: docs-to-process/{timestamp}-audit-{scope}.md
- Specs Created: {count}
- Plans Updated: {count}
- GitHub Issues: {count}

📋 Next Steps:
1. Review gap report in docs-to-process/
2. Address P0 items immediately
3. Run /implement for specs with updated plans
4. Track progress in todos/master-todo.md

🔗 Traceability: {covered_specs}/{total_specs} specs verified
```

---

## Error Handling

**PROJECT_INDEX.json missing:**
```
ERROR: PROJECT_INDEX.json not found
SOLUTION: Run /index to generate project intelligence
```

**No specs/ directory:**
```
WARNING: No specs/ directory found
SOLUTION: This project may not use SDD - audit limited to code analysis
FALLBACK: Run Phase 0-1 only, skip Phase 3 (SDD remediation)
```

**Agent failures:**
```
ERROR: {agent_name} failed with {error}
SOLUTION:
- Check agent logs in ~/.claude/agents/logs/
- Verify agent has necessary tools (Bash, Read, Glob)
- Retry with reduced scope (single spec vs full)
```

**Token overflow:**
```
ERROR: Context window exceeded in Phase 1 Stream 2
SOLUTION:
- Reduce firecrawl result limit (5 → 3)
- Use more targeted search queries
- Skip Stream 2 and rely on Ref MCP (Stream 3)
```

---

## Token Budget Allocation

| Phase | Budget | Usage Pattern |
|-------|--------|---------------|
| Phase 0 | 5-10% | Parallel agents (intelligence gathering) |
| Phase 1 | 10-15% | Parallel agents (verification streams) |
| Phase 2 | 5-10% | Single agent (synthesis) |
| Phase 3 | 10-15% | Skill invocations (SDD, GitHub) |
| Phase 4 | 5% | Skill invocation (streamline-docs) |
| **Total** | **35-55%** | Leaves 45-65% for user interaction |

**Efficiency Strategies:**
- Progressive disclosure: Load details on-demand
- Parallel execution: Never run agents sequentially unless dependent
- Intelligence-first: Query PROJECT_INDEX.json before reading files
- Agent delegation: ALL token-heavy tasks to subagents

---

## Usage Examples

**Example 1: Full Audit**
```bash
/deep-audit full
# Audits all specs in specs/ directory
# Typical runtime: 10-20 minutes
# Expected output: 50-200 findings depending on project size
```

**Example 2: Single Spec Audit**
```bash
/deep-audit spec-039
# Audits only specs/039-unified-context-engine/
# Typical runtime: 3-5 minutes
# Expected output: 10-30 findings for one feature
```

**Example 3: Feature Audit**
```bash
/deep-audit context-engine
# Searches for specs matching "context-engine"
# Audits all matching specs
# Typical runtime: 5-10 minutes
```

**Example 4: Interactive Mode**
```bash
/deep-audit
# Analyzes PROJECT_INDEX.json
# Recommends audit targets based on heuristics
# User selects scope
# Proceeds with selected scope
```

---

## Integration with Other Commands

**Typical Workflow:**

1. `/index` - Generate PROJECT_INDEX.json (prerequisite)
2. `/deep-audit full` - Comprehensive audit
3. Review gap report in docs-to-process/
4. `/implement specs/{NNN}/plan.md` - Address gaps for specific specs
5. `/e2e-test` - Verify fixes
6. `/deep-audit spec-{NNN}` - Re-audit to confirm gaps closed

**SDD Integration:**

- Deep audit GENERATES specs for undocumented features
- Deep audit UPDATES plans for incomplete specs
- Use /implement after audit completes Phase 3
- Audit findings feed into todos/master-todo.md

---

## Best Practices

1. **Run audit before major refactors** - Understand current state first
2. **Audit after onboarding to new project** - Build mental model via agents
3. **Schedule regular audits** - Monthly full audit, weekly single-spec audits
4. **Address P0 gaps immediately** - Don't let critical issues accumulate
5. **Use audit findings for sprint planning** - Gap report drives priorities
6. **Re-audit after implementations** - Verify gaps closed
7. **Track audit trends** - Compare gap counts over time (improving vs degrading)

---

## Troubleshooting

**High P0 count (>20):**
- Project may have significant spec drift
- Consider freezing new features until P0s addressed
- Break into smaller audit scopes (per-module vs full project)

**Low gap count (<5) but known issues:**
- Specs may be incomplete (requirements not detailed enough)
- Consider running /feature with more detailed requirements
- Verify acceptance criteria are specific and testable

**Audit taking >30 minutes:**
- Reduce scope (full → per-module)
- Check for token overflow in Phase 1 (reduce research depth)
- Verify agents are running in parallel (not sequential)

**Conflicting recommendations:**
- Review sources (best practices vs library docs)
- Prioritize library docs (authoritative)
- Note conflicts in gap report for user decision

---

## Maintenance

**Command Updates:**

This command should be updated when:
- New agent types added to toolkit
- New MCP tools available (e.g., better doc search)
- SDD workflow phases change
- New quality gates defined in project

**Version History:**
- v1.0.0 (2026-01-30): Initial release - parallel agent orchestration, 4-phase workflow

---

## References

- Intelligence-First Workflow: `.claude/shared-imports/project-intel-mjs-guide.md`
- SDD Unified Skill: `.claude/skills/sdd/SKILL.md`
- Agent Coordination: `.claude/CLAUDE.md` (Agent section)
- Firecrawl Best Practices: Project CLAUDE.md (Rule #11)
- Parallel Agent Patterns: Project CLAUDE.md (Rule #13)

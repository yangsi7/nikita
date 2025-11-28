---
description: Create detailed implementation plan from specification using create-implementation-plan skill with intelligence-first dependency analysis (project)
allowed-tools: Bash(project-intel.mjs:*), Bash(test:*), Bash(jq:*), Read, Grep, Write
argument-hint: <spec-file>
---

## Pre-Execution

<!-- Bash pre-validation removed - $1 not available in !`` context. Claude will validate file existence when reading. -->

# Plan Command - Create Implementation Plan from Specification

You are now executing the `/plan <spec-file>` command. This command creates a detailed implementation plan from a feature specification or bug report using the **create-implementation-plan skill**.

## Your Task

Create a comprehensive implementation plan from the provided specification using the **create-implementation-plan skill** (@.claude/skills/create-implementation-plan/SKILL.md).

**Input Spec:** `$1` (validated to exist)

## Process Overview

Follow the create-plan skill workflow:

1. **Load Input Spec** (Phase 1)
   - Read the provided spec file: `$1`
   - Extract all requirements (REQ-001, REQ-002, etc.)
   - Identify constraints and success criteria
   - If spec uses @.claude/templates/feature-spec.md ✓
   - If spec is informal, extract requirements anyway

2. **Task Breakdown** (Phase 2)
   - Break each requirement into granular tasks (2-8 hours each)
   - **CRITICAL:** Every task MUST have minimum 2 testable ACs
   - Use @.claude/shared-imports/CoD_Σ.md for breakdown reasoning
   - Group by layer: Database → Backend → Frontend → Testing
   - Example task structure:
     ```markdown
     ### Task 1: Add OAuth Database Schema
     - **ID:** T1
     - **Owner:** executor-agent
     - **Estimated:** 2 hours
     - **Dependencies:** None

     **Acceptance Criteria:**
     - [ ] AC1: users table has google_id VARCHAR(255) column
     - [ ] AC2: Migration runs without errors
     - [ ] AC3: google_id is nullable (existing users don't have it)
     ```

3. **Identify Dependencies** (Phase 3)
   - Use project-intel.mjs to find file dependencies
   - Use @.claude/shared-imports/project-intel-mjs-guide.md for query syntax
   - Map task dependencies (which tasks depend on others)
   - Identify parallel vs sequential tasks
   - Create dependency graph
   - Example queries:
     ```bash
     # Find existing files that will be modified
     project-intel.mjs --search "auth|session" --json

     # Check what depends on files we'll modify
     project-intel.mjs --dependencies src/auth/session.ts --direction downstream --json
     ```

4. **Validate Plan** (Phase 4)
   - Verify 100% requirement coverage (every REQ → tasks)
   - Verify all tasks have 2+ ACs
   - Verify no circular dependencies
   - Generate @.claude/templates/plan.md
   - Save as: `YYYYMMDD-HHMM-plan-{id}.md`

## Templates Reference

**Input Templates:**
- @.claude/templates/feature-spec.md - Feature specifications
- @.claude/templates/bug-report.md - Bug reports (alternative input)

**Output Templates:**
- @.claude/templates/plan.md - Implementation plans (required)

## Enforcement Rules

### Rule 1: Minimum 2 ACs Per Task

**❌ Violation:**
```markdown
Task: Add login button
ACs:
- Button exists
```

**✓ Correct:**
```markdown
Task: Add login button
ACs:
- AC1: Button renders with "Log in with Google" text
- AC2: Button click triggers OAuth redirect to Google
- AC3: Button shows loading state during authentication
```

### Rule 2: All Requirements → Tasks

**❌ Violation:**
```markdown
Requirements: REQ-001, REQ-002, REQ-003
Tasks: T1 (REQ-001), T2 (REQ-001)
# Missing REQ-002 and REQ-003!
```

**✓ Correct:**
```markdown
Requirements: REQ-001, REQ-002, REQ-003
Tasks:
- T1, T2 (REQ-001)
- T3, T4 (REQ-002)
- T5 (REQ-003)
Coverage: 100% ✓
```

### Rule 3: Testable ACs

ACs must be:
- Objectively verifiable (pass/fail clear)
- Specific (not "works" or "is good")
- Implementable (actionable)

## Task Sizing

**Ideal:** 2-8 hours per task

**Too large:** "Implement authentication system" → Break down!
**Just right:** "Add google_id column to users table" ✓

## CoD^Σ Reasoning

Use @.claude/shared-imports/CoD_Σ.md for planning reasoning:

```
Step 1: → LoadSpec
  ↳ Source: feature-spec-oauth.md
  ↳ Requirements: 3

Step 2: ∘ BreakdownTasks
  ↳ REQ-001 → T1 (DB), T2 (OAuth), T3 (UI)
  ↳ REQ-002 → T4 (Session)

Step 3: ⇄ IntelQuery("dependencies")
  ↳ Query: project-intel.mjs --search "auth"
  ↳ Data: Existing auth system found

Step 4: → DefineACs
  ↳ T1: 3 ACs (schema, migration, nullable)
  ↳ T2: 2 ACs (redirect, validation)

Step 5: ∘ Validate
  ↳ Coverage: 100% ✓
  ↳ All tasks: 2+ ACs ✓
```

## Expected Output

**Generated file:** `YYYYMMDD-HHMM-plan-{id}.md`

Must include:
1. **Goal** - High-level objective
2. **Tasks** - Each with ID, owner, ACs, dependencies
3. **Dependency Graph** - Visual representation
4. **Risks** - Potential blockers
5. **Verification** - How to verify completion

## Success Criteria

Before completing, verify:
- [ ] All requirements from spec are covered by tasks
- [ ] Every task has minimum 2 testable ACs
- [ ] Dependencies identified via project-intel.mjs
- [ ] No circular dependencies
- [ ] Tasks sized to 2-8 hours
- [ ] Plan uses template structure
- [ ] File saved with correct naming

## Start Now

Read the spec file: `$1`

Then proceed with the create-plan skill workflow to generate a comprehensive implementation plan.

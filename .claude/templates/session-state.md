---
description: "Template for session state and hook JSON output format"
---

# Session State Template

**Purpose**: Standard JSON format for hook outputs, particularly SessionStart hook

---

## SessionStart Hook Output

Hooks should output JSON to stdout for Claude Code to consume.

### Format

```json
{
  "feature": "###-feature-name",
  "directory": "specs/###-feature-name",
  "artifacts": {
    "spec": {
      "exists": boolean,
      "path": "specs/###-feature-name/spec.md",
      "size_kb": number,
      "last_modified": "YYYY-MM-DDTHH:MM:SSZ"
    },
    "plan": {
      "exists": boolean,
      "path": "specs/###-feature-name/plan.md",
      "size_kb": number,
      "last_modified": "YYYY-MM-DDTHH:MM:SSZ"
    },
    "tasks": {
      "exists": boolean,
      "path": "specs/###-feature-name/tasks.md",
      "size_kb": number,
      "last_modified": "YYYY-MM-DDTHH:MM:SSZ"
    },
    "audit": {
      "exists": boolean,
      "path": "docs/sessions/[session-id]/audit/[timestamp]-audit-###-feature-name.md",
      "quality_score": number,
      "implementation_ready": boolean
    }
  },
  "workflow_state": "needs_spec|needs_plan|needs_tasks|needs_audit|ready_for_implementation|in_progress|complete",
  "next_action": "Description of recommended next step",
  "session_id": "session-id-from-hook",
  "git_branch": "###-feature-name",
  "warnings": [
    "Warning message 1",
    "Warning message 2"
  ]
}
```

### Workflow States

| State | Meaning | Next Action |
|-------|---------|-------------|
| `needs_spec` | No spec.md exists | Run `/feature` or specify-feature skill |
| `needs_plan` | spec.md exists, no plan.md | Run `/plan` or create-implementation-plan skill |
| `needs_tasks` | plan.md exists, no tasks.md | Run generate-tasks skill |
| `needs_audit` | tasks.md exists, no audit report | Run `/audit` command |
| `ready_for_implementation` | Audit passed, ready to code | Run `/implement` command |
| `in_progress` | Implementation started but not complete | Continue with `/implement` or `/verify` |
| `complete` | All user stories verified and complete | Feature done! |

---

## Workflow State Reasoning (CoD^Σ)
<!-- Document how workflow state is determined through composition of checks -->

**State Determination Pipeline:**
```
Step 1: → FeatureDetection
  ↳ Source: git branch OR environment variable
  ↳ Pattern: ###-feature-name
  ↳ Result: [feature-id or null]

Step 2: ∥ ArtifactChecks
  ↳ Check: spec.md exists?
  ↳ Check: plan.md exists?
  ↳ Check: tasks.md exists?
  ↳ Check: audit report exists?
  ↳ Result: [artifact_status_map]

Step 3: ∘ StateComputation
  ↳ Logic: if !spec → "needs_spec"
  ↳ Logic: else if !plan → "needs_plan"
  ↳ Logic: else if !tasks → "needs_tasks"
  ↳ Logic: else if !audit → "needs_audit"
  ↳ Logic: else → "ready_for_implementation"
  ↳ Result: [computed_state]

Step 4: → NextActionMapping
  ↳ Input: [computed_state]
  ↳ Mapping: state → recommended_action
  ↳ Output: [actionable_guidance]
```

**Composition Formula:**
```
FeatureDetection ≫ ArtifactChecks ∥ [spec, plan, tasks, audit] ∘ StateComputation → NextAction
```

**Decision Flow:**
```
spec.md?
├─ NO  → needs_spec ─→ "Run /feature"
└─ YES → plan.md?
    ├─ NO  → needs_plan ─→ "Run /plan"
    └─ YES → tasks.md?
        ├─ NO  → needs_tasks ─→ "Auto-invoked after /plan"
        └─ YES → audit?
            ├─ NO  → needs_audit ─→ "Run /audit"
            └─ YES → ready_for_implementation ─→ "Run /implement"
```

---

### Example Output

```json
{
  "feature": "001-user-authentication",
  "directory": "specs/001-user-authentication",
  "artifacts": {
    "spec": {
      "exists": true,
      "path": "specs/001-user-authentication/spec.md",
      "size_kb": 12.4,
      "last_modified": "2025-10-22T10:30:00Z"
    },
    "plan": {
      "exists": true,
      "path": "specs/001-user-authentication/plan.md",
      "size_kb": 25.8,
      "last_modified": "2025-10-22T11:15:00Z"
    },
    "tasks": {
      "exists": true,
      "path": "specs/001-user-authentication/tasks.md",
      "size_kb": 18.2,
      "last_modified": "2025-10-22T11:45:00Z"
    },
    "audit": {
      "exists": true,
      "path": "docs/sessions/20251022-session/audit/20251022-1200-audit-001-user-authentication.md",
      "quality_score": 8.5,
      "implementation_ready": true
    }
  },
  "workflow_state": "ready_for_implementation",
  "next_action": "All quality gates passed. Run `/implement specs/001-user-authentication/plan.md` to begin implementation.",
  "session_id": "20251022-session",
  "git_branch": "001-user-authentication",
  "warnings": []
}
```

---

## PreToolUse Hook Output

### Blocking Example (Exit Code 2)

```json
{
  "decision": "block",
  "reason": "Cannot create plan.md without spec.md. Article IV: Specification-First Development requires spec.md to exist first.",
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Workflow order violation"
  }
}
```

### Allowing Example (Exit Code 0)

```json
{
  "decision": "allow",
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "Spec exists, proceeding with plan creation."
  }
}
```

---

## PostToolUse Hook Output

### Providing Feedback

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "File created successfully. Code formatted with Prettier."
  }
}
```

### Blocking Further Execution

```json
{
  "decision": "block",
  "reason": "Linting failed. Fix errors before continuing.",
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "Found 3 linting errors in file.ts:12, file.ts:45, file.ts:67"
  }
}
```

---

## UserPromptSubmit Hook Output

### Adding Context

```json
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "Current time: 2025-10-22 14:30:00 UTC\nCurrent feature: 001-user-authentication\nWorkflow state: ready_for_implementation"
  }
}
```

### Blocking Prompt

```json
{
  "decision": "block",
  "reason": "Detected potential secrets in prompt. Remove sensitive data before proceeding."
}
```

---

## Common Patterns

### Feature Detection

```bash
# From git branch
BRANCH=$(git branch --show-current)
FEATURE=$(echo "$BRANCH" | grep -oE '^[0-9]{3}-[a-z0-9-]+')

# Or from environment variable
FEATURE="${SPECIFY_FEATURE:-}"

# Output
echo "{\"feature\": \"$FEATURE\"}"
```

### Artifact Existence Check

```bash
FEATURE_DIR="specs/$FEATURE"
SPEC_EXISTS=false
PLAN_EXISTS=false
TASKS_EXISTS=false

[[ -f "$FEATURE_DIR/spec.md" ]] && SPEC_EXISTS=true
[[ -f "$FEATURE_DIR/plan.md" ]] && PLAN_EXISTS=true
[[ -f "$FEATURE_DIR/tasks.md" ]] && TASKS_EXISTS=true

# Output
cat <<EOF
{
  "artifacts": {
    "spec": {"exists": $SPEC_EXISTS},
    "plan": {"exists": $PLAN_EXISTS},
    "tasks": {"exists": $TASKS_EXISTS}
  }
}
EOF
```

### Workflow State Determination

```bash
if [[ "$SPEC_EXISTS" == "false" ]]; then
  STATE="needs_spec"
  NEXT_ACTION="Create specification with specify-feature skill or /feature command"
elif [[ "$PLAN_EXISTS" == "false" ]]; then
  STATE="needs_plan"
  NEXT_ACTION="Create implementation plan with /plan command"
elif [[ "$TASKS_EXISTS" == "false" ]]; then
  STATE="needs_tasks"
  NEXT_ACTION="Generate tasks with generate-tasks skill"
else
  STATE="ready_for_implementation"
  NEXT_ACTION="Run /audit to verify consistency, then /implement to begin coding"
fi

# Output
echo "{\"workflow_state\": \"$STATE\", \"next_action\": \"$NEXT_ACTION\"}"
```

---

## Hook Exit Codes

| Exit Code | Meaning | Usage |
|-----------|---------|-------|
| 0 | Success | Operation allowed, no issues |
| 2 | Blocking error | Operation denied, Claude sees stderr as feedback |
| Other | Non-blocking error | Warning shown to user, execution continues |

### Exit Code 0 - Success

```bash
#!/bin/bash
# Hook succeeds, output goes to stdout
echo '{"status": "ok", "message": "Validation passed"}'
exit 0
```

### Exit Code 2 - Block Operation

```bash
#!/bin/bash
# Hook blocks operation, stderr goes to Claude
echo '{"feedback": "Cannot proceed: missing prerequisite"}' >&2
exit 2
```

---

## Best Practices

### 1. Always Output Valid JSON

```bash
# Use jq to ensure valid JSON
OUTPUT=$(jq -n \
  --arg feature "$FEATURE" \
  --argjson spec_exists "$SPEC_EXISTS" \
  '{feature: $feature, artifacts: {spec: {exists: $spec_exists}}}')
echo "$OUTPUT"
```

### 2. Include Helpful Context

```json
{
  "workflow_state": "needs_spec",
  "next_action": "Create specification with /feature command",
  "hint": "Example: /feature 'I want users to be able to log in with email and password'",
  "documentation": "See @docs/guides/workflow-guide.md for SDD process"
}
```

### 3. Provide Actionable Errors

```json
{
  "decision": "block",
  "reason": "Missing spec.md - cannot create plan without specification (Article IV)",
  "fix": "Run: /feature '[describe your feature]'",
  "why": "Specification-first development ensures we understand WHAT before HOW"
}
```

### 4. Include Session Metadata

```json
{
  "session_id": "20251022-1430",
  "timestamp": "2025-10-22T14:30:00Z",
  "feature": "001-user-authentication",
  "git_branch": "001-user-authentication",
  "cwd": "/Users/yangsim/project"
}
```

---

## Example Hook Script

```bash
#!/bin/bash
# .claude/hooks/session-start.sh

# Capture session metadata from stdin
INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')

# Detect feature from git branch or environment
BRANCH=$(git branch --show-current 2>/dev/null)
FEATURE=$(echo "$BRANCH" | grep -oE '^[0-9]{3}-[a-z0-9-]+')
[[ -z "$FEATURE" ]] && FEATURE="${SPECIFY_FEATURE:-}"

# If no feature detected, provide generic state
if [[ -z "$FEATURE" ]]; then
  jq -n \
    --arg session_id "$SESSION_ID" \
    '{
      session_id: $session_id,
      feature: null,
      workflow_state: "no_feature",
      next_action: "Create a git branch with ###-feature-name format or set SPECIFY_FEATURE environment variable"
    }'
  exit 0
fi

# Check artifact existence
FEATURE_DIR="specs/$FEATURE"
SPEC_PATH="$FEATURE_DIR/spec.md"
PLAN_PATH="$FEATURE_DIR/plan.md"
TASKS_PATH="$FEATURE_DIR/tasks.md"

SPEC_EXISTS=false
PLAN_EXISTS=false
TASKS_EXISTS=false

[[ -f "$SPEC_PATH" ]] && SPEC_EXISTS=true
[[ -f "$PLAN_PATH" ]] && PLAN_EXISTS=true
[[ -f "$TASKS_PATH" ]] && TASKS_EXISTS=true

# Determine workflow state
if [[ "$SPEC_EXISTS" == "false" ]]; then
  STATE="needs_spec"
  NEXT_ACTION="Create specification: /feature '[describe feature]'"
elif [[ "$PLAN_EXISTS" == "false" ]]; then
  STATE="needs_plan"
  NEXT_ACTION="Create implementation plan: /plan $SPEC_PATH"
elif [[ "$TASKS_EXISTS" == "false" ]]; then
  STATE="needs_tasks"
  NEXT_ACTION="Generate tasks with generate-tasks skill (auto-invoked after /plan)"
else
  STATE="ready_for_implementation"
  NEXT_ACTION="Run /audit to verify consistency, then /implement to begin"
fi

# Output JSON
jq -n \
  --arg session_id "$SESSION_ID" \
  --arg feature "$FEATURE" \
  --arg directory "$FEATURE_DIR" \
  --argjson spec_exists "$SPEC_EXISTS" \
  --arg spec_path "$SPEC_PATH" \
  --argjson plan_exists "$PLAN_EXISTS" \
  --arg plan_path "$PLAN_PATH" \
  --argjson tasks_exists "$TASKS_EXISTS" \
  --arg tasks_path "$TASKS_PATH" \
  --arg workflow_state "$STATE" \
  --arg next_action "$NEXT_ACTION" \
  --arg git_branch "$BRANCH" \
  '{
    session_id: $session_id,
    feature: $feature,
    directory: $directory,
    artifacts: {
      spec: {exists: $spec_exists, path: $spec_path},
      plan: {exists: $plan_exists, path: $plan_path},
      tasks: {exists: $tasks_exists, path: $tasks_path}
    },
    workflow_state: $workflow_state,
    next_action: $next_action,
    git_branch: $git_branch
  }'

exit 0
```

---

## Related Documentation

- **@docs/reference/claude-code-docs/claude-code_hooks.md** - Hook system reference
- **@.claude/hooks/session-start.sh** - Actual implementation
- **@.claude/hooks/validate-workflow.sh** - Article IV enforcement

---

**Template Version**: 1.0
**Last Updated**: 2025-10-22

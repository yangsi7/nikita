# SDD Phase Routing

## Purpose

Route validated SDD requests to the correct phase command or skill.

---

## Routing Decision Tree

```
User Intent
    │
    ├─ feature_creation
    │   ├─ Prerequisites met? → YES → /feature "{feature_description}"
    │   └─ Missing product.md? → SUGGEST /define-product (optional)
    │
    ├─ implementation
    │   ├─ Audit PASS? → YES → /implement {plan_path}
    │   ├─ Audit FAIL? → BLOCK → Show audit failures
    │   └─ No tasks.md? → RUN /tasks first
    │
    ├─ audit
    │   ├─ All artifacts exist? → YES → /audit {feature_path}
    │   └─ Missing artifacts? → SUGGEST create them first
    │
    ├─ planning
    │   ├─ Spec clarified? → YES → /plan {spec_path}
    │   └─ [NEEDS CLARIFICATION]? → RUN /clarify first
    │
    ├─ status
    │   └─ Always → Report current phase + next steps
    │
    └─ foundation
        ├─ "define product" → /define-product
        └─ "generate constitution" → /generate-constitution
```

---

## Routing Implementation

### Feature Creation Route

```
IF intent = "feature_creation":
  IF user provided description:
    SlashCommand(command='/feature "{description}"')
  ELSE:
    ASK user: "What feature would you like to create?"
```

### Implementation Route

```
IF intent = "implementation":
  plan_path := find_plan_md()

  IF audit_status = "PASS":
    SlashCommand(command=f'/implement {plan_path}')
  ELIF audit_status = "FAIL":
    Report: "Audit failed. Fix these CRITICAL issues first:"
    Show audit failures
  ELIF audit_status = "NOT_RUN":
    SlashCommand(command='/audit')
    THEN retry implementation route
```

### Audit Route

```
IF intent = "audit":
  feature_path := find_feature_dir()
  SlashCommand(command=f'/audit {feature_path}')
```

### Planning Route

```
IF intent = "planning":
  spec_path := find_spec_md()

  IF has_clarification_markers(spec_path):
    SlashCommand(command='/clarify')
    THEN retry planning route
  ELSE:
    SlashCommand(command=f'/plan {spec_path}')
```

### Foundation Route

```
IF intent = "foundation":
  IF "define product" OR "/define-product" in trigger:
    SlashCommand(command='/define-product')
  ELIF "generate constitution" OR "/generate-constitution" in trigger:
    IF product.md exists:
      SlashCommand(command='/generate-constitution')
    ELSE:
      SUGGEST: "Run /define-product first to create product.md"
```

---

### Auto-Chain Documentation

**Note**: The specify-feature skill (Phase 3) automatically chains to subsequent phases:
- `/feature` → creates spec.md → auto-invokes `/plan`
- `/plan` → creates plan.md → auto-invokes `generate-tasks`
- `generate-tasks` → creates tasks.md → auto-invokes `/audit`

This is handled by specify-feature SKILL.md lines 40-45, NOT by this orchestrator.
The orchestrator's job is to route to the FIRST command; auto-chaining handles the rest.

---

### Status Route

```
IF intent = "status":
  # Try coordinator first
  coordinator_response := Task(subagent_type="sdd-coordinator", ...)

  IF coordinator_response.success:
    Report:
      "Current SDD Status:"
      - Phase: {coordinator_response.current_phase}
      - Status: {coordinator_response.phase_name}
      - Next Step: {coordinator_response.recommended_action}
      - Blockers: {coordinator_response.blocking_issues or "None"}
  ELSE:
    # Fallback: Direct file inspection when coordinator unavailable
    artifacts := {
      "product.md": fd product.md memory/,
      "constitution.md": fd constitution.md memory/,
      "spec.md": fd spec.md specs/,
      "plan.md": fd plan.md specs/,
      "tasks.md": fd tasks.md specs/,
      "audit-report.md": fd audit-report.md specs/
    }

    current_phase := determine_phase_from_artifacts(artifacts)

    Report:
      "Current SDD Status (fallback mode):"
      - Phase: {current_phase}
      - Artifacts found: {list existing artifacts}
      - Next Step: {infer_next_step(current_phase)}
```

---

## Path Resolution

### Finding Feature Directory

```bash
# Find most recent feature directory
fd --type d '^[0-9]{3}-' specs/ | sort | tail -1
```

### Finding Spec File

```bash
# For current feature
fd spec.md specs/$FEATURE/
```

### Finding Plan File

```bash
# For current feature
fd plan.md specs/$FEATURE/
```

---

## Post-Routing Hooks

After routing to a phase command:

1. **Wait for completion**: Monitor command execution
2. **Capture output**: Store artifacts created
3. **Trigger post-phase-sync**: Update plans/todos
4. **Log event**: Record in event-stream.md

---

## Error Recovery

### Command Fails

```
IF SlashCommand fails:
  Log error to event-stream.md
  Report to user: "Phase command failed: {error}"
  SUGGEST: Manual intervention or retry
```

### Infinite Loop Prevention

```
max_retries := 3
retry_count := 0

WHILE prerequisites not met AND retry_count < max_retries:
  Run prerequisite command
  retry_count += 1

IF retry_count >= max_retries:
  BLOCK: "Unable to satisfy prerequisites after 3 attempts"
```

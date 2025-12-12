# SDD Post-Phase Sync

## Purpose

Update project tracking files after each SDD phase completes.

---

## Sync Targets

| File | When Updated | What's Updated |
|------|--------------|----------------|
| `plans/master-plan.md` | After spec/plan creation | Spec references, phase status |
| `todos/master-todo.md` | After any phase | Task status, feature entries |
| `event-stream.md` | After every action | Phase completion log |

---

## Phase-Specific Sync Actions

### After Phase 3: Feature Creation (/feature)

```
1. Update todos/master-todo.md:
   - Add new feature entry:
     ## Phase N: {Feature Name}
     **Status**: TODO
     **Spec**: specs/{NNN-feature-name}/spec.md
     **Created**: {date}

2. Update plans/master-plan.md:
   - Add spec reference to relevant phase section
   - Update YAML frontmatter timestamp

3. Log to event-stream.md:
   [{timestamp}] SDD: Phase 3 complete - specs/{feature}/spec.md created
```

### After Phase 5: Planning (/plan)

```
1. Update todos/master-todo.md:
   - Update feature status to "Planning Complete"
   - Add link to plan.md

2. Update plans/master-plan.md:
   - Add architecture decisions (if any)
   - Update implementation phase section

3. Log to event-stream.md:
   [{timestamp}] SDD: Phase 5 complete - plan.md, research.md created
```

### After Phase 7: Audit (/audit)

```
1. Update todos/master-todo.md:
   - Update feature status:
     - PASS → "Ready for Implementation"
     - FAIL → "Audit Failed - Fix Required"

2. Log to event-stream.md:
   [{timestamp}] SDD: Phase 7 complete - Audit {PASS|FAIL}
```

### After Phase 8: Implementation (/implement)

```
1. Update todos/master-todo.md:
   - Mark completed tasks with [x]
   - Update progress summary table
   - Update feature status to "Complete" if all tasks done

2. Update plans/master-plan.md:
   - Update phase status in YAML frontmatter
   - Add to phases_complete list

3. Log to event-stream.md:
   [{timestamp}] SDD: Phase 8 - Task {T_id} complete
   [{timestamp}] SDD: Feature {feature} implementation complete
```

---

## Implementation

### Updating todos/master-todo.md

```python
def update_master_todo(phase, feature_name, status):
    # Read current todos
    content = read_file("todos/master-todo.md")

    if phase == "feature_creation":
        # Add new feature entry
        entry = f"""
## Phase N: {feature_name}
**Status**: TODO
**Spec**: specs/{feature_name}/spec.md
**Created**: {date.today()}
"""
        content = append_to_section(content, "Features", entry)

    elif phase == "implementation":
        # Mark tasks complete
        content = mark_task_complete(content, task_id)
        content = update_progress_table(content)

    # Update YAML frontmatter
    content = update_yaml_header(content, {
        "updated": datetime.now().isoformat(),
        "current_phase": get_current_phase()
    })

    write_file("todos/master-todo.md", content)
```

### Updating plans/master-plan.md

```python
def update_master_plan(phase, feature_name, artifacts):
    content = read_file("plans/master-plan.md")

    if phase == "feature_creation":
        # Add spec reference
        ref = f"- [{feature_name}](specs/{feature_name}/spec.md)"
        content = append_to_section(content, "Specifications", ref)

    elif phase == "planning":
        # Add plan reference
        content = append_to_section(content, "Implementation Plans",
            f"- [{feature_name}](specs/{feature_name}/plan.md)")

    # Update YAML frontmatter
    content = update_yaml_header(content, {
        "updated": datetime.now().isoformat(),
        "phases_complete": get_completed_phases()
    })

    write_file("plans/master-plan.md", content)
```

### Logging to event-stream.md

```python
def log_sdd_event(phase, message):
    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] SDD: {message}"

    # Read current events
    content = read_file("event-stream.md")
    lines = content.split("\n")

    # Keep header (3 lines) + last 22 events + new event = 25 max
    header = lines[:3]
    events = lines[3:]
    events.append(log_entry)
    events = events[-22:]  # Keep last 22 events

    write_file("event-stream.md", "\n".join(header + events))
```

---

## Verification

After each sync:

```bash
# Verify todos updated
rg "Status.*{feature_name}" todos/master-todo.md

# Verify plans updated
rg "{feature_name}" plans/master-plan.md

# Verify event logged
tail -3 event-stream.md
```

---

## Error Handling

### File Not Found

```
IF master-plan.md not found:
  WARN: "plans/master-plan.md missing. Creating from template."
  Create from .claude/templates/planning-template.md

IF master-todo.md not found:
  WARN: "todos/master-todo.md missing. Creating from template."
  Create from .claude/templates/todo-template.md
```

### Concurrent Edit Conflict

```
IF file modified during sync:
  RE-READ file
  MERGE changes
  RETRY write
```

---

## Integration with Orchestrator

Post-phase sync is triggered automatically after:
1. SlashCommand completes successfully
2. Skill execution finishes
3. Task/agent returns results

Call sequence:
```
Phase Command/Skill completes
    ↓
post_phase_sync(phase, feature_name, artifacts)
    ↓
Update todos → Update plans → Log event
    ↓
Return to orchestrator
```

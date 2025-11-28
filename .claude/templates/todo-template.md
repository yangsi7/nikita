# Current Session Tasks (CoD^Σ)

**Session**: YYYY-MM-DD
**Focus**: [Brief description of session focus]

---

## Instructions for Use

This file tracks actionable tasks for the current development session. It should be:
- **Updated frequently** - Mark tasks complete immediately after finishing
- **Organized by session** - Separate current work from backlog
- **Prioritized** - Order tasks by importance and dependencies
- **Specific** - Each task should be concrete and actionable

### Task Status Indicators

- `[ ]` Pending - Not yet started
- `[x]` Completed - Finished and verified
- `[~]` In Progress - Currently being worked on
- `[!]` Blocked - Cannot proceed due to dependency or issue
- `[?]` Needs Clarification - Requires more information

---

## Current Status (CoD^Σ)

```
Completed := {Phase1[tasks], Phase2[tasks], ...}
Pending := {Phase3[tasks], ...}
Blocked := {task_description: blocker_reason}

Progress := ∑(completed) / ∑(total) = X/Y = Z%
Status := [PLANNING | IN_PROGRESS | BLOCKED | COMPLETE]
```

---

## Active Tasks (Current Session)

### Phase 1: [Phase Name]
**Goal**: [Brief description of what this phase achieves]

- [ ] **Task ID**: Task description
  - **Acceptance Criteria**: How to verify completion
  - **Dependencies**: Prerequisites or blocking tasks
  - **Evidence**: File paths, test commands, etc.

- [ ] **Task ID**: Task description
  - **Acceptance Criteria**: How to verify completion
  - **Dependencies**: Prerequisites or blocking tasks
  - **Evidence**: File paths, test commands, etc.

### Phase 2: [Phase Name]
**Goal**: [Brief description of what this phase achieves]

- [ ] **Task ID**: Task description
  - **Acceptance Criteria**: How to verify completion
  - **Dependencies**: Prerequisites or blocking tasks
  - **Evidence**: File paths, test commands, etc.

---

## Backlog (Future Sessions)

### High Priority
- [ ] Task description
- [ ] Task description

### Medium Priority
- [ ] Task description
- [ ] Task description

### Low Priority
- [ ] Task description
- [ ] Task description

---

## Blocked Tasks

| Task | Blocker | Resolution Plan |
|------|---------|-----------------|
| Task description | Why it's blocked | How to unblock |
| Task description | Why it's blocked | How to unblock |

---

## Completed Tasks

### Session [session-id] (YYYY-MM-DD)

#### Phase 1: [Phase Name] ✓
- [x] Task description - Evidence: file:line or test output
- [x] Task description - Evidence: file:line or test output

#### Phase 2: [Phase Name] ✓
- [x] Task description - Evidence: file:line or test output
- [x] Task description - Evidence: file:line or test output

---

## Task Templates

### Standard Task Format
```markdown
- [ ] **T###**: [Action verb] [specific outcome]
  - **AC1**: [Testable acceptance criterion 1]
  - **AC2**: [Testable acceptance criterion 2]
  - **Dependencies**: [Other task IDs or prerequisites]
  - **Evidence**: [How to verify completion]
  - **Estimate**: [Time estimate if known]
```

### Feature Implementation Task
```markdown
- [ ] **T###**: Implement [feature name] for [user story]
  - **AC1**: User can [action] and sees [expected result]
  - **AC2**: Tests pass for all acceptance criteria
  - **AC3**: Code follows project conventions
  - **Dependencies**: T### (data model), T### (API endpoint)
  - **Evidence**: `npm test -- feature-name.test.ts` passes
  - **Estimate**: 2-4 hours
```

### Bug Fix Task
```markdown
- [ ] **T###**: Fix [bug description]
  - **AC1**: Bug no longer reproducible
  - **AC2**: Regression test added and passing
  - **AC3**: No new bugs introduced
  - **Dependencies**: None
  - **Evidence**: Issue reproduction steps fail (expected behavior)
  - **Estimate**: 1-2 hours
```

### Research Task
```markdown
- [ ] **T###**: Research [topic/technology/approach]
  - **AC1**: Document findings in [location]
  - **AC2**: Recommend approach with rationale
  - **AC3**: Identify risks and mitigation strategies
  - **Dependencies**: None
  - **Evidence**: Research document in docs/research/
  - **Estimate**: 2-3 hours
```

---

## CoD^Σ Task Workflow

```
Task_Lifecycle := created → planned → in_progress → verified → completed

Phase_Flow := ∀task∈Phase: task.status = completed ⇒ Phase.status = complete

Evidence_Requirement := ∀task: task.completed ⇒ ∃evidence: verifiable(evidence)
```

---

## Best Practices

1. **Break down large tasks** - If a task takes > 4 hours, split it into subtasks
2. **Define clear ACs** - Every task needs ≥ 2 testable acceptance criteria
3. **Track dependencies** - Note blocking relationships explicitly
4. **Update frequently** - Mark tasks complete immediately after verification
5. **Maintain backlog** - Move incomplete tasks to backlog at session end
6. **Archive completed** - Move finished sessions to archive section
7. **Evidence-based** - Every completion requires verifiable evidence

---

## Session Handover Checklist

Before ending a session:
- [ ] All in-progress tasks documented with current state
- [ ] Blockers identified with resolution plans
- [ ] Backlog updated with new discoveries
- [ ] Completed tasks have evidence links
- [ ] Next session priorities identified
- [ ] Planning.md updated if plan changed
- [ ] Event-stream.md updated with key events

---

## Related Documents

- **Planning**: @planning.md (master plan, architecture)
- **Workbook**: @workbook.md (current context, patterns)
- **Events**: @event-stream.md (chronological log)
- **Constitution**: @.claude/shared-imports/constitution.md (7 articles)

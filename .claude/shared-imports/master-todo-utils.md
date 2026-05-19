# Master Todo Utils - Feature Registration & Status Tracking

## Purpose

Provides instructions for skills to register features and track status in `todos/master-todo.md`.

---

## Master Todo Structure

```
todos/
├── master-todo.md      # Phase-organized feature tracker
└── [session-todos]/    # (Optional) Per-session task files
```

### master-todo.md Format

```markdown
# Master Todo

## Phase 2: Feature Name
**Status**: ❌ TODO | ⚠️ In Progress | ✅ Complete
**Spec**: `specs/NNN-feature-name/spec.md`
**Plan**: `specs/NNN-feature-name/plan.md`

### User Stories
- [ ] US-1: Story description (P1)
  - [ ] T1.1: Task 1
  - [ ] T1.2: Task 2
- [ ] US-2: Story description (P2)
  - [ ] T2.1: Task 1
```

---

## Registering a New Feature

### When to Register

| Event | Action |
|-------|--------|
| /gsd:spec-phase completes | Add new feature entry |
| /gsd:plan-phase completes | Update with plan link |
| /gsd:execute-phase completes | Add user story subtasks |

### Registration Format

```markdown
## Phase N: Feature Name
**Status**: ❌ TODO
**Spec**: `specs/NNN-feature-name/spec.md`
**Created**: YYYY-MM-DD

### Overview
[Brief description from spec.md Overview section]

### User Stories (from tasks.md)
- [ ] US-1: Story name
```

### Registration Command Pattern

```bash
# Check if feature already exists
rg "## Phase.*Feature Name" todos/master-todo.md

# If not found, append to master-todo.md
```

---

## Updating Feature Status

### Status Transitions

```
❌ TODO → ⚠️ In Progress → ✅ Complete
```

### Status Update Triggers

| Event | Status Update |
|-------|---------------|
| /gsd:execute-phase started | ⚠️ In Progress |
| /gsd:verify-work PASS (all stories) | ✅ Complete |
| Implementation blocked | Add 🚫 Blocked note |

### Update Pattern

```markdown
## Phase 2: OAuth Authentication
**Status**: ⚠️ In Progress ← Updated
**Spec**: `specs/002-oauth-auth/spec.md`
**Plan**: `specs/002-oauth-auth/plan.md`
**Started**: 2025-11-28

### User Stories
- [x] US-1: Google OAuth login (P1) ← Completed
- [ ] US-2: Session management (P1)  ← In progress
- [ ] US-3: Logout functionality (P2)
```

---

## Linking Tasks to Master Todo

### From tasks.md to master-todo.md

When generate-tasks creates tasks.md, also update master-todo.md with story entries:

```markdown
# In master-todo.md

## Phase 2: OAuth Authentication
...
### User Stories (linked to tasks.md)
- [ ] US-1: User Registration (P1) → `specs/002-oauth/tasks.md#us-1`
- [ ] US-2: Login Flow (P1) → `specs/002-oauth/tasks.md#us-2`
```

### From master-todo.md to spec artifacts

Each feature entry links to its spec directory:

```markdown
**Spec**: `specs/NNN-feature-name/spec.md`
**Plan**: `specs/NNN-feature-name/plan.md`
**Tasks**: `specs/NNN-feature-name/tasks.md`
**Research**: `specs/NNN-feature-name/research.md`
```

---

## Querying Master Todo

### Find Feature by Name

```bash
rg "## Phase.*Feature Name" todos/master-todo.md -A 10
```

### List All In-Progress Features

```bash
rg "Status: ⚠️" todos/master-todo.md -B 1
```

### Find Blocked Features

```bash
rg "🚫 Blocked" todos/master-todo.md -B 5
```

### Count Completed Stories

```bash
rg "- \[x\]" todos/master-todo.md | wc -l
```

---

## Feature ID Convention

Format: `NNN-feature-name`

- **NNN**: 3-digit sequential number (001, 002, ...)
- **feature-name**: kebab-case feature name

Examples:
- `001-therapy-app`
- `002-oauth-auth`
- `003-voice-integration`

### Get Next Feature ID

```bash
# Find highest existing ID
rg "specs/(\d{3})-" todos/master-todo.md -o | sort | tail -1
```

---

## Integration Points

**Skills that REGISTER features**:
- specify-feature: Creates initial entry

**Skills that UPDATE status**:
- create-implementation-plan: Adds plan link
- generate-tasks: Adds user story subtasks
- implement-and-verify: Updates completion status

**Skills that QUERY features**:
- audit: Validates cross-artifact consistency
- system-integrity: Checks feature coverage

---

## Maintenance

### Keep master-todo.md Clean

- **Remove completed Phase sections** after 30 days
- **Archive to** `todo/completed/YYYY-MM.md` if needed
- **Max entries**: Keep master-todo.md under 150 lines
- **Split by phase** if it grows too large

### Prune Pattern

```bash
# Check line count
wc -l todos/master-todo.md

# If > 150 lines, move completed phases to archive
```

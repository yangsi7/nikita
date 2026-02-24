# /roadmap — Project Roadmap Management

Manage the project roadmap (`ROADMAP.md`) — register features, check status, sync artifacts, suggest next work.

## Usage

- `/roadmap` — Display project status summary (active work, metrics, next planned)
- `/roadmap add NNN name` — Register a new feature spec
- `/roadmap sync` — Reconcile ROADMAP.md with specs/ directory
- `/roadmap next` — Suggest next feature based on resolved dependencies
- `/roadmap archive NNN` — Move superseded spec to specs/archive/

## Subcommand Details

### /roadmap (no args)
1. Read `ROADMAP.md`
2. Display: Project Status Dashboard, Active Work, Next Planned sections
3. Show quick metrics: total specs, tests, last deploy

### /roadmap add NNN name
1. Validate NNN is a 3-digit number not already in ROADMAP.md
2. Determine domain (ask user if unclear)
3. Create `specs/NNN-name/` directory
4. Add entry to ROADMAP.md in the appropriate domain table with status PLANNED
5. Log in event-stream.md: `[TIMESTAMP] ROADMAP: Registered Spec NNN — name`

### /roadmap sync
1. Scan `specs/*/` directories for all spec artifacts
2. Compare against ROADMAP.md entries
3. Report:
   - Unregistered specs (in specs/ but not in ROADMAP.md)
   - Missing artifacts (registered but missing spec.md/plan.md/tasks.md)
   - Status drift (ROADMAP says PLANNED but artifacts exist)
4. Suggest corrections (don't auto-edit)

### /roadmap next
1. Read ROADMAP.md for PLANNED/BACKLOG items
2. Check dependency graph for unblocked items
3. Suggest the next feature to implement with rationale

### /roadmap archive NNN
1. Verify spec NNN exists in specs/
2. Ask for superseding spec number
3. Move `specs/NNN-name/` to `specs/archive/NNN-name/`
4. Update ROADMAP.md: mark as ARCHIVED with superseding reference
5. Update `specs/archive/README.md` with new entry
6. Log in event-stream.md

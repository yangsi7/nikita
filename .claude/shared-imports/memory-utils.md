# Memory Utils - Query & Update memory/ Documentation

## Purpose

Provides instructions for skills to query and update the `memory/` documentation system.

---

## Memory Directory Structure

```
memory/
├── README.md              # Index/hub for all docs
├── architecture.md        # System design, components, data flow
├── backend.md             # API routes, database, patterns
├── game-mechanics.md      # Scoring, chapters, bosses, decay
├── user-journeys.md       # Player flows from signup to victory
├── integrations.md        # ElevenLabs, Graphiti, Telegram, Supabase
├── product.md             # (SDD output) User needs, personas, pain points
└── constitution.md        # (SDD output) Technical principles derived from product.md
```

---

## Document Format

Each memory doc uses **Current State vs Target Specs** format:

```markdown
## Section Name

### Current State
**Status**: ✅ Complete | ⚠️ In Progress | ❌ TODO
[What exists NOW in the codebase]

### Target Spec
[What SHOULD exist after implementation]
```

---

## Querying Memory Docs

### Find Relevant Documentation

```bash
# Search for patterns/concepts
rg "keyword" memory/ --type md -l

# Find specific section
rg "## Section Name" memory/ -A 20

# List all docs
fd . memory/ -e md
```

### Read Current State

```bash
# Get current state of a feature area
rg "### Current State" memory/architecture.md -A 10
```

### Check Implementation Status

```bash
# Find all statuses
rg "Status: (✅|⚠️|❌)" memory/ --type md
```

---

## Updating Memory Docs

### After Implementation Verification

When a feature implementation is verified (via /verify), update the corresponding memory doc:

1. **Find the section** matching the implemented feature
2. **Move Target content to Current State**
3. **Update Status** to ✅ Complete
4. **Preserve any Target enhancements** not yet implemented

### Update Pattern

```markdown
## Feature Area

### Current State
**Status**: ✅ Complete ← Updated from ⚠️ In Progress
[Content moved from Target Spec after verification]

### Target Spec
[Only content NOT yet implemented remains]
```

### When to Update

| Event | Action |
|-------|--------|
| /define-product completes | Create/update memory/product.md |
| /generate-constitution completes | Create/update memory/constitution.md |
| /verify PASS for story | Update relevant memory/ section |
| Full feature complete | Move all Target→Current for that feature |

---

## Reading Memory for Context

### For Plan Creation (create-implementation-plan skill)

Query memory/ to understand existing patterns before planning:

```bash
# Find existing authentication patterns
rg "auth|login|session" memory/ --type md -B 2 -A 5

# Check what's already implemented
rg "### Current State" memory/backend.md -A 15
```

### For Spec Creation (specify-feature skill)

Check what already exists to avoid duplication:

```bash
# See existing API routes
rg "API|route|endpoint" memory/backend.md -A 5

# Check existing game mechanics
rg "scoring|chapter|boss" memory/game-mechanics.md -A 10
```

---

## Integration Points

**Skills that READ memory/**:
- specify-feature: Check existing patterns
- create-implementation-plan: Reference current architecture
- clarify-specification: Find existing decisions

**Skills that WRITE memory/**:
- define-product: Creates/updates memory/product.md
- generate-constitution: Creates/updates memory/constitution.md
- implement-and-verify: Updates sections after verification

---

## Anti-Patterns

- **Never delete Current State** - Always preserve implemented features
- **Don't duplicate** - Check if pattern exists in memory/ before adding
- **Keep sections focused** - One concept per section
- **Maintain Status** - Always include status indicator

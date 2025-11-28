# Auto-Sync Utils - Target→Current State Migration

## Purpose

Provides instructions for automatically syncing documentation after implementation verification. Migrates **Target Spec** content to **Current State** in memory/ docs.

---

## Auto-Sync Triggers

| Event | Action |
|-------|--------|
| /verify PASS (single story) | Update specific section in memory/ |
| /verify PASS (all stories) | Full feature migration + master-todo update |
| /implement completes feature | Trigger full auto-sync |

---

## Sync Process Overview

```
1. VERIFY story/feature passes → Trigger auto-sync
2. IDENTIFY affected memory/ docs → Find sections to update
3. MIGRATE Target→Current → Move verified content
4. UPDATE status → ✅ Complete in memory/ and master-todo
5. PRESERVE future Target → Keep unimplemented enhancements
```

---

## Step-by-Step Sync Process

### 1. Identify Affected Documentation

After /verify PASS, determine which memory/ docs contain relevant sections:

```bash
# Find docs mentioning the feature area
rg "feature_keyword" memory/ --type md -l

# Common mappings:
# - API routes → memory/backend.md
# - Database → memory/backend.md
# - Game logic → memory/game-mechanics.md
# - User flows → memory/user-journeys.md
# - External APIs → memory/integrations.md
```

### 2. Locate Target Spec Section

```bash
# Find the Target Spec section
rg "### Target Spec" memory/backend.md -A 30 | rg -A 25 "Feature Name"
```

### 3. Migrate Content

**Before** (in memory/backend.md):
```markdown
## OAuth Authentication

### Current State
**Status**: ⚠️ In Progress
- Basic auth exists
- No OAuth support

### Target Spec
- Google OAuth 2.0 integration
- Session management (7-day persistence)
- Secure logout
```

**After** (post-verification):
```markdown
## OAuth Authentication

### Current State
**Status**: ✅ Complete
- Basic auth exists
- Google OAuth 2.0 integration ← Migrated from Target
- Session management (7-day persistence) ← Migrated from Target
- Secure logout ← Migrated from Target

### Target Spec
[Empty or future enhancements only]
```

---

## Partial vs Full Sync

### Partial Sync (Single Story)

When ONE user story passes /verify:

1. Find the specific capability implemented
2. Move ONLY that capability from Target→Current
3. Keep other Target items for remaining stories

**Example**: US-1 (Google OAuth login) passes

```markdown
### Current State
**Status**: ⚠️ In Progress
- Google OAuth 2.0 integration ← Moved from Target

### Target Spec
- Session management (7-day persistence) ← Stays (US-2)
- Secure logout ← Stays (US-3)
```

### Full Sync (Feature Complete)

When ALL stories pass /verify:

1. Move ALL Target content to Current
2. Update status to ✅ Complete
3. Clear Target (or leave only future enhancements)
4. Update master-todo.md status

---

## Status Update Rules

### In memory/ docs

| Verification Result | Status Update |
|--------------------|---------------|
| First story passes | ⚠️ In Progress (keep) |
| Some stories pass | ⚠️ In Progress (keep) |
| All stories pass | ✅ Complete |
| Story fails | No change (fix and re-verify) |

### In master-todo.md

| Verification Result | Status Update |
|--------------------|---------------|
| First story passes | ⚠️ In Progress + checkbox |
| All stories pass | ✅ Complete |

---

## Sync Commands

### Manual Sync Check

```bash
# List all incomplete Target sections
rg "### Target Spec" memory/ -A 10 | rg -B 3 "- "

# List all Current State sections
rg "### Current State" memory/ -A 10
```

### Verify Sync Consistency

```bash
# Check for orphaned Target content (should be empty after full sync)
for doc in memory/*.md; do
  echo "=== $doc ==="
  rg "### Target Spec" "$doc" -A 5
done
```

---

## Integration with Skills

### implement-and-verify Skill

After each story verification:

1. **Call auto-sync** for that story's capabilities
2. **Update memory/** relevant section
3. **Mark story complete** in master-todo.md
4. **Report** what was synced in verification report

### Sync Announcement

When auto-sync runs, announce:

```
📚 Auto-sync: Migrated Target→Current in memory/backend.md
   - OAuth 2.0 integration
   - Session management
   Updated master-todo.md: Phase 2 → ✅ Complete
```

---

## Edge Cases

### Target Has More Than Implemented

Keep unimplemented enhancements in Target:

```markdown
### Current State
**Status**: ✅ Complete (MVP)
- Google OAuth login
- Basic session management

### Target Spec (Future Enhancements)
- Facebook OAuth (v2)
- Twitter OAuth (v2)
- Advanced session analytics
```

### No Matching Memory Section

If feature doesn't have a memory/ section yet:

1. Create new section in appropriate doc
2. Add under relevant heading
3. Include both Current State (what was just built) and Target Spec (empty or future)

### Conflicting Content

If Current State and Target Spec conflict:

1. **Current State wins** for what's actually implemented
2. Update Target to reflect actual desired end state
3. Log conflict in verification report

---

## Anti-Patterns

- **Don't auto-sync without verification** - Only sync after /verify PASS
- **Don't overwrite Current State** - Always preserve existing implementations
- **Don't sync unverified content** - Failed tests mean no sync
- **Don't delete Target entirely** - Keep future enhancements section

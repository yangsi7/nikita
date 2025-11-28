---
description: Manage Intelligence Toolkit Constitution amendments with version tracking and dependency validation (project)
allowed-tools: Read, Write, Edit, Grep, Bash(rg:*)
argument-hint: ["amendment text"] or empty for viewing
---

## Pre-Execution

!`if [ ! -f ".claude/shared-imports/constitution.md" ]; then echo "ERROR: Constitution not found"; exit 1; fi && echo "Constitution validated"`

# Constitution Management

Execute `/constitution` to view or amend the Intelligence Toolkit Constitution at `.claude/shared-imports/constitution.md`.

**Input**: `$ARGUMENTS` (empty = viewing mode, text = amendment mode)

---

## Viewing Mode (No Arguments)

Display current constitution status.

**Process**:
1. **Read** `.claude/shared-imports/constitution.md`
2. **Parse metadata**: Extract version, ratified date, last-amended date, status from lines 3-5
3. **Extract articles**: Find all `## Article [Roman]: [Title]` headers with `**Status**:` levels
4. **Display formatted output**:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Intelligence Toolkit Constitution
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Version:       X.Y.Z
Ratified:      YYYY-MM-DD
Last Amended:  YYYY-MM-DD
Status:        [ACTIVE/DRAFT/ARCHIVED]

Articles
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Article I: [Title]                                [STATUS_LEVEL]
  [First paragraph summary]

...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total: N articles
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Error Handling**: If metadata missing, warn user. If file not found, pre-execution catches it.

---

## Amendment Mode (With Arguments)

Process amendments: ADD new articles, MODIFY existing, REMOVE deprecated, or FIX typos.

**Expected Format**:
```
[ADD|MODIFY|REMOVE] Article [Roman Numeral]: [Title]

[Amendment content]
```

Or for typos: `Fix typo in Article [Roman]: "[wrong]" → "[correct]"`

### Step 1: Parse Amendment

Extract type, article number, title, and content from `$ARGUMENTS`.

### Step 2: Determine Type & Version Bump

| Type | Trigger | Version Impact | Example |
|------|---------|----------------|---------|
| ADD | "ADD Article..." | MAJOR (+1.0.0) | 1.0.0 → 2.0.0 |
| MODIFY | "MODIFY Article..." | MINOR (+0.1.0) | 1.0.0 → 1.1.0 |
| REMOVE | "REMOVE Article..." | MAJOR (+1.0.0) | 1.0.0 → 2.0.0 |
| PATCH | "Fix typo", "formatting" | PATCH (+0.0.1) | 1.0.0 → 1.0.1 |

### Step 3: Find Dependencies

```bash
rg "@.*constitution\.md" --type md --files-with-matches
```

Parse results and categorize: Skills, Commands, Agents, Documentation.

### Step 4: Generate Impact Report

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Amendment Impact Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Amendment: [ADD|MODIFY|REMOVE] Article [Roman] - [Title]
Version: [old] → [new] ([MAJOR|MINOR|PATCH])

Affected Files: [count] ([breakdown by category])

Recommendations:
[MAJOR]: ⚠️  BREAKING CHANGE - Review all affected files
[MINOR]: ℹ️  Non-breaking - Update docs if needed
[PATCH]: ✓  No action required

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Step 5: Apply Amendment

Use **Edit** tool to update `.claude/shared-imports/constitution.md`:

**5a. Update Metadata** (lines 3-5):
```
**Version**: [new version]
**Ratified**: [NEVER CHANGE original date]
**Last Amended**: [today YYYY-MM-DD]
```

**5b. Apply Content Change**:
- **ADD**: Insert before "## Governance" section with proper formatting and status level
- **MODIFY**: Replace target article content, preserve article number
- **REMOVE**: Delete entire article section (renumber if needed)
- **PATCH**: Fix typo in target article

**5c. Update Amendment History** (before final closing statement):

Add entry ABOVE existing entries (reverse chronological):
```markdown
**v[new version]** ([today YYYY-MM-DD]):
- [Added|Modified|Removed|Fixed]: Article [Roman] - [Title]
- [Brief description of change]
```

**Examples**:
- `**v2.0.0** (2025-10-21): Added Article IX - Dependency Tracking`
- `**v1.1.0** (2025-10-21): Modified Article II - Minimum 2 CoD^Σ traces required`
- `**v1.0.1** (2025-10-21): Fixed typo in Article III`

### Step 6: Present Summary

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Amendment Applied Successfully
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Action:   [ADD|MODIFY|REMOVE|PATCH]
Article:  [Roman] - [Title]
Version:  [old] → [new]
Date:     [YYYY-MM-DD]

Changes:
  • Updated version to [new]
  • Updated last-amended date
  • [Added|Modified|Removed] Article [number]
  • Added Amendment History entry

Affected Files: [count] ([breakdown])

Next Steps:
  1. Review impact report
  2. Update affected files if needed
  3. Test dependent workflows
  4. Commit changes

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Error Handling

**Invalid amendment format**:
```
ERROR: Invalid format. Expected:
[ADD|MODIFY|REMOVE] Article [Roman]: [Title]
[Content]
```

**Article not found** (MODIFY/REMOVE):
```
ERROR: Article [number] not found
Available: [list current articles]
```

**Version parse failure**:
```
ERROR: Cannot parse version. Expected: X.Y.Z
Current: [extracted value]
```

---

## Decision Logic

**Version Bump**:
```
Typo/formatting keywords? → PATCH
  ↓ NO
Adding article? → MAJOR
  ↓ NO
Removing article? → MAJOR
  ↓ NO
Modifying article → MINOR
```

**Amendment Type Detection**:
- First word: ADD/MODIFY/REMOVE (case-insensitive)
- Keywords "fix typo", "formatting" → PATCH override
- Must specify article number (Roman numeral)

---

## Tool Usage

- **Read**: Load constitution, verify structure
- **Edit**: Update metadata, articles, history (ALWAYS use for existing file)
- **Bash(rg)**: Find dependency imports
- **Write**: NEVER use (file exists)

---

## Constraints

1. **NEVER** modify ratified date
2. **ALWAYS** update last-amended date
3. **ALWAYS** use Edit tool (not Write)
4. **ALWAYS** validate version format
5. **ALWAYS** find dependencies
6. **ALWAYS** update Amendment History
7. **PRESERVE** article formatting

---

## Constitutional Compliance

- **Article VI (Simplicity)**: Single file, < 300 lines ✓
- **Article IV (Spec-First)**: Built from spec.md ✓
- **Article V (Template-Driven)**: Consistent formatting ✓

---

**Example Usage**:

```bash
# View constitution
/constitution

# Add new article
/constitution ADD Article IX: Dependency Tracking
All skills must track dependencies using project-intel.mjs.

# Modify existing
/constitution MODIFY Article II: Evidence-Based Reasoning
Require minimum 2 CoD^Σ traces per architectural decision.

# Fix typo
/constitution Fix typo in Article III: "developemnt" → "development"
```

---

*End of /constitution command*

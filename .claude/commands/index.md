---
description: Generate or regenerate PROJECT_INDEX.json for project intelligence queries
allowed-tools: Bash(node:*), Bash(project-intel.mjs:*)
---

# Generate Project Index

Generate or regenerate PROJECT_INDEX.json containing:
- Directory structure and file metadata
- Code symbols (functions, classes, interfaces)
- Import/export relationships
- Call graphs and dependencies

This enables intelligence-first workflows with 80-95% token savings.

## Execution

The index generation tool was installed during toolkit installation.
If PROJECT_INDEX.json doesn't exist, the index tool should auto-generate it on first query.

Test if index exists:
```bash
ls -la PROJECT_INDEX.json
```

If missing, try running a query (will auto-generate):
```bash
project-intel.mjs stats
```

**Note**: Index generation is handled by the claude-code-project-index tool installed from GitHub.
If issues occur, re-run the installation script which installs this tool.

## When to Use

Run `/index` when:
- PROJECT_INDEX.json missing (first time setup)
- Significant code changes made
- After adding/removing files
- Index appears stale or incomplete
- Intelligence queries returning unexpected results

## After Indexing

Once complete, use project-intel.mjs to query the index:

```bash
# Get project overview
project-intel.mjs --overview --json

# Search for files
project-intel.mjs --search "auth" --json

# Get symbols from file
project-intel.mjs --symbols src/file.ts --json
```

Always query intelligence BEFORE reading files for maximum token efficiency.

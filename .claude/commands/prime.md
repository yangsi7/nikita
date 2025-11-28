---
description: Load optimal codebase context using standard intelligence queries
allowed-tools: Bash(./project-intel.mjs:*), Bash(jq:*), Read, Grep
---

## Auto-Load Overview

!`./project-intel.mjs stats --json`

!`./project-intel.mjs tree`

!`./project-intel.mjs report --json | jq -c '{files:.stats.totalFiles, langs:.stats.languages, tests:.stats.tests, docs:.stats.docs, hotspots:(.topInbound[:5]|map({fn:.fn,callers:.count})), couplings:(.topOutbound[:5]|map({fn:.fn,callees:.count})), modules:(.topModules[:10]|map({mod:.module,uses:.count}))}'`

!`jq -c '{tech_stack: [.deps | to_entries | map(.value) | flatten | group_by(.) | map({lib: .[0], uses: length}) | sort_by(-.uses)[:12] | .[] | "\(.lib):\(.uses)"], components: [.f | keys | map(split("/")[0]) | group_by(.) | map({name: .[0], files: length}) | sort_by(-.files)[:5] | .[] | "\(.name):\(.files)files"], key_docs: [.d | keys | map(select(test("CLAUDE|README")))[:8] | .[]], high_coupling: [.deps | to_entries | map({f: .key, i: (.value|length)}) | sort_by(-.i)[:5] | .[] | "\(.f|split("/")|.[-1]):\(.i)imports"], test_files: (.f | keys | map(select(test("test"))) | length | tostring) + "_found:" + ([.f | keys | map(select(test("test")))[:5] | .[]] | join(","))}' PROJECT_INDEX.json`

!`jq -c '{component_languages: [.f | keys | .[] | {component: split("/")[0], ext: split(".")[-1]}] | group_by(.component) | map({c: .[0].component, l: (group_by(.ext) | map("\(.[0].ext):\(length)") | join(","))}) | map("\(.c)=\(.l)")[:4]}' PROJECT_INDEX.json`

!`./project-intel.mjs dead -l 10 --json`

# Prime Code Context

You now have the codebase overview loaded above. Use this context to understand the project before diving into specifics.

## What You Have

- **Stats**: File counts, languages (parsed vs listed), markdown docs count
- **Tree**: Complete directory structure showing all components and subdirectories
- **Report**: Function hotspots (most called), call coupling (most callees), module usage (most imported)
- **Tech Stack**: Top 12 libraries by import frequency → framework decisions (React? Vue? Firebase? Express?)
- **Components**: Monorepo structure → files per top-level directory (where is the code?)
- **Key Docs**: Critical documentation files → read these first (CLAUDE.md = AI instructions, README.md = human setup)
- **High Coupling**: Files with most imports → entry points + change-risk hotspots (App.tsx:42imports = main React entry)
- **Test Files**: Count + paths of test files → testing infrastructure gaps
- **Component Languages**: Actual language distribution per component → CRITICAL (cloud-function-typescript is 32 JS, only 2 TS!)
- **Dead Code**: Unused exports → code quality snapshot + refactoring candidates

---

## Deeper Queries (Choose Based on Your Task)

### Find & Explore

```bash
# Search for files or symbols by name
./project-intel.mjs search "auth" --json
./project-intel.mjs search "payment" -l 10 --json

# Explore multiple concepts at once (files + symbols + docs for each term)
./project-intel.mjs investigate auth payment transcription -l 3 --json

# Find documentation
./project-intel.mjs docs "CLAUDE" -l 5 --json
./project-intel.mjs docs "README" -l 10 --json
```

### Analyze Functions (Call Graphs)

```bash
# Who calls this function?
./project-intel.mjs callers fetchTranscriptions --json

# What does this function call?
./project-intel.mjs callees Home --json

# Path between two functions
./project-intel.mjs trace Home fetchTranscriptions --json

# Full debug info (file summary + callers + callees)
./project-intel.mjs debug Home --json
./project-intel.mjs debug updateUser --json
```

### Analyze Dependencies (Import Graphs)

```bash
# What modules does this file import?
./project-intel.mjs imports front_react/sr/pages/Home.tsx --json

# Which files import this module?
./project-intel.mjs importers react --json
./project-intel.mjs importers "firebase/auth" --json
./project-intel.mjs importers "@/firebase.js" --json
```

### Analyze Structure

```bash
# Summarize a directory (file categories)
./project-intel.mjs summarize front_react/sr --json
./project-intel.mjs summarize cloud-function-typescript/functions --json

# Deeper tree with actual files
./project-intel.mjs tree --max-depth 3 --files

# Focus report on specific component
./project-intel.mjs report --focus cloud-function-typescript --json
./project-intel.mjs report --focus front_react --json
```

### Code Quality Analysis

```bash
# More dead code + list test files
./project-intel.mjs sanitize -l 20 --tests --json

# Complexity metrics (top functions by callers/callees)
./project-intel.mjs metrics --json

# All dead functions (careful: large output)
./project-intel.mjs dead -l 50 --json
```

---

## Example Workflows

### Debug a Bug

```bash
# 1. Find the function
./project-intel.mjs search "fetchTranscription" --json
# Result: fetchTranscriptions in front_react/sr/pages/Home.tsx

# 2. See who calls it (trace the flow)
./project-intel.mjs callers fetchTranscriptions --json
# Result: Home, handleGenerateSummary, loadTranscript

# 3. Debug the main caller
./project-intel.mjs debug Home --json
# Result: Shows callees, imports, file summary

# 4. NOW read the specific lines
Read front_react/sr/pages/Home.tsx
```

### Understand a Feature

```bash
# 1. Explore the concept across codebase
./project-intel.mjs investigate payment stripe checkout -l 5 --json
# Result: Files, symbols, and docs matching each term

# 2. Find relevant documentation
./project-intel.mjs docs "payment" -l 5 --json
# Result: Markdown files discussing payment

# 3. See what modules are used
./project-intel.mjs importers "stripe" --json
# Result: Files that import stripe
```

### Refactor/Clean Up

```bash
# 1. Find all unused exports
./project-intel.mjs dead -l 50 --json
# Result: Functions with no callers

# 2. Check test coverage gaps
./project-intel.mjs sanitize --tests --json
# Result: Dead code + test file locations

# 3. Find highly coupled functions
./project-intel.mjs metrics --json
# Result: Functions with many callers (change = high impact)
```

### Onboard to Codebase

```bash
# 1. Get full tree
./project-intel.mjs tree --max-depth 3

# 2. Read main documentation
./project-intel.mjs docs "CLAUDE" -l 10 --json
./project-intel.mjs docs "README" -l 10 --json

# 3. Understand top modules (tech stack)
./project-intel.mjs report --json | jq '.topModules[:20]'

# 4. Summarize main directories
./project-intel.mjs summarize front_react --json
./project-intel.mjs summarize cloud-function-typescript --json
```

---

## Pro Tips

1. **Always use --json** for structured output (easier to parse, filter with jq)
2. **Use -l to limit** results and save tokens (e.g., `-l 5`, `-l 10`)
3. **Pipe to jq** for custom views: `| jq '.[:3]'` for first 3 results
4. **Query before read** - intel queries cost ~10 tokens, file reads cost ~500+
5. **Combine investigate** - explore multiple terms in one command
6. **Focus reports** - `--focus <path>` narrows analysis to specific directories

---

## Command Reference

| Command | Purpose | Key Options |
|---------|---------|-------------|
| `stats` | Repo size, languages | `--json` |
| `tree` | Directory structure | `--max-depth <n>`, `--files` |
| `search <term>` | Find files/symbols | `--regex`, `-l <n>`, `--json` |
| `callers <fn>` | Who calls function | `-l <n>`, `--json` |
| `callees <fn>` | What function calls | `-l <n>`, `--json` |
| `trace <fn1> <fn2>` | Path between functions | `--json` |
| `dead` | Unused exports | `-l <n>`, `--json` |
| `imports <file>` | File's dependencies | `--json` |
| `importers <mod>` | Module's users | `-l <n>`, `--json` |
| `metrics` | Complexity hotspots | `--json` |
| `summarize <path>` | Directory breakdown | `--json` |
| `investigate <terms>` | Multi-term exploration | `-l <n>`, `--json` |
| `debug <fn\|file>` | Full analysis | `--json` |
| `sanitize` | Dead code + tests | `-l <n>`, `--tests`, `--json` |
| `docs <term>` | Search documentation | `-l <n>`, `--json` |
| `report` | Comprehensive metrics | `--focus <path>`, `--json` |

---

## Remember

**Query first, read second.** The overview above costs ~300 tokens. Reading all files would cost 50,000+. Each deeper query costs ~50 tokens. Targeted file reads (after intel) cost ~500 tokens.

**Token savings: 80-95% vs naive file reading.**

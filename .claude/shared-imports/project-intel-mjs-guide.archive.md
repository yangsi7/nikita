# project-intel.mjs: Intelligence-First Codebase Exploration Guide

**For:** AI agents encountering unfamiliar codebases
**Goal:** Achieve 80-99% token savings by querying indices before reading files
**Method:** Progressive intelligence gathering (overview → search → dependencies → read)

---

## Table of Contents

1. [Quick Start: 3-Minute Onboarding](#quick-start-3-minute-onboarding)
2. [Why Intelligence-First?](#why-intelligence-first)
3. [Command Reference by Category](#command-reference-by-category)
4. [Intelligence-First Workflows](#intelligence-first-workflows)
5. [Decision Trees](#decision-trees)
6. [Best Practices](#best-practices)
7. [Token Efficiency Metrics](#token-efficiency-metrics)

---

## Quick Start: 3-Minute Onboarding

**Scenario:** You're an AI agent, just dropped into an unfamiliar codebase. Here's your first 5 commands:

```bash
# 1. Get project overview (50 bytes vs 500KB reading all files)
node project-intel.mjs stats --json
# {"total_files":84,"fully_parsed":{"typescript":62},"markdown_files":64}
# → TypeScript project, 62 components, well-documented

# 2. See directory structure (200 bytes vs 5KB reading file list)
node project-intel.mjs tree --max-depth 2
# ├── app/ (10 files)
# │   ├── [lang]/ (8 files)
# ├── components/ (35 files)
# │   ├── booking/ (1 files)
# → Next.js 15 app, i18n setup, booking feature exists

# 3. Search for booking feature (100 bytes vs 10KB reading 5 files)
node project-intel.mjs search "booking" --json -l 5
# [{"type":"file","file":"components/booking/CalBookingModal.tsx"},
#  {"type":"symbol","name":"BookingSection"}]
# → Found 2 booking-related components

# 4. Investigate booking context (500 bytes vs 25KB reading related files)
node project-intel.mjs investigate "booking" -l 3
# Files: CalBookingModal.tsx, BookingSection.tsx
# Symbols: CalBookingModal, BookingSection
# Docs: booking-system.md
# → Entry point identified, specs available

# 5. Summarize target file (300 bytes vs 5KB full file read)
node project-intel.mjs summarize 'components/booking/CalBookingModal.tsx'
# Language: typescript
# Imports: @calcom/embed-react, components/ui/dialog
# Exports: CalBookingModal (line 12)
# → React component using Cal.com embed + Dialog wrapper

# 6. NOW read specific file with full context
Read components/booking/CalBookingModal.tsx
```

**Result:** Found booking feature using **1,150 bytes** of intelligence queries instead of reading **45KB** of files directly.
**Token Savings:** 97.4%

---

## Why Intelligence-First?

**Traditional Approach:**
```
User: "Find the booking feature"
Agent: Read app/ → Read components/ → Read all tsx files → Find BookingSection
Cost: 50KB tokens (500 files × 100 bytes scanning)
```

**Intelligence-First Approach:**
```
User: "Find the booking feature"
Agent: search "booking" → investigate "booking" → summarize CalBookingModal.tsx
Cost: 500 bytes tokens
Savings: 99%
```

**Key Insight:** PROJECT_INDEX.json is a pre-computed knowledge graph of your codebase. Query it like a database instead of reading files like books.

---

## Command Reference by Category

### Overview Commands

#### `stats` - Project Snapshot
**Purpose:** First command in every new session
**Cost:** ~50 bytes (vs 500KB reading all files)

```bash
# Get project statistics
node project-intel.mjs stats --json

# Example output:
{
  "total_files": 84,
  "total_directories": 99,
  "fully_parsed": {
    "typescript": 62,
    "shell": 2
  },
  "listed_only": {
    "json": 13,
    "css": 1
  },
  "markdown_files": 64
}
```

**Use Case:** "Is this a TypeScript or JavaScript project? How big is it?"
**Answer:** 62 TypeScript files, 64 markdown docs → well-documented TS project

---

#### `tree` - Directory Structure
**Purpose:** Visualize folder hierarchy without reading files
**Cost:** ~200-500 bytes (depends on depth)

```bash
# Quick 2-level overview (RECOMMENDED)
node project-intel.mjs tree --max-depth 2

# Example output:
.
├── app/ (10 files)
│   ├── [lang]/ (8 files)
├── components/ (35 files)
│   ├── booking/ (1 files)
│   ├── sections/ (9 files)
│   ├── ui/ (19 files)
├── lib/ (6 files)
│   ├── supabase/ (3 files)
├── docs/ (45 files)
    ├── guides/ (5 files)
    ├── specs/ (7 files)
```

**Options:**
- `--max-depth <n>` - Limit depth (prevents 200+ line output)
- `--files` - Show individual files (verbose)

**Use Case:** "Where are the UI components organized?"
**Answer:** `components/ui/` has 19 components, `components/sections/` has 9 page sections

---

### Search Commands

#### `search` - Find Files/Symbols
**Purpose:** Locate candidates before reading files
**Cost:** ~100 bytes for 5 results (vs 5KB reading candidates)

```bash
# Search for booking-related code
node project-intel.mjs search "booking" --json -l 5

# Example output:
[
  {"type":"file","file":"components/booking/CalBookingModal.tsx"},
  {"type":"file","file":"components/sections/BookingSection.tsx"},
  {"type":"symbol","name":"CalBookingModal","files":["components/booking/CalBookingModal.tsx"]},
  {"type":"symbol","name":"BookingSection","files":["components/sections/BookingSection.tsx"]}
]
```

**Options:**
- `-l <n>` - Limit results (default: 20)
- `--json` - JSON output (recommended for agents)
- `--regex` - Treat term as regex pattern

**Use Case:** "Find all Button components"
```bash
node project-intel.mjs search "Button" --type tsx --json
# Returns: components/ui/button.tsx, SelectScrollUpButton, etc.
```

---

#### `investigate` - Deep Exploration
**Purpose:** One-stop shop for files + symbols + docs matching term
**Cost:** ~500 bytes (combines 3 searches)

```bash
# Investigate booking feature comprehensively
node project-intel.mjs investigate "booking" -l 3

# Example output:
Investigate term: booking
  Files:
    - components/booking/CalBookingModal.tsx
    - components/sections/BookingSection.tsx
  Symbols:
    - CalBookingModal (in components/booking/CalBookingModal.tsx, callers: 0, callees: 1)
    - BookingSection (in components/sections/BookingSection.tsx, callers: 0, callees: 0)
  Documentation:
    - docs/specs/booking-system.md
```

**Use Case:** "I need to fix the booking flow but know nothing about this codebase"
**Answer:** CalBookingModal.tsx is entry point, BookingSection uses it, booking-system.md has specs

---

#### `docs` - Search Documentation
**Purpose:** Find markdown files explaining features
**Cost:** ~100 bytes

```bash
# Search for i18n documentation
node project-intel.mjs docs "i18n"

# Output:
Matching documentation files:
  - docs/specs/i18n-strategy.md

# Preview specific doc
node project-intel.mjs docs docs/specs/i18n-strategy.md
# Shows first 50 lines of the doc
```

---

### Dependency Commands

#### `imports` - What File Imports
**Purpose:** Understand file dependencies before modifying
**Cost:** ~50 bytes

```bash
# What does homepage import?
node project-intel.mjs imports 'app/[lang]/page.tsx' --json

# Output:
["app/[lang]/dictionaries.ts","app/[lang]/PageContent.tsx"]
```

**Use Case:** "What will break if I change this file's imports?"

---

#### `importers` - Who Imports This File
**Purpose:** Find reverse dependencies (refactoring safety check)
**Cost:** ~100 bytes

```bash
# Who imports the dictionary system?
node project-intel.mjs importers 'app/[lang]/dictionaries.ts'

# Output:
Files that import app/[lang]/dictionaries.ts:
  - app/[lang]/PageContent.tsx
  - app/[lang]/about/page.tsx
  - app/[lang]/learn/page.tsx
  - app/[lang]/page.tsx
  - app/[lang]/services/page.tsx
```

**Use Case:** "Can I safely change dictionaries.ts signature?"
**Answer:** 5 files import it → breaking change affects 5 components

---

#### `map-imports` - Recursive Import Tree
**Purpose:** Map transitive dependencies for complex systems
**Cost:** ~1000-5000 bytes

```bash
# Map skill dependencies (Claude Code specific)
node project-intel.mjs map-imports skills --json | head -50

# Shows:
# - Which templates each skill uses
# - Circular dependency detection
# - Import depth analysis
```

**Types:** `memory`, `skills`, `commands`, `agents` (Claude Code components)

---

### Call Graph Commands

#### `callers` - Who Calls This Function
**Purpose:** Find reverse call dependencies
**Cost:** ~100 bytes

```bash
# Who calls the carousel hook?
node project-intel.mjs callers useCarousel --json

# Output:
[{"caller":"Carousel","files":["components/ui/carousel.tsx"]}]
```

**Note:** Server Components show no callers (framework invokes them, not tracked)

---

#### `callees` - What This Function Calls
**Purpose:** Understand function dependencies
**Cost:** ~100 bytes

```bash
# What does PageContent call?
node project-intel.mjs callees PageContent

# Output:
PageContent calls scrollToSection (defined in app/[lang]/PageContent.tsx)
```

---

#### `trace` - Call Path Between Functions
**Purpose:** Find how function A reaches function B
**Cost:** ~50 bytes

```bash
# How does PageContent reach scrollToSection?
node project-intel.mjs trace PageContent scrollToSection

# Output:
PageContent -> scrollToSection
```

---

### Code Quality Commands

#### `dead` - Find Unused Exports
**Purpose:** Detect dead code (exported but never called)
**Cost:** ~200 bytes

```bash
# Find unused functions
node project-intel.mjs dead -l 10

# Output:
Unused exported functions:
  - generateMetadata (in app/[lang]/about/page.tsx)
  - getDictionary (in app/[lang]/dictionaries.ts)
```

**⚠️ False Positives:**
- Next.js reserved exports (generateMetadata, generateStaticParams)
- Server Components (framework uses them, not tracked as calls)
- Entry points (page.tsx default exports)

---

#### `sanitize` - Extended Dead Code Analysis
**Purpose:** Find unused functions + check test coverage
**Cost:** ~300 bytes

```bash
# Include test files in analysis
node project-intel.mjs sanitize --tests -l 20

# Output:
Unused exported functions: [list]
Test files: [test file list]
```

---

### Analysis Commands

#### `summarize` - File/Directory Summary
**Purpose:** High-level understanding without reading full file
**Cost:** ~300 bytes (vs 5KB full file)

```bash
# Summarize a file
node project-intel.mjs summarize 'app/[lang]/page.tsx'

# Output:
File app/[lang]/page.tsx
Language: typescript
Imports: app/[lang]/dictionaries.ts, app/[lang]/PageContent.tsx
Exported symbols:
  - LandingPage (line 4): async function returning JSX
```

```bash
# Summarize a directory
node project-intel.mjs summarize components/sections

# Output:
Directory components/sections
- components: 9 files (e.g. AboutSection.tsx, BookingSection.tsx, FAQSection.tsx)
```

**Use Case:** "What's in this component?" → Get 80% understanding with 6% tokens

---

#### `debug` - One-Stop Function Debugging
**Purpose:** Quick context (callers + callees + summary)
**Cost:** ~400 bytes

```bash
# Debug a function
node project-intel.mjs debug PageContent

# Output:
Function PageContent
Defined in: app/[lang]/PageContent.tsx
Callees: scrollToSection

# Debug a file
node project-intel.mjs debug 'components/ui/button.tsx'

# Output:
File components/ui/button.tsx
Language: typescript
Exported symbols:
  - Button (line 34)
  - buttonVariants (line 12)
```

---

#### `metrics` - Hotspot Analysis
**Purpose:** Find most connected functions (complexity indicators)
**Cost:** ~500 bytes

```bash
# Find architecture hotspots
node project-intel.mjs metrics --json

# Output:
{
  "topInbound": [
    {"fn":"useCarousel","count":4},
    {"fn":"useFormField","count":4}
  ],
  "topOutbound": [
    {"fn":"createClient","count":2}
  ]
}
```

**Use Case:** "What are the most critical utilities?"
**Answer:** useCarousel (4 callers), useFormField (4 callers) → shadcn/ui hooks are central

---

#### `report` - Comprehensive Analysis
**Purpose:** Full project or directory report
**Cost:** ~2000-10000 bytes (use `--focus` to reduce)

```bash
# Focused report on specific directory
node project-intel.mjs report --focus components/sections --json

# Output:
{
  "stats": {"totalFiles":9,"languages":{"typescript":9}},
  "topInbound": [...],
  "topOutbound": [...],
  "topModules": [{"module":"react","count":9}]
}
```

**Options:**
- `--focus <path>` - Analyze specific directory only (RECOMMENDED)
- `--json` - JSON output

**Use Case:** Architecture documentation, onboarding new developers

---

## Intelligence-First Workflows

### Workflow 1: Understanding Existing Feature

**Scenario:** "User reports booking is broken, I've never seen this codebase before"

```bash
# Step 1: Get project overview (50 bytes)
node project-intel.mjs stats --json
# → 84 files, TypeScript project

# Step 2: Search for feature (100 bytes)
node project-intel.mjs search "booking" --json -l 5
# → Found CalBookingModal.tsx, BookingSection.tsx

# Step 3: Investigate deeply (500 bytes)
node project-intel.mjs investigate "booking" -l 3
# Files: CalBookingModal.tsx, BookingSection.tsx
# Symbols: CalBookingModal, BookingSection
# Docs: booking-system.md

# Step 4: Check dependencies (50 bytes)
node project-intel.mjs imports 'components/booking/CalBookingModal.tsx'
# → Imports @calcom/embed-react, components/ui/dialog

# Step 5: Check consumers (100 bytes)
node project-intel.mjs importers 'components/booking/CalBookingModal.tsx' -l 5
# → Used by PageContent.tsx

# Step 6: Read specific file (5000 bytes)
Read components/booking/CalBookingModal.tsx
# → Now I understand: Cal.com embed in Dialog, used on homepage
```

**Total Intelligence Queries:** 800 bytes
**File Read:** 5,000 bytes
**Alternative (read-first):** 50,000 bytes (reading all booking-related files)
**Savings:** 88%

---

### Workflow 2: Debugging Function Call

**Scenario:** "scrollToSection function isn't working, find why"

```bash
# Step 1: Debug the function (400 bytes)
node project-intel.mjs debug scrollToSection
# → Defined in app/[lang]/PageContent.tsx

# Step 2: Find callers (100 bytes)
node project-intel.mjs callers scrollToSection -l 5
# → Called by PageContent

# Step 3: Trace call path (50 bytes)
node project-intel.mjs trace PageContent scrollToSection
# → PageContent -> scrollToSection (direct call)

# Step 4: Summarize file (300 bytes)
node project-intel.mjs summarize 'app/[lang]/PageContent.tsx'
# → Client component, handles scroll navigation

# Step 5: Read function context (3000 bytes)
Read app/[lang]/PageContent.tsx (lines 40-80)
# → scrollToSection uses querySelector + scrollIntoView
```

**Total Intelligence Queries:** 850 bytes
**File Read:** 3,000 bytes (targeted section)
**Alternative:** 15,000 bytes (reading multiple files to find function)
**Savings:** 74%

---

### Workflow 3: Refactoring Safety Check

**Scenario:** "I want to change cn() utility signature, what will break?"

```bash
# Step 1: Find importers (100 bytes)
node project-intel.mjs importers 'lib/utils.ts' --json
# → 18 files import it

# Step 2: Find function callers (100 bytes)
node project-intel.mjs callers cn -l 20
# → 18 functions call it across all UI components

# Step 3: Get metrics (500 bytes)
node project-intel.mjs metrics --json
# → cn is hotspot (18 usages - top 3 most called)

# Step 4: Check for safe removal (200 bytes)
node project-intel.mjs dead -l 20
# → cn is NOT in dead code list (actively used)

# Decision: Breaking change affects 18 files → DON'T change signature
```

**Total Intelligence Queries:** 900 bytes
**Alternative:** 90,000 bytes (reading 18 files to find usages)
**Savings:** 99%

**Outcome:** Decided NOT to refactor without major version bump, saved hours of debugging

---

### Workflow 4: New Feature Planning

**Scenario:** "Add a new modal component, what patterns exist?"

```bash
# Step 1: Search existing modals (100 bytes)
node project-intel.mjs search "modal" --json
# → Found Dialog component, CalBookingModal

# Step 2: Investigate modal pattern (500 bytes)
node project-intel.mjs investigate "dialog" "modal" -l 3
# Files: components/ui/dialog.tsx, components/booking/CalBookingModal.tsx
# Symbols: Dialog, DialogContent, DialogTrigger

# Step 3: Check dependencies (50 bytes)
node project-intel.mjs imports 'components/ui/dialog.tsx'
# → @radix-ui/react-dialog

# Step 4: Find similar components (100 bytes)
node project-intel.mjs search "ui/" --type tsx -l 20
# → 19 UI components in components/ui/

# Step 5: Read example (5000 bytes)
Read components/booking/CalBookingModal.tsx
# → Pattern: Dialog wrapper + custom content
```

**Total Intelligence Queries:** 750 bytes
**Planning Decision:** Reuse Dialog component, follow CalBookingModal pattern
**Savings:** Avoided reading all 19 UI components (95KB) to find pattern

---

### Workflow 5: Code Quality Audit

**Scenario:** "Clean up unused code before release"

```bash
# Step 1: Find dead functions (200 bytes)
node project-intel.mjs dead -l 20
# → 8 unused exports found

# Step 2: Find test coverage gaps (300 bytes)
node project-intel.mjs sanitize --tests -l 50
# → 3 test files, some unused test helpers

# Step 3: Get hotspot metrics (500 bytes)
node project-intel.mjs metrics --json
# → Identify over-connected functions (refactoring candidates)

# Step 4: Generate report (2000 bytes)
node project-intel.mjs report --focus components --json
# → Comprehensive component analysis

# Step 5: Read specific files for cleanup (10000 bytes)
Read [files identified in dead code list]
```

**Total Intelligence Queries:** 3,000 bytes
**Result:** Identified 8 dead exports, 2 refactoring candidates
**Savings:** vs reading all 84 files (420KB) to find dead code: 99.3%

---

## Decision Trees

### "Which Command Should I Use?"

```
START: What do I need?
│
├─ "Get project overview"
│  └─→ stats --json
│
├─ "Understand directory structure"
│  └─→ tree --max-depth 2
│
├─ "Find specific file/function"
│  ├─ Know exact name? → search "name" --json -l 5
│  └─ Know general area? → investigate "term" -l 3
│
├─ "Understand dependencies"
│  ├─ What does X import? → imports 'file.tsx'
│  ├─ Who imports X? → importers 'file.tsx'
│  └─ Full dependency tree? → map-imports <type>
│
├─ "Understand function calls"
│  ├─ Who calls X? → callers FunctionName
│  ├─ What does X call? → callees FunctionName
│  └─ Path from A to B? → trace FnA FnB
│
├─ "Find code quality issues"
│  ├─ Unused exports? → dead -l 20
│  ├─ Test coverage? → sanitize --tests
│  └─ Complexity hotspots? → metrics --json
│
├─ "Understand file/function quickly"
│  ├─ File summary? → summarize 'path/to/file.tsx'
│  └─ Function context? → debug FunctionName
│
└─ "Comprehensive analysis"
   └─→ report --focus path/to/dir --json
```

---

### "How Deep Should I Go?"

```
Level 1: PROJECT OVERVIEW (100 bytes)
stats --json + tree --max-depth 2
↓ (Understand: project size, tech stack, organization)

Level 2: FEATURE DISCOVERY (200 bytes)
search "feature" --json -l 5
↓ (Understand: where feature lives, candidates)

Level 3: CONTEXT GATHERING (500 bytes)
investigate "feature" -l 3
↓ (Understand: files + symbols + docs)

Level 4: DEPENDENCY ANALYSIS (200 bytes)
imports 'file.tsx' + importers 'file.tsx'
↓ (Understand: what it needs, who needs it)

Level 5: FILE SUMMARY (300 bytes)
summarize 'file.tsx'
↓ (Understand: exports, imports, language)

Level 6: FILE READ (5000 bytes)
Read file.tsx
↓ (Understand: implementation details)

TOTAL INTELLIGENCE: 1,300 bytes
TARGETED READ: 5,000 bytes
ALTERNATIVE (read-first): 50,000 bytes
SAVINGS: 87%
```

---

### "When to Query vs Read?"

```
QUERY FIRST (project-intel.mjs) when:
✓ You need to find files (search/investigate)
✓ You need to understand dependencies (imports/importers)
✓ You need to find callers/callees (call graph)
✓ You need project overview (stats/tree)
✓ You need to assess code quality (dead/sanitize/metrics)

READ FILE when:
✓ You need implementation details
✓ You need to modify code
✓ You need to understand algorithms
✓ Query results pointed you to specific file
✓ Summary wasn't enough detail

GOLDEN RULE: Always query → then read
ANTI-PATTERN: Read → hope to find what you need
```

---

## Best Practices

### ✅ DO

1. **Always use --json for programmatic parsing**
   ```bash
   # Good (easy to parse)
   node project-intel.mjs search "term" --json

   # Bad (harder to parse text output)
   node project-intel.mjs search "term"
   ```

2. **Limit results with -l to prevent token overflow**
   ```bash
   # Good (controlled output)
   node project-intel.mjs dead -l 10

   # Bad (might return 200+ results)
   node project-intel.mjs dead
   ```

3. **Chain commands (progressive depth)**
   ```bash
   # Good workflow
   stats → tree → search → summarize → read

   # Bad (skip intelligence phase)
   read → hope to find what you need
   ```

4. **Use investigate for unfamiliar features**
   ```bash
   # Good (combines files + symbols + docs)
   node project-intel.mjs investigate "booking" -l 3

   # Bad (multiple separate searches)
   search "booking" && search symbols && docs "booking"
   ```

5. **Check importers before refactoring**
   ```bash
   # Good (safety check)
   node project-intel.mjs importers 'lib/utils.ts'
   # → 18 files import it, breaking change risky

   # Bad (refactor blindly)
   Read lib/utils.ts → change signature → breaks 18 files
   ```

---

### ❌ DON'T

1. **Don't read files before querying indices**
   ```bash
   # ❌ Bad (wastes tokens)
   Read app/page.tsx → Read components/ → Read lib/

   # ✅ Good (intelligence-first)
   search "feature" → summarize → then Read
   ```

2. **Don't use tree without --max-depth**
   ```bash
   # ❌ Bad (200+ line output)
   node project-intel.mjs tree

   # ✅ Good (controlled depth)
   node project-intel.mjs tree --max-depth 2
   ```

3. **Don't trust dead code detection for framework exports**
   ```bash
   # ❌ False positive example
   dead → shows "generateMetadata" as unused
   # (Actually used by Next.js framework, not in call graph)

   # ✅ Good (verify before removing)
   Check if export is Next.js reserved function
   ```

4. **Don't skip --json for programmatic use**
   ```bash
   # ❌ Bad (hard to parse)
   output=$(node project-intel.mjs search "term")

   # ✅ Good (JSON parsing)
   output=$(node project-intel.mjs search "term" --json)
   ```

5. **Don't use report without --focus**
   ```bash
   # ❌ Bad (10,000+ bytes output)
   node project-intel.mjs report

   # ✅ Good (focused analysis)
   node project-intel.mjs report --focus components/ui
   ```

---

## Token Efficiency Metrics

### Real Examples from the-fountain-studio

| Workflow | Without Intel (Read-First) | With Intel (Query-First) | Savings |
|----------|----------------------------|--------------------------|---------|
| Find booking feature | Read 5 files (25KB) | `search` + `investigate` (500 bytes) | **98.0%** |
| Debug scrollToSection | Read 3 files (15KB) | `debug` + `summarize` (400 bytes) | **97.3%** |
| Check cn() usage | Read 18 files (90KB) | `importers` + `metrics` (300 bytes) | **99.7%** |
| Understand structure | Read all files (500KB) | `stats` + `tree` (500 bytes) | **99.9%** |
| Plan new modal | Read 19 UI files (95KB) | `search` + `investigate` (750 bytes) | **99.2%** |
| Code quality audit | Read 84 files (420KB) | `dead` + `sanitize` + `metrics` (3KB) | **99.3%** |

**Average Token Savings Across Workflows:** 98.9%

### Why It Works

**PROJECT_INDEX.json Structure:**
- **File metadata** (language, location, size)
- **Symbol exports** (functions, classes, types)
- **Call graph** (who calls what)
- **Import graph** (who imports what)
- **Documentation index** (markdown file locations)

**Query Cost:** 50-500 bytes per command
**File Read Cost:** 5,000-100,000 bytes
**Ratio:** 1:100 to 1:200

---

## Summary

**project-intel.mjs is a 17-command intelligence toolkit** for codebase exploration:

**Commands by Category:**
- **Overview** (2): stats, tree
- **Search** (3): search, investigate, docs
- **Dependencies** (3): imports, importers, map-imports
- **Call Graph** (3): callers, callees, trace
- **Quality** (2): dead, sanitize
- **Analysis** (4): summarize, debug, metrics, report

**Key Innovation:** Query lightweight indices (1-2% tokens) before reading files (100% tokens) → **80-99% token savings**.

**Primary Use Case:** Intelligence-first AI agent workflows where understanding project structure before file reads enables efficient, targeted exploration.

**Golden Rule:** Always query → summarize → then read

---

**Next Steps:**
1. Run `node project-intel.mjs stats --json` in your new codebase
2. Follow the 3-minute onboarding workflow
3. Use decision trees to pick the right command
4. Measure your token savings

**Happy exploring! 🚀**

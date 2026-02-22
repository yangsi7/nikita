# Nikita Project Intelligence Report

**Generated**: 2026-02-22 | **Index**: 2026-02-22T02:56:46 | **Source**: PROJECT_INDEX.json
**Scope**: 778 files, 5,885 dependency edges, 12,179 call graph entries, 345 parsed sources

---

## 1. Project Overview

```
NIKITA_PROJECT [root: .]
├─ [stats] 778 files / 278 directories
│  ├─ [py] 624 Python source files
│  ├─ [ts] 145 TypeScript source files
│  ├─ [sh] 2 Shell scripts
│  ├─ [md] 477 Markdown documents
│  └─ [listed] 7 (5 json, 1 css, 1 shell)
├─ [parsed] 345 fully-analyzed source files
│  ├─ [.f] 345 entries (symbols + type)
│  ├─ [.deps] 682 entries (imports graph) — 5,885 total edges
│  └─ [.g] 12,179 call graph entries
└─ [staleness] Index current as of 2026-02-22T02:56:46
```

---

## 2. Architecture Map

```
NIKITA_SYSTEM [type: AI girlfriend simulation game]
│
├─ BACKEND (Python 3.12 / FastAPI / Cloud Run)
│  │
│  ├─ nikita/agents/ [33 files] [role: AI agent layer]
│  │  ├─ text/ (9 files) — Pydantic AI text agent, handler, history, token budget
│  │  ├─ voice/ (16 files) — ElevenLabs voice agent, server tools, models
│  │  └─ psyche/ (6 files) — Psyche analysis agent (deep/quick)
│  │  └─ [ext_deps: 29 unique] → config, conflicts, context, db(12 repos),
│  │     emotional_state, engine, life_simulation, memory, onboarding, platforms, utils
│  │
│  ├─ nikita/api/ [16 files] [role: integration hub — 72 ext deps]
│  │  ├─ main.py — FastAPI app entry point (create_app)
│  │  ├─ routes/ (7 files) — admin, admin_debug, onboarding, portal, tasks, telegram, voice
│  │  ├─ schemas/ (4 files) — admin, admin_debug + others
│  │  ├─ dependencies/ (4 files) — error_logging + DI
│  │  └─ middleware/ — request middleware
│  │  └─ [ext_deps: 72] → ALL subsystems (widest coupling surface)
│  │
│  ├─ nikita/engine/ [7 files] [role: game mechanics core]
│  │  ├─ constants.py — chapters, thresholds (55-75%), decay rates (0.8-0.2/hr)
│  │  ├─ chapters/ — boss encounters, judgment, phase_manager, prompts
│  │  ├─ engagement/ — calculator, detection, models, recovery, state_machine
│  │  ├─ scoring/ — analyzer, calculator, models, service
│  │  ├─ decay/ — calculator, models, processor
│  │  └─ vice/ — analyzer, boundaries, injector, models, scorer, service
│  │  └─ [ext_deps: 11] → config, conflicts(3), db.database, db.repos(score_history, user, vice)
│  │
│  ├─ nikita/pipeline/ [2 indexed, 14 in deps] [role: 9-stage async orchestrator]
│  │  ├─ orchestrator.py — main pipeline entry
│  │  ├─ models.py — pipeline data models
│  │  └─ stages/ — base, conflict, emotional, extraction, game_state, life_sim,
│  │     memory_update, persistence, prompt_builder, summary, touchpoint
│  │  └─ [ext_deps: 23] → conflicts, context, db.repos(7), emotional_state,
│  │     engine.constants, life_simulation, memory, touchpoints, utils
│  │
│  ├─ nikita/db/ [15 files] [role: data layer — 3 ext deps]
│  │  ├─ database.py — async session factory
│  │  ├─ dependencies.py — DI (10 symbols)
│  │  ├─ transactions.py — atomic() wrapper
│  │  ├─ models/ — user, telegram_link, base, scheduled_touchpoint, + more
│  │  └─ migrations/ (9 versions)
│  │  └─ [ext_deps: 3] → config.settings, life_simulation.arcs, life_simulation.social_generator
│  │
│  ├─ nikita/memory/ [1 file] [role: pgVector memory — 3 ext deps]
│  │  └─ supabase_memory.py — SupabaseMemory (search, add_fact, dedup)
│  │  └─ [ext_deps: 3] → config.settings, db.database, db.repos.memory_fact_repository
│  │
│  ├─ nikita/platforms/ [4 indexed] [role: Telegram platform — 36 ext deps]
│  │  └─ telegram/ — bot, delivery, onboarding/handler, rate_limiter
│  │  └─ [ext_deps: 36] → agents, config, conflicts, db.repos(9), engine(chapters,
│  │     engagement, scoring, constants), services(3), text_patterns
│  │
│  ├─ nikita/conflicts/ [9 files] [role: Gottman conflict system]
│  │  ├─ breakup, escalation, generator, migration, models, persistence, resolution, store
│  │  └─ [ext_deps: 3] → config.settings, db.models.user, emotional_state.models
│  │
│  ├─ nikita/life_simulation/ [10 files] [role: Nikita's inner life — 2 ext deps]
│  │  ├─ arcs, entity_manager, event_generator, models, mood_calculator
│  │  ├─ narrative_manager, psychology_mapper, simulator, social_generator, store
│  │  └─ [ext_deps: 2] → config.settings, db.database
│  │
│  ├─ nikita/emotional_state/ [4 files] [role: emotional state tracking — 1 ext dep]
│  │  └─ [ext_deps: 1] → db.database
│  │
│  ├─ nikita/touchpoints/ [5 files] [role: scheduled engagement — 6 ext deps]
│  │  └─ [ext_deps: 6] → config.settings, db.models.scheduled_touchpoint,
│  │     db.repos.user_repository, emotional_state(2), platforms.telegram.bot
│  │
│  ├─ nikita/onboarding/ [4 files] [role: voice onboarding flow]
│  │  └─ handoff, meta_nikita, preference_config, profile_collector
│  │
│  ├─ nikita/config/ [5 files] [role: settings & enums]
│  │  └─ settings.py (Pydantic), enums, elevenlabs, yaml loaders
│  │
│  ├─ nikita/context/ [5 files] [role: legacy context utils — partial]
│  │  └─ logging, session_detector, store, utils/token_counter, validation
│  │
│  ├─ nikita/text_patterns/ [1 file] [role: pattern matching]
│  │
│  └─ nikita/utils/ [1 file] [role: shared utilities]
│     └─ nikita_state.py (7 symbols)
│
├─ FRONTEND (Next.js 16 / React 19 / shadcn/ui)
│  │
│  └─ portal/ [134 files]
│     ├─ sr/app/ (28 files) — player + admin pages
│     ├─ sr/components/ (79 files) — UI components (shadcn + custom)
│     ├─ sr/hooks/ (25 files) — React hooks (TanStack Query wrappers)
│     ├─ e2e/ (1 file) — Playwright fixtures
│     └─ middleware.ts — auth routing
│
└─ TESTS [320 files in .deps index]
   ├─ tests/agents/ (53 files)
   ├─ tests/engine/ (46 files)
   ├─ tests/db/ (30 files)
   ├─ tests/api/ (29 files)
   ├─ tests/e2e/ (28 files)
   ├─ tests/conflicts/ (22 files)
   ├─ tests/pipeline/ (21 files)
   ├─ tests/platforms/ (14 files)
   ├─ tests/onboarding/ (10 files)
   ├─ tests/integration/ (6 files)
   ├─ tests/behavioral/ (5 files)
   ├─ tests/config/ (5 files)
   ├─ tests/context/ (5 files)
   └─ tests/memory/ (1 file)
```

---

## 3. Dependency Topology

### 3.1 Most-Depended-On Modules (Risk Centers)

```
RISK_CENTERS [type: reverse-dependency ranking, internal only]
│
├─ [103 importers] nikita.engine.chapters.boss [! CRITICAL]
│  └─ Any change ripples to 103 files
├─ [ 80 importers] nikita.config.enums [! CRITICAL]
├─ [ 80 importers] nikita.db.repositories.user_repository [! CRITICAL]
├─ [ 70 importers] nikita.agents.text.agent [HIGH]
├─ [ 67 importers] nikita.config.settings [HIGH]
├─ [ 66 importers] nikita.db.database [HIGH]
├─ [ 65 importers] nikita.db.models.user [HIGH]
├─ [ 70 importers] @/lib/utils (portal) [HIGH — TS]
└─ Third-party risk:
   ├─ [324] uuid
   ├─ [295] pytest
   ├─ [290] datetime
   ├─ [217] unittest.mock
   ├─ [192] typing
   ├─ [129] decimal
   ├─ [ 97] logging
   ├─ [ 86] sqlalchemy
   └─ [ 81] sqlalchemy.ext.asyncio
```

### 3.2 Most-Importing Files (Coupling Hotspots)

```
COUPLING_HOTSPOTS [type: fan-in ranking]
│
├─ PRODUCTION FILES
│  ├─ [51 deps] nikita/platforms/telegram/message_handler.py [! HIGHEST]
│  ├─ [42 deps] nikita/api/routes/tasks.py
│  ├─ [37 deps] nikita/api/routes/admin.py
│  ├─ [37 deps] nikita/api/routes/admin_debug.py
│  └─ [35 deps] nikita/agents/voice/server_tools.py
│
└─ TEST FILES (naturally high — mocking all deps)
   ├─ [55 deps] tests/pipeline/test_stages.py
   ├─ [54 deps] tests/engine/engagement/test_calculator.py
   ├─ [52 deps] tests/engine/engagement/test_detection.py
   └─ [49 deps] tests/db/repositories/test_user_repository.py
```

### 3.3 Subsystem External Dependency Count

```
DEPENDENCY_FLOW [type: external dep count per subsystem]
│
│   ┌──────────────────────────────────────────────────┐
│   │              API (72 ext deps)                    │
│   │         Integration Hub — touches ALL             │
│   └──────┬──────┬──────┬──────┬──────┬───────────────┘
│          ↓      ↓      ↓      ↓      ↓
│   ┌──────┴──┐ ┌─┴────┐ ┌┴─────┐ ┌───┴────┐ ┌───────────┐
│   │PLATFORMS│ │AGENTS│ │PIPE- │ │ENGINE  │ │TOUCHPOINTS│
│   │(36)     │ │(29)  │ │LINE  │ │(11)    │ │(6)        │
│   └────┬────┘ └──┬───┘ │(23)  │ └───┬────┘ └───────────┘
│        │         │      └──┬───┘     │
│        ↓         ↓         ↓         ↓
│   ┌────┴─────────┴─────────┴─────────┴────┐
│   │   CONFLICTS(3)  LIFE_SIM(2)  EMO(1)   │
│   │   MEMORY(3)     DB(3)     CONFIG(0)    │
│   │           Foundation Layer              │
│   └────────────────────────────────────────┘
```

---

## 4. Call Graph Intelligence

### 4.1 Highest Fan-Out Functions (Most Callees)

```
FAN_OUT [type: functions calling most other functions]
│
├─ [6 callees] scripts/configure_meta_nikita_tools.py:main
├─ [5 callees] nikita/agents/text/agent.py:_create_nikita_agent [! production]
├─ [5 callees] nikita/db/transactions.py:atomic [! production]
├─ [5 callees] scripts/configure_nikita_tools.py:main
├─ [4 callees] nikita/api/main.py:create_app [! production]
├─ [4 callees] portal/sr/app/dashboard/nikita/day/page.tsx:NikitaDayPage
├─ [3 callees] nikita/agents/text/agent.py:generate_response
├─ [3 callees] nikita/api/routes/tasks.py:_generate_summary_with_llm
├─ [3 callees] nikita/engine/engagement/detection.py:analyze_neediness
├─ [3 callees] nikita/engine/engagement/detection.py:analyze_distraction
└─ [observation] Call graph is flat — no extreme fan-out (max 6)
```

### 4.2 Call Graph Statistics

```
CALL_GRAPH_META
├─ Total entries: 12,179
├─ Unique callees: 2,427
├─ Defined functions (.f): ~861
├─ Functions never called (static): ~738
│  └─ [note] Many are entry points, API handlers, UI components, test helpers
│     invoked dynamically — not true dead code
└─ Test inflation: Test parametrization/fixtures dominate caller counts
   └─ Top callees show 159-208 references from test expansion
```

### 4.3 Dead Code Candidates (Require Investigation)

```
DEAD_CODE_CANDIDATES [type: functions defined but never statically called]
│
├─ [? needs-investigation] Production functions
│  ├─ _generate_response — may be dynamic dispatch
│  ├─ _get_chapter_behaviors — possibly invoked via dict lookup
│  ├─ _get_nikita_agent_for_user — possibly route handler helper
│  ├─ _create_score_analyzer_agent — possibly lazy-init
│  └─ _get_processor_instance — possibly factory pattern
│
├─ [✓ expected] Test helpers (_make_* pattern)
│  ├─ _make_context, _make_details, _make_event, _make_conv_repo_mock
│  ├─ _make_mock_repo, _make_orchestrator, _make_server_handler
│  └─ _make_settings — all test class methods, not tracked by static analysis
│
└─ [! genuine candidates]
   ├─ _deprecation_warning — may be removable
   ├─ __getattr__ — module-level dynamic dispatch
   └─ _fake_repair_analysis — test fixture, possibly orphaned
```

---

## 5. Cross-Cutting Concerns

### 5.1 Circular Dependency Analysis

```
CIRCULAR_DEPS [type: bidirectional import check]
│
├─ engine ↔ pipeline: [✓ CLEAN — unidirectional]
│  ├─ pipeline → engine: nikita.engine.constants (read-only)
│  └─ engine → pipeline: NONE
│
├─ agents ↔ memory: [✓ CLEAN — unidirectional]
│  ├─ agents → memory: nikita.memory, nikita.memory.supabase_memory
│  └─ memory → agents: NONE
│
├─ api ↔ engine: [✓ CLEAN — unidirectional]
│  ├─ api → engine: engine.constants, engine.decay.processor, engine.scoring.models
│  └─ engine → api: NONE
│
└─ VERDICT: No circular dependencies detected across major module pairs
```

### 5.2 Module Boundary Violations

```
BOUNDARY_VIOLATIONS [type: non-stdlib, non-nikita imports in core modules]
│
├─ PIPELINE external dependencies
│  ├─ [✓ acceptable] pydantic — data models
│  ├─ [✓ acceptable] structlog — structured logging
│  ├─ [✓ acceptable] jinja2 — prompt templating
│  ├─ [? concern] pydantic_ai — direct LLM calls from pipeline
│  ├─ [? concern] pydantic_ai.models.anthropic — model instantiation in pipeline
│  ├─ [? concern] sqlalchemy.ext.asyncio — direct DB session access
│  └─ [? concern] importlib — dynamic module loading
│
├─ ENGINE external dependencies
│  ├─ [✓ acceptable] pydantic — data models
│  ├─ [✓ expected] pydantic_ai — scoring analyzer + engagement detection agents
│  └─ [? concern] sqlalchemy.ext.asyncio — engine touching DB sessions directly
│
└─ SUMMARY
   ├─ sqlalchemy.ext.asyncio in engine + pipeline — both bypass repository layer
   │  └─ [recommendation] Audit which files; push session management to API/DI layer
   ├─ pydantic_ai in pipeline — by design for prompt_builder stage
   └─ importlib in pipeline — investigate if avoidable
```

---

## 6. Coverage Analysis

### 6.1 Test-to-Source Ratios

```
COVERAGE_RATIOS [type: test files / source files per subsystem]
│
├─ [★★★] pipeline:    10.5:1  (21 tests / 2 source) — highest coverage density
├─ [★★★] engine:       6.5:1  (46 tests / 7 source) — game core well-tested
├─ [★★☆] platforms:    3.5:1  (14 tests / 4 source) — good
├─ [★★☆] onboarding:   2.5:1  (10 tests / 4 source) — good
├─ [★★☆] conflicts:    2.4:1  (22 tests / 9 source) — good
├─ [★★☆] db:           2.0:1  (30 tests / 15 source) — solid
├─ [★★☆] api:          1.8:1  (29 tests / 16 source) — adequate
├─ [★☆☆] agents:       1.6:1  (53 tests / 33 source) — below avg for complexity
├─ [★☆☆] config:       1.0:1  (5 tests / 5 source) — minimal
├─ [★☆☆] context:      1.0:1  (5 tests / 5 source) — minimal
├─ [★☆☆] memory:       1.0:1  (1 test / 1 source) — [! lowest ratio]
│
├─ [e2e] 28 test files — integration/journey coverage
├─ [integration] 6 test files — cross-module integration
├─ [behavioral] 5 test files — behavior-driven tests
│
├─ TOTAL: 320 test files / 345 source files = 0.93:1
│
└─ GAPS
   ├─ [! concern] memory: only 1 test file for supabase_memory.py
   ├─ [! concern] agents: 1.6:1 ratio despite 33 files (widest dep surface)
   ├─ [? gap] portal: 0 test files in index (134 source files)
   │  └─ 1 e2e fixture only; no unit/component tests indexed
   ├─ [? gap] life_simulation: 10 source files, test count unknown
   ├─ [? gap] emotional_state: 4 source files, test count unknown
   └─ [? gap] touchpoints: 5 source files, test count unknown
```

### 6.2 Widest Interfaces (Symbol Count)

```
INTERFACE_SIZE [type: files with most exported symbols]
│
├─ [40 syms] nikita/api/schemas/admin_debug.py [! largest interface]
├─ [37 syms] nikita/api/schemas/admin.py
├─ [33 syms] nikita/api/routes/admin.py
├─ [25 syms] portal/sr/components/ui/sidebar.tsx
├─ [23 syms] nikita/api/routes/portal.py
├─ [20 syms] nikita/api/routes/admin_debug.py
├─ [16 syms] nikita/api/routes/tasks.py
├─ [15 syms] portal/sr/components/ui/dropdown-menu.tsx
├─ [13 syms] nikita/api/routes/telegram.py
├─ [12 syms] nikita/agents/voice/models.py
│
└─ [observation] API admin layer dominates — consider splitting schemas
```

---

## 7. Health Indicators

```
HEALTH_DASHBOARD
│
├─ ARCHITECTURE
│  ├─ [✓] Circular dependencies: NONE detected (3 pairs checked)
│  ├─ [✓] Layer separation: DB(3) → ENGINE(11) → PIPELINE(23) → API(72)
│  ├─ [✓] Memory isolation: 3 ext deps only (cleanest subsystem)
│  ├─ [✓] Life simulation isolation: 2 ext deps (self-contained world sim)
│  ├─ [?] sqlalchemy.ext.asyncio leaks into engine + pipeline (bypass repos)
│  └─ [?] API has 72 external deps (god-module risk, but expected for integration hub)
│
├─ COUPLING
│  ├─ [!] engine.chapters.boss: 103 importers — highest blast radius
│  ├─ [!] config.enums + db.repos.user_repository: 80 importers each
│  ├─ [!] message_handler.py: 51 deps — most coupled production file
│  └─ [✓] Foundation modules (db, memory, config) have minimal outward coupling
│
├─ CALL GRAPH
│  ├─ [✓] Flat call graph — max fan-out = 6 (no God functions)
│  ├─ [✓] 12,179 edges across 345 files — average 35 edges/file
│  ├─ [?] ~738 unreferenced functions (mostly expected: handlers, test helpers)
│  └─ [?] Test parametrization inflates caller counts (159-208 range)
│
├─ TESTING
│  ├─ [✓] 320 test files / 345 source files (0.93:1 overall)
│  ├─ [✓] Engine + Pipeline heavily tested (6.5:1 and 10.5:1)
│  ├─ [!] Memory subsystem: 1:1 ratio despite critical pgVector operations
│  ├─ [!] Agents: 1.6:1 ratio despite highest file count + widest deps
│  └─ [!] Portal: no unit/component tests indexed
│
└─ INDEX QUALITY
   ├─ [✓] 345 files fully parsed with symbols + deps
   ├─ [?] Tests in .deps but not .f — symbol extraction skipped for tests
   ├─ [?] Portal paths use "sr/" prefix (not "src/") — possible path truncation
   └─ [✓] 12,179 call graph entries provide good static analysis coverage
```

---

## 8. Actionable Insights

```
RECOMMENDATIONS [type: prioritized by impact × effort]
│
├─ P0: CRITICAL (high impact, moderate effort)
│  │
│  ├─ [1] Increase memory subsystem test coverage
│  │  ├─ Current: 1 test file for supabase_memory.py
│  │  ├─ Risk: pgVector search, dedup, and fact storage are critical paths
│  │  └─ Action: Add tests for edge cases (empty results, dedup collision, embedding failures)
│  │
│  ├─ [2] Reduce message_handler.py coupling (51 deps)
│  │  ├─ Most coupled production file in the entire codebase
│  │  ├─ Risk: Any refactor touches 51 imports; hard to test in isolation
│  │  └─ Action: Extract processing steps into smaller, focused modules
│  │
│  └─ [3] Protect engine.chapters.boss API stability
│     ├─ 103 importers — highest blast radius of any first-party module
│     ├─ Risk: Any signature change cascades to 103 files
│     └─ Action: Freeze public API, add deprecation layer for changes
│
├─ P1: HIGH (moderate impact, low-moderate effort)
│  │
│  ├─ [4] Audit sqlalchemy.ext.asyncio usage in engine + pipeline
│  │  ├─ Both modules bypass the repository abstraction layer
│  │  └─ Action: Identify specific files; push session handling to DI/dependency injection
│  │
│  ├─ [5] Add portal component/unit tests
│  │  ├─ 134 source files with 0 indexed tests
│  │  └─ Action: Add Vitest + React Testing Library for critical components
│  │
│  ├─ [6] Boost agents test coverage
│  │  ├─ 1.6:1 ratio despite 33 files and 29 external deps
│  │  ├─ Widest dependency surface increases defect risk
│  │  └─ Action: Prioritize voice/server_tools.py and psyche/ agent tests
│  │
│  └─ [7] Investigate dead code candidates
│     ├─ _generate_response, _get_chapter_behaviors, _get_nikita_agent_for_user
│     └─ Action: Trace dynamic dispatch; remove if truly unused
│
├─ P2: MEDIUM (lower urgency, good housekeeping)
│  │
│  ├─ [8] Consider splitting admin schemas
│  │  ├─ admin_debug.py (40 symbols) + admin.py (37 symbols) = widest interfaces
│  │  └─ Action: Group by domain (user admin, pipeline admin, debug tools)
│  │
│  ├─ [9] Re-index with test symbol extraction
│  │  ├─ Tests appear in .deps but not .f — incomplete static analysis
│  │  └─ Action: Update indexer to parse test symbols for dead-code detection
│  │
│  └─ [10] Add life_simulation, emotional_state, touchpoints test metrics
│     ├─ These modules (19 source files) have unknown test coverage
│     └─ Action: Verify test counts on disk; add to CI coverage reporting
│
└─ P3: LOW (nice-to-have)
   │
   ├─ [11] Investigate importlib usage in pipeline
   │  └─ Dynamic imports reduce static analyzability
   │
   └─ [12] Portal path normalization in index
      └─ Paths use "sr/" instead of "src/" — confirm if intentional truncation
```

---

## Evidence Log

```
[query] jq '.stats' PROJECT_INDEX.json → 778 files, 278 dirs
[query] jq '.deps | to_entries | length' → 682 dep entries, 5,885 edges
[query] jq '.g | length' → 12,179 call graph entries
[query] jq '.f | to_entries | length' → 345 parsed files
[query] jq coupling top-20 → message_handler.py (51), test_stages.py (55)
[query] jq risk top-20 → engine.chapters.boss (103), config.enums (80)
[query] jq subsystem engine → 7 files, 11 ext deps
[query] jq subsystem pipeline → 2 indexed, 23 ext deps
[query] jq subsystem agents → 33 files, 29 ext deps
[query] jq subsystem memory → 1 file, 3 ext deps
[query] jq subsystem api → 16 files, 72 ext deps
[query] jq subsystem platforms → 4 files, 36 ext deps
[query] jq subsystem db → 15 files, 3 ext deps
[query] jq circular engine↔pipeline → CLEAN
[query] jq circular agents↔memory → CLEAN
[query] jq circular api↔engine → CLEAN
[query] jq boundary pipeline → 7 non-stdlib imports (jinja2, pydantic_ai, sqlalchemy, etc.)
[query] jq boundary engine → 3 non-stdlib imports (pydantic, pydantic_ai, sqlalchemy)
[query] jq test counts (from .deps) → 320 test files
[query] jq portal structure → 134 files (28 app, 79 components, 25 hooks)
[query] jq additional subsystems → conflicts(9), life_sim(10), emotional(4), touchpoints(5)
```

# Nikita Knowledge Transfer Documentation

```yaml
context_priority: critical
audience: ai_agents
last_updated: 2026-02-03
version: 1.0.0
total_docs: 15
estimated_lines: 8000-10000
```

## Purpose

This documentation set enables complete AI-to-AI knowledge transfer for the Nikita project. Each document is optimized for Claude Code consumption with:
- **file:line references** for code navigation
- **ASCII diagrams** for architecture visualization
- **NEEDS RETHINKING markers** for technical debt
- **Quick entry points** with rg/fd commands

---

## Quick Entry Points

### Find Key Files Fast

```bash
# Core entry points
rg "class ContextEngine" --type py -l              # Context engine
rg "class MetaPromptService" --type py -l          # Prompt generation
rg "class NikitaMemory" --type py -l               # Memory client
rg "class PostProcessor" --type py -l              # Pipeline orchestration
rg "class MessageHandler" --type py -l             # Telegram handler

# Configuration
fd "settings.py" --type f                          # Environment config
fd "constants.py" --type f                         # Game constants
fd "config_data" --type d                          # YAML configs

# Database
fd "models" --type d nikita/db                     # SQLAlchemy models
fd "repositories" --type d nikita/db              # Repository pattern

# Tests
fd "conftest.py" --type f tests/                  # Test fixtures
rg "NullPool" --type py tests/                    # Async isolation
```

### Understand Architecture Fast

```bash
# Voice vs Text agent comparison
diff <(rg "def get_context" nikita/agents/voice/) <(rg "_load_context" nikita/meta_prompts/)

# Pipeline stages
rg "class.*Stage" nikita/context/stages/ -l

# Game mechanics
rg "CHAPTER_.*THRESHOLD" --type py
rg "DECAY_RATE" --type py
```

---

## Document Index

### Core Architecture (Start Here)

| Doc | Lines | Purpose | Key Concepts |
|-----|-------|---------|--------------|
| [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) | 500 | Product concept, tech stack | C1 diagram, product vision |
| [USER_JOURNEY.md](USER_JOURNEY.md) | 600 | Game flow end-to-end | ASCII flowchart, states |
| [CONTEXT_ENGINE.md](CONTEXT_ENGINE.md) | 1100 | **CRITICAL** - Prompt assembly | 8 collectors, 115 fields |

### Data & Storage

| Doc | Lines | Purpose | Key Concepts |
|-----|-------|---------|--------------|
| [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) | 500 | Supabase + Neo4j schema | 22 tables, 3 graphs, RLS |
| [PIPELINE_STAGES.md](PIPELINE_STAGES.md) | 900 | Async post-processing | 11 stages, circuit breakers |

### Game Mechanics

| Doc | Lines | Purpose | Key Concepts |
|-----|-------|---------|--------------|
| [GAME_ENGINE_MECHANICS.md](GAME_ENGINE_MECHANICS.md) | 1100 | Scoring, chapters, decay | 4 metrics, boss fights |

### Integrations

| Doc | Lines | Purpose | Key Concepts |
|-----|-------|---------|--------------|
| [INTEGRATIONS.md](INTEGRATIONS.md) | 650 | External services | Telegram, ElevenLabs, Graphiti |
| [VOICE_IMPLEMENTATION.md](VOICE_IMPLEMENTATION.md) | 650 | Voice agent deep-dive | Server tools, bypasses |

### Authentication & Onboarding

| Doc | Lines | Purpose | Key Concepts |
|-----|-------|---------|--------------|
| [AUTHENTICATION.md](AUTHENTICATION.md) | 400 | Auth flows | OTP, JWT, phone linking |
| [ONBOARDING.md](ONBOARDING.md) | 550 | First-time user experience | Voice/text paths, Meta-Nikita |

### Engineering Practices

| Doc | Lines | Purpose | Key Concepts |
|-----|-------|---------|--------------|
| [TESTING_STRATEGY.md](TESTING_STRATEGY.md) | 550 | Test patterns | NullPool, fixtures, chaos |
| [DEPLOYMENT_OPERATIONS.md](DEPLOYMENT_OPERATIONS.md) | 650 | Cloud Run ops | Env vars, migrations |

### Technical Debt & Alternatives

| Doc | Lines | Purpose | Key Concepts |
|-----|-------|---------|--------------|
| [ANTI_PATTERNS.md](ANTI_PATTERNS.md) | 400 | What NOT to do | Lessons learned |
| [ARCHITECTURE_ALTERNATIVES.md](ARCHITECTURE_ALTERNATIVES.md) | 550 | Research findings | Trade-offs, future options |

---

## Reading Order

### For New AI Agents

1. **PROJECT_OVERVIEW.md** - Understand what Nikita is
2. **USER_JOURNEY.md** - See the game flow
3. **CONTEXT_ENGINE.md** - Learn the core prompt system
4. **DATABASE_SCHEMA.md** - Understand data model

### For Feature Implementation

1. **CONTEXT_ENGINE.md** - How context flows to prompts
2. **PIPELINE_STAGES.md** - Post-processing architecture
3. **GAME_ENGINE_MECHANICS.md** - Scoring and progression
4. **TESTING_STRATEGY.md** - How to test changes

### For Bug Investigation

1. **ANTI_PATTERNS.md** - Known pitfalls
2. **VOICE_IMPLEMENTATION.md** - Voice-specific issues
3. **INTEGRATIONS.md** - External service failures
4. **DEPLOYMENT_OPERATIONS.md** - Production debugging

### For Architecture Decisions

1. **ARCHITECTURE_ALTERNATIVES.md** - Research and trade-offs
2. **CONTEXT_ENGINE.md** - Current design rationale
3. **ANTI_PATTERNS.md** - Why things are the way they are

---

## Key Architectural Decisions

### Voice Bypasses ContextEngine

**CRITICAL**: Voice agent does NOT use ContextEngine. It has separate server tools with 2s timeouts.

```
Text Path:  Telegram → MessageHandler → ContextEngine → PromptGenerator → Claude
Voice Path: ElevenLabs → server_tools.py (get_context/get_memory) → Direct queries
```

See: [VOICE_IMPLEMENTATION.md](VOICE_IMPLEMENTATION.md#architecture-bypass)

### Three Knowledge Graphs

Graphiti maintains 3 separate Neo4j graphs:
- `nikita_graph` - Nikita's life events, personality
- `user_graph` - User's facts, preferences
- `relationship_graph` - Shared memories, conversations

See: [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md#neo4j-graphs)

### Pipeline Critical vs Non-Critical

11 stages with different failure handling:
- **Critical** (abort on failure): Ingestion, Extraction, Finalization
- **Non-critical** (skip on failure): All others

See: [PIPELINE_STAGES.md](PIPELINE_STAGES.md#failure-handling)

---

## Cross-Reference Quick Links

### By Component

| Component | Primary Doc | Related Docs |
|-----------|-------------|--------------|
| ContextEngine | CONTEXT_ENGINE.md | PIPELINE_STAGES.md, VOICE_IMPLEMENTATION.md |
| PostProcessor | PIPELINE_STAGES.md | CONTEXT_ENGINE.md, TESTING_STRATEGY.md |
| MessageHandler | INTEGRATIONS.md | AUTHENTICATION.md, ONBOARDING.md |
| Scoring | GAME_ENGINE_MECHANICS.md | CONTEXT_ENGINE.md |
| Voice | VOICE_IMPLEMENTATION.md | ONBOARDING.md, INTEGRATIONS.md |

### By File Path

| Path Pattern | Doc |
|--------------|-----|
| `nikita/context_engine/` | CONTEXT_ENGINE.md |
| `nikita/context/stages/` | PIPELINE_STAGES.md |
| `nikita/agents/voice/` | VOICE_IMPLEMENTATION.md |
| `nikita/engine/` | GAME_ENGINE_MECHANICS.md |
| `nikita/db/` | DATABASE_SCHEMA.md |
| `nikita/platforms/telegram/` | INTEGRATIONS.md |
| `nikita/onboarding/` | ONBOARDING.md |
| `tests/` | TESTING_STRATEGY.md |

---

## NEEDS RETHINKING Summary

Issues marked across all docs:

| Area | Issue | Doc |
|------|-------|-----|
| Voice-Text Parity | Voice bypasses ContextEngine entirely | VOICE_IMPLEMENTATION.md |
| Graphiti Utility | 3 graphs stored but retrieval underutilized | DATABASE_SCHEMA.md |
| Neo4j Cold Start | 30-60s cold start impacts UX | DEPLOYMENT_OPERATIONS.md |
| Portal | Frontend needs redesign | PROJECT_OVERVIEW.md |
| Pipeline Timeouts | 45s total may be too aggressive | CONTEXT_ENGINE.md |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-02-03 | Initial 15-doc set from research agents |

---

## Maintenance Notes

### Updating These Docs

1. Run research agents to gather current state
2. Update specific doc with file:line references
3. Update this INDEX.md with new line counts
4. Increment version in YAML frontmatter

### Validation Commands

```bash
# Count total lines
wc -l docs/knowledge-transfer/*.md

# Count file:line references
rg -c ":\d+(-\d+)?" docs/knowledge-transfer/ | awk -F: '{sum+=$2} END {print sum}'

# Find outdated references
rg "NEEDS RETHINKING" docs/knowledge-transfer/
```

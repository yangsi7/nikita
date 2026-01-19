# Nikita: Don't Get Dumped

An AI girlfriend simulation game featuring dual-agent architecture (voice + text), temporal knowledge graphs for memory, and sophisticated game mechanics.

## Overview

You're dating a 25-year-old hacker who microdoses LSD, survives on black coffee and spite, and will dump your ass if you can't keep up.

- **Win**: Reach Chapter 5 (Established relationship) → Victory message
- **Lose**: Score hits 0% OR fail a boss 3 times → Game over

## Tech Stack

| Component | Technology |
|-----------|------------|
| **LLM** | Claude Sonnet 4.5 (Pydantic AI) |
| **Voice** | ElevenLabs Conversational AI 2.0 |
| **Database** | Supabase (PostgreSQL + pgVector + RLS) |
| **Knowledge Graphs** | Graphiti + Neo4j Aura (free tier, managed) |
| **Platform** | Telegram + Voice calls |
| **API** | FastAPI (Google Cloud Run, serverless) |
| **Scheduling** | pg_cron + Supabase Edge Functions |

## Project Structure

```
nikita/
├── agents/          # AI agents (voice + text)
│   └── tools/       # Shared agent tools
├── api/             # FastAPI application
│   ├── routes/      # API endpoints
│   ├── schemas/     # Pydantic request/response models
│   └── middleware/  # Auth, rate limiting
├── config/          # Settings and configuration
├── db/              # Database layer
│   ├── models/      # SQLAlchemy models
│   ├── repositories/# Data access patterns
│   └── migrations/  # Alembic migrations
├── engine/          # Game engine
│   ├── scoring/     # Score calculation
│   ├── chapters/    # Chapter progression
│   ├── decay/       # Daily decay system
│   ├── vice/        # Vice discovery
│   └── conflicts/   # Conflict handling
├── memory/          # Graphiti knowledge graphs
│   └── graphs/      # Graph definitions
├── meta_prompts/    # LLM-powered prompt generation (Claude Haiku)
├── platforms/       # Platform integrations
│   ├── telegram/    # Telegram bot
│   ├── voice/       # ElevenLabs integration
│   └── portal/      # Player stats dashboard
└── prompts/         # Prompt templates
```

## Quick Start

### Prerequisites

- Python 3.11+
- Supabase account (database + auth)
- Neo4j Aura account (free tier for knowledge graphs)
- ElevenLabs API key
- Anthropic API key
- OpenAI API key (for embeddings)
- Telegram bot token
- Google Cloud project (for Cloud Run deployment)

### Installation

```bash
# Clone repository
cd nikita

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or: .venv\Scripts\activate  # Windows

# Install dependencies
pip install -e ".[dev]"

# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys and configuration
```

### Running the API

```bash
# Development mode
python -m nikita.api.main

# Or with uvicorn directly
uvicorn nikita.api.main:app --reload
```

### Deployment (Cloud Run)

```bash
# Build and push Docker image
docker build -t gcr.io/YOUR_PROJECT/nikita-api .
docker push gcr.io/YOUR_PROJECT/nikita-api

# Deploy to Cloud Run
gcloud run deploy nikita-api \
  --image gcr.io/YOUR_PROJECT/nikita-api \
  --region us-central1 \
  --allow-unauthenticated
```

### Background Tasks

Background tasks run via **pg_cron** (Supabase scheduled jobs):
- Hourly decay calculation
- Daily summaries
- Memory cleanup

Configure via Supabase Dashboard → Database → Extensions → pg_cron.

## Game Mechanics

### Scoring System

- **Single composite score**: 0-100% (Relationship Health)
- **Hidden sub-metrics**: Intimacy (30%), Passion (25%), Trust (25%), Secureness (20%)

### Chapters

| Ch | Name | Days | Boss | Score to Unlock |
|----|------|------|------|-----------------|
| 1 | Curiosity | 1-14 | "Worth my time?" | Start |
| 2 | Intrigue | 15-35 | "Handle intensity?" | 55% |
| 3 | Investment | 36-70 | "Trust test" | 60% |
| 4 | Intimacy | 71-120 | "Vulnerability" | 65% |
| 5 | Established | 121+ | "Ultimate test" → WIN | 70% |

### Key Mechanics

- **3 boss attempts** per boss, then game over
- **Stage-dependent decay** (fragile early, stable late)
- **Clingy penalty** - too much contact hurts
- **Dynamic vice discovery** - system learns preferences

## Documentation

**Living Documentation System** - Diagram-first, AI-optimized, Current State vs Target Specs

### Quick Reference

| Topic | File | Description |
|-------|------|-------------|
| **Index** | [memory/README.md](memory/README.md) | Documentation hub |
| **Architecture** | [memory/architecture.md](memory/architecture.md) | System design, components, data flow |
| **Backend** | [memory/backend.md](memory/backend.md) | FastAPI routes, database, API patterns |
| **Game Mechanics** | [memory/game-mechanics.md](memory/game-mechanics.md) | Scoring, chapters, bosses, decay |
| **User Journeys** | [memory/user-journeys.md](memory/user-journeys.md) | Player flows from signup to victory |
| **Integrations** | [memory/integrations.md](memory/integrations.md) | ElevenLabs, Graphiti, Telegram, Supabase |

### Planning & Tasks

- **Master Plan**: [plans/master-plan.md](plans/master-plan.md) - Full technical architecture (Sections 1-20)
- **Master Todo**: [todos/master-todo.md](todos/master-todo.md) - Phase-organized implementation tasks

### Module Context (for AI agents)

- [nikita/CLAUDE.md](nikita/CLAUDE.md) - Package overview
- [nikita/api/CLAUDE.md](nikita/api/CLAUDE.md) - FastAPI patterns
- [nikita/db/CLAUDE.md](nikita/db/CLAUDE.md) - Database layer
- [nikita/engine/CLAUDE.md](nikita/engine/CLAUDE.md) - Game engine
- [nikita/memory/CLAUDE.md](nikita/memory/CLAUDE.md) - Knowledge graphs

## Development Status

**Phase 1: Core Infrastructure** ✅ COMPLETE
- [x] 45+ Python files created
- [x] Database models + repositories (SQLAlchemy)
- [x] Game constants defined (boss thresholds 55-75%, hourly decay)
- [x] Memory system (NikitaMemory + Graphiti + Neo4j Aura)
- [x] Configuration (all services)
- [x] Documentation system + 20 specs

**Phase 2: Telegram + API** ✅ COMPLETE
- [x] Pydantic AI text agent (8 files, 156 tests)
- [x] Telegram bot platform (7 files, 74 tests)
- [x] API infrastructure (FastAPI + routes)
- [x] Database repositories (7 repositories)
- [x] Cloud Run deployment (live)
- [x] OTP authentication flow with security hardening

**Phase 3: Configuration + Game Engine** ✅ COMPLETE
- [x] Configuration system (YAML + JSON schemas) - 89 tests
- [x] Engagement model (6 states) - 179 tests
- [x] Scoring calculator (LLM-based) - 60 tests
- [x] Context engineering (6-stage pipeline) - 50 tests
- [x] Decay system (pg_cron integration) - 52 tests
- [x] Chapter state machine + boss encounters - 142 tests
- [x] Vice discovery (8 categories) - 81 tests

**Phase 4: Voice Agent** ✅ COMPLETE (Jan 2026)
- [x] ElevenLabs Conversational AI 2.0 (14 modules)
- [x] Server tools: get_context, get_memory, score_turn, update_memory
- [x] Voice session management (inbound.py, service.py)
- [x] 186 tests, 5 API endpoints deployed

**Phase 5: Portal & Polish** ⚠️ IN PROGRESS (85%)
- [x] Next.js player portal (dashboard works)
- [x] Stats dashboard (score, chapter, progress)
- [x] Security hardening (webhook validation, rate limiting)
- [x] Admin monitoring (voice, text, prompts)
- [ ] Settings page polish (remaining 15%)

See [todos/master-todo.md](todos/master-todo.md) for detailed task breakdown.

## Specifications

All 20 specs have complete SDD artifacts (spec.md, plan.md, tasks.md, audit-report.md):

| # | Spec | Status |
|---|------|--------|
| 001-020 | Full specification set | ✅ Artifacts complete |

See `specs/` directory and `specs/SPEC_INVENTORY.md` for details.

## License

Private - All rights reserved.

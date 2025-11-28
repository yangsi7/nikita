# Nikita: Don't Get Dumped

An AI girlfriend simulation game featuring dual-agent architecture (voice + text), temporal knowledge graphs for memory, and sophisticated game mechanics.

## Overview

You're dating a 25-year-old hacker who microdoses LSD, survives on black coffee and spite, and will dump your ass if you can't keep up.

- **Win**: Reach Chapter 5 (Established relationship) → Victory message
- **Lose**: Score hits 0% OR fail a boss 3 times → Game over

## Tech Stack

| Component | Technology |
|-----------|------------|
| **LLM** | Claude Sonnet (Pydantic AI) |
| **Voice** | ElevenLabs Conversational AI 2.0 |
| **Database** | Supabase (PostgreSQL + pgVector) |
| **Knowledge Graphs** | Graphiti + FalkorDB |
| **Platform** | Telegram + Voice calls |
| **API** | FastAPI |
| **Task Queue** | Celery + Redis |

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
├── platforms/       # Platform integrations
│   ├── telegram/    # Telegram bot
│   ├── voice/       # ElevenLabs integration
│   └── portal/      # Player stats dashboard
├── prompts/         # Prompt templates
└── tasks/           # Celery background jobs
```

## Quick Start

### Prerequisites

- Python 3.11+
- Supabase account
- FalkorDB (local or cloud)
- ElevenLabs API key
- Anthropic API key
- OpenAI API key (for embeddings)
- Telegram bot token

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

### Running Background Tasks

```bash
# Start Celery worker
celery -A nikita.tasks worker --loglevel=info

# Start Celery beat (scheduler)
celery -A nikita.tasks beat --loglevel=info
```

## Game Mechanics

### Scoring System

- **Single composite score**: 0-100% (Relationship Health)
- **Hidden sub-metrics**: Intimacy (30%), Passion (25%), Trust (25%), Secureness (20%)

### Chapters

| Ch | Name | Days | Boss | Score to Unlock |
|----|------|------|------|-----------------|
| 1 | Curiosity | 1-14 | "Worth my time?" | Start |
| 2 | Intrigue | 15-35 | "Handle intensity?" | 60% |
| 3 | Investment | 36-70 | "Trust test" | 65% |
| 4 | Intimacy | 71-120 | "Vulnerability" | 70% |
| 5 | Established | 121+ | "Ultimate test" → WIN | 75% |

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

- **Master Plan**: [plan/master-plan.md](plan/master-plan.md) - Full technical architecture (Sections 1-20)
- **Master Todo**: [todo/master-todo.md](todo/master-todo.md) - Phase-organized implementation tasks

### Module Context (for AI agents)

- [nikita/CLAUDE.md](nikita/CLAUDE.md) - Package overview
- [nikita/api/CLAUDE.md](nikita/api/CLAUDE.md) - FastAPI patterns
- [nikita/db/CLAUDE.md](nikita/db/CLAUDE.md) - Database layer
- [nikita/engine/CLAUDE.md](nikita/engine/CLAUDE.md) - Game engine
- [nikita/memory/CLAUDE.md](nikita/memory/CLAUDE.md) - Knowledge graphs

## Development Status

**Phase 1: Core Infrastructure** ✅ COMPLETE (Week 1-2)
- [x] 39 Python files created
- [x] Database models (SQLAlchemy)
- [x] Game constants defined
- [x] Memory system (NikitaMemory + Graphiti)
- [x] Configuration (all services)
- [x] Documentation system

**Phase 2: Text Agent** ❌ TODO (Week 2-3)
- [ ] Pydantic AI text agent
- [ ] Telegram bot (aiogram)
- [ ] Agent tools (memory, scoring, context)
- [ ] Database repositories
- [ ] API routes

**Phase 3: Game Engine** ❌ TODO (Week 3-4)
- [ ] Scoring calculator (LLM-based)
- [ ] Chapter state machine
- [ ] Boss encounters
- [ ] Decay system (Celery)
- [ ] Vice discovery

**Phase 4: Voice Agent** ❌ TODO (Week 4-5)
- [ ] ElevenLabs integration
- [ ] Server tools
- [ ] Voice session management

**Phase 5: Portal & Polish** ❌ TODO (Week 5-6)
- [ ] Next.js player portal
- [ ] Stats dashboard
- [ ] Performance testing
- [ ] Security audit

See [todo/master-todo.md](todo/master-todo.md) for detailed task breakdown.

## License

Private - All rights reserved.

# Nikita: Don't Get Dumped

An AI girlfriend simulation game featuring dual-agent architecture (voice + text), pgVector semantic memory, and sophisticated game mechanics across 5 chapters.

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
| **Memory** | SupabaseMemory (pgVector semantic search) |
| **Portal** | Next.js 16 (Vercel) |
| **Platform** | Telegram + Voice calls |
| **API** | FastAPI (Google Cloud Run, serverless) |
| **Scheduling** | pg_cron + Supabase Edge Functions |

## Project Structure

```
nikita/
├── agents/          # AI agents (voice + text)
│   ├── text/        # Pydantic AI text agent (10 files, 243 tests)
│   └── voice/       # ElevenLabs voice agent (14 files, 186 tests)
├── api/             # FastAPI application
│   ├── routes/      # API endpoints (19 routes)
│   ├── schemas/     # Pydantic request/response models
│   └── middleware/   # Auth, rate limiting
├── config/          # Settings and configuration (Pydantic)
├── db/              # Database layer
│   ├── models/      # SQLAlchemy models
│   └── repositories/# Data access patterns (7 repos)
├── engine/          # Game engine
│   ├── scoring/     # Score calculation (4 metrics)
│   ├── chapters/    # Chapter progression + boss encounters
│   ├── decay/       # Daily decay system
│   ├── vice/        # Vice discovery (8 categories)
│   └── conflicts/   # Conflict handling
├── memory/          # SupabaseMemory (pgVector semantic search)
├── pipeline/        # Unified 10-stage async pipeline
├── touchpoints/     # Proactive outreach engine
├── notifications/   # Push notification service
├── platforms/       # Platform integrations
│   └── telegram/    # Telegram bot (webhook mode)
├── onboarding/      # Voice onboarding (Meta-Nikita agent)
└── prompts/         # Prompt templates (deprecated v1 fallback)

portal/              # Next.js 16 player + admin dashboard
supabase/            # Migrations (90 stubs) + reference DDL + Edge Functions
```

## Quick Start

### Prerequisites

- Python 3.12+
- Supabase account (database + auth)
- ElevenLabs API key
- Anthropic API key
- OpenAI API key (for embeddings)
- Telegram bot token
- Google Cloud project (for Cloud Run deployment)

### Installation

```bash
cd nikita

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys and configuration
```

### Running the API

```bash
# Development mode
uvicorn nikita.api.main:app --reload
```

### Deployment (Cloud Run)

```bash
# Source-based deploy (no Docker image needed)
gcloud run deploy nikita-api \
  --source . \
  --region us-central1 \
  --project gcp-transcribe-test \
  --allow-unauthenticated
```

### Portal Deployment (Vercel)

```bash
source ~/.nvm/nvm.sh && nvm use 22
cd portal && npm run build && vercel --prod
```

### Background Tasks

Background tasks run via **pg_cron** (7 active jobs):
- Hourly decay calculation
- Daily summaries + psyche batch
- Conversation post-processing (every minute)
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
- **Multi-phase boss encounters** — OPENING → RESOLUTION with PARTIAL (truce) outcome
- **Stage-dependent decay** (fragile early, stable late)
- **Clingy penalty** — too much contact hurts
- **Dynamic vice discovery** — system learns preferences
- **Push notifications** — decay warnings, chapter advances

## Documentation

### Quick Reference

| Topic | File | Description |
|-------|------|-------------|
| **Roadmap** | [ROADMAP.md](ROADMAP.md) | Spec status, metrics, backlog |
| **Architecture** | [memory/architecture.md](memory/architecture.md) | System design, data flow |
| **Backend** | [memory/backend.md](memory/backend.md) | FastAPI routes, database patterns |
| **Game Mechanics** | [memory/game-mechanics.md](memory/game-mechanics.md) | Scoring, chapters, bosses, decay |
| **User Journeys** | [memory/user-journeys.md](memory/user-journeys.md) | Player flows |
| **Integrations** | [memory/integrations.md](memory/integrations.md) | ElevenLabs, Telegram, Supabase |
| **Deployment** | [docs/deployment.md](docs/deployment.md) | URLs, commands, environments |
| **Schema** | [docs/reference/schema-reference.md](docs/reference/schema-reference.md) | 32-table reference |

### Module Context (for AI agents)

Each module has its own `CLAUDE.md` for AI-assisted development:
- [nikita/CLAUDE.md](nikita/CLAUDE.md) — Package overview
- [nikita/api/CLAUDE.md](nikita/api/CLAUDE.md) — FastAPI patterns
- [nikita/db/CLAUDE.md](nikita/db/CLAUDE.md) — Database layer
- [nikita/engine/CLAUDE.md](nikita/engine/CLAUDE.md) — Game engine
- [nikita/memory/CLAUDE.md](nikita/memory/CLAUDE.md) — pgVector memory
- [nikita/pipeline/CLAUDE.md](nikita/pipeline/CLAUDE.md) — Async pipeline
- [portal/CLAUDE.md](portal/CLAUDE.md) — Next.js portal

## Development Status

**76 specs implemented across 8 domains. 5,347+ backend tests. All deployed.**

| Phase | Specs | Status |
|-------|-------|--------|
| Core Engine | 001-006, 014, 049, 055, 057-058, 101 | 12 specs, 831 tests |
| Humanization | 021-027, 029, 056 | 9 specs, 1,738 tests |
| Pipeline & Memory | 012, 031, 039-043, 045, 060, 067-068, 100, 102, 104 | 14 specs |
| Portal | 008, 044, 046-047, 050, 059, 061-063, 070, 106 | 11 specs |
| Voice | 007, 028, 032-033, 051, 108 | 6 specs, 649 tests |
| Infrastructure | 009-011, 013, 015, 036, 038, 041, 052, 064, 066, 069, 107 | 14 specs |
| Admin & Observability | 016, 018-020, 034-035, 105 | 7 specs, 242 tests |
| Quality & Testing | 030, 048, 103 | 3 specs, 111 tests |

See [ROADMAP.md](ROADMAP.md) for detailed spec breakdown and `specs/` directory for individual artifacts.

## License

Private - All rights reserved.

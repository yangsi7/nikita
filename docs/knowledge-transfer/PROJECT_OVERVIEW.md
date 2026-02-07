# Project Overview

```yaml
context_priority: critical
audience: ai_agents
last_updated: 2026-02-03
related_docs:
  - USER_JOURNEY.md
  - CONTEXT_ENGINE.md
  - DATABASE_SCHEMA.md
```

## Product Concept

**Nikita: Don't Get Dumped** is an AI girlfriend simulation game where players maintain a relationship with Nikita, a virtual girlfriend powered by dual AI agents (voice + text).

### Core Premise

- Players interact with Nikita via Telegram (text) or phone calls (voice)
- Nikita has her own personality, life events, emotions, and memory
- Players must maintain the relationship through regular interaction
- Neglect leads to relationship decay and eventual breakup ("game over")
- The game progresses through 5 chapters with boss encounters

### Target Audience

- Users interested in AI companionship experiences
- Players who enjoy relationship simulation games
- People curious about conversational AI capabilities

### Revenue Model

- Freemium with potential premium features
- Current cost: $35-65/month infrastructure

---

## Tech Stack

### C1 Context Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              NIKITA SYSTEM                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │   Telegram   │    │  ElevenLabs  │    │    Portal    │                  │
│  │   Bot API    │    │  Voice API   │    │  (Next.js)   │                  │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘                  │
│         │                   │                   │                          │
│         ▼                   ▼                   ▼                          │
│  ┌─────────────────────────────────────────────────────────────┐          │
│  │                    FastAPI Backend                          │          │
│  │                   (Cloud Run - GCP)                         │          │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │          │
│  │  │ Text Agent  │  │ Voice Agent │  │ Game Engine │         │          │
│  │  │(Pydantic AI)│  │(ElevenLabs) │  │  (Scoring)  │         │          │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │          │
│  │         │                │                │                 │          │
│  │         ▼                ▼                ▼                 │          │
│  │  ┌─────────────────────────────────────────────────┐       │          │
│  │  │              Context Engine                      │       │          │
│  │  │   (8 Collectors → Prompt Generator → Claude)     │       │          │
│  │  └──────────────────────┬──────────────────────────┘       │          │
│  └─────────────────────────┼───────────────────────────────────┘          │
│                            │                                               │
│         ┌──────────────────┼──────────────────┐                           │
│         ▼                  ▼                  ▼                           │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                   │
│  │  Supabase   │    │ Neo4j Aura  │    │   Claude    │                   │
│  │ (PostgreSQL)│    │ (Graphiti)  │    │ (Sonnet 4.5)│                   │
│  └─────────────┘    └─────────────┘    └─────────────┘                   │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
```

### Component Summary

| Component | Technology | Purpose | Key Files |
|-----------|------------|---------|-----------|
| **Backend** | FastAPI + Python 3.11 | API, business logic | `nikita/api/main.py` |
| **Text Agent** | Pydantic AI + Claude Sonnet 4.5 | Text conversations | `nikita/agents/text/agent.py` |
| **Voice Agent** | ElevenLabs Conversational AI 2.0 | Voice calls | `nikita/agents/voice/` |
| **Database** | Supabase (PostgreSQL) | Relational data | `nikita/db/models/` |
| **Memory** | Neo4j Aura + Graphiti | Knowledge graphs | `nikita/memory/graphiti_client.py` |
| **Compute** | Google Cloud Run | Serverless hosting | `Dockerfile`, `cloudbuild.yaml` |
| **Portal** | Next.js 14 + Vercel | Player dashboard | `portal/` |
| **Scheduling** | pg_cron | Background jobs | Supabase dashboard |

---

## Repository Structure

```
nikita/
├── nikita/                    # Main Python package
│   ├── agents/               # AI agents
│   │   ├── text/            # Pydantic AI text agent
│   │   └── voice/           # ElevenLabs voice agent
│   ├── api/                  # FastAPI application
│   │   ├── routes/          # API endpoints
│   │   ├── schemas/         # Pydantic schemas
│   │   └── dependencies/    # DI and middleware
│   ├── config/               # Configuration
│   │   └── settings.py      # Environment settings
│   ├── config_data/          # YAML configs
│   │   ├── prompts/         # Prompt templates
│   │   └── game/            # Game constants
│   ├── context/              # Legacy context system
│   │   └── stages/          # Pipeline stages
│   ├── context_engine/       # NEW context engine
│   │   ├── collectors/      # 8 data collectors
│   │   └── validators/      # Prompt validators
│   ├── db/                   # Database layer
│   │   ├── models/          # SQLAlchemy models
│   │   ├── repositories/    # Repository pattern
│   │   └── migrations/      # Alembic migrations
│   ├── engine/               # Game engine
│   │   ├── scoring/         # Score calculation
│   │   ├── chapters/        # Chapter progression
│   │   └── decay/           # Decay system
│   ├── memory/               # Knowledge graphs
│   │   └── graphiti_client.py
│   ├── onboarding/           # Onboarding flows
│   ├── platforms/            # Platform integrations
│   │   └── telegram/        # Telegram bot
│   └── touchpoints/          # Proactive messaging
├── portal/                    # Next.js frontend
├── tests/                     # Test suite (4000+ tests)
├── specs/                     # SDD specifications
├── docs/                      # Documentation
└── memory/                    # Living architecture docs
```

---

## Key File References

### Entry Points

| File | Line | Purpose |
|------|------|---------|
| `nikita/api/main.py:1-50` | FastAPI app initialization |
| `nikita/agents/text/agent.py:1-100` | Text agent setup |
| `nikita/agents/voice/inbound.py:1-80` | Voice call handling |
| `nikita/platforms/telegram/message_handler.py:1-100` | Telegram entry |

### Configuration

| File | Line | Purpose |
|------|------|---------|
| `nikita/config/settings.py:1-200` | All environment variables |
| `nikita/engine/constants.py:1-150` | Game constants |
| `nikita/config_data/prompts/base_personality.yaml` | Nikita's personality |

### Core Business Logic

| File | Line | Purpose |
|------|------|---------|
| `nikita/context_engine/engine.py:1-200` | Context collection orchestration |
| `nikita/context_engine/assembler.py:1-150` | Prompt assembly |
| `nikita/engine/scoring/calculator.py:1-100` | Score calculation |
| `nikita/engine/chapters/state_machine.py:1-150` | Chapter transitions |

---

## Development Status

### Completed (Jan 2026)

- **41 SDD Specifications** - All audited PASS
- **4000+ Tests** - Unit, integration, E2E
- **Voice Agent** - Deployed with server tools
- **Text Agent** - Full context engine integration
- **Game Engine** - Scoring, chapters, decay, vices
- **Telegram Integration** - Production deployed
- **Admin Portal** - Monitoring, debugging

### In Progress

- **Player Portal** - 85% complete (settings, polish)
- **Context Engine Enhancements** - Ongoing optimization

### Known Issues (NEEDS RETHINKING)

1. **Voice-Text Parity Gap** - Voice bypasses ContextEngine
2. **Neo4j Cold Start** - 30-60s on first request
3. **Portal UX** - Needs design improvements
4. **Graphiti Utility** - Stored but underutilized

---

## Environment Setup

### Required Services

| Service | Purpose | Setup |
|---------|---------|-------|
| Supabase | PostgreSQL database | Create project at supabase.com |
| Neo4j Aura | Graph database | Create free instance at neo4j.com |
| Claude API | LLM | Get key from anthropic.com |
| ElevenLabs | Voice AI | Create account at elevenlabs.io |
| Telegram Bot | Bot token | Create via @BotFather |
| GCP | Cloud Run | Enable Cloud Run API |

### Environment Variables

```bash
# Core
DATABASE_URL=postgresql://...
NEO4J_URI=neo4j+s://...
NEO4J_USER=neo4j
NEO4J_PASSWORD=...
ANTHROPIC_API_KEY=sk-ant-...

# ElevenLabs
ELEVENLABS_API_KEY=...
ELEVENLABS_AGENT_ID=...
ELEVENLABS_AGENT_META_NIKITA=...

# Telegram
TELEGRAM_BOT_TOKEN=...
TELEGRAM_WEBHOOK_SECRET=...

# GCP
GCP_PROJECT=gcp-transcribe-test
GCP_REGION=us-central1
```

See: `nikita/config/settings.py:1-200` for complete list.

### Local Development

```bash
# Setup
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Database
alembic upgrade head

# Run
uvicorn nikita.api.main:app --reload

# Tests
pytest tests/ -v
```

---

## Deployment Architecture

### Production Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                         Cloud Run                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   nikita-api                             │   │
│  │  - Min instances: 0 (scale to zero)                     │   │
│  │  - Max instances: 10                                     │   │
│  │  - Memory: 2GB                                           │   │
│  │  - CPU: 1                                                │   │
│  │  - Timeout: 300s                                         │   │
│  │  - Concurrency: 80                                       │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
              │                    │                    │
              ▼                    ▼                    ▼
     ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
     │  Supabase   │      │ Neo4j Aura  │      │   Vercel    │
     │  (Free tier)│      │ (Free tier) │      │  (Portal)   │
     └─────────────┘      └─────────────┘      └─────────────┘
```

### Scheduled Jobs (pg_cron)

| Job | Schedule | Endpoint |
|-----|----------|----------|
| decay | Every hour | `POST /tasks/decay` |
| deliver | Every 30 min | `POST /tasks/deliver` |
| summary | Daily 6 AM | `POST /tasks/summary` |
| cleanup | Daily 3 AM | `POST /tasks/cleanup` |
| process | Every 5 min | `POST /tasks/process-conversations` |

---

## Cost Structure

### Monthly Estimates

| Service | Cost | Notes |
|---------|------|-------|
| Cloud Run | $5-15 | Pay per request |
| Supabase | $0 | Free tier |
| Neo4j Aura | $0 | Free tier |
| Claude API | $20-40 | ~$0.003/1K tokens |
| ElevenLabs | $5-10 | Voice minutes |
| Vercel | $0 | Free tier |
| **Total** | **$35-65** | Usage-based |

---

## Related Documentation

- **Detailed Architecture**: [CONTEXT_ENGINE.md](CONTEXT_ENGINE.md)
- **Game Flow**: [USER_JOURNEY.md](USER_JOURNEY.md)
- **Data Model**: [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)
- **Deployment**: [DEPLOYMENT_OPERATIONS.md](DEPLOYMENT_OPERATIONS.md)

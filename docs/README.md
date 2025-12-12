# Nikita: Don't Get Dumped

**Documentation for the Nikita AI Girlfriend Game**

---

## The Game

You're dating a 25-year-old hacker who microdoses LSD, survives on black coffee and spite, and will dump your ass if you can't keep up.

**Win**: Reach Chapter 5 (Established relationship) → Victory message
**Lose**: Score hits 0% OR fail a boss 3 times → Game over

---

## Documentation Index

### Game Design

| Document | What It Covers |
|----------|----------------|
| [Game Mechanics](game/mechanics.md) | Scoring system, chapters, bosses, decay, vice system, conflicts |
| [Nikita's Character](game/nikita.md) | Voice, personality, emotional states, response patterns |
| [Player Journey](game/journey.md) | Day 1 through victory - the full experience walkthrough |

### Technical

| Document | What It Covers |
|----------|----------------|
| [Architecture Overview](architecture/overview.md) | Tech stack, system diagram, knowledge graphs, data model |

### Decisions & Audits

| Document | What It Covers |
|----------|----------------|
| [Backend DB Audit](decisions/20251201-analysis-backend-db-audit.md) | Database schema and backend analysis |
| [Game Mechanics Audit](decisions/20251201-report-game-mechanics-audit.md) | Game mechanics validation report |
| [Security Review](decisions/20251202-security-review-001.md) | Security audit findings |
| [System Audit Final](decisions/20251202-system-audit-final-report.md) | Comprehensive system audit |

### Verification Reports

| Document | What It Covers |
|----------|----------------|
| [Memory RLS Verification](verification/20251201-verification-memory-rls.md) | Row-level security verification |

### Guides

| Document | What It Covers |
|----------|----------------|
| [Audio System Guide](guides/20251202-system-audio-guide.md) | ElevenLabs voice integration guide |

---

## Quick Reference

### Scoring
- **Single composite score**: 0-100% (Relationship Health)
- **Hidden sub-metrics**: Intimacy (30%), Passion (25%), Trust (25%), Secureness (20%)
- **Summaries**: End of conversation + End of day

### Chapters (Compressed 21-Day Game)

| Ch | Name | Days | Boss | Score to Unlock |
|----|------|------|------|-----------------|
| 1 | Curiosity | 1-3 | "Worth my time?" | Start (55%) |
| 2 | Intrigue | 4-7 | "Handle intensity?" | 60% |
| 3 | Investment | 8-11 | "Trust test" | 65% |
| 4 | Intimacy | 12-16 | "Vulnerability" | 70% |
| 5 | Established | 17-21 | "Ultimate test" → WIN | 75% |

### Key Mechanics

- **3 boss attempts** per boss, then game over
- **Hourly decay**: 0.8/0.6/0.4/0.3/0.2 pts/hr (Ch1-5) after grace period
- **Grace periods**: 8/16/24/48/72 hours (Ch1-5)
- **Dynamic vice discovery** - system learns your preferences
- **Hard reset on game over** - stakes matter

### Tech Stack

| Component | Choice |
|-----------|--------|
| LLM | Claude Sonnet 4.5 |
| Voice | ElevenLabs Conv AI 2.0 |
| Database | Supabase (PostgreSQL + pgVector) |
| Knowledge Graphs | Graphiti + Neo4j Aura |
| Scheduling | pg_cron (Cloud Run tasks) |
| Platform | Telegram + Voice calls |
| Portal | Web stats dashboard (future) |

---

## Status

**Phase**: Phase 2 at 95%, Phase 3 (Configuration + Game Engine) in progress
**Current**:
- Telegram deployed to Cloud Run ✅
- Text agent complete (156 tests) ✅
- Configuration system 75% (52 tests) ⚠️
**Next**: Complete 013 Configuration → 014 Engagement Model → Game Engine

---

## Specifications

All specs live in `specs/` with complete SDD artifacts (spec.md, plan.md, tasks.md, audit-report.md):

| Spec | Domain | Status |
|------|--------|--------|
| 001-013 | Various | See `todos/master-todo.md` for detailed status |

**Critical Path**: 013 → 014 → 012 → 003-006 → 007-008

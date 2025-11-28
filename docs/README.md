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

---

## Quick Reference

### Scoring
- **Single composite score**: 0-100% (Relationship Health)
- **Hidden sub-metrics**: Intimacy (30%), Passion (25%), Trust (25%), Secureness (20%)
- **Summaries**: End of conversation + End of day

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
- **Clingy penalty** - too much contact hurts you too
- **Dynamic vice discovery** - system learns your preferences
- **Hard reset on game over** - stakes matter

### Tech Stack

| Component | Choice |
|-----------|--------|
| LLM | Claude Sonnet |
| Voice | ElevenLabs Conv AI 2.0 |
| Database | Supabase |
| Knowledge Graphs | Graphiti |
| Platform | Telegram + Voice calls |
| Portal | Web stats dashboard |

---

## Status

**Phase**: Pre-SDD Concept Development
**Next**: Full technical specification (SDD phase)

---

## Source Documents

Raw design documents in `docs-to-process/` (21 files). These were synthesized into the above documentation.

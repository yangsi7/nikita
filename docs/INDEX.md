# docs/ Index

Top-level navigation hub for the `docs/` directory tree. Updated 2026-05-05 (W6 doc-estate restructure).

## Architecture Diagrams (W6.5, code-verified 2026-05-05)

All diagrams derived directly from master HEAD source code (no docs read). Smell badges visible on rendered diagrams reflect real codebase issues — see node labels for `file:line` citations.

| Diagram | Topic | Figma |
|---|---|---|
| A | 11-Stage Pipeline (`orchestrator.py:47-59`) — state collisions, bare-Exception swallow, 5 invocation sites | [Open](https://www.figma.com/board/CgTUZGxzzNJNySxgf9IfGZ) |
| B | Pydantic AI Agent Map (text/onboarding/psyche; voice = ElevenLabs Server Tools NOT PydAI) | [Open](https://www.figma.com/board/Q0r37xW7CNT9WOY5ksyRAz) |
| C | Memory Subsystem (pgVector, dedup 0.87, supersession, 6 importers) | [Open](https://www.figma.com/board/M9ul54PIv4W5h3EBmNbDHe) |
| D | Game Engine — Scoring + Chapters + Boss + Decay + Vice (calibration multipliers contradict YAML, GRACE_PERIODS inverted) | [Open](https://www.figma.com/board/D0Nc1NELEt6slO2ECQzIIk) |
| E | Life Simulator (dual tick: pipeline stage + cron daily 0500) | [Open](https://www.figma.com/board/vmYn6BXyL9KXh4bCjyZkum) |
| F | Scheduled Actions + Background Tasks (cron + 11 task endpoints + hardcoded bearer + dev-mode bypass) | [Open](https://www.figma.com/board/xCjCjVhtERCFGYEK0eAufk) |
| G | UX Entry Routing + Auth Handoff (3 entry surfaces + 3-call user creation + dual-auth surface + E2E_AUTH_BYPASS leak) | [Open](https://www.figma.com/board/P9s9PS0yX0K5o3f8617zmm) |
| Doc Taxonomy | This doc tree (specs / living memory / nav / rules / cold storage / queue) | [Open](https://www.figma.com/board/yYL1NJfD1y1wNBdnj0qNcn) |

## Structure (ASCII)

```
docs/
├── INDEX.md                    ← you are here (top-level nav)
├── CONCEPTS.md                 ← glossary: ~40 concepts → canonical home
├── README.md                   ← legacy game-overview index (predates INDEX.md)
├── deployment.md               ← deployment reference (Cloud Run, Vercel, env)
├── how-nikita-works.md         ← engineering narrative ("how the system works")
├── nikita-technical-brief.md   ← single-page technical pitch
├── content/                    ← user-facing copy (wizard, narration, magic-link email)
│   ├── magic-link-email.md
│   ├── onboarding-design-brief.md
│   ├── tts-narration-part1.md
│   ├── tts-narration-part2.md
│   └── wizard-copy.md
├── diagrams/                   ← static diagrams (excalidraw + PNG)
│   ├── README.md               ← per-diagram index
│   ├── 01-full-stack-architecture.{excalidraw,png}
│   ├── 02-conversation-pipeline.{excalidraw,png}
│   ├── 03-prompt-assembly.{excalidraw,png}
│   └── testing/                ← test-pyramid + coverage diagrams
├── game/                       ← player-facing game design
│   ├── journey.md
│   ├── mechanics.md
│   └── nikita.md (character voice)
├── guides/                     ← how-to guides
│   ├── elevenlabs-console-setup.md
│   ├── context-engine-migration.md
│   ├── knowledge-transfer-generator.md  ← DEPRECATED (W4)
│   └── archive/
├── images-of-nikita/           ← brand image assets (Cloudinary ingestion targets)
├── models/                     ← stochastic-model artifacts
│   ├── response-timing.md      ← Spec 210 model doc
│   ├── response-timing-explorer.html
│   ├── heartbeat-intensity.md  ← Spec 215 model doc
│   └── heartbeat-*.png         ← Monte Carlo plots
├── reference/                  ← reference material (schemas, configs)
│   ├── elevenlabs-configuration.md
│   ├── schema-diagrams.md
│   ├── schema-reference.md
│   ├── spec-108-voice-optimization-summary.md
│   └── time-estimation.md
└── .archive/                   ← cold storage (with per-bucket README)
    ├── knowledge-transfer-2026-03-pgvector-deprecated/  ← W4 archive
    ├── docs-to-process-pile/                            ← Wave 3B archive
    └── brainstorm-2026-02-bayesian-sprint/              ← Wave 3A archive
```

## Cross-references

| Need | Go to |
|---|---|
| Spec status, roadmap | [`ROADMAP.md`](../ROADMAP.md) |
| Per-spec artifacts | [`specs/INDEX.md`](../specs/INDEX.md) |
| Audit index | [`audits/INDEX.md`](../audits/INDEX.md) |
| Concept glossary | [`docs/CONCEPTS.md`](CONCEPTS.md) |
| Memory canonical (architecture, game-mechanics, etc.) | [`memory/README.md`](../memory/README.md) |
| Project rules | [`.claude/rules/`](../.claude/rules/) |
| Root nav | [`CLAUDE.md`](../CLAUDE.md) |

## Conventions (post-W6)

- **One INDEX.md per top-level container**: `docs/INDEX.md`, `audits/INDEX.md`, `specs/INDEX.md`. INDEX is structured nav; README is narrative.
- **Subdir READMEs document scope** (e.g., `docs/.archive/<bucket>/README.md`).
- **Cold storage**: anything in `docs/.archive/` is historical. README in each archive bucket explains why.
- **Naming**: dated drafts use `{YYYYMMDD}-{type}-{slug}.md`; living docs have no date prefix. Convention will be codified in `.claude/rules/doc-lifecycle.md` (W9).
- **Reachability**: every doc must be reachable from `CLAUDE.md` Navigation → `docs/INDEX.md` → subdir/README within 2 hops. Drift detected by `rg -L` against this file.

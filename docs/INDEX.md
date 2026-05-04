# docs/ Index

Top-level navigation hub for the `docs/` directory tree. Updated 2026-05-05 (W6 doc-estate restructure).

> **Doc-taxonomy diagram**: a Figma-rendered diagram of this tree will be embedded here once the Figma MCP token is reauthenticated (W6.5 architecture-diagrams wave will produce both the doc-taxonomy + 7 architecture diagrams). Placeholder: see ASCII tree below.

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

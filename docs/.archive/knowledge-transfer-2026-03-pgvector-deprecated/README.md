# Knowledge-Transfer Archive (DO NOT CONSULT)

**Archived**: 2026-05-05 (W4 KT migration with code-verification gate)
**Reason**: Spec 042 replaced Neo4j/Graphiti memory with SupabaseMemory (pgVector); KT files were generated against the pre-Spec-042 architecture and contain stale Neo4j references, wrong file paths, wrong class names, wrong method signatures, and outdated engagement-multiplier values.
**Status**: HISTORICAL ARTIFACT. Do NOT use as a reference.

## Why this archive exists (instead of hard-delete)

KT files were code-verified during W4 (audits at `audits/2026/20260505-kt-migration-w4-verification-*.md`). Verified facts were migrated into `memory/*.md` with `file:line` citations. UNVERIFIABLE/STALE claims were dropped. Archiving (vs deletion) preserves traceability for the audit trail.

## Where to find current canonical content

| Former KT topic | Current canonical home |
|---|---|
| `ARCHITECTURE_ALTERNATIVES.md` | `memory/architecture.md` (root CLAUDE.md Navigation) |
| `GAME_ENGINE_MECHANICS.md` | `memory/game-mechanics.md` |
| `USER_JOURNEY.md` | `memory/user-journeys.md` |
| `PROJECT_OVERVIEW.md`, `CONTEXT_ENGINE.md`, `PIPELINE_STAGES.md` | `memory/architecture.md` §"11-Stage Async Pipeline" |
| `AUTHENTICATION.md`, `DATABASE_SCHEMA.md` | `memory/backend.md`, `memory/integrations.md` |
| `INTEGRATIONS.md` | `memory/integrations.md` |
| `VOICE_IMPLEMENTATION.md` | `memory/architecture.md` §"Pydantic AI Agents" + `nikita/agents/voice/CLAUDE.md` |
| `ONBOARDING.md` | `memory/user-journeys.md` §"Onboarding Plumbing" + `nikita/agents/onboarding/CLAUDE.md` |
| `TESTING_STRATEGY.md` | `.claude/rules/testing.md` |
| `DEPLOYMENT_OPERATIONS.md` | `docs/deployment.md` |
| `ANTI_PATTERNS.md` | `.claude/rules/agentic-design-patterns.md` + scattered rule files |
| `INDEX.md` | `memory/README.md` (Memory Documentation Hub) |

## Top staleness items (proven by W4 verification)

- "Memory uses Neo4j/Graphiti" → SupabaseMemory (pgVector) per Spec 042. Embedding `text-embedding-3-small`, dim 1536, dedup `0.87` at `nikita/memory/supabase_memory.py:42`.
- "8-collector context engine" → 11-stage `PipelineOrchestrator` at `nikita/pipeline/orchestrator.py:47-59`.
- `ContextEngine` / `PromptGenerator` / `PostProcessor` classes → none exist; replaced by pipeline stages.
- KT file paths `boss_encounter.py` / `boss_judgment.py` / `state_machine.py` → `boss.py` / `judgment.py` / `phase_manager.py` in `nikita/engine/chapters/`.
- KT engagement multipliers (IN_ZONE=1.2 etc.) → real values in `nikita/engine/scoring/calculator.py:20-27` `CALIBRATION_MULTIPLIERS` (IN_ZONE=1.0, etc.).
- KT vice taxonomy (humor/playfulness/flirtation) → real 8 categories in `nikita/db/models/user.py:393-403`: intellectual_dominance, risk_taking, substances, sexuality, emotional_intensity, rule_breaking, dark_humor, vulnerability.
- KT chapter names ("Getting Started"/"Building Connection") → real names in `nikita/config_data/chapters.yaml:6,14,22,30,38`: Curiosity / Intrigue / Investment / Intimacy / Established.

See the 3 W4 audit reports for the full claim-by-claim verification tables:
- `audits/2026/20260505-kt-migration-w4-verification-architecture.md`
- `audits/2026/20260505-kt-migration-w4-verification-game-mechanics.md`
- `audits/2026/20260505-kt-migration-w4-verification-user-journeys.md`

## Canonical evidence trail

- Wave 2A `cleanup-canonical-decisions.txt` (2026-05-03) initially picked KT for 3 of 5 topics on recency basis.
- W4 (2026-05-05) superseded that with code-verification gate; consolidated all 5 to `memory/`.
- Spec 042 (Feb 2026) is the architectural pivot that rendered most of this dir stale.

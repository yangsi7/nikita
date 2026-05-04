# context/ — LEGACY Context Engineering Module

> **LEGACY MODULE — body bulk-pruned 2026-05-05 (W7b-1)**. The pre-Spec-042 PostProcessor / stage-classes / TemplateGenerator API documented in earlier versions of this file does NOT exist on master. Spec 042 (unified pipeline) replaced the entire `nikita/context/` pipeline architecture with `nikita/pipeline/orchestrator.py` (11-stage `STAGE_DEFINITIONS` at `:47-59`).

## Active surviving files

Only the following files in this directory are still in use:

| File | Purpose |
|---|---|
| `session_detector.py` | Detects stale text sessions (15-min timeout) and enqueues them for post-processing. |
| `validation.py` | Helpers for context-package validation (Pydantic). |
| `package.py` | Defines `ContextPackage` Pydantic model (cache surface), consumed by the pipeline's `prompt_builder` stage. |
| `__init__.py` | Re-exports the above. |

All other files (`engine.py`, `stages/*.py`, `template_generator.py`, `pipeline_context.py`, etc.) referenced by the deleted body have been removed; the pipeline machinery is now `nikita/pipeline/`.

## Where to look instead

| Topic | Canonical home |
|---|---|
| 11-stage pipeline orchestrator | [`nikita/pipeline/CLAUDE.md`](../pipeline/CLAUDE.md) + [`memory/architecture.md`](../../memory/architecture.md) §"11-Stage Async Pipeline" |
| Pipeline observability (Spec 110) | [`memory/architecture.md`](../../memory/architecture.md) |
| Context-engineering history | This file's git history (`git log --follow nikita/context/CLAUDE.md`) |

## Rule

- **Do not extend this file.** Any new context-related work belongs in `nikita/pipeline/`.
- If you need a defunct concept's historical context (e.g., the Spec 037 ContextEngine framing), check the W4 KT-verification audit at `audits/2026/20260505-kt-migration-w4-verification-architecture.md` or the git history of this file.

Last verified: 2026-05-05

# .planning/ — GSD Workflow Context

## Purpose

GSD (Get Shit Done) planning directory for the Nikita project. Migrated from SDD on 2026-05-19. This directory is the canonical home for all active phase planning artifacts.

## Key Files

| File | Purpose |
|---|---|
| `PROJECT.md` | Project identity, tech stack, key files, game constants |
| `STATE.md` | Current state: active phase, last action, open issues |
| `ROADMAP.md` | Canonical roadmap — active phases + SDD backlog reference |
| `REQUIREMENTS.md` | REQ-NNN entries with AC traceability |
| `config.json` | GSD framework configuration |
| `phases/NN-*/` | Per-phase artifacts (CONTEXT.md, SPEC.md, PLAN.md, TASKS.md) |

## Active Phase

Phase 01: `canonical-tg-first-signup` — Spec 220 implementation. Entry: `phases/01-canonical-tg-first-signup/`.

## GSD Commands

| Command | When |
|---|---|
| `/gsd:spec-phase 01` | Author spec for Phase 01 |
| `/gsd:plan-phase 01` | Create implementation plan |
| `/gsd:execute-phase 01` | Begin TDD implementation |
| `/gsd:validate-phase 01` | Gate check before merge |
| `/gsd:progress` | Current phase status |
| `/gsd:resume-work` | Re-orient after gap |

## SDD Archive

All pre-migration SDD artifacts preserved at `specs/.archive/sdd-pre-migration-2026-05-19/` (91 spec dirs). Root `ROADMAP.md` is a redirect stub pointing here.

## Navigation

- Project root: `CLAUDE.md`
- GSD canonical: `.planning/ROADMAP.md`
- Active phase: `.planning/phases/01-canonical-tg-first-signup/`
- Architecture: `plans/master-plan.md`, `memory/architecture.md`

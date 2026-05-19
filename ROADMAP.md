---
title: "Nikita: Don't Get Dumped — Project Roadmap (redirect stub)"
lifecycle: superseded
successor: .planning/ROADMAP.md
last_updated: 2026-05-19
---

> **Canonical roadmap at `.planning/ROADMAP.md` post-GSD-migration 2026-05-19.**
> This file is a redirect/dashboard. Domain tables and active phase tracking live in `.planning/ROADMAP.md`.

# Nikita: Don't Get Dumped — Project Roadmap

---

## Project Status Dashboard

| Metric | Value | Source-of-truth |
|--------|-------|----------------|
| GSD Framework | Active | `.planning/ROADMAP.md` |
| Active phase | 01 — canonical-tg-first-signup | `.planning/STATE.md` |
| Total SDD spec dirs (archived) | 91 | `ls specs/.archive/sdd-pre-migration-2026-05-19/ \| wc -l` |
| Backend tests collected | 6,822 (184 deselected) | `uv run pytest --collect-only -q` |
| Portal routes (page.tsx files) | 30 | `find portal/src/app -name page.tsx \| wc -l` |
| Pipeline stages | 11 | `find nikita/pipeline/stages -name '*.py' -not -name '__init__.py' -not -name 'base.py' \| wc -l` |
| Feature flags (`*_enabled: bool = Field(...)`) | 11 | `rg -c "^\s+\w+_enabled: bool = Field" nikita/config/settings.py` |
| Supabase migrations | 110+ | `ls supabase/migrations/*.sql \| wc -l` |
| Cloud Run deploy | `nikita-api-00324-pkt` (us-central1) | `gcloud run revisions list` |
| Portal deploy | `nikita-mygirl.com` (apex canonical; www→apex 308) | Vercel REST API |
| Last master commit | 47c6158 — `fix(219): autobind race + dashboard_bridge 500 (Walk #219) (#663)` | `git log -1 origin/master` |

---

## Navigation

- **Active phases**: `.planning/ROADMAP.md`
- **Current state**: `.planning/STATE.md`
- **Phase 01 spec**: `.planning/phases/01-canonical-tg-first-signup/01-SPEC.md`
- **SDD archive**: `specs/.archive/sdd-pre-migration-2026-05-19/`
- **Architecture**: `plans/master-plan.md`, `memory/architecture.md`

---

*Migrated from SDD to GSD on 2026-05-19. Pre-migration content archived in `specs/.archive/sdd-pre-migration-2026-05-19/`.*

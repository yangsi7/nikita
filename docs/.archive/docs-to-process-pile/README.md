# docs-to-process pile (cold storage)

**Archived**: 2026-05-03 (Wave 3B doc-cleanup)
**Source**: `docs-to-process/` and `docs-to-process/.archive/` at the time of archive.
**Status**: Cold storage. NOT processed via `/streamline-docs`. Preserved for audit trail and historical research.

Per the cleanup plan locked decision #3, the pile was bulk-archived rather than streamlined into `docs/{domain}/`. Most files are research / planning artifacts from prior sprints (mid-2025 through April 2026). The 9 most-recent (`20260428-*` and `20260416-*`) are Spec 216 wave research drafts that were superseded by the Spec 216 master + 6 subspec dirs already living at `specs/216-onboarding-redesign-cinematic/`.

If a future need arises:
- For Spec 216 context: read `specs/216-onboarding-redesign-cinematic/spec.md` first; this pile only adds research depth, not authoritative state.
- For pre-2026 research artifacts: most have been distilled into the surviving `memory/` and `docs/knowledge-transfer/` canonical files (see `cleanup-canonical-decisions.txt` at the repo root).

The empty `docs-to-process/` directory at the repo root is preserved for the **forward** documentation lifecycle described in `.claude/CLAUDE.md` (new session artifacts → `docs-to-process/{YYYYMMDD}-{type}-{description}.md` → `/streamline-docs` → `docs/{domain}/`). Do NOT add backlogged work here; new artifacts only.

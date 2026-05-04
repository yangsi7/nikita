# Archive Policy

Cold-storage policy for superseded documentation, drafts, and historical artifacts.

## Cold-storage layout

```
docs/.archive/
├── <bucket>/                      ← one bucket per archive event
│   ├── README.md                  ← MANDATORY: archive trail + canonical pointers
│   └── <archived files…>
```

Bucket naming: `{slug}-{date}-{reason}` (e.g., `knowledge-transfer-2026-03-pgvector-deprecated`, `docs-to-process-pile-2026-05-wave3b`).

## Trigger matrix (archive vs hard-delete)

| Trigger | Action |
|---|---|
| Spec PASS audit | Stay in place; `lifecycle: frozen`. |
| Spec SUPERSEDED | Banner pointing at successor; do NOT move. |
| Spec replaced wholesale | Move to `specs/archive/<NNN>-<slug>/`. Update ROADMAP. |
| Doc orthogonal to current architecture (e.g., Neo4j-era KT) | Move to `docs/.archive/<bucket>/`. Add archive README. |
| Brainstorm / research drafts | Move to `docs/.archive/<bucket>/`. |
| Junk files (.DS_Store, editor swap) | Hard-delete. |
| Empty placeholder files | Hard-delete. |
| Duplicate of canonical | Verify (`git log -p` + grep), then hard-delete. |
| Code class/file deleted that doc referenced | Update doc OR archive doc + deprecation banner. |

## Mandatory README in every archive bucket

Each `docs/.archive/<bucket>/README.md` MUST include:
- **Archived**: date + driving wave/PR
- **Reason**: 1-3 sentences
- **Status**: HISTORICAL ARTIFACT. DO NOT CONSULT.
- **Where to find current canonical**: pointer table
- Top staleness items (if applicable)

Precedent: `docs/.archive/knowledge-transfer-2026-03-pgvector-deprecated/README.md` (W4 2026-05-05).

## Inbound-grep pre-step (mandatory)

Before archiving:
```bash
rg -l "<doc-path>" --type md
```
Update or remove every inbound reference. Atomic in the same PR.

## Atomicity

- CLAUDE.md Navigation update MUST land in same commit as `git mv` to archive.
- Inbound-ref rewrites (memory/, audits/, specs/) MUST land in same commit as the move.
- DO NOT batch archive moves across multiple PRs without a tracking issue.

## Quarterly archive audit

Cadence: every 3 months. Manual review of `docs/.archive/` for: buckets > 6 months old with 0 inbound refs → consider hard-delete after another quarter; buckets without README → add one or hard-delete; stragglers in non-archive dirs → sweep.

## Anti-rationalization

| Rationalization | Response |
|---|---|
| "Hard-delete is faster than archive" | Trace integrity > bucket size. Archive. |
| "I'll archive later, ship the PR now" | Atomicity rule. Same commit. |
| "No one uses this doc anyway" | Inbound-grep first. 0 hits = delete; hits = archive. |
| "Banner is enough; don't move" | Move OR delete. Banners + dir intact = clutter. |

## Precedent

- W4 (2026-05-05): KT → `docs/.archive/knowledge-transfer-2026-03-pgvector-deprecated/`
- Wave 3B (2026-05-03): docs-to-process pile → archive
- Wave 3A (2026-05-03): brainstorm/research → archive

## Reference

Sister rules: `docs-structure.md`, `claude-md-conventions.md`, `doc-lifecycle.md`

# Memory File Size Exceptions — 2026-05-03

**Status**: ACCEPTED
**Scope**: `memory/` canonical living docs over the project guideline of ≤500 lines per doc file (`.claude/CLAUDE.md` Documentation Rules).
**Driver**: Doc-cleanup Wave 2C (`~/.claude/plans/docs-to-process-20260503-doc-audit-clea-nested-balloon.md` locked decision #4 — accept >500L via documented exception rather than mechanical split).

> This file follows the ADR shape but lives in `audits/` (not `~/.claude/ecosystem-spec/decisions/`) because the user-global ecosystem-spec is **out of repo scope** for this cleanup (per the plan's Out of Scope list). When a stable in-repo ADR home is established, this file should be migrated.

---

## Context

The project's documentation guideline (`.claude/CLAUDE.md` "Documentation Rules") is **≤500 lines per doc file**. As of Wave 2C inventory (post Wave 2B doc-cleanup), the following `memory/` files exceed that threshold:

| File | Lines | Wave 2A canonical winner | Last edits in 90d | Decision |
|------|-------|--------------------------|-------------------|----------|
| `memory/backend.md` | 734 | memory/ | 2 | Exception (this doc) |
| `memory/integrations.md` | 1009 | memory/ | 3 | Exception (this doc) |
| `memory/product.md` | 795 | memory/ (no KT counterpart; not covered by `docs/how-nikita-works.md`) | 1 | Exception (this doc) |
| `memory/game-mechanics.md` | 552 (pre-W4) → grew post-W4 with code-verified additions | **memory/** (post-W4 2026-05-05) | 0 (pre-W4) | Now canonical; exception extended to cover post-W4 size |

`memory/architecture.md` (332L pre-W4) and `memory/user-journeys.md` (441L pre-W4) sat under the 500L cap pre-W4. **Post-W4 (2026-05-05)**: Wave 2A's "demote in favor of KT" was reversed. KT was archived to `docs/.archive/knowledge-transfer-2026-03-pgvector-deprecated/` after code-verification proved it stale; verified facts migrated into `memory/architecture.md` + `memory/game-mechanics.md` + `memory/user-journeys.md` with `file:line` citations. All 5 canonical topics now live in `memory/`.

The mechanical alternative — splitting each canonical file in two atomic commits per source file — would generate ~2× the file size in PR diff (delete + N new files), unavoidably exceeding the project 400-line PR cap and creating cross-reference fragmentation. The user has locked the decision to accept rather than split (see plan locked-decision #4).

---

## Decision

Accept the 3 canonical files (`backend.md`, `integrations.md`, `product.md`) as documented exceptions to the ≤500L guideline. The decision is in force until either:

(a) any of the files grows >50% from its current size, OR
(b) cross-reference fragmentation is observed in practice (e.g., a future spec splits the file's audience across multiple readers each needing only one section), OR
(c) a follow-up cleanup wave introduces a structured `docs/{domain}/` home that supersedes the topic.

**Post-W4 update (2026-05-05)**: `memory/game-mechanics.md` is now canonical (Wave 2A's KT-winner decision was reversed by W4 code-verification). The exception is extended to cover its post-W4 size.

---

## Per-file rationale

### `memory/backend.md` (734 lines)

- Canonical per Wave 2A `cleanup-canonical-decisions.txt`: `backend=memory`.
- 2 commits in last 90d (2026-03-16 GH #140 column-drop context, prior is older).
- Single-topic coherence: API routes + DB patterns + auth model live as one continuous narrative; readers consume top-to-bottom or via header anchor jumps.
- Splitting into `backend-api.md` + `backend-db.md` would cut a tight cross-reference graph and add 1 navigation hop per look-up.
- Acceptable.

### `memory/integrations.md` (1009 lines)

- Canonical per Wave 2A: `integrations=memory`.
- 3 commits in last 90d — most-active oversize file.
- Single-topic coherence: ElevenLabs + Telegram + Supabase config live together because the deployment-side concerns interleave (e.g., dashboard-side keys for ElevenLabs feed code-side `nikita/config/settings.py` referenced by Supabase migrations).
- An inevitable future split candidate: `integration-supabase.md` / `integration-elevenlabs.md` / `integration-telegram.md` once the file passes ~1500 lines OR a single integration grows enough that its dashboard recipe doesn't fit a single section.
- Acceptable for now.

### `memory/product.md` (795 lines)

- Canonical per process-of-elimination (no KT counterpart; not covered by `docs/how-nikita-works.md` which is the technical narrative, not product/marketing).
- 1 commit in last 90d.
- Single-topic coherence: product narrative is one continuous case for the project (overview → value prop → personas → stories → principles → GTM → success). Splitting Personas vs Principles vs GTM into 3 files would shred the argument.
- Diff-vs-how-nikita-works check (this PR): different audiences. `how-nikita-works.md` is the engineering narrative ("how the system works"); `product.md` is the product narrative ("why the product exists, who it serves, what success looks like"). Not redundant.
- Acceptable.

### `memory/game-mechanics.md` (552 lines pre-W4; ~700 post-W4 with code-verified additions)

- Canonical per `cleanup-canonical-decisions.txt` (W4 2026-05-05; Wave 2A's KT-winner decision was reversed after code-verification proved KT stale).
- W4 audit at `audits/2026/20260505-kt-migration-w4-verification-game-mechanics.md` documents the migration.
- Single-topic coherence: scoring + chapters + boss + decay + vices live as one narrative.
- Acceptable (extends the exception to post-W4 size).

---

## Consequences

- 3 files in `memory/` will continue to exceed the ≤500L guideline. New readers should be aware via this audit doc.
- `memory/README.md` index page references this audit-doc path (not added in Wave 2B README rewrite; follow-up if needed).
- A future cleanup wave that introduces a structured `docs/{domain}/` home (e.g., per-integration files, per-API-area files) supersedes this exception for any file it absorbs.
- If size triggers (a) (>50% growth) or (b) (cross-ref fragmentation observed) hit, file a fresh in-repo ADR or audit doc, do NOT silently extend this exception.

---

## Reference

- Cleanup plan: `~/.claude/plans/docs-to-process-20260503-doc-audit-clea-nested-balloon.md` (Wave 2C section)
- Source-of-truth canonical decisions: `cleanup-canonical-decisions.txt` (repo root, from Wave 2A PR #472)
- Project ≤500L rule source: `.claude/CLAUDE.md` Documentation Rules
- Sister cleanup PRs: #469 / #471 / #472 / #473

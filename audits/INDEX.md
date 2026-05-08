# audits/ Index

Index of audit reports under `audits/`. Updated 2026-05-05 (W6).

## Structure

```
audits/
├── INDEX.md          ← you are here
├── 2025/             ← legacy (Dec 2025)
└── 2026/             ← active (2026)
```

## By year

### 2025

| Date | File | Type | Driver |
|---|---|---|---|
| 2025-12-01 | [`20251201-analysis-backend-db-audit.md`](2025/20251201-analysis-backend-db-audit.md) | Analysis | Backend + DB schema audit |
| 2025-12-01 | [`20251201-report-game-mechanics-audit.md`](2025/20251201-report-game-mechanics-audit.md) | Report | Game-mechanics validation |
| 2025-12-01 | [`20251201-verification-memory-rls.md`](2025/20251201-verification-memory-rls.md) | Verification | Memory RLS policies |
| 2025-12-02 | [`20251202-security-review-001.md`](2025/20251202-security-review-001.md) | Security review | Security audit findings |
| 2025-12-02 | [`20251202-system-audit-final-report.md`](2025/20251202-system-audit-final-report.md) | System audit | Comprehensive system audit |

### 2026

| Date | File | Type | Driver |
|---|---|---|---|
| 2026-01-08 | [`20260108-doc-sync.md`](2026/20260108-doc-sync.md) | Doc sync | Pre-Jan-2026 doc-vs-code drift sweep |
| 2026-02-24 | [`20260224-deep-audit.md`](2026/20260224-deep-audit.md) | Deep audit | `/deep-audit` skill output |
| 2026-05-03 | [`20260503-memory-file-size-exceptions.md`](2026/20260503-memory-file-size-exceptions.md) | ADR-shaped | Wave 2C memory/ file-size exception decision |
| 2026-05-04 | [`20260504-doc-drift-audit-brief.md`](20260504-doc-drift-audit-brief.md) | Audit brief | PR #481 wiki-ingest drift fixes (root-level audit) |
| 2026-05-05 | [`20260505-kt-migration-w4-verification-architecture.md`](2026/20260505-kt-migration-w4-verification-architecture.md) | KT verification | W4 migration: ARCHITECTURE_ALTERNATIVES.md → memory/ (verdict: do not migrate) |
| 2026-05-05 | [`20260505-kt-migration-w4-verification-game-mechanics.md`](2026/20260505-kt-migration-w4-verification-game-mechanics.md) | KT verification | W4 migration: GAME_ENGINE_MECHANICS.md → memory/ (partial migration) |
| 2026-05-05 | [`20260505-kt-migration-w4-verification-user-journeys.md`](2026/20260505-kt-migration-w4-verification-user-journeys.md) | KT verification | W4 migration: USER_JOURNEY.md → memory/ (partial migration) |
| 2026-05-08 | [`20260508-walk-B3-spec217-3B.md`](2026/20260508-walk-B3-spec217-3B.md) | Walk report | Spec 217-3B Walk B3 (BLOCKED on deploy infra GH #566) |
| 2026-05-08 | [`20260508-walk-B3v2-spec217-3B.md`](2026/20260508-walk-B3v2-spec217-3B.md) | Walk report | Spec 217-3B Walk B3v2 (PARTIAL PASS, 15/18 ACs verified) |
| 2026-05-08 | [`20260508-walk-B4-spec217-final.md`](2026/20260508-walk-B4-spec217-final.md) | Walk report | Spec 217 final integration Walk B4 (PARTIAL, gated on GH #568) |

## By type

| Type | Definition | Examples |
|---|---|---|
| **Analysis** | Open-ended structural analysis (architecture, schema, code-paths). | `20251201-analysis-backend-db-audit.md` |
| **Report** | Validation pass with PASS/FAIL findings. | `20251201-report-game-mechanics-audit.md` |
| **Verification** | Targeted check that a specific property holds (e.g., RLS enabled). | `20251201-verification-memory-rls.md` |
| **Security review** | Security-specific audit (OWASP, OWASP-LLM, threat model). | `20251202-security-review-001.md` |
| **System audit** | Comprehensive cross-cutting system audit. | `20251202-system-audit-final-report.md` |
| **Doc sync** | Doc-vs-code drift sweep. | `20260108-doc-sync.md` |
| **Deep audit** | Output of `/deep-audit` skill. | `20260224-deep-audit.md` |
| **ADR-shaped** | Architecture-decision record format (Status / Context / Decision / Consequences). | `20260503-memory-file-size-exceptions.md` |
| **Audit brief** | Pre-fix audit identifying drift items + remediation plan (becomes a PR). | `20260504-doc-drift-audit-brief.md` |
| **KT verification** | W4 KT-migration claim-by-claim code verification. | `20260505-kt-migration-w4-verification-*.md` |

## Conventions

- **Naming**: `{YYYYMMDD}-{type}-{slug}.md` lowercase. Type matches the table above.
- **Year subdirs**: 2025/ closed; 2026/ active. New audits go in the current-year subdir; root-level audits (e.g., audit briefs that are about to drive a PR) may sit at `audits/` top level briefly.
- **PASS/FAIL discipline**: every audit ends with a verdict + per-finding severity (CRITICAL / HIGH / MEDIUM / LOW per `.claude/rules/issue-triage.md`).
- **GH-issue cross-ref**: CRITICAL/HIGH findings should reference the GH issue that tracks the fix.
- **ADR migration**: ADR-shaped audits will eventually move to `~/.claude/ecosystem-spec/decisions/` (per ADR-006); currently kept in repo until a stable in-repo ADR home is established.

## Cross-references

- Issue triage: [`.claude/rules/issue-triage.md`](../.claude/rules/issue-triage.md)
- Review-finding workflow: [`.claude/rules/review-findings.md`](../.claude/rules/review-findings.md)
- Doc index: [`docs/INDEX.md`](../docs/INDEX.md)
- Concepts: [`docs/CONCEPTS.md`](../docs/CONCEPTS.md)

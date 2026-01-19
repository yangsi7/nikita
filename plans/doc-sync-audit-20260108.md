# Documentation Sync Audit Plan

**Date**: 2026-01-08 00:15 UTC
**Project**: Nikita - AI Girlfriend Simulation Game

## Executive Summary
- **Total Findings**: 38
- **Critical**: 0 | **High**: 12 | **Medium**: 16 | **Low**: 10
- **Estimated Remediation**: 4-6 hours

---

## Findings & Remediation

### HIGH Priority (12 findings)

#### [PLAN-001] Stale Phase Section in master-plan.md
**Location**: `plans/master-plan.md:664-713`
**Evidence**: Section marks Phase 3-5 as "❌ TODO" but todos/master-todo.md shows COMPLETE
**Remediation**:
1. Remove or update Section 13 "Implementation Phases" entirely
2. It contradicts the current SDD status table which correctly shows phases complete
**Acceptance**: Section 13 removed or updated to match SDD status table

#### [PLAN-007] Missing Audit Reports for Specs 019-020
**Location**: `specs/019-admin-voice-monitoring/`, `specs/020-admin-text-monitoring/`
**Evidence**: Directories missing `audit-report.md` files (SDD violation)
**Remediation**:
1. Run `/audit specs/019-admin-voice-monitoring/spec.md`
2. Run `/audit specs/020-admin-text-monitoring/spec.md`
3. Create audit-report.md files with RETROACTIVE note
**Acceptance**: Both specs have audit-report.md files with PASS status

#### [PLAN-010] Voice Status Contradiction
**Location**: `plans/master-plan.md:34` vs `todos/master-todo.md:29`
**Evidence**: master-plan shows "Voice | ❌ Deferred" but todos shows "007 | voice-agent | ✅ 100%"
**Remediation**:
1. Update master-plan.md implementation order table
2. Change Spec 007 from "❌ Deferred to Phase 4" to "✅ COMPLETE (Jan 2026)"
**Acceptance**: master-plan.md shows Voice Agent as COMPLETE

#### [CLAUDE-002] Voice Test Count Conflict
**Location**: `nikita/CLAUDE.md:20,90` vs `nikita/agents/voice/CLAUDE.md:9`
**Evidence**: nikita/CLAUDE.md claims "124 tests", voice/CLAUDE.md claims "186 tests"
**Remediation**:
1. Run `pytest tests/agents/voice/ --co -q | wc -l` to verify actual count
2. Update both files to use consistent number (186 is newer)
**Acceptance**: Both CLAUDE.md files show identical voice test count

#### [CLAUDE-003] Spec Count Discrepancy (14 vs 20)
**Location**: `CLAUDE.md:443`
**Evidence**: Claims "14 specs" but actual count is 20 (specs 001-020 exist)
**Remediation**:
1. Update line 443 from "14 specs" to "20 specs"
2. Add entries for specs 015-020 to the specification list
**Acceptance**: CLAUDE.md correctly states 20 specs with complete list

#### [CLAUDE-004] Admin Portal Status Outdated
**Location**: `todos/master-todo.md:30`
**Evidence**: Shows "Admin 0%" but admin pages exist (voice, text, prompts, users, jobs)
**Remediation**:
1. Update spec 008 status from "Admin 0%" to "Admin 100%"
2. Update overall Portal status from "70%" to "85%+"
**Acceptance**: Admin status reflects actual implementation

#### [IMP-001] Twilio Integration Marked TODO But Voice Complete
**Location**: `memory/integrations.md:266`, `memory/architecture.md:264`
**Evidence**: Shows "Twilio | Voice call initiation | ❌ TODO" but ElevenLabs voice deployed
**Remediation**:
1. Update integrations.md line 266 from "❌ TODO" to "✅ Configured (ElevenLabs)"
2. Clarify voice uses ElevenLabs Conversational AI 2.0, not Twilio
**Acceptance**: Integrations.md correctly shows voice as complete via ElevenLabs

#### [IMP-003] Portal Admin Pages Exist But Documented as 0%
**Location**: `todos/master-todo.md:69`
**Evidence**: `portal/src/app/admin/` contains 8+ admin pages created Jan 2026
**Remediation**:
1. Update "Admin UI: User list, user detail, game controls" task
2. Mark as [x] complete (not [ ] TODO)
**Acceptance**: Admin UI tasks marked complete

#### [IMP-014] Spec Inventory Shows 14, Actual is 18-20
**Location**: `README.md:212`, `memory/architecture.md:169-192`
**Evidence**: Docs claim "14 specs" but specs 015-020 added Dec-Jan
**Remediation**:
1. Update README.md to show 20 specs
2. Update memory/architecture.md spec table to include all 20
**Acceptance**: All documentation shows correct spec count

#### [HYG-001] 19 Stale Artifacts in docs-to-process
**Location**: `docs-to-process/` (536KB, 19 files)
**Evidence**: Oldest artifact Dec 13, 2025 (25 days old) - violates 7-day rule
**Remediation**:
1. Run `/streamline-docs` to process all artifacts
2. Consolidate findings into memory/ or docs/
3. Delete processed files
**Acceptance**: docs-to-process/ contains only files < 7 days old

#### [HYG-002] Specs 019-020 Missing Audit Reports
**Location**: `specs/019-admin-voice-monitoring/`, `specs/020-admin-text-monitoring/`
**Evidence**: Missing audit-report.md files
**Remediation**: Same as PLAN-007
**Acceptance**: Both specs have audit-report.md

#### [SPEC-019/020] SDD Violation - Code Before Spec
**Location**: `specs/019-admin-voice-monitoring/`, `specs/020-admin-text-monitoring/`
**Evidence**: Admin monitoring code deployed Jan 7, specs created Jan 8
**Remediation**:
1. Document SDD violation in audit-report.md as RETROACTIVE
2. Add note to CLAUDE.md explaining rapid deployment decision
3. Mark as exception, not precedent
**Acceptance**: Violation documented with rationale

---

### MEDIUM Priority (16 findings)

#### [PLAN-002] Orphaned Session Plan Reference
**Location**: `plans/master-plan.md:69`
**Evidence**: References `/Users/yangsim/.claude/plans/whimsical-spinning-nygaard.md`
**Remediation**: Remove reference or integrate content into plans/
**Acceptance**: No external session plan references

#### [PLAN-003] Outdated Master Plan YAML Metadata
**Location**: `plans/master-plan.md:1-11`
**Evidence**: `updated: 2025-12-24` is 15 days old
**Remediation**: Update YAML to current date and align terminology
**Acceptance**: YAML shows correct date and uses "specs" not "phases"

#### [PLAN-004] SPEC_INVENTORY.md Incomplete
**Location**: `specs/SPEC_INVENTORY.md:3-5`
**Evidence**: Shows 18 specs but 20 exist
**Remediation**: Add specs 019-020 to inventory table
**Acceptance**: SPEC_INVENTORY.md lists all 20 specs

#### [PLAN-008] YAML Phase Model Mismatch
**Location**: `plans/master-plan.md:7-9`
**Evidence**: Uses phases 1-11 but project uses specs 001-020
**Remediation**: Replace phase tracking with spec-based status
**Acceptance**: YAML uses `specs_complete` not `phases_complete`

#### [PLAN-009] Orphaned .claude/plans Reference
**Location**: `plans/master-plan.md:69`
**Evidence**: References user's personal Claude session directory
**Remediation**: Remove reference (duplicate of PLAN-002)
**Acceptance**: Same as PLAN-002

#### [CLAUDE-001] Voice Module Count Mismatch
**Location**: `nikita/CLAUDE.md:20,90`
**Evidence**: Claims "13 files" but actual count is 14
**Remediation**: Update to "14 files"
**Acceptance**: nikita/CLAUDE.md shows 14 voice modules

#### [CLAUDE-006] Missing Voice/Text Monitoring Specs Documentation
**Location**: `CLAUDE.md:574-580`
**Evidence**: Specs 019-020 not documented in specs list
**Remediation**: Add entries for admin monitoring specs
**Acceptance**: CLAUDE.md includes specs 019-020 in list

#### [CLAUDE-007] Portal Status Discrepancy
**Location**: `CLAUDE.md:278`
**Evidence**: Shows "Phase 5 ⚠️ IN PROGRESS (Portal 85%)" but admin complete
**Remediation**: Update Portal status to "95%" or "near-complete"
**Acceptance**: Status reflects actual completion

#### [IMP-007] Voice Endpoints Naming Outdated
**Location**: `memory/backend.md:370-389`, `memory/integrations.md:414-442`
**Evidence**: Shows `/voice/elevenlabs/...` but actual is `/api/v1/voice/...`
**Remediation**: Update endpoint paths in documentation
**Acceptance**: Docs show correct API paths with /api/v1/ prefix

#### [IMP-013] ElevenLabs Agent ID Abstraction Overstated
**Location**: `memory/integrations.md:394-412`, `memory/architecture.md:58`
**Evidence**: Claims 6 different agent IDs but all point to same agent
**Remediation**: Clarify abstraction exists but uses single agent currently
**Acceptance**: Docs note "single agent ID, multi-agent capability available"

#### [HYG-003] Floating Docs Outside Approved Files
**Location**: `docs/portal-testing-report.md`, `docs/archive/20251214-MAGIC_LINK_FIX-archived.md`
**Evidence**: Not referenced in master files, superseded content
**Remediation**: Delete both files
**Acceptance**: No floating docs in docs/ root

#### [HYG-004] docs/ Structure Inconsistency
**Location**: `docs/` directory
**Evidence**: `docs/game/` duplicates `memory/`, decisions/ contains audits not ADRs
**Remediation**:
1. Consolidate docs/game/ into memory/
2. Rename decisions/ to audits/ or clarify purpose
**Acceptance**: No duplicate content between docs/ and memory/

#### [HYG-007] Superseded Portal Testing Report
**Location**: `docs/portal-testing-report.md`
**Evidence**: Dec 8, 2025 - superseded by newer E2E tests
**Remediation**: Delete (duplicate of HYG-003)
**Acceptance**: File deleted

#### [SPEC-008] Portal Status Underestimated
**Location**: `specs/008-player-portal/spec.md`
**Evidence**: Spec claims 70% but actual is 85%+
**Remediation**: Update spec status to reflect actual completion
**Acceptance**: Spec 008 status shows 85%+

#### [SPEC-016] Ambiguous Ready/In-Progress Status
**Location**: `specs/016-admin-debug-portal/`
**Evidence**: Marked "ready for /implement" but code exists
**Remediation**: Clarify status - either "in progress" or acknowledge prep work
**Acceptance**: Status is unambiguous

#### [SPEC-017] Status Inconsistency (96% vs 78%)
**Location**: `todos/master-todo.md` vs `specs/017-enhanced-onboarding/tasks.md`
**Evidence**: master-todo shows 96%, tasks.md shows 78% (18/23 complete)
**Remediation**: Update master-todo.md to 78%
**Acceptance**: Both files show consistent percentage

---

### LOW Priority (10 findings)

#### [PLAN-005] Test Coverage Claims Inconsistency
**Location**: `todos/master-todo.md` vs `event-stream.md`
**Evidence**: Event stream claims 1,623 tests, sum of spec tests ~1,200-1,300
**Remediation**: Run pytest --collect-only and update with authoritative count
**Acceptance**: Test count verified and consistent

#### [PLAN-006] README Phase Status Stale
**Location**: `README.md:190-209`
**Evidence**: Phase 5 "IN PROGRESS" but admin work done
**Remediation**: Update phase status or simplify
**Acceptance**: README reflects current state

#### [IMP-002] Celery/Redis Removal - OK
**Status**: No action needed - documentation matches reality

#### [IMP-004] Voice Module Count - OK (after CLAUDE-001 fix)
**Status**: Fixed by CLAUDE-001

#### [IMP-005] Settings Line Numbers Off
**Location**: `memory/architecture.md:196-204`
**Evidence**: Line references ~50 off from actual
**Remediation**: Update line numbers or remove specific references
**Acceptance**: Line numbers accurate or removed

#### [IMP-006] NikitaMemory Graphiti - OK
**Status**: No action needed - documentation matches reality

#### [IMP-010] Engine Module Structure Minor
**Location**: `memory/architecture.md:70-76`
**Evidence**: `nikita/engine/conflicts/` marked TODO but partial
**Remediation**: Update status from "TODO" to "Partial"
**Acceptance**: Status reflects partial implementation

#### [CLAUDE-010] Git Workflow Scopes Incomplete
**Location**: `CLAUDE.md:341`
**Evidence**: Missing scopes: voice, memory, context, config
**Remediation**: Add missing scopes to list
**Acceptance**: Scopes list complete

#### [HYG-006] docs/README.md Outdated
**Location**: `docs/README.md`
**Evidence**: Shows Phase 2 at 95%, old spec status
**Remediation**: Update with current phase and spec status
**Acceptance**: docs/README.md current

#### [HYG-008] Build Artifacts in Version Control
**Location**: `.pytest_cache`
**Evidence**: Should be in .gitignore
**Remediation**: Add to .gitignore if not present
**Acceptance**: .gitignore includes cache directories

---

## Master Plan Integration

Add to `plans/master-plan.md`:

```markdown
## Documentation Sync Audit (2026-01-08)
See: [plans/doc-sync-audit-20260108.md](./doc-sync-audit-20260108.md)
Priority: 0 critical, 12 high items
Status: Generated - awaiting implementation
```

---

## Master Todo Integration

Add to `todos/master-todo.md`:

```markdown
### Documentation Sync (2026-01-08)
- [ ] Process 19 stale docs-to-process artifacts (HYG-001)
- [ ] Create audit-report.md for specs 019-020 (PLAN-007, HYG-002)
- [ ] Update master-plan.md Section 13 (PLAN-001)
- [ ] Update master-plan.md Voice status (PLAN-010)
- [ ] Update CLAUDE.md spec count 14→20 (CLAUDE-003)
- [ ] Update todos/master-todo.md Admin 0%→100% (CLAUDE-004)
- [ ] Update integrations.md Twilio→ElevenLabs (IMP-001)
- [ ] Update all files with correct voice test count (CLAUDE-002)
- [ ] Delete floating docs in docs/ (HYG-003, HYG-007)
- [ ] Consolidate docs/game/ into memory/ (HYG-004)
- [ ] Update SPEC_INVENTORY.md to 20 specs (PLAN-004)
- [ ] Update README.md spec count (IMP-014)
```

---

## Severity Definitions

| Level | Definition | Action |
|-------|------------|--------|
| **CRITICAL** | Docs contradict reality, blocks understanding | Fix immediately |
| **HIGH** | Significant outdated info, misleading claims | Fix this week |
| **MEDIUM** | Minor inaccuracies, missing details | Fix when convenient |
| **LOW** | Style issues, minor improvements | Optional |

---

## Root Cause Analysis

**Primary Cause**: Documentation sync lag after rapid implementation (Jan 3-8, 2026)

**Timeline**:
- Dec 24: master-plan.md last updated
- Jan 1-3: Voice agent deployed, admin endpoints created
- Jan 7-8: Admin monitoring pages created, OTP auth fixed
- Jan 8: This audit identifies 38 findings

**Gap**: 15 days of implementation without documentation sync.

**Prevention**: Weekly documentation sync cadence, process docs-to-process/ regularly.

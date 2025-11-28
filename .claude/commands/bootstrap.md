---
description: Verify Intelligence Toolkit installation and system health
allowed-tools: Bash($CLAUDE_PROJECT_DIR/.claude/hooks/system-integrity-check.sh:*)
---

# Bootstrap & System Health Verification

Verify that all Intelligence Toolkit components are correctly installed and functioning.

## Verification Steps

Run comprehensive system integrity check:

!`"$CLAUDE_PROJECT_DIR"/.claude/hooks/system-integrity-check.sh`

## What This Checks

**Component Inventory**:
- Skills (expected: ≥10)
- Slash Commands (expected: ≥7)
- Agents (expected: 4)
- Templates (expected: ≥8)
- Hooks (expected: ≥2)
- Shared Imports (expected: 2)

**Critical Integrations**:
- All agents import constitution.md
- All agents have `model: inherit`
- All commands have `description` field (SlashCommand tool compatibility)
- Character budget within limits

**Workflow Chains**:
- Constitution imports present in all agents
- Template references valid
- Hooks use portable paths ($CLAUDE_PROJECT_DIR)

**Constitutional Compliance**:
- All 7 articles enforced across system
- Intelligence-first approach verified
- Evidence-based reasoning enabled

## Expected Output

**System Health Score**: Should be ≥ 90/100 for production readiness

**Status**:
- ✅ **PRODUCTION READY** (90-100 score, 0 critical issues)
- ⚠️  **REVIEW NEEDED** (75-89 score, or warnings present)
- ❌ **NOT READY** (<75 score, or critical issues)

## If Issues Found

**Missing Components**: Re-run install-toolkit.sh script
**Configuration Issues**: Check .claude/settings.json
**Integration Issues**: Verify @ imports resolve correctly
**Index Missing**: Run `/index` to generate PROJECT_INDEX.json

## Post-Bootstrap Steps

After successful bootstrap:

1. **Generate project index** (if not exists):
   ```bash
   /index
   ```

2. **Start development** with intelligence-first workflow:
   ```bash
   project-intel.mjs --overview --json
   ```

3. **Use SDD workflow** for new features:
   ```bash
   /feature "Your feature description"
   ```

4. **Review system documentation**:
   - Quick start: `.claude/templates/BOOTSTRAP_GUIDE.md`
   - Full architecture: `docs/architecture/system-overview.md`
   - Validation report: `VALIDATION_REPORT.md`

---

**Last Validated**: This system achieved 100/100 health score in comprehensive validation

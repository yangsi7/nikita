---
description: Validate Intelligence Toolkit system integrity including components, workflows, best practices, and constitutional compliance (project)
allowed-tools: Bash(.claude/hooks/system-integrity-check.sh:*), Read, Grep
argument-hint: [--verbose] [--fix]
---

## Pre-Execution

!`.claude/hooks/system-integrity-check.sh $ARGUMENTS`

# System Integrity Validation

You are now executing the `/system-integrity` command. This command performs comprehensive validation of the Intelligence Toolkit system.

## Validation Report

The pre-execution check above has validated:

1. **Component Inventory**
   - Skills, Commands, Agents, Templates, Hooks
   - YAML frontmatter validity
   - @ import resolution

2. **Workflow Chain Integrity**
   - Automated workflow connections
   - SlashCommand tool compatibility
   - Agent delegation patterns

3. **Best Practices Compliance**
   - Skill line count limits (<500 recommended)
   - Hook JSON output format
   - Template CoD^Σ usage
   - Constitutional imports

4. **Constitutional Compliance**
   - Article enforcement in skills
   - Quality gates configuration
   - Intelligence-first approach

5. **Documentation System**
   - memory/ directory structure (product.md, constitution.md, domain docs)
   - todo/master-todo.md feature tracking
   - specs/$FEATURE/ artifact organization

## Your Task

Review the validation report above and:

1. **If all checks PASS (✓)**:
   - System is healthy
   - No action needed
   - Document validation timestamp

2. **If warnings present (⚠️)**:
   - Review each warning
   - Assess criticality
   - Consider fixes if high-impact

3. **If failures present (❌)**:
   - CRITICAL: System integrity compromised
   - Review specific violations
   - Plan remediation
   - Re-run validation after fixes

## Options

**--verbose**: Show detailed check output
**--fix**: Attempt automated fixes for common issues (use with caution)

## Remediation Workflow

For failures:

1. **Document findings**: Note which checks failed
2. **Prioritize**: Critical > Important > Minor
3. **Fix systematically**: One category at a time
4. **Re-validate**: Run `/system-integrity` after each fix
5. **Verify**: Ensure no regressions introduced

## Expected Output

The validation script produces:

```
=== Intelligence Toolkit System Integrity Check ===

Component Inventory: ✓ PASS (10/10 skills, 12/12 commands, ...)
Workflow Chains: ⚠️ WARNING (1 connection issue)
Best Practices: ❌ FAIL (9 skills exceed 500 lines)
Constitutional Compliance: ✓ PASS

Overall: ⚠️ WARNINGS - Review recommended
```

## Follow-Up Actions

Based on validation results:

- **All PASS**: System ready for production use
- **Warnings**: Review and address high-impact warnings
- **Failures**: Execute remediation plan before production use

## Related Documentation

- Best Practices: @docs/reference/claude-code-docs/claude-code-skills-best-practices.md
- Constitution: @.claude/shared-imports/constitution.md
- Architecture: @docs/architecture/agent-skill-integration.md

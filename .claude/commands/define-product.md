---
description: Create user-centric product definition (product.md) by analyzing the repository and clarifying user needs
allowed-tools: Bash(project-intel.mjs:*), Read, Write, AskUserQuestion
---

# Define Product

Create a comprehensive, user-centric product definition following the define-product skill workflow.

## Prerequisites Check

!`test -f memory/product.md && echo "⚠️ memory/product.md already exists" || echo "✓ Creating new memory/product.md"`

---

## Invoke Skill

Follow the **define-product skill** (@.claude/skills/define-product/SKILL.md) to:

1. **Gather intelligence** - Query project-intel.mjs for repository insights
2. **Infer characteristics** - Analyze B2B/B2C signals, primary users, core problems
3. **Clarify ambiguities** - Ask max 5 structured questions if signals conflict
4. **Define 3 personas** - Use Jobs-to-be-Done framework
5. **Map 2-3 journeys** - Use CoD^Σ notation
6. **Generate memory/product.md** - Use template at @.claude/templates/product.md
7. **Validate** - Ensure NO technical decisions, only user needs

**Critical**: memory/product.md must be PURELY user-centric with NO tech stack, architecture, or implementation details.

---

## Next Step

After creating memory/product.md, run `/generate-constitution` to derive technical principles FROM these user needs.

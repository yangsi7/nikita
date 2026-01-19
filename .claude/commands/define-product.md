---
description: Create user-centric product definition (product.md) - SDD Phase 1
allowed-tools: Bash(project-intel.mjs:*), Read, Write, AskUserQuestion
---

# Define Product - SDD Phase 1

Create a comprehensive, user-centric product definition using the unified SDD skill.

## Unified Skill Routing

This command routes to **SDD Phase 1: Product Definition** via the unified skill at @.claude/skills/sdd/SKILL.md.

**Phase 1 Workflow:** @.claude/skills/sdd/workflows/01-product-definition.md

---

## Prerequisites

!`test -f memory/product.md && echo "⚠️ memory/product.md already exists" || echo "✓ Creating new memory/product.md"`

---

## Phase 1 Process

Follow the **sdd skill Phase 1** workflow:

1. **Intelligence Gathering**
   - Query project-intel.mjs for codebase signals
   - Identify B2B/B2C indicators, user types, problem domains

2. **Clarification** (max 5 questions)
   - Ask only if signals conflict
   - Validate inferences with user

3. **Define Personas** (3)
   - Use Jobs-to-be-Done framework
   - Include pain points, goals, context

4. **Map Journeys** (2-3)
   - Key user flows with emotional states
   - Use CoD^Σ notation for transitions

5. **Generate memory/product.md**
   - Use template at @.claude/templates/product.md
   - PURELY user-centric (NO tech stack)

---

## Quality Gate

**Article IV Compliance**: memory/product.md must contain:
- ✓ User personas with JTBD
- ✓ User journeys with emotional states
- ✓ Problems to solve (user-centric)
- ✓ Success metrics (user outcomes)
- ✗ NO implementation details
- ✗ NO technology choices

---

## Auto-Chain

After Phase 1 completes successfully:
→ System prompts for Phase 2 (/generate-constitution)

---

## Next Step

After creating memory/product.md, run `/generate-constitution` to derive technical principles FROM user needs.

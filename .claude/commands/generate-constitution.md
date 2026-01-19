---
description: Derive technical principles (constitution.md) from product.md - SDD Phase 2
allowed-tools: Read, Write, Edit
---

# Generate Constitution - SDD Phase 2

Derive technical development principles FROM user needs documented in product.md with complete traceability.

## Unified Skill Routing

This command routes to **SDD Phase 2: Constitution** via the unified skill at @.claude/skills/sdd/SKILL.md.

**Phase 2 Workflow:** @.claude/skills/sdd/workflows/02-constitution.md

---

## Prerequisites

!`test -f memory/product.md && echo "✓ memory/product.md exists" || echo "⚠️ ERROR: Run /define-product first (Phase 1 required)"`

---

## Phase 2 Process

Follow the **sdd skill Phase 2** workflow:

1. **Load Product Definition**
   - Read memory/product.md
   - Extract user needs, personas, journeys, North Star

2. **Map to Technical Requirements**
   - Use CoD^Σ derivation pattern
   - Every principle traces to user need

3. **Derive 7 Articles**
   - Article I: Architecture
   - Article II: Data Integrity
   - Article III: Performance
   - Article IV: Security
   - Article V: User Experience
   - Article VI: Development Process
   - Article VII: Scalability

4. **Create Derivation Map**
   - Full traceability from product.md → constitution.md
   - Evidence chain for each principle

5. **Generate constitution.md**
   - Save to memory/constitution.md
   - Copy to .claude/shared-imports/constitution.md

---

## Derivation Pattern

```
User Need (product.md) ≫ Capability Required → Technical Approach ≫ Constraint (constitution.md)
```

**Example:**
```
"User needs fast response" (persona.pain_point)
  ≫ Sub-200ms API latency required
  → Cache-first architecture
  ≫ Article III: "All endpoints MUST respond < 200ms p95"
```

---

## Quality Gate

**Article II Compliance**: Constitution must have:
- ✓ Every principle traceable to product.md
- ✓ CoD^Σ evidence chains
- ✓ Version and ratified_date metadata
- ✓ derived_from reference to product.md

---

## Output Location

Primary: `memory/constitution.md`
Import: `.claude/shared-imports/constitution.md`

---

## Usage After Generation

The constitution guides all subsequent phases:
- **Phase 3** (/feature): Spec must align with constitution
- **Phase 5** (/plan): Plan validates against principles
- **Phase 7** (/audit): Checks constitution compliance
- **Phase 8** (/implement): Code enforces constraints

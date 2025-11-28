---
description: Derive technical development principles (constitution.md) FROM user needs in product.md using evidence-based CoD^Σ reasoning
allowed-tools: Read, Write, Edit
---

# Generate Constitution

Derive technical principles FROM user needs documented in product.md, creating constitution.md with complete traceability.

## Prerequisites Check

!`test -f memory/product.md && echo "✓ memory/product.md exists" || echo "⚠️ ERROR: Run /define-product first to create memory/product.md"`

---

## Invoke Skill

Follow the **generate-constitution skill** (@.claude/skills/generate-constitution/SKILL.md) to:

1. **Load memory/product.md** - Extract user needs from personas, journeys, "Our Thing", North Star
2. **Map to technical requirements** - Use CoD^Σ derivation pattern
3. **Derive principles** - Create Articles with full evidence chains
4. **Organize by category** - Group into 7 standard Articles (Architecture, Data, Performance, Security, UX, Development, Scalability)
5. **Create derivation map** - Document complete traceability (product.md source → principle)
6. **Add metadata** - Version, ratified date, derived_from reference

**Critical**: Every principle MUST trace back to a specific user need via CoD^Σ reasoning.

**Derivation Pattern**:
```
User Need (product.md) ≫ Capability Required → Technical Approach ≫ Specific Constraint (constitution.md)
```

---

## Output Location

Write constitution to: `memory/constitution.md`

The constitution is also copied to `.claude/shared-imports/constitution.md` for skill imports via `@.claude/shared-imports/constitution.md`.

---

## Next Step

The constitution now guides all development decisions. Use it during:
- `/plan` - Implementation planning (validate against constitutional principles)
- `/implement` - Code implementation (enforce constitutional constraints)
- `/verify` - Verification (check compliance with constitution)

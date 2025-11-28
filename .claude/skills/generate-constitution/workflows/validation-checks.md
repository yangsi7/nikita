# Validation Checks: Constitution Quality

**Purpose**: Ensure constitution.md meets quality standards with complete derivation chains and proper classification.

---

## Quality Checklist

### For Each Article

- [ ] **Has explicit product.md reference** (file:section:line)
- [ ] **User need quoted verbatim** (exact quote from product.md)
- [ ] **CoD^Σ derivation chain documented** (uses ≫ → operators)
- [ ] **Principle is specific and measurable** (not vague)
- [ ] **Verification method defined** (how to validate compliance)
- [ ] **Classification clear** (NON-NEGOTIABLE | SHOULD | MAY)

### Example Pass

```markdown
## Article II: Real-Time Data Synchronization (NON-NEGOTIABLE) ✓

### User Need Evidence
From product.md:Persona1:Pain1:118 ✓
- "Manually copying campaign metrics from 7 different tools... wastes 2 hours/week" ✓

### Technical Derivation (CoD^Σ)
Manual data collection pain (product.md:Persona1:Pain1:118) ✓
  ⊕ Real-time visibility promise (product.md:OurThing:283)
  ≫ Automated cross-platform sync required
  → API polling or webhooks for each platform
  ≫ <15 minute maximum data latency

### Principle
All connected platforms MUST sync data automatically with <15 minute maximum latency ✓

### Verification
Monitor data staleness. Alert if any source exceeds 15-minute threshold. ✓
```

### Example Fail

```markdown
## Article II: Use React (SHOULD) ❌

### Principle
Frontend should use React ❌ (No user need evidence)

### Rationale
React is popular ❌ (Tech preference, not user need)
```

---

## Overall Validation

- [ ] **No orphaned principles** (all trace to user needs in product.md)
- [ ] **All "Our Thing" items have NON-NEGOTIABLE principles**
- [ ] **All pain resolutions have technical support**
- [ ] **Derivation map complete** (every Article has row)
- [ ] **Version metadata current** (version, ratified date, derived_from)
- [ ] **7 standard Articles present** (Architecture, Data, Performance, Security, UX, Development, Scalability)

---

## Quick Tests

### Test 1: "Can I delete this without breaking a user promise?"

- **YES** → Might not be needed, review if it should exist
- **NO** → Should be NON-NEGOTIABLE

**Example**:
- "Can I delete <15min sync latency?" → NO (breaks "instant visibility" promise) → NON-NEGOTIABLE ✓
- "Can I delete 'prefer TypeScript'?" → YES (preference, not promise) → SHOULD or remove

### Test 2: "Can I trace this to a specific user pain?"

- **YES** → Good principle, keep it
- **NO** → Remove it (orphaned tech preference)

**Example**:
- "Real-time sync" → YES (traces to Persona1:Pain1:118: manual copying) ✓
- "Use microservices" → NO (no user pain mentioned) → Remove ❌

### Test 3: "Does this enable 'Our Thing'?"

- **YES** → Upgrade to NON-NEGOTIABLE
- **NO** → Evaluate if needed

**Example**:
- "<2s dashboard load" → YES (enables "instant visibility") → NON-NEGOTIABLE ✓
- "Code coverage >80%" → NO (internal quality metric) → SHOULD

---

## Validation Workflow

**Step 1: Validate Each Article**
```bash
For each Article:
  Check product.md reference exists
  Check user need quote is verbatim
  Check CoD^Σ derivation present
  Check principle is measurable
  Check verification method defined
  Check classification justified
```

**Step 2: Validate Overall Structure**
```bash
Check no orphaned principles
Check all "Our Thing" items → NON-NEGOTIABLE
Check derivation map complete
Check version metadata present
```

**Step 3: Run Quick Tests**
```bash
For each principle:
  Run "Can I delete?" test
  Run "Can I trace?" test
  Run "Does this enable?" test
```

---

## Common Issues

### Issue: Article has no product.md reference

**Symptom**: "Technical Derivation" section missing or no product.md:line reference

**Solution**: Either find the user need in product.md OR delete the Article (orphaned tech preference)

### Issue: Vague principle

**Symptom**: "System should be performant" or "Use best practices"

**Solution**: Make specific and measurable:
- ✓ "Dashboard MUST load in <2 seconds (p95)"
- ✓ "All code MUST pass TypeScript strict mode checks"

### Issue: "Our Thing" marked SHOULD

**Symptom**: Key differentiator not marked NON-NEGOTIABLE

**Solution**: Upgrade to NON-NEGOTIABLE (core promise to users)

### Issue: Derivation map incomplete

**Symptom**: Articles exist but missing from derivation map table

**Solution**: Add rows for ALL Articles to the Appendix table

---

## Validation Output

After validation completes:

**PASS**: All checks green ✓
- Constitution.md is ready for use
- All technical decisions can reference these principles
- Proceed to feature development

**FAIL**: Issues found ❌
- Fix identified issues
- Re-run validation
- Do NOT proceed until all checks pass

---

## Next Action After Validation

**If PASS**:
- Share constitution.md with team
- Use as guide for ALL technical decisions
- Reference in feature specs and plans

**If FAIL**:
- Fix issues identified in validation
- Re-run validation checks
- Only proceed when all checks pass

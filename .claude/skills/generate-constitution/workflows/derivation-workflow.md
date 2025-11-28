# Derivation Workflow: Generate Constitution from Product.md

**Purpose**: Create constitution.md by deriving technical principles FROM user needs documented in product.md.

**Pattern**: User Need (product.md) ≫ Capability Required → Technical Approach ≫ Specific Constraint (constitution.md)

---

## Step 1: Load Product Definition

**Read product.md fully**:
```bash
Read product.md
```

**Extract from each section**:

1. **Personas → Pain Points**: What frustrates users?
   - Example: "Manually copying data from 7 tools wastes 2 hours/week"
   - These become NON-NEGOTIABLE efficiency principles

2. **User Journeys → Requirements**: What capabilities are needed?
   - Example: "User creates report in <10 seconds"
   - These become performance constraints

3. **"Our Thing"**: What's the key differentiator?
   - Example: "Instant cross-platform visibility"
   - These become NON-NEGOTIABLE core principles

4. **North Star Metric**: What's the success measure?
   - Example: "Weekly Active Users engage with dashboard"
   - This drives usage and performance principles

---

## Step 2: Map User Needs to Technical Requirements

**Pattern**: User Need ≫ Capability → Technical Approach ≫ Constraint

### Example 1: From Pain Point

```markdown
product.md:Persona1:Pain1:118: "Manually copying data from 7 tools wastes 2 hours/week"
  ≫ Automated cross-platform data sync required
  → API integrations with automatic refresh
  ≫ <15 minute data latency constraint
→ Constitution Article: Real-Time Data Sync (<15min latency, NON-NEGOTIABLE)
```

### Example 2: From "Our Thing"

```markdown
product.md:OurThing:283: "Instant cross-platform visibility"
  ≫ Dashboard load in <2 seconds required
  → Optimized queries + caching strategy
  ≫ Performance budget: <2s p95 load time
→ Constitution Article: Performance Standards (<2s dashboard, NON-NEGOTIABLE)
```

### Example 3: From User Journey

```markdown
product.md:Journey2:Step3:92: "User creates report and shares with team"
  ≫ Report generation + sharing capability
  → Report engine + access control
  ≫ <10s report generation, role-based permissions
→ Constitution Article: Reporting Performance (<10s generation, NON-NEGOTIABLE)
```

---

## Step 3: Derive Technical Principles

**For each user need**, create an Article using this structure:

```markdown
## Article N: [Principle Name] (NON-NEGOTIABLE | SHOULD | MAY)

### User Need Evidence
From product.md:[section]:[line]
- [Quote exact user need verbatim]

### Technical Derivation (CoD^Σ)
[User Need from product.md]
  ⊕ [Related needs if multiple sources]
  ≫ [Capability Required]
  → [Technical Approach]
  ≫ [Specific Constraint]

### Principle
[Clear, specific technical constraint]
1. [Specific requirement with measurable criteria]
2. [Specific requirement with measurable criteria]
3. [Specific requirement with measurable criteria]

### Rationale
[Why this serves the user need - explain the connection]

### Verification
[How to validate compliance - specific checks, monitoring, tests]
```

### Example: Real-Time Data Synchronization

```markdown
## Article II: Real-Time Data Synchronization (NON-NEGOTIABLE)

### User Need Evidence
From product.md:Persona1:Pain1:118
- "Manually copying campaign metrics from 7 different tools... wastes 2 hours/week"

### Technical Derivation (CoD^Σ)
Manual data collection pain (product.md:Persona1:Pain1:118)
  ⊕ Real-time visibility promise (product.md:OurThing:283)
  ≫ Automated cross-platform sync required
  → API polling or webhooks for each platform
  ≫ <15 minute maximum data latency

### Principle
1. All connected platforms MUST sync data automatically with <15 minute maximum latency
2. NO manual data entry workflows permitted
3. All integrations MUST use webhooks where available, polling otherwise (max 5min interval)

### Rationale
Eliminates 2hr/week manual copying pain while enabling "instant visibility" promise. Data freshness directly impacts user trust and decision quality.

### Verification
Monitor data staleness for each integration. Alert if any source exceeds 15-minute threshold. Dashboard shows last-sync timestamp per platform.
```

---

## Step 4: Organize by Category

Group principles into standard Articles:

1. **Article I: Architecture Patterns** - System-level (microservices, event-driven, etc.)
2. **Article II: Data & Integration** - Database, API, sync patterns
3. **Article III: Performance & Reliability** - SLAs, latency, uptime
4. **Article IV: Security & Privacy** - Auth, encryption, compliance
5. **Article V: User Experience** - UI constraints, accessibility
6. **Article VI: Development Process** - Testing, deployment, quality
7. **Article VII: Scalability** - Growth constraints, capacity

**Priority within each Article**:
- NON-NEGOTIABLE first (breaks user promises if violated)
- SHOULD next (strong preferences)
- MAY last (flexibility allowed)

---

## Step 5: Create Derivation Map

Document complete traceability:

```markdown
## Appendix: Constitution Derivation Map

| Article | Product.md Source | User Need | Technical Principle |
|---------|-------------------|-----------|---------------------|
| Article II | Persona1:Pain1:118 | Eliminate 2hr/week manual copying | <15min sync latency |
| Article V | Persona2:Demographics:65 | Age 65-75, vision decline | 20px min font size |
| Article III | OurThing:283 | "Instant visibility" | <2s dashboard load |
```

This enables:
- Tracing any principle back to user need
- Identifying orphaned principles (REMOVE THEM)
- Validating all user needs are addressed

---

## Step 6: Version & Metadata

```markdown
---
version: 1.0.0
ratified: YYYY-MM-DD
derived_from: product.md (v1.0)
---

# Development Constitution

**Purpose**: Technical principles derived FROM user needs

**Amendment Process**: See Article VIII

**Derivation Evidence**: See Appendix
```

---

## Output

Creates `constitution.md` in project root with:
- 7 standard Articles organized by category
- Each Article with full derivation chain to product.md
- NON-NEGOTIABLE vs SHOULD vs MAY classification
- Complete derivation map (traceability table)
- Version metadata and amendment process

**Template**: Use `@.claude/templates/product-constitution.md`

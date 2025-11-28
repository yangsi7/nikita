---
spec_id: ""
type: "analysis-spec"
created_by: ""
status: "draft"
naming_pattern: "YYYYMMDD-HHMM-analysis-spec-{id}.md"
---

# Analysis Specification: [Title]

## Objective
<!-- What question are we trying to answer? -->

**Question:**
**Success Criteria:**

---

## Scope

### In-Scope
- [Component/file/feature to analyze]
- [Component/file/feature to analyze]

### Out-of-Scope
- [What we're NOT analyzing]
- [What we're NOT analyzing]

### Boundaries
**Start:** [entry point]
**End:** [exit point]
**Depth:** [how deep to trace]

---

## Intel Queries

### Required Queries
<!-- These MUST be executed before any file reads -->

1. **Overview Query**
   ```bash
   project-intel.mjs --overview --json > /tmp/analysis_overview.json
   ```
   **Purpose:** [why we need this]

2. **Search Query**
   ```bash
   project-intel.mjs --search "[pattern]" --type [type] --json
   ```
   **Purpose:** [why we need this]

3. **Symbols Query**
   ```bash
   project-intel.mjs --symbols [file] --json
   ```
   **Purpose:** [why we need this]

4. **Dependencies Query**
   ```bash
   project-intel.mjs --dependencies [file] --direction [up/down] --json
   ```
   **Purpose:** [why we need this]

### Optional Queries
- [Additional queries if needed]

---

## MCP Verifications

### Library Documentation (Ref MCP)
- **Library:** [library name]
- **Query:** [what to verify]
- **Purpose:** [why authoritative source needed]

### Database Schema (Supabase MCP)
- **Tables:** [table names]
- **Query:** [schema elements to verify]
- **Purpose:** [why authoritative source needed]

### Other MCPs
- **Tool:** [MCP tool]
- **Query:** [query details]

---

## Success Criteria
<!-- How do we know when analysis is complete? -->

- [ ] All intel queries executed
- [ ] MCP verifications complete
- [ ] CoD^Σ trace links evidence to conclusions
- [ ] All claims backed by file:line or MCP data
- [ ] report.md generated with findings
- [ ] [Custom AC for this analysis]

---

## Constraints

**Time Limit:** [if applicable]
**Token Budget:** [if applicable]
**Avoid:** [what NOT to do]

---

## Enforcement

**Intel-First:** All queries above MUST execute before reading any full files.
**No Assumptions:** Every claim must have evidence link.
**MCP Verification:** Cross-reference intel with authoritative sources.

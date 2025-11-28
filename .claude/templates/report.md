---
chain_id: ""
status: "pending-review"
handover_to: ""
created_at: ""
created_by: ""
type: "report"
naming_pattern: "YYYYMMDD-HHMM-report-{id}.md"
---

# Analysis Report: [Title]

## Summary
<!-- Concise summary of findings (max 200 tokens) -->

**Objective:**
**Key Finding:**
**Recommendation:**

---

## CoD^Σ Trace

### Claim
<!-- What you assert to be true -->

### Reasoning Chain
```
Step 1: [Operator] [Action]
  ↳ Source: [file:line or MCP query]
  ↳ Data: [exact finding]

Step 2: [Operator] [Next Action]
  ↳ Logic: [how Step 1 leads to Step 2]
  ↳ Source: [file:line or MCP query]
  ↳ Data: [exact finding]

Step 3: [Operator] [Conclusion]
  ↳ Result: [final claim with evidence link]
```

---

## Evidence

### Intel Queries Executed
1. **Query:** `project-intel.mjs [command]`
   - **Result:** [summary]
   - **Link:** [file:line or output file]

2. **Query:** `[MCP tool query]`
   - **Result:** [summary]
   - **Link:** [reference]

### Code References
- [file:line] - [description]
- [file:line] - [description]

### MCP Verifications
- **Tool:** [Ref/Supabase/etc]
- **Query:** [query details]
- **Result:** [verification outcome]

---

## Recommendations

### Immediate Actions
1. [Action with specific file:line or component]
2. [Action with specific file:line or component]

### Follow-Up Tasks
1. [Task with AC]
2. [Task with AC]

### Next Steps
- [ ] [Actionable next step]
- [ ] [Actionable next step]

---

## Metadata

**Intel Files Generated:**
- `/tmp/intel_query_1.json`
- `/tmp/intel_query_2.json`

**Token Count:** [estimate]
**Handover:** [agent or human]

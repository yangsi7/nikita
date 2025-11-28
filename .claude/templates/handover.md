---
from_agent: ""
to_agent: ""
chain_id: ""
timestamp: ""
status: "pending"
type: "handover"
naming_pattern: "YYYYMMDD-HHMM-handover-{from}-to-{to}.md"
token_limit: 600
---

# Agent Handover: [From] → [To]

## Essential Context
<!-- ONLY non-obvious context. Assume receiving agent can query intel for basics. -->

**Current Task:**
**Why Handover:**
**Critical Context:**

---

## Reasoning Chain (CoD^Σ)
<!-- Document the workflow leading to this handover -->

**Delegation Path:**
```
Step 1: [Agent] → [Action]
  ↳ Context: [What was done]
  ↳ Output: [Result/finding]

Step 2: [Agent] ⇄ [Query/Analysis]
  ↳ Source: [Intel/MCP query]
  ↳ Finding: [Discovery that triggered handover]

Step 3: [Agent] → Handover([To Agent])
  ↳ Reason: [Why this agent is next]
  ↳ Expectation: [What receiving agent should do]
```

**Composition:**
```
[From Agent workflow] ∘ Handover → [To Agent workflow]
```

---

## Pending Tasks

### Task 1: [Task Name]
- **Status:** [not-started | in-progress | blocked]
- **ACs:**
  - [ ] [AC 1]
  - [ ] [AC 2]
- **Blocker:** [if applicable]

### Task 2: [Task Name]
- **Status:**
- **ACs:**
  - [ ] [AC 1]
  - [ ] [AC 2]

---

## Blockers

1. **[Blocker Description]**
   - **Impact:** [what is blocked]
   - **Resolution:** [what needs to happen]
   - **Owner:** [who can unblock]

---

## Intel Links
<!-- File paths ONLY. Receiving agent queries these. NO excerpts. -->

**Relevant Files:**
- `[file:line range]` - [why relevant]
- `[file:line range]` - [why relevant]

**Intel Queries to Run:**
```bash
project-intel.mjs --symbols [file]
project-intel.mjs --dependencies [file]
```

**MCP Queries to Run:**
- [MCP tool] query: [query details]

---

## Overflow Handling
<!-- If this handover exceeds 600 tokens, create report.md and link here -->

**Full Report:** [link to report.md if overflow]

---

**Handover Complete:** [yes/no]
**Confirmed By:** [receiving agent signature]

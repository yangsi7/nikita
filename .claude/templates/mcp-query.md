---
query_id: ""
mcp_tool: ""
timestamp: ""
status: "pending"
type: "mcp-query"
naming_pattern: "YYYYMMDD-HHMM-mcp-query-{tool}-{id}.md"
---

# MCP Query: [Query Title]

## MCP Tool Selection

**Selected Tool:** [Ref | Supabase | Shadcn | Chrome | Brave | 21st-dev]

**Supported MCP Tools:**
- **Ref:** Library documentation retrieval and verification
- **Supabase:** Database schema, RLS policies, edge functions, logs
- **Shadcn:** Component search, registry access, installation commands
- **Chrome:** Browser automation, E2E testing, console logs
- **Brave:** Web search for general information
- **21st-dev:** Design ideation and component inspiration

---

## Query

### Query Type
[ ] Documentation Lookup
[ ] Schema Retrieval
[ ] Component Search
[ ] Browser Automation
[ ] Web Search
[ ] Other: [specify]

### Query Details

**Library/Resource:** [e.g., "React", "users table", "button component"]

**Specific Question:** [What information are we seeking?]

**Query Parameters:**
```
[Exact MCP command or query structure]
```

**Example:**
```bash
# For Ref MCP
mcp ref_search_documentation "React useEffect dependencies"

# For Supabase MCP
mcp supabase_get_table_schema "users"

# For Shadcn MCP
mcp shadcn_search_items_in_registries query="button" registries=["@shadcn"]
```

---

## Reasoning Chain (CoD^Σ)
<!-- Document the verification workflow leading to this MCP query -->

**Verification Pipeline:**
```
Step 1: → IntelQuery([source])
  ↳ Source: [project-intel.mjs or analysis]
  ↳ Finding: [What was discovered in code]
  ↳ Uncertainty: [What needs authoritative confirmation]

Step 2: ⊕ MCPQuery([tool])
  ↳ Tool: [MCP tool selected]
  ↳ Query: [Specific question]
  ↳ Expected: [What authoritative answer we seek]

Step 3: ⇄ Comparison
  ↳ Intel: [What code shows]
  ↳ MCP: [What official docs say]
  ↳ Match: [Agreement or discrepancy]

Step 4: ∘ Conclusion
  ↳ Verification: [Confirmed or contradiction found]
  ↳ Action: [What to do with this authoritative info]
```

**Composition:**
```
IntelQuery ≫ MCPVerify ⇄ Comparison → [Decision | Report]
```

**Token Efficiency:**
```
Intel Query: [X] tokens (code location)
MCP Query:   [Y] tokens (authoritative verification)
Total:       [X+Y] tokens vs [Z] tokens for reading docs manually
Savings:     [percentage]%
```

---

## Expected Output

### Output Format
**Type:** [JSON | Markdown | HTML | Text]

**Structure:**
```json
{
  "field1": "expected type",
  "field2": "expected type",
  "field3": ["array", "of", "items"]
}
```

### Expected Information
- [Information element 1 we expect to receive]
- [Information element 2]
- [Information element 3]

### Success Criteria
- [ ] Query returns valid response
- [ ] Response contains expected fields
- [ ] Data is authoritative (from official source)
- [ ] Response is current (not outdated)

---

## Fallback Strategy

### If MCP Fails
**Reason:** [MCP unavailable | Library not found | Rate limit | Auth error]

**Fallback Action:**
1. **Primary Fallback:** [e.g., "Check cached documentation"]
2. **Secondary Fallback:** [e.g., "Use web search via Brave MCP"]
3. **Final Fallback:** [e.g., "Flag for manual review"]

### Error Handling
```typescript
try {
  const result = await mcpQuery(tool, query)
  if (!result.success) {
    // Fallback strategy
    return fallbackMethod()
  }
  return result.data
} catch (error) {
  // Log error and use fallback
  logError(error)
  return fallbackMethod()
}
```

---

## Query Validation

### Pre-Query Checklist
- [ ] MCP tool is available in this environment
- [ ] Query parameters are valid
- [ ] Required authentication/credentials present
- [ ] Resource/library exists in MCP database
- [ ] Rate limits not exceeded

### Post-Query Validation
- [ ] Response received successfully
- [ ] Response is not empty
- [ ] Response matches expected structure
- [ ] Data is relevant to query
- [ ] No error messages in response

---

## Use Case

**Why This Query:**
[Explanation of why we need this authoritative information]

**How It's Used:**
[How the response will be utilized in the workflow]

**Example:**
```
We're debugging a React infinite render loop. We need to verify the
correct usage of useEffect dependencies from React official docs via Ref MCP.
This authoritative source will confirm whether our intel findings match
best practices.
```

---

## Integration with Intel

### Intel → MCP Verification Flow
```
Step 1: → IntelQuery
  ↳ project-intel.mjs finds useEffect at src/Component.tsx:45

Step 2: ⊕ MCP Verification
  ↳ Ref MCP query: "React useEffect dependencies"
  ↳ Result: Confirms dependencies array should include all values used inside effect

Step 3: ∘ Comparison
  ↳ Intel shows dependency array: [state]
  ↳ MCP shows proper dependencies should include: [state, setState, callback]
  ↳ Conclusion: Missing dependencies confirmed as root cause
```

---

## Response Storage

**Cache Location:** [/tmp/mcp_response_[query_id].json]
**Cache Duration:** [Session | 1 hour | 24 hours | Permanent]
**Reuse Strategy:** [When to use cached vs. fresh query]

---

## Example Queries by Tool

### Ref MCP Examples
```bash
# Library documentation
mcp ref_search_documentation "Next.js App Router"
mcp ref_read_url "https://nextjs.org/docs/app/api-reference/functions/use-router"

# API reference
mcp ref_search_documentation "Supabase client authentication"
```

### Supabase MCP Examples
```bash
# Schema
mcp supabase_get_table_schema "users"

# RLS policies
mcp supabase_get_rls_policies "profiles"

# Logs
mcp supabase_get_logs type="database" period="1h"
```

### Shadcn MCP Examples
```bash
# Search components
mcp shadcn_search_items_in_registries query="form" registries=["@shadcn"]

# Get installation command
mcp shadcn_get_add_command_for_items items=["@shadcn/button"]

# View component code
mcp shadcn_view_items_in_registries items=["@shadcn/button"]
```

### Chrome MCP Examples
```bash
# Navigate and screenshot
mcp chrome_navigate "http://localhost:3000"
mcp chrome_screenshot

# Console logs
mcp chrome_get_console_logs

# Run script
mcp chrome_evaluate "document.querySelector('#app').innerHTML"
```

### Brave MCP Examples
```bash
# Web search
mcp brave_web_search query="Next.js 14 server components best practices" count=10

# Local search
mcp brave_local_search query="restaurants near Central Park"
```

---

**Query Status:** [Pending | In Progress | Complete | Failed]
**Result:** [link to result file or inline summary]

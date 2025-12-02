# Advanced Tool Use for MCP Servers: Discovery & Implementation Guide

**Session**: 20251202 | **Type**: Research | **ID**: atuc (Advanced Tool Use Conversion)

---

## Executive Summary

Anthropic's **Advanced Tool Use** features (beta: `advanced-tool-use-2025-11-20`) provide three patterns for optimizing Claude's tool interactions:

| Feature | Problem Solved | Token Savings | Best For |
|---------|---------------|---------------|----------|
| **Tool Search Tool** | Context bloat from loading all tool definitions | 85%+ (77K → 8.7K) | 10+ tools, multiple MCP servers |
| **Programmatic Tool Calling** | Round-trip latency, intermediate result bloat | 37-98% | Batch operations, data filtering |
| **Tool Use Examples** | Parameter format errors | 72% → 90% accuracy | Complex parameters, conventions |

---

## Part 1: Tool Search Tool

### What It Does

Instead of loading all tool definitions upfront, Claude queries a search tool to discover relevant tools on-demand. Tools are marked with `defer_loading: true` and only expanded when Claude needs them.

### API Configuration

```json
{
  "tools": [
    {
      "type": "tool_search_tool_regex_20251119",
      "name": "tool_search_tool_regex"
    },
    {
      "name": "my_critical_tool",
      "description": "Most-used tool, always loaded",
      "defer_loading": false
    },
    {
      "name": "rarely_used_tool",
      "description": "Edge case handler",
      "defer_loading": true
    }
  ],
  "betas": ["advanced-tool-use-2025-11-20"]
}
```

### Search Variants

| Variant | Pattern Type | Use Case |
|---------|-------------|----------|
| `tool_search_tool_regex_20251119` | Python regex (max 200 chars) | Precise matching: `get_.*_data`, `(?i)weather` |
| `tool_search_tool_bm25_20251119` | Natural language | Semantic matching: "find weather tools" |

### MCP Toolset Integration

For MCP servers, use the `mcp-client-2025-11-20` beta header:

```json
{
  "tools": [
    {
      "type": "mcp_toolset",
      "mcp_server_name": "firecrawl",
      "default_config": {
        "defer_loading": true
      },
      "configs": {
        "firecrawl_scrape": {"defer_loading": false},
        "firecrawl_search": {"defer_loading": false}
      }
    }
  ],
  "betas": ["advanced-tool-use-2025-11-20", "mcp-client-2025-11-20"]
}
```

**Pattern**: Keep 3-5 most-used tools with `defer_loading: false`, defer the rest.

### Performance Impact

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Token usage (50+ tools) | ~77K | ~8.7K | 85% reduction |
| Opus 4 accuracy | 49% | 74% | +25pp |
| Opus 4.5 accuracy | 79.5% | 88.1% | +8.6pp |

---

## Part 2: Programmatic Tool Calling (PTC)

### What It Does

Claude writes code that executes tools within a sandboxed code execution environment, rather than making round-trip API calls for each tool invocation.

### Key Benefits

1. **Batch operations**: Process hundreds of items without model inference per item
2. **Data filtering**: Filter large datasets before returning to Claude's context
3. **Complex orchestration**: Loops, conditionals, error handling in code
4. **Privacy**: Intermediate data stays in sandbox, never enters context

### Configuration

```json
{
  "tools": [
    {
      "type": "code_execution_20250825",
      "name": "code_execution"
    },
    {
      "name": "get_expenses",
      "description": "Fetch expense records",
      "allowed_callers": ["code_execution_20250825"]
    }
  ],
  "betas": ["advanced-tool-use-2025-11-20"]
}
```

**Critical**: Tools must opt-in with `"allowed_callers": ["code_execution_20250825"]`

### MCP + Code Execution Architecture

Anthropic's "Code Execution with MCP" approach:

```
servers/
├── google-drive/
│   ├── getDocument.ts      # Wraps MCP tool
│   └── index.ts            # Discovery index
├── salesforce/
│   ├── updateRecord.ts
│   └── index.ts
└── nikita-memory/          # Your custom server
    ├── addFact.ts
    ├── searchGraph.ts
    └── index.ts
```

Claude explores this filesystem to discover tools, loads only what's needed, and processes results in the sandbox.

### Token Savings Example

| Scenario | Traditional | With PTC | Savings |
|----------|-------------|----------|---------|
| Knowledge retrieval | 43,588 | 27,297 | 37% |
| Spreadsheet processing | 150,000 | 2,000 | 98.7% |
| Multi-step workflow | 19+ inference passes | 1 pass | 95%+ latency |

---

## Part 3: Tool Use Examples

### What It Does

Provides concrete examples showing how tools should be called, disambiguating what JSON schemas alone cannot express.

### Configuration

```json
{
  "name": "add_memory_fact",
  "description": "Add a fact to Nikita's memory graph",
  "input_schema": {...},
  "input_examples": [
    {
      "subject": "user",
      "predicate": "mentioned",
      "object": "loves hiking on weekends",
      "confidence": 0.9,
      "source": "conversation"
    },
    {
      "subject": "user",
      "predicate": "prefers",
      "object": "morning text messages"
    },
    {
      "subject": "user"
    }
  ]
}
```

### Best Practices

1. **Show variety**: Minimal, partial, and complete specifications
2. **Use realistic data**: Actual patterns from your domain
3. **Focus on ambiguous cases**: Not obvious usage, edge cases
4. **1-5 examples per tool**: More isn't necessarily better

### Impact

Internal testing: **72% → 90% accuracy** on complex parameter handling.

---

## Part 4: Application to Nikita Project

### Current MCP Tools (per CLAUDE.md)

| Tool | Purpose | Frequency | Recommendation |
|------|---------|-----------|----------------|
| Ref | Documentation lookup | High | `defer_loading: false` |
| Firecrawl | Web scraping/search | Medium | Mixed (scrape: false, others: true) |
| Supabase | Database operations | High | `defer_loading: false` |
| Shadcn | Component docs | Low | `defer_loading: true` |
| Chrome | E2E testing | Low | `defer_loading: true` |
| Brave | Web search | Medium | `defer_loading: true` |
| 21st-dev | Design tools | Low | `defer_loading: true` |

### Proposed Implementation Strategy

**Phase 1: Tool Search Integration**
- Add `tool_search_tool_bm25_20251119` for natural language discovery
- Configure `defer_loading` per tool based on usage frequency
- Keep Ref, Supabase, primary Firecrawl tools always loaded

**Phase 2: Tool Use Examples**
- Add `input_examples` to complex tools (memory graph operations)
- Document Nikita-specific conventions (user ID formats, timestamp formats)
- Focus on game engine tools with complex parameters

**Phase 3: Programmatic Tool Calling (Advanced)**
- For batch operations: bulk memory graph queries
- For data filtering: filtering game metrics before analysis
- Requires secure sandbox infrastructure

---

## Part 5: Implementation Checklist

### Prerequisites

- [ ] Anthropic API with beta access
- [ ] Beta headers: `advanced-tool-use-2025-11-20`, `mcp-client-2025-11-20`
- [ ] Compatible model: `claude-sonnet-4-5-20250929` or later

### Tool Search Setup

- [ ] Audit tool library for usage frequency
- [ ] Mark 3-5 high-frequency tools with `defer_loading: false`
- [ ] Mark remaining tools with `defer_loading: true`
- [ ] Write clear, searchable tool descriptions
- [ ] Add semantic keywords matching how users describe tasks
- [ ] Test regex/BM25 patterns for discovery accuracy

### Tool Examples Setup

- [ ] Identify tools with complex parameters
- [ ] Create 1-5 realistic examples per tool
- [ ] Show minimal, partial, and complete specifications
- [ ] Test parameter accuracy improvements

### Programmatic Calling Setup (Optional)

- [ ] Set up code execution environment
- [ ] Configure tool `allowed_callers`
- [ ] Create wrapper functions for MCP tools
- [ ] Implement result filtering patterns
- [ ] Document return formats for Claude

---

## Sources

- [Anthropic Advanced Tool Use Engineering Blog](https://www.anthropic.com/engineering/advanced-tool-use)
- [Tool Search Tool Documentation](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool)
- [Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)
- [Anthropic Cookbook - Tool Use](https://github.com/anthropics/anthropic-cookbook/tree/main/tool_use)
- [MCP Connector Documentation](https://docs.claude.com/en/docs/agents-and-tools/mcp-connector)

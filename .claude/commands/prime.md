---
description: Load optimal codebase context using jq queries on PROJECT_INDEX.json
allowed-tools: Bash(jq:*), Read, Grep
---

## Auto-Load Overview

!`if [ ! -f PROJECT_INDEX.json ]; then echo "NO_INDEX: Run /index to generate PROJECT_INDEX.json"; exit 0; fi`

!`jq -c '{stats: .stats, index_age: .at}' PROJECT_INDEX.json`

!`jq -c '{
  top_modules: [.deps | to_entries | map(.value[]) | map(select(startswith("nikita."))) | group_by(.) | map({m: .[0], n: length}) | sort_by(-.n)[:10] | .[] | "\(.m):\(.n)"],
  high_coupling: [.deps | to_entries | map({f: .key, n: (.value | length)}) | sort_by(-.n)[:5] | .[] | "\(.f | split("/")[-1]):\(.n)"],
  top_called: [.g | map(.[1]) | group_by(.) | map({fn: .[0], n: length}) | sort_by(-.n)[:5] | .[] | "\(.fn):\(.n)"]
}' PROJECT_INDEX.json`

!`jq -c '{
  tech_stack: [.deps | to_entries | map(.value) | flatten | group_by(.) | map({lib: .[0], uses: length}) | sort_by(-.uses)[:12] | .[] | "\(.lib):\(.uses)"],
  test_count: (.f | keys | map(select(test("test"))) | length),
  doc_count: (.d | keys | length)
}' PROJECT_INDEX.json`

# Prime Code Context

You now have the codebase overview loaded above. Use this context to understand the project before diving into specifics.

## What You Have

- **Stats**: File counts, languages, directories
- **Top modules**: Most-imported internal modules (high reuse = core infrastructure)
- **High coupling**: Files with most imports (entry points + change-risk hotspots)
- **Top called**: Most-called functions in call graph (critical paths)
- **Tech stack**: Top libraries by import frequency
- **Test/doc count**: Testing and documentation coverage

## Deeper Queries (jq on PROJECT_INDEX.json)

```bash
# Search for files by name
jq --arg t "TERM" '[.deps | keys[] | select(test($t; "i"))]' PROJECT_INDEX.json

# Show deps for a file
jq --arg f "FILE" '.deps[$f]' PROJECT_INDEX.json

# Show reverse deps (who imports this)
jq --arg m "MODULE" '[.deps | to_entries[] | select(.value | any(test($m; "i"))) | .key]' PROJECT_INDEX.json

# Show functions in a file
jq --arg f "FILE" '.f[$f][1]' PROJECT_INDEX.json

# Graph traversal (trace, dead code, investigate)
bash ~/.claude/skills/project-intel/references/graph-ops.sh trace <fn1> <fn2>
bash ~/.claude/skills/project-intel/references/graph-ops.sh dead -l 10
bash ~/.claude/skills/project-intel/references/graph-ops.sh investigate <term1> <term2>
```

## Pro Tips

1. **jq is 4-5x faster** than project-intel.mjs (17ms vs 80ms)
2. **Use -c flag** for compact output (saves tokens)
3. **Pipe to head** for large results: `jq '...' PI.json | head -20`
4. **Query before read** — jq queries cost ~10 tokens, file reads cost ~500+

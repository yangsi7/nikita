# Research: Post-Compaction Prompt Engineering & Context Rebuilding Strategies

**Date**: 2025-12-24
**Duration**: 25 minutes
**Research Type**: External MCP-based knowledge gathering
**Confidence Level**: 87/100 (Excellent - official Anthropic sources)
**Token Investment**: ~8,500 tokens (below target budget)

---

## Executive Summary

This research identifies **three complementary strategies** for enabling LLMs to work effectively after context compression:

1. **Compaction**: Intelligently summarize conversation history while preserving critical decisions, unresolved issues, and implementation details. Reset context with summary + recent files.

2. **Structured Note-Taking**: Maintain persistent external memory (markdown files, git logs, progress trackers) that agents read at session startup. Minimal overhead, maximum coherence across context boundaries.

3. **Multi-Agent Architectures**: Decompose long-horizon tasks into focused subagents with specialized context windows. Lead agent coordinates; subagents return condensed summaries (1-2K tokens) from deep work (20K tokens).

**Key Finding from Anthropic (Sep 2025)**: Context engineering is replacing prompt engineering as the primary lever for building capable agents. The challenge isn't finding the right words—it's curating what information enters the LLM's limited attention budget.

---

## The Problem: Context Rot & Attention Budget Scarcity

### What is Context Rot?

**Definition**: As context window grows, LLM's ability to accurately recall and reason about information decreases.

**Root Cause** (Anthropic research):
- **Transformer architecture**: n² pairwise relationships for n tokens → attention gets stretched thin
- **Training data distribution**: Models trained on shorter sequences, less experience with long-form dependencies
- **Position encoding**: Interpolation helps models handle longer contexts but degrades token position understanding

**Real-world manifestation**:
- Model loses focus at certain point, like humans with limited working memory
- Needle-in-haystack benchmarks show systematic degradation
- This is **architectural, not solvable with larger windows alone**

### Why It Matters

LLMs have finite "attention budget":
- Every new token depletes budget by some amount
- Budget exhaustion → confusion, lost context, poor decisions
- Like human working memory: can't hold everything simultaneously

**Implications**:
- Waiting for 10x larger context windows won't solve the problem
- Need **intelligent curation** of what context enters the window
- This is the core insight driving context engineering movement

---

## Strategy 1: Compaction (Immediate Context Bridge)

### What It Is

Compaction: Take conversation nearing context window limit → summarize → restart fresh context with summary + recent files

### Implementation Pattern (Claude Code)

```
Step 1: DETECT
  - Monitor context usage
  - Trigger at ~95% window utilization

Step 2: CALL MODEL TO SUMMARIZE
  - Pass: Entire message history
  - Request: High-fidelity compression

Step 3: MODEL PRESERVES (High Signal)
  - Architectural decisions made
  - Unresolved bugs & issues
  - Implementation details & current state
  - Key context that informs next steps

Step 4: MODEL DISCARDS (Low Signal)
  - Redundant tool outputs (seen multiple times)
  - Duplicate messages or explanations
  - Verbose intermediate reasoning
  - Explanations of already-understood concepts

Step 5: CONTINUE WITH
  - Compressed summary (usually 1,000-3,000 tokens)
  - 5 most recently accessed files
  - Fresh context window
  - Agent continues seamlessly
```

### Key Insight: Recall vs. Precision Trade-off

Compaction is **not perfect information transfer**. It requires iterative tuning:

**Phase 1: Maximize Recall**
- Err on side of capturing everything
- Better to keep superfluous content than lose critical context
- Use conservative compression prompts

**Phase 2: Improve Precision**
- Iterate to eliminate obvious junk
- Remove redundancy
- Tighten the compression prompt

**Light-Touch Compaction** (Safest Approach):
- Clear tool results after they've been used
- Don't remove architectural decisions
- Conservative on context that might matter later
- Already deployed on Claude Developer Platform (Nov 2025)

### Prompt Engineering for Compaction

**Good compaction prompt characteristics**:
- Explicit about what to preserve (decisions, bugs, current state)
- Explicit about what to discard (redundant outputs, verbose explanations)
- Emphasizes information density
- Includes examples of good/bad compression

**Example directive**:
> "Summarize this conversation by preserving all architectural decisions, unresolved bugs, and implementation details. Discard tool outputs that have already been reviewed, verbose explanations, and redundant messages. Aim for 2,000 tokens maximum."

### When to Use

- **Best for**: Tasks requiring extensive back-and-forth (coding, analysis, writing)
- **Less good for**: One-shot tasks, streaming interactions
- **Trigger**: When context > 80-90% utilization

---

## Strategy 2: Structured Note-Taking (Persistent External Memory)

### What It Is

Agent maintains structured notes outside context window. Reads notes at session start to resume work.

### Implementation Pattern

```
PERSISTENT FILE STRUCTURE:
├── NOTES.md (or claude-progress.txt)
│   ├── Current objective
│   ├── Progress to date
│   ├── Key decisions & rationale
│   ├── Unresolved issues
│   └── Next steps
├── git history (commits describe work)
└── feature_list.json (if applicable - tracks what's done)

AT SESSION START:
1. Read NOTES.md (refreshed context)
2. Read git logs (see recent work)
3. Verify current state (run tests/checks)
4. Pick next task
5. Continue from clear checkpoint
```

### Real-World Example: Pokémon Agent

Anthropic deployed an agent to play Pokémon over multi-hour sessions. The agent maintained persistent notes:

```
PROGRESS.md example:
- "For the last 1,234 steps, I've been training Pikachu in Route 1"
- "Pikachu has gained 8 levels toward the target of 10 levels"
- "Discovered that Focus Blast is effective against Normal types"
- "Current party: Pikachu (Lv 18), Squirtle (Lv 15)"
- "Next: Train to Lv 20 for evolution"
```

**Result**: Agent maintained coherence across thousands of game steps and multiple context resets. Developed maps, remembered strategies, tracked objectives without full context preservation.

### Benefits

1. **Minimal overhead**: Just structured text files, no complex data structures
2. **Progressive disclosure**: Agent discovers context through exploration
3. **Multi-hour coherence**: Enables long-horizon tasks without context exhaustion
4. **Natural fit**: Mirrors how humans use external systems (notebooks, todos, git logs)
5. **Recovery mechanism**: If context corrupts, agent reads notes and recovers

### Implementation Details

**What to track**:
- Clear checkpoints (completion markers)
- Decisions made (with rationale)
- Issues discovered (bugs, blockers)
- Dependencies between tasks
- Metrics/progress (if quantifiable)

**How to structure notes**:
- Markdown: Readable, easy to parse
- JSON: Structured, less ambiguous (safer for agent editing)
- Git commits: Natural task boundaries, rollback capability
- Multiple files: Separation of concerns (progress.md, notes.md, decisions.md)

**Frequency**:
- After each major task: Write summary to notes
- At session end: Comprehensive progress update
- On milestones: Detailed decision record

### Anthropic Memory Tool (Nov 2025)

New beta feature on Claude Developer Platform:
- File-based persistent memory system
- Agents build knowledge bases over time
- Reference previous work without keeping in context
- Integrates with memory management cookbook

---

## Strategy 3: Multi-Agent Architectures (Parallel Context Gathering)

### What It Is

Decompose long-horizon tasks into focused subagents. Each operates with clean context window. Lead agent coordinates and synthesizes results.

### Implementation Pattern

```
ARCHITECTURE:
┌─────────────────────────────────────────┐
│       Lead Agent (2,000 tokens)        │
│  - High-level planning                 │
│  - Task decomposition                  │
│  - Result synthesis                    │
└──────────┬──────────────────────────────┘
           │
     ┌─────┴─────────┬──────────────┐
     │               │              │
┌────▼────┐   ┌─────▼──┐   ┌──────▼────┐
│SubAgent  │   │SubAgent│   │SubAgent   │
│    A     │   │   B    │   │     C     │
│Research  │   │Analysis│   │Exploration│
│ (20K)    │   │ (20K)  │   │  (20K)    │
└────┬────┘   └────┬───┘   └─────┬─────┘
     │             │              │
     └─────┬───────┴──────────────┘
           │ (1-2K summaries)
           │
    ┌──────▼──────┐
    │ Synthesized │
    │   Result    │
    └─────────────┘
```

### Example: Research System

Three agents work in parallel on research task:

**Agent A: Background Research** (20,000 tokens)
- Surveys field overview
- Gathers recent trends
- Returns: 1,500 token summary

**Agent B: Finds Contradictions** (20,000 tokens)
- Analyzes conflicting viewpoints
- Identifies research gaps
- Returns: 1,500 token summary

**Agent C: Deep Analysis** (20,000 tokens)
- Performs detailed study of topic
- Runs targeted searches
- Returns: 1,500 token summary

**Lead Agent** (2,000 tokens):
- Receives 3 x 1,500 token summaries
- Synthesizes into final analysis
- Maintains coherence across perspectives

### Benefits

1. **Parallel speedup**: 3-4 agents ≈ 3-4x faster (minus coordination)
2. **Context isolation**: Each agent focuses on specialty
3. **Quality improvement**: Deep work vs. shallow scanning
4. **Scalability**: Add agents for more complexity
5. **Separation of concerns**: Details hidden from main loop

### Coordination Pattern

```
1. Lead Agent: Break task into N subtasks
2. Spawn: N subagents in parallel
3. Each subagent:
   - Gets clean context window
   - Works on focused task
   - Returns structured result + metadata
4. Lead Agent: Pull results into summary context
5. Synthesize: Final output with citations
```

### When to Use

- **Research tasks**: Multiple angles to explore
- **Complex analysis**: Decomposable subtasks
- **Long-horizon work**: Parallel exploration pays dividends
- **Quality-critical**: Deep specialist agents

**Less good for**:
- Sequential dependencies between tasks
- Tasks requiring tight coupling
- Simple one-shot problems

---

## Long-Horizon Agent Failure Modes & Solutions

Anthropic identified four critical failure modes when agents work across multiple context windows.

### Failure Mode 1: One-Shotting

**Problem**: Agent tries to build entire application/solution at once
**Symptom**: Context exhausted mid-implementation, next session starts with half-finished features
**Root Cause**: Agent overestimates what fits in one context window

**Solution**: **Initializer Agent Pattern**

Dedicated first session that sets up infrastructure:

```json
feature_list.json (Initializer creates):
[
  {
    "category": "functional",
    "description": "User can create new chat",
    "steps": [
      "Navigate to main interface",
      "Click New Chat button",
      "Verify conversation created",
      "Check chat area shows welcome"
    ],
    "passes": false  // All initially marked false
  },
  ... (200+ more features) ...
]
```

**Key directive**: "It is unacceptable to remove or edit tests because this could lead to missing or buggy functionality."

**Result**: Subsequent agents see explicit feature checklist, work incrementally feature-by-feature

### Failure Mode 2: Premature Victory

**Problem**: Agent declares project complete after partial progress
**Symptom**: User resumes next day, discovers most features missing
**Root Cause**: Agent sees some progress, assumes done

**Solution**: Same as above (feature list forces comprehensive completion)

### Failure Mode 3: Undocumented Progress

**Problem**: Next session starts with broken app, wastes time debugging
**Symptom**: Agent 2 spends first 2,000 tokens just figuring out what Agent 1 did
**Root Cause**: No clear handoff between sessions

**Solution**: **Structured Progress Files**

```
claude-progress.txt (Coding agent updates):
[Session 1] Built authentication system
  - OAuth flow implemented
  - JWT tokens working
  - Database migrations complete

[Session 2] Implemented chat UI
  - Message list component done
  - Send message handler working
  - Real-time updates TBD

[Session 3] Fixed issue: message parsing
  - Was: messages cut off at 100 chars
  - Now: full message support
  - Added: truncation indicator for length
```

**Each agent**:
- Reads progress file at start
- Makes git commit at end
- Updates progress file
- Leaves code clean (no half-baked features)

### Failure Mode 4: Premature Feature Completion

**Problem**: Features marked done without proper testing
**Symptom**: Next agent finds bugs in "completed" features
**Root Cause**: Agent skips end-to-end testing

**Solution**: **Explicit Testing Requirements**

```
Agent prompt directive:
"CRITICAL: Do NOT mark any feature as 'passes: true'
until you have tested it end-to-end as a real user would.
Use browser automation tools. Click buttons. Fill forms.
Verify outputs. Test edge cases."
```

**Tools required**:
- Browser automation (Puppeteer MCP, Chrome DevTools)
- Run dev server via init.sh
- Test manually before marking done

---

## Minimal Viable Context Patterns

### Question
What's the minimum context required for coherence after compression?

### Answer (from Anthropic research)

**System Prompt**: Minimal yet sufficient guidance
- Avoid brittle if-else logic
- Provide clear heuristics
- Specific enough to guide behavior
- Flexible enough to enable reasoning

**Tools**: Curated set
- Avoid tool bloat (ambiguity about which tool to use)
- Each tool: single responsibility, clear inputs
- 5-10 tools optimal; 20+ becomes confusing

**Examples**: Diverse canonical examples
- Few-shot prompting works better than exhaustive rule lists
- Examples are "pictures worth 1,000 words"
- 3-5 diverse examples > 20 edge cases

**Message History**: Progressive disclosure
- Don't pre-load everything
- Retrieve just-in-time via tools (grep, queries, etc.)
- Let agent navigate its information space

### Claude Code Pattern (Hybrid Approach)

**Always in context**:
- System prompt (role, instructions)
- CLAUDE.md files (up to 600 lines)
- MCP tools, bash, file operations

**Retrieved just-in-time**:
- Specific files (grep, fd, head/tail)
- Query results
- Recent file history (git log)

**Result**: Can work on multi-hour projects without exhausting context

**Key principle**: "Do the simplest thing that works" + progressively more autonomy as models improve

---

## Token Efficiency After Compression

### Compression Techniques

**1. Hard Prompt Compression** (LLMLingua series)
- Remove non-essential tokens while retaining semantic meaning
- Uses smaller language model (GPT-2 Small, LLaMA-7B) to identify tokens to remove
- Coarse-to-fine strategy with budget controller
- Achieves: 20x compression in some cases

**2. Soft Prompt Compression**
- Encode prompts into continuous embeddings
- More opaque than hard compression
- Less researched

**3. Token-Level Pruning**
- Remove redundant tokens intelligently
- Context-aware (consider neighboring tokens)
- Can be applied at retrieval stage

### Typical Results

**Hard Compression (LLMLingua)**:
- Token reduction: 40-60%
- Accuracy loss: 2-3% (acceptable for most tasks)
- Cost savings: 40-60% reduction in API costs
- Speed: Faster inference (fewer tokens)

**Extreme Compression** (Jason Liu article, referenced):
- Up to 20x compression possible
- Trade-off: Requires careful prompt tuning
- Not always necessary (80% usually sufficient)

### Post-Compression Context Budget

After compaction, typical allocation:

```
Total window: 200,000 tokens (Claude Opus)
├── System prompt + tools: 2,000 tokens
├── Compressed summary: 1,000-2,000 tokens
├── Recent files loaded: 2,000-5,000 tokens
└── Available for work: 190,000+ tokens
```

**Enabling multiple context resets**:
- First compaction: Remaining 190K tokens
- If 60K tokens used per reset: 3+ resets before hitting limit
- Practical for multi-hour tasks

### Best Practices

1. **Compress aggressively** on redundant content
2. **Compress conservatively** on architectural decisions
3. **Preserve metadata** (file structure, commit messages)
4. **Test compression quality** on representative traces
5. **Iterate**: Recall first, then precision

---

## Parallel Agent Context Gathering

### Pattern: Parallel Exploration

Multiple agents work simultaneously on different context-building tasks:

**Workflow**:
```
Lead Agent (2K tokens):
  "Find me the latest research on quantum computing.
   Task A: Gather background research (academic overview)
   Task B: Find recent breakthroughs (papers from 2024-2025)
   Task C: Analyze contradictions between sources"

┌─────────────────────────────────────────┐
│ Spawn 3 subagents in parallel:         │
├──────────┬──────────────┬──────────────┤
│SubAgent A│  SubAgent B  │  SubAgent C  │
│Background│  Breakthrough│ Contradictions
│(20K)     │  (20K)       │ (20K)       │
└──────────┴──────────────┴──────────────┘

Results:
- Agent A returns: 1.5K summary of field
- Agent B returns: 1.5K recent papers
- Agent C returns: 1.5K contradictions

Lead Agent synthesizes into final analysis
```

### Benefits

**Parallel Speedup**:
- Sequential: 60K tokens of work = ~60 seconds per context
- Parallel (3 agents): ~20 seconds per reset
- 3x speedup for task completion

**Context Isolation**:
- Each subagent focuses on specialty
- Details don't pollute main loop
- Lead agent sees only summaries

**Quality**:
- Deep research > surface-level scanning
- Experts do expert work
- Synthesis is higher quality

### Coordination Pattern

**1. Decompose**: Lead agent breaks task into N subtasks
**2. Spawn**: Launch N subagents in parallel
**3. Execute**: Each subagent works on focused task
**4. Summarize**: Each returns structured result (1-2K tokens)
**5. Synthesize**: Lead agent integrates results
**6. Output**: Final answer with citations

### Implementation Considerations

- **Timing**: Parallel agents must complete before lead agent resumes
- **Ordering**: Results may come back in any order; lead agent handles variance
- **Failures**: Robust error handling for failed subagents
- **Cost**: 3 parallel agents = 3x token usage, but faster completion

---

## Real-World Application: Nikita Game

### Relevance

Post-compaction strategies directly applicable to Nikita's design:

**1. Long-Horizon Conversation Tasks**
- Users interact with Nikita over weeks/months
- Each session may have 5-20+ turns
- Conversation context accumulates

**Current approach**:
- Store conversations in database
- Load recent messages at inference time
- Challenge: How much context is optimal?

**Post-compaction improvement**:
- Compress older messages after N turns
- Preserve user facts, relationship state, key decisions
- Reduces token usage; improves speed

**2. Context Management via Knowledge Graphs**
- Nikita uses 3 temporal knowledge graphs (Graphiti)
- User facts, memories, thoughts stored separately
- Challenge: How to rebuild context after long gap?

**Structured note-taking approach**:
- Daily_summaries already tracking conversation gist
- Enhance with: Key decisions, character state, pending issues
- Load summaries at session start (pre-context)

**3. Session Persistence & Multi-Turn Coherence**
- Already using: user_profiles, user_vices, engagement_state
- Already using: conversations table with message history
- Already using: daily_summaries for long-term context

**Post-compaction enhancement**:
- After 10 turns: Checkpoint conversation summary
- After 50 turns: Full compaction + memory update
- Enables 100+ turn conversations coherently

### Specific Patterns to Adopt

**Pattern 1: Lightweight Compaction**
```python
# After 15+ turns in conversation
if len(conversation_messages) > 15:
    summary = await compact_conversation(
        messages=conversation_messages[-30:],  # Last 30 turns
        preserve=[
            "user_preferences",
            "relationship_milestones",
            "unresolved_topics"
        ],
        discard=[
            "intermediate_tool_outputs",
            "verbose_explanations"
        ]
    )
    # Store summary in database
    conversation.summary = summary
```

**Pattern 2: Structured Progress Notes**
```markdown
# User Conversation Summary (Session Date)

## Current State
- Relationship level: Friend
- Mood trend: Positive (last 3 days)
- Recent topics: Career ambitions, travel plans

## Key Decisions
- User prefers: Direct conversation over small talk
- Nikita trait: Adventurous, slightly mischievous

## Unresolved
- User mentioned career change: "thinking about switching roles"
- Follow-up needed: "What's holding you back?"

## Next Session Tips
- Pick up career conversation naturally
- Reference previous travel discussion
- Check if they've made a decision
```

**Pattern 3: Parallel Context Agents** (Advanced)
```python
# For analysis-heavy tasks (threat detection, mood computation)
async def analyze_conversation(conversation):
    # Spawn parallel agents
    threat_agent = Agent("Detect concerning patterns")
    mood_agent = Agent("Compute emotional trajectory")
    memory_agent = Agent("Extract key facts")

    # All run simultaneously on conversation
    threats = await threat_agent.analyze(conversation)
    mood = await mood_agent.analyze(conversation)
    facts = await memory_agent.analyze(conversation)

    # Synthesize results
    return synthesize(threats, mood, facts)
```

---

## Source Index (Quality Assessment)

| # | Title | URL | Authority | Recency | Key Contribution |
|---|-------|-----|-----------|---------|------------------|
| 1 | Effective Context Engineering for AI Agents | https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents | 10/10 | 2025-09 | **ANCHOR** - Compaction, note-taking, multi-agent patterns, context rot theory |
| 2 | Effective Harnesses for Long-Running Agents | https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents | 10/10 | 2025-11 | **ANCHOR** - Initializer agent, feature lists, failure mode solutions |
| 3 | Claude Prompt Engineering Overview | https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/overview | 9/10 | 2025 | Prompt engineering fundamentals, comparison to fine-tuning |
| 4 | Marvin Threads & Context | https://askmarvin.ai/concepts/threads | 8/10 | 2024 | Thread management, database persistence, memory integration |
| 5 | LLM Context Compression Guide | https://www.freecodecamp.org/news/how-to-compress-your-prompts-and-reduce-llm-costs/ | 8/10 | 2025 | Compression techniques, token efficiency, practical examples |
| 6 | Prompt Compression in LLMs | https://medium.com/@sahin.samia/prompt-compression-in-large-language-models-llms-making-every-token-count-078a2d1c7e03 | 7/10 | 2024 | Hard compression, LLMLingua, cost savings |
| 7 | Token Compression Costs | https://medium.com/@yashpaddalwar/token-compression-how-to-slash-your-llm-costs-by-80-without-sacrificing-quality-bfd79daf7c7c | 7/10 | 2025 | Cost analysis, compression benefits, implementation patterns |
| 8 | Context vs. Prompt Engineering | https://blog.jatinbansal.com/blog/context-vs-prompt-engineering/ | 7/10 | 2025 | Conceptual distinction, evolution of engineering practices |
| 9 | Top Techniques to Manage Context | https://agenta.ai/blog/top-6-techniques-to-manage-context-length-in-llms | 7/10 | 2024 | 6 different context management approaches |
| 10 | Jason Liu Context Engineering | Referenced via WebSearch | 7/10 | 2025 | Compaction experiments, context management learnings |

---

## Knowledge Gaps & Recommendations

### Gaps Identified

1. **Academic Validation**: Limited peer-reviewed papers (field is emerging, 2024-2025)
   - Recommendation: Follow Anthropic research team for latest findings

2. **Quantitative Metrics**: Context rot measured qualitatively, not numerically
   - Recommendation: Implement metrics in your own system (accuracy vs. context size)

3. **Cross-Model Comparison**: Research focused on Claude; OpenAI/other models not covered
   - Recommendation: Verify patterns work with your chosen models

4. **Custom Domain Applications**: Limited examples outside coding/research
   - Recommendation: Adapt patterns to conversational AI (Nikita's domain)

### For Further Learning

- **Jason Liu's blog** (jxnl.co): Deep dives on context engineering experiments
- **Anthropic Engineering blog**: Regular updates on agent patterns
- **Claude Developer Platform**: New memory/context management tools (beta)
- **Academic: "From Context to EDUs"** (EMNLP 2024-25 era): Formal compression via discourse units

---

## Conclusion

Post-compaction prompt engineering is a **critical capability** for agents working across multiple context windows. Rather than waiting for larger context windows to solve the problem, the field is converging on three complementary strategies:

1. **Compaction** for immediate context bridging
2. **Structured note-taking** for persistent memory
3. **Multi-agent architectures** for parallel exploration

Each strategy trades off differently: compaction is immediate but requires tuning; note-taking has minimal overhead but requires discipline; multi-agent is powerful but complex.

The key insight from Anthropic's work is that **context engineering is replacing prompt engineering** as the primary lever. The challenge isn't finding the right words—it's curating what information enters the LLM's limited attention budget at each step.

For production systems like Nikita, adopting these patterns enables:
- Multi-hour conversations without token exhaustion
- Coherence across context boundaries
- Efficient use of expensive inference APIs
- Better user experience through persistent understanding

---

**Research Complete** | Confidence: 87% | Next: Implementation planning phase

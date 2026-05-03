# Approach evaluation: How to achieve continuity

This document proposes multiple viable approaches to improve Nikita’s continuity, and evaluates them from multiple expert perspectives.

**Goal**: pick a path that’s high-impact, shippable, and maintainable.

---

## The problem we are solving (reframed)

Continuity failure comes from two gaps:

1. **Missing working memory** in the text model input.
2. **Unreliable memory writes** (post-processing) leading to stale long-term context.

So any approach must:

- give the model immediate conversational context
- keep episodic/semantic memory artifacts updating reliably

---

## Approach A — Conversation buffer via chat history (recommended baseline)

### What it is

- For text: pass last N turns as `message_history` (or an equivalent chat history mechanism).
- Keep existing MetaPrompt long-term context injection as the system message.

### Pros

- Best raw coherence for follow-ups and short replies.
- Simple mental model.
- Minimal new infra.
- Deterministic truncation is straightforward.

### Cons

- Token cost increases with N.
- Requires careful handling of the agent framework’s message-history semantics.

### Expert critique

- **LLM engineer**: “This is the only thing that actually solves pronouns + ellipsis reliably.”
- **Infra**: “Watch token bloat; keep it bounded and measured.”
- **Security**: “History contains untrusted user text; but it’s already sent to the model anyway. Main risk is persisting injection in long-term memory, not transient history.”

---

## Approach B — Summary-only sessions (do not recommend as primary)

### What it is

- Do *not* pass raw turns.
- Use a rolling summary (“Today so far”) + last session summary + long-term memory.

### Pros

- Cheap tokens.
- Very stable inputs.
- No framework complexity.

### Cons

- Fails at the exact thing users complain about: short follow-ups.
- Summaries are lossy; user will feel “misremembered.”

### Expert critique

- **Product**: “Feels like talking to someone with mild amnesia: they remember the gist but not the flow.”
- **LLM engineer**: “Summaries can’t encode referents reliably.”

---

## Approach C — Hybrid: buffer + rolling summary

### What it is

- Always include last N turns.
- Maintain a rolling session summary for older turns that fall out of the buffer.

### Pros

- Strong coherence + bounded tokens.
- Prevents long sessions from exploding.

### Cons

- Requires summarization logic and update policy.
- Needs careful UX so summary doesn’t distort.

### Expert critique

- **LLM engineer**: “This is the normal ‘buffer + summary memory’ pattern.”
- **Infra**: “Summarization job can be async; doesn’t need to block.”

---

## Approach D — Retrieval over message embeddings (RAG)

### What it is

- Embed messages (or chunks) and retrieve relevant past messages when needed.
- Inject retrieved snippets into the prompt.

### Pros

- Powerful for long-range callbacks (days/weeks ago).
- Keeps prompt small and relevant.

### Cons

- Retrieval quality is hard; false positives feel creepy, false negatives feel forgetful.
- Requires embedding pipeline + indexing + observability.

### Expert critique

- **Product**: “When it works, it feels magical. When it fails, it feels random.”
- **Infra**: “Embedding cost and index maintenance. Needs strong monitoring.”

---

## Approach E — MemGPT-style memory manager

### What it is

- Treat the model context like a limited RAM.
- Maintain explicit working/archival memory stores and a controller policy.

### Pros

- Very flexible and scalable.
- Can approximate “infinite context” in theory.

### Cons

- High complexity.
- Harder to debug.
- Overkill for the immediate continuity problem.

### Expert critique

- **Engineering**: “This is a research project; ship A/C first.”

---

## Scoring matrix

Scores: 1 (bad) → 10 (excellent). Higher is better.

### Raw scores (unweighted)

| Approach | Continuity (short) | Continuity (long) | Complexity | Cost | Latency | Debuggability | Security posture |
|---|---:|---:|---:|---:|---:|---:|---:|
| A Buffer | 10 | 5 | 7 | 6 | 7 | 8 | 7 |
| B Summary-only | 4 | 6 | 9 | 9 | 9 | 9 | 8 |
| C Hybrid | 9 | 7 | 6 | 7 | 7 | 7 | 7 |
| D Retrieval (RAG) | 7 | 9 | 4 | 6 | 6 | 5 | 6 |
| E MemGPT-like | 8 | 9 | 2 | 5 | 5 | 3 | 5 |

### Weighted scoring (product-weighted)

Because this is a companion product, **continuity is weighted heavier** than operational convenience.

**Weights**:

- Continuity (short): 0.30
- Continuity (long): 0.20
- Complexity: 0.10
- Cost: 0.10
- Latency: 0.10
- Debuggability: 0.10
- Security posture: 0.10

| Approach | Weighted score |
|---|---:|
| A Buffer | 7.5 |
| C Hybrid | 7.5 |
| B Summary-only | 6.8 |
| D Retrieval (RAG) | 6.6 |
| E MemGPT-like | 6.2 |

**Interpretation**:

- **A (buffer)** is the fastest high-impact fix.
- **C (hybrid)** is the best medium-term shape once token costs are measured.
- **D (retrieval)** is strong for long-range recall but needs more infra + monitoring.
- **B (summary-only)** looks “operationally great,” but doesn’t solve short follow-ups.

## Recommendation

**Ship in this order:**

1. **Fix post-processing reliability** (no continuity without memory writes).
2. **Approach A (buffer) for text** as the P0 continuity fix.
3. **Approach C (hybrid)** once token/cost metrics are measured.
4. **Approach D (retrieval)** for P1 long-range recall.

This preserves momentum and avoids turning continuity into a science experiment.
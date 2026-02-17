# Appendix: References & best-practice reading list

This PRD is aligned with several widely-used patterns for agent memory:

- **Working memory** (short-term, in-context chat buffer)
- **Episodic memory** (summaries, key events)
- **Semantic memory** (facts, knowledge graphs)
- **Reflection** (periodic synthesis into higher-level insights)

Below is a curated set of sources worth reviewing.

---

## Research

- Park et al. (2023). **Generative Agents: Interactive Simulacra of Human Behavior**.
  - https://arxiv.org/abs/2304.03442
  - Key takeaways: memory stream + retrieval scored by relevance/recency/importance; reflection creates higher-level stable memories.

- Packer et al. (2023/2024). **MemGPT: Towards LLMs as Operating Systems**.
  - https://arxiv.org/abs/2310.08560
  - Key takeaways: explicit memory tiers (working vs archival) and control flow to manage limited context.

## Practical agent frameworks

- PydanticAI docs: **Messages and chat history**.
  - https://ai.pydantic.dev/message-history/
  - Key takeaways: use `message_history` to maintain context across agent runs.

- PydanticAI docs: **Agents / instructions behavior**.
  - https://ai.pydantic.dev/agents/

## Security & safety engineering

- OWASP: **LLM Prompt Injection Prevention Cheat Sheet**.
  - https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html

- OWASP: **AI Agent Security Cheat Sheet** (includes memory & context security).
  - https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html

## Heuristics worth stealing

### Retrieval scoring: relevance × recency × importance
A recurring best-practice is to retrieve memories not just by similarity, but by:

- **relevance** (semantic similarity to current context)
- **recency** (newer > older)
- **importance** (flagged “big moments”)

This matches the intuition that human recall is biased.

### Summary backstops, not replacements
Summaries help cross-session continuity, but they don’t replace a verbatim buffer for immediate coherence.

### Strict delimiter blocks for memory
Memory sections should be clearly delimited and framed as “context” not “instructions” to reduce prompt injection risk.

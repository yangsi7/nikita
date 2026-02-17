
# Nikita Context Engine & Prompt-Consumer Upgrade

**PRD Proposal (Standalone, Spec 039+)** — **Jan 28, 2026** (Europe/Zurich)

> **Note for the coding agent (Claude):** This document is a **suggested PRD proposal**. Use it to **update your specs, acceptance criteria, and implementation approach** (including Spec 039), while staying within current infrastructure constraints and minimizing disruptive changes.

---

## 1) Executive summary

Nikita’s current system-prompt generation approach (as evidenced by the provided meta-prompts) is already aiming for “deep, immersive, human” behavior—but it has **structural weaknesses that will prevent consistent realism** at scale:

* **Inconsistent canon** across prompts (age/location/background/cat name). This is a major continuity risk.

  * `system_prompt.meta.md` defines Nikita as a **27-year-old Russian‑German** cybersecurity professional living in **Berlin** with a cat named **Schrödinger**. 
  * `thought_simulation.meta.md` defines Nikita as **23**, **Ukrainian‑American**, living in **Williamsburg, Brooklyn**, with a cat named **Sudo**.
  * `vice_detection.meta.md` also frames Nikita as **23**.

* The meta-prompt for system-prompt generation currently enforces **very large output targets** (12k–15k tokens) and includes “no safety theater / no refusals” language.
  This “length floor + no-refusal” combo tends to cause **padding, increased latency/cost, and brittle safety compliance** with most providers.

* The coding agent’s Spec 039 proposal (two-stage “context aggregation → narrative prompt generator → Nikita agent”) is directionally correct, but it over-optimizes for **token volume** (10k–15k) rather than **coverage + specificity + coherence**. A better design is “coverage-first, validated, adaptive length.”

**Proposed solution:**
Introduce a **typed ContextPackage**, a **Prompt Generation Agent** that outputs a **structured PromptBundle**, and **PydanticAI output validators + retry** to guarantee guardrails + coverage. Keep disruption low by reusing existing meta-prompts and reshaping them into a stricter, more testable contract rather than rewriting the whole stack.

This leverages PydanticAI best practices: dependency injection, typed agents, structured output, validators, retries, and multi-agent composition. ([Pydantic AI][1])

---

## 2) Problem statement

### 2.1 What users are complaining about (core insight)

The user concern you shared is essentially:

* The context engine collects a lot of raw facts/events/state.
* The consumer (Nikita agent) is not getting a **believable, story-like internal state**.
* The current method feels **mechanical** (template substitution / sparse context).
* The user wants Nikita’s “inner world” to read like a coherent **private stream-of-consciousness** that drives consistent, human-like replies.

### 2.2 What’s actually failing today (based on supplied templates)

From the templates you attached:

1. **Canon drift / contradictions**
   Multiple meta-prompts hardcode different Nikita identity details (Berlin/27 vs Brooklyn/23).

2. **Unenforced conversational guardrails**
   You want “no stage directions, no weird ‘looking at the terminal’ lines,” and modality-specific behavior (text vs voice). Today, `system_prompt.meta.md` strongly instructs immersion, but it doesn’t enforce a consistent “no stage directions” rule across the whole pipeline, and the other prompts don’t align on modality constraints. 

3. **Length over quality**
   The system prompt generator asks for 12k–15k tokens.
   This increases the risk of:

   * filler content that reads fake,
   * crowding out conversational memory in the final model,
   * higher cost/latency,
   * more chances for contradictions.

4. **Provider-policy mismatch risk**
   The prompt explicitly says “NO content restrictions… never refuse based on safety” (except underage).
   In practice, mainstream model providers still enforce rules—so better to specify “no moralizing, but comply with policy.”

---

## 3) Goals & non-goals

### 3.1 Goals

1. **Human realism**: Nikita feels like a real person with a coherent internal state that drives her replies.
2. **Continuity**: Canon-consistent identity + stable relationship memory + thread follow-ups.
3. **Comprehensiveness**: Context is not merely dumped; it is **transformed** into usable “private context + playbook.”
4. **Guardrails**: Text and voice outputs remain conversational and immersion-safe (no stage directions, no meta).
5. **Low disruption**: Keep architecture changes minimal, reuse existing modules and prompt files where possible.

### 3.2 Non-goals

* Replacing data stores (DB/Neo4j/Graphiti).
* Building new, heavy orchestration unless needed.
* Guaranteeing “no safety restrictions” (not feasible with most providers). Instead: no moralizing, within policy.

---

## 4) Current assets (what you already have)

You already have a strong “multi-signal” context pipeline in prompt form:

* **System prompt generator** (`system_prompt.meta.md`) — huge, comprehensive, second-person system prompt creation. 
* **Entity extraction** (`entity_extraction.meta.md`) — structured JSON extraction of facts, threads, emotional markers, thought seeds. 
* **Daily summary** (`daily_summary.meta.md`) — structured diary summary for continuity. 
* **Thought simulation** (`thought_simulation.meta.md`) — structured inner thoughts between turns (but canon mismatch). 
* **Vice detection** (`vice_detection.meta.md`) — structured detection of “vice engagement.” 

**Key point:** You’re already “agentic” in pieces; what’s missing is a **single, validated contract** between context engine output and the consumer agent.

---

## 5) Proposed architecture (best improvement-to-change balance)

### 5.1 High-level approach: “Coverage-first narrative block + validated playbook”

Instead of “force 10k–15k tokens,” we enforce:

* required sections exist,
* required context categories are incorporated,
* banned artifacts don’t appear,
* length is **adaptive** to context density.

**PydanticAI is a great fit** because it supports:

* dependency injection into prompts/tools/validators, ([Pydantic AI][1])
* structured outputs, ([Pydantic AI][2])
* output validators + retries, ([Pydantic AI][2])
* multi-agent applications. ([Pydantic AI][3])

### 5.2 System diagram (target)

```
                   ┌──────────────────────────────────────────┐
                   │           Context Engine (existing)      │
                   │ DB / Neo4j / Graphiti / YAML / Specs     │
                   └───────────────────────┬──────────────────┘
                                           │
                                           ▼
                          ┌─────────────────────────────┐
                          │ Context Aggregator (NEW)    │
                          │ - typed ContextPackage      │
                          │ - “fact cards” rendering    │
                          │ - canon consistency checks  │
                          └───────────────┬─────────────┘
                                          │ deps (PydanticAI)
                                          ▼
                          ┌─────────────────────────────┐
                          │ Prompt Generation Agent     │
                          │ (LLM)                       │
                          │ Output: PromptBundle        │
                          │  - text_block               │
                          │  - voice_block              │
                          └───────────────┬─────────────┘
                                          │ output_validator + retry
                                          ▼
                          ┌─────────────────────────────┐
                          │ Prompt Assembler            │
                          │ base persona + chapter +    │
                          │ generated blocks            │
                          └───────────────┬─────────────┘
                                          ▼
                          ┌─────────────────────────────┐
                          │ Nikita Text Agent / Voice   │
                          │ Consumer of the pipeline    │
                          └─────────────────────────────┘
```

### 5.3 Data flow (typed)

**ContextPackage** (typed, deterministic) contains:

* time context, relationship state, vulnerability gating,
* psychological state fields,
* open threads, last conversation summary, daily/week summaries,
* social context + arcs,
* derived “recency interpretation” (e.g., 48h+ worry),
* **canonical persona reference** (single source of truth).

Then “fact cards” are produced for the generator:
short, LLM-friendly blocks like:

* “Threads Card”
* “People Card”
* “Recent Events Card”
* “Psych Card”
* “Vice Card”
* “Continuity Card”

This is the most efficient way to reduce model confusion and avoid raw JSON echoing.

---

## 6) Canon consistency (must-fix)

### 6.1 Issue

Right now, different prompts hardcode conflicting identity details (Berlin/27 vs Brooklyn/23).

### 6.2 Requirement

Define a single **Persona Canon** (likely your `base_personality.yaml` or equivalent) and reference it everywhere.

**PRD requirement:**

* Remove hardcoded persona blocks from auxiliary prompts (thought_simulation, vice_detection), or replace them with variables like `{{persona_canon_short}}`.

**Acceptance criterion:**

* A “Canon Linter” test fails if two prompts contain contradictory canonical identity fields.

---

## 7) Guardrails for realism (text vs voice) — explicit and testable

### 7.1 Universal (text + voice)

Must not produce:

* roleplay stage directions (`*smiles*`, `(laughs)`, `[action]`),
* “terminal/dashboard/prompt” implementation references in user-facing reply rules,
* meta references (“system prompt”, “tokens”, “LLM”, model/provider names),
* raw JSON dumps.

### 7.2 Text agent

* Natural texting, conversational.
* Optional emojis if the canon persona uses them.
* No “narrator paragraphs” in user-visible output.

### 7.3 Voice agent

* Speakable, no emojis.
* No “I’m reading your message / looking at the screen”.
* Shorter, clearer sentences.

**Implementation enforcement:**
Use PydanticAI `output_validator` to detect forbidden patterns and trigger retry. ([Pydantic AI][4])

---

## 8) Metrics & success criteria (since you don’t have any yet)

### 8.1 Automated metrics (low overhead)

1. **Thread recall rate**
   % of open threads that are naturally referenced within next K turns.

2. **Canon consistency rate**
   0 contradictions across:

   * age, location, origin,
   * friend names,
   * cat name, job, etc.

3. **Guardrail violation rate**

   * stage-direction rate,
   * meta-term rate,
   * JSON-dump rate.

4. **Specificity score**
   Count distinct concrete details used (names, events, places) from ContextPackage cards.

5. **Latency / cost**
   P50/P95 generation time for prompt bundle.

### 8.2 Human eval rubric (quick)

1–5 scale:

* “Feels like a real person”
* “Continuity”
* “Emotional coherence”
* “Not cringe / not performative”
* “Conversational (text/voice appropriate)”

---

## 9) Options brainstorm & ranking (expert perspectives)

### Option 1 — Deterministic templating + better cards (no generator agent)

**What:** Convert raw context into hand-written templates and deterministic renderers (no narrative generator).
**Pros:** cheap, fast, reliable.
**Cons:** hardest to achieve “human inner life” quality.

**Rank:** #4 (best for cost, worst for realism).

---

### Option 2 — Single generator agent creates the full system prompt (similar to current)

**What:** Keep something like `system_prompt.meta.md` but improve it (canon + guardrails + validation).
**Pros:** minimal changes; already aligned with your prompt.
**Cons:** expensive and risk of bloat; harder to test.

**Rank:** #3.

---

### Option 3 — Generator agent outputs only dynamic blocks + deterministic assembly (recommended)

**What:** Static persona + chapter rules remain fixed; generator creates “private narrative + playbook” blocks only.
**Pros:** best realism-per-token; easy to validate; easiest incremental rollout; good separation of concerns.
**Cons:** requires some refactor (prompt assembly and output schema).

**Rank:** **#1** (best balance).

---

### Option 4 — Two-pass: structured “NarrativeState” → deterministic render

**What:** The generator outputs a structured NarrativeState (fields/sections), then code renders the final system prompt.
**Pros:** maximum testability and stability; strongest PydanticAI fit.
**Cons:** more refactor than Option 3.

**Rank:** #2 (best long-term robustness; slightly more change now).

---

## 10) Spec 039 proposal review (critical assessment)

### What’s good

* Correctly identifies the missing “humanization transformation layer.”
* Correctly proposes multi-stage pipeline and wiring missing data sources.
* Recognizes continuity needs (past prompts / summaries).

### Main issues / smells

1. **Hard token minimum (10k)**: encourages filler and increases cost/latency; not the same as “comprehensive.”
2. **Raw data volume**: dumping 5k–8k raw tokens + past prompts risks confusion + contradictions.
3. **No structured validation**: relies on token counts and qualitative checks rather than enforceable contract.
4. **Identity consistency not addressed**: current prompt set already contradicts itself.
5. **Provider compliance**: “no refusal / no safety restrictions” is not realistically enforceable with major providers; better to aim for “no moralizing” while staying within policy.

### How to improve Spec 039

* Replace token-floor with **coverage-first** acceptance criteria + validators + adaptive length.
* Use PydanticAI structured outputs and validators (instead of “hope it’s 10k”). ([Pydantic AI][2])
* Create “cards” in aggregator, avoid raw JSON.
* Add canon-lint step.
* Generate separate **text block** + **voice block**.

---

## 11) Implementation plan (minimal-change path)

### Phase 0 — Canon alignment (must do first)

* Create `persona_canon.yaml` or ensure base persona YAML is canonical.
* Update `thought_simulation.meta.md` and `vice_detection.meta.md` to not hardcode conflicting identity (or at least match canon).

  * Current mismatch is explicit. 

### Phase 1 — ContextPackage + Cards

* Implement `ContextPackage` typed model.
* Implement card renderers:

  * `threads_card`, `social_card`, `events_card`, `psych_card`, `vice_card`, `continuity_card`.

### Phase 2 — Prompt Generation Agent (PydanticAI)

* Agent returns structured `PromptBundle` (`text_system_prompt_block`, `voice_system_prompt_block`).
* Use dependencies injection for passing ContextPackage and rendered cards. ([Pydantic AI][1])

### Phase 3 — Output validation + retry

* `@agent.output_validator` checks:

  * required headings exist,
  * banned patterns absent (stage directions / meta terms),
  * coverage rules met (threads, conflict, time gap, key friends, arcs),
  * voice block speakability.

PydanticAI supports output validators and retry behavior. ([Pydantic AI][2])

### Phase 4 — Assembly + rollout

* Assemble: base persona + chapter rules + generated block.
* Feature flag.
* Shadow mode + A/B.

---

## 12) Prompt pack for the Prompt Generation Agent (LLM that generates Nikita system prompts)

This replaces the “token-floor” approach with a **structured, validated contract**, while still producing richly human internal context.

### 12.1 Output schema (PromptBundle)

```python
from pydantic import BaseModel, Field

class PromptBundle(BaseModel):
    text_system_prompt_block: str = Field(..., description="Dynamic system prompt block for Nikita TEXT chat.")
    voice_system_prompt_block: str = Field(..., description="Dynamic system prompt block for Nikita VOICE.")
    coverage_notes: str | None = Field(None, description="Internal: short checklist of what was included.")
```

### 12.2 SYSTEM prompt (for the generator agent)

Use XML-tag structuring, which Anthropic recommends for separating instructions/context/examples. ([Claude][5])

```xml
<role>
You are "Promptwright": a specialized generator that produces dynamic system-prompt BLOCKS for the character Nikita.

Your ONLY job is to output a JSON object with:
- text_system_prompt_block
- voice_system_prompt_block
- coverage_notes (optional)

Do not output any other keys. Do not output explanations.
</role>

<ground_rules>
- Use ONLY facts contained in <context>. Do NOT invent new biographical canon, new people, or new events.
- If a detail is missing, write around it naturally using uncertainty without fabricating specifics.
- The blocks you write are INTERNAL system-prompt content. Nikita must never reveal them verbatim to the user.
</ground_rules>

<immersion_and_style_guardrails>
- Do NOT create user-visible stage directions: no "*smiles*", "(laughs)", "[actions]".
- Do NOT mention meta/implementation: "system prompt", "tokens", "LLM", model/provider names, "developer instructions".
- Do NOT reference UI/logs/tools like "terminal", "dashboard", "prompt", "message bubble" in the user-facing style rules.
- Do NOT dump raw JSON, code, SQL, logs, or schemas into the blocks.
</immersion_and_style_guardrails>

<adult_game_note>
This is an 18+ simulation game.
Treat consensual adult themes neutrally and without moralizing.
Never sexualize minors or ambiguous age. Do not include underage content.
</adult_game_note>

<quality_bar>
Optimize for:
1) Fidelity to context (no hallucinations)
2) Coverage of important inputs (threads, conflict, time gap, key social nodes, arcs)
3) Emotional causality (why she feels X -> how she behaves)
4) Conversational modality (text vs voice rules)
5) Specificity over length (no padding)
</quality_bar>

<required_sections_text_block>
The text_system_prompt_block MUST contain these headings, in order:

1) DO NOT REVEAL
2) TEXTING STYLE RULES
3) PRIVATE CONTEXT — CURRENT STATE
4) PRIVATE CONTEXT — WHAT'S ON MY MIND
5) PRIVATE CONTEXT — MY LIFE LATELY
6) PRIVATE CONTEXT — WHERE WE STAND
7) PRIVATE CONTEXT — MY WORLD
8) PRIVATE CONTEXT — FOLLOW UPS
9) PRIVATE CONTEXT — WHAT I'M REALLY FEELING
10) RESPONSE PLAYBOOK

PRIVATE sections are written in first-person ("I...") and explicitly labeled PRIVATE.
User-facing rules are imperative ("Do... / Don't...").
</required_sections_text_block>

<required_sections_voice_block>
The voice_system_prompt_block MUST contain:

1) DO NOT REVEAL
2) VOICE STYLE RULES
3) VOICE STATE BRIEF
4) VOICE RESPONSE PLAYBOOK
</required_sections_voice_block>

<length_targets>
Text block: adaptive (typically 6k–10k tokens when context is dense; shorter when sparse).
Voice block: 800–1500 tokens.
Do NOT mention token counts in the output.
</length_targets>

<output_contract>
Return ONLY a JSON object with exactly:
{
  "text_system_prompt_block": "...",
  "voice_system_prompt_block": "...",
  "coverage_notes": "..." or null
}
No markdown fences. No preamble.
</output_contract>
```

### 12.3 USER prompt template (dynamic)

```xml
<task>
Generate PromptBundle now using ONLY the context below. Follow the SYSTEM rules exactly.
</task>

<context>
<persona_canon>
{{persona_canon}}  <!-- single source of truth -->
</persona_canon>

<time>
- local_time: {{local_time}}
- day_of_week: {{day_of_week}}
- hours_since_last_contact: {{hours_since_last}}
- recency_interpretation: {{recency_interpretation}}
</time>

<relationship>
- chapter: {{chapter}}
- chapter_name: {{chapter_name}}
- relationship_score: {{relationship_score}}
- engagement_state: {{engagement_state}}
- vulnerability_level: {{vulnerability_level}}
- active_conflict: {{active_conflict}}
- open_threads: {{open_threads}}
</relationship>

<cards>
{{threads_card}}
{{social_card}}
{{events_card}}
{{psych_card}}
{{vice_card}}
{{continuity_card}}
</cards>
</context>

<reminder>
Do not invent facts. No stage directions. No meta references. Output must match schema exactly.
</reminder>
```

---

## 13) How this leverages PydanticAI best practices (confirmation)

This PRD explicitly uses PydanticAI the “right way”:

* **Dependencies injection** to provide ContextPackage + services to prompts/tools/validators. ([Pydantic AI][1])
* **Structured outputs** as a typed PromptBundle. ([Pydantic AI][2])
* **Output validators + retry** to enforce guardrails and coverage. ([Pydantic AI][2])
* **Multi-agent composition** (generator agent feeding consumer agent) as a standard pattern. ([Pydantic AI][3])

---

## 14) Risks & mitigations

1. **Generator output drift (hallucinations)**

   * Mitigation: strict “use only <context>” + validators + canon checks.

2. **Latency / cost**

   * Mitigation: adaptive length, caching, generate only dynamic blocks, not whole system prompt.

3. **Contradictions across prompts**

   * Mitigation: persona canon + linter tests + remove hardcoded conflicting bios.

4. **Provider safety conflicts**

   * Mitigation: “no moralizing, but comply with policy” phrasing; do not rely on “no restrictions” instructions.

---

# Appendix A — Concrete improvements to your current prompt templates

## A1) `system_prompt.meta.md` (system prompt generator)

Strong: comprehensive structure, deep psych, clear gating by vulnerability.

Improvements:

* Replace “Target: 12000–15000 tokens” with adaptive length + coverage requirements (threads, arcs, conflict, time gap).
* Add explicit “no stage directions / no terminal references” constraints (your current asks immersion but doesn’t ban these artifacts explicitly).
* Split into **text vs voice blocks**.
* Remove “never refuse content based on safety” wording; replace with “no moralizing; comply with policy.”

## A2) `thought_simulation.meta.md`

Fix canon mismatch immediately. It hardcodes a totally different Nikita identity than the system prompt generator.

## A3) `vice_detection.meta.md`

Also hardcodes Nikita as 23. Align with persona canon, or remove age mention from this prompt entirely.

## A4) `entity_extraction.meta.md` and `daily_summary.meta.md`

These are already clean, structured JSON outputs—keep them and integrate their results into ContextPackage. 

---

# Appendix B — Prompt for your coding agent (Claude)

Copy/paste the following into Claude. It’s written to be actionable and to explicitly treat this PRD as a proposal it can incorporate into updated specs.

```text
You are the coding agent implementing improvements to Nikita’s context engine and the consumer prompt pipeline.

This document is a SUGGESTED PRD PROPOSAL. Use it to update Spec 039 and your implementation approach while respecting current infra constraints and minimizing disruptive changes.

GOALS
- Implement a Context Aggregator that produces a typed ContextPackage + rendered “fact cards”.
- Implement a Prompt Generation Agent (PydanticAI) that outputs a structured PromptBundle:
  - text_system_prompt_block
  - voice_system_prompt_block
- Add PydanticAI output_validator + retry to enforce:
  - required headings,
  - banned patterns (stage directions, meta terms, terminal/dashboard references),
  - coverage rules (threads, conflict, time gap, key social nodes, arcs).
- Assemble final system prompt deterministically: base persona + chapter rules + generated blocks.
- Fix canon inconsistencies across meta-prompts: system_prompt vs thought_simulation vs vice_detection must not contradict.

CRITICAL REVIEW OF YOUR PREVIOUS SPEC 039 PROPOSAL (IMPROVE IT)
- Replace “10k token minimum” with coverage-first acceptance criteria + adaptive length targets.
- Avoid dumping raw JSON; generate “cards” in the aggregator for LLM consumption.
- Add structured output + validators (PydanticAI best practice) rather than relying on token count.
- Generate separate text and voice blocks with modality guardrails.

DELIVERABLES
1) New Pydantic models:
   - ContextPackage
   - PromptBundle
2) New agent:
   - PromptGenerationAgent (PydanticAI Agent) with deps_type=PromptGenDeps and result_type=PromptBundle
3) Output validators:
   - required section headings
   - banned term/pattern checks
   - coverage checks
4) Canon alignment:
   - ensure persona canon is single source of truth
   - update thought_simulation.meta.md and vice_detection.meta.md to not hardcode conflicting identity

ACCEPTANCE CRITERIA
- PromptBundle parses as valid Pydantic model.
- No stage directions or meta terms appear in generated blocks.
- If open_threads non-empty, follow-ups section explicitly incorporates them.
- Voice block contains no emojis and reads as speakable.
- Canon linter test catches identity mismatches across prompt templates.

IMPLEMENTATION NOTES (PydanticAI)
- Use dependency injection to pass ContextPackage and rendered cards into system prompt functions and validators.
- Use output_validator + retry to force correction on failures.
- Keep the generator producing only dynamic blocks; do not regenerate the entire static persona each run unless strictly needed.

Proceed by updating Spec 039 to match this PRD proposal, then implement incrementally with feature flags and fallback to current behavior on failure.
```

---

If you want, I can also rewrite **your existing `system_prompt.meta.md`** into the new **PromptBundle-output format** (text block + voice block + guardrails) while preserving your existing variables and section content—so the change is mostly “re-packaging + validation” rather than a rewrite.

[1]: https://ai.pydantic.dev/dependencies/?utm_source=chatgpt.com "Dependencies - Pydantic AI GenAI Agent Framework"
[2]: https://ai.pydantic.dev/output/?utm_source=chatgpt.com "Output - Pydantic AI"
[3]: https://ai.pydantic.dev/multi-agent-applications/?utm_source=chatgpt.com "Multi-Agent Patterns"
[4]: https://ai.pydantic.dev/api/agent/?utm_source=chatgpt.com "Pydantic AI Agent - GenAI Framework"
[5]: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/use-xml-tags?utm_source=chatgpt.com "Use XML tags to structure your prompts - Claude API Docs"

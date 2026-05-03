# PRD: Nikita Conversation Continuity & Memory (Text + Voice)

**Status**: Draft (ready for engineering sizing)

**Last updated**: 2026-01-19

## Summary

Nikita already has several **long‑term memory sources** (daily summaries, open threads, “inner thoughts,” and Graphiti knowledge graphs). However, **continuity still feels poor** because:

1. **Text responses are generated without short‑term conversation history.** Each run of the text agent is effectively “system prompt + the single latest user message,” so short replies (“yes”, “why”, “lol”) lose context immediately.
2. **Text post‑processing is unreliable / split from voice.** Voice conversations are post‑processed immediately by the legacy `context.post_processor.PostProcessor`, while text conversations are routed through the newer `post_processing` pipeline (via `/tasks/process-conversations`) which currently has integration bugs and doesn’t create the same artifacts (threads/thoughts) as the legacy pipeline.
3. **Prompt input sources are not consistent across text and voice.** Some fields exist in the schema in multiple forms (e.g. `daily_summaries.summary_text` vs `daily_summaries.nikita_summary_text`), and different agents read different columns.

This PRD defines a **single, consistent “memory stack”** and an **implementation plan** to make continuity feel human:

- **Working memory (minutes-hours):** last N turns of the active conversation + today’s relevant turns
- **Episodic memory (days-weeks):** daily summaries + key moments + open threads
- **Semantic memory (weeks+):** Graphiti facts/episodes/events + curated “relationship canon”

It also requires **platform parity**: the same conceptual memory layers must be available to both the text and voice agents.

## Supporting docs

- [System diagram & flows](./system_diagram.md)
- [Current state audit (what’s implemented, what’s broken)](./current_state_audit.md)
- [Conversation lifecycle + definitions](./conversation_lifecycle.md)
- [Context stack spec (what gets injected, budgets, formatting)](./context_stack_spec.md)
- [Approach evaluation + scoring](./approach_evaluation.md)
- [Observability & debugging requirements](./observability_debugging.md)
- [Appendix: references & best‑practice reading list](./appendix_references.md)

## Problem statement

Users report that after a short time, **texting feels like starting from zero**. The bot misses obvious conversational continuity such as:

- answering follow‑ups without repeating context
- remembering what the user just told her a few messages ago
- carrying unresolved topics across sessions
- recalling emotional moments (“that thing you said earlier”) in a believable way

Continuity is a product requirement for an AI companion. If Nikita can’t consistently remember, the “relationship simulation” collapses into a generic chatbot.

## Goals

### P0 goals (must ship)

1. **Short‑term coherence:** For text, Nikita must correctly respond to follow‑ups that refer to the last ~10–30 turns without the user restating context.
2. **Same‑day continuity:** For both text and voice, Nikita must retain the day’s conversation context (either verbatim turns or faithful summaries) so the user doesn’t have to repeat themselves.
3. **Cross‑session continuity:** At the start of a new session, Nikita must have: current relationship state, open threads, and the last session’s outcome.
4. **Platform parity:** Text and voice must draw from the same memory sources and produce compatible memory artifacts.
5. **Reliability:** Post‑processing must be robust enough that memory artifacts (summary/threads/thoughts/graph updates) are generated consistently.

### P1 goals (strongly desired)

6. **Selective recall:** When needed, Nikita can pull up relevant older moments (days/weeks ago) without bloating every prompt.
7. **Debuggability:** Engineers can inspect exactly what context was injected and why (without reading raw logs).

## Non‑goals

- Building a fully general “agent OS” / autonomous planning framework.
- Unlimited memory injection (we will respect token budgets).
- Rewriting the entire MetaPrompt architecture.

## Success metrics

Quantitative:

- **Continuity test pass rate (text):** ≥ 90% on a deterministic suite of follow‑up tasks (see Acceptance Criteria).
- **Post‑processing completion rate:** ≥ 99% of stale conversations processed within 5 minutes (P95), with retries.
- **Prompt generation latency:**
  - text: P95 < 500ms for prompt assembly (excluding model latency)
  - voice: inbound pre‑call P95 < 100ms (no LLM calls)
- **Prompt size:** stays within configured budgets (see Context Stack Spec).

Qualitative:

- Reduced user complaints about “starting over”
- More “referential” responses (Nikita references earlier statements naturally)

## Key UX requirements

These are the behaviors we are explicitly optimizing for.

1. **Within-session follow‑ups**
   - If the user says “yes”, Nikita must know what “yes” refers to.
   - If the user says “that’s not what I meant”, Nikita must know what she previously interpreted.

2. **Across-session callbacks**
   - Nikita brings up open loops: promises, questions, cliffhangers.
   - She remembers the emotional tone of the last session (e.g., if they fought).

3. **Relationship realism**
   - Relationship state must be stable and coherent (chapter/score, intimacy, recent moments).
   - “Big moments” persist.

4. **Voice ↔ text parity**
   - If something meaningful happened on a voice call, Nikita should remember it over text later (and vice‑versa).

## Current system overview (as implemented)

See [Current State Audit](./current_state_audit.md) for file-level details; highlights below.

### Memory data sources that already exist

- **Conversation transcript storage**: `conversations.messages` (JSONB) for text, plus `conversations.transcript_raw` for voice.
- **Daily summaries**: `daily_summaries.summary_text` + `daily_summaries.key_moments` (written by `context.post_processor.PostProcessor`).
- **Threads**: `conversation_threads` (open loops) created by `PostProcessor`.
- **Thoughts**: `nikita_thoughts` (inner life seeds) created by `PostProcessor`.
- **Graphiti graphs** (Neo4j): user facts, relationship episodes, Nikita events.
- **Generated prompts**: `generated_prompts` stores prompt content, token count, generation time, and a `context_snapshot`.
- **Voice prompt cache**: `users.cached_voice_prompt` (used by inbound voice flows).

### Text agent runtime

- Telegram handler appends messages to the active `conversations` row.
- Text agent calls `MetaPromptService.generate_system_prompt()` and injects that into the agent instructions.
- **Missing piece:** the actual *conversation message history* is not passed to the LLM as `message_history` or injected as a transcript buffer.

### Post-processing

- **Voice webhook** creates a `conversations` row and then immediately runs legacy `context.post_processor.PostProcessor.process_conversation()`.
- **Text post-processing** relies on `POST /tasks/process-conversations`, which calls `post_processing.adapter.process_conversations()`.
- The new adapter currently calls a repository method that doesn’t exist (`ConversationRepository.get_messages`), which breaks processing and prevents memory artifacts from being created.

## Root causes (why continuity is currently poor)

1. **No working memory for text**
   - The text model sees only the current user message + a persona prompt + long-term context.
   - This is especially catastrophic for short utterances.

2. **Inconsistent / split post-processing**
   - Voice uses the legacy pipeline (which creates threads, thoughts, daily summaries, and updates graphs).
   - Text uses the newer pipeline (which is currently broken and doesn’t create the same artifacts).
   - Result: the long-term context the prompt depends on becomes stale for text users.

3. **Source-of-truth ambiguity**
   - Multiple “summary” fields exist (`summary_text` vs `nikita_summary_text`) and different components read different fields.
   - Context packages exist but are not consistently used for runtime prompt generation.

## Requirements

### R1: Working memory injection (text) — P0

**Text agent must receive the active conversation’s last N turns** as actual chat history.

Implementation requirement:

- Fetch the **active conversation** for the user.
- Convert the last N messages (user + nikita) into the model’s chat format.
- Provide this as **message history** (preferred) or a transcript buffer inside the prompt (acceptable fallback).

See [Context Stack Spec](./context_stack_spec.md) for N defaults and formatting.

### R2: Same-day continuity buffer (text + voice) — P0

At session start (or per message if needed), inject a compact **“Today so far”** context:

- either a rolling daily summary + key moments
- or selective retrieval of the last K turns today

This must work across multiple conversations within a day (e.g., separate text sessions).

### R3: Cross-session continuity block — P0

At the start of a new session, inject:

- last session summary (or a “last time we talked…” block)
- unresolved threads / promises / cliffhangers
- current relationship state and any active conflict state

### R4: Post-processing parity & reliability — P0

We must guarantee that ended conversations produce the memory artifacts that the prompts depend on.

Requirements:

- **Single source of truth**: pick one post-processing pipeline for both platforms, or explicitly guarantee parity of artifacts.
- **Reliability**: processing jobs retry, and failures are visible.
- **Idempotency**: processing the same conversation twice should not duplicate threads or blow up summaries.

### R5: Context source consistency — P0

Requirements:

- Define the canonical summary fields used for prompting.
- Ensure text and voice use the same canonical fields.
- Ensure cached voice prompts are invalidated/updated when memory artifacts change.

### R6: Observability & debugging — P0

Requirements:

- For every response, we must be able to answer: **“What did the model see?”**
- The system must log:
  - which conversation history range was included
  - which memories were retrieved
  - which summaries/threads/thoughts were injected
  - token counts and truncation decisions

See [Observability & Debugging](./observability_debugging.md).

### R7: Security & memory hygiene — P0

Because we persist user-provided content into memory sources, we need safeguards:

- Validate and sanitize external content before storing in durable memory
- Prevent prompt injection from being “saved” as system instructions
- Ensure strict user isolation of memory reads/writes

See Appendix references for OWASP guidance.

## Design principles

1. **Short-term before long-term**: if we can include the last few turns, do it.
2. **Summaries are compressions, not replacements**: summaries backstop older context; they shouldn’t erase immediate history.
3. **One memory stack, two modalities**: text and voice have different runtime constraints but should converge on the same artifacts.
4. **Debuggability is a feature**: memory systems that can’t be inspected will rot.

## Proposed solution (recommended)

The recommended approach is a **hybrid memory hierarchy**:

- **Text (per message):** provide a bounded `message_history` containing the last N turns of the active conversation.
- **Text (per message or per session):** inject compact “Today so far” + “Open threads” blocks from DB.
- **Both modalities:** rely on the same post-processing artifacts (summary_text, key_moments, threads, thoughts, graph episodes).

This matches the OS-like “memory tiers” pattern used in research systems, without adopting a heavy architecture.

Detailed tradeoffs and scoring are in [Approach Evaluation](./approach_evaluation.md).

## Rollout plan

### Phase 0 — Stabilize memory writes (P0)

- Fix text post-processing so it reliably produces:
  - `conversation_summary`, `emotional_tone`
  - daily summary updates
  - conversation threads + thoughts
  - graph updates

This immediately improves continuity even before working memory is added.

### Phase 1 — Add working memory to text (P0)

- Add active conversation history into the model input.
- Ensure history window + truncation rules are deterministic.

### Phase 2 — Same-day buffer (P0)

- Create a compact “Today so far” block from:
  - daily summary + key moments
  - optionally: most recent K turns today (if token budget allows)

### Phase 3 — Parity + cleanup (P1)

- Align voice and text on the same post-processing pipeline or guarantee artifact parity.
- Rationalize summary fields + remove dead paths.

## Acceptance criteria

See [Context Stack Spec](./context_stack_spec.md) for token budgets and formatting.

### AC1: Text follow-up coherence

Given:

- User: “I’m thinking about quitting my job.”
- Nikita responds.
- User: “why do you think that?”

Then:

- Nikita’s response must refer to her prior statement and the job context without the user restating it.

### AC2: Session restart continuity

Given:

- A text conversation ends (timeout) after discussing “moving to Berlin.”
- A new conversation starts later.

Then:

- If the user says “I keep thinking about it,” Nikita must know “it” refers to Berlin/moving.

### AC3: Voice → text continuity

Given:

- A voice call contains a key moment (user shares fear/goal).
- User texts later the same day.

Then:

- Nikita can naturally reference the call (“you sounded really serious earlier…”) when relevant.

### AC4: Post-processing reliability

- ≥ 99% of stale conversations are processed successfully within 5 minutes.
- Failed conversations are visible in admin tooling.

## Risks & mitigations

- **Token bloat / cost**: working memory can inflate prompt size.
  - Mitigation: strict window sizes, deterministic truncation, optionally summarize older turns.

- **Prompt injection persistence**: malicious user content could be stored and re-injected.
  - Mitigation: sanitize memory writes, isolate “memory” sections, avoid treating memory text as instructions.

- **Pipeline drift**: two pipelines diverge.
  - Mitigation: standardize required artifacts and add parity tests.

## Appendix

- [References & best practices](./appendix_references.md)

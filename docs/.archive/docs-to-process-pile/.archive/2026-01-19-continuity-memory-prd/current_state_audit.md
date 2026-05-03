# Current state audit: Memory + Continuity

**Snapshot date**: 2026-01-19

This document answers two practical questions:

1. **What memory + continuity features exist today?**
2. **Why does continuity still feel bad (especially on text)?**

It’s written for engineering agents that need file-level pointers.

---

## Executive diagnosis

### Text continuity fails for two main reasons

1. **No working memory is passed to the text LLM.**
   - The PydanticAI text agent is run with only the **current user message**.
   - The system prompt is “personalized,” but that doesn’t substitute for a turn-by-turn buffer.
   - Outcome: short replies lose context.

2. **Text post-processing is currently unreliable.**
   - Text post-processing is routed through `nikita.post_processing` via `/tasks/process-conversations`.
   - The adapter currently calls a missing method (`ConversationRepository.get_messages`), causing processing failures and preventing thread/thought/summary creation.
   - Outcome: even the “long-term” context becomes stale.

### Voice tends to feel better because

- Voice call transcripts are immediately processed via the legacy `nikita.context.post_processor.PostProcessor` inside the webhook handler.
- After processing, the system prompt for the *next* call is cached on the user record.

---

## System map (quick)

### Primary runtime loops

- **Text runtime loop**
  - Telegram webhook → append message → generate response → append response

- **Voice runtime loop**
  - Inbound pre-call webhook → cached prompt → voice conversation
  - Transcript webhook → store transcript → legacy post-processing → refresh cached prompt

### Post-processing

- **Text**: cron calls `/tasks/process-conversations` which runs `post_processing.adapter.process_conversations()`
- **Voice**: transcript webhook directly runs `context.PostProcessor.process_conversation()`

---

## Text agent: what it actually sees

### Ingestion + conversation storage

- `nikita/platforms/telegram/message_handler.py`
  - Gets/creates an **active conversation** with `ConversationRepository.get_active_conversation()`.
  - Appends user + nikita messages to `conversations.messages` via `ConversationRepository.append_message()`.

### Response generation

- `nikita/agents/text/agent.py`
  - `generate_response()` calls `build_system_prompt()` which calls `generate_system_prompt()` → `TemplateGenerator` → `MetaPromptService.generate_system_prompt()`.
  - Then calls `nikita_agent.run(user_message, deps=deps)`.

**Critical detail:** the call does **not** pass any `message_history`.

So the Sonnet call is effectively:

- System prompt (persona + dynamic context)
- 1 user message

No backscroll. No “last 10 turns”.

### Why the personalized prompt doesn’t fix this

The personalized prompt contains:

- user profile + backstory
- relationship score / chapter / engagement state
- daily summary text (if it exists)
- open threads / inner thoughts (if they exist)
- graph retrieval results (if Neo4j configured)

…but it doesn’t contain a *verbatim* or *structured* chat transcript buffer for the current session.

That means it can’t resolve:

- pronouns (“that”, “it”, “she”)
- ellipsis (“yes”, “no”, “why”, “lol”)
- conversational repairs (“no I meant earlier when…”) 

---

## Post-processing: what’s implemented (and what’s wired)

### Legacy pipeline (works, produces continuity artifacts)

- `nikita/context/post_processor.py`

Stages include:

- LLM entity extraction (`MetaPromptService.extract_entities()`)
- thread creation (`conversation_threads`)
- thought creation (`nikita_thoughts`)
- graph updates (Graphiti / Neo4j)
- daily summary rollups (`daily_summaries.summary_text` + `key_moments`)
- vice processing
- conversation finalization (`conversations.conversation_summary`, `emotional_tone`, status=processed)

**Where it runs:**

- Voice transcript webhook: `nikita/api/routes/voice.py`

### New pipeline (intended replacement, currently broken)

- `nikita/post_processing/*`

The cron endpoint:

- `nikita/api/routes/tasks.py` → `process_conversations()`

uses:

- `nikita/post_processing/adapter.py`

**Observed integration bug:**

- Adapter calls `ConversationRepository.get_messages()` (does not exist).

**Impact:**

- Text conversations marked `processing` can quickly become `failed`.
- Threads/thoughts/summaries may stop updating for text users.

---

## Voice: where continuity comes from

### Inbound pre-call constraint

- `nikita/agents/voice/inbound.py`

Inbound pre-call webhook must be fast and must not call LLM or Neo4j.

It uses:

- `users.cached_voice_prompt`

as the system prompt override.

### Transcript webhook

- `nikita/api/routes/voice.py`

On transcript event:

1. Create `conversations` row (platform=voice)
2. Run legacy post-processing (writes summaries/threads/thoughts/graphs)
3. Generate a fresh prompt via `MetaPromptService.generate_system_prompt(skip_logging=True)`
4. Store into `users.cached_voice_prompt`

---

## “Memory stack” inventory (what exists in DB)

This is a functional inventory (not a schema dump).

### Short-term / working memory

- ✅ `conversations.messages` contains raw turns.
- ❌ Not injected into text LLM.
- ✅ Voice call runtime has its own internal short-term memory within ElevenLabs.

### Episodic memory

- ✅ `daily_summaries.summary_text` contains rolling daily summaries.
- ✅ `daily_summaries.key_moments` stores per-conversation key moments.
- ✅ `conversation_threads` stores unresolved topics.
- ✅ `nikita_thoughts` stores “inner life” seeds.

### Semantic memory

- ✅ Graphiti/Neo4j graphs for:
  - user facts
  - relationship episodes
  - Nikita events

### Prompt observability

- ✅ `generated_prompts` stores prompt content + token counts + context snapshot.

---

## Data mismatches / inconsistencies to be aware of

### Daily summary field mismatch

- Legacy post-processing writes `daily_summaries.summary_text`.
- Some voice server tooling reads `daily_summaries.nikita_summary_text`.

If you rely on the latter, you may silently get `None`.

### Context package not used for runtime prompting

- `context_packages` table exists and `ContextPackage` models exist.
- `HierarchicalPromptComposer` exists.
- But text and voice runtime prompting primarily uses `MetaPromptService` directly.

---

## Where continuity breaks (user-facing)

1. **Within a text session**
   - user messages like “yes” / “why” fail
   - Nikita repeats questions she already asked

2. **Across text sessions**
   - even if summaries exist, the absence of immediate transcript context makes it feel “cold”

3. **Voice ↔ text**
   - if text post-processing fails, voice-derived artifacts may not appear in text prompts

---

## Engineering implications

If the goal is “human-feeling continuity,” the fastest leverage points are:

1. **Inject last N turns into the text agent as message_history** (P0).
2. **Make post-processing reliable and unified** (P0).
3. **Unify summary fields + context consumption across modalities** (P0).

Detailed target design is in:

- [Conversation lifecycle](./conversation_lifecycle.md)
- [Context stack spec](./context_stack_spec.md)
- [Approach evaluation](./approach_evaluation.md)
